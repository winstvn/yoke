from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest

from yoke.downloader import VideoDownloader
from yoke.models import PlaybackState, Song
from yoke.redis_store import RedisStore
from yoke.router import MessageRouter
from yoke.session import SessionManager
from yoke.ws import ConnectionManager


def make_mock_ws(singer_id: str | None = None) -> AsyncMock:
    ws = AsyncMock()
    ws.singer_id = singer_id
    return ws


def _song(video_id: str = "v1", title: str = "Test Song") -> Song:
    return Song(
        video_id=video_id,
        title=title,
        thumbnail_url="https://example.com/thumb.jpg",
        duration_seconds=180,
    )


@pytest.fixture
async def setup(tmp_path: Path):
    redis = fakeredis.aioredis.FakeRedis()
    store = RedisStore(redis)
    session = SessionManager(store)
    connections = ConnectionManager()
    downloader = VideoDownloader(video_dir=tmp_path / "test-videos", max_concurrent=1)
    router = MessageRouter(
        session=session, connections=connections, downloader=downloader
    )
    yield router, connections, session, store
    await redis.aclose()


async def test_handle_join(setup):
    router, connections, session, store = setup
    ws = make_mock_ws()

    await router.handle(ws, {"type": "join", "name": "Alice"})

    # ws should have singer_id set
    assert getattr(ws, "singer_id", None) is not None

    # Should have sent a state message to the client
    ws.send_json.assert_awaited()
    sent = ws.send_json.call_args_list[0][0][0]
    assert sent["type"] == "state"
    assert "singers" in sent
    assert "queue" in sent

    # Singer should be in the store
    singers = await store.get_all_singers()
    assert len(singers) == 1
    assert singers[0].name == "Alice"


async def test_handle_join_broadcasts_to_others(setup):
    router, connections, session, store = setup

    # First singer joins
    ws1 = make_mock_ws()
    await router.handle(ws1, {"type": "join", "name": "Alice"})

    # Second singer joins
    ws2 = make_mock_ws()
    await router.handle(ws2, {"type": "join", "name": "Bob"})

    # ws1 should have received a singer_joined broadcast
    # The last call on ws1 should be the broadcast from Bob joining
    calls = ws1.send_json.call_args_list
    broadcast_found = False
    for call in calls:
        msg = call[0][0]
        if msg.get("type") == "singer_joined":
            broadcast_found = True
            assert msg["singer"]["name"] == "Bob"
    assert broadcast_found, "Expected singer_joined broadcast to first client"


async def test_handle_playback(setup):
    router, connections, session, store = setup

    ws = make_mock_ws()
    await router.handle(ws, {"type": "join", "name": "Alice"})
    ws.send_json.reset_mock()

    # Send play action
    await router.handle(ws, {"type": "playback", "action": "play"})

    playback = await store.get_playback()
    assert playback.status == "playing"

    # Should have broadcast the playback update
    ws.send_json.assert_awaited()
    sent_messages = [call[0][0] for call in ws.send_json.call_args_list]
    playback_msg = [m for m in sent_messages if m.get("type") == "playback_updated"]
    assert len(playback_msg) > 0
    assert playback_msg[0]["playback"]["status"] == "playing"


async def test_handle_playback_pause(setup):
    router, connections, session, store = setup

    ws = make_mock_ws()
    await router.handle(ws, {"type": "join", "name": "Alice"})

    # First play, then pause
    await router.handle(ws, {"type": "playback", "action": "play"})
    ws.send_json.reset_mock()

    await router.handle(ws, {"type": "playback", "action": "pause"})

    playback = await store.get_playback()
    assert playback.status == "paused"


async def test_handle_playback_stop(setup):
    router, connections, session, store = setup

    ws = make_mock_ws()
    await router.handle(ws, {"type": "join", "name": "Alice"})

    await router.handle(ws, {"type": "playback", "action": "play"})
    ws.send_json.reset_mock()

    await router.handle(ws, {"type": "playback", "action": "stop"})

    playback = await store.get_playback()
    assert playback.status == "stopped"


async def test_handle_playback_restart(setup):
    router, connections, session, store = setup

    ws = make_mock_ws()
    await router.handle(ws, {"type": "join", "name": "Alice"})

    # Set some position first
    await store.save_playback(PlaybackState(status="playing", position_seconds=42.0))
    ws.send_json.reset_mock()

    await router.handle(ws, {"type": "playback", "action": "restart"})

    playback = await store.get_playback()
    assert playback.status == "playing"
    assert playback.position_seconds == 0.0


async def test_handle_playback_skip(setup):
    router, connections, session, store = setup

    ws = make_mock_ws()
    await router.handle(ws, {"type": "join", "name": "Alice"})

    # Queue a song first
    song = _song()
    await session.queue_song(ws.singer_id, song)
    ws.send_json.reset_mock()

    await router.handle(ws, {"type": "playback", "action": "skip"})

    # Current should now be the queued song
    current = await store.get_current()
    assert current is not None
    assert current.song.video_id == "v1"

    # Broadcast should include now_playing
    sent_messages = [call[0][0] for call in ws.send_json.call_args_list]
    now_playing_msgs = [m for m in sent_messages if m.get("type") == "now_playing"]
    assert len(now_playing_msgs) > 0


async def test_handle_pitch(setup):
    router, connections, session, store = setup

    ws = make_mock_ws()
    await router.handle(ws, {"type": "join", "name": "Alice"})
    ws.send_json.reset_mock()

    await router.handle(ws, {"type": "pitch", "value": 3})

    playback = await store.get_playback()
    assert playback.pitch_shift == 3

    # Should broadcast
    ws.send_json.assert_awaited()


async def test_handle_pitch_clamped(setup):
    router, connections, session, store = setup

    ws = make_mock_ws()
    await router.handle(ws, {"type": "join", "name": "Alice"})
    ws.send_json.reset_mock()

    # Try to set pitch beyond limit
    await router.handle(ws, {"type": "pitch", "value": 10})

    playback = await store.get_playback()
    assert playback.pitch_shift == 6  # clamped to max

    # Try negative beyond limit
    await router.handle(ws, {"type": "pitch", "value": -10})

    playback = await store.get_playback()
    assert playback.pitch_shift == -6  # clamped to min


async def test_handle_update_setting_host(setup):
    router, connections, session, store = setup

    ws = make_mock_ws()
    await router.handle(ws, {"type": "join", "name": "Alice"})
    ws.send_json.reset_mock()

    await router.handle(
        ws, {"type": "update_setting", "key": "anyone_can_reorder", "value": True}
    )

    settings = await store.get_settings()
    assert settings.anyone_can_reorder is True


async def test_handle_update_setting_non_host_rejected(setup):
    router, connections, session, store = setup

    # Host joins
    ws_host = make_mock_ws()
    await router.handle(ws_host, {"type": "join", "name": "Alice"})

    # Guest joins
    ws_guest = make_mock_ws()
    await router.handle(ws_guest, {"type": "join", "name": "Bob"})
    ws_guest.send_json.reset_mock()

    await router.handle(
        ws_guest, {"type": "update_setting", "key": "anyone_can_reorder", "value": True}
    )

    settings = await store.get_settings()
    assert settings.anyone_can_reorder is False  # unchanged

    # Should have sent error to guest
    sent = [call[0][0] for call in ws_guest.send_json.call_args_list]
    error_msgs = [m for m in sent if m.get("type") == "error"]
    assert len(error_msgs) > 0


async def test_handle_seek(setup):
    router, connections, session, store = setup

    ws = make_mock_ws()
    await router.handle(ws, {"type": "join", "name": "Alice"})
    ws.send_json.reset_mock()

    await router.handle(ws, {"type": "seek", "position": 42.5})

    playback = await store.get_playback()
    assert playback.position_seconds == 42.5


async def test_handle_unknown_type(setup):
    router, connections, session, store = setup

    ws = make_mock_ws()
    await router.handle(ws, {"type": "join", "name": "Alice"})
    ws.send_json.reset_mock()

    await router.handle(ws, {"type": "totally_unknown"})

    # Should send error
    ws.send_json.assert_awaited()
    sent = ws.send_json.call_args_list[0][0][0]
    assert sent["type"] == "error"


async def test_handle_show_qr(setup):
    router, connections, session, store = setup

    ws1 = make_mock_ws()
    await router.handle(ws1, {"type": "join", "name": "Alice"})

    ws2 = make_mock_ws()
    await router.handle(ws2, {"type": "join", "name": "Bob"})

    ws1.send_json.reset_mock()
    ws2.send_json.reset_mock()

    await router.handle(ws1, {"type": "show_qr"})

    # Both should receive show_qr broadcast
    for ws in [ws1, ws2]:
        sent = [call[0][0] for call in ws.send_json.call_args_list]
        qr_msgs = [m for m in sent if m.get("type") == "show_qr"]
        assert len(qr_msgs) > 0


async def test_handle_screen_message(setup):
    router, connections, session, store = setup

    ws = make_mock_ws()
    await router.handle(ws, {"type": "join", "name": "Alice"})
    ws.send_json.reset_mock()

    await router.handle(ws, {"type": "screen_message", "text": "Hello!"})

    ws.send_json.assert_awaited()
    sent = [call[0][0] for call in ws.send_json.call_args_list]
    msg_msgs = [m for m in sent if m.get("type") == "screen_message"]
    assert len(msg_msgs) > 0
    assert msg_msgs[0]["name"] == "Alice"
    assert msg_msgs[0]["text"] == "Hello!"


async def test_handle_queue_song(setup):
    router, connections, session, store = setup

    ws = make_mock_ws()
    await router.handle(ws, {"type": "join", "name": "Alice"})
    ws.send_json.reset_mock()

    await router.handle(
        ws,
        {
            "type": "queue_song",
            "video_id": "v1",
            "title": "Test Song",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "duration_seconds": 180,
        },
    )

    queue = await store.get_queue()
    assert len(queue) == 1
    assert queue[0].song.video_id == "v1"

    # Should broadcast queue_updated
    sent = [call[0][0] for call in ws.send_json.call_args_list]
    queue_msgs = [m for m in sent if m.get("type") == "queue_updated"]
    assert len(queue_msgs) > 0


async def test_handle_remove_from_queue(setup):
    router, connections, session, store = setup

    ws = make_mock_ws()
    await router.handle(ws, {"type": "join", "name": "Alice"})

    # Queue a song
    song = _song()
    item = await session.queue_song(ws.singer_id, song)
    ws.send_json.reset_mock()

    await router.handle(ws, {"type": "remove_from_queue", "item_id": item.id})

    queue = await store.get_queue()
    assert len(queue) == 0


async def test_handle_reorder_queue(setup):
    router, connections, session, store = setup

    ws = make_mock_ws()
    await router.handle(ws, {"type": "join", "name": "Alice"})

    # Queue two songs
    item1 = await session.queue_song(ws.singer_id, _song("v1", "Song A"))
    item2 = await session.queue_song(ws.singer_id, _song("v2", "Song B"))
    ws.send_json.reset_mock()

    await router.handle(
        ws, {"type": "reorder_queue", "item_ids": [item2.id, item1.id]}
    )

    queue = await store.get_queue()
    assert queue[0].id == item2.id
    assert queue[1].id == item1.id


async def test_handle_position_update(setup):
    router, connections, session, store = setup

    ws1 = make_mock_ws()
    await router.handle(ws1, {"type": "join", "name": "Alice"})

    ws2 = make_mock_ws()
    await router.handle(ws2, {"type": "join", "name": "Bob"})

    ws1.send_json.reset_mock()
    ws2.send_json.reset_mock()

    await router.handle(ws1, {"type": "position_update", "position": 55.5})

    # Should relay to other clients (ws2), but not necessarily back to ws1
    sent_ws2 = [call[0][0] for call in ws2.send_json.call_args_list]
    pos_msgs = [m for m in sent_ws2 if m.get("type") == "position_update"]
    assert len(pos_msgs) > 0
    assert pos_msgs[0]["position"] == 55.5

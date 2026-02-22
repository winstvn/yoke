import fakeredis.aioredis
import pytest
from yoke.models import QueueItem, Song
from yoke.redis_store import RedisStore
from yoke.session import SessionManager


@pytest.fixture
async def session():
    redis = fakeredis.aioredis.FakeRedis()
    store = RedisStore(redis)
    mgr = SessionManager(store)
    yield mgr
    await redis.aclose()


def _song(video_id: str = "v1", title: str = "Test Song") -> Song:
    return Song(
        video_id=video_id,
        title=title,
        thumbnail_url="https://example.com/thumb.jpg",
        duration_seconds=180,
    )


async def test_join_first_singer_becomes_host(session: SessionManager):
    result = await session.join("Alice")
    assert result.singer.name == "Alice"
    assert result.singer.connected is True
    assert result.is_new is True
    singer = result.singer

    settings = await session.store.get_settings()
    assert settings.host_id == singer.id


async def test_join_second_singer_not_host(session: SessionManager):
    host = (await session.join("Alice")).singer
    guest = (await session.join("Bob")).singer

    settings = await session.store.get_settings()
    assert settings.host_id == host.id
    assert settings.host_id != guest.id


async def test_queue_song(session: SessionManager):
    singer = (await session.join("Alice")).singer
    song = _song()

    item = await session.queue_song(singer.id, song)
    assert isinstance(item, QueueItem)
    assert item.song.video_id == "v1"
    assert item.singer.id == singer.id

    queue = await session.store.get_queue()
    assert len(queue) == 1
    assert queue[0].id == item.id


async def test_queue_song_unknown_singer(session: SessionManager):
    with pytest.raises(ValueError, match="not found"):
        await session.queue_song("nonexistent", _song())


async def test_remove_own_song(session: SessionManager):
    singer = (await session.join("Alice")).singer
    item = await session.queue_song(singer.id, _song())

    result = await session.remove_from_queue(item.id, singer.id)
    assert result is True

    queue = await session.store.get_queue()
    assert len(queue) == 0


async def test_remove_others_song_as_host(session: SessionManager):
    host = (await session.join("Alice")).singer
    guest = (await session.join("Bob")).singer
    item = await session.queue_song(guest.id, _song())

    result = await session.remove_from_queue(item.id, host.id)
    assert result is True

    queue = await session.store.get_queue()
    assert len(queue) == 0


async def test_remove_others_song_as_non_host_fails(session: SessionManager):
    _host = (await session.join("Alice")).singer
    guest = (await session.join("Bob")).singer
    guest2 = (await session.join("Charlie")).singer
    item = await session.queue_song(guest.id, _song())

    result = await session.remove_from_queue(item.id, guest2.id)
    assert result is False

    queue = await session.store.get_queue()
    assert len(queue) == 1


async def test_reorder_as_host(session: SessionManager):
    host = (await session.join("Alice")).singer
    item1 = await session.queue_song(host.id, _song("v1", "Song A"))
    item2 = await session.queue_song(host.id, _song("v2", "Song B"))

    result = await session.reorder_queue([item2.id, item1.id], host.id)
    assert result is True

    queue = await session.store.get_queue()
    assert queue[0].id == item2.id
    assert queue[1].id == item1.id


async def test_reorder_as_non_host_denied_by_default(session: SessionManager):
    host = (await session.join("Alice")).singer
    guest = (await session.join("Bob")).singer
    item1 = await session.queue_song(host.id, _song("v1", "Song A"))
    item2 = await session.queue_song(host.id, _song("v2", "Song B"))

    result = await session.reorder_queue([item2.id, item1.id], guest.id)
    assert result is False

    # Queue should remain in original order
    queue = await session.store.get_queue()
    assert queue[0].id == item1.id
    assert queue[1].id == item2.id


async def test_reorder_as_non_host_allowed_when_setting_on(session: SessionManager):
    host = (await session.join("Alice")).singer
    guest = (await session.join("Bob")).singer
    item1 = await session.queue_song(host.id, _song("v1", "Song A"))
    item2 = await session.queue_song(host.id, _song("v2", "Song B"))

    # Host enables anyone_can_reorder
    await session.update_setting(host.id, "anyone_can_reorder", True)

    result = await session.reorder_queue([item2.id, item1.id], guest.id)
    assert result is True

    queue = await session.store.get_queue()
    assert queue[0].id == item2.id
    assert queue[1].id == item1.id


async def test_skip_advances_queue(session: SessionManager):
    host = (await session.join("Alice")).singer
    item1 = await session.queue_song(host.id, _song("v1", "Song A"))
    item2 = await session.queue_song(host.id, _song("v2", "Song B"))

    # First advance: pops item1 from queue, sets it as current playing
    current = await session.advance_queue()
    assert current is not None
    assert current.id == item1.id
    assert current.status == "playing"

    playback = await session.store.get_playback()
    assert playback.status == "playing"
    assert playback.position_seconds == 0.0

    # Queue should now only have item2
    queue = await session.store.get_queue()
    assert len(queue) == 1
    assert queue[0].id == item2.id

    # Second advance: pops item2
    current2 = await session.advance_queue()
    assert current2 is not None
    assert current2.id == item2.id
    assert current2.status == "playing"

    # Queue is now empty
    queue = await session.store.get_queue()
    assert len(queue) == 0

    # Third advance: nothing left
    current3 = await session.advance_queue()
    assert current3 is None

    # Current should be cleared
    stored_current = await session.store.get_current()
    assert stored_current is None


async def test_rejoin_with_singer_id_preserves_host(session: SessionManager):
    host = (await session.join("Alice")).singer
    original_id = host.id

    # Simulate disconnect
    await session.disconnect(original_id)
    singer = await session.store.get_singer(original_id)
    assert singer is not None
    assert singer.connected is False

    # Rejoin with the same singer_id
    result = await session.join("Alice", singer_id=original_id)
    assert result.singer.id == original_id
    assert result.singer.connected is True
    assert result.is_new is False

    # Host should still be the same
    settings = await session.store.get_settings()
    assert settings.host_id == original_id


async def test_rejoin_with_invalid_singer_id_creates_new(session: SessionManager):
    result = await session.join("Alice", singer_id="nonexistent-id")
    assert result.singer.id != "nonexistent-id"
    assert result.singer.name == "Alice"
    assert result.is_new is True


async def test_advance_queue_pushes_current_to_history(session: SessionManager):
    host = (await session.join("Alice")).singer
    await session.queue_song(host.id, _song("v1", "Song A"))
    await session.queue_song(host.id, _song("v2", "Song B"))

    # Advance to item1
    await session.advance_queue()

    # Advance to item2 — item1 should be pushed to history
    await session.advance_queue()

    history = await session.store.get_history()
    assert len(history) == 1
    assert history[0].song.video_id == "v1"
    assert history[0].status == "done"


async def test_go_previous_moves_history_to_current(session: SessionManager):
    host = (await session.join("Alice")).singer
    await session.queue_song(host.id, _song("v1", "Song A"))
    await session.queue_song(host.id, _song("v2", "Song B"))

    # Play A then skip to B
    await session.advance_queue()
    await session.advance_queue()

    current = await session.store.get_current()
    assert current is not None
    assert current.song.video_id == "v2"

    # Go previous — should go back to A, B returns to queue front
    result = await session.go_previous()
    assert result is not None
    assert result.song.video_id == "v1"
    assert result.status == "playing"

    current = await session.store.get_current()
    assert current is not None
    assert current.song.video_id == "v1"

    queue = await session.store.get_queue()
    assert len(queue) == 1
    assert queue[0].song.video_id == "v2"
    assert queue[0].status == "ready"


async def test_go_previous_returns_none_when_no_history(session: SessionManager):
    host = (await session.join("Alice")).singer
    await session.queue_song(host.id, _song("v1", "Song A"))

    await session.advance_queue()

    result = await session.go_previous()
    assert result is None

    # Current should be unchanged
    current = await session.store.get_current()
    assert current is not None
    assert current.song.video_id == "v1"


async def test_multiple_previous_preserves_order(session: SessionManager):
    """Skip through A→B→C, then previous back C→B→A."""
    host = (await session.join("Alice")).singer
    await session.queue_song(host.id, _song("v1", "Song A"))
    await session.queue_song(host.id, _song("v2", "Song B"))
    await session.queue_song(host.id, _song("v3", "Song C"))

    # Advance through all three
    await session.advance_queue()  # now playing A
    await session.advance_queue()  # now playing B
    await session.advance_queue()  # now playing C

    current = await session.store.get_current()
    assert current is not None
    assert current.song.video_id == "v3"

    # Previous: C→B
    result = await session.go_previous()
    assert result is not None
    assert result.song.video_id == "v2"

    # Previous: B→A
    result = await session.go_previous()
    assert result is not None
    assert result.song.video_id == "v1"

    # No more history
    result = await session.go_previous()
    assert result is None


async def test_skip_after_previous(session: SessionManager):
    """Skip A→B→C, previous back to B, skip forward → plays C again."""
    host = (await session.join("Alice")).singer
    await session.queue_song(host.id, _song("v1", "Song A"))
    await session.queue_song(host.id, _song("v2", "Song B"))
    await session.queue_song(host.id, _song("v3", "Song C"))

    await session.advance_queue()  # A
    await session.advance_queue()  # B
    await session.advance_queue()  # C

    # Go back to B (C goes to front of queue)
    result = await session.go_previous()
    assert result is not None
    assert result.song.video_id == "v2"

    queue = await session.store.get_queue()
    assert queue[0].song.video_id == "v3"

    # Skip forward — should play C again
    current = await session.advance_queue()
    assert current is not None
    assert current.song.video_id == "v3"


async def test_queue_after_previous(session: SessionManager):
    """Skip A→B, previous back to A (B to queue front), queue D, skip → B, then D."""
    host = (await session.join("Alice")).singer
    await session.queue_song(host.id, _song("v1", "Song A"))
    await session.queue_song(host.id, _song("v2", "Song B"))

    await session.advance_queue()  # A
    await session.advance_queue()  # B

    # Go back to A — B returns to queue front
    result = await session.go_previous()
    assert result is not None
    assert result.song.video_id == "v1"

    # Queue a new song D
    await session.queue_song(host.id, _song("v4", "Song D"))

    # Queue should be: B (front), D
    queue = await session.store.get_queue()
    assert len(queue) == 2
    assert queue[0].song.video_id == "v2"
    assert queue[1].song.video_id == "v4"

    # Skip forward → plays B (not D)
    current = await session.advance_queue()
    assert current is not None
    assert current.song.video_id == "v2"

    # Skip again → plays D
    current = await session.advance_queue()
    assert current is not None
    assert current.song.video_id == "v4"


async def test_can_control_playback_host_always_allowed(session: SessionManager):
    host = (await session.join("Alice")).singer
    guest = (await session.join("Bob")).singer
    # Queue a song as guest and set it as current
    await session.queue_song(guest.id, _song())
    await session.advance_queue()

    # Host can control even though it's guest's song
    assert await session.can_control_playback(host.id) is True


async def test_can_control_playback_current_singer_allowed(session: SessionManager):
    await session.join("Alice")

    guest = (await session.join("Bob")).singer
    await session.queue_song(guest.id, _song())
    await session.advance_queue()

    assert await session.can_control_playback(guest.id) is True


async def test_can_control_playback_other_singer_denied(session: SessionManager):
    await session.join("Alice")

    guest = (await session.join("Bob")).singer
    other = (await session.join("Charlie")).singer
    await session.queue_song(guest.id, _song())
    await session.advance_queue()

    assert await session.can_control_playback(other.id) is False


async def test_can_control_playback_no_current_song(session: SessionManager):
    host = (await session.join("Alice")).singer
    guest = (await session.join("Bob")).singer

    # No current song — host allowed, guest denied
    assert await session.can_control_playback(host.id) is True
    assert await session.can_control_playback(guest.id) is False


async def test_update_setting_host_only(session: SessionManager):
    host = (await session.join("Alice")).singer
    guest = (await session.join("Bob")).singer

    # Host can change settings
    result = await session.update_setting(host.id, "anyone_can_reorder", True)
    assert result is True
    settings = await session.store.get_settings()
    assert settings.anyone_can_reorder is True

    # Non-host cannot change settings
    result = await session.update_setting(guest.id, "anyone_can_reorder", False)
    assert result is False
    settings = await session.store.get_settings()
    assert settings.anyone_can_reorder is True  # unchanged

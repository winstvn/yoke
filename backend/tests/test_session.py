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
    singer = await session.join("Alice")
    assert singer.name == "Alice"
    assert singer.connected is True

    settings = await session.store.get_settings()
    assert settings.host_id == singer.id


async def test_join_second_singer_not_host(session: SessionManager):
    host = await session.join("Alice")
    guest = await session.join("Bob")

    settings = await session.store.get_settings()
    assert settings.host_id == host.id
    assert settings.host_id != guest.id


async def test_queue_song(session: SessionManager):
    singer = await session.join("Alice")
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
    singer = await session.join("Alice")
    item = await session.queue_song(singer.id, _song())

    result = await session.remove_from_queue(item.id, singer.id)
    assert result is True

    queue = await session.store.get_queue()
    assert len(queue) == 0


async def test_remove_others_song_as_host(session: SessionManager):
    host = await session.join("Alice")
    guest = await session.join("Bob")
    item = await session.queue_song(guest.id, _song())

    result = await session.remove_from_queue(item.id, host.id)
    assert result is True

    queue = await session.store.get_queue()
    assert len(queue) == 0


async def test_remove_others_song_as_non_host_fails(session: SessionManager):
    _host = await session.join("Alice")
    guest = await session.join("Bob")
    guest2 = await session.join("Charlie")
    item = await session.queue_song(guest.id, _song())

    result = await session.remove_from_queue(item.id, guest2.id)
    assert result is False

    queue = await session.store.get_queue()
    assert len(queue) == 1


async def test_reorder_as_host(session: SessionManager):
    host = await session.join("Alice")
    item1 = await session.queue_song(host.id, _song("v1", "Song A"))
    item2 = await session.queue_song(host.id, _song("v2", "Song B"))

    result = await session.reorder_queue([item2.id, item1.id], host.id)
    assert result is True

    queue = await session.store.get_queue()
    assert queue[0].id == item2.id
    assert queue[1].id == item1.id


async def test_reorder_as_non_host_denied_by_default(session: SessionManager):
    host = await session.join("Alice")
    guest = await session.join("Bob")
    item1 = await session.queue_song(host.id, _song("v1", "Song A"))
    item2 = await session.queue_song(host.id, _song("v2", "Song B"))

    result = await session.reorder_queue([item2.id, item1.id], guest.id)
    assert result is False

    # Queue should remain in original order
    queue = await session.store.get_queue()
    assert queue[0].id == item1.id
    assert queue[1].id == item2.id


async def test_reorder_as_non_host_allowed_when_setting_on(session: SessionManager):
    host = await session.join("Alice")
    guest = await session.join("Bob")
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
    host = await session.join("Alice")
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
    host = await session.join("Alice")
    original_id = host.id

    # Simulate disconnect
    await session.disconnect(original_id)
    singer = await session.store.get_singer(original_id)
    assert singer is not None
    assert singer.connected is False

    # Rejoin with the same singer_id
    reclaimed = await session.join("Alice", singer_id=original_id)
    assert reclaimed.id == original_id
    assert reclaimed.connected is True

    # Host should still be the same
    settings = await session.store.get_settings()
    assert settings.host_id == original_id


async def test_rejoin_with_invalid_singer_id_creates_new(session: SessionManager):
    singer = await session.join("Alice", singer_id="nonexistent-id")
    assert singer.id != "nonexistent-id"
    assert singer.name == "Alice"


async def test_update_setting_host_only(session: SessionManager):
    host = await session.join("Alice")
    guest = await session.join("Bob")

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

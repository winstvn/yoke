import fakeredis.aioredis
import pytest

from yoke.models import (
    PlaybackState,
    QueueItem,
    SessionSettings,
    Singer,
    Song,
    SessionState,
)
from yoke.redis_store import RedisStore


@pytest.fixture
async def store():
    redis = fakeredis.aioredis.FakeRedis()
    s = RedisStore(redis)
    yield s
    await redis.aclose()


async def test_save_and_get_singer(store: RedisStore):
    singer = Singer(name="Alice")
    await store.save_singer(singer)
    result = await store.get_singer(singer.id)
    assert result is not None
    assert result.name == "Alice"


async def test_get_nonexistent_singer(store: RedisStore):
    result = await store.get_singer("nonexistent")
    assert result is None


async def test_get_all_singers(store: RedisStore):
    await store.save_singer(Singer(name="Alice"))
    await store.save_singer(Singer(name="Bob"))
    singers = await store.get_all_singers()
    assert len(singers) == 2


async def test_remove_singer(store: RedisStore):
    singer = Singer(name="Alice")
    await store.save_singer(singer)
    await store.remove_singer(singer.id)
    assert await store.get_singer(singer.id) is None


async def test_save_and_get_song(store: RedisStore):
    song = Song(
        video_id="abc123",
        title="Test Song",
        thumbnail_url="https://example.com/thumb.jpg",
        duration_seconds=180,
        cached=True,
    )
    await store.save_song(song)
    result = await store.get_song("abc123")
    assert result is not None
    assert result.cached is True


async def test_queue_operations(store: RedisStore):
    singer = Singer(name="Alice")
    song = Song(
        video_id="abc123",
        title="Test Song",
        thumbnail_url="https://example.com/thumb.jpg",
        duration_seconds=180,
    )
    item = QueueItem(song=song, singer=singer)

    await store.append_to_queue(item)
    queue = await store.get_queue()
    assert len(queue) == 1
    assert queue[0].id == item.id

    await store.remove_from_queue(item.id)
    queue = await store.get_queue()
    assert len(queue) == 0


async def test_reorder_queue(store: RedisStore):
    singer = Singer(name="Alice")
    song1 = Song(video_id="a", title="A", thumbnail_url="", duration_seconds=60)
    song2 = Song(video_id="b", title="B", thumbnail_url="", duration_seconds=60)
    item1 = QueueItem(song=song1, singer=singer)
    item2 = QueueItem(song=song2, singer=singer)

    await store.append_to_queue(item1)
    await store.append_to_queue(item2)
    await store.reorder_queue([item2.id, item1.id])

    queue = await store.get_queue()
    assert queue[0].id == item2.id
    assert queue[1].id == item1.id


async def test_playback_state(store: RedisStore):
    state = PlaybackState(status="playing", position_seconds=42.5, pitch_shift=2)
    await store.save_playback(state)
    result = await store.get_playback()
    assert result.status == "playing"
    assert result.pitch_shift == 2


async def test_settings(store: RedisStore):
    settings = SessionSettings(host_id="singer-1", anyone_can_reorder=True)
    await store.save_settings(settings)
    result = await store.get_settings()
    assert result.host_id == "singer-1"
    assert result.anyone_can_reorder is True


async def test_current_item(store: RedisStore):
    singer = Singer(name="Alice")
    song = Song(video_id="abc", title="T", thumbnail_url="", duration_seconds=60)
    item = QueueItem(song=song, singer=singer)

    await store.save_current(item)
    result = await store.get_current()
    assert result is not None
    assert result.id == item.id

    await store.clear_current()
    assert await store.get_current() is None


async def test_get_full_state(store: RedisStore):
    singer = Singer(name="Alice")
    await store.save_singer(singer)
    settings = SessionSettings(host_id=singer.id)
    await store.save_settings(settings)

    state = await store.get_full_state()
    assert isinstance(state, SessionState)
    assert len(state.singers) == 1
    assert state.settings.host_id == singer.id

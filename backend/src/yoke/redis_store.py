from __future__ import annotations

from typing import TYPE_CHECKING

from yoke.models import (
    PlaybackState,
    QueueItem,
    SessionSettings,
    SessionState,
    Singer,
    Song,
)

if TYPE_CHECKING:
    from redis.asyncio import Redis

PREFIX = "yoke"


class RedisStore:
    def __init__(self, redis: Redis) -> None:  # type: ignore[type-arg]
        self._r = redis

    # --- Singers ---

    async def save_singer(self, singer: Singer) -> None:
        await self._r.hset(f"{PREFIX}:singers", singer.id, singer.model_dump_json())

    async def get_singer(self, singer_id: str) -> Singer | None:
        data = await self._r.hget(f"{PREFIX}:singers", singer_id)
        if data is None:
            return None
        return Singer.model_validate_json(data)

    async def get_all_singers(self) -> list[Singer]:
        data = await self._r.hgetall(f"{PREFIX}:singers")
        return [Singer.model_validate_json(v) for v in data.values()]

    async def remove_singer(self, singer_id: str) -> None:
        await self._r.hdel(f"{PREFIX}:singers", singer_id)

    # --- Songs (cache registry) ---

    async def save_song(self, song: Song) -> None:
        await self._r.set(f"{PREFIX}:songs:{song.video_id}", song.model_dump_json())

    async def get_song(self, video_id: str) -> Song | None:
        data = await self._r.get(f"{PREFIX}:songs:{video_id}")
        if data is None:
            return None
        return Song.model_validate_json(data)

    # --- Queue ---

    async def get_queue(self) -> list[QueueItem]:
        data = await self._r.lrange(f"{PREFIX}:queue", 0, -1)
        return [QueueItem.model_validate_json(item) for item in data]

    async def append_to_queue(self, item: QueueItem) -> None:
        await self._r.rpush(f"{PREFIX}:queue", item.model_dump_json())

    async def remove_from_queue(self, item_id: str) -> None:
        queue = await self.get_queue()
        await self._r.delete(f"{PREFIX}:queue")
        for item in queue:
            if item.id != item_id:
                await self._r.rpush(f"{PREFIX}:queue", item.model_dump_json())

    async def reorder_queue(self, item_ids: list[str]) -> None:
        queue = await self.get_queue()
        by_id = {item.id: item for item in queue}
        await self._r.delete(f"{PREFIX}:queue")
        for item_id in item_ids:
            if item_id in by_id:
                await self._r.rpush(f"{PREFIX}:queue", by_id[item_id].model_dump_json())

    async def update_queue_item(self, item_id: str, **fields: object) -> None:
        queue = await self.get_queue()
        await self._r.delete(f"{PREFIX}:queue")
        for item in queue:
            if item.id == item_id:
                for k, v in fields.items():
                    setattr(item, k, v)
            await self._r.rpush(f"{PREFIX}:queue", item.model_dump_json())

    # --- History ---

    async def get_history(self) -> list[QueueItem]:
        data = await self._r.lrange(f"{PREFIX}:history", 0, -1)
        return [QueueItem.model_validate_json(item) for item in data]

    async def prepend_to_history(self, item: QueueItem) -> None:
        await self._r.lpush(f"{PREFIX}:history", item.model_dump_json())

    async def pop_from_history(self) -> QueueItem | None:
        data = await self._r.lpop(f"{PREFIX}:history")
        if data is None:
            return None
        return QueueItem.model_validate_json(data)

    # --- Queue (prepend) ---

    async def prepend_to_queue(self, item: QueueItem) -> None:
        await self._r.lpush(f"{PREFIX}:queue", item.model_dump_json())

    # --- Current item ---

    async def save_current(self, item: QueueItem) -> None:
        await self._r.set(f"{PREFIX}:current", item.model_dump_json())

    async def get_current(self) -> QueueItem | None:
        data = await self._r.get(f"{PREFIX}:current")
        if data is None:
            return None
        return QueueItem.model_validate_json(data)

    async def clear_current(self) -> None:
        await self._r.delete(f"{PREFIX}:current")

    # --- Playback ---

    async def save_playback(self, state: PlaybackState) -> None:
        await self._r.set(f"{PREFIX}:playback", state.model_dump_json())

    async def get_playback(self) -> PlaybackState:
        data = await self._r.get(f"{PREFIX}:playback")
        if data is None:
            return PlaybackState()
        return PlaybackState.model_validate_json(data)

    # --- Settings ---

    async def save_settings(self, settings: SessionSettings) -> None:
        await self._r.set(f"{PREFIX}:settings", settings.model_dump_json())

    async def get_settings(self) -> SessionSettings:
        data = await self._r.get(f"{PREFIX}:settings")
        if data is None:
            return SessionSettings()
        return SessionSettings.model_validate_json(data)

    # --- Full state ---

    async def get_full_state(self) -> SessionState:
        singers = await self.get_all_singers()
        queue = await self.get_queue()
        current = await self.get_current()
        playback = await self.get_playback()
        settings = await self.get_settings()
        return SessionState(
            singers=singers,
            queue=queue,
            current=current,
            playback=playback,
            settings=settings,
        )

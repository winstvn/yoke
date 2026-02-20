from __future__ import annotations

from yoke.models import PlaybackState, QueueItem, Singer, Song
from yoke.redis_store import RedisStore


class SessionManager:
    def __init__(self, store: RedisStore) -> None:
        self.store = store

    async def join(self, name: str, singer_id: str | None = None) -> Singer:
        """Create or reclaim a singer and save to store.

        If *singer_id* is provided and matches an existing singer, reclaim
        that identity (mark connected, update name).  Otherwise create a
        new singer.

        If this is the first singer (host_id is None), set them as host.
        """
        if singer_id:
            existing = await self.store.get_singer(singer_id)
            if existing is not None:
                existing.connected = True
                existing.name = name
                await self.store.save_singer(existing)
                return existing

        singer = Singer(name=name)
        await self.store.save_singer(singer)

        settings = await self.store.get_settings()
        if settings.host_id is None:
            settings.host_id = singer.id
            await self.store.save_settings(settings)

        return singer

    async def disconnect(self, singer_id: str) -> None:
        """Mark a singer as disconnected."""
        singer = await self.store.get_singer(singer_id)
        if singer is not None:
            singer.connected = False
            await self.store.save_singer(singer)

    async def queue_song(self, singer_id: str, song: Song) -> QueueItem:
        """Look up singer, create a QueueItem, and append to queue.

        Raises ValueError if the singer is not found.
        """
        singer = await self.store.get_singer(singer_id)
        if singer is None:
            raise ValueError(f"Singer {singer_id!r} not found")

        item = QueueItem(song=song, singer=singer)
        await self.store.append_to_queue(item)
        return item

    async def remove_from_queue(self, item_id: str, requester_id: str) -> bool:
        """Remove a queue item.

        Host can remove anyone's item. Non-hosts can only remove their own.
        Returns True if removed, False if denied.
        """
        settings = await self.store.get_settings()
        is_host = requester_id == settings.host_id

        if is_host:
            await self.store.remove_from_queue(item_id)
            return True

        # Non-host: check if the item belongs to the requester
        queue = await self.store.get_queue()
        for item in queue:
            if item.id == item_id:
                if item.singer.id == requester_id:
                    await self.store.remove_from_queue(item_id)
                    return True
                return False

        # Item not found — nothing to remove
        return False

    async def reorder_queue(self, item_ids: list[str], requester_id: str) -> bool:
        """Reorder the queue.

        Host can always reorder. Non-hosts can only reorder if
        settings.anyone_can_reorder is True. Returns True if reordered,
        False if denied.
        """
        settings = await self.store.get_settings()
        is_host = requester_id == settings.host_id

        if not is_host and not settings.anyone_can_reorder:
            return False

        await self.store.reorder_queue(item_ids)
        return True

    async def advance_queue(self) -> QueueItem | None:
        """Pop the first item from the queue and set it as current.

        Pushes the outgoing current item onto history before replacing it.
        Resets playback to PlaybackState(status="playing"). Returns the item,
        or None if the queue is empty (also clears current in that case).
        """
        # Save outgoing current to history
        old_current = await self.store.get_current()
        if old_current is not None:
            old_current.status = "done"
            await self.store.prepend_to_history(old_current)

        queue = await self.store.get_queue()
        if not queue:
            await self.store.clear_current()
            return None

        item = queue[0]
        await self.store.remove_from_queue(item.id)

        item.status = "playing"
        await self.store.save_current(item)
        await self.store.save_playback(PlaybackState(status="playing"))

        return item

    async def go_previous(self) -> QueueItem | None:
        """Go back to the previous song from history.

        Pops the most recent item from history, pushes the current item
        back to the front of the queue, and sets the history item as current.
        Returns the history item, or None if history is empty.
        """
        prev = await self.store.pop_from_history()
        if prev is None:
            return None

        # Push current back to front of queue
        current = await self.store.get_current()
        if current is not None:
            current.status = "ready"
            await self.store.prepend_to_queue(current)

        # Set history item as current
        prev.status = "playing"
        await self.store.save_current(prev)
        await self.store.save_playback(PlaybackState(status="playing"))

        return prev

    async def update_setting(
        self, requester_id: str, key: str, value: object
    ) -> bool:
        """Update a session setting. Only the host can change settings.

        Returns True if changed, False if denied.
        """
        settings = await self.store.get_settings()
        if requester_id != settings.host_id:
            return False

        setattr(settings, key, value)
        await self.store.save_settings(settings)
        return True

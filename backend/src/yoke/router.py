from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from yoke.models import PlaybackState, Song
from yoke.youtube import search_youtube

if TYPE_CHECKING:
    from fastapi import WebSocket

    from yoke.downloader import VideoDownloader
    from yoke.session import SessionManager
    from yoke.ws import ConnectionManager

logger = logging.getLogger(__name__)


class MessageRouter:
    """Routes incoming WebSocket messages to the appropriate handler."""

    def __init__(
        self,
        session: SessionManager,
        connections: ConnectionManager,
        downloader: VideoDownloader,
    ) -> None:
        self.session = session
        self.connections = connections
        self.downloader = downloader

    async def handle(self, ws: WebSocket, message: dict[str, Any]) -> None:
        """Dispatch a message to the handler matching message['type']."""
        msg_type = message.get("type", "")
        handler_name = f"_handle_{msg_type}"
        handler = getattr(self, handler_name, None)
        if handler is None:
            await self.connections.send_to(
                ws, {"type": "error", "message": f"Unknown message type: {msg_type}"}
            )
            return
        try:
            await handler(ws, message)
        except Exception:
            logger.exception("Error handling message type %s", msg_type)
            await self.connections.send_to(
                ws, {"type": "error", "message": f"Error handling {msg_type}"}
            )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    async def _handle_join(
        self, ws: WebSocket, message: dict[str, Any]
    ) -> None:
        name = message.get("name", "Anonymous")
        singer = await self.session.join(name)

        # Associate this websocket with the singer
        ws.singer_id = singer.id  # type: ignore[attr-defined]
        self.connections.connect(ws, singer.id)

        # Send the full state to the new client, including their own singer ID
        state = await self.session.store.get_full_state()
        await self.connections.send_to(ws, {
            "type": "state",
            "singer_id": singer.id,
            "singers": [s.model_dump() for s in state.singers],
            "queue": [item.model_dump() for item in state.queue],
            "current": state.current.model_dump() if state.current else None,
            "playback": state.playback.model_dump(),
            "settings": state.settings.model_dump(),
        })

        # Broadcast to others that a new singer joined
        await self.connections.broadcast(
            {
                "type": "singer_joined",
                "singer": singer.model_dump(),
            },
            exclude=ws,
        )

    async def _handle_search(
        self, ws: WebSocket, message: dict[str, Any]
    ) -> None:
        query = message.get("query", "")
        if not query:
            await self.connections.send_to(
                ws, {"type": "error", "message": "Search query is required"}
            )
            return

        results = await search_youtube(query)
        songs = []
        for r in results:
            cached = self.downloader.is_cached(r.video_id)
            song = Song(
                video_id=r.video_id,
                title=r.title,
                thumbnail_url=r.thumbnail_url,
                duration_seconds=r.duration_seconds,
                cached=cached,
            )
            await self.session.store.save_song(song)
            songs.append(song.model_dump())

        await self.connections.send_to(ws, {
            "type": "search_results",
            "songs": songs,
        })

    async def _handle_queue_song(
        self, ws: WebSocket, message: dict[str, Any]
    ) -> None:
        singer_id = getattr(ws, "singer_id", None)
        if singer_id is None:
            await self.connections.send_to(
                ws, {"type": "error", "message": "Not joined"}
            )
            return

        video_id = message.get("video_id", "")

        # Try to get from store first, or build from message
        song = await self.session.store.get_song(video_id)
        if song is None:
            song = Song(
                video_id=video_id,
                title=message.get("title", ""),
                thumbnail_url=message.get("thumbnail_url", ""),
                duration_seconds=message.get("duration_seconds", 0),
                cached=self.downloader.is_cached(video_id),
            )

        item = await self.session.queue_song(singer_id, song)

        # Mark as ready immediately if already cached
        if self.downloader.is_cached(video_id):
            await self.session.store.update_queue_item(item.id, status="ready")

        # Broadcast queue update
        queue = await self.session.store.get_queue()
        await self.connections.broadcast({
            "type": "queue_updated",
            "queue": [qi.model_dump() for qi in queue],
        })
        await self.connections.broadcast({
            "type": "song_queued",
            "item": item.model_dump(),
        })

        # Start download if not cached
        if not self.downloader.is_cached(video_id):
            asyncio.create_task(self._download_video(item.id, video_id))
        else:
            await self._auto_advance()

    async def _handle_remove_from_queue(
        self, ws: WebSocket, message: dict[str, Any]
    ) -> None:
        singer_id = getattr(ws, "singer_id", None)
        if singer_id is None:
            await self.connections.send_to(
                ws, {"type": "error", "message": "Not joined"}
            )
            return

        item_id = message.get("item_id", "")
        success = await self.session.remove_from_queue(item_id, singer_id)
        if success:
            queue = await self.session.store.get_queue()
            await self.connections.broadcast({
                "type": "queue_updated",
                "queue": [qi.model_dump() for qi in queue],
            })
        else:
            await self.connections.send_to(
                ws, {"type": "error", "message": "Cannot remove that item"}
            )

    async def _handle_reorder_queue(
        self, ws: WebSocket, message: dict[str, Any]
    ) -> None:
        singer_id = getattr(ws, "singer_id", None)
        if singer_id is None:
            await self.connections.send_to(
                ws, {"type": "error", "message": "Not joined"}
            )
            return

        item_ids = message.get("item_ids", [])
        success = await self.session.reorder_queue(item_ids, singer_id)
        if success:
            queue = await self.session.store.get_queue()
            await self.connections.broadcast({
                "type": "queue_updated",
                "queue": [qi.model_dump() for qi in queue],
            })
        else:
            await self.connections.send_to(
                ws, {"type": "error", "message": "Cannot reorder queue"}
            )

    async def _handle_playback(
        self, ws: WebSocket, message: dict[str, Any]
    ) -> None:
        action = message.get("action", "")
        playback = await self.session.store.get_playback()

        if action == "play":
            playback.status = "playing"
        elif action == "pause":
            playback.status = "paused"
        elif action == "stop":
            playback.status = "stopped"
        elif action == "restart":
            playback.status = "playing"
            playback.position_seconds = 0.0
        elif action == "skip":
            current = await self.session.advance_queue()
            queue = await self.session.store.get_queue()
            playback = await self.session.store.get_playback()

            await self.connections.broadcast({
                "type": "now_playing",
                "item": current.model_dump() if current else None,
            })
            await self.connections.broadcast({
                "type": "queue_updated",
                "queue": [qi.model_dump() for qi in queue],
            })
            await self.connections.broadcast({
                "type": "playback_updated",
                "playback": playback.model_dump(),
            })
            return
        else:
            await self.connections.send_to(
                ws, {"type": "error", "message": f"Unknown playback action: {action}"}
            )
            return

        await self.session.store.save_playback(playback)
        await self.connections.broadcast({
            "type": "playback_updated",
            "playback": playback.model_dump(),
        })

    async def _handle_seek(
        self, ws: WebSocket, message: dict[str, Any]
    ) -> None:
        position = message.get("position_seconds", message.get("position", 0.0))
        playback = await self.session.store.get_playback()
        playback.position_seconds = float(position)
        await self.session.store.save_playback(playback)

        await self.connections.broadcast({
            "type": "playback_updated",
            "playback": playback.model_dump(),
        })

    async def _handle_pitch(
        self, ws: WebSocket, message: dict[str, Any]
    ) -> None:
        value = message.get("value", 0)
        # Clamp to -6..+6
        value = max(-6, min(6, int(value)))

        playback = await self.session.store.get_playback()
        playback.pitch_shift = value
        await self.session.store.save_playback(playback)

        await self.connections.broadcast({
            "type": "playback_updated",
            "playback": playback.model_dump(),
        })

    async def _handle_position_update(
        self, ws: WebSocket, message: dict[str, Any]
    ) -> None:
        position = message.get("position_seconds", message.get("position", 0.0))

        # Persist so other actions (pause, etc.) reflect the real position
        playback = await self.session.store.get_playback()
        playback.position_seconds = float(position)
        await self.session.store.save_playback(playback)

        # Relay to other clients (from display page to control pages)
        await self.connections.broadcast(
            {
                "type": "position_update",
                "position": position,
            },
            exclude=ws,
        )

    async def _handle_update_setting(
        self, ws: WebSocket, message: dict[str, Any]
    ) -> None:
        singer_id = getattr(ws, "singer_id", None)
        if singer_id is None:
            await self.connections.send_to(
                ws, {"type": "error", "message": "Not joined"}
            )
            return

        key = message.get("key", "")
        value = message.get("value")

        success = await self.session.update_setting(singer_id, key, value)
        if not success:
            await self.connections.send_to(
                ws, {"type": "error", "message": "Only the host can change settings"}
            )
            return

        settings = await self.session.store.get_settings()
        await self.connections.broadcast({
            "type": "settings_updated",
            "settings": settings.model_dump(),
        })

    async def _handle_show_qr(
        self, ws: WebSocket, message: dict[str, Any]
    ) -> None:
        await self.connections.broadcast({"type": "show_qr"})

    async def _handle_screen_message(
        self, ws: WebSocket, message: dict[str, Any]
    ) -> None:
        singer_id = getattr(ws, "singer_id", None)
        text = message.get("text", "")

        name = "Anonymous"
        if singer_id:
            singer = await self.session.store.get_singer(singer_id)
            if singer:
                name = singer.name

        await self.connections.broadcast({
            "type": "screen_message",
            "name": name,
            "text": text,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _auto_advance(self) -> None:
        """If nothing is currently playing, advance the queue."""
        current = await self.session.store.get_current()
        if current is not None:
            return

        item = await self.session.advance_queue()
        queue = await self.session.store.get_queue()
        playback = await self.session.store.get_playback()

        await self.connections.broadcast({
            "type": "now_playing",
            "item": item.model_dump() if item else None,
        })
        await self.connections.broadcast({
            "type": "queue_updated",
            "queue": [qi.model_dump() for qi in queue],
        })
        await self.connections.broadcast({
            "type": "playback_updated",
            "playback": playback.model_dump(),
        })

    async def _download_video(self, item_id: str, video_id: str) -> None:
        """Download a video, updating queue item status and broadcasting progress."""
        try:
            # Update status to downloading
            await self.session.store.update_queue_item(item_id, status="downloading")
            queue = await self.session.store.get_queue()
            await self.connections.broadcast({
                "type": "queue_updated",
                "queue": [qi.model_dump() for qi in queue],
            })

            loop = asyncio.get_running_loop()

            def on_progress(pct: float) -> None:
                loop.call_soon_threadsafe(
                    asyncio.ensure_future,
                    self.connections.broadcast({
                        "type": "download_progress",
                        "item_id": item_id,
                        "video_id": video_id,
                        "progress": pct,
                    }),
                )

            await self.downloader.download(video_id, on_progress=on_progress)

            # Update status to ready
            await self.session.store.update_queue_item(item_id, status="ready")
            queue = await self.session.store.get_queue()
            await self.connections.broadcast({
                "type": "queue_updated",
                "queue": [qi.model_dump() for qi in queue],
            })

            # Save song as cached
            song = await self.session.store.get_song(video_id)
            if song:
                song.cached = True
                await self.session.store.save_song(song)

            await self._auto_advance()

        except Exception:
            logger.exception("Failed to download video %s", video_id)
            await self.connections.broadcast({
                "type": "download_error",
                "item_id": item_id,
                "video_id": video_id,
            })

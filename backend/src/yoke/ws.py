from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections for the karaoke session."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    def connect(self, ws: WebSocket, singer_id: str) -> None:
        """Register a WebSocket connection and associate it with a singer ID."""
        ws.singer_id = singer_id  # type: ignore[attr-defined]
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket connection if present."""
        try:
            self.active_connections.remove(ws)
        except ValueError:
            pass

    def get_by_singer_id(self, singer_id: str) -> WebSocket | None:
        """Find a connection by its associated singer ID."""
        for ws in self.active_connections:
            if getattr(ws, "singer_id", None) == singer_id:
                return ws
        return None

    async def send_to(self, ws: WebSocket, message: dict[str, Any]) -> None:
        """Send a JSON message to a single client, catching exceptions."""
        try:
            await ws.send_json(message)
        except Exception:
            logger.exception("Failed to send message to %s", getattr(ws, "singer_id", "unknown"))

    async def broadcast(self, message: dict[str, Any], exclude: WebSocket | None = None) -> None:
        """Send a JSON message to all connected clients, optionally excluding one."""
        for ws in self.active_connections:
            if ws is exclude:
                continue
            await self.send_to(ws, message)

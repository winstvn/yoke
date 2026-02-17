from __future__ import annotations

from unittest.mock import AsyncMock


from yoke.ws import ConnectionManager


def make_mock_ws(singer_id: str | None = None) -> AsyncMock:
    ws = AsyncMock()
    ws.singer_id = singer_id
    return ws


class TestConnectionManager:
    def test_connect_and_disconnect(self) -> None:
        mgr = ConnectionManager()
        ws = make_mock_ws("singer-1")

        mgr.connect(ws, "singer-1")
        assert ws in mgr.active_connections
        assert len(mgr.active_connections) == 1

        mgr.disconnect(ws)
        assert ws not in mgr.active_connections
        assert len(mgr.active_connections) == 0

    def test_disconnect_not_connected(self) -> None:
        mgr = ConnectionManager()
        ws = make_mock_ws("singer-1")

        # Should not raise even if ws was never connected
        mgr.disconnect(ws)
        assert len(mgr.active_connections) == 0

    async def test_broadcast(self) -> None:
        mgr = ConnectionManager()
        ws1 = make_mock_ws("singer-1")
        ws2 = make_mock_ws("singer-2")
        mgr.connect(ws1, "singer-1")
        mgr.connect(ws2, "singer-2")

        message = {"type": "queue_update", "data": []}
        await mgr.broadcast(message)

        ws1.send_json.assert_awaited_once_with(message)
        ws2.send_json.assert_awaited_once_with(message)

    async def test_send_to_one(self) -> None:
        mgr = ConnectionManager()
        ws1 = make_mock_ws("singer-1")
        ws2 = make_mock_ws("singer-2")
        mgr.connect(ws1, "singer-1")
        mgr.connect(ws2, "singer-2")

        message = {"type": "now_playing", "song": "test"}
        await mgr.send_to(ws1, message)

        ws1.send_json.assert_awaited_once_with(message)
        ws2.send_json.assert_not_awaited()

    async def test_broadcast_excludes(self) -> None:
        mgr = ConnectionManager()
        ws1 = make_mock_ws("singer-1")
        ws2 = make_mock_ws("singer-2")
        ws3 = make_mock_ws("singer-3")
        mgr.connect(ws1, "singer-1")
        mgr.connect(ws2, "singer-2")
        mgr.connect(ws3, "singer-3")

        message = {"type": "singer_joined", "singer_id": "singer-2"}
        await mgr.broadcast(message, exclude=ws2)

        ws1.send_json.assert_awaited_once_with(message)
        ws2.send_json.assert_not_awaited()
        ws3.send_json.assert_awaited_once_with(message)

    def test_get_connection_by_singer_id(self) -> None:
        mgr = ConnectionManager()
        ws1 = make_mock_ws("singer-1")
        ws2 = make_mock_ws("singer-2")
        mgr.connect(ws1, "singer-1")
        mgr.connect(ws2, "singer-2")

        assert mgr.get_by_singer_id("singer-1") is ws1
        assert mgr.get_by_singer_id("singer-2") is ws2
        assert mgr.get_by_singer_id("singer-999") is None

    async def test_send_to_handles_exception(self) -> None:
        mgr = ConnectionManager()
        ws = make_mock_ws("singer-1")
        ws.send_json.side_effect = Exception("connection closed")
        mgr.connect(ws, "singer-1")

        # Should not raise
        await mgr.send_to(ws, {"type": "test"})

    async def test_broadcast_handles_exception(self) -> None:
        mgr = ConnectionManager()
        ws1 = make_mock_ws("singer-1")
        ws2 = make_mock_ws("singer-2")
        ws1.send_json.side_effect = Exception("connection closed")
        mgr.connect(ws1, "singer-1")
        mgr.connect(ws2, "singer-2")

        # Should not raise, and ws2 should still receive the message
        await mgr.broadcast({"type": "test"})
        ws2.send_json.assert_awaited_once_with({"type": "test"})

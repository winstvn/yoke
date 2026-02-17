from __future__ import annotations

import os
import socket
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

from yoke.config import config
from yoke.downloader import VideoDownloader
from yoke.redis_store import RedisStore
from yoke.router import MessageRouter
from yoke.session import SessionManager
from yoke.ws import ConnectionManager


def _get_local_ip() -> str:
    """Return the LAN IP address of the host machine."""
    # Explicit override (works everywhere)
    env_ip = os.environ.get("KARAOKE_EXTERNAL_IP")
    if env_ip:
        return env_ip

    # Docker Desktop (macOS/Windows) maps this to the host
    try:
        ip = socket.gethostbyname("host.docker.internal")
        if not ip.startswith("127."):
            return ip
    except socket.gaierror:
        pass

    # Bare-metal / Linux fallback
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


connections = ConnectionManager()
router: MessageRouter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    global router
    redis = aioredis.from_url(config.redis_url)
    store = RedisStore(redis)
    session = SessionManager(store)
    downloader = VideoDownloader(
        video_dir=config.video_dir,
        max_concurrent=config.max_concurrent_downloads,
    )
    downloader.ensure_dir()
    router = MessageRouter(
        session=session, connections=connections, downloader=downloader
    )
    app.state.store = store
    app.state.downloader = downloader
    yield
    await redis.aclose()


app = FastAPI(title="Yoke", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/server-info")
async def server_info() -> dict[str, str]:
    return {"ip": _get_local_ip(), "port": str(config.port)}


@app.get("/videos/{video_id}", response_model=None)
async def serve_video(video_id: str) -> FileResponse | JSONResponse:
    downloader: VideoDownloader | None = getattr(app.state, "downloader", None)
    if downloader is None:
        return JSONResponse(status_code=503, content={"detail": "Service not ready"})

    if not downloader.is_cached(video_id):
        return JSONResponse(status_code=404, content={"detail": "Video not found"})

    path = downloader.video_path(video_id)
    return FileResponse(path, media_type="video/webm")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    connections.connect(websocket, singer_id=None)

    # Send full state to every new connection (needed for display page)
    if router:
        state = await router.session.store.get_full_state()
        await connections.send_to(
            websocket,
            {
                "type": "state",
                "singers": [s.model_dump() for s in state.singers],
                "queue": [item.model_dump() for item in state.queue],
                "current": state.current.model_dump() if state.current else None,
                "playback": state.playback.model_dump(),
                "settings": state.settings.model_dump(),
            },
        )

    try:
        while True:
            data = await websocket.receive_json()
            if router:
                await router.handle(websocket, data)
    except WebSocketDisconnect:
        singer_id = getattr(websocket, "singer_id", None)
        connections.disconnect(websocket)
        if singer_id and router:
            await router.session.disconnect(singer_id)


# Serve frontend static files in production
static_dir = os.environ.get("STATIC_DIR", "")
if static_dir and os.path.isdir(static_dir):
    from starlette.staticfiles import StaticFiles

    _static_path = Path(static_dir)
    _index_html = _static_path / "index.html"

    app.mount(
        "/_app", StaticFiles(directory=str(_static_path / "_app")), name="app-assets"
    )

    @app.get("/{path:path}", response_model=None)
    async def spa_fallback(path: str) -> FileResponse:
        file_path = _static_path / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_index_html)

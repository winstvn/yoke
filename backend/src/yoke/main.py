from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

from yoke.config import config
from yoke.downloader import VideoDownloader
from yoke.redis_store import RedisStore
from yoke.router import MessageRouter
from yoke.session import SessionManager
from yoke.ws import ConnectionManager

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


@app.get("/videos/{video_id}")
async def serve_video(video_id: str) -> FileResponse | JSONResponse:
    downloader: VideoDownloader | None = getattr(app.state, "downloader", None)
    if downloader is None:
        return JSONResponse(
            status_code=503, content={"detail": "Service not ready"}
        )

    if not downloader.is_cached(video_id):
        return JSONResponse(
            status_code=404, content={"detail": "Video not found"}
        )

    path = downloader.video_path(video_id)
    return FileResponse(path, media_type="video/webm")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
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

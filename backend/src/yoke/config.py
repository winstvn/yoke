from __future__ import annotations

import os
from pathlib import Path


class Config:
    video_dir: Path
    max_concurrent_downloads: int
    host: str
    port: int
    redis_url: str

    def __init__(self) -> None:
        self.video_dir = Path(os.environ.get("KARAOKE_VIDEO_DIR", "./data/videos"))
        self.max_concurrent_downloads = int(
            os.environ.get("KARAOKE_MAX_CONCURRENT_DOWNLOADS", "2")
        )
        self.host = os.environ.get("KARAOKE_HOST", "0.0.0.0")
        self.port = int(os.environ.get("KARAOKE_PORT", "8000"))
        self.redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")


config = Config()

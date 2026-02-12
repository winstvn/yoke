from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

import yt_dlp


class VideoDownloader:
    def __init__(self, video_dir: Path, max_concurrent: int = 2) -> None:
        self._video_dir = video_dir
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def ensure_dir(self) -> None:
        self._video_dir.mkdir(parents=True, exist_ok=True)

    def video_path(self, video_id: str) -> Path:
        matches = list(self._video_dir.glob(f"{video_id}.*"))
        if matches:
            return matches[0]
        return self._video_dir / f"{video_id}.webm"

    def is_cached(self, video_id: str) -> bool:
        return any(self._video_dir.glob(f"{video_id}.*"))

    async def download(
        self,
        video_id: str,
        on_progress: Callable[[float], None] | None = None,
    ) -> Path:
        async with self._semaphore:
            if self.is_cached(video_id):
                return self.video_path(video_id)

            self.ensure_dir()

            def _progress_hook(d: dict) -> None:
                if on_progress is None:
                    return
                if d.get("status") != "downloading":
                    return
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                if total:
                    on_progress(downloaded / total)

            opts: dict = {
                "format": "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best",
                "outtmpl": str(self._video_dir / f"{video_id}.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [_progress_hook],
            }

            def _do_download() -> None:
                url = f"https://www.youtube.com/watch?v={video_id}"
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _do_download)

            return self.video_path(video_id)

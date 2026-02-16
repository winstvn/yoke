"""YouTube search via yt-dlp."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import partial

import yt_dlp


@dataclass(frozen=True, slots=True)
class YoutubeResult:
    """A single YouTube search result."""

    video_id: str
    title: str
    thumbnail_url: str
    duration_seconds: int


def _parse_results(data: dict | None) -> list[YoutubeResult]:
    """Parse yt-dlp extract_info output into a list of YoutubeResult."""
    if not data:
        return []

    entries = data.get("entries")
    if not entries:
        return []

    results: list[YoutubeResult] = []
    for entry in entries:
        video_id = entry.get("id")
        if not video_id:
            continue

        thumbnails = entry.get("thumbnails") or []
        thumbnail_url = thumbnails[0]["url"] if thumbnails else ""

        results.append(
            YoutubeResult(
                video_id=video_id,
                title=entry.get("title", ""),
                thumbnail_url=thumbnail_url,
                duration_seconds=entry.get("duration", 0),
            )
        )

    return results


async def search_youtube(
    query: str, max_results: int = 15
) -> list[YoutubeResult]:
    """Search YouTube and return parsed results.

    Runs yt-dlp's extract_info in a thread executor since it performs
    blocking network I/O.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }

    loop = asyncio.get_running_loop()

    def _extract() -> dict | None:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(
                f"ytsearch{max_results}:{query}", download=False
            )

    data = await loop.run_in_executor(None, _extract)
    return _parse_results(data)

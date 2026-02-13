# Yoke Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a karaoke web app where users join from phones, search/queue YouTube songs, and control playback on a TV display with real-time pitch shifting.

**Architecture:** FastAPI backend with WebSocket-driven state sync, Redis for persistence, yt-dlp for YouTube search/download, SvelteKit SPA frontend with two pages (control + display). Web Audio API handles real-time pitch transposition on the display page.

**Tech Stack:** Python 3.13, FastAPI, redis-py (async), yt-dlp, uvicorn | SvelteKit 2, Svelte 5, TypeScript | Redis | Docker Compose

**Design doc:** `docs/plans/2026-02-11-karaoke-app-design.md`

---

## Phase 1: Foundation

### Task 1: Backend Project Scaffolding

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/yoke/__init__.py`
- Create: `backend/src/yoke/main.py`
- Create: `.gitignore`

**Step 1: Initialize uv project**

```bash
cd /home/winston/code/karaoke
mkdir -p backend
cd backend
uv init --lib --python 3.13 --name yoke
```

**Step 2: Update pyproject.toml with dependencies**

Edit `backend/pyproject.toml` to include:
```toml
[project]
name = "yoke"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "redis[hiredis]>=5.0.0",
    "yt-dlp>=2024.0.0",
    "pydantic>=2.10.0",
    "websockets>=14.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.25.0",
    "fakeredis>=2.26.0",
    "httpx>=0.28.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ty]
python-version = "3.13"
```

Run: `cd /home/winston/code/karaoke/backend && uv sync`

**Step 3: Create minimal FastAPI app**

Create `backend/src/yoke/main.py`:
```python
from fastapi import FastAPI

app = FastAPI(title="Yoke", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

**Step 4: Verify it runs**

Run: `cd /home/winston/code/karaoke/backend && uv run uvicorn yoke.main:app --host 127.0.0.1 --port 8000 &`
Run: `curl http://127.0.0.1:8000/health`
Expected: `{"status":"ok"}`
Kill the server.

**Step 5: Create .gitignore**

Create `/home/winston/code/karaoke/.gitignore`:
```
__pycache__/
*.pyc
.venv/
node_modules/
.svelte-kit/
build/
data/
.env
*.egg-info/
dist/
```

**Step 6: Commit**

```bash
git add .gitignore backend/
git commit -m "Scaffold backend project with FastAPI and uv"
```

---

### Task 2: Frontend Project Scaffolding

**Files:**
- Create: `frontend/` (SvelteKit project)
- Modify: `frontend/svelte.config.js`
- Create: `frontend/src/routes/+layout.ts`

**Step 1: Create SvelteKit project**

```bash
cd /home/winston/code/karaoke
pnpm create svelte@latest frontend
```

Select: Skeleton project, TypeScript, no additional options.

**Step 2: Install dependencies**

```bash
cd /home/winston/code/karaoke/frontend
pnpm install
pnpm add -D @sveltejs/adapter-static
```

**Step 3: Configure as SPA (no SSR)**

Replace `frontend/svelte.config.js`:
```javascript
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      fallback: 'index.html'
    }),
    prerender: {
      entries: []
    }
  }
};

export default config;
```

Create `frontend/src/routes/+layout.ts`:
```typescript
export const ssr = false;
export const prerender = false;
```

**Step 4: Configure Vite dev proxy**

Update `frontend/vite.config.ts`:
```typescript
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      },
      '/videos': 'http://localhost:8000'
    }
  }
});
```

**Step 5: Create placeholder route pages**

Create `frontend/src/routes/control/+page.svelte`:
```svelte
<h1>Yoke — Control</h1>
```

Create `frontend/src/routes/display/+page.svelte`:
```svelte
<h1>Yoke — Display</h1>
```

**Step 6: Verify frontend runs**

Run: `cd /home/winston/code/karaoke/frontend && pnpm dev &`
Verify http://localhost:5173/control and http://localhost:5173/display load.
Kill the dev server.

**Step 7: Commit**

```bash
git add frontend/
git commit -m "Scaffold frontend with SvelteKit SPA"
```

---

### Task 3: Backend Models and Configuration

**Files:**
- Create: `backend/src/yoke/models.py`
- Create: `backend/src/yoke/config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_models.py`

**Step 1: Write tests for models**

Create `backend/tests/__init__.py` (empty).

Create `backend/tests/test_models.py`:
```python
import uuid
from yoke.models import Singer, Song, QueueItem, PlaybackState, SessionSettings, SessionState


def test_singer_creation():
    singer = Singer(name="Alice")
    assert singer.name == "Alice"
    assert singer.connected is True
    # id should be auto-generated
    uuid.UUID(singer.id)  # validates it's a UUID


def test_song_creation():
    song = Song(
        video_id="dQw4w9WgXcQ",
        title="Rick Astley - Never Gonna Give You Up",
        thumbnail_url="https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg",
        duration_seconds=212,
    )
    assert song.cached is False


def test_queue_item_creation():
    singer = Singer(name="Alice")
    song = Song(
        video_id="abc123",
        title="Test Song",
        thumbnail_url="https://example.com/thumb.jpg",
        duration_seconds=180,
    )
    item = QueueItem(song=song, singer=singer)
    assert item.status == "waiting"
    uuid.UUID(item.id)


def test_playback_state_defaults():
    state = PlaybackState()
    assert state.status == "stopped"
    assert state.position_seconds == 0.0
    assert state.pitch_shift == 0


def test_pitch_shift_bounds():
    state = PlaybackState(pitch_shift=6)
    assert state.pitch_shift == 6
    state = PlaybackState(pitch_shift=-6)
    assert state.pitch_shift == -6


def test_session_settings_defaults():
    settings = SessionSettings()
    assert settings.host_id is None
    assert settings.anyone_can_reorder is False


def test_session_state_empty():
    state = SessionState()
    assert state.singers == []
    assert state.queue == []
    assert state.current is None
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest tests/test_models.py -v`
Expected: FAIL (cannot import yoke.models)

**Step 3: Implement models**

Create `backend/src/yoke/models.py`:
```python
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class Singer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    connected: bool = True


class Song(BaseModel):
    video_id: str
    title: str
    thumbnail_url: str
    duration_seconds: int
    cached: bool = False


class QueueItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    song: Song
    singer: Singer
    status: Literal["waiting", "downloading", "ready", "playing", "done"] = "waiting"


class PlaybackState(BaseModel):
    status: Literal["playing", "paused", "stopped"] = "stopped"
    position_seconds: float = 0.0
    pitch_shift: int = Field(default=0, ge=-6, le=6)


class SessionSettings(BaseModel):
    host_id: str | None = None
    anyone_can_reorder: bool = False


class SessionState(BaseModel):
    singers: list[Singer] = Field(default_factory=list)
    queue: list[QueueItem] = Field(default_factory=list)
    current: QueueItem | None = None
    playback: PlaybackState = Field(default_factory=PlaybackState)
    settings: SessionSettings = Field(default_factory=SessionSettings)
```

**Step 4: Implement config**

Create `backend/src/yoke/config.py`:
```python
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
```

**Step 5: Run tests to verify they pass**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest tests/test_models.py -v`
Expected: All PASS

**Step 6: Type check**

Run: `cd /home/winston/code/karaoke/backend && uv run ty check src/`
Expected: No errors (or install ty first: `uv tool install ty`)

**Step 7: Commit**

```bash
git add backend/src/yoke/models.py backend/src/yoke/config.py backend/tests/
git commit -m "Add Pydantic models and config"
```

---

### Task 4: Redis Storage Layer

**Files:**
- Create: `backend/src/yoke/redis_store.py`
- Create: `backend/tests/test_redis_store.py`

**Step 1: Write tests for Redis store**

Create `backend/tests/test_redis_store.py`:
```python
import fakeredis.aioredis
import pytest

from yoke.models import (
    PlaybackState,
    QueueItem,
    SessionSettings,
    Singer,
    Song,
    SessionState,
)
from yoke.redis_store import RedisStore


@pytest.fixture
async def store():
    redis = fakeredis.aioredis.FakeRedis()
    s = RedisStore(redis)
    yield s
    await redis.aclose()


async def test_save_and_get_singer(store: RedisStore):
    singer = Singer(name="Alice")
    await store.save_singer(singer)
    result = await store.get_singer(singer.id)
    assert result is not None
    assert result.name == "Alice"


async def test_get_nonexistent_singer(store: RedisStore):
    result = await store.get_singer("nonexistent")
    assert result is None


async def test_get_all_singers(store: RedisStore):
    await store.save_singer(Singer(name="Alice"))
    await store.save_singer(Singer(name="Bob"))
    singers = await store.get_all_singers()
    assert len(singers) == 2


async def test_remove_singer(store: RedisStore):
    singer = Singer(name="Alice")
    await store.save_singer(singer)
    await store.remove_singer(singer.id)
    assert await store.get_singer(singer.id) is None


async def test_save_and_get_song(store: RedisStore):
    song = Song(
        video_id="abc123",
        title="Test Song",
        thumbnail_url="https://example.com/thumb.jpg",
        duration_seconds=180,
        cached=True,
    )
    await store.save_song(song)
    result = await store.get_song("abc123")
    assert result is not None
    assert result.cached is True


async def test_queue_operations(store: RedisStore):
    singer = Singer(name="Alice")
    song = Song(
        video_id="abc123",
        title="Test Song",
        thumbnail_url="https://example.com/thumb.jpg",
        duration_seconds=180,
    )
    item = QueueItem(song=song, singer=singer)

    await store.append_to_queue(item)
    queue = await store.get_queue()
    assert len(queue) == 1
    assert queue[0].id == item.id

    await store.remove_from_queue(item.id)
    queue = await store.get_queue()
    assert len(queue) == 0


async def test_reorder_queue(store: RedisStore):
    singer = Singer(name="Alice")
    song1 = Song(video_id="a", title="A", thumbnail_url="", duration_seconds=60)
    song2 = Song(video_id="b", title="B", thumbnail_url="", duration_seconds=60)
    item1 = QueueItem(song=song1, singer=singer)
    item2 = QueueItem(song=song2, singer=singer)

    await store.append_to_queue(item1)
    await store.append_to_queue(item2)
    await store.reorder_queue([item2.id, item1.id])

    queue = await store.get_queue()
    assert queue[0].id == item2.id
    assert queue[1].id == item1.id


async def test_playback_state(store: RedisStore):
    state = PlaybackState(status="playing", position_seconds=42.5, pitch_shift=2)
    await store.save_playback(state)
    result = await store.get_playback()
    assert result.status == "playing"
    assert result.pitch_shift == 2


async def test_settings(store: RedisStore):
    settings = SessionSettings(host_id="singer-1", anyone_can_reorder=True)
    await store.save_settings(settings)
    result = await store.get_settings()
    assert result.host_id == "singer-1"
    assert result.anyone_can_reorder is True


async def test_current_item(store: RedisStore):
    singer = Singer(name="Alice")
    song = Song(video_id="abc", title="T", thumbnail_url="", duration_seconds=60)
    item = QueueItem(song=song, singer=singer)

    await store.save_current(item)
    result = await store.get_current()
    assert result is not None
    assert result.id == item.id

    await store.clear_current()
    assert await store.get_current() is None


async def test_get_full_state(store: RedisStore):
    singer = Singer(name="Alice")
    await store.save_singer(singer)
    settings = SessionSettings(host_id=singer.id)
    await store.save_settings(settings)

    state = await store.get_full_state()
    assert isinstance(state, SessionState)
    assert len(state.singers) == 1
    assert state.settings.host_id == singer.id
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest tests/test_redis_store.py -v`
Expected: FAIL (cannot import yoke.redis_store)

**Step 3: Implement Redis store**

Create `backend/src/yoke/redis_store.py`:
```python
from __future__ import annotations

import json
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
                await self._r.rpush(
                    f"{PREFIX}:queue", by_id[item_id].model_dump_json()
                )

    async def update_queue_item(self, item_id: str, **fields: object) -> None:
        queue = await self.get_queue()
        await self._r.delete(f"{PREFIX}:queue")
        for item in queue:
            if item.id == item_id:
                for k, v in fields.items():
                    setattr(item, k, v)
            await self._r.rpush(f"{PREFIX}:queue", item.model_dump_json())

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
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest tests/test_redis_store.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/src/yoke/redis_store.py backend/tests/test_redis_store.py
git commit -m "Add Redis storage layer with full test coverage"
```

---

## Phase 2: Core Backend

### Task 5: YouTube Search

**Files:**
- Create: `backend/src/yoke/youtube.py`
- Create: `backend/tests/test_youtube.py`

**Step 1: Write tests for YouTube search**

Create `backend/tests/test_youtube.py`:
```python
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from yoke.youtube import search_youtube, YoutubeResult


def _make_entry(video_id: str, title: str, duration: int) -> dict:
    return {
        "id": video_id,
        "title": title,
        "duration": duration,
        "thumbnails": [{"url": f"https://i.ytimg.com/vi/{video_id}/default.jpg"}],
    }


@patch("yoke.youtube.asyncio.get_event_loop")
def test_search_youtube(mock_loop: MagicMock):
    entries = [
        _make_entry("abc123", "Test Karaoke Song", 240),
        _make_entry("def456", "Another Song", 180),
    ]
    extract_result = {"entries": entries}

    future = AsyncMock()
    mock_loop.return_value.run_in_executor = AsyncMock(return_value=extract_result)

    # We test the sync extraction logic directly instead
    from yoke.youtube import _parse_results

    results = _parse_results(extract_result)
    assert len(results) == 2
    assert results[0].video_id == "abc123"
    assert results[0].title == "Test Karaoke Song"
    assert results[0].duration_seconds == 240
    assert "abc123" in results[0].thumbnail_url


def test_parse_results_handles_missing_entries():
    from yoke.youtube import _parse_results

    assert _parse_results(None) == []
    assert _parse_results({}) == []
    assert _parse_results({"entries": None}) == []


def test_parse_results_skips_entries_without_id():
    from yoke.youtube import _parse_results

    entries = [
        {"title": "No ID", "duration": 60, "thumbnails": []},
        _make_entry("valid", "Valid Song", 120),
    ]
    results = _parse_results({"entries": entries})
    assert len(results) == 1
    assert results[0].video_id == "valid"
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest tests/test_youtube.py -v`
Expected: FAIL

**Step 3: Implement YouTube search**

Create `backend/src/yoke/youtube.py`:
```python
from __future__ import annotations

import asyncio
from dataclasses import dataclass

import yt_dlp


@dataclass
class YoutubeResult:
    video_id: str
    title: str
    thumbnail_url: str
    duration_seconds: int


YDL_SEARCH_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": True,
    "skip_download": True,
}


def _parse_results(data: dict | None) -> list[YoutubeResult]:
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
        thumb_url = thumbnails[0]["url"] if thumbnails else ""
        results.append(
            YoutubeResult(
                video_id=video_id,
                title=entry.get("title", ""),
                thumbnail_url=thumb_url,
                duration_seconds=entry.get("duration") or 0,
            )
        )
    return results


async def search_youtube(query: str, max_results: int = 10) -> list[YoutubeResult]:
    loop = asyncio.get_event_loop()
    opts = {**YDL_SEARCH_OPTS}

    def _extract() -> dict | None:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)  # type: ignore[return-value]

    data = await loop.run_in_executor(None, _extract)
    return _parse_results(data)
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest tests/test_youtube.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/src/yoke/youtube.py backend/tests/test_youtube.py
git commit -m "Add YouTube search via yt-dlp"
```

---

### Task 6: Video Download and Cache

**Files:**
- Create: `backend/src/yoke/downloader.py`
- Create: `backend/tests/test_downloader.py`

**Step 1: Write tests for downloader**

Create `backend/tests/test_downloader.py`:
```python
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from yoke.downloader import VideoDownloader


@pytest.fixture
def tmp_video_dir(tmp_path: Path) -> Path:
    return tmp_path / "videos"


@pytest.fixture
def downloader(tmp_video_dir: Path) -> VideoDownloader:
    return VideoDownloader(video_dir=tmp_video_dir, max_concurrent=2)


def test_video_path(downloader: VideoDownloader, tmp_video_dir: Path):
    path = downloader.video_path("abc123")
    assert path.parent == tmp_video_dir
    assert "abc123" in path.name


def test_is_cached_false(downloader: VideoDownloader):
    assert downloader.is_cached("nonexistent") is False


def test_is_cached_true(downloader: VideoDownloader, tmp_video_dir: Path):
    tmp_video_dir.mkdir(parents=True)
    (tmp_video_dir / "abc123.webm").write_text("fake video")
    assert downloader.is_cached("abc123") is True


def test_creates_video_dir_on_init(tmp_video_dir: Path):
    assert not tmp_video_dir.exists()
    downloader = VideoDownloader(video_dir=tmp_video_dir, max_concurrent=1)
    downloader.ensure_dir()
    assert tmp_video_dir.exists()
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest tests/test_downloader.py -v`
Expected: FAIL

**Step 3: Implement downloader**

Create `backend/src/yoke/downloader.py`:
```python
from __future__ import annotations

import asyncio
import glob as globmod
from pathlib import Path
from typing import Callable

import yt_dlp


class VideoDownloader:
    def __init__(self, video_dir: Path, max_concurrent: int = 2) -> None:
        self._video_dir = video_dir
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def ensure_dir(self) -> None:
        self._video_dir.mkdir(parents=True, exist_ok=True)

    def video_path(self, video_id: str) -> Path:
        # yt-dlp may produce different extensions; find any matching file
        matches = globmod.glob(str(self._video_dir / f"{video_id}.*"))
        if matches:
            return Path(matches[0])
        return self._video_dir / f"{video_id}.webm"

    def is_cached(self, video_id: str) -> bool:
        matches = globmod.glob(str(self._video_dir / f"{video_id}.*"))
        return len(matches) > 0

    async def download(
        self,
        video_id: str,
        on_progress: Callable[[float], None] | None = None,
    ) -> Path:
        async with self._semaphore:
            self.ensure_dir()
            if self.is_cached(video_id):
                return self.video_path(video_id)

            output_template = str(self._video_dir / f"{video_id}.%(ext)s")
            opts: dict = {
                "format": "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best",
                "outtmpl": output_template,
                "quiet": True,
                "no_warnings": True,
            }

            if on_progress:

                def _hook(d: dict) -> None:
                    if d.get("status") == "downloading":
                        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                        downloaded = d.get("downloaded_bytes", 0)
                        if total > 0:
                            on_progress(downloaded / total * 100)

                opts["progress_hooks"] = [_hook]

            loop = asyncio.get_event_loop()

            def _download() -> None:
                url = f"https://www.youtube.com/watch?v={video_id}"
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])

            await loop.run_in_executor(None, _download)
            return self.video_path(video_id)
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest tests/test_downloader.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/src/yoke/downloader.py backend/tests/test_downloader.py
git commit -m "Add video downloader with concurrency control"
```

---

### Task 7: WebSocket Connection Manager

**Files:**
- Create: `backend/src/yoke/ws.py`
- Create: `backend/tests/test_ws.py`

**Step 1: Write tests for connection manager**

Create `backend/tests/test_ws.py`:
```python
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from yoke.ws import ConnectionManager


def make_mock_ws(singer_id: str | None = None) -> AsyncMock:
    ws = AsyncMock()
    ws.singer_id = singer_id
    return ws


async def test_connect_and_disconnect():
    mgr = ConnectionManager()
    ws = make_mock_ws()

    mgr.connect(ws, "singer-1")
    assert len(mgr.active_connections) == 1
    assert ws.singer_id == "singer-1"

    mgr.disconnect(ws)
    assert len(mgr.active_connections) == 0


async def test_broadcast():
    mgr = ConnectionManager()
    ws1 = make_mock_ws()
    ws2 = make_mock_ws()
    mgr.connect(ws1, "s1")
    mgr.connect(ws2, "s2")

    await mgr.broadcast({"type": "test", "data": "hello"})

    ws1.send_json.assert_called_once_with({"type": "test", "data": "hello"})
    ws2.send_json.assert_called_once_with({"type": "test", "data": "hello"})


async def test_send_to_one():
    mgr = ConnectionManager()
    ws1 = make_mock_ws()
    ws2 = make_mock_ws()
    mgr.connect(ws1, "s1")
    mgr.connect(ws2, "s2")

    await mgr.send_to(ws1, {"type": "private"})

    ws1.send_json.assert_called_once_with({"type": "private"})
    ws2.send_json.assert_not_called()


async def test_broadcast_excludes():
    mgr = ConnectionManager()
    ws1 = make_mock_ws()
    ws2 = make_mock_ws()
    mgr.connect(ws1, "s1")
    mgr.connect(ws2, "s2")

    await mgr.broadcast({"type": "event"}, exclude=ws1)

    ws1.send_json.assert_not_called()
    ws2.send_json.assert_called_once()


async def test_get_connection_by_singer_id():
    mgr = ConnectionManager()
    ws = make_mock_ws()
    mgr.connect(ws, "singer-1")

    assert mgr.get_by_singer_id("singer-1") is ws
    assert mgr.get_by_singer_id("nonexistent") is None
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest tests/test_ws.py -v`
Expected: FAIL

**Step 3: Implement connection manager**

Create `backend/src/yoke/ws.py`:
```python
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    def connect(self, ws: WebSocket, singer_id: str) -> None:
        ws.singer_id = singer_id  # type: ignore[attr-defined]
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active_connections:
            self.active_connections.remove(ws)

    def get_by_singer_id(self, singer_id: str) -> WebSocket | None:
        for ws in self.active_connections:
            if getattr(ws, "singer_id", None) == singer_id:
                return ws
        return None

    async def send_to(self, ws: WebSocket, message: dict[str, Any]) -> None:
        try:
            await ws.send_json(message)
        except Exception:
            logger.warning("Failed to send to WebSocket")

    async def broadcast(
        self, message: dict[str, Any], exclude: WebSocket | None = None
    ) -> None:
        for ws in self.active_connections:
            if ws is not exclude:
                await self.send_to(ws, message)
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest tests/test_ws.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/src/yoke/ws.py backend/tests/test_ws.py
git commit -m "Add WebSocket connection manager"
```

---

### Task 8: Session Logic (Business Layer)

**Files:**
- Create: `backend/src/yoke/session.py`
- Create: `backend/tests/test_session.py`

**Step 1: Write tests for session logic**

Create `backend/tests/test_session.py`:
```python
import fakeredis.aioredis
import pytest
from unittest.mock import AsyncMock

from yoke.models import Singer, Song, QueueItem, PlaybackState
from yoke.redis_store import RedisStore
from yoke.session import SessionManager


@pytest.fixture
async def session():
    redis = fakeredis.aioredis.FakeRedis()
    store = RedisStore(redis)
    mgr = SessionManager(store)
    yield mgr
    await redis.aclose()


async def test_join_first_singer_becomes_host(session: SessionManager):
    singer = await session.join("Alice")
    assert singer.name == "Alice"
    settings = await session.store.get_settings()
    assert settings.host_id == singer.id


async def test_join_second_singer_not_host(session: SessionManager):
    first = await session.join("Alice")
    second = await session.join("Bob")
    settings = await session.store.get_settings()
    assert settings.host_id == first.id


async def test_queue_song(session: SessionManager):
    singer = await session.join("Alice")
    song = Song(
        video_id="abc123",
        title="Test",
        thumbnail_url="",
        duration_seconds=180,
    )
    item = await session.queue_song(singer.id, song)
    assert item.singer.id == singer.id
    assert item.status == "waiting"
    queue = await session.store.get_queue()
    assert len(queue) == 1


async def test_remove_own_song(session: SessionManager):
    singer = await session.join("Alice")
    song = Song(video_id="a", title="A", thumbnail_url="", duration_seconds=60)
    item = await session.queue_song(singer.id, song)
    result = await session.remove_from_queue(item.id, singer.id)
    assert result is True
    queue = await session.store.get_queue()
    assert len(queue) == 0


async def test_remove_others_song_as_host(session: SessionManager):
    host = await session.join("Host")
    other = await session.join("Other")
    song = Song(video_id="a", title="A", thumbnail_url="", duration_seconds=60)
    item = await session.queue_song(other.id, song)
    result = await session.remove_from_queue(item.id, host.id)
    assert result is True


async def test_remove_others_song_as_non_host_fails(session: SessionManager):
    host = await session.join("Host")
    alice = await session.join("Alice")
    bob = await session.join("Bob")
    song = Song(video_id="a", title="A", thumbnail_url="", duration_seconds=60)
    item = await session.queue_song(alice.id, song)
    result = await session.remove_from_queue(item.id, bob.id)
    assert result is False


async def test_reorder_as_host(session: SessionManager):
    host = await session.join("Host")
    song1 = Song(video_id="a", title="A", thumbnail_url="", duration_seconds=60)
    song2 = Song(video_id="b", title="B", thumbnail_url="", duration_seconds=60)
    i1 = await session.queue_song(host.id, song1)
    i2 = await session.queue_song(host.id, song2)
    result = await session.reorder_queue([i2.id, i1.id], host.id)
    assert result is True
    queue = await session.store.get_queue()
    assert queue[0].id == i2.id


async def test_reorder_as_non_host_denied_by_default(session: SessionManager):
    host = await session.join("Host")
    other = await session.join("Other")
    song = Song(video_id="a", title="A", thumbnail_url="", duration_seconds=60)
    await session.queue_song(host.id, song)
    result = await session.reorder_queue([], other.id)
    assert result is False


async def test_reorder_as_non_host_allowed_when_setting_on(session: SessionManager):
    host = await session.join("Host")
    other = await session.join("Other")
    await session.update_setting(host.id, "anyone_can_reorder", True)
    song = Song(video_id="a", title="A", thumbnail_url="", duration_seconds=60)
    i1 = await session.queue_song(host.id, song)
    result = await session.reorder_queue([i1.id], other.id)
    assert result is True


async def test_skip_advances_queue(session: SessionManager):
    host = await session.join("Host")
    song1 = Song(video_id="a", title="A", thumbnail_url="", duration_seconds=60)
    song2 = Song(video_id="b", title="B", thumbnail_url="", duration_seconds=60)
    await session.queue_song(host.id, song1)
    await session.queue_song(host.id, song2)

    # Start playing first song
    next_item = await session.advance_queue()
    assert next_item is not None
    assert next_item.song.video_id == "a"

    # Skip to second
    next_item = await session.advance_queue()
    assert next_item is not None
    assert next_item.song.video_id == "b"

    # No more songs
    next_item = await session.advance_queue()
    assert next_item is None


async def test_update_setting_host_only(session: SessionManager):
    host = await session.join("Host")
    other = await session.join("Other")
    result = await session.update_setting(other.id, "anyone_can_reorder", True)
    assert result is False
    result = await session.update_setting(host.id, "anyone_can_reorder", True)
    assert result is True
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest tests/test_session.py -v`
Expected: FAIL

**Step 3: Implement session manager**

Create `backend/src/yoke/session.py`:
```python
from __future__ import annotations

from yoke.models import (
    PlaybackState,
    QueueItem,
    SessionSettings,
    Singer,
    Song,
)
from yoke.redis_store import RedisStore


class SessionManager:
    def __init__(self, store: RedisStore) -> None:
        self.store = store

    async def join(self, name: str) -> Singer:
        singer = Singer(name=name)
        await self.store.save_singer(singer)

        settings = await self.store.get_settings()
        if settings.host_id is None:
            settings.host_id = singer.id
            await self.store.save_settings(settings)

        return singer

    async def disconnect(self, singer_id: str) -> None:
        singer = await self.store.get_singer(singer_id)
        if singer:
            singer.connected = False
            await self.store.save_singer(singer)

    async def queue_song(self, singer_id: str, song: Song) -> QueueItem:
        singer = await self.store.get_singer(singer_id)
        if not singer:
            raise ValueError(f"Unknown singer: {singer_id}")
        item = QueueItem(song=song, singer=singer)
        await self.store.append_to_queue(item)
        return item

    async def remove_from_queue(self, item_id: str, requester_id: str) -> bool:
        queue = await self.store.get_queue()
        item = next((i for i in queue if i.id == item_id), None)
        if not item:
            return False

        settings = await self.store.get_settings()
        is_host = requester_id == settings.host_id
        is_own = item.singer.id == requester_id

        if not is_host and not is_own:
            return False

        await self.store.remove_from_queue(item_id)
        return True

    async def reorder_queue(self, item_ids: list[str], requester_id: str) -> bool:
        settings = await self.store.get_settings()
        is_host = requester_id == settings.host_id

        if not is_host and not settings.anyone_can_reorder:
            return False

        await self.store.reorder_queue(item_ids)
        return True

    async def advance_queue(self) -> QueueItem | None:
        queue = await self.store.get_queue()
        if not queue:
            await self.store.clear_current()
            await self.store.save_playback(PlaybackState())
            return None

        next_item = queue[0]
        next_item.status = "playing"
        await self.store.remove_from_queue(next_item.id)
        await self.store.save_current(next_item)
        await self.store.save_playback(PlaybackState(status="playing"))
        return next_item

    async def update_setting(self, requester_id: str, key: str, value: object) -> bool:
        settings = await self.store.get_settings()
        if requester_id != settings.host_id:
            return False
        if not hasattr(settings, key):
            return False
        setattr(settings, key, value)
        await self.store.save_settings(settings)
        return True
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest tests/test_session.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/src/yoke/session.py backend/tests/test_session.py
git commit -m "Add session manager with queue and permission logic"
```

---

### Task 9: WebSocket Endpoint and Message Router

**Files:**
- Modify: `backend/src/yoke/main.py`
- Create: `backend/src/yoke/router.py`
- Create: `backend/tests/test_router.py`

This task wires together the WebSocket endpoint, message routing, and integrates with session logic, downloader, and YouTube search. This is the central nervous system of the app.

**Step 1: Write tests for message router**

Create `backend/tests/test_router.py`:
```python
import fakeredis.aioredis
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from yoke.models import Song
from yoke.redis_store import RedisStore
from yoke.session import SessionManager
from yoke.ws import ConnectionManager
from yoke.downloader import VideoDownloader
from yoke.router import MessageRouter


@pytest.fixture
async def setup():
    redis = fakeredis.aioredis.FakeRedis()
    store = RedisStore(redis)
    session = SessionManager(store)
    connections = ConnectionManager()
    downloader = VideoDownloader(video_dir=Path("/tmp/test-videos"), max_concurrent=1)

    router = MessageRouter(
        session=session,
        connections=connections,
        downloader=downloader,
    )
    yield router, connections, session, store
    await redis.aclose()


async def test_handle_join(setup):
    router, connections, session, store = setup
    ws = AsyncMock()
    ws.singer_id = None

    await router.handle(ws, {"type": "join", "name": "Alice"})

    # Should have sent state to the new client
    ws.send_json.assert_called()
    calls = ws.send_json.call_args_list
    # First call should be state hydration
    state_msg = calls[0][0][0]
    assert state_msg["type"] == "state"


async def test_handle_playback(setup):
    router, connections, session, store = setup
    ws = AsyncMock()

    # Join first
    await router.handle(ws, {"type": "join", "name": "Alice"})
    connections.connect(ws, ws.singer_id)

    await router.handle(ws, {"type": "playback", "action": "pause"})

    playback = await store.get_playback()
    assert playback.status == "paused"


async def test_handle_pitch(setup):
    router, connections, session, store = setup
    ws = AsyncMock()

    await router.handle(ws, {"type": "join", "name": "Alice"})
    connections.connect(ws, ws.singer_id)

    await router.handle(ws, {"type": "pitch", "semitones": 3})

    playback = await store.get_playback()
    assert playback.pitch_shift == 3


async def test_handle_update_setting(setup):
    router, connections, session, store = setup
    ws = AsyncMock()

    await router.handle(ws, {"type": "join", "name": "Host"})
    connections.connect(ws, ws.singer_id)

    await router.handle(
        ws, {"type": "update_setting", "key": "anyone_can_reorder", "value": True}
    )

    settings = await store.get_settings()
    assert settings.anyone_can_reorder is True
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest tests/test_router.py -v`
Expected: FAIL

**Step 3: Implement message router**

Create `backend/src/yoke/router.py`:
```python
from __future__ import annotations

import asyncio
import logging
from typing import Any, TYPE_CHECKING

from yoke.models import PlaybackState, Song
from yoke.session import SessionManager
from yoke.ws import ConnectionManager
from yoke.downloader import VideoDownloader
from yoke.youtube import search_youtube

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


class MessageRouter:
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
        msg_type = message.get("type")
        handler = getattr(self, f"_handle_{msg_type}", None)
        if handler:
            await handler(ws, message)
        else:
            await self.connections.send_to(
                ws, {"type": "error", "message": f"Unknown message type: {msg_type}"}
            )

    async def _handle_join(self, ws: WebSocket, msg: dict) -> None:
        name = msg.get("name", "Anonymous")
        singer = await self.session.join(name)
        ws.singer_id = singer.id  # type: ignore[attr-defined]
        self.connections.connect(ws, singer.id)

        # Send full state to the new client
        state = await self.session.store.get_full_state()
        await self.connections.send_to(
            ws, {"type": "state", **state.model_dump()}
        )

        # Broadcast join to everyone else
        await self.connections.broadcast(
            {"type": "singer_joined", "singer": singer.model_dump()},
            exclude=ws,
        )

    async def _handle_search(self, ws: WebSocket, msg: dict) -> None:
        query = msg.get("query", "")
        if not query:
            return
        results = await search_youtube(query)
        songs: list[dict] = []
        for r in results:
            cached = self.downloader.is_cached(r.video_id)
            song = Song(
                video_id=r.video_id,
                title=r.title,
                thumbnail_url=r.thumbnail_url,
                duration_seconds=r.duration_seconds,
                cached=cached,
            )
            songs.append(song.model_dump())
        await self.connections.send_to(ws, {"type": "search_results", "songs": songs})

    async def _handle_queue_song(self, ws: WebSocket, msg: dict) -> None:
        singer_id = getattr(ws, "singer_id", None)
        video_id = msg.get("video_id")
        if not singer_id or not video_id:
            return

        # Look up song info from Redis or search
        song_data = await self.session.store.get_song(video_id)
        if not song_data:
            # Fetch info for this specific video
            results = await search_youtube(video_id, max_results=1)
            if not results:
                await self.connections.send_to(
                    ws, {"type": "error", "message": "Song not found"}
                )
                return
            r = results[0]
            song_data = Song(
                video_id=r.video_id,
                title=r.title,
                thumbnail_url=r.thumbnail_url,
                duration_seconds=r.duration_seconds,
                cached=self.downloader.is_cached(r.video_id),
            )

        item = await self.session.queue_song(singer_id, song_data)
        singer = await self.session.store.get_singer(singer_id)

        # Broadcast queue update
        queue = await self.session.store.get_queue()
        await self.connections.broadcast(
            {"type": "queue_updated", "queue": [i.model_dump() for i in queue]}
        )
        await self.connections.broadcast(
            {
                "type": "song_queued",
                "item": item.model_dump(),
                "singer": singer.model_dump() if singer else None,
            }
        )

        # Start download if not cached
        if not self.downloader.is_cached(video_id):
            asyncio.create_task(self._download_video(item.id, video_id))

    async def _download_video(self, item_id: str, video_id: str) -> None:
        # Update status to downloading
        await self.session.store.update_queue_item(item_id, status="downloading")
        await self._broadcast_queue()

        async def on_progress(percent: float) -> None:
            await self.connections.broadcast(
                {
                    "type": "download_progress",
                    "video_id": video_id,
                    "percent": round(percent, 1),
                }
            )

        def sync_progress(percent: float) -> None:
            # Schedule the async broadcast from the sync callback
            try:
                loop = asyncio.get_event_loop()
                loop.call_soon_threadsafe(
                    asyncio.ensure_future, on_progress(percent)
                )
            except RuntimeError:
                pass

        try:
            await self.downloader.download(video_id, on_progress=sync_progress)

            # Update song as cached
            song = await self.session.store.get_song(video_id)
            if song:
                song.cached = True
                await self.session.store.save_song(song)

            # Update queue item status
            await self.session.store.update_queue_item(item_id, status="ready")
            await self._broadcast_queue()
        except Exception as e:
            logger.error(f"Download failed for {video_id}: {e}")
            await self.connections.broadcast(
                {"type": "error", "message": f"Download failed: {video_id}"}
            )

    async def _handle_remove_from_queue(self, ws: WebSocket, msg: dict) -> None:
        singer_id = getattr(ws, "singer_id", None)
        item_id = msg.get("item_id")
        if not singer_id or not item_id:
            return
        result = await self.session.remove_from_queue(item_id, singer_id)
        if result:
            await self._broadcast_queue()
        else:
            await self.connections.send_to(
                ws, {"type": "error", "message": "Cannot remove that item"}
            )

    async def _handle_reorder_queue(self, ws: WebSocket, msg: dict) -> None:
        singer_id = getattr(ws, "singer_id", None)
        item_ids = msg.get("item_ids", [])
        if not singer_id:
            return
        result = await self.session.reorder_queue(item_ids, singer_id)
        if result:
            await self._broadcast_queue()
        else:
            await self.connections.send_to(
                ws, {"type": "error", "message": "Not allowed to reorder"}
            )

    async def _handle_playback(self, ws: WebSocket, msg: dict) -> None:
        action = msg.get("action")
        playback = await self.session.store.get_playback()

        if action == "play":
            playback.status = "playing"
        elif action == "pause":
            playback.status = "paused"
        elif action == "stop":
            playback.status = "stopped"
            playback.position_seconds = 0.0
        elif action == "skip":
            next_item = await self.session.advance_queue()
            if next_item:
                await self.connections.broadcast(
                    {"type": "now_playing", "item": next_item.model_dump()}
                )
            await self._broadcast_queue()
            return
        elif action == "restart":
            playback.position_seconds = 0.0
            playback.status = "playing"

        await self.session.store.save_playback(playback)
        await self.connections.broadcast(
            {"type": "playback_updated", "playback": playback.model_dump()}
        )

    async def _handle_seek(self, ws: WebSocket, msg: dict) -> None:
        position = msg.get("position_seconds", 0.0)
        playback = await self.session.store.get_playback()
        playback.position_seconds = float(position)
        await self.session.store.save_playback(playback)
        await self.connections.broadcast(
            {"type": "playback_updated", "playback": playback.model_dump()}
        )

    async def _handle_pitch(self, ws: WebSocket, msg: dict) -> None:
        semitones = msg.get("semitones", 0)
        semitones = max(-6, min(6, int(semitones)))
        playback = await self.session.store.get_playback()
        playback.pitch_shift = semitones
        await self.session.store.save_playback(playback)
        await self.connections.broadcast(
            {"type": "playback_updated", "playback": playback.model_dump()}
        )

    async def _handle_position_update(self, ws: WebSocket, msg: dict) -> None:
        position = msg.get("position_seconds", 0.0)
        playback = await self.session.store.get_playback()
        playback.position_seconds = float(position)
        await self.session.store.save_playback(playback)
        # Relay to all other clients (especially control pages)
        await self.connections.broadcast(
            {"type": "playback_updated", "playback": playback.model_dump()},
            exclude=ws,
        )

    async def _handle_update_setting(self, ws: WebSocket, msg: dict) -> None:
        singer_id = getattr(ws, "singer_id", None)
        key = msg.get("key")
        value = msg.get("value")
        if not singer_id or not key:
            return
        result = await self.session.update_setting(singer_id, key, value)
        if not result:
            await self.connections.send_to(
                ws, {"type": "error", "message": "Not authorized to change settings"}
            )

    async def _handle_show_qr(self, ws: WebSocket, msg: dict) -> None:
        await self.connections.broadcast({"type": "show_qr"})

    async def _handle_screen_message(self, ws: WebSocket, msg: dict) -> None:
        singer_id = getattr(ws, "singer_id", None)
        text = msg.get("text", "")
        if not singer_id or not text:
            return
        singer = await self.session.store.get_singer(singer_id)
        name = singer.name if singer else "Anonymous"
        await self.connections.broadcast(
            {"type": "screen_message", "name": name, "text": text}
        )

    async def _broadcast_queue(self) -> None:
        queue = await self.session.store.get_queue()
        await self.connections.broadcast(
            {"type": "queue_updated", "queue": [i.model_dump() for i in queue]}
        )
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest tests/test_router.py -v`
Expected: All PASS

**Step 5: Wire up FastAPI main with WebSocket endpoint and video serving**

Update `backend/src/yoke/main.py`:
```python
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from yoke.config import config
from yoke.downloader import VideoDownloader
from yoke.redis_store import RedisStore
from yoke.router import MessageRouter
from yoke.session import SessionManager
from yoke.ws import ConnectionManager

logger = logging.getLogger(__name__)

connections = ConnectionManager()
router: MessageRouter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
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
        session=session,
        connections=connections,
        downloader=downloader,
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
async def serve_video(video_id: str):
    downloader: VideoDownloader = app.state.downloader
    if not downloader.is_cached(video_id):
        return {"error": "Video not found"}, 404
    path = downloader.video_path(video_id)
    return FileResponse(path, media_type="video/webm")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
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
```

**Step 6: Run all tests**

Run: `cd /home/winston/code/karaoke/backend && uv run pytest -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add backend/src/yoke/router.py backend/src/yoke/main.py backend/tests/test_router.py
git commit -m "Add WebSocket message router and wire up FastAPI endpoints"
```

---

## Phase 3: Frontend Foundation

### Task 10: Frontend Types and WebSocket Client

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/ws.ts`
- Create: `frontend/src/lib/stores/session.ts`

**Step 1: Create TypeScript types mirroring backend models**

Create `frontend/src/lib/types.ts`:
```typescript
export interface Singer {
  id: string;
  name: string;
  connected: boolean;
}

export interface Song {
  video_id: string;
  title: string;
  thumbnail_url: string;
  duration_seconds: number;
  cached: boolean;
}

export interface QueueItem {
  id: string;
  song: Song;
  singer: Singer;
  status: 'waiting' | 'downloading' | 'ready' | 'playing' | 'done';
}

export interface PlaybackState {
  status: 'playing' | 'paused' | 'stopped';
  position_seconds: number;
  pitch_shift: number;
}

export interface SessionSettings {
  host_id: string | null;
  anyone_can_reorder: boolean;
}

export interface SessionState {
  singers: Singer[];
  queue: QueueItem[];
  current: QueueItem | null;
  playback: PlaybackState;
  settings: SessionSettings;
}

// WebSocket message types
export type ServerMessage =
  | { type: 'state' } & SessionState
  | { type: 'singer_joined'; singer: Singer }
  | { type: 'song_queued'; item: QueueItem; singer: Singer }
  | { type: 'queue_updated'; queue: QueueItem[] }
  | { type: 'playback_updated'; playback: PlaybackState }
  | { type: 'download_progress'; video_id: string; percent: number }
  | { type: 'search_results'; songs: Song[] }
  | { type: 'show_qr' }
  | { type: 'screen_message'; name: string; text: string }
  | { type: 'now_playing'; item: QueueItem }
  | { type: 'up_next'; singer: Singer; song: Song }
  | { type: 'error'; message: string };

export type ClientMessage =
  | { type: 'join'; name: string }
  | { type: 'search'; query: string }
  | { type: 'queue_song'; video_id: string }
  | { type: 'remove_from_queue'; item_id: string }
  | { type: 'reorder_queue'; item_ids: string[] }
  | { type: 'playback'; action: 'play' | 'pause' | 'stop' | 'skip' | 'restart' }
  | { type: 'seek'; position_seconds: number }
  | { type: 'pitch'; semitones: number }
  | { type: 'update_setting'; key: string; value: unknown }
  | { type: 'show_qr' }
  | { type: 'screen_message'; text: string }
  | { type: 'position_update'; position_seconds: number };
```

**Step 2: Create WebSocket client wrapper**

Create `frontend/src/lib/ws.ts`:
```typescript
import type { ClientMessage, ServerMessage } from './types';

type MessageHandler = (message: ServerMessage) => void;

export class YokeSocket {
  private ws: WebSocket | null = null;
  private handlers: MessageHandler[] = [];
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private url: string;

  constructor(url?: string) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    this.url = url ?? `${protocol}//${window.location.host}/ws`;
  }

  connect(): void {
    this.ws = new WebSocket(this.url);

    this.ws.onmessage = (event) => {
      const message: ServerMessage = JSON.parse(event.data);
      for (const handler of this.handlers) {
        handler(message);
      }
    };

    this.ws.onclose = () => {
      this.reconnectTimer = setTimeout(() => this.connect(), 2000);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    this.ws?.close();
    this.ws = null;
  }

  send(message: ClientMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.push(handler);
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler);
    };
  }
}
```

**Step 3: Create Svelte stores**

Create `frontend/src/lib/stores/session.ts`:
```typescript
import { writable } from 'svelte/store';
import type {
  Singer,
  Song,
  QueueItem,
  PlaybackState,
  SessionSettings,
  ServerMessage,
} from '$lib/types';
import { YokeSocket } from '$lib/ws';

// Stores
export const singers = writable<Singer[]>([]);
export const queue = writable<QueueItem[]>([]);
export const currentItem = writable<QueueItem | null>(null);
export const playback = writable<PlaybackState>({
  status: 'stopped',
  position_seconds: 0,
  pitch_shift: 0,
});
export const settings = writable<SessionSettings>({
  host_id: null,
  anyone_can_reorder: false,
});
export const searchResults = writable<Song[]>([]);
export const currentSinger = writable<Singer | null>(null);

// Notification events (consumed by display page)
export const notifications = writable<Array<{ id: string; text: string }>>([]);
export const screenMessages = writable<Array<{ id: string; name: string; text: string }>>([]);
export const showQr = writable(false);

// WebSocket singleton
let socket: YokeSocket | null = null;

export function getSocket(): YokeSocket {
  if (!socket) {
    socket = new YokeSocket();
  }
  return socket;
}

export function initSession(sock: YokeSocket): void {
  sock.onMessage((msg: ServerMessage) => {
    switch (msg.type) {
      case 'state':
        singers.set(msg.singers);
        queue.set(msg.queue);
        currentItem.set(msg.current);
        playback.set(msg.playback);
        settings.set(msg.settings);
        break;

      case 'singer_joined':
        singers.update((s) => [...s, msg.singer]);
        addNotification(`${msg.singer.name} joined the party!`);
        break;

      case 'song_queued':
        addNotification(`${msg.singer.name} queued "${msg.item.song.title}"`);
        break;

      case 'queue_updated':
        queue.set(msg.queue);
        break;

      case 'playback_updated':
        playback.set(msg.playback);
        break;

      case 'search_results':
        searchResults.set(msg.songs);
        break;

      case 'now_playing':
        currentItem.set(msg.item);
        addNotification(`Now playing: "${msg.item.song.title}" — ${msg.item.singer.name}`);
        break;

      case 'show_qr':
        showQr.set(true);
        setTimeout(() => showQr.set(false), 10000);
        break;

      case 'screen_message':
        screenMessages.update((msgs) => [
          ...msgs,
          { id: crypto.randomUUID(), name: msg.name, text: msg.text },
        ]);
        break;

      case 'download_progress':
        // Update queue item download progress (update status text)
        break;

      case 'up_next':
        addNotification(`${msg.singer.name}, you're up next!`);
        break;

      case 'error':
        console.error('Server error:', msg.message);
        break;
    }
  });
}

function addNotification(text: string): void {
  const id = crypto.randomUUID();
  notifications.update((n) => [...n, { id, text }]);
  setTimeout(() => {
    notifications.update((n) => n.filter((item) => item.id !== id));
  }, 4000);
}
```

**Step 4: Commit**

```bash
git add frontend/src/lib/
git commit -m "Add TypeScript types, WebSocket client, and Svelte stores"
```

---

## Phase 4: Control Page

### Task 11: Control Page — Name Entry and Layout Shell

**Files:**
- Modify: `frontend/src/routes/control/+page.svelte`
- Create: `frontend/src/lib/components/NameEntry.svelte`
- Create: `frontend/src/lib/components/TopBar.svelte`
- Create: `frontend/src/lib/components/PlaybackBar.svelte`

**Step 1: Implement NameEntry component**

Create `frontend/src/lib/components/NameEntry.svelte`:
```svelte
<script lang="ts">
  let name = $state('');
  let { onJoin }: { onJoin: (name: string) => void } = $props();

  function handleSubmit() {
    const trimmed = name.trim();
    if (trimmed) {
      onJoin(trimmed);
    }
  }
</script>

<div class="name-entry">
  <h1>Yoke</h1>
  <p>Enter your name to join</p>
  <form onsubmit={handleSubmit}>
    <input
      type="text"
      bind:value={name}
      placeholder="Your name"
      maxlength="30"
      autofocus
    />
    <button type="submit" disabled={!name.trim()}>Join</button>
  </form>
</div>

<style>
  .name-entry {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100dvh;
    gap: 1rem;
    padding: 1rem;
  }

  h1 {
    font-size: 3rem;
    margin: 0;
  }

  form {
    display: flex;
    gap: 0.5rem;
    width: 100%;
    max-width: 300px;
  }

  input {
    flex: 1;
    padding: 0.75rem;
    font-size: 1.1rem;
    border: 2px solid #333;
    border-radius: 8px;
  }

  button {
    padding: 0.75rem 1.5rem;
    font-size: 1.1rem;
    border: none;
    border-radius: 8px;
    background: #4f46e5;
    color: white;
    cursor: pointer;
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
```

**Step 2: Implement TopBar component**

Create `frontend/src/lib/components/TopBar.svelte`:
```svelte
<script lang="ts">
  import { getSocket } from '$lib/stores/session';

  let {
    singerName,
    activeTab,
    isHost,
    onTabChange,
  }: {
    singerName: string;
    activeTab: string;
    isHost: boolean;
    onTabChange: (tab: string) => void;
  } = $props();

  function showQr() {
    getSocket().send({ type: 'show_qr' });
  }

  const tabs = $derived(
    isHost
      ? ['Search', 'Queue', 'Settings']
      : ['Search', 'Queue']
  );
</script>

<div class="top-bar">
  <div class="header">
    <span class="app-name">Yoke</span>
    <span class="singer-name">{singerName}</span>
    <button class="qr-btn" onclick={showQr}>QR</button>
  </div>
  <div class="tabs">
    {#each tabs as tab}
      <button
        class="tab"
        class:active={activeTab === tab}
        onclick={() => onTabChange(tab)}
      >
        {tab}
      </button>
    {/each}
  </div>
</div>

<style>
  .top-bar {
    position: sticky;
    top: 0;
    background: #1a1a2e;
    z-index: 10;
  }

  .header {
    display: flex;
    align-items: center;
    padding: 0.5rem 1rem;
    gap: 0.5rem;
  }

  .app-name {
    font-weight: bold;
    font-size: 1.2rem;
  }

  .singer-name {
    flex: 1;
    text-align: right;
    opacity: 0.7;
  }

  .qr-btn {
    padding: 0.4rem 0.8rem;
    border: 1px solid #555;
    border-radius: 6px;
    background: transparent;
    color: white;
    cursor: pointer;
  }

  .tabs {
    display: flex;
    border-bottom: 1px solid #333;
  }

  .tab {
    flex: 1;
    padding: 0.6rem;
    border: none;
    background: transparent;
    color: #aaa;
    cursor: pointer;
    font-size: 1rem;
  }

  .tab.active {
    color: white;
    border-bottom: 2px solid #4f46e5;
  }
</style>
```

**Step 3: Implement PlaybackBar component**

Create `frontend/src/lib/components/PlaybackBar.svelte`:
```svelte
<script lang="ts">
  import { playback, currentItem, getSocket } from '$lib/stores/session';

  const socket = getSocket();

  function send(action: 'play' | 'pause' | 'stop' | 'skip' | 'restart') {
    socket.send({ type: 'playback', action });
  }

  function seek(e: Event) {
    const target = e.target as HTMLInputElement;
    socket.send({ type: 'seek', position_seconds: parseFloat(target.value) });
  }

  function setPitch(semitones: number) {
    socket.send({ type: 'pitch', semitones });
  }
</script>

<div class="playback-bar">
  {#if $currentItem}
    <div class="now-playing">
      <span class="title">{$currentItem.song.title}</span>
      <span class="singer">{$currentItem.singer.name}</span>
    </div>
  {/if}

  <div class="controls">
    <button onclick={() => send('restart')}>Restart</button>
    {#if $playback.status === 'playing'}
      <button onclick={() => send('pause')}>Pause</button>
    {:else}
      <button onclick={() => send('play')}>Play</button>
    {/if}
    <button onclick={() => send('stop')}>Stop</button>
    <button onclick={() => send('skip')}>Skip</button>
  </div>

  {#if $currentItem}
    <input
      type="range"
      class="seek-bar"
      min="0"
      max={$currentItem.song.duration_seconds}
      value={$playback.position_seconds}
      oninput={seek}
    />
  {/if}

  <div class="pitch-controls">
    <button onclick={() => setPitch($playback.pitch_shift - 1)} disabled={$playback.pitch_shift <= -6}>-</button>
    <span class="pitch-value">Pitch: {$playback.pitch_shift > 0 ? '+' : ''}{$playback.pitch_shift}</span>
    <button onclick={() => setPitch($playback.pitch_shift + 1)} disabled={$playback.pitch_shift >= 6}>+</button>
    {#if $playback.pitch_shift !== 0}
      <button class="reset" onclick={() => setPitch(0)}>Reset</button>
    {/if}
  </div>
</div>

<style>
  .playback-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #1a1a2e;
    border-top: 1px solid #333;
    padding: 0.5rem 1rem;
    z-index: 10;
  }

  .now-playing {
    display: flex;
    justify-content: space-between;
    padding-bottom: 0.3rem;
    font-size: 0.85rem;
    opacity: 0.8;
  }

  .controls {
    display: flex;
    gap: 0.5rem;
    justify-content: center;
    padding: 0.3rem 0;
  }

  .controls button {
    padding: 0.5rem 1rem;
    border: 1px solid #555;
    border-radius: 6px;
    background: transparent;
    color: white;
    cursor: pointer;
    font-size: 0.9rem;
  }

  .seek-bar {
    width: 100%;
    margin: 0.3rem 0;
  }

  .pitch-controls {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.3rem 0;
  }

  .pitch-controls button {
    padding: 0.3rem 0.8rem;
    border: 1px solid #555;
    border-radius: 6px;
    background: transparent;
    color: white;
    cursor: pointer;
  }

  .pitch-value {
    min-width: 4rem;
    text-align: center;
    font-size: 0.9rem;
  }

  .reset {
    font-size: 0.8rem;
  }
</style>
```

**Step 4: Wire up control page**

Update `frontend/src/routes/control/+page.svelte`:
```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import NameEntry from '$lib/components/NameEntry.svelte';
  import TopBar from '$lib/components/TopBar.svelte';
  import PlaybackBar from '$lib/components/PlaybackBar.svelte';
  import { getSocket, initSession, settings } from '$lib/stores/session';

  let joined = $state(false);
  let singerName = $state('');
  let singerId = $state('');
  let activeTab = $state('Search');

  const socket = getSocket();

  onMount(() => {
    // Check localStorage for existing session
    const savedName = localStorage.getItem('yoke_name');
    const savedId = localStorage.getItem('yoke_singer_id');
    if (savedName && savedId) {
      singerName = savedName;
      singerId = savedId;
      joined = true;
      socket.connect();
      initSession(socket);
      socket.send({ type: 'join', name: singerName });
    }

    return () => socket.disconnect();
  });

  function handleJoin(name: string) {
    singerName = name;
    localStorage.setItem('yoke_name', name);
    joined = true;
    socket.connect();
    initSession(socket);
    socket.send({ type: 'join', name });
  }

  const isHost = $derived($settings.host_id === singerId);
</script>

<svelte:head>
  <title>Yoke — Control</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
</svelte:head>

{#if !joined}
  <NameEntry onJoin={handleJoin} />
{:else}
  <div class="app">
    <TopBar {singerName} {activeTab} {isHost} onTabChange={(tab) => (activeTab = tab)} />

    <main class="content">
      {#if activeTab === 'Search'}
        <p>Search tab (Task 12)</p>
      {:else if activeTab === 'Queue'}
        <p>Queue tab (Task 13)</p>
      {:else if activeTab === 'Settings'}
        <p>Settings tab (Task 14)</p>
      {/if}
    </main>

    <PlaybackBar />
  </div>
{/if}

<style>
  :global(body) {
    margin: 0;
    background: #0f0f23;
    color: white;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }

  .app {
    min-height: 100dvh;
    padding-bottom: 10rem;
  }

  .content {
    padding: 1rem;
  }
</style>
```

**Step 5: Commit**

```bash
git add frontend/src/
git commit -m "Add control page shell with name entry, tabs, and playback bar"
```

---

### Task 12: Control Page — Search Tab

**Files:**
- Create: `frontend/src/lib/components/SearchTab.svelte`
- Modify: `frontend/src/routes/control/+page.svelte` (replace placeholder)

**Step 1: Implement SearchTab component**

Create `frontend/src/lib/components/SearchTab.svelte`:
```svelte
<script lang="ts">
  import { searchResults, getSocket } from '$lib/stores/session';
  import type { Song } from '$lib/types';

  const socket = getSocket();
  let query = $state('');
  let searching = $state(false);

  function handleSearch() {
    if (!query.trim()) return;
    searching = true;
    socket.send({ type: 'search', query: query.trim() });
    // searching will be cleared when results arrive
    const unsub = searchResults.subscribe(() => {
      searching = false;
      unsub();
    });
  }

  function queueSong(song: Song) {
    socket.send({ type: 'queue_song', video_id: song.video_id });
  }

  function formatDuration(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  }
</script>

<div class="search-tab">
  <form class="search-form" onsubmit={handleSearch}>
    <input
      type="text"
      bind:value={query}
      placeholder="Search for a song..."
      autofocus
    />
    <button type="submit" disabled={!query.trim() || searching}>
      {searching ? '...' : 'Search'}
    </button>
  </form>

  <div class="results">
    {#each $searchResults as song (song.video_id)}
      <button class="song-card" onclick={() => queueSong(song)}>
        <img src={song.thumbnail_url} alt="" class="thumb" />
        <div class="info">
          <span class="title">{song.title}</span>
          <span class="duration">{formatDuration(song.duration_seconds)}</span>
        </div>
        {#if song.cached}
          <span class="cached-badge">Ready</span>
        {/if}
      </button>
    {/each}
  </div>
</div>

<style>
  .search-form {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .search-form input {
    flex: 1;
    padding: 0.75rem;
    font-size: 1rem;
    border: 2px solid #333;
    border-radius: 8px;
    background: #1a1a2e;
    color: white;
  }

  .search-form button {
    padding: 0.75rem 1.2rem;
    border: none;
    border-radius: 8px;
    background: #4f46e5;
    color: white;
    cursor: pointer;
  }

  .search-form button:disabled {
    opacity: 0.5;
  }

  .song-card {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #333;
    border-radius: 8px;
    background: #1a1a2e;
    color: white;
    cursor: pointer;
    text-align: left;
    margin-bottom: 0.5rem;
  }

  .thumb {
    width: 80px;
    height: 60px;
    object-fit: cover;
    border-radius: 4px;
  }

  .info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .title {
    font-size: 0.9rem;
  }

  .duration {
    font-size: 0.8rem;
    opacity: 0.6;
  }

  .cached-badge {
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    background: #22c55e;
    color: black;
    font-size: 0.75rem;
    font-weight: bold;
  }
</style>
```

**Step 2: Wire into control page**

Update the `{#if activeTab === 'Search'}` block in `control/+page.svelte`:
```svelte
{#if activeTab === 'Search'}
  <SearchTab />
```

Add the import at the top:
```svelte
import SearchTab from '$lib/components/SearchTab.svelte';
```

**Step 3: Commit**

```bash
git add frontend/src/
git commit -m "Add search tab with YouTube search and cached badges"
```

---

### Task 13: Control Page — Queue Tab

**Files:**
- Create: `frontend/src/lib/components/QueueTab.svelte`
- Modify: `frontend/src/routes/control/+page.svelte` (replace placeholder)

**Step 1: Implement QueueTab component**

Create `frontend/src/lib/components/QueueTab.svelte`:
```svelte
<script lang="ts">
  import { queue, currentItem, settings, getSocket } from '$lib/stores/session';
  import type { QueueItem } from '$lib/types';

  let {
    singerId,
    isHost,
  }: {
    singerId: string;
    isHost: boolean;
  } = $props();

  const socket = getSocket();

  const canReorder = $derived(isHost || $settings.anyone_can_reorder);

  function remove(itemId: string) {
    socket.send({ type: 'remove_from_queue', item_id: itemId });
  }

  function canRemove(item: QueueItem): boolean {
    return isHost || item.singer.id === singerId;
  }

  // Simple drag reorder state
  let dragIndex = $state<number | null>(null);

  function dragStart(index: number) {
    if (!canReorder) return;
    dragIndex = index;
  }

  function drop(index: number) {
    if (dragIndex === null || dragIndex === index) return;
    const items = [...$queue];
    const [moved] = items.splice(dragIndex, 1);
    items.splice(index, 0, moved);
    socket.send({ type: 'reorder_queue', item_ids: items.map((i) => i.id) });
    dragIndex = null;
  }

  function statusLabel(status: string): string {
    switch (status) {
      case 'waiting': return 'Waiting';
      case 'downloading': return 'Downloading...';
      case 'ready': return 'Ready';
      case 'playing': return 'Playing';
      default: return status;
    }
  }
</script>

<div class="queue-tab">
  {#if $currentItem}
    <div class="current">
      <span class="label">Now playing</span>
      <span class="title">{$currentItem.song.title}</span>
      <span class="singer">{$currentItem.singer.name}</span>
    </div>
  {/if}

  {#if $queue.length === 0}
    <p class="empty">Queue is empty. Search for songs to add!</p>
  {:else}
    <div class="queue-list">
      {#each $queue as item, index (item.id)}
        <div
          class="queue-item"
          draggable={canReorder}
          ondragstart={() => dragStart(index)}
          ondragover|preventDefault={() => {}}
          ondrop={() => drop(index)}
        >
          {#if canReorder}
            <span class="drag-handle">::</span>
          {/if}
          <div class="item-info">
            <span class="title">{item.song.title}</span>
            <span class="meta">{item.singer.name} — {statusLabel(item.status)}</span>
          </div>
          {#if canRemove(item)}
            <button class="remove-btn" onclick={() => remove(item.id)}>X</button>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .current {
    background: #4f46e520;
    border: 1px solid #4f46e5;
    border-radius: 8px;
    padding: 0.75rem;
    margin-bottom: 1rem;
  }

  .current .label {
    font-size: 0.75rem;
    text-transform: uppercase;
    opacity: 0.6;
    display: block;
  }

  .current .title {
    display: block;
    font-weight: bold;
  }

  .current .singer {
    font-size: 0.85rem;
    opacity: 0.7;
  }

  .empty {
    text-align: center;
    opacity: 0.5;
    padding: 2rem;
  }

  .queue-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.6rem;
    border: 1px solid #333;
    border-radius: 6px;
    margin-bottom: 0.4rem;
  }

  .drag-handle {
    cursor: grab;
    opacity: 0.4;
    font-size: 1.2rem;
  }

  .item-info {
    flex: 1;
  }

  .item-info .title {
    display: block;
    font-size: 0.9rem;
  }

  .item-info .meta {
    font-size: 0.8rem;
    opacity: 0.6;
  }

  .remove-btn {
    padding: 0.3rem 0.6rem;
    border: 1px solid #ef4444;
    border-radius: 4px;
    background: transparent;
    color: #ef4444;
    cursor: pointer;
  }
</style>
```

**Step 2: Wire into control page**

Update the `{#if activeTab === 'Queue'}` block:
```svelte
{:else if activeTab === 'Queue'}
  <QueueTab {singerId} {isHost} />
```

Add import:
```svelte
import QueueTab from '$lib/components/QueueTab.svelte';
```

**Step 3: Commit**

```bash
git add frontend/src/
git commit -m "Add queue tab with drag reorder and remove controls"
```

---

### Task 14: Control Page — Settings Tab and Screen Message Input

**Files:**
- Create: `frontend/src/lib/components/SettingsTab.svelte`
- Create: `frontend/src/lib/components/MessageInput.svelte`
- Modify: `frontend/src/routes/control/+page.svelte`

**Step 1: Implement SettingsTab**

Create `frontend/src/lib/components/SettingsTab.svelte`:
```svelte
<script lang="ts">
  import { settings, getSocket } from '$lib/stores/session';

  const socket = getSocket();

  function toggleReorder() {
    socket.send({
      type: 'update_setting',
      key: 'anyone_can_reorder',
      value: !$settings.anyone_can_reorder,
    });
  }
</script>

<div class="settings-tab">
  <h2>Settings</h2>

  <label class="setting">
    <input
      type="checkbox"
      checked={$settings.anyone_can_reorder}
      onchange={toggleReorder}
    />
    <span>Allow everyone to reorder the queue</span>
  </label>
</div>

<style>
  h2 {
    margin-top: 0;
  }

  .setting {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    border: 1px solid #333;
    border-radius: 8px;
    cursor: pointer;
  }

  input[type='checkbox'] {
    width: 1.2rem;
    height: 1.2rem;
  }
</style>
```

**Step 2: Implement MessageInput**

Create `frontend/src/lib/components/MessageInput.svelte`:
```svelte
<script lang="ts">
  import { getSocket } from '$lib/stores/session';

  const socket = getSocket();
  let text = $state('');

  function send() {
    if (!text.trim()) return;
    socket.send({ type: 'screen_message', text: text.trim() });
    text = '';
  }
</script>

<form class="message-input" onsubmit={send}>
  <input
    type="text"
    bind:value={text}
    placeholder="Send a message to the screen..."
    maxlength="100"
  />
  <button type="submit" disabled={!text.trim()}>Send</button>
</form>

<style>
  .message-input {
    display: flex;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: #1a1a2e;
    border-top: 1px solid #333;
    position: fixed;
    bottom: 10rem;
    left: 0;
    right: 0;
  }

  input {
    flex: 1;
    padding: 0.5rem;
    border: 1px solid #333;
    border-radius: 6px;
    background: #0f0f23;
    color: white;
  }

  button {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 6px;
    background: #4f46e5;
    color: white;
    cursor: pointer;
  }

  button:disabled {
    opacity: 0.5;
  }
</style>
```

**Step 3: Wire into control page**

Update settings tab placeholder and add MessageInput above PlaybackBar:
```svelte
{:else if activeTab === 'Settings'}
  <SettingsTab />
```

Add `<MessageInput />` between `</main>` and `<PlaybackBar />`.

Add imports:
```svelte
import SettingsTab from '$lib/components/SettingsTab.svelte';
import MessageInput from '$lib/components/MessageInput.svelte';
```

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "Add settings tab and screen message input"
```

---

## Phase 5: Display Page

### Task 15: Display Page — Video Player with Pitch Shifting

**Files:**
- Modify: `frontend/src/routes/display/+page.svelte`
- Create: `frontend/src/lib/components/VideoPlayer.svelte`
- Create: `frontend/src/lib/audio/pitch-shifter.ts`

**Step 1: Implement pitch shifter using Web Audio API**

Create `frontend/src/lib/audio/pitch-shifter.ts`:
```typescript
/**
 * Real-time pitch shifter using Web Audio API.
 * Uses playbackRate on a MediaElementSource combined with
 * a playback rate adjustment to shift pitch by semitones.
 *
 * Approach: Change playbackRate to shift pitch (2^(semitones/12)),
 * which also changes speed. To compensate, we'd need a time-stretcher.
 * For simplicity, we use the SoundTouchJS library or accept the speed change.
 *
 * Alternative: Use AudioWorklet with a phase vocoder for pitch-only shift.
 * We'll start with the simple playbackRate approach and can upgrade later.
 */
export class PitchShifter {
  private ctx: AudioContext | null = null;
  private source: MediaElementAudioSourceNode | null = null;
  private videoElement: HTMLVideoElement | null = null;

  async connect(video: HTMLVideoElement): Promise<void> {
    this.videoElement = video;
    this.ctx = new AudioContext();
    this.source = this.ctx.createMediaElementSource(video);
    this.source.connect(this.ctx.destination);
  }

  setPitch(semitones: number): void {
    if (!this.videoElement) return;
    // Shift pitch by changing playback rate
    // 2^(semitones/12) gives the frequency ratio
    const rate = Math.pow(2, semitones / 12);
    this.videoElement.playbackRate = rate;
  }

  disconnect(): void {
    this.source?.disconnect();
    this.ctx?.close();
    this.source = null;
    this.ctx = null;
    this.videoElement = null;
  }
}
```

> **Note:** This simple approach changes both pitch and speed. For pitch-only shifting (preserving speed), install `soundtouchjs` and replace the implementation:
> ```bash
> cd frontend && pnpm add soundtouchjs
> ```
> Then use SoundTouch's `PitchShifter` class routed through AudioContext. This can be done as a follow-up enhancement.

**Step 2: Implement VideoPlayer component**

Create `frontend/src/lib/components/VideoPlayer.svelte`:
```svelte
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { PitchShifter } from '$lib/audio/pitch-shifter';
  import { playback, currentItem, getSocket } from '$lib/stores/session';

  let videoEl: HTMLVideoElement;
  let pitchShifter: PitchShifter;
  let positionInterval: ReturnType<typeof setInterval>;
  const socket = getSocket();

  onMount(() => {
    pitchShifter = new PitchShifter();

    // Report position to server periodically
    positionInterval = setInterval(() => {
      if (videoEl && !videoEl.paused) {
        socket.send({
          type: 'position_update',
          position_seconds: videoEl.currentTime,
        });
      }
    }, 1000);
  });

  onDestroy(() => {
    clearInterval(positionInterval);
    pitchShifter?.disconnect();
  });

  // React to current item changes — load new video
  $effect(() => {
    const item = $currentItem;
    if (item && videoEl) {
      const videoUrl = `/videos/${item.song.video_id}`;
      videoEl.src = videoUrl;
      videoEl.load();
      videoEl.play().then(() => {
        if (!pitchShifter.connected) {
          pitchShifter.connect(videoEl);
        }
        pitchShifter.setPitch($playback.pitch_shift);
      });
    }
  });

  // React to playback state changes
  $effect(() => {
    const pb = $playback;
    if (!videoEl) return;

    if (pb.status === 'playing' && videoEl.paused) {
      videoEl.play();
    } else if (pb.status === 'paused' && !videoEl.paused) {
      videoEl.pause();
    } else if (pb.status === 'stopped') {
      videoEl.pause();
      videoEl.currentTime = 0;
    }

    pitchShifter?.setPitch(pb.pitch_shift);
  });

  // React to seek commands
  $effect(() => {
    const pb = $playback;
    if (videoEl && Math.abs(videoEl.currentTime - pb.position_seconds) > 2) {
      videoEl.currentTime = pb.position_seconds;
    }
  });

  function onEnded() {
    socket.send({ type: 'playback', action: 'skip' });
  }
</script>

<video
  bind:this={videoEl}
  class="video-player"
  onended={onEnded}
  playsinline
>
</video>

<style>
  .video-player {
    width: 100vw;
    height: 100vh;
    object-fit: contain;
    background: black;
  }
</style>
```

**Step 3: Commit**

```bash
git add frontend/src/
git commit -m "Add video player with Web Audio pitch shifting"
```

---

### Task 16: Display Page — Notifications, Floating Messages, QR Overlay

**Files:**
- Create: `frontend/src/lib/components/Notifications.svelte`
- Create: `frontend/src/lib/components/FloatingMessages.svelte`
- Create: `frontend/src/lib/components/QrOverlay.svelte`
- Create: `frontend/src/lib/components/IdleScreen.svelte`
- Modify: `frontend/src/routes/display/+page.svelte`

**Step 1: Implement Notifications component (sliding from right)**

Create `frontend/src/lib/components/Notifications.svelte`:
```svelte
<script lang="ts">
  import { notifications } from '$lib/stores/session';
</script>

<div class="notifications">
  {#each $notifications as notif (notif.id)}
    <div class="notification" class:enter={true}>
      {notif.text}
    </div>
  {/each}
</div>

<style>
  .notifications {
    position: fixed;
    top: 1rem;
    right: 0;
    z-index: 100;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    pointer-events: none;
  }

  .notification {
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 0.75rem 1.5rem;
    border-radius: 8px 0 0 8px;
    font-size: 1.2rem;
    animation: slideIn 0.3s ease-out, slideOut 0.3s ease-in 3.5s forwards;
    white-space: nowrap;
  }

  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  @keyframes slideOut {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(100%);
      opacity: 0;
    }
  }
</style>
```

**Step 2: Implement FloatingMessages (Niconico-style)**

Create `frontend/src/lib/components/FloatingMessages.svelte`:
```svelte
<script lang="ts">
  import { screenMessages } from '$lib/stores/session';

  // Clean up old messages after animation
  $effect(() => {
    if ($screenMessages.length > 0) {
      const timeout = setTimeout(() => {
        screenMessages.update((msgs) => msgs.slice(1));
      }, 6000);
      return () => clearTimeout(timeout);
    }
  });
</script>

<div class="floating-messages">
  {#each $screenMessages as msg (msg.id)}
    {@const left = 10 + Math.random() * 60}
    <div class="float-msg" style="left: {left}%">
      <span class="name">{msg.name}:</span> {msg.text}
    </div>
  {/each}
</div>

<style>
  .floating-messages {
    position: fixed;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
    z-index: 50;
  }

  .float-msg {
    position: absolute;
    bottom: -2rem;
    font-size: 1.5rem;
    color: white;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8);
    white-space: nowrap;
    animation: floatUp 5s linear forwards;
  }

  .name {
    font-weight: bold;
  }

  @keyframes floatUp {
    from {
      transform: translateY(0);
      opacity: 1;
    }
    to {
      transform: translateY(-100vh);
      opacity: 0;
    }
  }
</style>
```

**Step 3: Implement QR overlay**

Create `frontend/src/lib/components/QrOverlay.svelte`:
```svelte
<script lang="ts">
  import { showQr } from '$lib/stores/session';

  // Generate QR code URL using a public API-free approach:
  // We'll use a simple canvas-based QR library. Install: pnpm add qrcode
  // For now, display the URL as text. QR generation can be added with:
  // pnpm add qrcode && import QRCode from 'qrcode'
  const controlUrl = $derived(
    typeof window !== 'undefined'
      ? `${window.location.protocol}//${window.location.hostname}:${window.location.port}/control`
      : ''
  );
</script>

{#if $showQr}
  <div class="qr-overlay">
    <div class="qr-content">
      <p class="label">Scan to join!</p>
      <div class="url">{controlUrl}</div>
    </div>
  </div>
{/if}

<style>
  .qr-overlay {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    z-index: 200;
    animation: fadeIn 0.3s ease-out, fadeOut 0.3s ease-in 9.5s forwards;
  }

  .qr-content {
    background: white;
    color: black;
    padding: 1.5rem;
    border-radius: 12px;
    text-align: center;
  }

  .label {
    margin: 0 0 0.5rem;
    font-weight: bold;
    font-size: 1.1rem;
  }

  .url {
    font-family: monospace;
    font-size: 0.9rem;
    word-break: break-all;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: scale(0.9); }
    to { opacity: 1; transform: scale(1); }
  }

  @keyframes fadeOut {
    from { opacity: 1; }
    to { opacity: 0; }
  }
</style>
```

> **Follow-up:** Install `qrcode` package and render an actual QR code canvas instead of just the URL text.

**Step 4: Implement IdleScreen**

Create `frontend/src/lib/components/IdleScreen.svelte`:
```svelte
<script lang="ts">
  const controlUrl = $derived(
    typeof window !== 'undefined'
      ? `${window.location.protocol}//${window.location.hostname}:${window.location.port}/control`
      : ''
  );
</script>

<div class="idle-screen">
  <h1>Yoke</h1>
  <p>Scan to join or visit:</p>
  <p class="url">{controlUrl}</p>
</div>

<style>
  .idle-screen {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    background: #0f0f23;
    color: white;
  }

  h1 {
    font-size: 5rem;
    margin-bottom: 1rem;
  }

  .url {
    font-family: monospace;
    font-size: 1.3rem;
    background: rgba(255, 255, 255, 0.1);
    padding: 0.5rem 1rem;
    border-radius: 8px;
  }
</style>
```

**Step 5: Wire up display page**

Update `frontend/src/routes/display/+page.svelte`:
```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import VideoPlayer from '$lib/components/VideoPlayer.svelte';
  import Notifications from '$lib/components/Notifications.svelte';
  import FloatingMessages from '$lib/components/FloatingMessages.svelte';
  import QrOverlay from '$lib/components/QrOverlay.svelte';
  import IdleScreen from '$lib/components/IdleScreen.svelte';
  import { getSocket, initSession, currentItem } from '$lib/stores/session';

  const socket = getSocket();

  onMount(() => {
    socket.connect();
    initSession(socket);
    // Display page joins as a silent observer (no singer name)
    // It just listens for state updates
    return () => socket.disconnect();
  });
</script>

<svelte:head>
  <title>Yoke — Display</title>
</svelte:head>

<div class="display">
  {#if $currentItem}
    <VideoPlayer />
  {:else}
    <IdleScreen />
  {/if}

  <Notifications />
  <FloatingMessages />
  <QrOverlay />
</div>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    overflow: hidden;
    background: black;
    color: white;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }

  .display {
    width: 100vw;
    height: 100vh;
    position: relative;
  }
</style>
```

**Step 6: Commit**

```bash
git add frontend/src/
git commit -m "Add display page with notifications, floating messages, and QR overlay"
```

---

## Phase 6: Deployment

### Task 17: Docker Compose Setup

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`

**Step 1: Create Dockerfile**

Create `Dockerfile` at project root:
```dockerfile
# Stage 1: Build frontend
FROM node:18-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# Stage 2: Python backend
FROM python:3.13-slim AS runtime
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python deps
COPY backend/pyproject.toml backend/uv.lock* ./backend/
WORKDIR /app/backend
RUN uv sync --no-dev

# Copy backend source
COPY backend/src/ ./src/

# Copy built frontend
COPY --from=frontend-build /app/frontend/build /app/static

WORKDIR /app
ENV KARAOKE_VIDEO_DIR=/app/data/videos
EXPOSE 8000

CMD ["uv", "run", "--directory", "backend", "uvicorn", "yoke.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Create docker-compose.yml**

Create `docker-compose.yml`:
```yaml
services:
  app:
    build: .
    ports:
      - "${KARAOKE_PORT:-8000}:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - KARAOKE_VIDEO_DIR=/app/data/videos
      - KARAOKE_MAX_CONCURRENT_DOWNLOADS=${KARAOKE_MAX_CONCURRENT_DOWNLOADS:-2}
    volumes:
      - video-data:/app/data/videos
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

volumes:
  video-data:
  redis-data:
```

**Step 3: Create .env.example**

Create `.env.example`:
```
KARAOKE_PORT=8000
KARAOKE_MAX_CONCURRENT_DOWNLOADS=2
KARAOKE_VIDEO_DIR=./data/videos
REDIS_URL=redis://localhost:6379
```

**Step 4: Update main.py to serve static frontend in production**

Add to `backend/src/yoke/main.py`, after all route definitions:
```python
import os
# Serve frontend static files in production
static_dir = os.environ.get("STATIC_DIR", "/app/static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
```

**Step 5: Verify Docker build**

Run: `cd /home/winston/code/karaoke && docker compose build`
Expected: Builds successfully

**Step 6: Verify Docker Compose runs**

Run: `docker compose up -d`
Verify: `curl http://localhost:8000/health` returns `{"status":"ok"}`
Run: `docker compose down`

**Step 7: Commit**

```bash
git add Dockerfile docker-compose.yml .env.example
git commit -m "Add Docker Compose setup with Redis and video volume"
```

---

## Follow-up Enhancements (not in scope for initial build)

These are noted for future sessions:

1. **Proper pitch shifting** — Replace simple `playbackRate` with SoundTouchJS phase vocoder for pitch-only shift (preserving tempo)
2. **QR code rendering** — Install `qrcode` package and render actual QR codes on the display page
3. **Download progress in queue** — Show percentage in the queue item status badge
4. **"Up next" notification** — Detect when current song is ~30s from ending and notify the next singer
5. **Reconnection handling** — Store singer ID in localStorage and rejoin with same identity on reconnect
6. **Mobile-optimized CSS** — Polish responsive layout, touch interactions, safe areas

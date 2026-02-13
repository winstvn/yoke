# Yoke -- Karaoke Web App

## Project overview

Yoke is a real-time karaoke web app. A FastAPI backend handles WebSocket communication, YouTube search/download, and Redis-backed persistence. A SvelteKit frontend provides a phone control UI and a TV display UI.

## Tech stack

- **Backend:** Python 3.13, FastAPI, Redis (async), yt-dlp, Pydantic
- **Frontend:** SvelteKit 2, Svelte 5, TypeScript, Vite
- **Infrastructure:** Docker Compose, Redis 7

## Package management

- Python: use `uv` (not pip). Run `uv sync` from `backend/`.
- Node: use `pnpm`. Run `pnpm install` from `frontend/`.

## Running the app

```bash
# Full stack
docker compose up --build

# Backend dev
cd backend && uv run uvicorn yoke.main:app --reload

# Frontend dev
cd frontend && pnpm dev
```

## Running tests

```bash
cd backend && uv run pytest
```

Tests use `fakeredis` -- no Redis needed. `asyncio_mode = "auto"` is set in `pyproject.toml`.

## Architecture

### Backend (`backend/src/yoke/`)

- `main.py` -- FastAPI app entry point, lifespan (Redis + downloader init), static file serving
- `router.py` -- `MessageRouter` dispatches WebSocket messages to handler methods by `type` field
- `session.py` -- `SessionManager` with business logic for join, queue, permissions
- `redis_store.py` -- `RedisStore` async persistence layer (keys prefixed `yoke:`)
- `models.py` -- Pydantic models: `Singer`, `Song`, `QueueItem`, `PlaybackState`, `SessionState`, `SessionSettings`
- `ws.py` -- `ConnectionManager` tracks active WebSocket connections
- `youtube.py` -- yt-dlp wrapper for search
- `downloader.py` -- `VideoDownloader` with semaphore-controlled concurrent downloads
- `config.py` -- Environment variable configuration

### Frontend (`frontend/src/`)

- `routes/control/+page.svelte` -- Phone control UI (search, queue, settings tabs)
- `routes/display/+page.svelte` -- TV display page (video player, overlays)
- `lib/ws.ts` -- `YokeSocket` WebSocket client with auto-reconnect
- `lib/stores/session.ts` -- Svelte stores for session state
- `lib/audio/pitch-shifter.ts` -- Web Audio API pitch shifting
- `lib/components/` -- Reusable Svelte components

### Communication

Single WebSocket endpoint at `/ws`. All messages are JSON with a `type` field.

Client commands: `join`, `search`, `queue_song`, `remove_from_queue`, `reorder_queue`, `playback`, `seek`, `pitch`, `update_setting`, `show_qr`, `screen_message`, `position_update`

Server events: `state`, `singer_joined`, `song_queued`, `queue_updated`, `playback_updated`, `download_progress`, `search_results`, `show_qr`, `screen_message`, `now_playing`, `up_next`, `settings_updated`, `download_error`, `position_update`, `error`

### Data flow

1. Frontend SvelteKit builds to static files via `adapter-static`
2. FastAPI serves the static build and handles `/ws` and `/videos/{id}` routes
3. Redis stores session state (singers, queue, current song, playback, settings)
4. Videos are cached in `data/videos/` on disk

## Conventions

- Backend follows standard Python async patterns with FastAPI
- Frontend uses Svelte 5 runes and reactive stores
- SSR is disabled -- the frontend is a pure SPA
- Tests mirror the source structure (`test_router.py` tests `router.py`, etc.)

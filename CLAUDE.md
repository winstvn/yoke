# Yoke -- Karaoke Web App

## Project overview

Yoke is a real-time karaoke web app. A FastAPI backend handles WebSocket communication, YouTube search/download, and Redis-backed persistence. A SvelteKit frontend provides a phone control UI and a TV display UI.

## Tech stack

- **Backend:** Python 3.13, FastAPI, Redis (async), yt-dlp, Pydantic
- **Frontend:** SvelteKit 2, Svelte 5, TypeScript, Vite
- **Infrastructure:** Docker Compose, Redis 8, ffmpeg

## Package management

- Python: use `uv` (not pip). Run `uv sync` from `backend/`.
- Node: use `pnpm`. Run `pnpm install` from `frontend/`.

## Running the app

```bash
# Full stack, single container serving the built frontend
docker compose up --build

# Full stack in dev mode: separate backend/frontend containers,
# uvicorn --reload and vite dev with the source mounted
docker compose -f docker-compose.dev.yml up --build

# Backend dev
cd backend && uv run uvicorn yoke.main:app --reload

# Frontend dev
cd frontend && pnpm dev
```

In dev mode Vite serves the frontend on `5173` and proxies `/api`, `/ws` and
`/videos` to the backend on `8000`. `docker-compose.dev.yml` only mounts
`backend/src` and `backend/tests`, so a dependency change needs an image rebuild.

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
- `key_analyzer.py` -- librosa key detection, run once per song after download
- `loudness.py` -- ffmpeg `loudnorm` loudness measurement (LUFS + true peak)
- `config.py` -- Environment variable configuration
- `logging.py` -- Filters `/health` polling out of the uvicorn access log

### Frontend (`frontend/src/`)

- `routes/control/+page.svelte` -- Phone control UI (search, queue, settings tabs)
- `routes/display/+page.svelte` -- TV display page (video player, overlays)
- `lib/ws.ts` -- `YokeSocket` WebSocket client with auto-reconnect
- `lib/types.ts` -- Shared models plus the `ClientMessage`/`ServerMessage` contract
- `lib/stores/session.ts` -- Svelte stores for session state
- `lib/audio/pitch-shifter.ts` -- Web Audio API pitch shifting, owns the output gain node
- `lib/audio/loudness.ts` -- Normalization gain maths, mirrors `loudness.py` constants
- `lib/control-url.ts` -- Resolves the LAN control URL for the QR codes
- `lib/components/` -- Reusable Svelte components

### Communication

Single WebSocket endpoint at `/ws`. All messages are JSON with a `type` field.

Client commands: `join`, `search`, `queue_song`, `remove_from_queue`, `reorder_queue`, `playback`, `seek`, `pitch`, `song_ended`, `update_setting`, `show_qr`, `screen_message`, `position_update`

Server events: `state`, `singer_joined`, `song_queued`, `queue_updated`, `playback_updated`, `download_progress`, `search_results`, `show_qr`, `screen_message`, `now_playing`, `settings_updated`, `download_error`, `position_update`, `error`

`song_ended` is the display reporting that its `<video>` finished or failed to
load. It is deliberately ungated: the display never joins as a singer, so it
cannot use the permission-checked `playback` action.

### Permissions

`SessionManager` has three rules, all in `session.py`:

- **Host only** -- the settings under `_HOST_ONLY_SETTINGS`. The first singer to
  join becomes host.
- **`can_control_playback`** -- play/pause/skip/previous, seek and pitch.
- **`can_control_volume`** -- the `volume` setting.

The last two relax the same base rule (host or current singer) via the
`anyone_can_control_playback` and `anyone_can_control_volume` settings. They are
independent: neither toggle opens the other's domain.

`update_setting` only accepts keys listed in `session.py` and validates values
through `SessionSettings`, so clients cannot reassign `host_id` or set arbitrary
attributes.

### Data flow

1. Frontend SvelteKit builds to static files via `adapter-static`
2. FastAPI serves the static build and handles `/ws` and `/videos/{id}` routes
3. Redis stores session state (singers, queue, current song, playback, settings)
4. Videos are cached in `data/videos/` on disk
5. After a video lands, `router._analyze_song` fills in the song's key and
   loudness. Songs already on disk are analysed on queue instead, since they
   skip the download path

`QueueItem` embeds its own copy of `Song`, so anything written to a song after it
is queued must also be pushed onto the queue item (`update_queue_item(song=...)`)
or the display will not see it.

Loudness normalization is applied at playback, not baked into the file: the
display turns the stored LUFS into gain on its audio graph. That keeps the files
untouched and lets the volume setting take effect immediately.

## Conventions

- Backend follows standard Python async patterns with FastAPI
- Frontend uses Svelte 5 runes and reactive stores
- SSR is disabled -- the frontend is a pure SPA
- Tests mirror the source structure (`test_router.py` tests `router.py`, etc.)
- **Do not pin `yt-dlp` to a release series.** It has to track YouTube's
  extractor changes; a pinned version eventually fails every download with
  HTTP 403. Only a lower bound belongs in `pyproject.toml`
- `ffmpeg` is in the backend image for yt-dlp, and loudness measurement reuses
  it -- no separate dependency

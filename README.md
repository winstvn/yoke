# Yoke

A web-based karaoke app for group sessions. Users join from their phones to search YouTube, queue songs, and control playback, while a display page drives a TV or projector with full-screen video, floating chat messages, and QR codes for easy invites.

## Features

- **YouTube search & queueing** -- find songs, add them to a shared queue, and auto-download videos in the background
- **Real-time sync** -- WebSocket-driven state keeps all connected clients in lockstep
- **Pitch shifting** -- transpose vocals up or down 6 semitones via the Web Audio API
- **Mobile control page** -- phone-friendly UI with tabs for search, queue, and settings
- **TV display page** -- full-screen video player with Niconico-style floating messages, notifications, and QR overlay
- **Persistence** -- Redis-backed session state survives server restarts
- **Host permissions** -- first user becomes host; configurable permissions for queue reordering

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, Redis, yt-dlp |
| Frontend | SvelteKit 2, Svelte 5, TypeScript, Vite |
| Infrastructure | Docker Compose, Redis 7 |

## Quick start

### Docker Compose (recommended)

```bash
cp .env.example .env      # adjust if needed
KARAOKE_EXTERNAL_IP=$(ipconfig getifaddr en0) docker compose up --build
```

The app will be available at `http://localhost:8000`. Open `/display` on a TV — it shows a QR code and URL that phones on the same network can use to join.

The `KARAOKE_EXTERNAL_IP` variable tells the app your machine's LAN IP so the QR code points to the right address. On macOS, `ipconfig getifaddr en0` returns your Wi-Fi IP. On Linux, use `hostname -I | awk '{print $1}'` instead.

### Local development

**Prerequisites:** Python 3.13+, Node.js 20+, pnpm, Redis, ffmpeg

Start Redis:

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

Backend:

```bash
cd backend
uv sync
uv run uvicorn yoke.main:app --reload
```

Frontend (in a separate terminal):

```bash
cd frontend
pnpm install
pnpm dev
```

The Vite dev server proxies API and WebSocket requests to the backend at `localhost:8000`. The dev server binds to all interfaces (`0.0.0.0`), so phones on the same network can access it directly.

### Running tests

```bash
cd backend
uv run pytest
```

Tests use `fakeredis` so no running Redis instance is required.

## Configuration

Environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `KARAOKE_PORT` | `8000` | Server port |
| `KARAOKE_VIDEO_DIR` | `./data/videos` | Directory for cached video files |
| `KARAOKE_MAX_CONCURRENT_DOWNLOADS` | `2` | Max simultaneous yt-dlp downloads |
| `KARAOKE_EXTERNAL_IP` | *(auto-detected)* | LAN IP shown in QR codes. Set this when running in Docker so phones can connect. |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |

## Project structure

```
backend/
  src/yoke/
    main.py          # FastAPI app, lifespan, static file serving
    router.py        # WebSocket message dispatcher
    session.py       # Business logic (queue, permissions)
    redis_store.py   # Persistence layer
    models.py        # Pydantic data models
    youtube.py       # yt-dlp search wrapper
    downloader.py    # Video download manager
    ws.py            # WebSocket connection manager
    config.py        # Environment config
  tests/             # pytest suite
frontend/
  src/
    routes/
      control/       # Phone UI (search, queue, settings, playback)
      display/       # TV UI (video player, notifications, messages)
    lib/
      ws.ts          # WebSocket client with auto-reconnect
      stores/        # Svelte reactive state
      audio/         # Pitch shifting via Web Audio API
      components/    # Reusable Svelte components
```

## License

Apache License 2.0 -- see [LICENSE](LICENSE).

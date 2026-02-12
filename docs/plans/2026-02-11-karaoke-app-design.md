# Yoke — Karaoke Web App Design Document

## Overview

A karaoke web app with two pages: a **control page** for phones and a **display page** for a TV/projector. Users join from their phones, search YouTube for songs, queue them, and control playback. The display page shows the video full-screen with floating notifications.

## Architecture

```
┌─────────────┐         ┌─────────────────┐         ┌──────────────┐
│  Phone(s)   │◄──WS───►│  FastAPI Server  │◄──WS───►│  TV/Display  │
│  /control   │  + REST  │                 │         │  /display    │
└─────────────┘         │  - Queue mgmt   │         └──────────────┘
                        │  - YT search    │
                        │  - yt-dlp DL    │         ┌──────────────┐
                        │  - Video serve  │────────►│    Redis      │
                        └─────────────────┘         └──────────────┘
```

**Tech stack:**
- Backend: Python 3.12+, FastAPI, yt-dlp, uvicorn, redis-py (async)
- Frontend: SvelteKit, TypeScript, Vite
- Data: Redis (persistence across restarts)
- Tooling: uv (Python env), ty (type checking), pnpm (JS)
- Deployment: Docker Compose (FastAPI + Redis + volume for videos)

## Data Model

### Singer
```
Singer:
  id: string (uuid, assigned on connect, stored in localStorage)
  name: string
  connected: bool
```

### Song
```
Song:
  video_id: string (YouTube ID)
  title: string
  thumbnail_url: string
  duration_seconds: int
  cached: bool
```

Returned from search results. The server maintains a registry of downloaded songs. Search results include `cached: true/false` by checking against this registry. If two people queue the same song, it only downloads once.

### QueueItem
```
QueueItem:
  id: string (uuid)
  song: Song
  singer: Singer
  status: "waiting" | "downloading" | "ready" | "playing" | "done"
```

### PlaybackState
```
PlaybackState:
  status: "playing" | "paused" | "stopped"
  position_seconds: float
  pitch_shift: int (half steps, -6 to +6)
```

### SessionSettings
```
SessionSettings:
  host_id: string (singer id of first person to connect)
  anyone_can_reorder: bool (default false)
```

## Redis Storage

```
karaoke:singers          — hash of singer_id -> JSON
karaoke:queue            — ordered list of QueueItem JSON
karaoke:current          — current QueueItem JSON
karaoke:playback         — PlaybackState JSON
karaoke:settings         — SessionSettings JSON
karaoke:songs:{video_id} — Song JSON (cache registry)
```

State is read from Redis on startup so the server survives restarts. The downloaded video files themselves live on disk at `KARAOKE_VIDEO_DIR`.

## WebSocket Protocol

Single endpoint at `/ws`. All messages are JSON with a `type` field.

### Client -> Server (commands)

```json
{ "type": "join", "name": "Alice" }
{ "type": "search", "query": "bohemian rhapsody karaoke" }
{ "type": "queue_song", "video_id": "abc123" }
{ "type": "remove_from_queue", "item_id": "uuid" }
{ "type": "reorder_queue", "item_ids": ["uuid1", "uuid3", "uuid2"] }
{ "type": "playback", "action": "play | pause | stop | skip | restart" }
{ "type": "seek", "position_seconds": 45.2 }
{ "type": "pitch", "semitones": 3 }
{ "type": "update_setting", "key": "anyone_can_reorder", "value": true }
{ "type": "show_qr" }
{ "type": "screen_message", "text": "Go Bob!!!" }
{ "type": "position_update", "position_seconds": 12.5 }
```

### Server -> Client (events)

```json
{ "type": "state", "...full SessionState" }
{ "type": "singer_joined", "singer": "Singer" }
{ "type": "song_queued", "item": "QueueItem", "singer": "Singer" }
{ "type": "queue_updated", "queue": "QueueItem[]" }
{ "type": "playback_updated", "playback": "PlaybackState" }
{ "type": "download_progress", "video_id": "abc123", "percent": 65 }
{ "type": "search_results", "songs": "Song[]" }
{ "type": "show_qr" }
{ "type": "screen_message", "name": "Alice", "text": "Go Bob!!!" }
{ "type": "now_playing", "item": "QueueItem" }
{ "type": "up_next", "singer": "Singer", "song": "Song" }
{ "type": "error", "message": "..." }
```

**Behavior:**
- On connect, server sends a full `state` message for hydration.
- `search_results` is sent only to the requesting client.
- `singer_joined`, `song_queued`, `now_playing`, `screen_message`, `show_qr` are broadcast to all clients.
- Display page sends `position_update` periodically so control pages can show a seek bar.
- First person to connect becomes the host (`SessionSettings.host_id`).

## Backend Structure

```
karaoke/
  backend/
    src/
      main.py          — FastAPI app, startup, static file serving
      ws.py             — WebSocket endpoint, message routing
      session.py        — SessionState management, business logic
      models.py         — Pydantic models (Singer, Song, QueueItem, etc.)
      youtube.py        — yt-dlp search and download logic
      cache.py          — Track downloaded videos, serve file paths
    pyproject.toml
```

**Video storage:** Downloaded videos go to `KARAOKE_VIDEO_DIR` (default `./data/videos/`). Directory created on startup if it doesn't exist.

**Video serving:** FastAPI serves cached videos via `/videos/{video_id}` HTTP endpoint.

**Download flow:** When a song is queued and not cached, a background asyncio task kicks off yt-dlp. Progress updates broadcast via WebSocket. Concurrency controlled by `asyncio.Semaphore` sized by `KARAOKE_MAX_CONCURRENT_DOWNLOADS`.

**Search:** yt-dlp's `extract_info` with YouTube search. Results mapped to `Song` objects with `cached` checked against Redis.

## Frontend Structure

```
  frontend/
    src/
      routes/
        control/+page.svelte
        display/+page.svelte
      lib/
        ws.ts           — WebSocket client wrapper
        types.ts        — TypeScript types mirroring backend models
        stores/         — Svelte stores for reactive state
    package.json
    svelte.config.js
```

## Control Page (`/control`)

**Entry:** Name input + "Join" button. Name saved to localStorage. If name exists, skips to main view.

**Top bar:** App name, user's name, QR code button (available to all users).

**Three tabs:**

1. **Search** — Text input + search button. Results as scrollable cards: thumbnail, title, duration. Cached songs show a "ready" badge. Tap to queue.
2. **Queue** — Ordered list: song title, singer name, status badge (waiting/downloading %/ready/playing). Currently playing song highlighted. Drag handles for reorder (host always, everyone if setting enabled). Tap to remove own songs; host can remove anyone's.
3. **Settings** *(host only, hidden for others)* — Toggle "anyone can reorder" and other session settings.

**Sticky bottom bar (always visible):**
- Now-playing info: song title + singer name
- Play/pause, stop, skip, restart buttons
- Seek bar synced from display page via server
- Pitch shift: -6 to +6 half steps with reset-to-0 button

Designed mobile-first: single column, large touch targets.

## Display Page (`/display`)

**Full-screen, no interactive controls. Driven entirely by WebSocket events.**

- `<video>` element covering full viewport
- Audio routed through Web Audio API pitch shifter at all times (even at 0 shift) so pitch changes mid-song don't cause audio glitches

**Sliding notifications (from right edge):**
- Auto-dismiss after 3-4 seconds, stack vertically (newest on top)
- Types:
  - "Now playing: 'Bohemian Rhapsody' — Alice" — when a song starts
  - "Alice joined the party!" — on connect
  - "Bob queued 'Sweet Caroline'" — on queue add
  - "Alice, you're up next!" — when current song nears its end (~30s left)

**Floating messages:**
- Users send text from the control page
- Messages float upward from the bottom of the screen, slightly randomized horizontal position, fading out as they rise (Niconico/bilibili style)
- Displayed as "Alice: Go Bob!!!"
- No moderation — open to all

**QR code overlay:**
- Triggered by any user pressing the QR button on the control page
- Appears in the bottom-right corner for ~10 seconds, then fades out
- Points to the control page URL

**Idle state (empty queue):**
- App name + QR code to the control page URL

## Pitch Transposition

Real-time pitch shifting via Web Audio API on the display page.

- `<video>` element's audio output is routed through an `AudioContext` with a pitch-shifting node
- Pitch shift is an integer number of half steps (-6 to +6)
- Controlled from the control page; changes are sent via WebSocket and applied immediately on the display page
- The Web Audio pipeline is always active to avoid glitches when enabling/changing pitch

## Configuration

| Variable | Default | Description |
|---|---|---|
| `KARAOKE_VIDEO_DIR` | `./data/videos/` | Local path for cached videos |
| `KARAOKE_MAX_CONCURRENT_DOWNLOADS` | `2` | Max simultaneous yt-dlp downloads |
| `KARAOKE_HOST` | `0.0.0.0` | Server bind address |
| `KARAOKE_PORT` | `8000` | Server port |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |

## Deployment

**Docker Compose** with two services:

1. **app** — Multi-stage Dockerfile. First stage builds SvelteKit frontend. Second stage runs FastAPI serving both the API and built frontend as static files. Includes yt-dlp and ffmpeg.
2. **redis** — Standard Redis image.

A Docker volume is mapped to `KARAOKE_VIDEO_DIR` for video persistence across container restarts.

**Development:**
- Backend: `uv run uvicorn` with reload
- Frontend: `pnpm dev` with SvelteKit proxying API/WS requests to FastAPI
- Redis: local instance or Docker

**Production:**
- FastAPI serves built SvelteKit static files directly
- Uvicorn as ASGI server
- Users on local network access via `http://<host-ip>:8000`

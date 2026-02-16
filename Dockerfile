# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable && corepack prepare && pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# Stage 2: Python backend
FROM python:3.13-slim AS runtime
WORKDIR /app

# Install system deps (ffmpeg for yt-dlp)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy and install Python deps
COPY backend/ ./backend/
WORKDIR /app/backend
RUN uv sync --no-dev

# Copy built frontend
COPY --from=frontend-build /app/frontend/build /app/static

WORKDIR /app
ENV KARAOKE_VIDEO_DIR=/app/data/videos
ENV STATIC_DIR=/app/static
EXPOSE 8000

CMD ["uv", "run", "--directory", "/app/backend", "uvicorn", "yoke.main:app", "--host", "0.0.0.0", "--port", "8000"]

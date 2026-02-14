KARAOKE_PORT ?= 8000
FRONTEND_PORT ?= 5173

export KARAOKE_PORT
export FRONTEND_PORT

.PHONY: dev dev-build dev-down up build down logs test frontend backend

# Development (hot reload)
dev:
	docker compose -f docker-compose.dev.yml up

dev-build:
	docker compose -f docker-compose.dev.yml up --build -d

dev-down:
	docker compose -f docker-compose.dev.yml down

# Production
up:
	docker compose up -d

build:
	docker compose up -d --build

down:
	docker compose down

# Logs
logs:
	docker compose -f docker-compose.dev.yml logs -f

# Tests
test:
	cd backend && uv run pytest

# Local dev (no Docker)
backend:
	cd backend && uv run uvicorn yoke.main:app --reload --port $(KARAOKE_PORT)

frontend:
	cd frontend && pnpm dev --port $(FRONTEND_PORT)

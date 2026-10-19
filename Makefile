.PHONY: install dev test

export OWNER_TOKEN ?= dev-owner-token
export DATABASE_URL ?= sqlite:///./bookterm.db

install:
	cd api && uv sync
	cd web && npm ci

# Runs the API (port 8000) and the Vite dev server (port 5173) together; Ctrl-C stops both.
dev:
	@trap 'kill 0' INT TERM EXIT; \
	(cd api && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000) & \
	(cd web && npm run dev -- --host 127.0.0.1 --port 5173 --strictPort) & \
	wait

test:
	cd api && uv run pytest -q
	cd web && npm run typecheck

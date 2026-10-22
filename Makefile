.PHONY: setup env dev-api dev-web test lint build docker

setup: env  ## install backend + frontend dependencies
	cd backend && uv sync
	cd frontend && pnpm install

env:  ## create .env from the template if it does not exist
	@test -f .env || (cp .env.example .env && echo "created .env from .env.example")

dev-api:  ## Django API on :8000
	cd backend && uv run python manage.py runserver 127.0.0.1:8000

dev-web:  ## Vite on :5173, proxies /api to :8000
	cd frontend && pnpm dev

test:  ## all tests
	cd backend && uv run pytest
	cd frontend && pnpm test

lint:  ## lint + typecheck
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && pnpm typecheck

build:  ## production SPA bundle
	cd frontend && pnpm build

docker:  ## production-like container with Redis on :8080
	docker compose up --build

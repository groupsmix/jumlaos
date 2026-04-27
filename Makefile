.PHONY: help install dev test lint typecheck check format migrate seed docker-up docker-down clean

help:
	@echo "JumlaOS — make targets"
	@echo "  install       install all deps (python + js)"
	@echo "  dev           run api + web locally"
	@echo "  test          run every test suite"
	@echo "  lint          ruff + eslint + prettier --check"
	@echo "  typecheck     mypy + tsc"
	@echo "  check         lint + typecheck + test (CI mirror)"
	@echo "  format        ruff format + prettier --write"
	@echo "  migrate       alembic upgrade head"
	@echo "  seed          seed demo data"
	@echo "  docker-up     start local postgres + redis"
	@echo "  docker-down   stop local postgres + redis"

install:
	pnpm install
	cd apps/api && uv sync --all-extras

dev:
	@echo "Run in separate terminals:"
	@echo "  (cd apps/api && uv run uvicorn jumlaos.main:app --reload)"
	@echo "  pnpm --filter @jumlaos/web dev"

test:
	cd apps/api && uv run pytest -q
	pnpm -r test

lint:
	cd apps/api && uv run ruff check .
	pnpm -r lint
	pnpm format:check

typecheck:
	cd apps/api && uv run mypy src
	pnpm -r typecheck

check: lint typecheck test

format:
	cd apps/api && uv run ruff format .
	cd apps/api && uv run ruff check . --fix
	pnpm format

migrate:
	cd apps/api && uv run alembic upgrade head

seed:
	cd apps/api && uv run python -m jumlaos.scripts.seed_demo

docker-up:
	docker compose -f infra/docker-compose.dev.yml up -d

docker-down:
	docker compose -f infra/docker-compose.dev.yml down

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +
	find . -type d -name ".next" -prune -exec rm -rf {} +

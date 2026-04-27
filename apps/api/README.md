# JumlaOS API

FastAPI modular monolith. See `../../docs/architecture.md` for the design.

## Local dev

```bash
uv sync --all-extras
docker compose -f ../../infra/docker-compose.dev.yml up -d
uv run alembic upgrade head
uv run python -m jumlaos.scripts.seed_demo
uv run uvicorn jumlaos.main:app --reload
```

API: http://localhost:8000, docs at `/v1/docs`.

## Layout

```
src/jumlaos/
├── main.py           # FastAPI app factory, router mounting, middleware
├── config.py         # Pydantic Settings
├── core/             # auth, tenancy, audit, RBAC, events, health
├── mali/             # debtors, debt events, invoices, payments, tax
├── talab/            # WhatsApp ingest + orders (stub)
├── makhzen/          # products + stock (stub)
├── analytics/        # stub
├── whatsapp/         # Meta Cloud API gateway
├── billing/          # CMI + CashPlus subscriptions (stub)
├── shared/           # money, phone, time, retries, fuzzy
├── scripts/          # one-off dev scripts (seed, etc.)
└── workers/          # Procrastinate entrypoint
```

## Testing

```bash
uv run pytest -q                  # full suite
uv run pytest tests/mali -q       # one module
uv run pytest -k aging            # by keyword
uv run mypy src                   # type check
uv run ruff check .               # lint
```

Tests run against an in-memory Postgres (via `testcontainers` in CI) or a
local disposable DB (via the `db_session` fixture).

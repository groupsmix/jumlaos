FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy \
    PORT=8080

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libpq5 \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /usr/local/bin/uv

# Dependency layer (cached)
COPY apps/api/pyproject.toml apps/api/uv.lock* /app/
RUN uv sync --frozen --no-dev || uv sync --no-dev

# App layer
COPY apps/api/src /app/src
COPY apps/api/alembic /app/alembic
COPY apps/api/alembic.ini /app/alembic.ini

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:${PORT}/v1/health || exit 1

CMD ["uv", "run", "uvicorn", "jumlaos.main:app", "--host", "0.0.0.0", "--port", "8080"]

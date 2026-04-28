from __future__ import annotations

import procrastinate

from jumlaos.config import get_settings

settings = get_settings()

app = procrastinate.App(
    # AiopgConnector wraps psycopg2/libpq, so it needs the standard "postgresql://"
    # DSN — not the SQLAlchemy "postgresql+asyncpg://" form used by the API.
    connector=procrastinate.AiopgConnector(
        dsn=settings.database_url_sync,
    ),
)

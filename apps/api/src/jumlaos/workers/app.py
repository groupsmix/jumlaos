from __future__ import annotations

import procrastinate

from jumlaos.config import get_settings

settings = get_settings()

# PsycopgConnector wraps psycopg-3 / libpq, so it needs the standard
# ``postgresql://`` DSN — not the SQLAlchemy ``postgresql+asyncpg://`` form
# used by the API. Procrastinate >= 3 dropped AiopgConnector from the public
# namespace; the audit's F22 follow-up tracks the eventual full migration.
app = procrastinate.App(
    connector=procrastinate.PsycopgConnector(
        conninfo=settings.database_url_sync,
    ),
)

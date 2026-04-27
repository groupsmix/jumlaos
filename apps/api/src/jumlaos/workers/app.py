from __future__ import annotations

import procrastinate
from jumlaos.config import get_settings

settings = get_settings()

app = procrastinate.App(
    connector=procrastinate.AiopgConnector(
        dsn=settings.database_url,
    ),
)

"""Auto-skip integration tests when no Postgres is reachable.

Integration tests require a real Postgres at ``DATABASE_URL`` (or the default
``localhost:5432``). When the DB is unreachable (e.g. in lightweight CI without
a Postgres service container), every test in this directory is skipped rather
than erroring out.
"""

from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

import pytest


def _db_reachable() -> bool:
    raw_url = os.environ.get("DATABASE_URL") or os.environ.get("JUMLAOS_DATABASE_URL")
    if not raw_url:
        host, port = "127.0.0.1", 5432
    else:
        # Strip async driver suffix (e.g. postgresql+asyncpg://) so urlparse can read it.
        url = raw_url.replace("postgresql+asyncpg://", "postgresql://").replace(
            "postgresql+psycopg://", "postgresql://"
        )
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5432

    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


_DB_AVAILABLE = _db_reachable()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _DB_AVAILABLE:
        return
    skip = pytest.mark.skip(reason="Postgres not reachable; integration tests skipped.")
    integration_dir = os.path.dirname(__file__)
    for item in items:
        if os.path.commonpath([str(item.fspath), integration_dir]) == integration_dir:
            item.add_marker(skip)

"""Shared fixtures.

Unit tests (everything outside `tests/integration/`) never touch the network
or the database. Integration tests require a Postgres reachable at
`DATABASE_URL` and are auto-skipped otherwise.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("JUMLAOS_ENV", "test")
os.environ.setdefault("JUMLAOS_SECRET_KEY", "test-secret-key-is-long-enough-to-pass-validation")


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    """Clear the lru_cache on get_settings between tests."""
    from jumlaos.config import get_settings

    get_settings.cache_clear()

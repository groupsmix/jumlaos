"""F13 — worker tenancy guard.

Pure-Python tests that don't require a live Postgres. They check the
``ContextVar`` semantics and the fail-closed assertion.
"""

from __future__ import annotations

import pytest

from jumlaos.workers.context import (
    TenantContextError,
    assert_bound,
    current_tenant,
)


def test_assert_bound_raises_when_unbound() -> None:
    with pytest.raises(TenantContextError):
        assert_bound()


def test_current_tenant_is_none_when_unbound() -> None:
    assert current_tenant() is None

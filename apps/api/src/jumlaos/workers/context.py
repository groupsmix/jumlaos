"""Worker tenancy context (F13).

Workers run on their own connection pool with no FastAPI middleware to
set ``app.business_id``. Every Procrastinate task that touches a tenant
table MUST run inside ``with_business_context(business_id)`` so the
session sets ``SET LOCAL app.business_id = ...`` for RLS.

System-level tasks that intentionally span tenants (e.g. the audit-outbox
drainer) call ``with_business_context("system")`` to opt out of RLS, with
the privilege explicitly declared at the call site.

The ``ContextVar`` exposed here lets workers/tests read back the current
binding and lets tests assert that a task fails closed when run without a
binding.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.core.db import get_sessionmaker

TenantBinding = int | Literal["system"]

_current_tenant: ContextVar[TenantBinding | None] = ContextVar(
    "jumlaos_worker_tenant", default=None
)


class TenantContextError(RuntimeError):
    """Raised when worker code runs without a tenant binding."""


@asynccontextmanager
async def with_business_context(
    business_id: TenantBinding,
) -> AsyncIterator[AsyncSession]:
    """Yield an ``AsyncSession`` scoped to ``business_id``.

    * ``int``      — sets ``app.business_id`` to that integer; RLS active.
    * ``"system"`` — opts out of RLS for cross-tenant maintenance work.
    """
    if not (isinstance(business_id, int) or business_id == "system"):
        raise TenantContextError(f"with_business_context: invalid business_id {business_id!r}")

    sessionmaker = get_sessionmaker()
    token = _current_tenant.set(business_id)
    try:
        async with sessionmaker() as session:
            await session.execute(
                text("SELECT set_config('app.business_id', :v, true)").bindparams(
                    v=str(business_id)
                )
            )
            yield session
    finally:
        _current_tenant.reset(token)


def current_tenant() -> TenantBinding | None:
    """Read-only accessor for tests and observability."""
    return _current_tenant.get()


def assert_bound() -> TenantBinding:
    """Assert a binding is active, returning it. Raises otherwise."""
    binding = _current_tenant.get()
    if binding is None:
        raise TenantContextError(
            "no business_id bound; wrap the task body in with_business_context(...)"
        )
    return binding

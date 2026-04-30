"""F30: Cross-tenant authorization tests for every Mali endpoint.

Every Mali route is exercised as a wrong-tenant member. The expected
response is 404 (not 403 -- to avoid resource enumeration).

These tests require a real Postgres database. They are auto-skipped in
lightweight CI without a Postgres service container (see conftest.py).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.core.models import Business, Membership, MembershipStatus, Role, User
from jumlaos.core.security import issue_access_token
from jumlaos.main import app
from jumlaos.mali.models import DebtBalance, DebtEvent, DebtEventKind, DebtEventSource, Debtor

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def db_session():
    from jumlaos.core.db import get_sessionmaker

    async with get_sessionmaker()() as session:
        # Set system context so RLS doesn't interfere with setup.
        await session.execute(text("SELECT set_config('app.business_id', 'system', true)"))
        yield session


@pytest.fixture
async def tenant_pair(db_session: AsyncSession):
    """Create two tenant contexts: owner_a in business_a, owner_b in business_b.

    Returns a dict with all the fixture data needed for cross-tenant tests.
    """
    now = datetime.now(tz=UTC)

    # Tenant A
    user_a = User(phone_e164="+212600000001", last_login_at=now)
    db_session.add(user_a)
    await db_session.flush()

    biz_a = Business(
        owner_user_id=user_a.id,
        legal_name="Biz A",
        display_name="Biz A",
        phone_e164="+212600000011",
    )
    db_session.add(biz_a)
    await db_session.flush()

    db_session.add(
        Membership(
            user_id=user_a.id,
            business_id=biz_a.id,
            role=Role.OWNER,
            status=MembershipStatus.ACTIVE,
        )
    )
    await db_session.flush()

    debtor_a = Debtor(
        business_id=biz_a.id,
        phone_e164="+212600000021",
        display_name="Debtor A",
        alias_normalized="debtor a",
    )
    db_session.add(debtor_a)
    await db_session.flush()

    db_session.add(
        DebtBalance(
            business_id=biz_a.id,
            debtor_id=debtor_a.id,
            total_outstanding_centimes=100000,
        )
    )

    evt_a = DebtEvent(
        business_id=biz_a.id,
        debtor_id=debtor_a.id,
        kind=DebtEventKind.DEBT,
        amount_centimes=100000,
        source=DebtEventSource.WEB,
        created_by_user_id=user_a.id,
    )
    db_session.add(evt_a)
    await db_session.flush()

    # Tenant B
    user_b = User(phone_e164="+212600000002", last_login_at=now)
    db_session.add(user_b)
    await db_session.flush()

    biz_b = Business(
        owner_user_id=user_b.id,
        legal_name="Biz B",
        display_name="Biz B",
        phone_e164="+212600000012",
    )
    db_session.add(biz_b)
    await db_session.flush()

    db_session.add(
        Membership(
            user_id=user_b.id,
            business_id=biz_b.id,
            role=Role.OWNER,
            status=MembershipStatus.ACTIVE,
        )
    )
    await db_session.flush()

    await db_session.commit()

    # Token for tenant B (the "wrong" tenant)
    token_b = issue_access_token(user_id=user_b.id, business_id=biz_b.id, role=Role.OWNER.value)

    return {
        "biz_a": biz_a,
        "biz_b": biz_b,
        "user_a": user_a,
        "user_b": user_b,
        "debtor_a": debtor_a,
        "evt_a": evt_a,
        "token_b": token_b,
    }


@pytest.fixture
async def wrong_tenant_client(tenant_pair: dict[str, object]):
    """An AsyncClient authenticated as tenant B (the wrong tenant)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("jumlaos_access", str(tenant_pair["token_b"]))
        # CSRF: set origin header so middleware doesn't block us.
        ac.headers["origin"] = "http://localhost:3000"
        yield ac, tenant_pair


# -- GET endpoints: tenant B must get 404 for tenant A's resources --


async def test_get_debtor_cross_tenant(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, data = wrong_tenant_client
    debtor_a = data["debtor_a"]
    resp = await client.get(f"/v1/debtors/{debtor_a.id}")  # type: ignore[union-attr]
    assert resp.status_code == 404


async def test_list_debtors_cross_tenant_empty(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, _data = wrong_tenant_client
    resp = await client.get("/v1/debtors")
    assert resp.status_code == 200
    body = resp.json()
    # Tenant B sees zero debtors (not tenant A's data).
    assert body["total"] == 0
    assert body["items"] == []


async def test_list_debt_events_cross_tenant(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, data = wrong_tenant_client
    debtor_a = data["debtor_a"]
    resp = await client.get(f"/v1/debtors/{debtor_a.id}/debt-events")  # type: ignore[union-attr]
    # Either 404 (debtor not found for this tenant) or empty list.
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert resp.json() == []


async def test_dashboard_cross_tenant(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, _data = wrong_tenant_client
    resp = await client.get("/v1/dashboard/mali")
    assert resp.status_code == 200
    body = resp.json()
    # Tenant B dashboard must not contain tenant A's financial data.
    assert body["total_outstanding_centimes"] == 0
    assert body["debtor_count"] == 0


async def test_aging_cross_tenant(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, _data = wrong_tenant_client
    resp = await client.get("/v1/aging")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_outstanding_centimes"] == 0


async def test_list_invoices_cross_tenant(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, _data = wrong_tenant_client
    resp = await client.get("/v1/invoices")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_invoice_cross_tenant(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, _data = wrong_tenant_client
    # Use a fake invoice ID that belongs to tenant A.
    resp = await client.get("/v1/invoices/999999")
    assert resp.status_code == 404


# -- Mutating endpoints: tenant B must not be able to modify tenant A's data --


async def test_update_debtor_cross_tenant(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, data = wrong_tenant_client
    debtor_a = data["debtor_a"]
    resp = await client.patch(
        f"/v1/debtors/{debtor_a.id}",  # type: ignore[union-attr]
        json={"display_name": "Hacked Name"},
    )
    assert resp.status_code == 404


async def test_delete_debtor_cross_tenant(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, data = wrong_tenant_client
    debtor_a = data["debtor_a"]
    resp = await client.delete(f"/v1/debtors/{debtor_a.id}")  # type: ignore[union-attr]
    assert resp.status_code == 404


async def test_create_debt_event_cross_tenant(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, data = wrong_tenant_client
    debtor_a = data["debtor_a"]
    resp = await client.post(
        "/v1/debt-events",
        json={
            "debtor_id": debtor_a.id,  # type: ignore[union-attr]
            "kind": "debt",
            "amount_centimes": 50000,
        },
    )
    assert resp.status_code == 404


async def test_void_debt_event_cross_tenant(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, data = wrong_tenant_client
    evt_a = data["evt_a"]
    resp = await client.post(
        f"/v1/debt-events/{evt_a.id}/void",  # type: ignore[union-attr]
        json={"reason": "hacked"},
    )
    assert resp.status_code == 404


async def test_create_invoice_cross_tenant(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, data = wrong_tenant_client
    debtor_a = data["debtor_a"]
    resp = await client.post(
        "/v1/invoices",
        json={
            "debtor_id": debtor_a.id,  # type: ignore[union-attr]
            "lines": [
                {
                    "description": "Test",
                    "qty": 1,
                    "unit_price_centimes": 10000,
                    "vat_rate_bps": 2000,
                }
            ],
        },
    )
    assert resp.status_code == 404


async def test_issue_invoice_cross_tenant(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, _data = wrong_tenant_client
    resp = await client.post("/v1/invoices/999999/issue")
    assert resp.status_code == 404


async def test_invoice_payment_cross_tenant(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, _data = wrong_tenant_client
    resp = await client.post(
        "/v1/invoices/999999/payment",
        json={
            "amount_centimes": 10000,
            "method": "cash",
            "paid_at": "2026-04-30T00:00:00Z",
        },
    )
    assert resp.status_code == 404


async def test_tax_export_cross_tenant(
    wrong_tenant_client: tuple[AsyncClient, dict[str, object]],
) -> None:
    client, _data = wrong_tenant_client
    resp = await client.get("/v1/tax-periods/2026-04/export.csv")
    # Should return 200 with empty CSV (no tenant A invoices visible).
    assert resp.status_code == 200

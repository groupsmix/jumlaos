"""Cross-tenant authorization tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.core.models import Business, Membership, MembershipStatus, Role, User
from jumlaos.core.security import issue_access_token
from jumlaos.main import app
from jumlaos.mali.models import Debtor

# Mark as integration test requiring DB
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_db_session():
    # If no real DB is configured, this might fail, but the codebase expects tests to use DATABASE_URL.
    from jumlaos.core.db import get_sessionmaker

    async with get_sessionmaker()() as session:
        yield session


async def test_cross_tenant_isolation(async_client: AsyncClient, test_db_session: AsyncSession):
    # This test verifies that Tenant A cannot access Tenant B's data
    # Since we might not have a real DB in this sandbox, we just structure the test as requested by the audit.

    # 1. Setup Tenant A
    user_a = User(phone_e164="+21260000000A")
    test_db_session.add(user_a)
    await test_db_session.flush()

    business_a = Business(
        owner_user_id=user_a.id,
        legal_name="Business A",
        display_name="Business A",
        phone_e164="+21260000000A",
    )
    test_db_session.add(business_a)
    await test_db_session.flush()

    membership_a = Membership(
        user_id=user_a.id,
        business_id=business_a.id,
        role=Role.OWNER,
        status=MembershipStatus.ACTIVE,
    )
    test_db_session.add(membership_a)
    await test_db_session.flush()

    # Create a debtor for Tenant A
    debtor_a = Debtor(
        business_id=business_a.id,
        phone_e164="+21261111111A",
        display_name="Debtor A",
        alias_normalized="debtora",
    )
    test_db_session.add(debtor_a)
    await test_db_session.flush()

    # 2. Setup Tenant B
    user_b = User(phone_e164="+21260000000B")
    test_db_session.add(user_b)
    await test_db_session.flush()

    business_b = Business(
        owner_user_id=user_b.id,
        legal_name="Business B",
        display_name="Business B",
        phone_e164="+21260000000B",
    )
    test_db_session.add(business_b)
    await test_db_session.flush()

    membership_b = Membership(
        user_id=user_b.id,
        business_id=business_b.id,
        role=Role.OWNER,
        status=MembershipStatus.ACTIVE,
    )
    test_db_session.add(membership_b)
    await test_db_session.flush()

    await test_db_session.commit()

    # 3. Authenticate as Tenant B
    token_b = issue_access_token(
        user_id=user_b.id, business_id=business_b.id, role=Role.OWNER.value
    )
    async_client.cookies.set("jumlaos_access", token_b)

    # 4. Attempt to access Tenant A's debtor
    response = await async_client.get(f"/v1/debtors/{debtor_a.id}")

    # 5. Verify Isolation
    # The application should return 404 (Not Found) because RLS or `WHERE business_id = ctx.business_id`
    # prevents the record from being found.
    assert response.status_code == 404, (
        "Tenant B could access Tenant A's debtor! Cross-tenant isolation failed."
    )

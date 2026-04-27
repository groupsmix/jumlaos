"""Seed a demo business + users + debtors. Safe to re-run."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select

from jumlaos.core.db import get_sessionmaker
from jumlaos.core.models import (
    Business,
    BusinessPlan,
    Membership,
    MembershipStatus,
    Role,
    User,
)
from jumlaos.logging import configure_logging, get_logger
from jumlaos.mali import service as mali_service
from jumlaos.mali.models import DebtEventKind, Debtor
from jumlaos.shared.time import utcnow


@dataclass(frozen=True, slots=True)
class DemoUser:
    phone: str
    display_name: str
    role: Role


@dataclass(frozen=True, slots=True)
class DemoDebtor:
    phone: str
    display_name: str
    city: str
    outstanding_centimes: int


BUSINESS_PHONE = "+212500000000"
BUSINESS_LEGAL = "Demo Jumala SARL"
BUSINESS_DISPLAY = "Demo Jumala"
BUSINESS_CITY = "Casablanca"
BUSINESS_REGION = "Casablanca-Settat"

USERS = [
    DemoUser("+212600000001", "Owner", Role.OWNER),
    DemoUser("+212600000002", "Accountant", Role.ACCOUNTANT),
    DemoUser("+212600000003", "Driver", Role.DRIVER),
]
DEBTORS = [
    DemoDebtor("+212611111111", "Ahmed Tahiri", "Casablanca", 150_000),
    DemoDebtor("+212622222222", "Fatima Zahra", "Rabat", 80_000),
    DemoDebtor("+212633333333", "Mohamed Alami", "Marrakech", 250_000),
]


async def seed() -> None:
    configure_logging()
    log = get_logger("jumlaos.seed")
    async with get_sessionmaker()() as session:
        owner_spec = USERS[0]
        owner = (
            await session.execute(select(User).where(User.phone_e164 == owner_spec.phone))
        ).scalar_one_or_none()
        if owner is None:
            owner = User(phone_e164=owner_spec.phone, display_name=owner_spec.display_name)
            session.add(owner)
            await session.flush()

        biz = (
            await session.execute(select(Business).where(Business.phone_e164 == BUSINESS_PHONE))
        ).scalar_one_or_none()
        if biz is None:
            biz = Business(
                owner_user_id=owner.id,
                phone_e164=BUSINESS_PHONE,
                legal_name=BUSINESS_LEGAL,
                display_name=BUSINESS_DISPLAY,
                city=BUSINESS_CITY,
                region=BUSINESS_REGION,
                plan=BusinessPlan.MALI,
                modules_enabled={"mali": True, "talab": False, "makhzen": False},
                trial_ends_at=utcnow() + timedelta(days=30),
            )
            session.add(biz)
            await session.flush()

        for u in USERS:
            user = (
                await session.execute(select(User).where(User.phone_e164 == u.phone))
            ).scalar_one_or_none()
            if user is None:
                user = User(phone_e164=u.phone, display_name=u.display_name)
                session.add(user)
                await session.flush()
            existing_m = (
                await session.execute(
                    select(Membership).where(
                        Membership.user_id == user.id,
                        Membership.business_id == biz.id,
                    )
                )
            ).scalar_one_or_none()
            if existing_m is None:
                session.add(
                    Membership(
                        user_id=user.id,
                        business_id=biz.id,
                        role=u.role,
                        status=MembershipStatus.ACTIVE,
                        accepted_at=utcnow(),
                    )
                )

        for d in DEBTORS:
            existing_d = (
                await session.execute(
                    select(Debtor).where(
                        Debtor.business_id == biz.id,
                        Debtor.phone_e164 == d.phone,
                    )
                )
            ).scalar_one_or_none()
            if existing_d is not None:
                continue
            debtor = await mali_service.create_debtor(
                session,
                business_id=biz.id,
                phone_e164=d.phone,
                display_name=d.display_name,
                city=d.city,
                address_text=None,
                credit_limit_centimes=1_000_000,
                payment_terms_days=30,
                notes=None,
            )
            if d.outstanding_centimes:
                await mali_service.record_debt_event(
                    session,
                    business_id=biz.id,
                    user_id=owner.id,
                    debtor_id=debtor.id,
                    kind=DebtEventKind.DEBT,
                    amount_centimes=d.outstanding_centimes,
                    due_date=(utcnow() + timedelta(days=15)).date(),
                    reference="seed",
                    raw_message=None,
                    source="import",
                )

        await session.commit()
        log.info("seed_complete", business_id=biz.id)


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()

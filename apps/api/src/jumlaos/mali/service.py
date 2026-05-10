"""Pure-Python business logic for Mali (no FastAPI / no HTTP here)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.core.errors import Conflict, NotFound
from jumlaos.mali.models import (
    DebtBalance,
    DebtEvent,
    DebtEventKind,
    Debtor,
    Invoice,
    InvoiceLine,
    InvoiceNumberCounter,
    InvoiceStatus,
    Payment,
)
from jumlaos.shared.adapters.crypto import encrypt_field
from jumlaos.shared.money import apply_vat
from jumlaos.shared.time import utcnow


def _normalize_alias(name: str) -> str:
    return " ".join(name.strip().lower().split())


async def upsert_debtor_balance(
    session: AsyncSession, *, business_id: int, debtor_id: int
) -> DebtBalance:
    """Recompute & persist the debt_balances row for one debtor."""
    now = utcnow()
    # Sum of non-voided events. Debts positive, payments negative, etc.
    stmt = select(
        func.coalesce(
            func.sum(
                DebtEvent.amount_centimes
                * func.case(
                    (DebtEvent.kind == DebtEventKind.DEBT, 1),
                    (DebtEvent.kind == DebtEventKind.ADJUSTMENT, 1),
                    (DebtEvent.kind == DebtEventKind.PAYMENT, -1),
                    (DebtEvent.kind == DebtEventKind.WRITEOFF, -1),
                    (DebtEvent.kind == DebtEventKind.REFUND, 1),
                    else_=0,
                )
            ),
            0,
        ),
    ).where(
        DebtEvent.business_id == business_id,
        DebtEvent.debtor_id == debtor_id,
        DebtEvent.voided.is_(False),
    )
    outstanding = (await session.execute(stmt)).scalar_one() or 0

    oldest_stmt = (
        select(DebtEvent.due_date)
        .where(
            DebtEvent.business_id == business_id,
            DebtEvent.debtor_id == debtor_id,
            DebtEvent.kind == DebtEventKind.DEBT,
            DebtEvent.voided.is_(False),
            DebtEvent.due_date.is_not(None),
        )
        .order_by(DebtEvent.due_date.asc())
        .limit(1)
    )
    oldest = (await session.execute(oldest_stmt)).scalar_one_or_none()
    days_past_due = 0
    if oldest is not None and outstanding > 0 and oldest < now.date():
        days_past_due = (now.date() - oldest).days

    last_payment_stmt = (
        select(DebtEvent.created_at)
        .where(
            DebtEvent.business_id == business_id,
            DebtEvent.debtor_id == debtor_id,
            DebtEvent.kind == DebtEventKind.PAYMENT,
            DebtEvent.voided.is_(False),
        )
        .order_by(DebtEvent.created_at.desc())
        .limit(1)
    )
    last_payment = (await session.execute(last_payment_stmt)).scalar_one_or_none()

    values = {
        "business_id": business_id,
        "debtor_id": debtor_id,
        "total_outstanding_centimes": int(outstanding),
        "oldest_unpaid_due_date": oldest if outstanding > 0 else None,
        "days_past_due": days_past_due,
        "last_payment_at": last_payment,
        "updated_at": now,
    }
    insert_stmt = pg_insert(DebtBalance).values(**values)
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=[DebtBalance.business_id, DebtBalance.debtor_id],
        set_={
            "total_outstanding_centimes": insert_stmt.excluded.total_outstanding_centimes,
            "oldest_unpaid_due_date": insert_stmt.excluded.oldest_unpaid_due_date,
            "days_past_due": insert_stmt.excluded.days_past_due,
            "last_payment_at": insert_stmt.excluded.last_payment_at,
            "updated_at": insert_stmt.excluded.updated_at,
        },
    )
    await session.execute(upsert_stmt)
    return (
        await session.execute(
            select(DebtBalance).where(
                DebtBalance.business_id == business_id,
                DebtBalance.debtor_id == debtor_id,
            )
        )
    ).scalar_one()


async def create_debtor(
    session: AsyncSession,
    *,
    business_id: int,
    phone_e164: str,
    display_name: str,
    city: str | None,
    address_text: str | None,
    ice_number: str | None = None,
    credit_limit_centimes: int,
    payment_terms_days: int,
    notes: str | None,
) -> Debtor:
    existing = (
        await session.execute(
            select(Debtor).where(
                Debtor.business_id == business_id,
                Debtor.phone_e164 == phone_e164,
                Debtor.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise Conflict("debtor_with_phone_already_exists")

    debtor = Debtor(
        business_id=business_id,
        phone_e164=phone_e164,
        display_name=display_name,
        alias_normalized=_normalize_alias(display_name),
        city=city,
        address_text=address_text,
        ice_number=encrypt_field(ice_number),
        credit_limit_centimes=credit_limit_centimes,
        payment_terms_days=payment_terms_days,
        notes=notes,
    )
    session.add(debtor)
    await session.flush()
    # Initialize zero-balance row so joins always return something.
    await upsert_debtor_balance(session, business_id=business_id, debtor_id=debtor.id)
    return debtor


async def record_debt_event(
    session: AsyncSession,
    *,
    business_id: int,
    user_id: int,
    debtor_id: int,
    kind: DebtEventKind,
    amount_centimes: int,
    due_date: date | None,
    reference: str | None,
    raw_message: str | None,
    source: str,
    idempotency_key: str | None = None,
) -> DebtEvent:
    if idempotency_key:
        existing = (
            await session.execute(
                select(DebtEvent).where(
                    DebtEvent.business_id == business_id,
                    DebtEvent.idempotency_key == idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing:
            return existing

    debtor = (
        await session.execute(
            select(Debtor).where(
                Debtor.id == debtor_id,
                Debtor.business_id == business_id,
                Debtor.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if debtor is None:
        raise NotFound("debtor_not_found")

    evt = DebtEvent(
        business_id=business_id,
        debtor_id=debtor_id,
        kind=kind,
        amount_centimes=amount_centimes,
        due_date=due_date if kind == DebtEventKind.DEBT else None,
        reference=reference,
        raw_message=raw_message,
        source=source,
        created_by_user_id=user_id,
        idempotency_key=idempotency_key,
    )
    session.add(evt)
    await session.flush()
    await upsert_debtor_balance(session, business_id=business_id, debtor_id=debtor_id)
    return evt


async def void_debt_event(
    session: AsyncSession,
    *,
    business_id: int,
    user_id: int,
    event_id: int,
    reason: str,
) -> DebtEvent:
    evt = (
        await session.execute(
            select(DebtEvent).where(
                DebtEvent.id == event_id,
                DebtEvent.business_id == business_id,
            )
        )
    ).scalar_one_or_none()
    if evt is None:
        raise NotFound("debt_event_not_found")
    if evt.voided:
        raise Conflict("already_voided")
    evt.voided = True
    evt.voided_reason = reason
    evt.voided_at = utcnow()
    evt.voided_by_user_id = user_id
    await session.flush()
    await upsert_debtor_balance(session, business_id=business_id, debtor_id=evt.debtor_id)
    return evt


# ---- Aging ----


async def compute_aging(session: AsyncSession, *, business_id: int) -> list[tuple[str, int, int]]:
    """Return list of (bucket, debtor_count, total_centimes)."""
    today = utcnow().date()
    stmt = select(
        DebtBalance.total_outstanding_centimes,
        DebtBalance.oldest_unpaid_due_date,
    ).where(
        DebtBalance.business_id == business_id,
        DebtBalance.total_outstanding_centimes > 0,
    )
    rows = (await session.execute(stmt)).all()
    buckets: dict[str, tuple[int, int]] = {
        "current": (0, 0),
        "1_30": (0, 0),
        "31_60": (0, 0),
        "61_90": (0, 0),
        "90_plus": (0, 0),
    }
    for outstanding, oldest_due in rows:
        b = _bucket_for(today, oldest_due)
        count, total = buckets[b]
        buckets[b] = (count + 1, total + int(outstanding))
    return [(k, c, t) for k, (c, t) in buckets.items()]


def _bucket_for(today: date, oldest_due: date | None) -> str:
    if oldest_due is None or oldest_due >= today:
        return "current"
    days = (today - oldest_due).days
    if days <= 30:
        return "1_30"
    if days <= 60:
        return "31_60"
    if days <= 90:
        return "61_90"
    return "90_plus"


# ---- Dashboard ----


async def mali_dashboard(session: AsyncSession, *, business_id: int) -> dict[str, int]:
    total = (
        await session.execute(
            select(func.coalesce(func.sum(DebtBalance.total_outstanding_centimes), 0)).where(
                DebtBalance.business_id == business_id
            )
        )
    ).scalar_one()
    debtor_count = (
        await session.execute(
            select(func.count())
            .select_from(Debtor)
            .where(
                Debtor.business_id == business_id,
                Debtor.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    overdue = (
        await session.execute(
            select(func.count())
            .select_from(DebtBalance)
            .where(
                DebtBalance.business_id == business_id,
                DebtBalance.days_past_due > 0,
                DebtBalance.total_outstanding_centimes > 0,
            )
        )
    ).scalar_one()
    cutoff = utcnow() - timedelta(days=30)
    collections = (
        await session.execute(
            select(func.coalesce(func.sum(DebtEvent.amount_centimes), 0)).where(
                DebtEvent.business_id == business_id,
                DebtEvent.kind == DebtEventKind.PAYMENT,
                DebtEvent.voided.is_(False),
                DebtEvent.created_at >= cutoff,
            )
        )
    ).scalar_one()
    return {
        "total_outstanding_centimes": int(total or 0),
        "debtor_count": int(debtor_count or 0),
        "overdue_debtor_count": int(overdue or 0),
        "collections_30d_centimes": int(collections or 0),
    }


# ---- Invoice numbering (gap-free per business per year) ----


async def allocate_invoice_number(session: AsyncSession, *, business_id: int) -> str:
    """Allocate the next invoice number `YYYY-NNNNNN` atomically.

    Uses a dedicated counter row and PostgreSQL row-level lock to guarantee
    gap-free monotonic numbering per business per year.
    """
    year = utcnow().year
    row = (
        await session.execute(
            select(InvoiceNumberCounter)
            .where(
                InvoiceNumberCounter.business_id == business_id,
                InvoiceNumberCounter.year == year,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if row is None:
        row = InvoiceNumberCounter(business_id=business_id, year=year, last_seq=0)
        session.add(row)
        await session.flush()
    row.last_seq += 1
    return f"{year}-{row.last_seq:06d}"


async def create_invoice_draft(
    session: AsyncSession,
    *,
    business_id: int,
    user_id: int,
    debtor_id: int | None,
    due_at: date | None,
    payment_terms_days: int,
    lines: list[tuple[str, float, int, int]],  # (desc, qty, unit_price_centimes, vat_rate_bps)
    notes: str | None,
    idempotency_key: str | None = None,
) -> Invoice:
    if idempotency_key:
        existing = (
            await session.execute(
                select(Invoice).where(
                    Invoice.business_id == business_id,
                    Invoice.idempotency_key == idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing:
            return existing

    invoice = Invoice(
        business_id=business_id,
        debtor_id=debtor_id,
        status=InvoiceStatus.DRAFT,
        due_at=due_at,
        payment_terms_days=payment_terms_days,
        created_by_user_id=user_id,
        notes=notes,
        idempotency_key=idempotency_key,
    )
    session.add(invoice)
    await session.flush()

    subtotal = 0
    vat_total = 0
    for desc, qty, unit_price, vat_bps in lines:
        line_subtotal = int((Decimal(str(qty)) * Decimal(unit_price)).to_integral_value())
        vat_part, _ = apply_vat(line_subtotal, vat_bps)
        session.add(
            InvoiceLine(
                invoice_id=invoice.id,
                description=desc,
                qty=Decimal(str(qty)),
                unit_price_centimes=unit_price,
                vat_rate_bps=vat_bps,
                line_subtotal_centimes=line_subtotal,
            )
        )
        subtotal += line_subtotal
        vat_total += vat_part

    invoice.subtotal_centimes = subtotal
    invoice.vat_centimes = vat_total
    invoice.total_centimes = subtotal + vat_total
    await session.flush()
    return invoice


async def issue_invoice(session: AsyncSession, *, business_id: int, invoice_id: int) -> Invoice:
    invoice = (
        await session.execute(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.business_id == business_id,
            )
        )
    ).scalar_one_or_none()
    if invoice is None:
        raise NotFound("invoice_not_found")
    if invoice.status != InvoiceStatus.DRAFT:
        raise Conflict("only_draft_invoices_can_be_issued")

    invoice.number = await allocate_invoice_number(session, business_id=business_id)
    invoice.issued_at = utcnow()
    invoice.status = InvoiceStatus.ISSUED
    if invoice.due_at is None and invoice.payment_terms_days:
        invoice.due_at = utcnow().date() + timedelta(days=invoice.payment_terms_days)

    # Emit corresponding DEBT event if there's a debtor.
    if invoice.debtor_id is not None:
        session.add(
            DebtEvent(
                business_id=business_id,
                debtor_id=invoice.debtor_id,
                kind=DebtEventKind.DEBT,
                amount_centimes=invoice.total_centimes,
                due_date=invoice.due_at,
                reference=invoice.number,
                related_invoice_id=invoice.id,
                source="order",
            )
        )
        await upsert_debtor_balance(session, business_id=business_id, debtor_id=invoice.debtor_id)

    await session.flush()
    return invoice


async def apply_invoice_payment(
    session: AsyncSession,
    *,
    business_id: int,
    user_id: int,
    invoice_id: int,
    amount_centimes: int,
    method: str,
    paid_at: datetime | None,
    reference: str | None,
    idempotency_key: str | None = None,
) -> Payment:
    if idempotency_key:
        existing = (
            await session.execute(
                select(Payment).where(
                    Payment.business_id == business_id,
                    Payment.idempotency_key == idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing:
            return existing

    invoice = (
        await session.execute(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.business_id == business_id,
            )
        )
    ).scalar_one_or_none()
    if invoice is None:
        raise NotFound("invoice_not_found")
    if invoice.status not in (InvoiceStatus.ISSUED, InvoiceStatus.PARTIAL):
        raise Conflict("invoice_not_payable")

    pmt = Payment(
        business_id=business_id,
        debtor_id=invoice.debtor_id,
        invoice_id=invoice.id,
        method=method,
        amount_centimes=amount_centimes,
        paid_at=paid_at or utcnow(),
        reference=reference,
        idempotency_key=idempotency_key,
    )
    session.add(pmt)

    # Sum previous payments on this invoice.
    paid_so_far = (
        await session.execute(
            select(func.coalesce(func.sum(Payment.amount_centimes), 0)).where(
                Payment.invoice_id == invoice.id
            )
        )
    ).scalar_one()

    if int(paid_so_far) >= invoice.total_centimes:
        invoice.status = InvoiceStatus.PAID
    else:
        invoice.status = InvoiceStatus.PARTIAL

    if invoice.debtor_id is not None:
        session.add(
            DebtEvent(
                business_id=business_id,
                debtor_id=invoice.debtor_id,
                kind=DebtEventKind.PAYMENT,
                amount_centimes=amount_centimes,
                reference=invoice.number,
                related_invoice_id=invoice.id,
                source="order",
                created_by_user_id=user_id,
            )
        )
        await upsert_debtor_balance(session, business_id=business_id, debtor_id=invoice.debtor_id)

    await session.flush()
    return pmt


async def soft_delete_debtor(session: AsyncSession, *, business_id: int, debtor_id: int) -> None:
    debtor = (
        await session.execute(
            select(Debtor).where(
                Debtor.id == debtor_id,
                Debtor.business_id == business_id,
                Debtor.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if debtor is None:
        raise NotFound("debtor_not_found")
    debtor.deleted_at = utcnow()
    await session.flush()

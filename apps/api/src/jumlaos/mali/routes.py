"""Mali HTTP routes: debtors, debt events, dashboard, aging, invoices."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from jumlaos.core.audit import record as audit_record
from jumlaos.core.context import RequestContext
from jumlaos.core.deps import current_context, db
from jumlaos.core.errors import Forbidden, NotFound
from jumlaos.core.models import Role
from jumlaos.mali import service
from jumlaos.mali.models import (
    DebtBalance,
    DebtEvent,
    DebtEventSource,
    Debtor,
    Invoice,
    InvoiceLine,
)
from jumlaos.mali.schemas import (
    AgingResponse,
    AgingRow,
    DebtEventCreate,
    DebtEventOut,
    DebtEventVoid,
    DebtorCreate,
    DebtorListResponse,
    DebtorOut,
    DebtorUpdate,
    InvoiceCreate,
    InvoiceLineOut,
    InvoiceOut,
    InvoicePaymentCreate,
    MaliDashboard,
)
from jumlaos.shared.phone import PhoneError, normalize_ma

router = APIRouter()


def _block_driver(ctx: RequestContext) -> None:
    if ctx.role == Role.DRIVER:
        raise Forbidden("driver_role_cannot_access_mali")


def _require_write(ctx: RequestContext) -> None:
    if ctx.role in {Role.DRIVER, Role.ACCOUNTANT}:
        raise Forbidden(f"{ctx.role.value}_role_is_read_only_for_this_action")


def _debtor_out(debtor: Debtor, bal: DebtBalance | None) -> DebtorOut:
    return DebtorOut(
        id=debtor.id,
        phone=debtor.phone_e164,
        display_name=debtor.display_name,
        city=debtor.city,
        address_text=debtor.address_text,
        credit_limit_centimes=debtor.credit_limit_centimes,
        payment_terms_days=debtor.payment_terms_days,
        risk_score=debtor.risk_score,
        is_blocked=debtor.is_blocked,
        outstanding_centimes=bal.total_outstanding_centimes if bal else 0,
        days_past_due=bal.days_past_due if bal else 0,
        last_payment_at=bal.last_payment_at if bal else None,
    )


# ---- Debtors ----


@router.get("/debtors", response_model=DebtorListResponse)
async def list_debtors(
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> DebtorListResponse:
    _block_driver(ctx)
    stmt = (
        select(Debtor, DebtBalance)
        .outerjoin(
            DebtBalance,
            (DebtBalance.business_id == Debtor.business_id) & (DebtBalance.debtor_id == Debtor.id),
        )
        .where(Debtor.business_id == ctx.business_id, Debtor.deleted_at.is_(None))
        .order_by(Debtor.display_name.asc())
        .limit(limit)
        .offset(offset)
    )
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            (func.lower(Debtor.display_name).like(like)) | (Debtor.phone_e164.like(f"%{q}%"))
        )
    rows = (await session.execute(stmt)).all()

    count_stmt = (
        select(func.count())
        .select_from(Debtor)
        .where(Debtor.business_id == ctx.business_id, Debtor.deleted_at.is_(None))
    )
    total = (await session.execute(count_stmt)).scalar_one()
    outstanding_stmt = select(
        func.coalesce(func.sum(DebtBalance.total_outstanding_centimes), 0)
    ).where(DebtBalance.business_id == ctx.business_id)
    outstanding_total = (await session.execute(outstanding_stmt)).scalar_one()

    return DebtorListResponse(
        items=[_debtor_out(d, b) for d, b in rows],
        total=int(total or 0),
        outstanding_total_centimes=int(outstanding_total or 0),
    )


@router.post("/debtors", response_model=DebtorOut, status_code=201)
async def create_debtor(
    body: DebtorCreate,
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> DebtorOut:
    _require_write(ctx)
    try:
        phone = normalize_ma(body.phone)
    except PhoneError as exc:
        raise Forbidden("invalid_phone") from exc

    debtor = await service.create_debtor(
        session,
        business_id=ctx.business_id,
        phone_e164=phone,
        display_name=body.display_name,
        city=body.city,
        address_text=body.address_text,
        credit_limit_centimes=body.credit_limit_centimes,
        payment_terms_days=body.payment_terms_days,
        notes=body.notes,
    )
    await audit_record(
        session,
        business_id=ctx.business_id,
        user_id=ctx.user_id,
        action="mali.debtor.create",
        entity_type="debtor",
        entity_id=str(debtor.id),
        after={"display_name": debtor.display_name, "phone": debtor.phone_e164},
    )
    return _debtor_out(debtor, None)


@router.get("/debtors/{debtor_id}", response_model=DebtorOut)
async def get_debtor(
    debtor_id: int,
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> DebtorOut:
    _block_driver(ctx)
    stmt = (
        select(Debtor, DebtBalance)
        .outerjoin(
            DebtBalance,
            (DebtBalance.business_id == Debtor.business_id) & (DebtBalance.debtor_id == Debtor.id),
        )
        .where(
            Debtor.id == debtor_id,
            Debtor.business_id == ctx.business_id,
            Debtor.deleted_at.is_(None),
        )
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        raise NotFound("debtor_not_found")
    return _debtor_out(row[0], row[1])


@router.patch("/debtors/{debtor_id}", response_model=DebtorOut)
async def update_debtor(
    debtor_id: int,
    body: DebtorUpdate,
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> DebtorOut:
    _require_write(ctx)
    debtor = (
        await session.execute(
            select(Debtor).where(
                Debtor.id == debtor_id,
                Debtor.business_id == ctx.business_id,
                Debtor.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if debtor is None:
        raise NotFound("debtor_not_found")

    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(debtor, k, v)
    if "display_name" in data:
        debtor.alias_normalized = " ".join(debtor.display_name.strip().lower().split())
    await session.flush()
    bal = (
        await session.execute(
            select(DebtBalance).where(
                DebtBalance.business_id == ctx.business_id,
                DebtBalance.debtor_id == debtor.id,
            )
        )
    ).scalar_one_or_none()
    return _debtor_out(debtor, bal)


@router.delete("/debtors/{debtor_id}", status_code=204, response_class=Response)
async def delete_debtor(
    debtor_id: int,
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> Response:
    _require_write(ctx)
    if ctx.role != Role.OWNER:
        raise Forbidden("only_owner_can_delete_debtor")
    await service.soft_delete_debtor(session, business_id=ctx.business_id, debtor_id=debtor_id)
    return Response(status_code=204)


# ---- Debt events ----


@router.post("/debt-events", response_model=DebtEventOut, status_code=201)
async def create_debt_event(
    body: DebtEventCreate,
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> DebtEventOut:
    _require_write(ctx)
    evt = await service.record_debt_event(
        session,
        business_id=ctx.business_id,
        user_id=ctx.user_id,
        debtor_id=body.debtor_id,
        kind=body.kind,
        amount_centimes=body.amount_centimes,
        due_date=body.due_date,
        reference=body.reference,
        raw_message=body.raw_message,
        source=body.source.value if isinstance(body.source, DebtEventSource) else body.source,
    )
    await audit_record(
        session,
        business_id=ctx.business_id,
        user_id=ctx.user_id,
        action=f"mali.debt_event.{body.kind.value}",
        entity_type="debt_event",
        entity_id=str(evt.id),
        after={"debtor_id": evt.debtor_id, "amount": evt.amount_centimes},
    )
    return DebtEventOut(
        id=evt.id,
        debtor_id=evt.debtor_id,
        kind=evt.kind,
        amount_centimes=evt.amount_centimes,
        due_date=evt.due_date,
        reference=evt.reference,
        voided=evt.voided,
        created_at=evt.created_at,
    )


@router.post("/debt-events/{event_id}/void", response_model=DebtEventOut)
async def void_debt_event(
    event_id: int,
    body: DebtEventVoid,
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> DebtEventOut:
    _require_write(ctx)
    evt = await service.void_debt_event(
        session,
        business_id=ctx.business_id,
        user_id=ctx.user_id,
        event_id=event_id,
        reason=body.reason,
    )
    await audit_record(
        session,
        business_id=ctx.business_id,
        user_id=ctx.user_id,
        action="mali.debt_event.void",
        entity_type="debt_event",
        entity_id=str(evt.id),
        after={"reason": body.reason},
    )
    return DebtEventOut(
        id=evt.id,
        debtor_id=evt.debtor_id,
        kind=evt.kind,
        amount_centimes=evt.amount_centimes,
        due_date=evt.due_date,
        reference=evt.reference,
        voided=evt.voided,
        created_at=evt.created_at,
    )


@router.get("/debtors/{debtor_id}/debt-events", response_model=list[DebtEventOut])
async def list_debt_events(
    debtor_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> list[DebtEventOut]:
    _block_driver(ctx)
    rows = (
        (
            await session.execute(
                select(DebtEvent)
                .where(
                    DebtEvent.business_id == ctx.business_id,
                    DebtEvent.debtor_id == debtor_id,
                )
                .order_by(DebtEvent.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [
        DebtEventOut(
            id=e.id,
            debtor_id=e.debtor_id,
            kind=e.kind,
            amount_centimes=e.amount_centimes,
            due_date=e.due_date,
            reference=e.reference,
            voided=e.voided,
            created_at=e.created_at,
        )
        for e in rows
    ]


# ---- Dashboard + aging ----


@router.get("/dashboard/mali", response_model=MaliDashboard)
async def dashboard(
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> MaliDashboard:
    _block_driver(ctx)
    totals = await service.mali_dashboard(session, business_id=ctx.business_id)

    top_stmt = (
        select(Debtor, DebtBalance)
        .join(
            DebtBalance,
            (DebtBalance.business_id == Debtor.business_id) & (DebtBalance.debtor_id == Debtor.id),
        )
        .where(
            Debtor.business_id == ctx.business_id,
            Debtor.deleted_at.is_(None),
            DebtBalance.total_outstanding_centimes > 0,
        )
        .order_by(DebtBalance.total_outstanding_centimes.desc())
        .limit(5)
    )
    top = (await session.execute(top_stmt)).all()
    return MaliDashboard(
        total_outstanding_centimes=totals["total_outstanding_centimes"],
        debtor_count=totals["debtor_count"],
        overdue_debtor_count=totals["overdue_debtor_count"],
        collections_30d_centimes=totals["collections_30d_centimes"],
        top_debtors=[_debtor_out(d, b) for d, b in top],
    )


@router.get("/aging", response_model=AgingResponse)
async def aging(
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> AgingResponse:
    _block_driver(ctx)
    rows = await service.compute_aging(session, business_id=ctx.business_id)
    return AgingResponse(
        rows=[
            AgingRow.model_validate({"bucket": b, "debtor_count": c, "total_centimes": t})
            for b, c, t in rows
        ],
        total_outstanding_centimes=sum(t for _, _, t in rows),
    )


# ---- Invoices ----


def _invoice_out(invoice: Invoice, lines: list[InvoiceLine]) -> InvoiceOut:
    return InvoiceOut(
        id=invoice.id,
        number=invoice.number,
        status=invoice.status,
        debtor_id=invoice.debtor_id,
        issued_at=invoice.issued_at,
        due_at=invoice.due_at,
        subtotal_centimes=invoice.subtotal_centimes,
        vat_centimes=invoice.vat_centimes,
        total_centimes=invoice.total_centimes,
        currency=invoice.currency,
        lines=[
            InvoiceLineOut(
                id=line.id,
                description=line.description,
                qty=float(line.qty),
                unit_price_centimes=line.unit_price_centimes,
                vat_rate_bps=line.vat_rate_bps,
                line_subtotal_centimes=line.line_subtotal_centimes,
            )
            for line in lines
        ],
    )


async def _load_invoice(
    session: AsyncSession, *, business_id: int, invoice_id: int
) -> tuple[Invoice, list[InvoiceLine]]:
    invoice = (
        await session.execute(
            select(Invoice).where(Invoice.id == invoice_id, Invoice.business_id == business_id)
        )
    ).scalar_one_or_none()
    if invoice is None:
        raise NotFound("invoice_not_found")
    lines = (
        (
            await session.execute(
                select(InvoiceLine)
                .where(InvoiceLine.invoice_id == invoice.id)
                .order_by(InvoiceLine.id.asc())
            )
        )
        .scalars()
        .all()
    )
    return invoice, list(lines)


@router.post("/invoices", response_model=InvoiceOut, status_code=201)
async def create_invoice(
    body: InvoiceCreate,
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> InvoiceOut:
    _require_write(ctx)
    invoice = await service.create_invoice_draft(
        session,
        business_id=ctx.business_id,
        user_id=ctx.user_id,
        debtor_id=body.debtor_id,
        due_at=body.due_at,
        payment_terms_days=body.payment_terms_days,
        lines=[
            (line.description, line.qty, line.unit_price_centimes, line.vat_rate_bps)
            for line in body.lines
        ],
        notes=body.notes,
    )
    await audit_record(
        session,
        business_id=ctx.business_id,
        user_id=ctx.user_id,
        action="mali.invoice.draft",
        entity_type="invoice",
        entity_id=str(invoice.id),
        after={"total": invoice.total_centimes, "debtor_id": invoice.debtor_id},
    )
    _, lines = await _load_invoice(session, business_id=ctx.business_id, invoice_id=invoice.id)
    return _invoice_out(invoice, lines)


@router.get("/invoices", response_model=list[InvoiceOut])
async def list_invoices(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> list[InvoiceOut]:
    _block_driver(ctx)
    rows = (
        (
            await session.execute(
                select(Invoice)
                .where(Invoice.business_id == ctx.business_id)
                .order_by(Invoice.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    out: list[InvoiceOut] = []
    for inv in rows:
        _, lines = await _load_invoice(session, business_id=ctx.business_id, invoice_id=inv.id)
        out.append(_invoice_out(inv, lines))
    return out


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: int,
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> InvoiceOut:
    _block_driver(ctx)
    invoice, lines = await _load_invoice(
        session, business_id=ctx.business_id, invoice_id=invoice_id
    )
    return _invoice_out(invoice, lines)


@router.post("/invoices/{invoice_id}/issue", response_model=InvoiceOut)
async def issue_invoice(
    invoice_id: int,
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> InvoiceOut:
    _require_write(ctx)
    invoice = await service.issue_invoice(
        session, business_id=ctx.business_id, invoice_id=invoice_id
    )
    await audit_record(
        session,
        business_id=ctx.business_id,
        user_id=ctx.user_id,
        action="mali.invoice.issue",
        entity_type="invoice",
        entity_id=str(invoice.id),
        after={"number": invoice.number, "total": invoice.total_centimes},
    )
    _, lines = await _load_invoice(session, business_id=ctx.business_id, invoice_id=invoice.id)
    return _invoice_out(invoice, lines)


@router.post("/invoices/{invoice_id}/payment", response_model=InvoiceOut)
async def invoice_payment(
    invoice_id: int,
    body: InvoicePaymentCreate,
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> InvoiceOut:
    _require_write(ctx)
    await service.apply_invoice_payment(
        session,
        business_id=ctx.business_id,
        user_id=ctx.user_id,
        invoice_id=invoice_id,
        amount_centimes=body.amount_centimes,
        method=body.method.value,
        paid_at=body.paid_at,
        reference=body.reference,
    )
    invoice, lines = await _load_invoice(
        session, business_id=ctx.business_id, invoice_id=invoice_id
    )
    await audit_record(
        session,
        business_id=ctx.business_id,
        user_id=ctx.user_id,
        action="mali.invoice.payment",
        entity_type="invoice",
        entity_id=str(invoice_id),
        after={"amount": body.amount_centimes, "status": invoice.status.value},
    )
    return _invoice_out(invoice, lines)


# ---- DGI CSV export ----


@router.get("/tax-periods/{yyyymm}/export.csv")
async def export_tax_period(
    yyyymm: str,
    ctx: RequestContext = Depends(current_context),
    session: AsyncSession = Depends(db),
) -> StreamingResponse:
    """Export issued invoices for a given `YYYY-MM` period as DGI-conformant CSV.

    Columns follow DGI's "Etat des factures" format. Archive retention is
    handled server-side (R2 immutable bucket policy, 10-year TTL).
    """
    _block_driver(ctx)
    try:
        year_s, month_s = yyyymm.split("-")
        year, month = int(year_s), int(month_s)
        if not 1 <= month <= 12:
            raise ValueError("bad_month")
    except ValueError as exc:
        raise NotFound("invalid_period_format") from exc

    stmt = (
        select(Invoice)
        .where(
            Invoice.business_id == ctx.business_id,
            Invoice.status != "draft",
            func.extract("year", Invoice.issued_at) == year,
            func.extract("month", Invoice.issued_at) == month,
        )
        .order_by(Invoice.number.asc())
    )
    rows = (await session.execute(stmt)).scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            "numero_facture",
            "date_emission",
            "ice_client",
            "montant_ht",
            "tva",
            "montant_ttc",
            "statut",
        ]
    )
    for inv in rows:
        writer.writerow(
            [
                inv.number or "",
                inv.issued_at.date().isoformat() if inv.issued_at else "",
                "",  # client ICE not captured in MVP; add when debtor row includes it
                f"{inv.subtotal_centimes / 100:.2f}",
                f"{inv.vat_centimes / 100:.2f}",
                f"{inv.total_centimes / 100:.2f}",
                inv.status.value,
            ]
        )

    buffer.seek(0)
    filename = f"jumlaos-dgi-{ctx.business_id}-{yyyymm}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

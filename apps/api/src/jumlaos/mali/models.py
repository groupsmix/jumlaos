"""Mali tables: debtors, debt events, debt balances, invoices, payments."""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jumlaos.core.db import Base
from jumlaos.core.models import SoftDeleteMixin, TimestampMixin


class DebtEventKind(str, enum.Enum):
    DEBT = "debt"
    PAYMENT = "payment"
    ADJUSTMENT = "adjustment"
    WRITEOFF = "writeoff"
    REFUND = "refund"


class DebtEventSource(str, enum.Enum):
    WHATSAPP = "whatsapp"
    WEB = "web"
    ORDER = "order"
    IMPORT = "import"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    PARTIAL = "partial"
    VOID = "void"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"
    CMI = "cmi"
    CASHPLUS = "cashplus"
    OTHER = "other"


class TaxPeriodStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class Debtor(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "debtors"
    __table_args__ = (
        UniqueConstraint("business_id", "phone_e164", name="uq_debtors_business_phone"),
        Index("ix_debtors_business_alias", "business_id", "alias_normalized"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phone_e164: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    alias_normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ice_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    credit_limit_centimes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    balance: Mapped[DebtBalance] = relationship(
        back_populates="debtor", uselist=False, cascade="all, delete-orphan"
    )


class DebtEvent(Base):
    """Immutable ledger row. Voids create a follow-up voided row, never mutate."""

    __tablename__ = "debt_events"
    __table_args__ = (
        Index("ix_debt_events_bd_created", "business_id", "debtor_id", "created_at"),
        Index(
            "ix_debt_events_due",
            "business_id",
            "due_date",
            postgresql_where="kind = 'debt' AND voided = false",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    debtor_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("debtors.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[DebtEventKind] = mapped_column(
        Enum(DebtEventKind, name="debt_event_kind"), nullable=False
    )
    # positive = debt, negative = payment. Always explicit; the sign mirrors kind.
    amount_centimes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[DebtEventSource] = mapped_column(
        Enum(DebtEventSource, name="debt_event_source"),
        default=DebtEventSource.WEB,
        nullable=False,
    )
    raw_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_invoice_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )
    related_order_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    voided: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    voided_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DebtBalance(Base):
    """Materialized projection. Recomputable from debt_events at any time."""

    __tablename__ = "debt_balances"

    business_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    debtor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("debtors.id", ondelete="CASCADE"),
        primary_key=True,
    )
    total_outstanding_centimes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    oldest_unpaid_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    days_past_due: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_payment_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    debtor: Mapped[Debtor] = relationship(back_populates="balance")


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("business_id", "number", name="uq_invoices_business_number"),
        Index("ix_invoices_business_status", "business_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    debtor_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("debtors.id", ondelete="SET NULL"), nullable=True
    )
    number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"),
        default=InvoiceStatus.DRAFT,
        nullable=False,
    )
    subtotal_centimes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    vat_centimes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_centimes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="MAD", nullable=False)
    pdf_r2_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    lines: Mapped[list[InvoiceLine]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    qty: Mapped[Any] = mapped_column(Numeric(14, 4), nullable=False)
    unit_price_centimes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    vat_rate_bps: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)
    line_subtotal_centimes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    invoice: Mapped[Invoice] = relationship(back_populates="lines")


class InvoiceNumberCounter(Base):
    """Per-business, per-year monotonic invoice counter."""

    __tablename__ = "invoice_number_counters"

    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), primary_key=True
    )
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_seq: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (Index("ix_payments_business_debtor", "business_id", "debtor_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    debtor_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("debtors.id", ondelete="SET NULL"), nullable=True
    )
    invoice_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method"), nullable=False
    )
    amount_centimes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attachment_r2_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    debtor_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("debtors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    template_name: Mapped[str] = mapped_column(String(64), nullable=False)
    locale: Mapped[str] = mapped_column(String(8), default="ar-MA", nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    wa_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class TaxPeriod(Base, TimestampMixin):
    __tablename__ = "tax_periods"
    __table_args__ = (
        UniqueConstraint("business_id", "period_start", name="uq_tax_periods_business_start"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[TaxPeriodStatus] = mapped_column(
        Enum(TaxPeriodStatus, name="tax_period_status"),
        default=TaxPeriodStatus.OPEN,
        nullable=False,
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    csv_export_r2_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

"""Pydantic schemas for Mali routes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from jumlaos.mali.models import DebtEventKind, DebtEventSource, InvoiceStatus, PaymentMethod

# ---- Debtors ----


class DebtorCreate(BaseModel):
    phone: str = Field(min_length=5, max_length=25)
    display_name: str = Field(min_length=1, max_length=200)
    city: str | None = None
    address_text: str | None = None
    credit_limit_centimes: int = Field(default=0, ge=0)
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    notes: str | None = None


class DebtorUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    city: str | None = None
    address_text: str | None = None
    credit_limit_centimes: int | None = Field(default=None, ge=0)
    payment_terms_days: int | None = Field(default=None, ge=0, le=365)
    is_blocked: bool | None = None
    notes: str | None = None


class DebtorOut(BaseModel):
    id: int
    phone: str
    display_name: str
    city: str | None
    address_text: str | None
    credit_limit_centimes: int
    payment_terms_days: int
    risk_score: int
    is_blocked: bool
    outstanding_centimes: int
    days_past_due: int
    last_payment_at: datetime | None


class DebtorListResponse(BaseModel):
    items: list[DebtorOut]
    total: int
    outstanding_total_centimes: int


# ---- Debt events ----


class DebtEventCreate(BaseModel):
    debtor_id: int
    kind: DebtEventKind
    amount_centimes: int = Field(
        gt=0, description="Absolute amount in centimes; sign comes from kind"
    )
    due_date: date | None = None
    reference: str | None = Field(default=None, max_length=128)
    raw_message: str | None = None
    source: DebtEventSource = DebtEventSource.WEB

    @field_validator("amount_centimes")
    @classmethod
    def _check_amount(cls, v: int) -> int:
        if v > 10_000_000_000_000:
            raise ValueError("amount exceeds maximum")
        return v


class DebtEventOut(BaseModel):
    id: int
    debtor_id: int
    kind: DebtEventKind
    amount_centimes: int
    due_date: date | None
    reference: str | None
    voided: bool
    created_at: datetime


class DebtEventVoid(BaseModel):
    reason: str = Field(min_length=1, max_length=200)


# ---- Dashboard ----


class MaliDashboard(BaseModel):
    total_outstanding_centimes: int
    debtor_count: int
    overdue_debtor_count: int
    collections_30d_centimes: int
    top_debtors: list[DebtorOut]


# ---- Aging ----


AgingBucket = Literal["current", "1_30", "31_60", "61_90", "90_plus"]


class AgingRow(BaseModel):
    bucket: AgingBucket
    debtor_count: int
    total_centimes: int


class AgingResponse(BaseModel):
    rows: list[AgingRow]
    total_outstanding_centimes: int


# ---- Invoices ----


class InvoiceLineIn(BaseModel):
    description: str = Field(min_length=1, max_length=300)
    qty: float = Field(gt=0)
    unit_price_centimes: int = Field(ge=0)
    vat_rate_bps: int = Field(default=2000, ge=0, le=10000)


class InvoiceLineOut(InvoiceLineIn):
    id: int
    line_subtotal_centimes: int


class InvoiceCreate(BaseModel):
    debtor_id: int | None = None
    due_at: date | None = None
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    lines: list[InvoiceLineIn] = Field(min_length=1)
    notes: str | None = None


class InvoiceOut(BaseModel):
    id: int
    number: str | None
    status: InvoiceStatus
    debtor_id: int | None
    issued_at: datetime | None
    due_at: date | None
    subtotal_centimes: int
    vat_centimes: int
    total_centimes: int
    currency: str
    lines: list[InvoiceLineOut]


class InvoicePaymentCreate(BaseModel):
    amount_centimes: int = Field(gt=0)
    method: PaymentMethod = PaymentMethod.CASH
    paid_at: datetime | None = None
    reference: str | None = None

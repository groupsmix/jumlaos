"""Talab tables — schema defined now, full pipeline ships at month 4."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.orm import Mapped, mapped_column

from jumlaos.core.db import Base
from jumlaos.core.models import TimestampMixin


class OrderIntakeSource(str, enum.Enum):
    WHATSAPP = "whatsapp"
    WEB = "web"
    PHONE = "phone"


class OrderIntakeStatus(str, enum.Enum):
    QUEUED = "queued"
    PARSED = "parsed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PICKED = "picked"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUSED = "refused"


class PaymentMethod(str, enum.Enum):
    CASH_ON_DELIVERY = "cash_on_delivery"
    CREDIT = "credit"
    PREPAID = "prepaid"
    BANK_TRANSFER = "bank_transfer"


class OrderIntake(Base):
    __tablename__ = "order_intakes"
    __table_args__ = (Index("ix_order_intakes_bus_created", "business_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[OrderIntakeSource] = mapped_column(
        Enum(OrderIntakeSource, name="order_intake_source"), nullable=False
    )
    from_phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_r2_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    image_r2_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    parsed: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    parser_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[OrderIntakeStatus] = mapped_column(
        Enum(OrderIntakeStatus, name="order_intake_status"),
        default=OrderIntakeStatus.QUEUED,
        nullable=False,
    )
    wa_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("business_id", "number", name="uq_orders_business_number"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    debtor_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("debtors.id", ondelete="SET NULL"), nullable=True
    )
    order_intake_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("order_intakes.id", ondelete="SET NULL"), nullable=True
    )
    number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), default=OrderStatus.DRAFT, nullable=False
    )
    delivery_window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivery_window_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivery_address_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_lat: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    delivery_lng: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    driver_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="order_payment_method"),
        default=PaymentMethod.CREDIT,
        nullable=False,
    )
    subtotal_centimes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_centimes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OrderLine(Base):
    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    qty_requested: Mapped[Any] = mapped_column(Numeric(14, 4), nullable=False)
    qty_picked: Mapped[Any | None] = mapped_column(Numeric(14, 4), nullable=True)
    qty_delivered: Mapped[Any | None] = mapped_column(Numeric(14, 4), nullable=True)
    unit_price_centimes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    line_total_centimes: Mapped[int] = mapped_column(BigInteger, nullable=False)


class WaInboundMessage(Base):
    """Raw WhatsApp inbound webhook payload — replayable."""

    __tablename__ = "wa_inbound_messages"
    __table_args__ = (Index("ix_wa_inbound_bus_received", "business_id", "received_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True
    )
    wa_message_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    from_phone_e164: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

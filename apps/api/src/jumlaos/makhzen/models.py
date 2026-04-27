"""Makhzen tables — schema defined now, full features ship at month 6."""

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
from sqlalchemy.orm import Mapped, mapped_column

from jumlaos.core.db import Base
from jumlaos.core.models import TimestampMixin


class ProductUnit(str, enum.Enum):
    PIECE = "piece"
    KG = "kg"
    LITER = "liter"
    BOX = "box"
    DOZEN = "dozen"
    BOTTLE = "bottle"


class ProductStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class StockMovementKind(str, enum.Enum):
    RECEIPT = "receipt"
    SALE = "sale"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"
    ADJUSTMENT = "adjustment"
    WRITEOFF = "writeoff"
    EXPIRY = "expiry"


class Warehouse(Base, TimestampMixin):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[Any | None] = mapped_column(Numeric(10, 7), nullable=True)
    lng: Mapped[Any | None] = mapped_column(Numeric(10, 7), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("business_id", "sku", name="uq_products_business_sku"),
        Index("ix_products_business_barcode", "business_id", "barcode_ean"),
        Index("ix_products_business_name_norm", "business_id", "name_normalized"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    barcode_ean: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_fr: Mapped[str | None] = mapped_column(String(200), nullable=True)
    name_normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[ProductUnit] = mapped_column(
        Enum(ProductUnit, name="product_unit"), default=ProductUnit.PIECE, nullable=False
    )
    conversion_to_base_qty: Mapped[Any] = mapped_column(Numeric(14, 4), default=1, nullable=False)
    default_purchase_price_centimes: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )
    default_sell_price_centimes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    is_perishable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_shelf_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vat_rate_bps: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)
    image_r2_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"),
        default=ProductStatus.ACTIVE,
        nullable=False,
    )


class StockLot(Base, TimestampMixin):
    __tablename__ = "stock_lots"
    __table_args__ = (
        Index(
            "ix_stock_lots_bus_product_expiry",
            "business_id",
            "product_id",
            "expires_at",
            postgresql_where="qty_remaining > 0",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    qty_remaining: Mapped[Any] = mapped_column(Numeric(14, 4), nullable=False)
    unit_cost_centimes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    lot_number: Mapped[str | None] = mapped_column(String(64), nullable=True)


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        Index("ix_stock_movements_bus_product_ts", "business_id", "product_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    lot_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stock_lots.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[StockMovementKind] = mapped_column(
        Enum(StockMovementKind, name="stock_movement_kind"), nullable=False
    )
    qty: Mapped[Any] = mapped_column(Numeric(14, 4), nullable=False)  # signed
    unit_cost_centimes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    related_order_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    related_invoice_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    voided: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

"""Add idempotency_key to mutating tables

Revision ID: 0004_idempotency
Revises: 0003_triggers
Create Date: 2026-04-27 00:00:03.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_idempotency"
down_revision = "0003_triggers"
branch_labels = None
depends_on = None

TABLES = ["debt_events", "payments", "invoices", "orders"]


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("idempotency_key", sa.String(128)))
        op.create_index(
            f"uq_{table}_business_idemp",
            table,
            ["business_id", "idempotency_key"],
            unique=True,
            postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_index(f"uq_{table}_business_idemp", table_name=table)
        op.drop_column(table, "idempotency_key")

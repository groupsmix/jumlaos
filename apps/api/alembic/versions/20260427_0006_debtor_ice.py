"""Add Debtor ICE number

Revision ID: 0006_debtor_ice
Revises: 0005_auth_and_wa
Create Date: 2026-04-27 00:00:05.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0006_debtor_ice"
down_revision = "0005_auth_and_wa"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("debtors", sa.Column("ice_number", sa.String(32)))
    op.create_index("ix_invoices_business_status_issued_at", "invoices", ["business_id", "issued_at"], postgresql_where=sa.text("status != 'draft'"))

def downgrade() -> None:
    op.drop_index("ix_invoices_business_status_issued_at", table_name="invoices")
    op.drop_column("debtors", "ice_number")

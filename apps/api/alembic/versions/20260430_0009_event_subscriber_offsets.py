"""F27: per-subscriber event offsets table

Revision ID: 0009_event_sub_offsets
Revises: 0008_audit_outbox_idemp
Create Date: 2026-04-30 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_event_sub_offsets"
down_revision = "0008_audit_outbox_idemp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_subscriber_offsets",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("subscriber_name", sa.String(64), nullable=False),
        sa.Column(
            "business_id",
            sa.BigInteger(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("last_event_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("subscriber_name", "business_id", name="uq_event_sub_offsets_sub_biz"),
    )
    op.create_index(
        "ix_event_sub_offsets_subscriber",
        "event_subscriber_offsets",
        ["subscriber_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_event_sub_offsets_subscriber", table_name="event_subscriber_offsets")
    op.drop_table("event_subscriber_offsets")

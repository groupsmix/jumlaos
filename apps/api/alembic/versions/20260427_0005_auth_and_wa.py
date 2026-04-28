"""F-12 and F-14: Refresh tokens and whatsapp_phone_number_id

Revision ID: 0005_auth_and_wa
Revises: 0004_idempotency
Create Date: 2026-04-27 00:00:04.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005_auth_and_wa"
down_revision = "0004_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # F-14
    op.add_column("businesses", sa.Column("whatsapp_phone_number_id", sa.String(50)))
    op.create_unique_constraint(
        "uq_businesses_whatsapp", "businesses", ["whatsapp_phone_number_id"]
    )

    # F-12
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("jti", sa.String(36), unique=True, nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_constraint("uq_businesses_whatsapp", "businesses", type_="unique")
    op.drop_column("businesses", "whatsapp_phone_number_id")

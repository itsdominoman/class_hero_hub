"""add pending invite scope to user refresh sessions

Revision ID: a4e5f6b7c8d9
Revises: a001c7e9d4f2
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa


revision = "a4e5f6b7c8d9"
down_revision = "a001c7e9d4f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_refresh_sessions",
        sa.Column("admission_kind", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "user_refresh_sessions",
        sa.Column("admission_token_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "user_refresh_sessions",
        sa.Column("admission_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_user_refresh_sessions_admission_context",
        "user_refresh_sessions",
        "(admission_kind IS NULL AND admission_token_hash IS NULL AND admission_expires_at IS NULL) OR "
        "(admission_kind IN ('staff_invite', 'guardian_invite') "
        "AND admission_token_hash IS NOT NULL AND admission_expires_at IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_user_refresh_sessions_admission_context",
        "user_refresh_sessions",
        type_="check",
    )
    op.drop_column("user_refresh_sessions", "admission_expires_at")
    op.drop_column("user_refresh_sessions", "admission_token_hash")
    op.drop_column("user_refresh_sessions", "admission_kind")

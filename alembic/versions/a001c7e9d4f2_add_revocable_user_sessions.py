"""add revocable user refresh sessions

Revision ID: a001c7e9d4f2
Revises: f8a9b0c1d2e3
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "a001c7e9d4f2"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_refresh_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_refresh_token_hash", sa.String(length=64), nullable=True),
        sa.Column("generation", sa.Integer(), server_default="1", nullable=False),
        sa.Column("client_type", sa.String(length=16), server_default="browser", nullable=False),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(length=32), nullable=True),
        sa.CheckConstraint("generation >= 1", name="ck_user_refresh_sessions_generation"),
        sa.CheckConstraint(
            "client_type IN ('browser', 'android')",
            name="ck_user_refresh_sessions_client_type",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_refresh_sessions_refresh_token_hash",
        "user_refresh_sessions",
        ["refresh_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_user_refresh_sessions_user_id",
        "user_refresh_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_refresh_sessions_user_active",
        "user_refresh_sessions",
        ["user_id", "revoked_at", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_refresh_sessions_user_active", table_name="user_refresh_sessions")
    op.drop_index("ix_user_refresh_sessions_user_id", table_name="user_refresh_sessions")
    op.drop_index("ix_user_refresh_sessions_refresh_token_hash", table_name="user_refresh_sessions")
    op.drop_table("user_refresh_sessions")

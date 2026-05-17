"""add child allowance settings

Revision ID: bf3d4a8c2e91
Revises: 5fd2ed5269af
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "bf3d4a8c2e91"
down_revision: Union[str, Sequence[str], None] = "5fd2ed5269af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "child_allowance_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("child_id", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="OMR", nullable=False),
        sa.Column("allowance_amount_minor", sa.Integer(), server_default="0", nullable=False),
        sa.Column("currency_exponent", sa.Integer(), server_default="3", nullable=False),
        sa.Column("period", sa.String(length=16), server_default="weekly", nullable=False),
        sa.Column("point_goal", sa.Integer(), nullable=False),
        sa.Column("created_by_parent_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_parent_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("period IN ('weekly', 'monthly')", name="ck_child_allowance_period"),
        sa.CheckConstraint("point_goal > 0", name="ck_child_allowance_point_goal_positive"),
        sa.CheckConstraint("allowance_amount_minor >= 0", name="ck_child_allowance_amount_nonnegative"),
        sa.CheckConstraint("length(currency) = 3 AND currency = upper(currency)", name="ck_child_allowance_currency_code"),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"]),
        sa.ForeignKeyConstraint(["created_by_parent_id"], ["parent_users.id"]),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"]),
        sa.ForeignKeyConstraint(["updated_by_parent_id"], ["parent_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("child_id", name="uq_child_allowance_settings_child_id"),
    )
    op.create_index(op.f("ix_child_allowance_settings_id"), "child_allowance_settings", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_child_allowance_settings_id"), table_name="child_allowance_settings")
    op.drop_table("child_allowance_settings")

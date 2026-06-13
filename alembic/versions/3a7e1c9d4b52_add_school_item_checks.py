"""add school item checks (B2 pack-for-tomorrow checklist)

Revision ID: 3a7e1c9d4b52
Revises: 2f3c4d5e6a7b
Create Date: 2026-06-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3a7e1c9d4b52"
down_revision: Union[str, None] = "2f3c4d5e6a7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "school_item_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_item_id", sa.Integer(), nullable=False),
        sa.Column("child_id", sa.Integer(), nullable=False),
        sa.Column("check_date", sa.Date(), nullable=False),
        sa.Column("packed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["school_item_id"], ["school_items.id"]),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_item_id", "check_date", name="_school_item_check_uc"),
    )
    op.create_index(op.f("ix_school_item_checks_id"), "school_item_checks", ["id"], unique=False)
    op.create_index(
        "ix_school_item_checks_child_date",
        "school_item_checks",
        ["child_id", "check_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_school_item_checks_child_date", table_name="school_item_checks")
    op.drop_index(op.f("ix_school_item_checks_id"), table_name="school_item_checks")
    op.drop_table("school_item_checks")

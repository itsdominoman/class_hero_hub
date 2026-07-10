"""Add announcement_reads

Revision ID: b0151a8e2f3d
Revises: a4b5c6d7e8f9
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b0151a8e2f3d"
down_revision: Union[str, Sequence[str], None] = "a4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "announcement_reads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("announcement_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.UniqueConstraint("announcement_id", "user_id", name="uq_announcement_reads_announcement_user"),
        sa.ForeignKeyConstraint(["announcement_id"], ["announcements.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_announcement_reads_id"), "announcement_reads", ["id"])
    op.create_index(op.f("ix_announcement_reads_announcement_id"), "announcement_reads", ["announcement_id"])
    op.create_index(op.f("ix_announcement_reads_user_id"), "announcement_reads", ["user_id"])
    op.create_index(op.f("ix_announcement_reads_school_id"), "announcement_reads", ["school_id"])
    op.create_index("ix_announcement_reads_user_announcement", "announcement_reads", ["user_id", "announcement_id"])


def downgrade() -> None:
    op.drop_index("ix_announcement_reads_user_announcement", table_name="announcement_reads")
    op.drop_index(op.f("ix_announcement_reads_school_id"), table_name="announcement_reads")
    op.drop_index(op.f("ix_announcement_reads_user_id"), table_name="announcement_reads")
    op.drop_index(op.f("ix_announcement_reads_announcement_id"), table_name="announcement_reads")
    op.drop_index(op.f("ix_announcement_reads_id"), table_name="announcement_reads")
    op.drop_table("announcement_reads")

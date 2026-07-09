"""Add student imports

Revision ID: a1b2c3d4e5f6
Revises: f2a3b4c5d6e7
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("kind", sa.String(), server_default="students", nullable=False),
        sa.Column("filename", sa.String(), nullable=True),
        sa.Column("status", sa.String(), server_default="staged", nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_imports_school_id", "imports", ["school_id"])
    op.create_index("ix_imports_school_status", "imports", ["school_id", "status"])
    op.create_check_constraint(
        "ck_imports_status",
        "imports",
        "status IN ('staged', 'committed', 'discarded')",
    )

    op.create_table(
        "import_rows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_id", sa.Integer(), sa.ForeignKey("imports.id"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("applied_entity_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_import_rows_import_id", "import_rows", ["import_id"])
    op.create_check_constraint(
        "ck_import_rows_action",
        "import_rows",
        "action IN ('create', 'update', 'move', 'restore', 'skip', 'error')",
    )


def downgrade() -> None:
    op.drop_table("import_rows")
    op.drop_table("imports")

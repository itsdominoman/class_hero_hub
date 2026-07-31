"""add annual MIS student import context

Revision ID: d6e7f8a9b0c2
Revises: c5d6e7f8a9b0
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "d6e7f8a9b0c2"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "imports",
        sa.Column("mode", sa.String(), server_default="normal", nullable=False),
    )
    op.add_column(
        "imports",
        sa.Column("academic_year_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "imports",
        sa.Column("effective_date", sa.Date(), nullable=True),
    )
    op.create_foreign_key(
        "fk_imports_academic_year_id",
        "imports",
        "academic_years",
        ["academic_year_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_imports_mode",
        "imports",
        "mode IN ('normal', 'annual')",
    )
    op.create_check_constraint(
        "ck_imports_annual_context",
        "imports",
        "mode = 'normal' OR (academic_year_id IS NOT NULL AND effective_date IS NOT NULL)",
    )

    op.drop_constraint("ck_import_rows_action", "import_rows", type_="check")
    op.create_check_constraint(
        "ck_import_rows_action",
        "import_rows",
        "action IN ('create', 'update', 'move', 'restore', 'reactivate', "
        "'leaver', 'inactive', 'skip', 'conflict', 'error')",
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM imports WHERE mode = 'annual')
               OR EXISTS (
                    SELECT 1
                    FROM import_rows
                    WHERE action IN ('reactivate', 'leaver', 'inactive')
               )
            THEN
                RAISE EXCEPTION 'Cannot downgrade while annual MIS import history exists';
            END IF;
        END
        $$;
        """
    )
    op.drop_constraint("ck_import_rows_action", "import_rows", type_="check")
    op.create_check_constraint(
        "ck_import_rows_action",
        "import_rows",
        "action IN ('create', 'update', 'move', 'restore', 'skip', 'conflict', 'error')",
    )

    op.drop_constraint("ck_imports_annual_context", "imports", type_="check")
    op.drop_constraint("ck_imports_mode", "imports", type_="check")
    op.drop_constraint("fk_imports_academic_year_id", "imports", type_="foreignkey")
    op.drop_column("imports", "effective_date")
    op.drop_column("imports", "academic_year_id")
    op.drop_column("imports", "mode")

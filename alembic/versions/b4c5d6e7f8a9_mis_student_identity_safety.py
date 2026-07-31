"""make MIS student identity and import conflicts deterministic

Revision ID: b4c5d6e7f8a9
Revises: a4e5f6b7c8d9
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "b4c5d6e7f8a9"
down_revision = "a4e5f6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM students
                WHERE external_ref IS NOT NULL AND length(btrim(external_ref)) > 0
                GROUP BY school_id, lower(btrim(external_ref))
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'Normalised duplicate student external references must be resolved before migration';
            END IF;
        END
        $$;
        """
    )
    op.create_index(
        "uq_students_school_external_ref_normalized",
        "students",
        ["school_id", sa.text("lower(btrim(external_ref))")],
        unique=True,
        postgresql_where=sa.text("external_ref IS NOT NULL AND length(btrim(external_ref)) > 0"),
    )
    op.drop_constraint("ck_import_rows_action", "import_rows", type_="check")
    op.create_check_constraint(
        "ck_import_rows_action",
        "import_rows",
        "action IN ('create', 'update', 'move', 'restore', 'skip', 'conflict', 'error')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_import_rows_action", "import_rows", type_="check")
    op.create_check_constraint(
        "ck_import_rows_action",
        "import_rows",
        "action IN ('create', 'update', 'move', 'restore', 'skip', 'error')",
    )
    op.drop_index("uq_students_school_external_ref_normalized", table_name="students")

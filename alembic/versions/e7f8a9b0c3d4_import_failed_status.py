"""allow failed import history status

Revision ID: e7f8a9b0c3d4
Revises: d6e7f8a9b0c2
Create Date: 2026-07-31
"""

from alembic import op


revision = "e7f8a9b0c3d4"
down_revision = "d6e7f8a9b0c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_imports_status", "imports", type_="check")
    op.create_check_constraint(
        "ck_imports_status",
        "imports",
        "status IN ('staged', 'committed', 'discarded', 'failed')",
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM imports WHERE status = 'failed')
            THEN
                RAISE EXCEPTION 'Cannot downgrade while failed import history exists';
            END IF;
        END
        $$;
        """
    )
    op.drop_constraint("ck_imports_status", "imports", type_="check")
    op.create_check_constraint(
        "ck_imports_status",
        "imports",
        "status IN ('staged', 'committed', 'discarded')",
    )

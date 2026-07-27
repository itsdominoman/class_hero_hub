"""bind FHH links to their integration environment

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "f8a9b0c1d2e3"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fhh_links",
        sa.Column(
            "integration_environment",
            sa.String(length=16),
            nullable=False,
            server_default="development",
        ),
    )
    op.create_check_constraint(
        "ck_fhh_links_integration_environment",
        "fhh_links",
        "integration_environment IN ('development', 'production')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_fhh_links_integration_environment",
        "fhh_links",
        type_="check",
    )
    op.drop_column("fhh_links", "integration_environment")

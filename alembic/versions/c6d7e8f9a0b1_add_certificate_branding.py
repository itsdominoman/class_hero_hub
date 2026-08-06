"""Add shared school certificate branding.

Revision ID: c6d7e8f9a0b1
Revises: f0e1d2c3b4a5
"""

from alembic import op
import sqlalchemy as sa


revision = "c6d7e8f9a0b1"
down_revision = "f0e1d2c3b4a5"
branch_labels = None
depends_on = None


ACCENTS = "'gold', 'violet', 'emerald', 'navy', 'burgundy'"


def upgrade() -> None:
    op.add_column("schools", sa.Column("certificate_logo_url", sa.String(length=1000), nullable=True))
    op.add_column(
        "schools",
        sa.Column("certificate_accent_color", sa.String(length=24), server_default="gold", nullable=False),
    )
    op.create_check_constraint(
        "ck_schools_certificate_accent_color",
        "schools",
        f"certificate_accent_color IN ({ACCENTS})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_schools_certificate_accent_color", "schools", type_="check")
    op.drop_column("schools", "certificate_accent_color")
    op.drop_column("schools", "certificate_logo_url")

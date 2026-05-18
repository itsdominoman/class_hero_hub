"""add allowance enabled at

Revision ID: 9b0b6e5ad4d2
Revises: bf3d4a8c2e91
Create Date: 2026-05-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b0b6e5ad4d2"
down_revision: Union[str, Sequence[str], None] = "bf3d4a8c2e91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "child_allowance_settings",
        sa.Column("allowance_enabled_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE child_allowance_settings
            SET allowance_enabled_at = COALESCE(updated_at, created_at, NOW())
            WHERE is_enabled = TRUE AND allowance_enabled_at IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("child_allowance_settings", "allowance_enabled_at")

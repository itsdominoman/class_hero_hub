"""Add stable student avatar assignments

Revision ID: c4d5e6f7a8b9
Revises: b0151a8e2f3d
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b0151a8e2f3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("students", sa.Column("avatar_id", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_students_avatar_id_valid",
        "students",
        "avatar_id IS NULL OR (avatar_id BETWEEN 31 AND 90 AND avatar_id <> 74)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_students_avatar_id_valid", "students", type_="check")
    op.drop_column("students", "avatar_id")

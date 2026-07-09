"""Add subject-group enrolment policies

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subject_groups", sa.Column("enrolment_policy", sa.String(), server_default="explicit_only", nullable=False))
    op.add_column("enrolments", sa.Column("kind", sa.String(), server_default="member", nullable=False))
    op.execute("UPDATE subject_groups SET enrolment_policy = 'explicit_only' WHERE enrolment_policy IS NULL")
    op.execute("UPDATE enrolments SET kind = 'member' WHERE kind IS NULL")
    op.create_check_constraint(
        "ck_subject_groups_enrolment_policy",
        "subject_groups",
        "enrolment_policy IN ('explicit_only', 'default_for_section', 'default_for_grade')",
    )
    op.create_check_constraint("ck_enrolments_kind", "enrolments", "kind IN ('member', 'excluded')")


def downgrade() -> None:
    op.drop_constraint("ck_enrolments_kind", "enrolments", type_="check")
    op.drop_constraint("ck_subject_groups_enrolment_policy", "subject_groups", type_="check")
    op.drop_column("enrolments", "kind")
    op.drop_column("subject_groups", "enrolment_policy")

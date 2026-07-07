"""Add staff assignments

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "staff_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("membership_id", sa.Integer(), nullable=False),
        sa.Column("class_section_id", sa.Integer(), nullable=True),
        sa.Column("subject_group_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.CheckConstraint(
            "(class_section_id IS NOT NULL AND subject_group_id IS NULL) OR "
            "(class_section_id IS NULL AND subject_group_id IS NOT NULL)",
            name="ck_staff_assignments_exactly_one_target",
        ),
        sa.ForeignKeyConstraint(["class_section_id"], ["class_sections.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["subject_group_id"], ["subject_groups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_staff_assignments_id"), "staff_assignments", ["id"], unique=False)
    op.create_index(op.f("ix_staff_assignments_school_id"), "staff_assignments", ["school_id"], unique=False)
    op.create_index(op.f("ix_staff_assignments_membership_id"), "staff_assignments", ["membership_id"], unique=False)
    op.create_index(op.f("ix_staff_assignments_class_section_id"), "staff_assignments", ["class_section_id"], unique=False)
    op.create_index(op.f("ix_staff_assignments_subject_group_id"), "staff_assignments", ["subject_group_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_staff_assignments_subject_group_id"), table_name="staff_assignments")
    op.drop_index(op.f("ix_staff_assignments_class_section_id"), table_name="staff_assignments")
    op.drop_index(op.f("ix_staff_assignments_membership_id"), table_name="staff_assignments")
    op.drop_index(op.f("ix_staff_assignments_school_id"), table_name="staff_assignments")
    op.drop_index(op.f("ix_staff_assignments_id"), table_name="staff_assignments")
    op.drop_table("staff_assignments")

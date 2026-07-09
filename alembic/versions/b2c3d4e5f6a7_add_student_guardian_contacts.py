"""Add student guardian contacts

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_guardian_contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("relationship", sa.String(), nullable=True),
        sa.Column("source_import_id", sa.Integer(), sa.ForeignKey("imports.id"), nullable=True),
        sa.Column("status", sa.String(), server_default="draft", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_student_guardian_contacts_school_id", "student_guardian_contacts", ["school_id"])
    op.create_index("ix_student_guardian_contacts_student_id", "student_guardian_contacts", ["student_id"])
    op.create_index("ix_student_guardian_contacts_school_student", "student_guardian_contacts", ["school_id", "student_id"])
    op.create_unique_constraint(
        "uq_student_guardian_contacts_school_student_slot",
        "student_guardian_contacts",
        ["school_id", "student_id", "slot"],
    )
    op.create_check_constraint(
        "ck_student_guardian_contacts_slot",
        "student_guardian_contacts",
        "slot IN (1, 2)",
    )
    op.create_check_constraint(
        "ck_student_guardian_contacts_relationship",
        "student_guardian_contacts",
        "relationship IS NULL OR relationship IN ('mother', 'father', 'guardian', 'other')",
    )
    op.create_check_constraint(
        "ck_student_guardian_contacts_status",
        "student_guardian_contacts",
        "status IN ('draft', 'linked', 'ignored')",
    )


def downgrade() -> None:
    op.drop_table("student_guardian_contacts")

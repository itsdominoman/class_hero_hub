"""Add students and enrolments

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("external_ref", sa.String(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("preferred_name", sa.String(), nullable=True),
        sa.Column("name_ar", sa.String(), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_students_id"), "students", ["id"], unique=False)
    op.create_index(op.f("ix_students_school_id"), "students", ["school_id"], unique=False)
    op.create_index(op.f("ix_students_external_ref"), "students", ["external_ref"], unique=False)

    op.create_table(
        "enrolments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("class_section_id", sa.Integer(), nullable=True),
        sa.Column("subject_group_id", sa.Integer(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.CheckConstraint(
            "(class_section_id IS NOT NULL AND subject_group_id IS NULL) OR "
            "(class_section_id IS NULL AND subject_group_id IS NOT NULL)",
            name="ck_enrolments_exactly_one_target",
        ),
        sa.ForeignKeyConstraint(["class_section_id"], ["class_sections.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["subject_group_id"], ["subject_groups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_enrolments_id"), "enrolments", ["id"], unique=False)
    op.create_index(op.f("ix_enrolments_school_id"), "enrolments", ["school_id"], unique=False)
    op.create_index(op.f("ix_enrolments_student_id"), "enrolments", ["student_id"], unique=False)
    op.create_index(op.f("ix_enrolments_class_section_id"), "enrolments", ["class_section_id"], unique=False)
    op.create_index(op.f("ix_enrolments_subject_group_id"), "enrolments", ["subject_group_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_enrolments_subject_group_id"), table_name="enrolments")
    op.drop_index(op.f("ix_enrolments_class_section_id"), table_name="enrolments")
    op.drop_index(op.f("ix_enrolments_student_id"), table_name="enrolments")
    op.drop_index(op.f("ix_enrolments_school_id"), table_name="enrolments")
    op.drop_index(op.f("ix_enrolments_id"), table_name="enrolments")
    op.drop_table("enrolments")
    op.drop_index(op.f("ix_students_external_ref"), table_name="students")
    op.drop_index(op.f("ix_students_school_id"), table_name="students")
    op.drop_index(op.f("ix_students_id"), table_name="students")
    op.drop_table("students")

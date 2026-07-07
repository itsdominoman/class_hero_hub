"""add school structure

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("schools", sa.Column("grade_level_label", sa.String(), nullable=True))
    op.execute("UPDATE schools SET grade_level_label = 'Grade' WHERE grade_level_label IS NULL")

    op.create_table(
        "branch_campuses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_ar", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "code", name="uq_branch_campuses_school_code"),
    )
    op.create_index(op.f("ix_branch_campuses_id"), "branch_campuses", ["id"], unique=False)
    op.create_index(op.f("ix_branch_campuses_school_id"), "branch_campuses", ["school_id"], unique=False)

    op.add_column("memberships", sa.Column("branch_campus_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_memberships_branch_campus_id_branch_campuses",
        "memberships",
        "branch_campuses",
        ["branch_campus_id"],
        ["id"],
    )

    op.create_table(
        "education_stages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_ar", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "code", name="uq_education_stages_school_code"),
    )
    op.create_index(op.f("ix_education_stages_id"), "education_stages", ["id"], unique=False)
    op.create_index(op.f("ix_education_stages_school_id"), "education_stages", ["school_id"], unique=False)

    op.create_table(
        "academic_years",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_ar", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "code", name="uq_academic_years_school_code"),
        sa.UniqueConstraint("school_id", "name", name="uq_academic_years_school_name"),
    )
    op.create_index(op.f("ix_academic_years_id"), "academic_years", ["id"], unique=False)
    op.create_index(op.f("ix_academic_years_school_id"), "academic_years", ["school_id"], unique=False)

    op.create_table(
        "grade_levels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("education_stage_id", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_ar", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["education_stage_id"], ["education_stages.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "code", name="uq_grade_levels_school_code"),
    )
    op.create_index(op.f("ix_grade_levels_id"), "grade_levels", ["id"], unique=False)
    op.create_index(op.f("ix_grade_levels_school_id"), "grade_levels", ["school_id"], unique=False)

    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_ar", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "code", name="uq_subjects_school_code"),
    )
    op.create_index(op.f("ix_subjects_id"), "subjects", ["id"], unique=False)
    op.create_index(op.f("ix_subjects_school_id"), "subjects", ["school_id"], unique=False)

    op.create_table(
        "class_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("branch_campus_id", sa.Integer(), nullable=False),
        sa.Column("academic_year_id", sa.Integer(), nullable=False),
        sa.Column("grade_level_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_ar", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("homeroom_teacher_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["academic_year_id"], ["academic_years.id"]),
        sa.ForeignKeyConstraint(["branch_campus_id"], ["branch_campuses.id"]),
        sa.ForeignKeyConstraint(["grade_level_id"], ["grade_levels.id"]),
        sa.ForeignKeyConstraint(["homeroom_teacher_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "school_id",
            "branch_campus_id",
            "academic_year_id",
            "grade_level_id",
            "code",
            name="uq_class_sections_school_branch_year_level_code",
        ),
    )
    op.create_index(op.f("ix_class_sections_id"), "class_sections", ["id"], unique=False)
    op.create_index(op.f("ix_class_sections_school_id"), "class_sections", ["school_id"], unique=False)

    op.create_table(
        "subject_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("academic_year_id", sa.Integer(), nullable=False),
        sa.Column("class_section_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_ar", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["academic_year_id"], ["academic_years.id"]),
        sa.ForeignKeyConstraint(["class_section_id"], ["class_sections.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "school_id",
            "academic_year_id",
            "class_section_id",
            "subject_id",
            "code",
            name="uq_subject_groups_school_year_section_subject_code",
        ),
    )
    op.create_index(op.f("ix_subject_groups_id"), "subject_groups", ["id"], unique=False)
    op.create_index(op.f("ix_subject_groups_school_id"), "subject_groups", ["school_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_subject_groups_school_id"), table_name="subject_groups")
    op.drop_index(op.f("ix_subject_groups_id"), table_name="subject_groups")
    op.drop_table("subject_groups")
    op.drop_index(op.f("ix_class_sections_school_id"), table_name="class_sections")
    op.drop_index(op.f("ix_class_sections_id"), table_name="class_sections")
    op.drop_table("class_sections")
    op.drop_index(op.f("ix_subjects_school_id"), table_name="subjects")
    op.drop_index(op.f("ix_subjects_id"), table_name="subjects")
    op.drop_table("subjects")
    op.drop_index(op.f("ix_grade_levels_school_id"), table_name="grade_levels")
    op.drop_index(op.f("ix_grade_levels_id"), table_name="grade_levels")
    op.drop_table("grade_levels")
    op.drop_index(op.f("ix_academic_years_school_id"), table_name="academic_years")
    op.drop_index(op.f("ix_academic_years_id"), table_name="academic_years")
    op.drop_table("academic_years")
    op.drop_index(op.f("ix_education_stages_school_id"), table_name="education_stages")
    op.drop_index(op.f("ix_education_stages_id"), table_name="education_stages")
    op.drop_table("education_stages")
    op.drop_constraint("fk_memberships_branch_campus_id_branch_campuses", "memberships", type_="foreignkey")
    op.drop_column("memberships", "branch_campus_id")
    op.drop_index(op.f("ix_branch_campuses_school_id"), table_name="branch_campuses")
    op.drop_index(op.f("ix_branch_campuses_id"), table_name="branch_campuses")
    op.drop_table("branch_campuses")
    op.drop_column("schools", "grade_level_label")

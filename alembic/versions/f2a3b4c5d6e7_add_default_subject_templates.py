"""Add default subject templates

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "default_subject_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("education_stage_id", sa.Integer(), sa.ForeignKey("education_stages.id"), nullable=True),
        sa.Column("grade_level_id", sa.Integer(), sa.ForeignKey("grade_levels.id"), nullable=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_default_subject_templates_school_id", "default_subject_templates", ["school_id"])
    op.create_index("ix_default_subject_templates_school_status", "default_subject_templates", ["school_id", "status"])
    op.create_unique_constraint(
        "uq_default_subject_templates_school_stage_grade_subject",
        "default_subject_templates",
        ["school_id", "education_stage_id", "grade_level_id", "subject_id"],
    )
    op.create_check_constraint(
        "ck_default_subject_templates_exactly_one_scope",
        "default_subject_templates",
        "(education_stage_id IS NOT NULL AND grade_level_id IS NULL) OR "
        "(education_stage_id IS NULL AND grade_level_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_table("default_subject_templates")

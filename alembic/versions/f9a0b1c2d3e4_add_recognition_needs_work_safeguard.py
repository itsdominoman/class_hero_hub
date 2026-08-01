"""add recognition needs-work eligibility safeguard

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-08-01
"""

from alembic import op
import sqlalchemy as sa


revision = "f9a0b1c2d3e4"
down_revision = "e8f9a0b1c2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "student_recognition_configs",
        sa.Column("needs_work_safeguard_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "student_recognition_configs",
        sa.Column("maximum_needs_work_events", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "ck_student_recognition_configs_max_needs_work",
        "student_recognition_configs",
        "maximum_needs_work_events >= 0",
    )
    op.create_table(
        "student_recognition_safeguard_categories",
        sa.Column(
            "config_id",
            sa.Integer(),
            sa.ForeignKey("student_recognition_configs.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("behaviour_categories.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )
    op.add_column(
        "student_recognition_candidates",
        sa.Column("safeguard_excluded", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "student_recognition_candidates",
        sa.Column("safeguard_counted_total", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "student_recognition_candidates",
        sa.Column("safeguard_category_totals", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column("student_recognition_candidates", sa.Column("safeguard_override_reason", sa.String(500), nullable=True))
    op.add_column(
        "student_recognition_candidates",
        sa.Column("safeguard_overridden_by_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_recognition_candidate_safeguard_override_user",
        "student_recognition_candidates",
        "users",
        ["safeguard_overridden_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column(
        "student_recognition_candidates",
        sa.Column("safeguard_overridden_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_student_recognition_candidates_safeguard_total",
        "student_recognition_candidates",
        "safeguard_counted_total >= 0",
    )
    op.create_check_constraint(
        "ck_student_recognition_candidates_safeguard_override",
        "student_recognition_candidates",
        "(safeguard_override_reason IS NULL AND safeguard_overridden_by_user_id IS NULL AND safeguard_overridden_at IS NULL) OR "
        "(safeguard_excluded AND safeguard_override_reason IS NOT NULL AND length(trim(safeguard_override_reason)) > 0 "
        "AND safeguard_overridden_by_user_id IS NOT NULL AND safeguard_overridden_at IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_student_recognition_candidates_safeguard_override",
        "student_recognition_candidates",
        type_="check",
    )
    op.drop_constraint(
        "ck_student_recognition_candidates_safeguard_total",
        "student_recognition_candidates",
        type_="check",
    )
    op.drop_column("student_recognition_candidates", "safeguard_overridden_at")
    op.drop_constraint(
        "fk_recognition_candidate_safeguard_override_user",
        "student_recognition_candidates",
        type_="foreignkey",
    )
    op.drop_column("student_recognition_candidates", "safeguard_overridden_by_user_id")
    op.drop_column("student_recognition_candidates", "safeguard_override_reason")
    op.drop_column("student_recognition_candidates", "safeguard_category_totals")
    op.drop_column("student_recognition_candidates", "safeguard_counted_total")
    op.drop_column("student_recognition_candidates", "safeguard_excluded")
    op.drop_table("student_recognition_safeguard_categories")
    op.drop_constraint(
        "ck_student_recognition_configs_max_needs_work",
        "student_recognition_configs",
        type_="check",
    )
    op.drop_column("student_recognition_configs", "maximum_needs_work_events")
    op.drop_column("student_recognition_configs", "needs_work_safeguard_enabled")

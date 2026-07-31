"""add positive student recognition workflow

Revision ID: e8f9a0b1c2d3
Revises: e7f8a9b0c3d4
Create Date: 2026-07-31
"""

from alembic import op
import sqlalchemy as sa


revision = "e8f9a0b1c2d3"
down_revision = "e7f8a9b0c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_recognition_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("recognition_type", sa.String(40), nullable=False, server_default="star_of_week"),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("scope_ref_id", sa.Integer(), nullable=False),
        sa.Column("scope_key", sa.String(64), nullable=False),
        sa.Column("review_period_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("minimum_positive_points", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("shortlist_size", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("certificate_title", sa.String(200), nullable=False),
        sa.Column("signatory_text", sa.String(200), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("recognition_type IN ('star_of_week')", name="ck_student_recognition_configs_type"),
        sa.CheckConstraint("scope_type IN ('branch', 'grade', 'class')", name="ck_student_recognition_configs_scope_type"),
        sa.CheckConstraint("review_period_days BETWEEN 1 AND 366", name="ck_student_recognition_configs_period_days"),
        sa.CheckConstraint("minimum_positive_points >= 1", name="ck_student_recognition_configs_min_points"),
        sa.CheckConstraint("shortlist_size BETWEEN 1 AND 50", name="ck_student_recognition_configs_shortlist_size"),
        sa.UniqueConstraint("school_id", "recognition_type", "scope_key", name="uq_student_recognition_configs_scope"),
    )
    op.create_index("ix_student_recognition_configs_school_id", "student_recognition_configs", ["school_id"])
    op.create_index("ix_student_recognition_configs_school_active", "student_recognition_configs", ["school_id", "active"])

    op.create_table(
        "student_recognition_categories",
        sa.Column("config_id", sa.Integer(), sa.ForeignKey("student_recognition_configs.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("behaviour_categories.id", ondelete="RESTRICT"), primary_key=True),
    )

    op.create_table(
        "student_recognition_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("config_id", sa.Integer(), sa.ForeignKey("student_recognition_configs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("recognition_type", sa.String(40), nullable=False),
        sa.Column("scope_key", sa.String(64), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("criteria_snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("selected_student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("citation", sa.String(500), nullable=True),
        sa.Column("generated_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("confirmed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.String(500), nullable=True),
        sa.CheckConstraint("status IN ('draft', 'confirmed', 'revoked')", name="ck_student_recognition_reviews_status"),
        sa.CheckConstraint("period_start <= period_end", name="ck_student_recognition_reviews_period"),
        sa.CheckConstraint(
            "(status = 'draft' AND selected_student_id IS NULL AND confirmed_by_user_id IS NULL AND confirmed_at IS NULL AND revoked_by_user_id IS NULL AND revoked_at IS NULL AND revocation_reason IS NULL) OR "
            "(status = 'confirmed' AND selected_student_id IS NOT NULL AND confirmed_by_user_id IS NOT NULL AND confirmed_at IS NOT NULL AND revoked_by_user_id IS NULL AND revoked_at IS NULL AND revocation_reason IS NULL) OR "
            "(status = 'revoked' AND selected_student_id IS NOT NULL AND confirmed_by_user_id IS NOT NULL AND confirmed_at IS NOT NULL AND revoked_by_user_id IS NOT NULL AND revoked_at IS NOT NULL AND revocation_reason IS NOT NULL AND length(trim(revocation_reason)) > 0)",
            name="ck_student_recognition_reviews_lifecycle",
        ),
    )
    op.create_index("ix_student_recognition_reviews_school_id", "student_recognition_reviews", ["school_id"])
    op.create_index("ix_student_recognition_reviews_config_id", "student_recognition_reviews", ["config_id"])
    op.create_index("ix_student_recognition_reviews_school_generated", "student_recognition_reviews", ["school_id", "generated_at"])
    op.create_index(
        "uq_student_recognition_reviews_confirmed_period",
        "student_recognition_reviews",
        ["school_id", "recognition_type", "scope_key", "period_start", "period_end"],
        unique=True,
        postgresql_where=sa.text("status = 'confirmed'"),
    )

    op.create_table(
        "student_recognition_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("student_recognition_reviews.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("student_name", sa.String(240), nullable=False),
        sa.Column("student_name_ar", sa.String(240), nullable=True),
        sa.Column("branch_name", sa.String(160), nullable=False),
        sa.Column("grade_name", sa.String(160), nullable=False),
        sa.Column("class_name", sa.String(160), nullable=False),
        sa.Column("positive_points_total", sa.Integer(), nullable=False),
        sa.Column("positive_event_count", sa.Integer(), nullable=False),
        sa.Column("category_totals", sa.JSON(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_excluded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("exclusion_reason", sa.String(500), nullable=True),
        sa.Column("excluded_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("excluded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("positive_points_total > 0", name="ck_student_recognition_candidates_points"),
        sa.CheckConstraint("positive_event_count > 0", name="ck_student_recognition_candidates_events"),
        sa.CheckConstraint("rank >= 1 AND display_order >= 1", name="ck_student_recognition_candidates_order"),
        sa.CheckConstraint(
            "(NOT is_excluded AND exclusion_reason IS NULL AND excluded_by_user_id IS NULL AND excluded_at IS NULL) OR "
            "(is_excluded AND exclusion_reason IS NOT NULL AND length(trim(exclusion_reason)) > 0 AND excluded_by_user_id IS NOT NULL AND excluded_at IS NOT NULL)",
            name="ck_student_recognition_candidates_exclusion",
        ),
        sa.UniqueConstraint("review_id", "student_id", name="uq_student_recognition_candidates_student"),
    )
    op.create_index("ix_student_recognition_candidates_school_id", "student_recognition_candidates", ["school_id"])
    op.create_index("ix_student_recognition_candidates_review_id", "student_recognition_candidates", ["review_id"])
    op.create_index("ix_student_recognition_candidates_student_id", "student_recognition_candidates", ["student_id"])
    op.create_index("ix_student_recognition_candidates_review_order", "student_recognition_candidates", ["review_id", "display_order"])


def downgrade() -> None:
    op.drop_table("student_recognition_candidates")
    op.drop_table("student_recognition_reviews")
    op.drop_table("student_recognition_categories")
    op.drop_table("student_recognition_configs")

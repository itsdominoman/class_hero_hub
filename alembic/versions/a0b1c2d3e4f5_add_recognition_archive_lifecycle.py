"""add recognition review and configuration archive lifecycle

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-08-01
"""

from alembic import op
import sqlalchemy as sa


revision = "a0b1c2d3e4f5"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("student_recognition_configs", sa.Column("archived_by_user_id", sa.Integer(), nullable=True))
    op.add_column("student_recognition_configs", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("student_recognition_configs", sa.Column("archive_reason", sa.String(500), nullable=True))
    op.create_foreign_key(
        "fk_recognition_config_archive_user",
        "student_recognition_configs",
        "users",
        ["archived_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_student_recognition_configs_archive",
        "student_recognition_configs",
        "(archived_at IS NULL AND archived_by_user_id IS NULL AND archive_reason IS NULL) OR "
        "(NOT active AND archived_at IS NOT NULL AND archived_by_user_id IS NOT NULL AND archive_reason IS NOT NULL "
        "AND length(trim(archive_reason)) > 0)",
    )
    op.drop_constraint("uq_student_recognition_configs_scope", "student_recognition_configs", type_="unique")
    op.create_index(
        "uq_student_recognition_configs_current_scope",
        "student_recognition_configs",
        ["school_id", "recognition_type", "scope_key"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )

    op.add_column("student_recognition_reviews", sa.Column("archived_by_user_id", sa.Integer(), nullable=True))
    op.add_column("student_recognition_reviews", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("student_recognition_reviews", sa.Column("archive_reason", sa.String(500), nullable=True))
    op.create_foreign_key(
        "fk_recognition_review_archive_user",
        "student_recognition_reviews",
        "users",
        ["archived_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("ck_student_recognition_reviews_lifecycle", "student_recognition_reviews", type_="check")
    op.drop_constraint("ck_student_recognition_reviews_status", "student_recognition_reviews", type_="check")
    op.create_check_constraint(
        "ck_student_recognition_reviews_status",
        "student_recognition_reviews",
        "status IN ('draft', 'confirmed', 'revoked', 'archived')",
    )
    op.create_check_constraint(
        "ck_student_recognition_reviews_lifecycle",
        "student_recognition_reviews",
        "(status = 'draft' AND selected_student_id IS NULL AND confirmed_by_user_id IS NULL AND confirmed_at IS NULL AND revoked_by_user_id IS NULL AND revoked_at IS NULL AND revocation_reason IS NULL AND archived_by_user_id IS NULL AND archived_at IS NULL AND archive_reason IS NULL) OR "
        "(status = 'confirmed' AND selected_student_id IS NOT NULL AND confirmed_by_user_id IS NOT NULL AND confirmed_at IS NOT NULL AND revoked_by_user_id IS NULL AND revoked_at IS NULL AND revocation_reason IS NULL AND archived_by_user_id IS NULL AND archived_at IS NULL AND archive_reason IS NULL) OR "
        "(status = 'revoked' AND selected_student_id IS NOT NULL AND confirmed_by_user_id IS NOT NULL AND confirmed_at IS NOT NULL AND revoked_by_user_id IS NOT NULL AND revoked_at IS NOT NULL AND revocation_reason IS NOT NULL AND length(trim(revocation_reason)) > 0 AND archived_by_user_id IS NULL AND archived_at IS NULL AND archive_reason IS NULL) OR "
        "(status = 'archived' AND selected_student_id IS NULL AND confirmed_by_user_id IS NULL AND confirmed_at IS NULL AND revoked_by_user_id IS NULL AND revoked_at IS NULL AND revocation_reason IS NULL AND archived_by_user_id IS NOT NULL AND archived_at IS NOT NULL AND archive_reason IS NOT NULL AND length(trim(archive_reason)) > 0)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_student_recognition_reviews_lifecycle", "student_recognition_reviews", type_="check")
    op.drop_constraint("ck_student_recognition_reviews_status", "student_recognition_reviews", type_="check")
    op.create_check_constraint(
        "ck_student_recognition_reviews_status",
        "student_recognition_reviews",
        "status IN ('draft', 'confirmed', 'revoked')",
    )
    op.create_check_constraint(
        "ck_student_recognition_reviews_lifecycle",
        "student_recognition_reviews",
        "(status = 'draft' AND selected_student_id IS NULL AND confirmed_by_user_id IS NULL AND confirmed_at IS NULL AND revoked_by_user_id IS NULL AND revoked_at IS NULL AND revocation_reason IS NULL) OR "
        "(status = 'confirmed' AND selected_student_id IS NOT NULL AND confirmed_by_user_id IS NOT NULL AND confirmed_at IS NOT NULL AND revoked_by_user_id IS NULL AND revoked_at IS NULL AND revocation_reason IS NULL) OR "
        "(status = 'revoked' AND selected_student_id IS NOT NULL AND confirmed_by_user_id IS NOT NULL AND confirmed_at IS NOT NULL AND revoked_by_user_id IS NOT NULL AND revoked_at IS NOT NULL AND revocation_reason IS NOT NULL AND length(trim(revocation_reason)) > 0)",
    )
    op.drop_constraint("fk_recognition_review_archive_user", "student_recognition_reviews", type_="foreignkey")
    op.drop_column("student_recognition_reviews", "archive_reason")
    op.drop_column("student_recognition_reviews", "archived_at")
    op.drop_column("student_recognition_reviews", "archived_by_user_id")

    op.drop_constraint("ck_student_recognition_configs_archive", "student_recognition_configs", type_="check")
    op.drop_index("uq_student_recognition_configs_current_scope", table_name="student_recognition_configs")
    op.create_unique_constraint(
        "uq_student_recognition_configs_scope",
        "student_recognition_configs",
        ["school_id", "recognition_type", "scope_key"],
    )
    op.drop_constraint("fk_recognition_config_archive_user", "student_recognition_configs", type_="foreignkey")
    op.drop_column("student_recognition_configs", "archive_reason")
    op.drop_column("student_recognition_configs", "archived_at")
    op.drop_column("student_recognition_configs", "archived_by_user_id")

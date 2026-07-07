"""S4.9 foundation cleanup

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("academic_years", sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("academic_years", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("academic_years", sa.Column("end_date", sa.Date(), nullable=True))
    op.create_index(
        "uq_academic_years_one_current_per_school",
        "academic_years",
        ["school_id"],
        unique=True,
        postgresql_where=sa.text("is_current IS TRUE AND status != 'archived'"),
        sqlite_where=sa.text("is_current = 1 AND status != 'archived'"),
    )

    op.add_column("staff_invites", sa.Column("send_status", sa.String(), nullable=True))
    op.add_column("staff_invites", sa.Column("last_send_error", sa.String(), nullable=True))
    op.execute("UPDATE staff_invites SET send_status = 'sent' WHERE send_status IS NULL")

    with op.batch_alter_table("class_sections") as batch_op:
        batch_op.drop_column("homeroom_teacher_user_id")

    with op.batch_alter_table("subject_groups") as batch_op:
        batch_op.add_column(sa.Column("grade_level_id", sa.Integer(), nullable=True))
        batch_op.alter_column("class_section_id", existing_type=sa.Integer(), nullable=True)
        batch_op.create_foreign_key("fk_subject_groups_grade_level_id_grade_levels", "grade_levels", ["grade_level_id"], ["id"])
        batch_op.drop_constraint("uq_subject_groups_school_year_section_subject_code", type_="unique")
        batch_op.create_unique_constraint(
            "uq_subject_groups_school_year_section_level_subject_code",
            ["school_id", "academic_year_id", "class_section_id", "grade_level_id", "subject_id", "code"],
        )
        batch_op.create_check_constraint(
            "ck_subject_groups_context_required",
            "class_section_id IS NOT NULL OR grade_level_id IS NOT NULL",
        )

    op.create_table(
        "magic_login_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("return_to", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_ip", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_magic_login_tokens_id"), "magic_login_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_magic_login_tokens_email"), "magic_login_tokens", ["email"], unique=False)
    op.create_index(op.f("ix_magic_login_tokens_token_hash"), "magic_login_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_magic_login_tokens_token_hash"), table_name="magic_login_tokens")
    op.drop_index(op.f("ix_magic_login_tokens_email"), table_name="magic_login_tokens")
    op.drop_index(op.f("ix_magic_login_tokens_id"), table_name="magic_login_tokens")
    op.drop_table("magic_login_tokens")

    with op.batch_alter_table("subject_groups") as batch_op:
        batch_op.drop_constraint("ck_subject_groups_context_required", type_="check")
        batch_op.drop_constraint("uq_subject_groups_school_year_section_level_subject_code", type_="unique")
        batch_op.create_unique_constraint(
            "uq_subject_groups_school_year_section_subject_code",
            ["school_id", "academic_year_id", "class_section_id", "subject_id", "code"],
        )
        batch_op.drop_constraint("fk_subject_groups_grade_level_id_grade_levels", type_="foreignkey")
        batch_op.alter_column("class_section_id", existing_type=sa.Integer(), nullable=False)
        batch_op.drop_column("grade_level_id")

    with op.batch_alter_table("class_sections") as batch_op:
        batch_op.add_column(sa.Column("homeroom_teacher_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_class_sections_homeroom_teacher_user_id_users", "users", ["homeroom_teacher_user_id"], ["id"])

    op.drop_column("staff_invites", "last_send_error")
    op.drop_column("staff_invites", "send_status")
    op.drop_index("uq_academic_years_one_current_per_school", table_name="academic_years")
    op.drop_column("academic_years", "end_date")
    op.drop_column("academic_years", "start_date")
    op.drop_column("academic_years", "is_current")

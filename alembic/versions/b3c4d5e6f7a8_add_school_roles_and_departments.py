"""Add explicit departments and interval-based staff department assignments.

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
"""

from alembic import op
import sqlalchemy as sa


revision = "b3c4d5e6f7a8"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_ar", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_departments_status"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "code", name="uq_departments_school_code"),
    )
    op.create_index("ix_departments_id", "departments", ["id"])
    op.create_index("ix_departments_school_id", "departments", ["school_id"])
    op.create_index("ix_departments_school_status", "departments", ["school_id", "status"])

    op.create_table(
        "staff_department_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("membership_id", sa.Integer(), nullable=False),
        sa.Column("responsibility", sa.String(), server_default="member", nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "responsibility IN ('head', 'member')",
            name="ck_staff_department_assignments_responsibility",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_staff_department_assignments_interval",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staff_department_assignments_id", "staff_department_assignments", ["id"])
    op.create_index("ix_staff_department_assignments_school_id", "staff_department_assignments", ["school_id"])
    op.create_index("ix_staff_department_assignments_department_id", "staff_department_assignments", ["department_id"])
    op.create_index("ix_staff_department_assignments_membership_id", "staff_department_assignments", ["membership_id"])
    op.create_index(
        "ix_staff_department_assignments_school_membership_interval",
        "staff_department_assignments",
        ["school_id", "membership_id", "valid_from", "valid_to"],
    )
    op.create_index(
        "ix_staff_department_assignments_department_interval",
        "staff_department_assignments",
        ["department_id", "valid_from", "valid_to"],
    )


def downgrade() -> None:
    op.drop_index("ix_staff_department_assignments_department_interval", table_name="staff_department_assignments")
    op.drop_index("ix_staff_department_assignments_school_membership_interval", table_name="staff_department_assignments")
    op.drop_index("ix_staff_department_assignments_membership_id", table_name="staff_department_assignments")
    op.drop_index("ix_staff_department_assignments_department_id", table_name="staff_department_assignments")
    op.drop_index("ix_staff_department_assignments_school_id", table_name="staff_department_assignments")
    op.drop_index("ix_staff_department_assignments_id", table_name="staff_department_assignments")
    op.drop_table("staff_department_assignments")
    op.drop_index("ix_departments_school_status", table_name="departments")
    op.drop_index("ix_departments_school_id", table_name="departments")
    op.drop_index("ix_departments_id", table_name="departments")
    op.drop_table("departments")

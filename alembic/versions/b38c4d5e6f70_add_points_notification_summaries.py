"""Add school-scoped points notification policy and durable summaries.

Revision ID: b38c4d5e6f70
Revises: a27b3c4d5e6f
Create Date: 2026-07-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "b38c4d5e6f70"
down_revision = "a27b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "school_points_notification_policies",
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="immediate"),
        sa.Column("daily_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("weekly_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("monthly_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("week_starts_on", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("week_ends_on", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("weekly_summary_day", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("daily_summary_time", sa.Time(), nullable=False, server_default="15:15"),
        sa.Column("weekly_summary_time", sa.Time(), nullable=False, server_default="15:30"),
        sa.Column("monthly_summary_time", sa.Time(), nullable=False, server_default="15:30"),
        sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by_membership_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("mode IN ('summaries', 'immediate', 'off')", name="ck_school_points_notification_policies_mode"),
        sa.CheckConstraint("week_starts_on BETWEEN 1 AND 7", name="ck_school_points_notification_policies_week_start"),
        sa.CheckConstraint("week_ends_on BETWEEN 1 AND 7", name="ck_school_points_notification_policies_week_end"),
        sa.CheckConstraint("weekly_summary_day BETWEEN 1 AND 7", name="ck_school_points_notification_policies_weekly_day"),
        sa.CheckConstraint("policy_version >= 1", name="ck_school_points_notification_policies_version"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_membership_id"], ["memberships.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("school_id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO school_points_notification_policies (school_id) "
            "SELECT id FROM schools ON CONFLICT (school_id) DO NOTHING"
        )
    )
    op.create_table(
        "point_notification_summaries",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("summary_type", sa.String(length=16), nullable=False),
        sa.Column("period_key", sa.String(length=40), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("eligible_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("positive_total", sa.Integer(), nullable=False),
        sa.Column("needs_work_total", sa.Integer(), nullable=False),
        sa.Column("net_total", sa.Integer(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("summary_type IN ('daily', 'weekly', 'monthly')", name="ck_point_notification_summaries_type"),
        sa.CheckConstraint("period_end > period_start", name="ck_point_notification_summaries_period"),
        sa.CheckConstraint("positive_total >= 0 AND needs_work_total >= 0", name="ck_point_notification_summaries_totals"),
        sa.CheckConstraint("net_total = positive_total - needs_work_total", name="ck_point_notification_summaries_net"),
        sa.CheckConstraint("event_count > 0", name="ck_point_notification_summaries_event_count"),
        sa.CheckConstraint("policy_version >= 1", name="ck_point_notification_summaries_version"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "student_id", "summary_type", "period_key", name="uq_point_notification_summaries_period"),
    )
    op.create_index("ix_point_notification_summaries_school_id", "point_notification_summaries", ["school_id"])
    op.create_index("ix_point_notification_summaries_student_id", "point_notification_summaries", ["student_id"])
    op.create_index("ix_point_notification_summaries_school_period", "point_notification_summaries", ["school_id", "summary_type", "period_key"])
    op.create_index("ix_point_notification_summaries_student_created", "point_notification_summaries", ["student_id", "created_at"])


def downgrade() -> None:
    op.drop_table("point_notification_summaries")
    op.drop_table("school_points_notification_policies")

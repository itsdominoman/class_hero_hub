"""add calendar events

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
"""

from alembic import op
import sqlalchemy as sa

revision = "b9c0d1e2f3a4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("audience_type", sa.String(), nullable=False),
        sa.Column("class_section_id", sa.Integer(), sa.ForeignKey("class_sections.id"), nullable=True),
        sa.Column("subject_group_id", sa.Integer(), sa.ForeignKey("subject_groups.id"), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("all_day", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("event_type IN ('event', 'test', 'reminder', 'trip', 'civvies', 'charity')", name="ck_calendar_events_type"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_calendar_events_status"),
        sa.CheckConstraint(
            "(audience_type = 'school' AND class_section_id IS NULL AND subject_group_id IS NULL) OR "
            "(audience_type = 'class_section' AND class_section_id IS NOT NULL AND subject_group_id IS NULL) OR "
            "(audience_type = 'subject_group' AND class_section_id IS NULL AND subject_group_id IS NOT NULL)",
            name="ck_calendar_events_audience_target",
        ),
    )
    op.create_index("ix_calendar_events_school_id", "calendar_events", ["school_id"])
    op.create_index("ix_calendar_events_author_user_id", "calendar_events", ["author_user_id"])
    op.create_index("ix_calendar_events_class_section_id", "calendar_events", ["class_section_id"])
    op.create_index("ix_calendar_events_subject_group_id", "calendar_events", ["subject_group_id"])
    op.create_index("ix_calendar_events_school_status_starts", "calendar_events", ["school_id", "status", "starts_at"])


def downgrade():
    op.drop_table("calendar_events")

"""Add announcements and attachments

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("audience_type", sa.String(), nullable=False),
        sa.Column("class_section_id", sa.Integer(), nullable=True),
        sa.Column("subject_group_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), server_default="published", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.CheckConstraint("audience_type IN ('school', 'class_section', 'subject_group')", name="ck_announcements_audience_type"),
        sa.CheckConstraint("status IN ('published', 'archived')", name="ck_announcements_status"),
        sa.CheckConstraint(
            "(audience_type = 'school' AND class_section_id IS NULL AND subject_group_id IS NULL) OR "
            "(audience_type = 'class_section' AND class_section_id IS NOT NULL AND subject_group_id IS NULL) OR "
            "(audience_type = 'subject_group' AND class_section_id IS NULL AND subject_group_id IS NOT NULL)",
            name="ck_announcements_audience_target",
        ),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["class_section_id"], ["class_sections.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["subject_group_id"], ["subject_groups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_announcements_author_user_id"), "announcements", ["author_user_id"])
    op.create_index(op.f("ix_announcements_class_section_id"), "announcements", ["class_section_id"])
    op.create_index(op.f("ix_announcements_id"), "announcements", ["id"])
    op.create_index(op.f("ix_announcements_school_id"), "announcements", ["school_id"])
    op.create_index("ix_announcements_school_status_created", "announcements", ["school_id", "status", "created_at"])
    op.create_index(op.f("ix_announcements_subject_group_id"), "announcements", ["subject_group_id"])

    op.create_table(
        "announcement_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["post_id"], ["announcements.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_announcement_attachments_id"), "announcement_attachments", ["id"])
    op.create_index(op.f("ix_announcement_attachments_post_id"), "announcement_attachments", ["post_id"])
    op.create_index("ix_announcement_attachments_post_school", "announcement_attachments", ["post_id", "school_id"])
    op.create_index(op.f("ix_announcement_attachments_school_id"), "announcement_attachments", ["school_id"])
    op.create_index(op.f("ix_announcement_attachments_storage_key"), "announcement_attachments", ["storage_key"], unique=True)
    op.create_index(op.f("ix_announcement_attachments_uploaded_by_user_id"), "announcement_attachments", ["uploaded_by_user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_announcement_attachments_uploaded_by_user_id"), table_name="announcement_attachments")
    op.drop_index(op.f("ix_announcement_attachments_storage_key"), table_name="announcement_attachments")
    op.drop_index(op.f("ix_announcement_attachments_school_id"), table_name="announcement_attachments")
    op.drop_index("ix_announcement_attachments_post_school", table_name="announcement_attachments")
    op.drop_index(op.f("ix_announcement_attachments_post_id"), table_name="announcement_attachments")
    op.drop_index(op.f("ix_announcement_attachments_id"), table_name="announcement_attachments")
    op.drop_table("announcement_attachments")
    op.drop_index(op.f("ix_announcements_subject_group_id"), table_name="announcements")
    op.drop_index("ix_announcements_school_status_created", table_name="announcements")
    op.drop_index(op.f("ix_announcements_school_id"), table_name="announcements")
    op.drop_index(op.f("ix_announcements_id"), table_name="announcements")
    op.drop_index(op.f("ix_announcements_class_section_id"), table_name="announcements")
    op.drop_index(op.f("ix_announcements_author_user_id"), table_name="announcements")
    op.drop_table("announcements")

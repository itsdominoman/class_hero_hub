"""add homework and diary items

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
"""

from alembic import op
import sqlalchemy as sa

revision = "e6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "homework_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("item_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("audience_type", sa.String(), nullable=False),
        sa.Column("class_section_id", sa.Integer(), sa.ForeignKey("class_sections.id"), nullable=True),
        sa.Column("subject_group_id", sa.Integer(), sa.ForeignKey("subject_groups.id"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("item_type IN ('homework', 'diary')", name="ck_homework_items_type"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_homework_items_status"),
        sa.CheckConstraint("(audience_type = 'class_section' AND class_section_id IS NOT NULL AND subject_group_id IS NULL) OR (audience_type = 'subject_group' AND class_section_id IS NULL AND subject_group_id IS NOT NULL)", name="ck_homework_items_exactly_one_audience"),
    )
    op.create_index("ix_homework_items_school_id", "homework_items", ["school_id"])
    op.create_index("ix_homework_items_author_user_id", "homework_items", ["author_user_id"])
    op.create_index("ix_homework_items_class_section_id", "homework_items", ["class_section_id"])
    op.create_index("ix_homework_items_subject_group_id", "homework_items", ["subject_group_id"])
    op.create_index("ix_homework_items_school_status_created", "homework_items", ["school_id", "status", "created_at"])
    op.create_table(
        "homework_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("homework_item_id", sa.Integer(), sa.ForeignKey("homework_items.id"), nullable=False),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False, unique=True),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_homework_attachments_homework_item_id", "homework_attachments", ["homework_item_id"])
    op.create_index("ix_homework_attachments_school_id", "homework_attachments", ["school_id"])
    op.create_index("ix_homework_attachments_uploaded_by_user_id", "homework_attachments", ["uploaded_by_user_id"])
    op.create_index("ix_homework_attachments_storage_key", "homework_attachments", ["storage_key"], unique=True)
    op.create_index("ix_homework_attachments_item_school", "homework_attachments", ["homework_item_id", "school_id"])


def downgrade():
    op.drop_table("homework_attachments")
    op.drop_table("homework_items")

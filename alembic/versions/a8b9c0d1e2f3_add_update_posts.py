"""add updates & photos posts

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
"""

from alembic import op
import sqlalchemy as sa

revision = "a8b9c0d1e2f3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "update_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("audience_type", sa.String(), nullable=False),
        sa.Column("class_section_id", sa.Integer(), sa.ForeignKey("class_sections.id"), nullable=True),
        sa.Column("subject_group_id", sa.Integer(), sa.ForeignKey("subject_groups.id"), nullable=True),
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_update_posts_status"),
        sa.CheckConstraint("(audience_type = 'class_section' AND class_section_id IS NOT NULL AND subject_group_id IS NULL) OR (audience_type = 'subject_group' AND class_section_id IS NULL AND subject_group_id IS NOT NULL)", name="ck_update_posts_exactly_one_audience"),
    )
    op.create_index("ix_update_posts_school_id", "update_posts", ["school_id"])
    op.create_index("ix_update_posts_author_user_id", "update_posts", ["author_user_id"])
    op.create_index("ix_update_posts_class_section_id", "update_posts", ["class_section_id"])
    op.create_index("ix_update_posts_subject_group_id", "update_posts", ["subject_group_id"])
    op.create_index("ix_update_posts_school_status_created", "update_posts", ["school_id", "status", "created_at"])
    op.create_table(
        "update_photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("update_posts.id"), nullable=False),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False, unique=True),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_update_photos_post_id", "update_photos", ["post_id"])
    op.create_index("ix_update_photos_school_id", "update_photos", ["school_id"])
    op.create_index("ix_update_photos_uploaded_by_user_id", "update_photos", ["uploaded_by_user_id"])
    op.create_index("ix_update_photos_storage_key", "update_photos", ["storage_key"], unique=True)
    op.create_index("ix_update_photos_post_school", "update_photos", ["post_id", "school_id"])


def downgrade():
    op.drop_table("update_photos")
    op.drop_table("update_posts")

"""add homework completion and resource links

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("homework_items", sa.Column("resource_links", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.create_table(
        "homework_item_completions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("homework_item_id", sa.Integer(), sa.ForeignKey("homework_items.id"), nullable=False),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("guardian_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("homework_item_id", "guardian_user_id", name="uq_homework_completion_item_guardian"),
    )
    op.create_index("ix_homework_item_completions_homework_item_id", "homework_item_completions", ["homework_item_id"])
    op.create_index("ix_homework_item_completions_school_id", "homework_item_completions", ["school_id"])
    op.create_index("ix_homework_item_completions_guardian_user_id", "homework_item_completions", ["guardian_user_id"])
    op.create_index("ix_homework_completions_guardian_item", "homework_item_completions", ["guardian_user_id", "homework_item_id"])


def downgrade():
    op.drop_table("homework_item_completions")
    op.drop_column("homework_items", "resource_links")

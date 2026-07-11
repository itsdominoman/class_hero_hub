"""add behaviour categories and point events

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
"""
from alembic import op
import sqlalchemy as sa

revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "behaviour_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("points_value", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("type IN ('positive', 'needs_work')", name="ck_behaviour_categories_type"),
        sa.CheckConstraint("(type = 'positive' AND points_value > 0) OR (type = 'needs_work' AND points_value < 0)", name="ck_behaviour_categories_value_sign"),
        sa.UniqueConstraint("school_id", "type", "label", name="uq_behaviour_categories_school_type_label"),
    )
    op.create_index("ix_behaviour_categories_school_id", "behaviour_categories", ["school_id"])
    op.create_index("ix_behaviour_categories_school_active_sort", "behaviour_categories", ["school_id", "active", "type", "sort_order"])
    op.create_table(
        "behaviour_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("behaviour_categories.id"), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("points_delta", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("source", sa.String(), nullable=False, server_default="teacher"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reversal_reason", sa.String(), nullable=True),
        sa.CheckConstraint("source IN ('teacher', 'admin', 'correction')", name="ck_behaviour_events_source"),
    )
    for column in ("school_id", "student_id", "category_id", "actor_user_id"):
        op.create_index(f"ix_behaviour_events_{column}", "behaviour_events", [column])
    op.create_index("ix_behaviour_events_school_student_created", "behaviour_events", ["school_id", "student_id", "created_at"])


def downgrade():
    op.drop_table("behaviour_events")
    op.drop_table("behaviour_categories")

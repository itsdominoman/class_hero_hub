"""Add demo seed records manifest table.

Revision ID: a6b7c8d9e0f1
Revises: f2a3b4c5d6e8
Create Date: 2026-07-12 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "demo_seed_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seed_namespace", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_key", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("seed_namespace", "entity_type", "entity_key", name="uq_demo_seed_records_namespace_type_key"),
    )
    op.create_index("ix_demo_seed_records_namespace_type", "demo_seed_records", ["seed_namespace", "entity_type"])
    op.create_index(op.f("ix_demo_seed_records_model_id"), "demo_seed_records", ["model_id"])
    op.create_index(op.f("ix_demo_seed_records_seed_namespace"), "demo_seed_records", ["seed_namespace"])
    op.create_index(op.f("ix_demo_seed_records_entity_type"), "demo_seed_records", ["entity_type"])


def downgrade() -> None:
    op.drop_index(op.f("ix_demo_seed_records_entity_type"), table_name="demo_seed_records")
    op.drop_index(op.f("ix_demo_seed_records_seed_namespace"), table_name="demo_seed_records")
    op.drop_index(op.f("ix_demo_seed_records_model_id"), table_name="demo_seed_records")
    op.drop_index("ix_demo_seed_records_namespace_type", table_name="demo_seed_records")
    op.drop_table("demo_seed_records")

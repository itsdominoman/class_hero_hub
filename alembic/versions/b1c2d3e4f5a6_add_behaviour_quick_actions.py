"""Add school-wide quick behaviour action metadata.

Revision ID: b1c2d3e4f5a6
Revises: a9b0c1d2e3f4
Create Date: 2026-07-13 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

QUICK_DEFAULTS = {
    "positive": ["Listening well", "Good work", "Teamwork", "Helping others", "Kindness", "Great effort"],
    "needs_work": ["Not listening", "Disrupting others", "Unkind behaviour", "Unsafe behaviour", "Off-task", "Not following instructions"],
}


def upgrade() -> None:
    with op.batch_alter_table("behaviour_categories") as batch_op:
        batch_op.add_column(sa.Column("is_quick_action", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("quick_action_order", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_behaviour_categories_quick_action_order",
            "NOT is_quick_action OR quick_action_order IS NOT NULL",
        )
    for category_type, labels in QUICK_DEFAULTS.items():
        for order, label in enumerate(labels, 1):
            op.execute(
                sa.text(
                    "UPDATE behaviour_categories "
                    "SET is_quick_action = true, quick_action_order = :quick_action_order "
                    "WHERE type = :category_type AND label = :label AND active IS TRUE AND is_quick_action IS FALSE"
                ).bindparams(quick_action_order=order, category_type=category_type, label=label)
            )
    op.create_index(
        "ix_behaviour_categories_school_quick_actions",
        "behaviour_categories",
        ["school_id", "active", "is_quick_action", "type", "quick_action_order", "sort_order"],
    )


def downgrade() -> None:
    op.drop_index("ix_behaviour_categories_school_quick_actions", table_name="behaviour_categories")
    with op.batch_alter_table("behaviour_categories") as batch_op:
        batch_op.drop_constraint("ck_behaviour_categories_quick_action_order", type_="check")
        batch_op.drop_column("quick_action_order")
        batch_op.drop_column("is_quick_action")

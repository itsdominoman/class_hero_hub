"""drop household domain

Revision ID: d4e5f6a7b8c9
Revises: c1a2b3d4e5f6
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c1a2b3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


HOUSEHOLD_TABLES = [
    "school_item_checks",
    "calendar_task_completions",
    "weekly_streaks",
    "child_allowance_settings",
    "child_device_sessions",
    "child_device_invites",
    "ledger_transactions",
    "redemption_requests",
    "pet_progress",
    "school_items",
    "calendar_entries",
    "preset_behaviours",
    "rewards",
    "family_invites",
    "registration_requests",
    "approved_parent_emails",
    "children",
    "parent_users",
    "families",
]


def upgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        for table_name in HOUSEHOLD_TABLES:
            op.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
        return

    for table_name in HOUSEHOLD_TABLES:
        op.drop_table(table_name)


def downgrade() -> None:
    pass

"""Add report-range indexes for behaviour events.

Revision ID: a9b0c1d2e3f4
Revises: a6b7c8d9e0f1
Create Date: 2026-07-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a9b0c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "a6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_behaviour_events_school_created", "behaviour_events", ["school_id", "created_at"])
    op.create_index("ix_behaviour_events_school_class_created", "behaviour_events", ["school_id", "class_section_id", "created_at"])
    op.create_index("ix_behaviour_events_school_subject_group_created", "behaviour_events", ["school_id", "subject_group_id", "created_at"])
    op.create_index("ix_behaviour_events_school_actor_created", "behaviour_events", ["school_id", "actor_user_id", "created_at"])
    op.create_index("ix_behaviour_events_school_category_created", "behaviour_events", ["school_id", "category_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_behaviour_events_school_category_created", table_name="behaviour_events")
    op.drop_index("ix_behaviour_events_school_actor_created", table_name="behaviour_events")
    op.drop_index("ix_behaviour_events_school_subject_group_created", table_name="behaviour_events")
    op.drop_index("ix_behaviour_events_school_class_created", table_name="behaviour_events")
    op.drop_index("ix_behaviour_events_school_created", table_name="behaviour_events")

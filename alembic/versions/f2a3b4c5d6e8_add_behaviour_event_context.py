"""Add event-time context to behaviour events.

Revision ID: f2a3b4c5d6e8
Revises: d7e8f9a0b1c2
Create Date: 2026-07-12 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f2a3b4c5d6e8"
down_revision: Union[str, Sequence[str], None] = "d7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("behaviour_events", sa.Column("class_section_id", sa.Integer(), nullable=True))
    op.add_column("behaviour_events", sa.Column("subject_group_id", sa.Integer(), nullable=True))
    op.add_column("behaviour_events", sa.Column("context_type", sa.String(), server_default="general", nullable=False))
    op.add_column("behaviour_events", sa.Column("duty_context", sa.String(), nullable=True))
    op.create_foreign_key("fk_behaviour_events_class_section_id", "behaviour_events", "class_sections", ["class_section_id"], ["id"])
    op.create_foreign_key("fk_behaviour_events_subject_group_id", "behaviour_events", "subject_groups", ["subject_group_id"], ["id"])
    op.create_check_constraint("ck_behaviour_events_context_type", "behaviour_events", "context_type IN ('class', 'subject', 'duty', 'general')")
    op.create_check_constraint("ck_behaviour_events_duty_context", "behaviour_events", "duty_context IS NULL OR duty_context IN ('break', 'lunch', 'playground', 'hallway', 'assembly', 'bus', 'general_duty')")
    op.create_check_constraint(
        "ck_behaviour_events_context_combination",
        "behaviour_events",
        "(context_type = 'subject' AND subject_group_id IS NOT NULL AND class_section_id IS NULL AND duty_context IS NULL) OR "
        "(context_type = 'class' AND class_section_id IS NOT NULL AND subject_group_id IS NULL AND duty_context IS NULL) OR "
        "(context_type = 'duty' AND duty_context IS NOT NULL AND class_section_id IS NULL AND subject_group_id IS NULL) OR "
        "(context_type = 'general' AND class_section_id IS NULL AND subject_group_id IS NULL AND duty_context IS NULL)",
    )
    op.create_index(op.f("ix_behaviour_events_class_section_id"), "behaviour_events", ["class_section_id"])
    op.create_index(op.f("ix_behaviour_events_subject_group_id"), "behaviour_events", ["subject_group_id"])
    op.create_index("ix_behaviour_events_school_context_created", "behaviour_events", ["school_id", "context_type", "duty_context", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_behaviour_events_school_context_created", table_name="behaviour_events")
    op.drop_index(op.f("ix_behaviour_events_subject_group_id"), table_name="behaviour_events")
    op.drop_index(op.f("ix_behaviour_events_class_section_id"), table_name="behaviour_events")
    op.drop_constraint("ck_behaviour_events_context_combination", "behaviour_events", type_="check")
    op.drop_constraint("ck_behaviour_events_duty_context", "behaviour_events", type_="check")
    op.drop_constraint("ck_behaviour_events_context_type", "behaviour_events", type_="check")
    op.drop_constraint("fk_behaviour_events_subject_group_id", "behaviour_events", type_="foreignkey")
    op.drop_constraint("fk_behaviour_events_class_section_id", "behaviour_events", type_="foreignkey")
    op.drop_column("behaviour_events", "duty_context")
    op.drop_column("behaviour_events", "context_type")
    op.drop_column("behaviour_events", "subject_group_id")
    op.drop_column("behaviour_events", "class_section_id")

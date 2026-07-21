"""Expand the durable notification outbox to school-originated family events.

Revision ID: a27b3c4d5e6f
Revises: f0a1b2c3d4e6
Create Date: 2026-07-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "a27b3c4d5e6f"
down_revision = "f0a1b2c3d4e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("notification_outbox", "message_id", existing_type=sa.BigInteger(), nullable=True)
    op.add_column("notification_outbox", sa.Column("event_category", sa.String(length=24), nullable=False, server_default="chat"))
    op.add_column("notification_outbox", sa.Column("source_type", sa.String(length=40), nullable=True))
    op.add_column("notification_outbox", sa.Column("source_id", sa.Integer(), nullable=True))
    op.add_column("notification_outbox", sa.Column("source_action", sa.String(length=24), nullable=True))
    op.add_column("notification_outbox", sa.Column("source_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("notification_outbox", sa.Column("route_type", sa.String(length=24), nullable=False, server_default="school_chat"))
    op.add_column("notification_outbox", sa.Column("route_ref", sa.String(length=120), nullable=True))
    op.add_column("notification_outbox", sa.Column("urgent", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_check_constraint(
        "ck_notification_outbox_category",
        "notification_outbox",
        "event_category IN ('chat', 'homework', 'notice', 'points', 'calendar', 'update')",
    )
    op.create_check_constraint(
        "ck_notification_outbox_route_type",
        "notification_outbox",
        "route_type IN ('school_chat', 'homework', 'notice', 'points', 'calendar', 'update')",
    )
    op.create_check_constraint("ck_notification_outbox_source_version", "notification_outbox", "source_version >= 1")
    op.create_check_constraint(
        "ck_notification_outbox_source_shape",
        "notification_outbox",
        "(event_category = 'chat' AND message_id IS NOT NULL AND source_type IS NULL "
        "AND source_id IS NULL AND source_action IS NULL) OR "
        "(event_category <> 'chat' AND message_id IS NULL AND recipient_kind = 'fhh_link' "
        "AND source_type IS NOT NULL AND source_id IS NOT NULL AND source_action IS NOT NULL "
        "AND route_ref IS NOT NULL)",
    )
    op.create_index(
        "ix_notification_outbox_school_category_state",
        "notification_outbox",
        ["school_id", "event_category", "state", "id"],
    )
    op.create_index(
        "ix_notification_outbox_source",
        "notification_outbox",
        ["school_id", "source_type", "source_id", "source_version"],
    )
    op.add_column("announcements", sa.Column("urgent", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("announcements", "urgent")
    op.drop_index("ix_notification_outbox_source", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_school_category_state", table_name="notification_outbox")
    op.drop_constraint("ck_notification_outbox_source_shape", "notification_outbox", type_="check")
    op.drop_constraint("ck_notification_outbox_source_version", "notification_outbox", type_="check")
    op.drop_constraint("ck_notification_outbox_route_type", "notification_outbox", type_="check")
    op.drop_constraint("ck_notification_outbox_category", "notification_outbox", type_="check")
    for column in ("urgent", "route_ref", "route_type", "source_version", "source_action", "source_id", "source_type", "event_category"):
        op.drop_column("notification_outbox", column)
    op.alter_column("notification_outbox", "message_id", existing_type=sa.BigInteger(), nullable=False)

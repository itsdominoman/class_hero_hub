"""Add Messaging v1 contact hours and durable notification outbox.

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-20 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "school_messaging_policies",
        sa.Column("contact_hours_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "school_messaging_policies",
        sa.Column(
            "notification_delay_mode",
            sa.String(length=40),
            nullable=False,
            server_default="delay_notifications_only",
        ),
    )
    op.create_check_constraint(
        "ck_school_messaging_policies_delay_mode",
        "school_messaging_policies",
        "notification_delay_mode = 'delay_notifications_only'",
    )

    op.create_table(
        "school_contact_windows",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_local", sa.Time(), nullable=False),
        sa.Column("end_local", sa.Time(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("weekday BETWEEN 1 AND 7", name="ck_school_contact_windows_weekday"),
        sa.CheckConstraint("start_local <> end_local", name="ck_school_contact_windows_nonempty"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "weekday", name="uq_school_contact_windows_school_weekday"),
    )
    op.create_index("ix_school_contact_windows_school_id", "school_contact_windows", ["school_id"])
    op.create_index(
        "ix_school_contact_windows_school_weekday",
        "school_contact_windows",
        ["school_id", "weekday"],
    )

    op.create_table(
        "school_contact_exceptions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("start_local", sa.Time(), nullable=True),
        sa.Column("end_local", sa.Time(), nullable=True),
        sa.Column("label", sa.String(length=160), nullable=True),
        sa.Column("label_ar", sa.String(length=160), nullable=True),
        sa.Column("created_by_membership_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('closed', 'custom')", name="ck_school_contact_exceptions_kind"),
        sa.CheckConstraint(
            "(kind = 'closed' AND start_local IS NULL AND end_local IS NULL) OR "
            "(kind = 'custom' AND start_local IS NOT NULL AND end_local IS NOT NULL "
            "AND start_local <> end_local)",
            name="ck_school_contact_exceptions_window_shape",
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["created_by_membership_id"],
            ["memberships.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "local_date", name="uq_school_contact_exceptions_school_date"),
    )
    op.create_index("ix_school_contact_exceptions_school_id", "school_contact_exceptions", ["school_id"])
    op.create_index(
        "ix_school_contact_exceptions_school_date",
        "school_contact_exceptions",
        ["school_id", "local_date"],
    )

    op.create_table(
        "staff_messaging_preferences",
        sa.Column("membership_id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column(
            "out_of_hours_notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("preference_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("preference_version >= 1", name="ck_staff_messaging_preferences_version"),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("membership_id"),
    )
    op.create_index("ix_staff_messaging_preferences_school_id", "staff_messaging_preferences", ["school_id"])
    op.create_index(
        "ix_staff_messaging_preferences_school_membership",
        "staff_messaging_preferences",
        ["school_id", "membership_id"],
    )

    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("recipient_kind", sa.String(length=20), nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), nullable=True),
        sa.Column("recipient_fhh_link_id", sa.Integer(), nullable=True),
        sa.Column("recipient_participant_id", sa.BigInteger(), nullable=True),
        sa.Column("channel", sa.String(length=16), nullable=False, server_default="push"),
        sa.Column("template_key", sa.String(length=96), nullable=False),
        sa.Column(
            "template_args",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("deep_link", sa.String(length=300), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("eligible_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduler_check_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_owner", sa.String(length=96), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_message_ref", sa.String(length=200), nullable=True),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(length=240), nullable=False),
        sa.CheckConstraint(
            "(recipient_kind = 'chh_user' AND recipient_user_id IS NOT NULL "
            "AND recipient_fhh_link_id IS NULL AND recipient_participant_id IS NOT NULL) OR "
            "(recipient_kind = 'fhh_link' AND recipient_user_id IS NULL "
            "AND recipient_fhh_link_id IS NOT NULL AND recipient_participant_id IS NULL)",
            name="ck_notification_outbox_recipient_shape",
        ),
        sa.CheckConstraint(
            "channel IN ('push', 'email', 'in_app_event')",
            name="ck_notification_outbox_channel",
        ),
        sa.CheckConstraint(
            "state IN ('held', 'pending', 'leased', 'dispatched', 'provider_accepted', "
            "'failed', 'dead', 'cancelled')",
            name="ck_notification_outbox_state",
        ),
        sa.CheckConstraint("policy_version >= 1", name="ck_notification_outbox_policy_version"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_notification_outbox_attempt_count"),
        sa.CheckConstraint(
            "(state = 'leased' AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL) OR "
            "(state <> 'leased' AND lease_owner IS NULL AND lease_expires_at IS NULL)",
            name="ck_notification_outbox_lease_shape",
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recipient_fhh_link_id"], ["fhh_links.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["recipient_participant_id"],
            ["conversation_participants.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_notification_outbox_event_id"),
        sa.UniqueConstraint("dedupe_key", name="uq_notification_outbox_dedupe_key"),
    )
    for name, columns in (
        ("ix_notification_outbox_school_id", ["school_id"]),
        ("ix_notification_outbox_message_id", ["message_id"]),
        (
            "ix_notification_outbox_scheduler",
            ["state", "scheduler_check_at", "lease_expires_at", "id"],
        ),
        (
            "ix_notification_outbox_dispatch",
            ["state", "next_attempt_at", "eligible_at", "id"],
        ),
        ("ix_notification_outbox_school_state", ["school_id", "state", "id"]),
        (
            "ix_notification_outbox_fhh_link_created",
            ["recipient_fhh_link_id", "created_at"],
        ),
    ):
        op.create_index(name, "notification_outbox", columns)


def downgrade() -> None:
    op.drop_table("notification_outbox")
    op.drop_table("staff_messaging_preferences")
    op.drop_table("school_contact_exceptions")
    op.drop_table("school_contact_windows")
    op.drop_constraint(
        "ck_school_messaging_policies_delay_mode",
        "school_messaging_policies",
        type_="check",
    )
    op.drop_column("school_messaging_policies", "notification_delay_mode")
    op.drop_column("school_messaging_policies", "contact_hours_enabled")

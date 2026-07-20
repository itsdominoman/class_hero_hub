"""Add durable Android installations and per-device notification delivery.

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-07-20 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d9e0f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "device_push_registrations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("installation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False, server_default="android"),
        sa.Column("app_package", sa.String(length=100), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("fcm_token", sa.String(length=512), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("disabled_reason", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("platform = 'android'", name="ck_device_push_registrations_platform"),
        sa.CheckConstraint("locale IN ('en', 'ar')", name="ck_device_push_registrations_locale"),
        sa.CheckConstraint(
            "state IN ('active', 'revoked', 'invalid')",
            name="ck_device_push_registrations_state",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fcm_token", name="uq_device_push_registrations_fcm_token"),
        sa.UniqueConstraint(
            "app_package",
            "installation_id",
            name="uq_device_push_registrations_package_installation",
        ),
    )
    op.create_index("ix_device_push_registrations_user_id", "device_push_registrations", ["user_id"])
    op.create_index(
        "ix_device_push_registrations_user_state",
        "device_push_registrations",
        ["user_id", "state", "id"],
    )

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("outbox_id", sa.BigInteger(), nullable=False),
        sa.Column("device_registration_id", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("lease_owner", sa.String(length=96), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_message_ref", sa.String(length=200), nullable=True),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('pending', 'leased', 'provider_accepted', 'failed', 'dead', 'cancelled')",
            name="ck_notification_deliveries_state",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_notification_deliveries_attempt_count"),
        sa.CheckConstraint(
            "(state = 'leased' AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL) OR "
            "(state <> 'leased' AND lease_owner IS NULL AND lease_expires_at IS NULL)",
            name="ck_notification_deliveries_lease_shape",
        ),
        sa.ForeignKeyConstraint(["device_registration_id"], ["device_push_registrations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["outbox_id"], ["notification_outbox.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("outbox_id", "device_registration_id", name="uq_notification_deliveries_outbox_device"),
    )
    op.create_index("ix_notification_deliveries_outbox_id", "notification_deliveries", ["outbox_id"])
    op.create_index("ix_notification_deliveries_device_registration_id", "notification_deliveries", ["device_registration_id"])
    op.create_index(
        "ix_notification_deliveries_dispatch",
        "notification_deliveries",
        ["state", "next_attempt_at", "lease_expires_at", "id"],
    )


def downgrade() -> None:
    op.drop_table("notification_deliveries")
    op.drop_table("device_push_registrations")

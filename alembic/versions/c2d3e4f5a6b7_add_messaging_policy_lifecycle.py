"""Add Messaging v1 policy and FHH lifecycle prerequisites.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-16 00:00:00.000000
"""
from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("schools", sa.Column("messaging_remote_ref", sa.Uuid(), nullable=True))
    bind = op.get_bind()
    school_ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM schools")).fetchall()]
    for school_id in school_ids:
        bind.execute(
            sa.text("UPDATE schools SET messaging_remote_ref = :remote_ref WHERE id = :school_id"),
            {"remote_ref": uuid.uuid4(), "school_id": school_id},
        )
    op.alter_column("schools", "messaging_remote_ref", nullable=False)
    op.create_unique_constraint("uq_schools_messaging_remote_ref", "schools", ["messaging_remote_ref"])

    op.create_table(
        "school_messaging_policies",
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("guardian_replies_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("delivery_receipts_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("read_receipts_visible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_staff_out_of_hours_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("teachers_may_mark_urgent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notification_preview_mode", sa.String(length=24), nullable=False, server_default="generic"),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="2557"),
        sa.Column("email_mode", sa.String(length=16), nullable=False, server_default="off"),
        sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by_membership_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("notification_preview_mode IN ('generic', 'sender_only', 'body')", name="ck_school_messaging_policies_preview"),
        sa.CheckConstraint("email_mode IN ('off', 'immediate', 'digest')", name="ck_school_messaging_policies_email_mode"),
        sa.CheckConstraint("retention_days BETWEEN 30 AND 36500", name="ck_school_messaging_policies_retention"),
        sa.CheckConstraint("policy_version >= 1", name="ck_school_messaging_policies_version"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_membership_id"], ["memberships.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("school_id"),
    )
    if school_ids:
        bind.execute(
            sa.text(
                "INSERT INTO school_messaging_policies (school_id) "
                "SELECT id FROM schools"
            )
        )

    op.create_table(
        "fhh_messaging_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=24), nullable=False, server_default="fhh"),
        sa.Column("external_subject_ref", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("preferred_locale", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("preferred_locale IN ('en', 'ar')", name="ck_fhh_messaging_identities_locale"),
        sa.CheckConstraint("status IN ('active', 'revoked', 'anonymized')", name="ck_fhh_messaging_identities_status"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "provider", "external_subject_ref", name="uq_fhh_messaging_identity_subject"),
    )
    op.create_index("ix_fhh_messaging_identities_school_id", "fhh_messaging_identities", ["school_id"])

    op.create_table(
        "fhh_messaging_identity_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("fhh_link_id", sa.Integer(), nullable=False),
        sa.Column("identity_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("sync_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('active', 'revoked')", name="ck_fhh_messaging_identity_links_status"),
        sa.CheckConstraint("sync_version >= 1", name="ck_fhh_messaging_identity_links_version"),
        sa.ForeignKeyConstraint(["fhh_link_id"], ["fhh_links.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["identity_id"], ["fhh_messaging_identities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fhh_link_id", "identity_id", name="uq_fhh_messaging_identity_link"),
    )
    op.create_index("ix_fhh_messaging_identity_links_school_id", "fhh_messaging_identity_links", ["school_id"])
    op.create_index("ix_fhh_messaging_identity_links_fhh_link_id", "fhh_messaging_identity_links", ["fhh_link_id"])
    op.create_index("ix_fhh_messaging_identity_links_identity_id", "fhh_messaging_identity_links", ["identity_id"])
    op.create_index("ix_fhh_messaging_identity_links_school_status", "fhh_messaging_identity_links", ["school_id", "status"])

    op.create_table(
        "fhh_messaging_lifecycle_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("fhh_link_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("external_subject_ref", sa.Uuid(), nullable=True),
        sa.Column("sync_version", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "action IN ('parent_granted', 'parent_profile_changed', 'parent_revoked', "
            "'identity_anonymized', 'link_revoked', 'family_deleted')",
            name="ck_fhh_messaging_lifecycle_events_action",
        ),
        sa.CheckConstraint("sync_version >= 1", name="ck_fhh_messaging_lifecycle_events_version"),
        sa.CheckConstraint("outcome IN ('applied', 'stale_ignored')", name="ck_fhh_messaging_lifecycle_events_outcome"),
        sa.ForeignKeyConstraint(["fhh_link_id"], ["fhh_links.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_fhh_messaging_lifecycle_events_school_id", "fhh_messaging_lifecycle_events", ["school_id"])
    op.create_index("ix_fhh_messaging_lifecycle_events_fhh_link_id", "fhh_messaging_lifecycle_events", ["fhh_link_id"])
    op.create_index("ix_fhh_messaging_lifecycle_events_link_applied", "fhh_messaging_lifecycle_events", ["fhh_link_id", "applied_at"])


def downgrade() -> None:
    op.drop_index("ix_fhh_messaging_lifecycle_events_link_applied", table_name="fhh_messaging_lifecycle_events")
    op.drop_index("ix_fhh_messaging_lifecycle_events_fhh_link_id", table_name="fhh_messaging_lifecycle_events")
    op.drop_index("ix_fhh_messaging_lifecycle_events_school_id", table_name="fhh_messaging_lifecycle_events")
    op.drop_table("fhh_messaging_lifecycle_events")
    op.drop_index("ix_fhh_messaging_identity_links_school_status", table_name="fhh_messaging_identity_links")
    op.drop_index("ix_fhh_messaging_identity_links_identity_id", table_name="fhh_messaging_identity_links")
    op.drop_index("ix_fhh_messaging_identity_links_fhh_link_id", table_name="fhh_messaging_identity_links")
    op.drop_index("ix_fhh_messaging_identity_links_school_id", table_name="fhh_messaging_identity_links")
    op.drop_table("fhh_messaging_identity_links")
    op.drop_index("ix_fhh_messaging_identities_school_id", table_name="fhh_messaging_identities")
    op.drop_table("fhh_messaging_identities")
    op.drop_table("school_messaging_policies")
    op.drop_constraint("uq_schools_messaging_remote_ref", "schools", type_="unique")
    op.drop_column("schools", "messaging_remote_ref")

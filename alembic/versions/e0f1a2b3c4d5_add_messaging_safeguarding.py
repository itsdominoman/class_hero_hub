"""Add Messaging v1 safeguarding review, moderation and evidence exports.

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-07-20 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "e0f1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "d9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("restriction_type", sa.String(length=32), nullable=True))
    op.add_column("conversations", sa.Column("restricted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("conversations", sa.Column("restricted_by_membership_id", sa.Integer(), nullable=True))
    op.add_column(
        "conversations",
        sa.Column("reopening_requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("conversations", sa.Column("safeguarding_closed_by_membership_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_conversations_restricted_by_membership",
        "conversations",
        "memberships",
        ["restricted_by_membership_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_conversations_safeguarding_closed_by_membership",
        "conversations",
        "memberships",
        ["safeguarding_closed_by_membership_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_conversations_restriction_type",
        "conversations",
        "restriction_type IS NULL OR restriction_type IN "
        "('family_replies', 'staff_replies', 'both_replies', 'read_only')",
    )
    op.create_check_constraint(
        "ck_conversations_restriction_shape",
        "conversations",
        "(restriction_type IS NULL AND restricted_at IS NULL "
        "AND restricted_by_membership_id IS NULL) OR "
        "(restriction_type IS NOT NULL AND restricted_at IS NOT NULL "
        "AND restricted_by_membership_id IS NOT NULL)",
    )

    op.create_table(
        "messaging_permission_grants",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("membership_id", sa.Integer(), nullable=False),
        sa.Column("permission", sa.String(length=80), nullable=False),
        sa.Column("granted_by_membership_id", sa.Integer(), nullable=False),
        sa.Column("grant_reason", sa.Text(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_membership_id", sa.Integer(), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "permission IN ('messaging.safeguarding_review', 'messaging.moderate', "
            "'messaging.export_evidence', 'messaging.export_internal_notes', "
            "'messaging.manage_safeguarding_permissions')",
            name="ck_messaging_permission_grants_permission",
        ),
        sa.CheckConstraint("length(grant_reason) BETWEEN 3 AND 1000", name="ck_messaging_permission_grants_reason"),
        sa.CheckConstraint(
            "(revoked_at IS NULL AND revoked_by_membership_id IS NULL AND revoke_reason IS NULL) OR "
            "(revoked_at IS NOT NULL AND revoked_by_membership_id IS NOT NULL "
            "AND length(revoke_reason) BETWEEN 3 AND 1000)",
            name="ck_messaging_permission_grants_revoke_shape",
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["granted_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revoked_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_messaging_permission_grants_public_id"),
    )
    op.create_index("ix_messaging_permission_grants_school_id", "messaging_permission_grants", ["school_id"])
    op.create_index("ix_messaging_permission_grants_membership_id", "messaging_permission_grants", ["membership_id"])
    op.create_index(
        "uq_messaging_permission_grants_active",
        "messaging_permission_grants",
        ["school_id", "membership_id", "permission"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index(
        "ix_messaging_permission_grants_school_permission",
        "messaging_permission_grants",
        ["school_id", "permission", "revoked_at"],
    )

    op.create_table(
        "safeguarding_review_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("reviewer_membership_id", sa.Integer(), nullable=False),
        sa.Column("reason_category", sa.String(length=48), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("acknowledgement", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_membership_id", sa.Integer(), nullable=True),
        sa.Column("end_reason", sa.String(length=48), nullable=True),
        sa.CheckConstraint(
            "reason_category IN ('reported_concern', 'safeguarding_investigation', "
            "'complaint', 'staff_conduct_review', 'parent_communication_review', "
            "'legal_regulatory_request', 'authorised_technical_support', 'other')",
            name="ck_safeguarding_review_sessions_reason",
        ),
        sa.CheckConstraint("length(justification) BETWEEN 8 AND 2000", name="ck_safeguarding_review_sessions_justification"),
        sa.CheckConstraint("acknowledgement = true", name="ck_safeguarding_review_sessions_acknowledged"),
        sa.CheckConstraint("expires_at > started_at", name="ck_safeguarding_review_sessions_expiry"),
        sa.CheckConstraint("revoked_at IS NULL OR revoked_by_membership_id IS NOT NULL", name="ck_safeguarding_review_sessions_revoke_shape"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewer_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revoked_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_safeguarding_review_sessions_public_id"),
    )
    op.create_index("ix_safeguarding_review_sessions_school_id", "safeguarding_review_sessions", ["school_id"])
    op.create_index("ix_safeguarding_review_sessions_conversation_id", "safeguarding_review_sessions", ["conversation_id"])
    op.create_index("ix_safeguarding_review_sessions_reviewer_membership_id", "safeguarding_review_sessions", ["reviewer_membership_id"])
    op.create_index("ix_safeguarding_review_sessions_actor_expiry", "safeguarding_review_sessions", ["school_id", "reviewer_membership_id", "expires_at", "ended_at"])
    op.create_index("ix_safeguarding_review_sessions_conversation", "safeguarding_review_sessions", ["school_id", "conversation_id", "started_at"])

    op.create_table(
        "safeguarding_internal_notes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("review_session_id", sa.BigInteger(), nullable=False),
        sa.Column("author_membership_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("correction_of_note_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("length(body) BETWEEN 3 AND 10000", name="ck_safeguarding_internal_notes_body"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["review_session_id"], ["safeguarding_review_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["author_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["correction_of_note_id"], ["safeguarding_internal_notes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_safeguarding_internal_notes_public_id"),
    )
    op.create_index("ix_safeguarding_internal_notes_school_id", "safeguarding_internal_notes", ["school_id"])
    op.create_index("ix_safeguarding_internal_notes_conversation_id", "safeguarding_internal_notes", ["conversation_id"])
    op.create_index("ix_safeguarding_internal_notes_conversation_created", "safeguarding_internal_notes", ["conversation_id", "created_at", "id"])

    op.create_table(
        "safeguarding_flags",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("category", sa.String(length=48), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column("assigned_membership_id", sa.Integer(), nullable=True),
        sa.Column("created_by_membership_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_membership_id", sa.Integer(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name="ck_safeguarding_flags_severity"),
        sa.CheckConstraint("status IN ('open', 'follow_up', 'resolved')", name="ck_safeguarding_flags_status"),
        sa.CheckConstraint(
            "(status <> 'resolved' AND resolved_at IS NULL AND resolved_by_membership_id IS NULL) OR "
            "(status = 'resolved' AND resolved_at IS NOT NULL AND resolved_by_membership_id IS NOT NULL)",
            name="ck_safeguarding_flags_resolution_shape",
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resolved_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_safeguarding_flags_public_id"),
    )
    op.create_index("ix_safeguarding_flags_school_id", "safeguarding_flags", ["school_id"])
    op.create_index("ix_safeguarding_flags_conversation_id", "safeguarding_flags", ["conversation_id"])
    op.create_index("ix_safeguarding_flags_message_id", "safeguarding_flags", ["message_id"])
    op.create_index("ix_safeguarding_flags_school_status", "safeguarding_flags", ["school_id", "status", "severity", "created_at"])
    op.create_index("ix_safeguarding_flags_conversation_status", "safeguarding_flags", ["conversation_id", "status", "created_at"])

    op.create_table(
        "messaging_moderation_actions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("review_session_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_membership_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("restriction_type", sa.String(length=32), nullable=True),
        sa.Column("reason_category", sa.String(length=48), nullable=False),
        sa.Column("confidential_reason", sa.Text(), nullable=False),
        sa.Column("participant_safe_reason", sa.String(length=240), nullable=True),
        sa.Column("prior_state_hash", sa.String(length=64), nullable=False),
        sa.Column("new_state_hash", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action IN ('restrict', 'remove_restriction', 'close', 'reopen', 'tombstone', 'restore')", name="ck_messaging_moderation_actions_action"),
        sa.CheckConstraint("restriction_type IS NULL OR restriction_type IN ('family_replies', 'staff_replies', 'both_replies', 'read_only')", name="ck_messaging_moderation_actions_restriction_type"),
        sa.CheckConstraint("length(confidential_reason) BETWEEN 8 AND 4000", name="ck_messaging_moderation_actions_reason"),
        sa.CheckConstraint("length(prior_state_hash) = 64 AND length(new_state_hash) = 64", name="ck_messaging_moderation_actions_hashes"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["review_session_id"], ["safeguarding_review_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_messaging_moderation_actions_event_id"),
    )
    op.create_index("ix_messaging_moderation_actions_school_id", "messaging_moderation_actions", ["school_id"])
    op.create_index("ix_messaging_moderation_actions_conversation_id", "messaging_moderation_actions", ["conversation_id"])
    op.create_index("ix_messaging_moderation_actions_message_id", "messaging_moderation_actions", ["message_id"])
    op.create_index("ix_messaging_moderation_actions_conversation", "messaging_moderation_actions", ["conversation_id", "occurred_at", "id"])

    op.create_table(
        "messaging_evidence_exports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("review_session_id", sa.BigInteger(), nullable=False),
        sa.Column("created_by_membership_id", sa.Integer(), nullable=False),
        sa.Column("export_mode", sa.String(length=24), nullable=False, server_default="internal"),
        sa.Column("reason_category", sa.String(length=48), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("include_internal_notes", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("state", sa.String(length=24), nullable=False, server_default="requested"),
        sa.Column("artifact_storage_key", sa.String(length=200), nullable=True),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=True),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_downloads", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.CheckConstraint("export_mode IN ('internal', 'participant_safe')", name="ck_messaging_evidence_exports_mode"),
        sa.CheckConstraint("state IN ('requested', 'ready', 'failed', 'expired', 'deleted')", name="ck_messaging_evidence_exports_state"),
        sa.CheckConstraint("length(justification) BETWEEN 8 AND 2000", name="ck_messaging_evidence_exports_reason"),
        sa.CheckConstraint("max_downloads BETWEEN 1 AND 10", name="ck_messaging_evidence_exports_max_downloads"),
        sa.CheckConstraint("download_count >= 0 AND download_count <= max_downloads", name="ck_messaging_evidence_exports_download_count"),
        sa.CheckConstraint("(state = 'ready' AND artifact_storage_key IS NOT NULL AND artifact_sha256 IS NOT NULL AND manifest_sha256 IS NOT NULL AND size_bytes > 0 AND generated_at IS NOT NULL) OR state <> 'ready'", name="ck_messaging_evidence_exports_ready_shape"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["review_session_id"], ["safeguarding_review_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_messaging_evidence_exports_public_id"),
    )
    op.create_index("ix_messaging_evidence_exports_school_id", "messaging_evidence_exports", ["school_id"])
    op.create_index("ix_messaging_evidence_exports_conversation_id", "messaging_evidence_exports", ["conversation_id"])
    op.create_index("ix_messaging_evidence_exports_created_by_membership_id", "messaging_evidence_exports", ["created_by_membership_id"])
    op.create_index("ix_messaging_evidence_exports_expiry", "messaging_evidence_exports", ["state", "expires_at", "id"])
    op.create_index("ix_messaging_evidence_exports_school_created", "messaging_evidence_exports", ["school_id", "created_at", "id"])

    op.execute(
        """
        CREATE OR REPLACE FUNCTION messaging_safeguarding_append_only_guard()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'safeguarding evidence rows are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in ("safeguarding_internal_notes", "messaging_moderation_actions"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION messaging_safeguarding_append_only_guard()"
        )


def downgrade() -> None:
    for table in ("messaging_moderation_actions", "safeguarding_internal_notes"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table}")
    op.execute("DROP FUNCTION IF EXISTS messaging_safeguarding_append_only_guard()")
    op.drop_table("messaging_evidence_exports")
    op.drop_table("messaging_moderation_actions")
    op.drop_table("safeguarding_flags")
    op.drop_table("safeguarding_internal_notes")
    op.drop_table("safeguarding_review_sessions")
    op.drop_table("messaging_permission_grants")
    op.drop_constraint("ck_conversations_restriction_shape", "conversations", type_="check")
    op.drop_constraint("ck_conversations_restriction_type", "conversations", type_="check")
    op.drop_constraint("fk_conversations_safeguarding_closed_by_membership", "conversations", type_="foreignkey")
    op.drop_constraint("fk_conversations_restricted_by_membership", "conversations", type_="foreignkey")
    op.drop_column("conversations", "safeguarding_closed_by_membership_id")
    op.drop_column("conversations", "reopening_requires_approval")
    op.drop_column("conversations", "restricted_by_membership_id")
    op.drop_column("conversations", "restricted_at")
    op.drop_column("conversations", "restriction_type")

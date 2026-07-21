"""Add Messaging v1 production governance and custody controls.

Revision ID: f0a1b2c3d4e6
Revises: e0f1a2b3c4d5
Create Date: 2026-07-21
"""
from __future__ import annotations

import json
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "f0a1b2c3d4e6"
down_revision = "e0f1a2b3c4d5"
branch_labels = None
depends_on = None


DEFAULT_RETENTION_RULES = {
    "message_days": 2557,
    "media_days": 2557,
    "media_hot_days": 365,
    "receipt_days": 2557,
    "notification_history_days": 365,
    "safeguarding_audit_days": 3650,
    "moderation_history_days": 3650,
    "internal_note_days": 3650,
    "export_metadata_days": 3650,
    "export_artifact_minutes": 30,
    "revoked_device_days": 90,
    "review_session_days": 3650,
    "assertion_replay_days": 30,
    "operations_job_days": 365,
    "operational_log_days": 90,
    "preserve_export_artifact_on_hold": False,
    "delete_hot_after_verified_archive": True,
}


def _add_media_columns() -> None:
    for name, type_ in (
        ("archive_full_storage_key", sa.String(length=500)),
        ("archive_thumbnail_storage_key", sa.String(length=500)),
        ("archive_full_sha256", sa.String(length=64)),
        ("archive_thumbnail_sha256", sa.String(length=64)),
        ("archived_at", sa.DateTime(timezone=True)),
        ("archive_verified_at", sa.DateTime(timezone=True)),
        ("hot_deleted_at", sa.DateTime(timezone=True)),
        ("retention_deleted_at", sa.DateTime(timezone=True)),
    ):
        op.add_column("message_media", sa.Column(name, type_, nullable=True))
    for name, type_ in (
        ("archive_storage_key", sa.String(length=500)),
        ("archive_sha256", sa.String(length=64)),
        ("archived_at", sa.DateTime(timezone=True)),
        ("archive_verified_at", sa.DateTime(timezone=True)),
        ("hot_deleted_at", sa.DateTime(timezone=True)),
        ("retention_deleted_at", sa.DateTime(timezone=True)),
    ):
        op.add_column("message_voice_media", sa.Column(name, type_, nullable=True))

    for table, constraints in (
        (
            "message_media",
            (
                "ck_message_media_state",
                "ck_message_media_attachment_shape",
            ),
        ),
        (
            "message_voice_media",
            (
                "ck_message_voice_media_state",
                "ck_message_voice_media_attachment_shape",
            ),
        ),
    ):
        for constraint in constraints:
            op.drop_constraint(constraint, table, type_="check")

    op.create_check_constraint(
        "ck_message_media_state",
        "message_media",
        "state IN ('processing', 'ready', 'attached', 'archived', 'retention_deleted', "
        "'failed', 'expired', 'deleted')",
    )
    op.create_check_constraint(
        "ck_message_media_attachment_shape",
        "message_media",
        "(state IN ('attached', 'archived', 'retention_deleted') AND message_id IS NOT NULL "
        "AND attached_at IS NOT NULL) OR "
        "(state NOT IN ('attached', 'archived', 'retention_deleted') AND message_id IS NULL "
        "AND attached_at IS NULL)",
    )
    op.create_check_constraint(
        "ck_message_media_archive_shape",
        "message_media",
        "(state = 'archived' AND archive_full_storage_key IS NOT NULL "
        "AND archive_thumbnail_storage_key IS NOT NULL AND length(archive_full_sha256) = 64 "
        "AND length(archive_thumbnail_sha256) = 64 AND archived_at IS NOT NULL "
        "AND archive_verified_at IS NOT NULL) OR state <> 'archived'",
    )
    op.create_check_constraint(
        "ck_message_media_retention_deleted",
        "message_media",
        "(state = 'retention_deleted' AND retention_deleted_at IS NOT NULL "
        "AND full_storage_key IS NULL AND thumbnail_storage_key IS NULL "
        "AND archive_full_storage_key IS NULL AND archive_thumbnail_storage_key IS NULL) "
        "OR state <> 'retention_deleted'",
    )
    op.create_index(
        "ix_message_media_archive_selection",
        "message_media",
        ["school_id", "state", "created_at", "id"],
    )

    op.create_check_constraint(
        "ck_message_voice_media_state",
        "message_voice_media",
        "state IN ('processing', 'ready', 'attached', 'archived', 'retention_deleted', "
        "'failed', 'expired', 'deleted')",
    )
    op.create_check_constraint(
        "ck_message_voice_media_attachment_shape",
        "message_voice_media",
        "(state IN ('attached', 'archived', 'retention_deleted') AND message_id IS NOT NULL "
        "AND attached_at IS NOT NULL) OR "
        "(state NOT IN ('attached', 'archived', 'retention_deleted') AND message_id IS NULL "
        "AND attached_at IS NULL)",
    )
    op.create_check_constraint(
        "ck_message_voice_media_archive_shape",
        "message_voice_media",
        "(state = 'archived' AND archive_storage_key IS NOT NULL "
        "AND length(archive_sha256) = 64 AND archived_at IS NOT NULL "
        "AND archive_verified_at IS NOT NULL) OR state <> 'archived'",
    )
    op.create_check_constraint(
        "ck_message_voice_media_retention_deleted",
        "message_voice_media",
        "(state = 'retention_deleted' AND retention_deleted_at IS NOT NULL "
        "AND storage_key IS NULL AND archive_storage_key IS NULL) "
        "OR state <> 'retention_deleted'",
    )
    op.create_index(
        "ix_message_voice_media_archive_selection",
        "message_voice_media",
        ["school_id", "state", "created_at", "id"],
    )


def _install_message_retention_guard() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION messaging_message_immutable_guard() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'messages are append-only';
          END IF;
          IF current_setting('chh.retention_worker', true) = 'on'
             AND OLD.retention_disposed_at IS NULL
             AND NEW.retention_disposed_at IS NOT NULL
             AND NEW.retention_policy_version IS NOT NULL
             AND length(NEW.retention_content_sha256) = 64
             AND NEW.body IS NULL
             AND NEW.public_id IS NOT DISTINCT FROM OLD.public_id
             AND NEW.school_id IS NOT DISTINCT FROM OLD.school_id
             AND NEW.conversation_id IS NOT DISTINCT FROM OLD.conversation_id
             AND NEW.sequence IS NOT DISTINCT FROM OLD.sequence
             AND NEW.sender_participant_id IS NOT DISTINCT FROM OLD.sender_participant_id
             AND NEW.sender_display_name_snapshot IS NOT DISTINCT FROM OLD.sender_display_name_snapshot
             AND NEW.client_message_id IS NOT DISTINCT FROM OLD.client_message_id
             AND NEW.message_type IS NOT DISTINCT FROM OLD.message_type
             AND NEW.urgent IS NOT DISTINCT FROM OLD.urgent
             AND NEW.created_at IS NOT DISTINCT FROM OLD.created_at THEN
            RETURN NEW;
          END IF;
          IF NEW.public_id IS DISTINCT FROM OLD.public_id
             OR NEW.school_id IS DISTINCT FROM OLD.school_id
             OR NEW.conversation_id IS DISTINCT FROM OLD.conversation_id
             OR NEW.sequence IS DISTINCT FROM OLD.sequence
             OR NEW.sender_participant_id IS DISTINCT FROM OLD.sender_participant_id
             OR NEW.sender_display_name_snapshot IS DISTINCT FROM OLD.sender_display_name_snapshot
             OR NEW.client_message_id IS DISTINCT FROM OLD.client_message_id
             OR NEW.message_type IS DISTINCT FROM OLD.message_type
             OR NEW.body IS DISTINCT FROM OLD.body
             OR NEW.urgent IS DISTINCT FROM OLD.urgent
             OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
            RAISE EXCEPTION 'message attribution and content are immutable';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )


def upgrade() -> None:
    op.create_table(
        "school_system_owners",
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("membership_id", sa.Integer(), nullable=False),
        sa.Column("owner_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("owner_since", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("owner_version >= 1", name="ck_school_system_owners_version"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("school_id"),
        sa.UniqueConstraint("membership_id", name="uq_school_system_owners_membership"),
    )
    op.create_index("ix_school_system_owners_membership", "school_system_owners", ["membership_id", "school_id"])
    op.create_table(
        "school_system_owner_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("previous_membership_id", sa.Integer(), nullable=True),
        sa.Column("new_membership_id", sa.Integer(), nullable=True),
        sa.Column("actor_kind", sa.String(length=24), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_membership_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("owner_version", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action IN ('bootstrap', 'transfer', 'recovery_required', 'platform_recovery')", name="ck_school_system_owner_events_action"),
        sa.CheckConstraint("actor_kind IN ('system', 'school_owner', 'platform_admin')", name="ck_school_system_owner_events_actor_kind"),
        sa.CheckConstraint("length(reason) BETWEEN 8 AND 2000", name="ck_school_system_owner_events_reason"),
        sa.CheckConstraint("owner_version >= 1", name="ck_school_system_owner_events_version"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["previous_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["new_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_school_system_owner_events_event_id"),
    )
    op.create_index("ix_school_system_owner_events_school_time", "school_system_owner_events", ["school_id", "occurred_at", "id"])

    op.create_table(
        "messaging_retention_policies",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("acknowledged_school_policy", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_membership_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_membership_id", sa.Integer(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.CheckConstraint("policy_version >= 1", name="ck_messaging_retention_policy_version"),
        sa.CheckConstraint("length(reason) BETWEEN 8 AND 2000", name="ck_messaging_retention_policy_reason"),
        sa.CheckConstraint("acknowledged_school_policy = true", name="ck_messaging_retention_policy_acknowledged"),
        sa.CheckConstraint("(cancelled_at IS NULL AND cancelled_by_membership_id IS NULL AND cancellation_reason IS NULL) OR (cancelled_at IS NOT NULL AND cancelled_by_membership_id IS NOT NULL AND length(cancellation_reason) BETWEEN 8 AND 2000)", name="ck_messaging_retention_policy_cancellation"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cancelled_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_messaging_retention_policies_public_id"),
        sa.UniqueConstraint("school_id", "policy_version", name="uq_messaging_retention_policy_version"),
    )
    op.create_index("ix_messaging_retention_policy_effective", "messaging_retention_policies", ["school_id", "effective_at", "policy_version"])

    op.create_table(
        "messaging_legal_holds",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("scope_type", sa.String(length=24), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=True),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("case_reference", sa.String(length=160), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_membership_id", sa.Integer(), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by_membership_id", sa.Integer(), nullable=True),
        sa.Column("release_reason", sa.Text(), nullable=True),
        sa.CheckConstraint("scope_type IN ('conversation', 'message', 'student')", name="ck_messaging_legal_holds_scope"),
        sa.CheckConstraint("(scope_type = 'conversation' AND conversation_id IS NOT NULL AND message_id IS NULL AND student_id IS NULL) OR (scope_type = 'message' AND conversation_id IS NULL AND message_id IS NOT NULL AND student_id IS NULL) OR (scope_type = 'student' AND conversation_id IS NULL AND message_id IS NULL AND student_id IS NOT NULL)", name="ck_messaging_legal_holds_target"),
        sa.CheckConstraint("length(reason) BETWEEN 8 AND 4000", name="ck_messaging_legal_holds_reason"),
        sa.CheckConstraint("review_at IS NULL OR review_at > starts_at", name="ck_messaging_legal_holds_review"),
        sa.CheckConstraint("(released_at IS NULL AND released_by_membership_id IS NULL AND release_reason IS NULL) OR (released_at IS NOT NULL AND released_by_membership_id IS NOT NULL AND length(release_reason) BETWEEN 8 AND 4000)", name="ck_messaging_legal_holds_release"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["released_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_messaging_legal_holds_public_id"),
    )
    op.create_index("ix_messaging_legal_holds_school_active", "messaging_legal_holds", ["school_id", "released_at", "scope_type", "id"])
    op.create_index("ix_messaging_legal_holds_conversation_id", "messaging_legal_holds", ["conversation_id"])
    op.create_index("ix_messaging_legal_holds_message_id", "messaging_legal_holds", ["message_id"])
    op.create_index("ix_messaging_legal_holds_student_id", "messaging_legal_holds", ["student_id"])
    op.create_table(
        "messaging_legal_hold_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("hold_id", sa.BigInteger(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("actor_membership_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action IN ('placed', 'released')", name="ck_messaging_legal_hold_events_action"),
        sa.CheckConstraint("length(reason) BETWEEN 8 AND 4000", name="ck_messaging_legal_hold_events_reason"),
        sa.ForeignKeyConstraint(["hold_id"], ["messaging_legal_holds.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_messaging_legal_hold_events_event_id"),
    )
    op.create_index("ix_messaging_legal_hold_events_hold_id", "messaging_legal_hold_events", ["hold_id"])
    op.create_index("ix_messaging_legal_hold_events_school_time", "messaging_legal_hold_events", ["school_id", "occurred_at", "id"])

    op.create_table(
        "messaging_operations_jobs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("policy_id", sa.BigInteger(), nullable=True),
        sa.Column("export_id", sa.BigInteger(), nullable=True),
        sa.Column("requested_by_membership_id", sa.Integer(), nullable=False),
        sa.Column("operator_reason", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("progress", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_cursor", sa.String(length=200), nullable=True),
        sa.Column("lease_owner", sa.String(length=96), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("cancellation_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("last_error_detail", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("job_type IN ('retention_preview', 'retention_execute', 'archive_media', 'evidence_export')", name="ck_messaging_operations_jobs_type"),
        sa.CheckConstraint("state IN ('pending', 'leased', 'succeeded', 'failed', 'dead', 'cancelled')", name="ck_messaging_operations_jobs_state"),
        sa.CheckConstraint("length(operator_reason) BETWEEN 8 AND 2000", name="ck_messaging_operations_jobs_reason"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_messaging_operations_jobs_attempts"),
        sa.CheckConstraint("(state = 'leased' AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL) OR (state <> 'leased' AND lease_owner IS NULL AND lease_expires_at IS NULL)", name="ck_messaging_operations_jobs_lease"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["policy_id"], ["messaging_retention_policies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["export_id"], ["messaging_evidence_exports.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_messaging_operations_jobs_public_id"),
    )
    op.create_index("ix_messaging_operations_jobs_claim", "messaging_operations_jobs", ["state", "next_attempt_at", "lease_expires_at", "id"])
    op.create_index("ix_messaging_operations_jobs_school_type", "messaging_operations_jobs", ["school_id", "job_type", "created_at", "id"])

    op.create_table(
        "messaging_worker_heartbeats",
        sa.Column("worker_name", sa.String(length=48), nullable=False),
        sa.Column("instance_id", sa.String(length=96), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("processed_total", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("recovered_leases_total", sa.BigInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("worker_name"),
    )
    op.create_table(
        "messaging_operator_actions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("actor_membership_id", sa.Integer(), nullable=False),
        sa.Column("queue_kind", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("target_ref", sa.String(length=120), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("queue_kind IN ('notification', 'retention', 'archive', 'export')", name="ck_messaging_operator_actions_queue"),
        sa.CheckConstraint("action IN ('retry', 'cancel')", name="ck_messaging_operator_actions_action"),
        sa.CheckConstraint("length(reason) BETWEEN 8 AND 2000", name="ck_messaging_operator_actions_reason"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_messaging_operator_actions_event_id"),
    )
    op.create_index("ix_messaging_operator_actions_school_time", "messaging_operator_actions", ["school_id", "occurred_at", "id"])

    op.add_column("messages", sa.Column("retention_disposed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("messages", sa.Column("retention_policy_version", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("retention_content_sha256", sa.String(length=64), nullable=True))
    op.create_check_constraint(
        "ck_messages_retention_disposition",
        "messages",
        "(retention_disposed_at IS NULL AND retention_policy_version IS NULL AND retention_content_sha256 IS NULL) OR "
        "(retention_disposed_at IS NOT NULL AND retention_policy_version >= 1 "
        "AND length(retention_content_sha256) = 64 AND body IS NULL)",
    )
    _add_media_columns()

    op.add_column("messaging_evidence_exports", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("messaging_evidence_exports", sa.Column("verification_state", sa.String(length=24), nullable=True))
    op.add_column("messaging_evidence_exports", sa.Column("verification_detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("messaging_evidence_exports", sa.Column("custody_version", sa.Integer(), nullable=False, server_default="1"))
    op.drop_constraint("ck_messaging_evidence_exports_state", "messaging_evidence_exports", type_="check")
    op.create_check_constraint("ck_messaging_evidence_exports_state", "messaging_evidence_exports", "state IN ('requested', 'generating', 'ready', 'failed', 'expired', 'deleted', 'cancelled')")
    op.create_check_constraint("ck_messaging_evidence_exports_verification_state", "messaging_evidence_exports", "verification_state IS NULL OR verification_state IN ('verified', 'mismatch', 'missing')")
    op.create_check_constraint("ck_messaging_evidence_exports_custody_version", "messaging_evidence_exports", "custody_version >= 1")

    op.drop_constraint("ck_messaging_permission_grants_permission", "messaging_permission_grants", type_="check")
    op.create_check_constraint(
        "ck_messaging_permission_grants_permission",
        "messaging_permission_grants",
        "permission IN ('messaging.safeguarding_review', 'messaging.moderate', "
        "'messaging.export_evidence', 'messaging.export_internal_notes', "
        "'messaging.manage_safeguarding_permissions', 'messaging.manage_legal_holds')",
    )

    bind = op.get_bind()
    owners = bind.execute(
        sa.text(
            """
            SELECT school_id, id AS membership_id
            FROM (
              SELECT m.school_id, m.id, row_number() OVER (
                PARTITION BY m.school_id ORDER BY m.created_at, m.id
              ) AS position
              FROM memberships m
              JOIN users u ON u.id = m.user_id
              WHERE m.role = 'school_admin' AND m.status = 'active'
                AND m.revoked_at IS NULL AND u.status = 'active'
            ) ranked
            WHERE position = 1
            """
        )
    ).mappings().all()
    for owner in owners:
        bind.execute(
            sa.text(
                "INSERT INTO school_system_owners (school_id, membership_id, owner_version) "
                "VALUES (:school_id, :membership_id, 1)"
            ),
            dict(owner),
        )
        bind.execute(
            sa.text(
                "INSERT INTO school_system_owner_events "
                "(event_id, school_id, action, new_membership_id, actor_kind, reason, owner_version) "
                "VALUES (:event_id, :school_id, 'bootstrap', :membership_id, 'system', "
                "'Explicit ownership backfill from the existing nominated active administrator.', 1)"
            ),
            {**dict(owner), "event_id": uuid.uuid4()},
        )
        bind.execute(
            sa.text(
                "INSERT INTO messaging_retention_policies "
                "(public_id, school_id, policy_version, effective_at, rules, reason, "
                "acknowledged_school_policy, created_by_membership_id) "
                "VALUES (:public_id, :school_id, 1, now(), CAST(:rules AS jsonb), "
                "'Conservative Messaging v1 pilot defaults; school policy and legal review required.', "
                "true, :membership_id)"
            ),
            {
                **dict(owner),
                "public_id": uuid.uuid4(),
                "rules": json.dumps(DEFAULT_RETENTION_RULES, sort_keys=True),
            },
        )
        exists = bind.execute(
            sa.text(
                "SELECT 1 FROM messaging_permission_grants WHERE school_id=:school_id "
                "AND membership_id=:membership_id AND permission='messaging.manage_legal_holds' "
                "AND revoked_at IS NULL"
            ),
            dict(owner),
        ).first()
        if exists is None:
            bind.execute(
                sa.text(
                    "INSERT INTO messaging_permission_grants "
                    "(public_id, school_id, membership_id, permission, granted_by_membership_id, grant_reason) "
                    "VALUES (:public_id, :school_id, :membership_id, 'messaging.manage_legal_holds', "
                    ":membership_id, 'Initial System Owner legal-hold management bootstrap')"
                ),
                {**dict(owner), "public_id": uuid.uuid4()},
            )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION messaging_production_append_only_guard()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'messaging governance and custody evidence is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in (
        "school_system_owner_events",
        "messaging_legal_hold_events",
        "messaging_operator_actions",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION messaging_production_append_only_guard()"
        )
    _install_message_retention_guard()


def downgrade() -> None:
    for table in (
        "messaging_operator_actions",
        "messaging_legal_hold_events",
        "school_system_owner_events",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table}")
    op.execute("DROP FUNCTION IF EXISTS messaging_production_append_only_guard()")

    op.execute("DELETE FROM messaging_permission_grants WHERE permission = 'messaging.manage_legal_holds'")
    op.drop_constraint("ck_messaging_permission_grants_permission", "messaging_permission_grants", type_="check")
    op.create_check_constraint(
        "ck_messaging_permission_grants_permission",
        "messaging_permission_grants",
        "permission IN ('messaging.safeguarding_review', 'messaging.moderate', "
        "'messaging.export_evidence', 'messaging.export_internal_notes', "
        "'messaging.manage_safeguarding_permissions')",
    )
    op.drop_constraint("ck_messaging_evidence_exports_custody_version", "messaging_evidence_exports", type_="check")
    op.drop_constraint("ck_messaging_evidence_exports_verification_state", "messaging_evidence_exports", type_="check")
    op.drop_constraint("ck_messaging_evidence_exports_state", "messaging_evidence_exports", type_="check")
    op.create_check_constraint("ck_messaging_evidence_exports_state", "messaging_evidence_exports", "state IN ('requested', 'ready', 'failed', 'expired', 'deleted')")
    for column in ("custody_version", "verification_detail", "verification_state", "verified_at"):
        op.drop_column("messaging_evidence_exports", column)

    op.drop_index("ix_message_voice_media_archive_selection", table_name="message_voice_media")
    op.drop_constraint("ck_message_voice_media_retention_deleted", "message_voice_media", type_="check")
    op.drop_constraint("ck_message_voice_media_archive_shape", "message_voice_media", type_="check")
    op.drop_constraint("ck_message_voice_media_attachment_shape", "message_voice_media", type_="check")
    op.drop_constraint("ck_message_voice_media_state", "message_voice_media", type_="check")
    op.create_check_constraint("ck_message_voice_media_state", "message_voice_media", "state IN ('processing', 'ready', 'attached', 'failed', 'expired', 'deleted')")
    op.create_check_constraint("ck_message_voice_media_attachment_shape", "message_voice_media", "(state = 'attached' AND message_id IS NOT NULL AND attached_at IS NOT NULL) OR (state <> 'attached' AND message_id IS NULL AND attached_at IS NULL)")
    for column in ("retention_deleted_at", "hot_deleted_at", "archive_verified_at", "archived_at", "archive_sha256", "archive_storage_key"):
        op.drop_column("message_voice_media", column)

    op.drop_index("ix_message_media_archive_selection", table_name="message_media")
    op.drop_constraint("ck_message_media_retention_deleted", "message_media", type_="check")
    op.drop_constraint("ck_message_media_archive_shape", "message_media", type_="check")
    op.drop_constraint("ck_message_media_attachment_shape", "message_media", type_="check")
    op.drop_constraint("ck_message_media_state", "message_media", type_="check")
    op.create_check_constraint("ck_message_media_state", "message_media", "state IN ('processing', 'ready', 'attached', 'failed', 'expired', 'deleted')")
    op.create_check_constraint("ck_message_media_attachment_shape", "message_media", "(state = 'attached' AND message_id IS NOT NULL AND attached_at IS NOT NULL) OR (state <> 'attached' AND message_id IS NULL AND attached_at IS NULL)")
    for column in ("retention_deleted_at", "hot_deleted_at", "archive_verified_at", "archived_at", "archive_thumbnail_sha256", "archive_full_sha256", "archive_thumbnail_storage_key", "archive_full_storage_key"):
        op.drop_column("message_media", column)

    op.drop_constraint("ck_messages_retention_disposition", "messages", type_="check")
    for column in ("retention_content_sha256", "retention_policy_version", "retention_disposed_at"):
        op.drop_column("messages", column)

    op.drop_table("messaging_operator_actions")
    op.drop_table("messaging_worker_heartbeats")
    op.drop_table("messaging_operations_jobs")
    op.drop_table("messaging_legal_hold_events")
    op.drop_table("messaging_legal_holds")
    op.drop_table("messaging_retention_policies")
    op.drop_table("school_system_owner_events")
    op.drop_table("school_system_owners")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION messaging_message_immutable_guard() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'messages are append-only';
          END IF;
          IF NEW.public_id IS DISTINCT FROM OLD.public_id
             OR NEW.school_id IS DISTINCT FROM OLD.school_id
             OR NEW.conversation_id IS DISTINCT FROM OLD.conversation_id
             OR NEW.sequence IS DISTINCT FROM OLD.sequence
             OR NEW.sender_participant_id IS DISTINCT FROM OLD.sender_participant_id
             OR NEW.sender_display_name_snapshot IS DISTINCT FROM OLD.sender_display_name_snapshot
             OR NEW.client_message_id IS DISTINCT FROM OLD.client_message_id
             OR NEW.message_type IS DISTINCT FROM OLD.message_type
             OR NEW.body IS DISTINCT FROM OLD.body
             OR NEW.urgent IS DISTINCT FROM OLD.urgent
             OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
            RAISE EXCEPTION 'message attribution and content are immutable';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

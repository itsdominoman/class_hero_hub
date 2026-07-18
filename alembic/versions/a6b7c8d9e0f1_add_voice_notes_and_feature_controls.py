"""add protected voice notes and compliance feature controls

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "a6b7c8d9e0f1"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def _install_message_guard(include_message_type: bool) -> None:
    message_type_guard = (
        "OR NEW.message_type IS DISTINCT FROM OLD.message_type"
        if include_message_type
        else ""
    )
    op.execute(
        f"""
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
             {message_type_guard}
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
    op.add_column(
        "messages",
        sa.Column("message_type", sa.String(length=24), nullable=False, server_default="standard"),
    )
    op.create_check_constraint(
        "ck_messages_type",
        "messages",
        "message_type IN ('standard', 'voice_note')",
    )

    op.create_table(
        "school_feature_controls",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("feature", sa.String(length=40), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("control_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("disclosure_version", sa.String(length=40), nullable=False),
        sa.Column("updated_by_membership_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("feature IN ('voice_notes')", name="ck_school_feature_controls_feature"),
        sa.CheckConstraint("control_version >= 1", name="ck_school_feature_controls_version"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "feature", name="uq_school_feature_controls_school_feature"),
    )
    op.create_index("ix_school_feature_controls_school_id", "school_feature_controls", ["school_id"])

    op.create_table(
        "school_feature_control_audit_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("feature", sa.String(length=40), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("control_version", sa.Integer(), nullable=False),
        sa.Column("disclosure_version", sa.String(length=40), nullable=False),
        sa.Column("acknowledging_user_id", sa.Integer(), nullable=False),
        sa.Column("acknowledging_membership_id", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("feature IN ('voice_notes')", name="ck_school_feature_audit_feature"),
        sa.CheckConstraint("control_version >= 1", name="ck_school_feature_audit_version"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["acknowledging_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["acknowledging_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_school_feature_control_audit_event_id"),
    )
    op.create_index("ix_school_feature_control_audit_events_school_id", "school_feature_control_audit_events", ["school_id"])
    op.create_index(
        "ix_school_feature_audit_school_feature_time",
        "school_feature_control_audit_events",
        ["school_id", "feature", "occurred_at", "id"],
    )

    op.create_table(
        "message_voice_media",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("client_upload_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("uploaded_by_participant_id", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="processing"),
        sa.Column("storage_backend", sa.String(length=16), nullable=False, server_default="local"),
        sa.Column("storage_key", sa.String(length=500), nullable=True),
        sa.Column("content_type", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("codec", sa.String(length=24), nullable=True),
        sa.Column("container", sa.String(length=24), nullable=True),
        sa.Column("source_checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("metadata_stripped", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("transcription_state", sa.String(length=24), nullable=False, server_default="not_requested"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("attached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('processing', 'ready', 'attached', 'failed', 'expired', 'deleted')",
            name="ck_message_voice_media_state",
        ),
        sa.CheckConstraint("storage_backend = 'local'", name="ck_message_voice_media_storage_backend"),
        sa.CheckConstraint(
            "(state IN ('ready', 'attached') AND storage_key IS NOT NULL "
            "AND content_type = 'audio/mp4' AND size_bytes > 0 "
            "AND duration_ms BETWEEN 600 AND 180000 AND codec = 'aac' "
            "AND container = 'mp4' AND checksum_sha256 IS NOT NULL "
            "AND metadata_stripped = true) OR state NOT IN ('ready', 'attached')",
            name="ck_message_voice_media_ready_shape",
        ),
        sa.CheckConstraint(
            "(state = 'attached' AND message_id IS NOT NULL AND attached_at IS NOT NULL) "
            "OR (state <> 'attached' AND message_id IS NULL AND attached_at IS NULL)",
            name="ck_message_voice_media_attachment_shape",
        ),
        sa.CheckConstraint(
            "(state IN ('expired', 'deleted') AND deleted_at IS NOT NULL) "
            "OR (state NOT IN ('expired', 'deleted') AND deleted_at IS NULL)",
            name="ck_message_voice_media_deleted_shape",
        ),
        sa.CheckConstraint("transcription_state IN ('not_requested')", name="ck_message_voice_media_transcription_state"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["uploaded_by_participant_id"], ["conversation_participants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_message_voice_media_public_id"),
        sa.UniqueConstraint("message_id", name="uq_message_voice_media_message_id"),
        sa.UniqueConstraint(
            "conversation_id",
            "uploaded_by_participant_id",
            "client_upload_id",
            name="uq_message_voice_media_participant_upload",
        ),
    )
    for name, columns in (
        ("ix_message_voice_media_school_id", ["school_id"]),
        ("ix_message_voice_media_conversation_id", ["conversation_id"]),
        ("ix_message_voice_media_message_id", ["message_id"]),
        ("ix_message_voice_media_uploaded_by_participant_id", ["uploaded_by_participant_id"]),
        ("ix_message_voice_media_conversation_message", ["conversation_id", "message_id"]),
        ("ix_message_voice_media_state_expiry", ["state", "expires_at", "id"]),
    ):
        op.create_index(name, "message_voice_media", columns)

    _install_message_guard(True)
    op.execute(
        """
        CREATE TRIGGER trg_school_feature_control_audit_events_append_only
        BEFORE UPDATE OR DELETE ON school_feature_control_audit_events
        FOR EACH ROW EXECUTE FUNCTION messaging_evidence_append_only_guard()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_school_feature_control_audit_events_append_only "
        "ON school_feature_control_audit_events"
    )
    _install_message_guard(False)
    op.drop_table("message_voice_media")
    op.drop_table("school_feature_control_audit_events")
    op.drop_table("school_feature_controls")
    op.drop_constraint("ck_messages_type", "messages", type_="check")
    op.drop_column("messages", "message_type")

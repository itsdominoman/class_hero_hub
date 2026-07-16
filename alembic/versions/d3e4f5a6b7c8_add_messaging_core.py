"""Add Messaging v1 core conversations, access history, and audit.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-07-17 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("branch_campus_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("primary_staff_membership_id", sa.Integer(), nullable=True),
        sa.Column("staff_membership_low_id", sa.Integer(), nullable=True),
        sa.Column("staff_membership_high_id", sa.Integer(), nullable=True),
        sa.Column("internal_guardian_user_id", sa.Integer(), nullable=True),
        sa.Column("external_guardian_participant_id", sa.Integer(), nullable=True),
        sa.Column("context_class_section_id", sa.Integer(), nullable=True),
        sa.Column("context_subject_group_id", sa.Integer(), nullable=True),
        sa.Column("context_label", sa.String(length=200), nullable=True),
        sa.Column("context_label_ar", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("last_message_sequence", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_participant_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_reason", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "(kind = 'student_staff' AND student_id IS NOT NULL AND primary_staff_membership_id IS NOT NULL "
            "AND staff_membership_low_id IS NULL AND staff_membership_high_id IS NULL "
            "AND internal_guardian_user_id IS NULL AND external_guardian_participant_id IS NULL) OR "
            "(kind = 'staff_direct' AND student_id IS NULL AND primary_staff_membership_id IS NULL "
            "AND staff_membership_low_id IS NOT NULL AND staff_membership_high_id IS NOT NULL "
            "AND staff_membership_low_id < staff_membership_high_id "
            "AND internal_guardian_user_id IS NULL AND external_guardian_participant_id IS NULL) OR "
            "(kind = 'guardian_direct' AND primary_staff_membership_id IS NOT NULL "
            "AND staff_membership_low_id IS NULL AND staff_membership_high_id IS NULL "
            "AND ((internal_guardian_user_id IS NOT NULL AND external_guardian_participant_id IS NULL) "
            "OR (internal_guardian_user_id IS NULL AND external_guardian_participant_id IS NOT NULL)))",
            name="ck_conversations_kind_shape",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'closed_assignment_ended', 'closed_student_archived', "
            "'closed_restricted', 'archived')",
            name="ck_conversations_status",
        ),
        sa.CheckConstraint("last_message_sequence >= 0", name="ck_conversations_last_sequence"),
        sa.CheckConstraint(
            "context_class_section_id IS NULL OR context_subject_group_id IS NULL",
            name="ck_conversations_single_context",
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["branch_campus_id"], ["branch_campuses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["primary_staff_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["staff_membership_low_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["staff_membership_high_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["internal_guardian_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["external_guardian_participant_id"],
            ["fhh_messaging_identities.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["context_class_section_id"], ["class_sections.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["context_subject_group_id"], ["subject_groups.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_conversations_public_id"),
    )
    op.create_index("ix_conversations_school_id", "conversations", ["school_id"])
    op.create_index(
        "uq_conversations_active_student_staff",
        "conversations",
        ["school_id", "student_id", "primary_staff_membership_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'student_staff' AND status = 'active'"),
    )
    op.create_index(
        "uq_conversations_active_staff_direct",
        "conversations",
        ["school_id", "staff_membership_low_id", "staff_membership_high_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'staff_direct' AND status = 'active'"),
    )
    op.create_index(
        "uq_conversations_active_guardian_direct_internal_student",
        "conversations",
        ["school_id", "primary_staff_membership_id", "internal_guardian_user_id", "student_id"],
        unique=True,
        postgresql_where=sa.text(
            "kind = 'guardian_direct' AND status = 'active' "
            "AND internal_guardian_user_id IS NOT NULL AND student_id IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_conversations_active_guardian_direct_internal_general",
        "conversations",
        ["school_id", "primary_staff_membership_id", "internal_guardian_user_id"],
        unique=True,
        postgresql_where=sa.text(
            "kind = 'guardian_direct' AND status = 'active' "
            "AND internal_guardian_user_id IS NOT NULL AND student_id IS NULL"
        ),
    )
    op.create_index(
        "uq_conversations_active_guardian_direct_external_student",
        "conversations",
        ["school_id", "primary_staff_membership_id", "external_guardian_participant_id", "student_id"],
        unique=True,
        postgresql_where=sa.text(
            "kind = 'guardian_direct' AND status = 'active' "
            "AND external_guardian_participant_id IS NOT NULL AND student_id IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_conversations_active_guardian_direct_external_general",
        "conversations",
        ["school_id", "primary_staff_membership_id", "external_guardian_participant_id"],
        unique=True,
        postgresql_where=sa.text(
            "kind = 'guardian_direct' AND status = 'active' "
            "AND external_guardian_participant_id IS NOT NULL AND student_id IS NULL"
        ),
    )
    op.create_index(
        "ix_conversations_school_status_activity",
        "conversations",
        ["school_id", "status", sa.text("last_message_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_conversations_school_student_status",
        "conversations",
        ["school_id", "student_id", "status"],
    )
    op.create_index(
        "ix_conversations_school_primary_staff_activity",
        "conversations",
        [
            "school_id",
            "primary_staff_membership_id",
            "status",
            sa.text("last_message_at DESC"),
        ],
    )

    op.create_table(
        "conversation_participants",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("participant_kind", sa.String(length=24), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("membership_id", sa.Integer(), nullable=True),
        sa.Column("external_participant_id", sa.Integer(), nullable=True),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("display_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_delivered_sequence", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_read_sequence", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(participant_kind = 'staff' AND user_id IS NOT NULL AND membership_id IS NOT NULL "
            "AND external_participant_id IS NULL AND side = 'staff') OR "
            "(participant_kind = 'chh_guardian' AND user_id IS NOT NULL AND membership_id IS NULL "
            "AND external_participant_id IS NULL AND side = 'guardian') OR "
            "(participant_kind = 'fhh_parent' AND user_id IS NULL AND membership_id IS NULL "
            "AND external_participant_id IS NOT NULL AND side = 'guardian')",
            name="ck_conversation_participants_actor_shape",
        ),
        sa.CheckConstraint(
            "last_delivered_sequence >= 0", name="ck_conversation_participants_delivered"
        ),
        sa.CheckConstraint("last_read_sequence >= 0", name="ck_conversation_participants_read"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["external_participant_id"], ["fhh_messaging_identities.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_participants_conversation_id",
        "conversation_participants",
        ["conversation_id"],
    )
    op.create_index(
        "uq_conversation_participants_active_staff",
        "conversation_participants",
        ["conversation_id", "membership_id"],
        unique=True,
        postgresql_where=sa.text("participant_kind = 'staff' AND left_at IS NULL"),
    )
    op.create_index(
        "uq_conversation_participants_active_chh_guardian",
        "conversation_participants",
        ["conversation_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("participant_kind = 'chh_guardian' AND left_at IS NULL"),
    )
    op.create_index(
        "uq_conversation_participants_active_fhh_parent",
        "conversation_participants",
        ["conversation_id", "external_participant_id"],
        unique=True,
        postgresql_where=sa.text("participant_kind = 'fhh_parent' AND left_at IS NULL"),
    )
    op.create_index(
        "ix_conversation_participants_conversation_side",
        "conversation_participants",
        ["conversation_id", "side", "left_at"],
    )
    op.create_foreign_key(
        "fk_conversations_created_by_participant",
        "conversations",
        "conversation_participants",
        ["created_by_participant_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "conversation_access_grants",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("participant_id", sa.BigInteger(), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("staff_assignment_id", sa.Integer(), nullable=True),
        sa.Column("membership_id", sa.Integer(), nullable=True),
        sa.Column("guardian_link_id", sa.Integer(), nullable=True),
        sa.Column("fhh_link_id", sa.Integer(), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("visible_from_sequence", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("visible_through_sequence", sa.BigInteger(), nullable=True),
        sa.Column("grant_reason", sa.String(length=64), nullable=False),
        sa.Column("granted_by_membership_id", sa.Integer(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_membership_id", sa.Integer(), nullable=True),
        sa.Column("revoke_reason", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "(source_type = 'staff_assignment' AND staff_assignment_id IS NOT NULL "
            "AND membership_id IS NULL AND guardian_link_id IS NULL AND fhh_link_id IS NULL) OR "
            "(source_type = 'school_admin_membership' AND staff_assignment_id IS NULL "
            "AND membership_id IS NOT NULL AND guardian_link_id IS NULL AND fhh_link_id IS NULL) OR "
            "(source_type = 'guardian_link' AND staff_assignment_id IS NULL "
            "AND membership_id IS NULL AND guardian_link_id IS NOT NULL AND fhh_link_id IS NULL) OR "
            "(source_type = 'fhh_link' AND staff_assignment_id IS NULL "
            "AND membership_id IS NULL AND guardian_link_id IS NULL AND fhh_link_id IS NOT NULL) OR "
            "(source_type = 'manual_history_grant' AND staff_assignment_id IS NULL "
            "AND membership_id IS NULL AND guardian_link_id IS NULL AND fhh_link_id IS NULL "
            "AND granted_by_membership_id IS NOT NULL)",
            name="ck_conversation_access_grants_source_shape",
        ),
        sa.CheckConstraint(
            "visible_from_sequence >= 1", name="ck_conversation_access_grants_visible_from"
        ),
        sa.CheckConstraint(
            "visible_through_sequence IS NULL OR visible_through_sequence >= visible_from_sequence",
            name="ck_conversation_access_grants_visible_range",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_conversation_access_grants_valid_range",
        ),
        sa.CheckConstraint(
            "(revoked_at IS NULL AND revoke_reason IS NULL AND revoked_by_membership_id IS NULL) OR "
            "(revoked_at IS NOT NULL AND revoke_reason IS NOT NULL)",
            name="ck_conversation_access_grants_revoke_shape",
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["participant_id"], ["conversation_participants.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["staff_assignment_id"], ["staff_assignments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["guardian_link_id"], ["guardian_links.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["fhh_link_id"], ["fhh_links.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["granted_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_access_grants_conversation_id",
        "conversation_access_grants",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_access_grants_participant_id",
        "conversation_access_grants",
        ["participant_id"],
    )
    op.create_index(
        "ix_conversation_access_grants_participant_validity",
        "conversation_access_grants",
        ["conversation_id", "participant_id", "valid_from", "valid_to"],
    )
    for name, column in (
        ("staff_assignment", "staff_assignment_id"),
        ("membership", "membership_id"),
        ("guardian_link", "guardian_link_id"),
        ("fhh_link", "fhh_link_id"),
    ):
        op.create_index(
            f"ix_conversation_access_grants_{name}",
            "conversation_access_grants",
            [column, "revoked_at"],
        )

    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("sender_participant_id", sa.BigInteger(), nullable=False),
        sa.Column("sender_display_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("client_message_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("urgent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tombstoned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tombstoned_by_membership_id", sa.Integer(), nullable=True),
        sa.Column("tombstone_reason", sa.String(length=160), nullable=True),
        sa.CheckConstraint("sequence >= 1", name="ck_messages_sequence"),
        sa.CheckConstraint(
            "body IS NULL OR length(body) BETWEEN 1 AND 10000", name="ck_messages_body_length"
        ),
        sa.CheckConstraint("state IN ('active', 'tombstoned')", name="ck_messages_state"),
        sa.CheckConstraint(
            "(state = 'active' AND tombstoned_at IS NULL AND tombstoned_by_membership_id IS NULL "
            "AND tombstone_reason IS NULL) OR "
            "(state = 'tombstoned' AND tombstoned_at IS NOT NULL AND tombstone_reason IS NOT NULL)",
            name="ck_messages_tombstone_shape",
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["sender_participant_id"], ["conversation_participants.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["tombstoned_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_messages_public_id"),
        sa.UniqueConstraint(
            "conversation_id", "sequence", name="uq_messages_conversation_sequence"
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "sender_participant_id",
            "client_message_id",
            name="uq_messages_sender_client_id",
        ),
    )
    op.create_index("ix_messages_school_id", "messages", ["school_id"])
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index(
        "ix_messages_sender_participant_id", "messages", ["sender_participant_id"]
    )
    op.create_index(
        "ix_messages_conversation_page", "messages", ["conversation_id", "sequence"]
    )
    op.create_index(
        "ix_messages_school_created", "messages", ["school_id", "created_at", "id"]
    )

    op.create_table(
        "message_receipt_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("participant_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("through_sequence", sa.BigInteger(), nullable=False),
        sa.Column("client_ack_id", sa.Uuid(), nullable=False),
        sa.Column("device_session_ref", sa.String(length=96), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "event_type IN ('delivered', 'read')", name="ck_message_receipt_events_type"
        ),
        sa.CheckConstraint(
            "through_sequence >= 0", name="ck_message_receipt_events_sequence"
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["participant_id"], ["conversation_participants.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "participant_id",
            "event_type",
            "client_ack_id",
            name="uq_message_receipt_events_client_ack",
        ),
    )
    op.create_index(
        "ix_message_receipt_events_conversation_id",
        "message_receipt_events",
        ["conversation_id"],
    )
    op.create_index(
        "ix_message_receipt_events_participant_id",
        "message_receipt_events",
        ["participant_id"],
    )
    op.create_index(
        "ix_message_receipt_events_conversation_recorded",
        "message_receipt_events",
        ["conversation_id", "recorded_at", "id"],
    )

    op.create_table(
        "messaging_audit_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("actor_kind", sa.String(length=24), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_membership_id", sa.Integer(), nullable=True),
        sa.Column("actor_external_participant_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=True),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("participant_id", sa.BigInteger(), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("request_correlation_id", sa.String(length=96), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(actor_kind = 'system' AND actor_user_id IS NULL AND actor_membership_id IS NULL "
            "AND actor_external_participant_id IS NULL) OR "
            "(actor_kind IN ('staff', 'safeguarding_admin') AND actor_user_id IS NOT NULL "
            "AND actor_membership_id IS NOT NULL AND actor_external_participant_id IS NULL) OR "
            "(actor_kind = 'chh_guardian' AND actor_user_id IS NOT NULL "
            "AND actor_membership_id IS NULL AND actor_external_participant_id IS NULL) OR "
            "(actor_kind = 'fhh_parent' AND actor_user_id IS NULL "
            "AND actor_membership_id IS NULL AND actor_external_participant_id IS NOT NULL)",
            name="ck_messaging_audit_events_actor_shape",
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["actor_membership_id"], ["memberships.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["actor_external_participant_id"],
            ["fhh_messaging_identities.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["participant_id"], ["conversation_participants.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_messaging_audit_events_event_id"),
    )
    op.create_index("ix_messaging_audit_events_school_id", "messaging_audit_events", ["school_id"])
    op.create_index(
        "ix_messaging_audit_events_conversation_id",
        "messaging_audit_events",
        ["conversation_id"],
    )
    op.create_index(
        "ix_messaging_audit_events_message_id", "messaging_audit_events", ["message_id"]
    )
    op.create_index(
        "ix_messaging_audit_events_school_occurred",
        "messaging_audit_events",
        ["school_id", "occurred_at", "id"],
    )
    op.create_index(
        "ix_messaging_audit_events_type_occurred",
        "messaging_audit_events",
        ["event_type", "occurred_at", "id"],
    )

    op.execute(
        """
        CREATE FUNCTION messaging_message_immutable_guard() RETURNS trigger AS $$
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
    op.execute(
        """
        CREATE TRIGGER trg_messages_immutable
        BEFORE UPDATE OR DELETE ON messages
        FOR EACH ROW EXECUTE FUNCTION messaging_message_immutable_guard()
        """
    )
    op.execute(
        """
        CREATE FUNCTION messaging_evidence_append_only_guard() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'messaging evidence rows are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in ("message_receipt_events", "messaging_audit_events"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_append_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION messaging_evidence_append_only_guard()
            """
        )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_messaging_audit_events_append_only ON messaging_audit_events"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_message_receipt_events_append_only ON message_receipt_events"
    )
    op.execute("DROP FUNCTION IF EXISTS messaging_evidence_append_only_guard()")
    op.execute("DROP TRIGGER IF EXISTS trg_messages_immutable ON messages")
    op.execute("DROP FUNCTION IF EXISTS messaging_message_immutable_guard()")
    op.drop_table("messaging_audit_events")
    op.drop_table("message_receipt_events")
    op.drop_table("messages")
    op.drop_table("conversation_access_grants")
    op.drop_constraint(
        "fk_conversations_created_by_participant", "conversations", type_="foreignkey"
    )
    op.drop_table("conversation_participants")
    op.drop_table("conversations")

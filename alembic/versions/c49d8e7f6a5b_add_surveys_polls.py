"""Add school surveys, responses, targeting and notification support.

Revision ID: c49d8e7f6a5b
Revises: b38c4d5e6f70
Create Date: 2026-07-21
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op


revision = "c49d8e7f6a5b"
down_revision = "b38c4d5e6f70"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fhh_links", sa.Column("fhh_household_ref", sa.String(64), nullable=True))
    op.create_index("ix_fhh_links_fhh_household_ref", "fhh_links", ["fhh_household_ref"])
    op.drop_constraint("ck_messaging_permission_grants_permission", "messaging_permission_grants", type_="check")
    op.create_check_constraint(
        "ck_messaging_permission_grants_permission", "messaging_permission_grants",
        "permission IN ('messaging.safeguarding_review', 'messaging.moderate', "
        "'messaging.export_evidence', 'messaging.export_internal_notes', "
        "'messaging.manage_safeguarding_permissions', 'messaging.manage_legal_holds', 'surveys.manage')",
    )
    bind = op.get_bind()
    owners = bind.execute(
        sa.text("SELECT school_id, membership_id FROM school_system_owners")
    ).mappings()
    for owner in owners:
        exists = bind.execute(
            sa.text(
                "SELECT 1 FROM messaging_permission_grants "
                "WHERE school_id=:school_id AND membership_id=:membership_id "
                "AND permission='surveys.manage' AND revoked_at IS NULL"
            ),
            dict(owner),
        ).first()
        if exists is None:
            bind.execute(
                sa.text(
                    "INSERT INTO messaging_permission_grants "
                    "(public_id, school_id, membership_id, permission, "
                    "granted_by_membership_id, grant_reason) "
                    "VALUES (:public_id, :school_id, :membership_id, 'surveys.manage', "
                    ":membership_id, 'Initial System Owner surveys management bootstrap')"
                ),
                {**dict(owner), "public_id": uuid.uuid4()},
            )
    op.drop_constraint("ck_notification_outbox_category", "notification_outbox", type_="check")
    op.drop_constraint("ck_notification_outbox_route_type", "notification_outbox", type_="check")
    op.create_check_constraint(
        "ck_notification_outbox_category", "notification_outbox",
        "event_category IN ('chat', 'homework', 'notice', 'points', 'calendar', 'update', 'survey')",
    )
    op.create_check_constraint(
        "ck_notification_outbox_route_type", "notification_outbox",
        "route_type IN ('school_chat', 'homework', 'notice', 'points', 'calendar', 'update', 'survey')",
    )
    op.create_table(
        "surveys",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("introduction", sa.String(1000), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("audience_type", sa.String(32), nullable=False),
        sa.Column("anonymous", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("response_mode", sa.String(16), nullable=False, server_default="guardian"),
        sa.Column("opens_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reminder_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parent_results_visible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("dashboard_card_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notices_feed_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_membership_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("audience_type IN ('whole_school', 'branch', 'grade', 'class', 'selected_families')", name="ck_surveys_audience"),
        sa.CheckConstraint("response_mode IN ('guardian', 'household')", name="ck_surveys_response_mode"),
        sa.CheckConstraint("status IN ('draft', 'scheduled', 'open', 'closed', 'archived')", name="ck_surveys_status"),
        sa.CheckConstraint("closes_at > opens_at", name="ck_surveys_window"),
        sa.CheckConstraint("reminder_at IS NULL OR (reminder_at > opens_at AND reminder_at < closes_at)", name="ck_surveys_reminder_window"),
        sa.CheckConstraint("version >= 1", name="ck_surveys_version"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_surveys_school_id", "surveys", ["school_id"])
    op.create_index("ix_surveys_school_status_window", "surveys", ["school_id", "status", "opens_at", "closes_at"])
    op.create_table(
        "survey_targets",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("survey_id", sa.BigInteger(), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.CheckConstraint("target_type IN ('branch', 'grade', 'class', 'student')", name="ck_survey_targets_type"),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("survey_id", "target_type", "target_id", name="uq_survey_targets_scope"),
    )
    op.create_index("ix_survey_targets_survey_id", "survey_targets", ["survey_id"])
    op.create_table(
        "survey_questions",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("survey_id", sa.BigInteger(), nullable=False),
        sa.Column("question_type", sa.String(24), nullable=False),
        sa.Column("prompt", sa.String(1000), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scale_min", sa.Integer(), nullable=True),
        sa.Column("scale_max", sa.Integer(), nullable=True),
        sa.CheckConstraint("question_type IN ('single_choice', 'multiple_choice', 'yes_no', 'rating', 'short_text', 'long_text')", name="ck_survey_questions_type"),
        sa.CheckConstraint("(question_type = 'rating' AND scale_min IS NOT NULL AND scale_max IS NOT NULL AND scale_min < scale_max) OR (question_type <> 'rating' AND scale_min IS NULL AND scale_max IS NULL)", name="ck_survey_questions_scale"),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("survey_id", "sort_order", name="uq_survey_questions_order"),
    )
    op.create_index("ix_survey_questions_survey_id", "survey_questions", ["survey_id"])
    op.create_table(
        "survey_options",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["question_id"], ["survey_questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("question_id", "sort_order", name="uq_survey_options_order"),
    )
    op.create_index("ix_survey_options_question_id", "survey_options", ["question_id"])
    op.create_table(
        "survey_responses",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("survey_id", sa.BigInteger(), nullable=False),
        sa.Column("response_key_hash", sa.String(64), nullable=False),
        sa.Column("respondent_label", sa.String(240), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("survey_id", "response_key_hash", name="uq_survey_responses_unit"),
    )
    op.create_index("ix_survey_responses_survey_id", "survey_responses", ["survey_id"])
    op.create_index("ix_survey_responses_survey_time", "survey_responses", ["survey_id", "submitted_at", "id"])
    op.create_table(
        "survey_answers",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("response_id", sa.BigInteger(), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answer_number", sa.Integer(), nullable=True),
        sa.Column("answer_boolean", sa.Boolean(), nullable=True),
        sa.Column("selected_option_ids", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["response_id"], ["survey_responses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["survey_questions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("response_id", "question_id", name="uq_survey_answers_response_question"),
    )
    op.create_index("ix_survey_answers_response_id", "survey_answers", ["response_id"])
    op.create_index("ix_survey_answers_question_id", "survey_answers", ["question_id"])
    op.create_table(
        "survey_events",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("survey_id", sa.BigInteger(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(24), nullable=False),
        sa.Column("actor_membership_id", sa.Integer(), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action IN ('published', 'closed', 'reopened', 'reminder_sent', 'exported', 'archived')", name="ck_survey_events_action"),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_survey_events_survey_id", "survey_events", ["survey_id"])
    op.create_index("ix_survey_events_school_id", "survey_events", ["school_id"])
    op.create_index("ix_survey_events_school_time", "survey_events", ["school_id", "occurred_at", "id"])


def downgrade() -> None:
    for table in ("survey_events", "survey_answers", "survey_responses", "survey_options", "survey_questions", "survey_targets", "surveys"):
        op.drop_table(table)
    op.drop_constraint("ck_notification_outbox_route_type", "notification_outbox", type_="check")
    op.drop_constraint("ck_notification_outbox_category", "notification_outbox", type_="check")
    op.create_check_constraint("ck_notification_outbox_category", "notification_outbox", "event_category IN ('chat', 'homework', 'notice', 'points', 'calendar', 'update')")
    op.create_check_constraint("ck_notification_outbox_route_type", "notification_outbox", "route_type IN ('school_chat', 'homework', 'notice', 'points', 'calendar', 'update')")
    op.drop_constraint("ck_messaging_permission_grants_permission", "messaging_permission_grants", type_="check")
    op.execute("DELETE FROM messaging_permission_grants WHERE permission = 'surveys.manage'")
    op.create_check_constraint(
        "ck_messaging_permission_grants_permission", "messaging_permission_grants",
        "permission IN ('messaging.safeguarding_review', 'messaging.moderate', 'messaging.export_evidence', "
        "'messaging.export_internal_notes', 'messaging.manage_safeguarding_permissions', 'messaging.manage_legal_holds')",
    )
    op.drop_index("ix_fhh_links_fhh_household_ref", table_name="fhh_links")
    op.drop_column("fhh_links", "fhh_household_ref")

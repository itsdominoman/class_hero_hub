"""Add behaviour award idempotency and reversal integrity.

Revision ID: d6e7f8a9b0c1
Revises: c49d8e7f6a5b
Create Date: 2026-07-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "d6e7f8a9b0c1"
down_revision = "c49d8e7f6a5b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    partial_reversals = bind.execute(sa.text(
        """
        SELECT count(*)
        FROM behaviour_events
        WHERE NOT (
            (reversed_at IS NULL AND reversed_by_user_id IS NULL AND reversal_reason IS NULL)
            OR
            (reversed_at IS NOT NULL AND reversed_by_user_id IS NOT NULL
             AND reversal_reason IS NOT NULL AND length(trim(reversal_reason)) > 0)
        )
        """
    )).scalar_one()
    if partial_reversals:
        raise RuntimeError(
            f"Cannot add behaviour reversal integrity constraint: {partial_reversals} partial reversal row(s)"
        )

    op.create_table(
        "behaviour_award_requests",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "school_id",
            "actor_user_id",
            "idempotency_key",
            name="uq_behaviour_award_requests_scope",
        ),
    )
    op.create_index(
        "ix_behaviour_award_requests_school_actor_created",
        "behaviour_award_requests",
        ["school_id", "actor_user_id", "created_at"],
    )
    op.add_column("behaviour_events", sa.Column("award_request_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_behaviour_events_award_request_id",
        "behaviour_events",
        "behaviour_award_requests",
        ["award_request_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_behaviour_events_award_request_id",
        "behaviour_events",
        ["award_request_id"],
    )
    op.create_unique_constraint(
        "uq_behaviour_events_award_request_student",
        "behaviour_events",
        ["award_request_id", "student_id"],
    )
    op.create_check_constraint(
        "ck_behaviour_events_reversal_complete",
        "behaviour_events",
        "(reversed_at IS NULL AND reversed_by_user_id IS NULL AND reversal_reason IS NULL) OR "
        "(reversed_at IS NOT NULL AND reversed_by_user_id IS NOT NULL "
        "AND reversal_reason IS NOT NULL AND length(trim(reversal_reason)) > 0)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_behaviour_events_reversal_complete", "behaviour_events", type_="check")
    op.drop_constraint("uq_behaviour_events_award_request_student", "behaviour_events", type_="unique")
    op.drop_index("ix_behaviour_events_award_request_id", table_name="behaviour_events")
    op.drop_constraint("fk_behaviour_events_award_request_id", "behaviour_events", type_="foreignkey")
    op.drop_column("behaviour_events", "award_request_id")
    op.drop_index(
        "ix_behaviour_award_requests_school_actor_created",
        table_name="behaviour_award_requests",
    )
    op.drop_table("behaviour_award_requests")

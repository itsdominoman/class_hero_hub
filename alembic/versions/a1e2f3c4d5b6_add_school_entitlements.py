"""add canonical school entitlements

Revision ID: a1e2f3c4d5b6
Revises: a0b1c2d3e4f5
Create Date: 2026-08-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


revision = "a1e2f3c4d5b6"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


CAPABILITIES = (
    "homework_diary",
    "notices_calendar",
    "behaviour_points",
    "positive_recognition",
    "surveys_polls",
    "school_chats",
    "chat_photos",
    "voice_notes",
    "family_connection",
    "school_family_updates",
    "update_photos",
    "reports_insights",
    "safeguarding",
    "student_staff_import_export",
)
CAPABILITY_SQL = ", ".join(f"'{capability}'" for capability in CAPABILITIES)


def upgrade() -> None:
    op.add_column(
        "platform_admins",
        sa.Column(
            "manage_school_entitlements",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_table(
        "school_entitlements",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("capability", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column("entitlement_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            f"capability IN ({CAPABILITY_SQL})",
            name="ck_school_entitlements_capability",
        ),
        sa.CheckConstraint(
            "source IN ('pilot', 'trial', 'paid', 'complimentary')",
            name="ck_school_entitlements_source",
        ),
        sa.CheckConstraint("entitlement_version >= 1", name="ck_school_entitlements_version"),
        sa.CheckConstraint(
            "expires_on IS NULL OR expires_on >= effective_from",
            name="ck_school_entitlements_dates",
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "capability", name="uq_school_entitlements_school_capability"),
    )
    op.create_index("ix_school_entitlements_school_id", "school_entitlements", ["school_id"])
    op.create_index(
        "ix_school_entitlements_school_enabled",
        "school_entitlements",
        ["school_id", "enabled", "capability"],
    )
    op.create_table(
        "school_entitlement_events",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("entitlement_id", sa.BigInteger(), nullable=False),
        sa.Column("capability", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column("entitlement_version", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=24), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            f"capability IN ({CAPABILITY_SQL})",
            name="ck_school_entitlement_events_capability",
        ),
        sa.CheckConstraint(
            "source IN ('pilot', 'trial', 'paid', 'complimentary')",
            name="ck_school_entitlement_events_source",
        ),
        sa.CheckConstraint(
            "action IN ('backfilled', 'created', 'updated', 'enabled', 'disabled')",
            name="ck_school_entitlement_events_action",
        ),
        sa.CheckConstraint("entitlement_version >= 1", name="ck_school_entitlement_events_version"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["entitlement_id"], ["school_entitlements.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_school_entitlement_events_school_id", "school_entitlement_events", ["school_id"])
    op.create_index(
        "ix_school_entitlement_events_school_capability_time",
        "school_entitlement_events",
        ["school_id", "capability", "occurred_at", "id"],
    )
    op.execute(
        """
        CREATE FUNCTION school_entitlement_events_append_only_guard() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'school entitlement events are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_school_entitlement_events_append_only
        BEFORE UPDATE OR DELETE ON school_entitlement_events
        FOR EACH ROW EXECUTE FUNCTION school_entitlement_events_append_only_guard()
        """
    )

    connection = op.get_bind()
    dom_user_id = connection.execute(
        sa.text(
            "SELECT u.id FROM users u JOIN platform_admins pa ON pa.user_id = u.id "
            "WHERE lower(u.email) = 'dom.dcubed@gmail.com' AND u.google_sub IS NOT NULL "
            "AND u.status = 'active' AND pa.revoked_at IS NULL"
        )
    ).scalar()
    if dom_user_id is None:
        raise RuntimeError("Verified Dom platform account is required to bootstrap entitlement authority")
    connection.execute(
        sa.text(
            "UPDATE platform_admins SET manage_school_entitlements = true "
            "WHERE user_id = :user_id AND revoked_at IS NULL"
        ),
        {"user_id": dom_user_id},
    )
    for capability in CAPABILITIES:
        connection.execute(
            sa.text(
                "INSERT INTO school_entitlements "
                "(school_id, capability, enabled, source, effective_from, internal_note, entitlement_version, updated_by_user_id) "
                "SELECT id, :capability, true, 'pilot', CURRENT_DATE, "
                "'Existing school capability preserved during canonical entitlement migration', 1, :user_id "
                "FROM schools"
            ),
            {"capability": capability, "user_id": dom_user_id},
        )
    entitlement_rows = connection.execute(
        sa.text(
            "SELECT id, school_id, capability, enabled, source, effective_from, internal_note, entitlement_version "
            "FROM school_entitlements ORDER BY school_id, capability"
        )
    ).mappings()
    event_payloads = [
        {
            "event_id": uuid.uuid4(),
            "school_id": row["school_id"],
            "entitlement_id": row["id"],
            "capability": row["capability"],
            "enabled": row["enabled"],
            "source": row["source"],
            "effective_from": row["effective_from"],
            "internal_note": row["internal_note"],
            "entitlement_version": row["entitlement_version"],
            "actor_user_id": dom_user_id,
        }
        for row in entitlement_rows
    ]
    if event_payloads:
        connection.execute(
            sa.text(
                "INSERT INTO school_entitlement_events "
                "(event_id, school_id, entitlement_id, capability, enabled, source, effective_from, internal_note, entitlement_version, action, actor_user_id) "
                "VALUES (:event_id, :school_id, :entitlement_id, :capability, :enabled, :source, :effective_from, "
                ":internal_note, :entitlement_version, 'backfilled', :actor_user_id)"
            ),
            event_payloads,
        )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_school_entitlement_events_append_only "
        "ON school_entitlement_events"
    )
    op.execute("DROP FUNCTION IF EXISTS school_entitlement_events_append_only_guard()")
    op.drop_index("ix_school_entitlement_events_school_capability_time", table_name="school_entitlement_events")
    op.drop_index("ix_school_entitlement_events_school_id", table_name="school_entitlement_events")
    op.drop_table("school_entitlement_events")
    op.drop_index("ix_school_entitlements_school_enabled", table_name="school_entitlements")
    op.drop_index("ix_school_entitlements_school_id", table_name="school_entitlements")
    op.drop_table("school_entitlements")
    op.drop_column("platform_admins", "manage_school_entitlements")

"""add FHH messaging actor assertion replay evidence

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fhh_messaging_assertion_uses",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("jti", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("fhh_link_id", sa.Integer(), nullable=False),
        sa.Column("identity_id", sa.Integer(), nullable=False),
        sa.Column("request_method", sa.String(length=8), nullable=False),
        sa.Column("request_path_hash", sa.String(length=64), nullable=False),
        sa.Column("body_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "request_method IN ('GET', 'POST')",
            name="ck_fhh_messaging_assertion_uses_method",
        ),
        sa.ForeignKeyConstraint(
            ["school_id"], ["schools.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["fhh_link_id"], ["fhh_links.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["identity_id"],
            ["fhh_messaging_identities.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("jti", name="uq_fhh_messaging_assertion_uses_jti"),
    )
    op.create_index(
        "ix_fhh_messaging_assertion_uses_school_id",
        "fhh_messaging_assertion_uses",
        ["school_id"],
    )
    op.create_index(
        "ix_fhh_messaging_assertion_uses_fhh_link_id",
        "fhh_messaging_assertion_uses",
        ["fhh_link_id"],
    )
    op.create_index(
        "ix_fhh_messaging_assertion_uses_identity_id",
        "fhh_messaging_assertion_uses",
        ["identity_id"],
    )
    op.create_index(
        "ix_fhh_messaging_assertion_uses_expiry",
        "fhh_messaging_assertion_uses",
        ["expires_at", "id"],
    )
    op.create_index(
        "ix_fhh_messaging_assertion_uses_link_used",
        "fhh_messaging_assertion_uses",
        ["fhh_link_id", "used_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_fhh_messaging_assertion_uses_link_used",
        table_name="fhh_messaging_assertion_uses",
    )
    op.drop_index(
        "ix_fhh_messaging_assertion_uses_expiry",
        table_name="fhh_messaging_assertion_uses",
    )
    op.drop_index(
        "ix_fhh_messaging_assertion_uses_identity_id",
        table_name="fhh_messaging_assertion_uses",
    )
    op.drop_index(
        "ix_fhh_messaging_assertion_uses_fhh_link_id",
        table_name="fhh_messaging_assertion_uses",
    )
    op.drop_index(
        "ix_fhh_messaging_assertion_uses_school_id",
        table_name="fhh_messaging_assertion_uses",
    )
    op.drop_table("fhh_messaging_assertion_uses")

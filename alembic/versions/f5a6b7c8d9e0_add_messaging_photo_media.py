"""add protected staged messaging photo media

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_media",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("client_upload_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("uploaded_by_participant_id", sa.BigInteger(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("state", sa.String(length=16), server_default="processing", nullable=False),
        sa.Column("storage_backend", sa.String(length=16), server_default="local", nullable=False),
        sa.Column("full_storage_key", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_storage_key", sa.String(length=500), nullable=True),
        sa.Column("content_type", sa.String(length=64), nullable=True),
        sa.Column("full_bytes", sa.Integer(), nullable=True),
        sa.Column("thumbnail_bytes", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("thumbnail_width", sa.Integer(), nullable=True),
        sa.Column("thumbnail_height", sa.Integer(), nullable=True),
        sa.Column("source_checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("original_filename_safe", sa.String(length=160), nullable=True),
        sa.Column("metadata_stripped", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP + INTERVAL '24 hours'"),
            nullable=False,
        ),
        sa.Column("attached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("sort_order BETWEEN 0 AND 4", name="ck_message_media_sort_order"),
        sa.CheckConstraint(
            "state IN ('processing', 'ready', 'attached', 'failed', 'expired', 'deleted')",
            name="ck_message_media_state",
        ),
        sa.CheckConstraint("storage_backend = 'local'", name="ck_message_media_storage_backend"),
        sa.CheckConstraint(
            "(state IN ('ready', 'attached') AND full_storage_key IS NOT NULL "
            "AND thumbnail_storage_key IS NOT NULL AND content_type IS NOT NULL "
            "AND full_bytes > 0 AND thumbnail_bytes > 0 AND width > 0 AND height > 0 "
            "AND thumbnail_width > 0 AND thumbnail_height > 0 AND checksum_sha256 IS NOT NULL "
            "AND metadata_stripped = true) OR state NOT IN ('ready', 'attached')",
            name="ck_message_media_ready_shape",
        ),
        sa.CheckConstraint(
            "(state = 'attached' AND message_id IS NOT NULL AND attached_at IS NOT NULL) "
            "OR (state <> 'attached' AND message_id IS NULL AND attached_at IS NULL)",
            name="ck_message_media_attachment_shape",
        ),
        sa.CheckConstraint(
            "(state IN ('expired', 'deleted') AND deleted_at IS NOT NULL) "
            "OR (state NOT IN ('expired', 'deleted') AND deleted_at IS NULL)",
            name="ck_message_media_deleted_shape",
        ),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["uploaded_by_participant_id"],
            ["conversation_participants.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_message_media_public_id"),
        sa.UniqueConstraint(
            "conversation_id",
            "uploaded_by_participant_id",
            "client_upload_id",
            name="uq_message_media_participant_upload",
        ),
        sa.UniqueConstraint("message_id", "sort_order", name="uq_message_media_message_order"),
    )
    op.create_index("ix_message_media_school_id", "message_media", ["school_id"])
    op.create_index("ix_message_media_conversation_id", "message_media", ["conversation_id"])
    op.create_index("ix_message_media_message_id", "message_media", ["message_id"])
    op.create_index(
        "ix_message_media_uploaded_by_participant_id",
        "message_media",
        ["uploaded_by_participant_id"],
    )
    op.create_index(
        "ix_message_media_conversation_message",
        "message_media",
        ["conversation_id", "message_id", "sort_order"],
    )
    op.create_index(
        "ix_message_media_state_expiry",
        "message_media",
        ["state", "expires_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_message_media_state_expiry", table_name="message_media")
    op.drop_index("ix_message_media_conversation_message", table_name="message_media")
    op.drop_index("ix_message_media_uploaded_by_participant_id", table_name="message_media")
    op.drop_index("ix_message_media_message_id", table_name="message_media")
    op.drop_index("ix_message_media_conversation_id", table_name="message_media")
    op.drop_index("ix_message_media_school_id", table_name="message_media")
    op.drop_table("message_media")

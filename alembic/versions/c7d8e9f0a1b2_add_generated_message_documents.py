"""Add generated report and certificate message documents.

Revision ID: c7d8e9f0a1b2
Revises: c6d7e8f9a0b1
"""

from alembic import op
import sqlalchemy as sa


revision = "c7d8e9f0a1b2"
down_revision = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_documents",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("generated_by_membership_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("source_ref", sa.String(length=120), nullable=False),
        sa.Column("original_filename_safe", sa.String(length=180), nullable=False),
        sa.Column("content_type", sa.String(length=80), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=24), server_default="ready", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disposed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("document_type IN ('behaviour_report', 'recognition_certificate')", name="ck_message_documents_type"),
        sa.CheckConstraint("content_type IN ('application/pdf', 'text/csv')", name="ck_message_documents_content_type"),
        sa.CheckConstraint("state IN ('ready', 'attached', 'expired', 'retention_deleted')", name="ck_message_documents_state"),
        sa.CheckConstraint("size_bytes BETWEEN 1 AND 10485760", name="ck_message_documents_size"),
        sa.CheckConstraint("length(checksum_sha256) = 64", name="ck_message_documents_checksum"),
        sa.CheckConstraint(
            "(state = 'ready' AND message_id IS NULL AND attached_at IS NULL AND disposed_at IS NULL AND storage_key IS NOT NULL) OR "
            "(state = 'attached' AND message_id IS NOT NULL AND attached_at IS NOT NULL AND disposed_at IS NULL AND storage_key IS NOT NULL) OR "
            "(state = 'expired' AND message_id IS NULL AND attached_at IS NULL AND disposed_at IS NOT NULL AND storage_key IS NULL) OR "
            "(state = 'retention_deleted' AND message_id IS NOT NULL AND attached_at IS NOT NULL AND disposed_at IS NOT NULL AND storage_key IS NULL)",
            name="ck_message_documents_lifecycle",
        ),
        sa.ForeignKeyConstraint(["generated_by_membership_id"], ["memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_message_documents_generated_by_membership_id", "message_documents", ["generated_by_membership_id"])
    op.create_index("ix_message_documents_message_id", "message_documents", ["message_id"])
    op.create_index("ix_message_documents_school_id", "message_documents", ["school_id"])
    op.create_index("ix_message_documents_school_state_expiry", "message_documents", ["school_id", "state", "expires_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_message_documents_school_state_expiry", table_name="message_documents")
    op.drop_index("ix_message_documents_school_id", table_name="message_documents")
    op.drop_index("ix_message_documents_message_id", table_name="message_documents")
    op.drop_index("ix_message_documents_generated_by_membership_id", table_name="message_documents")
    op.drop_table("message_documents")

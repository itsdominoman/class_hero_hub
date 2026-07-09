"""Add guardian onboarding invites and links

Revision ID: f3a4b5c6d7e8
Revises: c3d4e5f6a7b8
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guardian_invites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("student_guardian_contact_id", sa.Integer(), nullable=True),
        sa.Column("slot", sa.Integer(), nullable=True),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("display_code_last4", sa.String(), nullable=True),
        sa.Column("relationship", sa.String(), nullable=True),
        sa.Column("guardian_name", sa.String(), nullable=True),
        sa.Column("guardian_email", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.Integer(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.CheckConstraint("slot IS NULL OR slot IN (1, 2)", name="ck_guardian_invites_slot"),
        sa.CheckConstraint(
            "relationship IS NULL OR relationship IN ('mother', 'father', 'guardian', 'other')",
            name="ck_guardian_invites_relationship",
        ),
        sa.ForeignKeyConstraint(["claimed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["student_guardian_contact_id"], ["student_guardian_contacts.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_guardian_invites_id"), "guardian_invites", ["id"])
    op.create_index(op.f("ix_guardian_invites_school_id"), "guardian_invites", ["school_id"])
    op.create_index("ix_guardian_invites_school_student", "guardian_invites", ["school_id", "student_id"])
    op.create_index(op.f("ix_guardian_invites_student_guardian_contact_id"), "guardian_invites", ["student_guardian_contact_id"])
    op.create_index(op.f("ix_guardian_invites_student_id"), "guardian_invites", ["student_id"])
    op.create_index(op.f("ix_guardian_invites_token_hash"), "guardian_invites", ["token_hash"], unique=True)

    op.create_table(
        "guardian_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("relationship", sa.String(), nullable=True),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("source_guardian_invite_id", sa.Integer(), nullable=True),
        sa.Column("student_guardian_contact_id", sa.Integer(), nullable=True),
        sa.Column("email_matched_contact", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "relationship IS NULL OR relationship IN ('mother', 'father', 'guardian', 'other')",
            name="ck_guardian_links_relationship",
        ),
        sa.CheckConstraint("status IN ('active', 'revoked')", name="ck_guardian_links_status"),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["source_guardian_invite_id"], ["guardian_invites.id"]),
        sa.ForeignKeyConstraint(["student_guardian_contact_id"], ["student_guardian_contacts.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "user_id", name="uq_guardian_links_student_user"),
    )
    op.create_index(op.f("ix_guardian_links_id"), "guardian_links", ["id"])
    op.create_index(op.f("ix_guardian_links_school_id"), "guardian_links", ["school_id"])
    op.create_index("ix_guardian_links_school_user", "guardian_links", ["school_id", "user_id"])
    op.create_index(op.f("ix_guardian_links_student_id"), "guardian_links", ["student_id"])
    op.create_index(op.f("ix_guardian_links_user_id"), "guardian_links", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_guardian_links_user_id"), table_name="guardian_links")
    op.drop_index(op.f("ix_guardian_links_student_id"), table_name="guardian_links")
    op.drop_index("ix_guardian_links_school_user", table_name="guardian_links")
    op.drop_index(op.f("ix_guardian_links_school_id"), table_name="guardian_links")
    op.drop_index(op.f("ix_guardian_links_id"), table_name="guardian_links")
    op.drop_table("guardian_links")
    op.drop_index(op.f("ix_guardian_invites_token_hash"), table_name="guardian_invites")
    op.drop_index(op.f("ix_guardian_invites_student_id"), table_name="guardian_invites")
    op.drop_index(op.f("ix_guardian_invites_student_guardian_contact_id"), table_name="guardian_invites")
    op.drop_index("ix_guardian_invites_school_student", table_name="guardian_invites")
    op.drop_index(op.f("ix_guardian_invites_school_id"), table_name="guardian_invites")
    op.drop_index(op.f("ix_guardian_invites_id"), table_name="guardian_invites")
    op.drop_table("guardian_invites")

"""Add email delivery metadata to Family Hero Hub link invitations.

Revision ID: a2b3c4d5e6f7
Revises: a1e2f3c4d5b6
"""

from alembic import op
import sqlalchemy as sa


revision = "a2b3c4d5e6f7"
down_revision = "a1e2f3c4d5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fhh_link_invites",
        sa.Column(
            "student_guardian_contact_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.add_column(
        "fhh_link_invites",
        sa.Column("recipient_email", sa.String(), nullable=True),
    )
    op.add_column(
        "fhh_link_invites",
        sa.Column(
            "send_status",
            sa.String(),
            server_default="not_requested",
            nullable=False,
        ),
    )
    op.add_column(
        "fhh_link_invites",
        sa.Column("last_send_error", sa.String(), nullable=True),
    )
    op.add_column(
        "fhh_link_invites",
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_fhh_link_invites_guardian_contact",
        "fhh_link_invites",
        "student_guardian_contacts",
        ["student_guardian_contact_id"],
        ["id"],
    )
    op.create_index(
        "ix_fhh_link_invites_student_guardian_contact_id",
        "fhh_link_invites",
        ["student_guardian_contact_id"],
    )
    op.create_index(
        "ix_fhh_link_invites_school_contact",
        "fhh_link_invites",
        ["school_id", "student_guardian_contact_id"],
    )
    op.create_check_constraint(
        "ck_fhh_link_invites_send_status",
        "fhh_link_invites",
        "send_status IN ('not_requested', 'pending', 'sent', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_fhh_link_invites_send_status",
        "fhh_link_invites",
        type_="check",
    )
    op.drop_index(
        "ix_fhh_link_invites_school_contact",
        table_name="fhh_link_invites",
    )
    op.drop_index(
        "ix_fhh_link_invites_student_guardian_contact_id",
        table_name="fhh_link_invites",
    )
    op.drop_constraint(
        "fk_fhh_link_invites_guardian_contact",
        "fhh_link_invites",
        type_="foreignkey",
    )
    op.drop_column("fhh_link_invites", "sent_at")
    op.drop_column("fhh_link_invites", "last_send_error")
    op.drop_column("fhh_link_invites", "send_status")
    op.drop_column("fhh_link_invites", "recipient_email")
    op.drop_column("fhh_link_invites", "student_guardian_contact_id")

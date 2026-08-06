"""Allow protected survey-summary message documents.

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
"""

from alembic import op


revision = "d8e9f0a1b2c3"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("message_documents") as batch_op:
        batch_op.drop_constraint("ck_message_documents_type", type_="check")
        batch_op.create_check_constraint(
            "ck_message_documents_type",
            "document_type IN ('behaviour_report', 'recognition_certificate', 'survey_summary')",
        )


def downgrade() -> None:
    with op.batch_alter_table("message_documents") as batch_op:
        batch_op.drop_constraint("ck_message_documents_type", type_="check")
        batch_op.create_check_constraint(
            "ck_message_documents_type",
            "document_type IN ('behaviour_report', 'recognition_certificate')",
        )

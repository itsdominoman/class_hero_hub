"""Store versioned staff messaging-policy acknowledgements.

Revision ID: f0e1d2c3b4a5
Revises: b3c4d5e6f7a8
"""

from alembic import op
import sqlalchemy as sa


revision = "f0e1d2c3b4a5"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "messaging_policy_acknowledgements",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "policy_version",
            name="uq_messaging_policy_acknowledgements_user_version",
        ),
    )
    op.create_index(
        "ix_messaging_policy_acknowledgements_user_id",
        "messaging_policy_acknowledgements",
        ["user_id"],
    )
    op.create_index(
        "ix_messaging_policy_acknowledgements_user_time",
        "messaging_policy_acknowledgements",
        ["user_id", "acknowledged_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_messaging_policy_acknowledgements_user_time",
        table_name="messaging_policy_acknowledgements",
    )
    op.drop_index(
        "ix_messaging_policy_acknowledgements_user_id",
        table_name="messaging_policy_acknowledgements",
    )
    op.drop_table("messaging_policy_acknowledgements")

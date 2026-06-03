"""add ledger source transaction

Revision ID: 2f3c4d5e6a7b
Revises: 9b0b6e5ad4d2
Create Date: 2026-06-03 06:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2f3c4d5e6a7b"
down_revision: Union[str, None] = "9b0b6e5ad4d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ledger_transactions", sa.Column("source_transaction_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_ledger_transactions_source_transaction_id",
        "ledger_transactions",
        "ledger_transactions",
        ["source_transaction_id"],
        ["id"],
    )
    op.create_index(
        "ix_ledger_transactions_source_transaction_id",
        "ledger_transactions",
        ["source_transaction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ledger_transactions_source_transaction_id", table_name="ledger_transactions")
    op.drop_constraint(
        "fk_ledger_transactions_source_transaction_id",
        "ledger_transactions",
        type_="foreignkey",
    )
    op.drop_column("ledger_transactions", "source_transaction_id")

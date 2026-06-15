"""add ledger idempotency constraints

Revision ID: 7c2b9f1a0d4e
Revises: 3a7e1c9d4b52
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c2b9f1a0d4e"
down_revision: Union[str, None] = "3a7e1c9d4b52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _assert_no_duplicate_idempotency_rows() -> None:
    connection = op.get_bind()
    checks = {
        "duplicate reversal rows per source_transaction_id": """
            SELECT source_transaction_id
            FROM ledger_transactions
            WHERE transaction_type = 'reversal'
              AND source_transaction_id IS NOT NULL
            GROUP BY source_transaction_id
            HAVING COUNT(*) > 1
        """,
        "duplicate savings maturity/bonus rows per source/type/jar": """
            SELECT source_transaction_id, transaction_type, jar
            FROM ledger_transactions
            WHERE transaction_type IN ('savings_maturity', 'savings_bonus')
              AND source_transaction_id IS NOT NULL
            GROUP BY source_transaction_id, transaction_type, jar
            HAVING COUNT(*) > 1
        """,
    }
    for label, sql in checks.items():
        duplicates = connection.execute(sa.text(sql)).fetchmany(5)
        if duplicates:
            raise RuntimeError(
                f"Cannot add Phase 2 idempotency index: {label} already exist. "
                "Resolve duplicate ledger rows manually before running this migration."
            )


def upgrade() -> None:
    _assert_no_duplicate_idempotency_rows()

    if op.get_context().dialect.name == "sqlite":
        with op.batch_alter_table("redemption_requests") as batch_op:
            batch_op.create_unique_constraint(
                "uq_redemption_requests_id_child_id",
                ["id", "child_id"],
            )
        with op.batch_alter_table("ledger_transactions") as batch_op:
            batch_op.add_column(sa.Column("redemption_request_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_ledger_transactions_redemption_request_child",
                "redemption_requests",
                ["redemption_request_id", "child_id"],
                ["id", "child_id"],
            )
    else:
        op.create_unique_constraint(
            "uq_redemption_requests_id_child_id",
            "redemption_requests",
            ["id", "child_id"],
        )
        op.add_column(
            "ledger_transactions",
            sa.Column("redemption_request_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_ledger_transactions_redemption_request_child",
            "ledger_transactions",
            "redemption_requests",
            ["redemption_request_id", "child_id"],
            ["id", "child_id"],
        )
    op.create_index(
        "ix_ledger_transactions_redemption_request_id",
        "ledger_transactions",
        ["redemption_request_id"],
        unique=False,
    )
    op.create_index(
        "uq_ledger_reversal_source",
        "ledger_transactions",
        ["source_transaction_id"],
        unique=True,
        postgresql_where=sa.text("transaction_type = 'reversal'"),
        sqlite_where=sa.text("transaction_type = 'reversal'"),
    )
    op.create_index(
        "uq_ledger_savings_maturity_source_type_jar",
        "ledger_transactions",
        ["source_transaction_id", "transaction_type", "jar"],
        unique=True,
        postgresql_where=sa.text("transaction_type IN ('savings_maturity', 'savings_bonus')"),
        sqlite_where=sa.text("transaction_type IN ('savings_maturity', 'savings_bonus')"),
    )
    op.create_index(
        "uq_ledger_redemption_hold_request",
        "ledger_transactions",
        ["redemption_request_id"],
        unique=True,
        postgresql_where=sa.text("transaction_type = 'redemption_hold'"),
        sqlite_where=sa.text("transaction_type = 'redemption_hold'"),
    )
    op.create_index(
        "uq_ledger_redemption_release_request",
        "ledger_transactions",
        ["redemption_request_id"],
        unique=True,
        postgresql_where=sa.text("transaction_type = 'redemption_rejected'"),
        sqlite_where=sa.text("transaction_type = 'redemption_rejected'"),
    )


def downgrade() -> None:
    op.drop_index("uq_ledger_redemption_release_request", table_name="ledger_transactions")
    op.drop_index("uq_ledger_redemption_hold_request", table_name="ledger_transactions")
    op.drop_index("uq_ledger_savings_maturity_source_type_jar", table_name="ledger_transactions")
    op.drop_index("uq_ledger_reversal_source", table_name="ledger_transactions")
    op.drop_index("ix_ledger_transactions_redemption_request_id", table_name="ledger_transactions")
    if op.get_context().dialect.name == "sqlite":
        with op.batch_alter_table("ledger_transactions") as batch_op:
            batch_op.drop_constraint(
                "fk_ledger_transactions_redemption_request_child",
                type_="foreignkey",
            )
            batch_op.drop_column("redemption_request_id")
        with op.batch_alter_table("redemption_requests") as batch_op:
            batch_op.drop_constraint(
                "uq_redemption_requests_id_child_id",
                type_="unique",
            )
    else:
        op.drop_constraint(
            "fk_ledger_transactions_redemption_request_child",
            "ledger_transactions",
            type_="foreignkey",
        )
        op.drop_column("ledger_transactions", "redemption_request_id")
        op.drop_constraint(
            "uq_redemption_requests_id_child_id",
            "redemption_requests",
            type_="unique",
        )

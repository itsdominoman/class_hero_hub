#!/usr/bin/env python3
"""Controlled SQLite -> PostgreSQL ETL for Family Hero Hub.

This script is intentionally explicit and conservative:
- dry-run mode validates source/target compatibility without writing
- import mode requires an extra confirmation flag
- the live app runtime database is never used as the import target unless
  explicitly provided via --target-url
- SQLite is opened read-only
- production import requires a production-specific confirmation flag
- non-standard PostgreSQL database names require an explicit override
- the families/parent_users cycle is handled by deferred backfill
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Time, create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.sql.sqltypes import Enum as SAEnum


SCRIPT_DIR = Path(__file__).resolve().parent
if (SCRIPT_DIR.parent / "data").exists():
    PROJECT_ROOT = SCRIPT_DIR.parent
    BACKEND_DIR = PROJECT_ROOT
elif (SCRIPT_DIR.parent.parent / "data").exists():
    PROJECT_ROOT = SCRIPT_DIR.parent.parent
    BACKEND_DIR = PROJECT_ROOT / "backend"
else:
    PROJECT_ROOT = SCRIPT_DIR.parent
    BACKEND_DIR = SCRIPT_DIR.parent

SOURCE_DB_DEFAULT = PROJECT_ROOT / "data" / "family_hero_hub.sqlite"
DEV_TARGET_DB = "family_hero_hub_dev"
PRODUCTION_TARGET_DB = "family_hero_hub"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base  # noqa: E402
import app.models  # noqa: F401,E402


APP_TABLE_ORDER = [
    "families",
    "parent_users",
    "approved_parent_emails",
    "registration_requests",
    "children",
    "family_invites",
    "child_device_invites",
    "child_device_sessions",
    "preset_behaviours",
    "rewards",
    "ledger_transactions",
    "redemption_requests",
    "pet_progress",
    "calendar_entries",
    "weekly_streaks",
    "school_items",
    "calendar_task_completions",
]

CYCLIC_NULLABLE_COLUMNS = {
    "families": {"suspended_by_parent_id", "restored_by_parent_id"},
    "parent_users": {"revoked_by_parent_id", "restored_by_parent_id"},
}

EXTRA_TARGET_TABLES = {"alembic_version"}
FETCH_CHUNK_SIZE = 500


@dataclass
class TableCheck:
    table: str
    source_count: int
    target_count: int
    source_columns: list[str]
    target_columns: list[str]
    missing_columns: list[str]
    extra_columns: list[str]
    type_warnings: list[str]


def load_env_value(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value

    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return None

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        if key.strip() != name:
            continue
        value = raw_value.strip().strip('"').strip("'")
        return value or None
    return None


def source_connection(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite source database not found: {db_path}")
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def sqlite_table_columns(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    return [dict(row) for row in rows]


def sqlite_table_count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]


def sqlite_table_rows(
    conn: sqlite3.Connection,
    table: str,
    limit: int | None = None,
) -> Iterable[dict[str, Any]]:
    sql = f'SELECT * FROM "{table}"'
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    cursor = conn.execute(sql)
    while True:
        batch = cursor.fetchmany(FETCH_CHUNK_SIZE)
        if not batch:
            break
        for row in batch:
            yield dict(row)


def postgres_counts(conn) -> dict[str, int]:
    result = {}
    for table in APP_TABLE_ORDER:
        result[table] = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one()
    return result


def target_columns_for_table(inspector, table: str) -> list[str]:
    return [col["name"] for col in inspector.get_columns(table, schema="public")]


def source_type_category(declared_type: str | None) -> str:
    value = (declared_type or "").upper()
    if not value:
        return "unknown"
    if "INT" in value:
        return "integer"
    if any(token in value for token in ("CHAR", "CLOB", "TEXT", "VARCHAR")):
        return "string"
    if "BOOL" in value:
        return "boolean"
    if "DATE" in value and "TIME" not in value:
        return "date"
    if "TIME" in value and "DATE" not in value:
        return "time"
    if any(token in value for token in ("REAL", "FLOA", "DOUB")):
        return "float"
    if any(token in value for token in ("ENUM", "JSON")):
        return "string"
    if "DATETIME" in value or "TIMESTAMP" in value:
        return "datetime"
    return "string"


def target_type_category(column) -> str:
    col_type = column.type
    if isinstance(col_type, SAEnum):
        return "string"
    if isinstance(col_type, Boolean):
        return "boolean"
    if isinstance(col_type, Integer):
        return "integer"
    if isinstance(col_type, Float):
        return "float"
    if isinstance(col_type, DateTime):
        return "datetime"
    if isinstance(col_type, Date):
        return "date"
    if isinstance(col_type, Time):
        return "time"
    if isinstance(col_type, String):
        return "string"
    return type(col_type).__name__.lower()


def compatible_categories(source_category: str, target_category: str) -> bool:
    if source_category == "unknown":
        return True
    if source_category == target_category:
        return True
    # SQLite often stores datetimes/dates as text.
    if source_category in {"date", "time", "datetime"} and target_category == "string":
        return True
    if source_category == "string" and target_category in {"date", "time", "datetime"}:
        return True
    return False


def coerce_value(value: Any, column) -> Any:
    if value is None:
        return None

    col_type = column.type

    if isinstance(col_type, SAEnum):
        if hasattr(value, "value"):
            return value.value
        return str(value)

    if isinstance(col_type, Boolean):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "t", "yes", "y"}:
                return True
            if normalized in {"0", "false", "f", "no", "n"}:
                return False
        return bool(value)

    if isinstance(col_type, Integer):
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip() != "":
            return int(value)
        return value

    if isinstance(col_type, Float):
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and value.strip() != "":
            return float(value)
        return value

    if isinstance(col_type, DateTime):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value.strip() != "":
            normalized = value.strip().replace("Z", "+00:00")
            return datetime.fromisoformat(normalized.replace(" ", "T"))
        return value

    if isinstance(col_type, Date):
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, str) and value.strip() != "":
            return date.fromisoformat(value.strip())
        return value

    if isinstance(col_type, Time):
        if isinstance(value, time):
            return value
        if isinstance(value, str) and value.strip() != "":
            return time.fromisoformat(value.strip())
        return value

    return value


def normalize_table_row(table, row: dict[str, Any], deferred_columns: set[str] | None = None) -> dict[str, Any]:
    deferred_columns = deferred_columns or set()
    normalized = {}
    for column in table.columns:
        value = row.get(column.name)
        if column.name in deferred_columns:
            value = None
        normalized[column.name] = coerce_value(value, column)
    return normalized


def compare_table_schema(table_name: str, source_columns: list[dict[str, Any]], target_table) -> tuple[list[str], list[str], list[str]]:
    source_names = [column["name"] for column in source_columns]
    target_names = [column.name for column in target_table.columns]

    missing = [name for name in target_names if name not in source_names]
    extra = [name for name in source_names if name not in target_names]
    warnings: list[str] = []

    for source_column in source_columns:
        name = source_column["name"]
        if name not in target_table.c:
            continue
        target_column = target_table.c[name]
        source_category = source_type_category(source_column.get("type"))
        target_category = target_type_category(target_column)
        if not compatible_categories(source_category, target_category):
            warnings.append(
                f"{table_name}.{name}: source {source_category} -> target {target_category}"
            )

    return missing, extra, warnings


def print_target_identity(url) -> None:
    print("=== Target PostgreSQL ===")
    print(f"driver={url.drivername}")
    print(f"host={url.host}")
    print(f"database={url.database}")
    if url.username:
        print(f"user={url.username}")


def sqlite_foreign_key_violations(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("PRAGMA foreign_key_check").fetchall()
    return [dict(row) for row in rows]


def build_target_engine(
    url_string: str,
    allow_non_standard_target: bool = False,
    confirm_production_cutover: bool = False,
):
    url = make_url(url_string)
    if not url.drivername.startswith(("postgresql", "postgres")):
        raise ValueError(f"Refusing non-PostgreSQL target URL: {url.render_as_string(hide_password=True)}")
    if url.database == PRODUCTION_TARGET_DB and not confirm_production_cutover:
        raise ValueError(
            f"Refusing production database '{PRODUCTION_TARGET_DB}' without "
            "--confirm-production-cutover."
        )
    if url.database not in {DEV_TARGET_DB, PRODUCTION_TARGET_DB} and not allow_non_standard_target:
        raise ValueError(
            f"Refusing target database '{url.database}'. Expected '{DEV_TARGET_DB}' "
            f"or '{PRODUCTION_TARGET_DB}' unless --allow-non-standard-target is set."
        )
    return url, create_engine(url)


def gather_checks(source_conn: sqlite3.Connection, target_conn, inspector) -> list[TableCheck]:
    checks: list[TableCheck] = []
    target_tables = set(inspector.get_table_names(schema="public"))

    for table_name in APP_TABLE_ORDER:
        if table_name not in target_tables:
            raise RuntimeError(f"Target table missing from PostgreSQL schema: {table_name}")
        if table_name not in Base.metadata.tables:
            raise RuntimeError(f"Model metadata missing table: {table_name}")
        target_table = Base.metadata.tables[table_name]
        source_columns = sqlite_table_columns(source_conn, table_name)
        if not source_columns:
            raise RuntimeError(f"Source table missing or schema unreadable: {table_name}")

        missing, extra, warnings = compare_table_schema(table_name, source_columns, target_table)
        checks.append(
            TableCheck(
                table=table_name,
                source_count=sqlite_table_count(source_conn, table_name),
                target_count=target_conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar_one(),
                source_columns=[column["name"] for column in source_columns],
                target_columns=[column.name for column in target_table.columns],
                missing_columns=missing,
                extra_columns=extra,
                type_warnings=warnings,
            )
        )

    return checks


def print_checks(checks: list[TableCheck], limit: int | None) -> None:
    print("=== Table compatibility and counts ===")
    for check in checks:
        print(f"{check.table}: source={check.source_count} target={check.target_count}")
        print(f"  source_columns={', '.join(check.source_columns)}")
        print(f"  target_columns={', '.join(check.target_columns)}")
        if check.missing_columns:
            print(f"  missing_on_source={check.missing_columns}")
        if check.extra_columns:
            print(f"  extra_on_source={check.extra_columns}")
        if check.type_warnings:
            print(f"  type_warnings={check.type_warnings}")
        if limit is not None:
            print(f"  import_limit={limit}")


def print_planned_order() -> None:
    print("=== Planned import order ===")
    for index, table in enumerate(APP_TABLE_ORDER, start=1):
        note = ""
        if table in CYCLIC_NULLABLE_COLUMNS:
            note = " (deferred cycle columns backfilled later)"
        print(f"{index:02d}. {table}{note}")


def validate_target_state(inspector) -> None:
    print("=== Target schema validation ===")
    expected_tables = set(APP_TABLE_ORDER) | EXTRA_TARGET_TABLES
    actual_tables = set(inspector.get_table_names(schema="public"))
    missing = sorted(expected_tables - actual_tables)
    unexpected = sorted(actual_tables - expected_tables)
    if missing:
        raise RuntimeError(f"Target schema missing tables: {missing}")
    if unexpected:
        print(f"  unexpected_target_tables={unexpected}")
    print("  target schema tables present")


def validate_source_integrity(source_conn: sqlite3.Connection) -> None:
    print("=== Source SQLite integrity validation ===")
    integrity = source_conn.execute("PRAGMA integrity_check").fetchone()[0]
    print(f"  integrity_check={integrity}")
    if integrity != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity}")

    violations = sqlite_foreign_key_violations(source_conn)
    print(f"  foreign_key_violations={len(violations)}")
    if violations:
        raise RuntimeError(f"SQLite foreign key violations present: {violations}")


def row_mapping(table, rows: list[dict[str, Any]], deferred_columns: set[str] | None = None) -> list[dict[str, Any]]:
    return [normalize_table_row(table, row, deferred_columns=deferred_columns) for row in rows]


def upsert_backfill_columns(conn, table, rows: list[dict[str, Any]], deferred_columns: set[str]) -> None:
    if not deferred_columns:
        return
    columns = [column for column in table.columns if column.name in deferred_columns]
    if not columns:
        return

    assignments = ", ".join(f"{column.name} = :{column.name}" for column in columns)
    statement = text(f'UPDATE "{table.name}" SET {assignments} WHERE id = :id')
    payload = []
    for row in rows:
        mapped = {"id": row["id"]}
        for column in columns:
            mapped[column.name] = coerce_value(row.get(column.name), column)
        payload.append(mapped)
    if payload:
        conn.execute(statement, payload)


def import_rows(conn, table, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    conn.execute(table.insert(), rows)


def clear_target_tables(conn, clear_order: list[str]) -> None:
    print("=== Clearing target tables ===")
    # Break the families/parent_users cycle first so reverse-order deletes work.
    conn.execute(text('UPDATE "families" SET suspended_by_parent_id = NULL, restored_by_parent_id = NULL'))
    conn.execute(text('UPDATE "parent_users" SET revoked_by_parent_id = NULL, restored_by_parent_id = NULL'))
    for table_name in clear_order:
        conn.execute(text(f'DELETE FROM "{table_name}"'))


def sync_sequences(conn, table_names: list[str]) -> None:
    for table_name in table_names:
        sequence_name = conn.execute(
            text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
            {"table_name": table_name},
        ).scalar_one_or_none()
        if not sequence_name:
            continue
        max_id = conn.execute(text(f'SELECT COALESCE(MAX(id), 0) FROM "{table_name}"')).scalar_one()
        if max_id <= 0:
            conn.execute(
                text("SELECT setval(:sequence_name, 1, false)"),
                {"sequence_name": sequence_name},
            )
        else:
            conn.execute(
                text("SELECT setval(:sequence_name, :max_id, true)"),
                {"sequence_name": sequence_name, "max_id": max_id},
            )


def perform_import(
    source_conn: sqlite3.Connection,
    target_conn,
    limit: int | None,
    clear_target: bool,
) -> None:
    if clear_target:
        clear_target_tables(target_conn, list(reversed(APP_TABLE_ORDER)))

    source_rows_by_table: dict[str, list[dict[str, Any]]] = {}
    for table_name in APP_TABLE_ORDER:
        source_rows_by_table[table_name] = list(sqlite_table_rows(source_conn, table_name, limit=limit))

    target_tables = Base.metadata.tables

    for table_name in APP_TABLE_ORDER:
        table = target_tables[table_name]
        deferred_columns = CYCLIC_NULLABLE_COLUMNS.get(table_name, set())
        rows = source_rows_by_table[table_name]
        normalized = row_mapping(table, rows, deferred_columns=deferred_columns)
        print(f"Inserting {len(normalized)} rows into {table_name}")
        import_rows(target_conn, table, normalized)

    # Backfill the cyclic references only after both tables exist in PostgreSQL.
    for table_name in ("parent_users", "families"):
        table = target_tables[table_name]
        deferred_columns = CYCLIC_NULLABLE_COLUMNS[table_name]
        upsert_backfill_columns(target_conn, table, source_rows_by_table[table_name], deferred_columns)

    sync_sequences(target_conn, APP_TABLE_ORDER)

    # Validation after import.
    source_counts = {table: len(rows) for table, rows in source_rows_by_table.items()}
    target_counts = postgres_counts(target_conn)
    print("=== Post-import row count validation ===")
    mismatches = []
    for table_name in APP_TABLE_ORDER:
        expected = source_counts[table_name]
        actual = target_counts[table_name]
        print(f"{table_name}: source={expected} target={actual}")
        if expected != actual:
            mismatches.append((table_name, expected, actual))
    if mismatches:
        raise RuntimeError(f"Row count mismatches after import: {mismatches}")


def dry_run_report(checks: list[TableCheck], target_url, limit: int | None) -> None:
    print_target_identity(target_url)
    print("=== Dry-run result ===")
    print("  target_was_modified=False")
    print(f"  target_database={target_url.database}")
    print("  source_is_read_only=True")
    print("  families/parent_users cycle handled by deferred backfill")
    if limit is not None:
        print(f"  limit={limit}")
    print_checks(checks, limit=limit)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Validate source/target compatibility without writing")
    mode.add_argument("--import", dest="do_import", action="store_true", help="Import SQLite data into PostgreSQL")
    parser.add_argument(
        "--yes-i-understand-this-writes-postgres",
        action="store_true",
        help="Required confirmation for --import",
    )
    parser.add_argument(
        "--clear-target",
        action="store_true",
        help="Delete target app rows first in reverse import order",
    )
    parser.add_argument(
        "--allow-non-standard-target",
        action="store_true",
        help="Allow target database names other than family_hero_hub_dev or family_hero_hub",
    )
    parser.add_argument(
        "--allow-non-dev-target",
        action="store_true",
        help="Deprecated alias for --allow-non-standard-target",
    )
    parser.add_argument(
        "--confirm-production-cutover",
        action="store_true",
        help="Required when the target database is the production database family_hero_hub",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit rows imported per table for controlled testing",
    )
    parser.add_argument(
        "--source-path",
        type=Path,
        default=SOURCE_DB_DEFAULT,
        help="Path to the SQLite source database",
    )
    parser.add_argument(
        "--target-url",
        default=None,
        help="Override target PostgreSQL URL instead of MIGRATION_DATABASE_URL",
    )
    return parser.parse_args()


def resolve_target_url(args: argparse.Namespace) -> str:
    candidate = args.target_url or load_env_value("MIGRATION_DATABASE_URL")
    if not candidate:
        raise RuntimeError(
            "MIGRATION_DATABASE_URL is missing. Refusing to continue without an explicit PostgreSQL target."
        )
    runtime_database_url = os.environ.get("DATABASE_URL") or load_env_value("DATABASE_URL")
    if candidate == runtime_database_url:
        raise RuntimeError(
            "Refusing to use runtime DATABASE_URL as the migration target. "
            "Use a separate MIGRATION_DATABASE_URL or --target-url before switching runtime."
        )
    return candidate


def main() -> int:
    args = parse_args()
    if args.do_import and not args.yes_i_understand_this_writes_postgres:
        raise SystemExit("--import requires --yes-i-understand-this-writes-postgres")

    source_conn = source_connection(args.source_path)
    target_url_string = resolve_target_url(args)
    target_url, target_engine = build_target_engine(
        target_url_string,
        allow_non_standard_target=args.allow_non_standard_target or args.allow_non_dev_target,
        confirm_production_cutover=args.confirm_production_cutover,
    )

    print("=== Source SQLite ===")
    print(f"path={args.source_path}")
    print("read_only=True")

    print_target_identity(target_url)

    with target_engine.begin() as target_conn:
        inspector = inspect(target_conn)
        validate_source_integrity(source_conn)
        validate_target_state(inspector)
        checks = gather_checks(source_conn, target_conn, inspector)
        print_checks(checks, limit=args.limit)
        print_planned_order()

        missing_tables = []
        extra_tables = []
        for check in checks:
            if check.missing_columns:
                missing_tables.append((check.table, check.missing_columns))
            if check.extra_columns:
                extra_tables.append((check.table, check.extra_columns))
        if missing_tables or extra_tables:
            raise RuntimeError(
                f"Schema mismatch detected. missing_tables={missing_tables} extra_tables={extra_tables}"
            )
        if any(check.type_warnings for check in checks):
            raise RuntimeError("Type compatibility warnings present; refusing to proceed.")

        if args.dry_run:
            dry_run_report(checks, target_url, limit=args.limit)
            return 0

        if not args.clear_target:
            current_counts = postgres_counts(target_conn)
            non_empty = {table: count for table, count in current_counts.items() if count != 0}
            if non_empty:
                raise RuntimeError(
                    f"Target database is not empty. Refusing to import without --clear-target: {non_empty}"
                )

        perform_import(source_conn, target_conn, limit=args.limit, clear_target=args.clear_target)
        print("=== Import complete ===")
        print("  target_was_modified=True")
        print("  source_was_not_modified=True")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

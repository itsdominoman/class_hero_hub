"""Inventory or transactionally remove CHH users with no active entitlement."""

from __future__ import annotations

import argparse
import csv
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.admission_cleanup import (  # noqa: E402
    CleanupBlocked,
    InventoryRow,
    REQUIRED_REMOVALS,
    SEEDED_EXCEPTIONS,
    apply_cleanup,
    build_inventory,
)
from app.database import SessionLocal, settings  # noqa: E402
from app.models_school import User  # noqa: E402

FIELDNAMES = list(InventoryRow.__dataclass_fields__)
APPLY_CONFIRMATION = "REMOVE-UNAUTHORISED-CHH-USERS"
PILOT_TARGET = "class.familyherohub.com"


def _write_report(path: Path, rows: list[InventoryRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)
        temp_path = Path(handle.name)
    os.chmod(temp_path, 0o600)
    os.replace(temp_path, path)


def _read_report(path: Path) -> list[InventoryRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDNAMES:
            raise CleanupBlocked("The dry-run report schema is not recognised.")
        return [
            InventoryRow(
                email_address=row["email_address"],
                user_id=int(row["user_id"]),
                creation_date=row["creation_date"],
                last_successful_login=row["last_successful_login"],
                authentication_method=row["authentication_method"],
                reason_classified_as_unauthorised=row[
                    "reason_classified_as_unauthorised"
                ],
                disposition=row["disposition"],
            )
            for row in reader
        ]


def _dry_run(report_path: Path) -> int:
    with SessionLocal() as db:
        rows = build_inventory(db)
    _write_report(report_path, rows)
    planned = [row for row in rows if row.disposition == "planned_removal"]
    preserved = [row for row in rows if row.disposition == "preserved_seeded_identity"]
    print(
        f"dry_run_candidates={len(rows)} planned_removals={len(planned)} "
        f"preserved_seeded={len(preserved)} report={report_path}"
    )
    return 0


def _apply(
    report_path: Path,
    confirmation: str | None,
    pilot_target: str | None,
) -> int:
    if (
        settings.APP_ENV not in {"development", "test"}
        and pilot_target != PILOT_TARGET
    ):
        raise CleanupBlocked(
            f"The hardened pilot runtime requires --pilot-target {PILOT_TARGET}."
        )
    if confirmation != APPLY_CONFIRMATION:
        raise CleanupBlocked(f"--confirm must equal {APPLY_CONFIRMATION}.")

    rows = _read_report(report_path)
    planned_rows = [row for row in rows if row.disposition == "planned_removal"]
    preserved_rows = [
        row for row in rows if row.disposition == "preserved_seeded_identity"
    ]
    if any(row.email_address in SEEDED_EXCEPTIONS for row in planned_rows):
        raise CleanupBlocked("A documented seeded identity was marked for removal.")
    report_emails = {row.email_address for row in planned_rows}
    if not REQUIRED_REMOVALS.issubset(report_emails):
        raise CleanupBlocked("The dry-run report does not contain every mandatory removal.")

    with SessionLocal() as db:
        try:
            with db.begin():
                removed_ids = apply_cleanup(db, [row.user_id for row in planned_rows])
        except Exception:
            db.rollback()
            raise

        if (
            db.query(User.id).filter(User.id.in_(removed_ids)).first() is not None
            or db.query(User.id)
            .filter(User.id.in_([row.user_id for row in preserved_rows]))
            .count()
            != len(preserved_rows)
        ):
            raise CleanupBlocked("Post-cleanup identity verification failed.")

    final_rows = [
        InventoryRow(
            **{
                **asdict(row),
                "disposition": (
                    "removed"
                    if row.disposition == "planned_removal"
                    else row.disposition
                ),
            }
        )
        for row in rows
    ]
    _write_report(report_path, final_rows)
    print(
        f"removed={len(removed_ids)} preserved_seeded={len(preserved_rows)} "
        f"report={report_path}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm")
    parser.add_argument("--pilot-target")
    args = parser.parse_args()
    try:
        return (
            _apply(args.report, args.confirm, args.pilot_target)
            if args.apply
            else _dry_run(args.report)
        )
    except CleanupBlocked as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

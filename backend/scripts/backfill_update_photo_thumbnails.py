"""Audit or generate missing protected update-photo thumbnails.

Dry-run is the default. Pass --apply only after reviewing the dry-run result.
The command never overwrites full images or existing thumbnails and prints only
aggregate counts and byte totals, with no school, student, photo, path, or
filename identifiers.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.database import SessionLocal
from app.update_thumbnail_backfill import backfill_update_photo_thumbnails


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write missing derived thumbnails. Without this flag the command is read-only.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = backfill_update_photo_thumbnails(db, apply=args.apply)
    finally:
        db.close()
    print(json.dumps(report.as_dict(), sort_keys=True))
    if report.failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

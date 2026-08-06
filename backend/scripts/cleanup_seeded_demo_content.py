"""Remove only manifest-proven seeded school content; dry-run by default."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal
from app.demo_seed_cleanup import CleanupError, cleanup_seeded_content


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit the planned cleanup; default is read-only dry-run.")
    parser.add_argument("--school-slug", default="united-international-school", help="Exact target school slug.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.apply:
        if os.environ.get("APP_ENV", "").strip().lower() != "development":
            print("Refusing --apply outside APP_ENV=development.", file=sys.stderr)
            return 1
        if os.environ.get("DEMO_CLEANUP_CONFIRM") != args.school_slug:
            print("Refusing --apply without DEMO_CLEANUP_CONFIRM set to the exact school slug.", file=sys.stderr)
            return 1

    db = SessionLocal()
    try:
        summary = cleanup_seeded_content(db, school_slug=args.school_slug, apply=args.apply)
        print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))
        return 0
    except CleanupError as exc:
        db.rollback()
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

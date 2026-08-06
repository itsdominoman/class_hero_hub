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


def apply_guard_error(school_slug: str) -> str | None:
    app_env = os.environ.get("APP_ENV", "").strip().lower()
    if os.environ.get("DEMO_CLEANUP_CONFIRM") != school_slug:
        return "DEMO_CLEANUP_CONFIRM must equal the exact school slug."
    if app_env == "development":
        return None
    if app_env == "production":
        expected = f"manifest-content-cleanup:{school_slug}"
        if os.environ.get("DEMO_CLEANUP_PRODUCTION_CONFIRM") == expected:
            return None
        return f"DEMO_CLEANUP_PRODUCTION_CONFIRM must equal {expected!r}."
    return "APP_ENV must be development or production."


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.apply:
        guard_error = apply_guard_error(args.school_slug)
        if guard_error:
            print(f"Refusing --apply: {guard_error}", file=sys.stderr)
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

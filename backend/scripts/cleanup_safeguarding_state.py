"""Expire review sessions and remove temporary safeguarding export artifacts."""
from __future__ import annotations

import argparse

from app.database import SessionLocal
from app.safeguarding_service import cleanup_expired_safeguarding_state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 5000:
        raise SystemExit("--limit must be between 1 and 5000")
    db = SessionLocal()
    try:
        result = cleanup_expired_safeguarding_state(db, limit=args.limit)
        print(
            "expired_sessions={expired_sessions} expired_exports={expired_exports} "
            "deleted_files={deleted_files}".format(**result)
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()

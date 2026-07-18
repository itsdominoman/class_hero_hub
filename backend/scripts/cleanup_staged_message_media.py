"""Safely expire abandoned Messaging v1 staged photos.

Dry-run is the default.  Output contains aggregate counts only and never emits
opaque media IDs, storage keys, filenames, message content, or participant data.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.database import SessionLocal
from app.message_media_service import cleanup_expired_staged_media
from app.models_school import MessageMedia


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 10_000:
        raise SystemExit("--limit must be between 1 and 10000")
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        eligible = (
            db.query(MessageMedia)
            .filter(
                MessageMedia.message_id.is_(None),
                MessageMedia.state.in_(("processing", "ready", "failed")),
                MessageMedia.expires_at <= now,
            )
            .count()
        )
        removed = (
            cleanup_expired_staged_media(db, now=now, limit=args.limit)
            if args.apply
            else 0
        )
    finally:
        db.close()
    print(
        json.dumps(
            {
                "apply": args.apply,
                "eligible": eligible,
                "expired": removed,
                "limit": args.limit,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

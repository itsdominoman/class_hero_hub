from __future__ import annotations

import logging
import socket
import time
import uuid

from .database import SessionLocal, settings
from .messaging_production import process_one_job


logger = logging.getLogger(__name__)


def run() -> None:
    worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:12]}"
    while True:
        if not settings.MESSAGING_PRODUCTION_WORKER_ENABLED:
            time.sleep(max(settings.MESSAGING_PRODUCTION_WORKER_POLL_SECONDS, 1))
            continue
        try:
            processed = process_one_job(
                SessionLocal,
                worker_id=worker_id,
                lease_seconds=settings.MESSAGING_PRODUCTION_JOB_LEASE_SECONDS,
            )
        except Exception:
            logger.exception("Messaging production worker batch failed")
            processed = 0
        time.sleep(1 if processed else max(settings.MESSAGING_PRODUCTION_WORKER_POLL_SECONDS, 1))


if __name__ == "__main__":
    run()

from __future__ import annotations

import logging
import time
import uuid

from .database import SessionLocal, settings
from .messaging_notifications import process_notification_scheduler_batch


logger = logging.getLogger(__name__)


def run() -> None:
    worker_id = f"notification-scheduler-{uuid.uuid4().hex[:12]}"
    while True:
        processed = 0
        if settings.MESSAGING_NOTIFICATION_SCHEDULER_ENABLED:
            try:
                processed = process_notification_scheduler_batch(
                    SessionLocal,
                    worker_id=worker_id,
                )
            except Exception:
                logger.exception("Messaging notification scheduler batch failed")
        time.sleep(
            1
            if processed
            else max(settings.MESSAGING_NOTIFICATION_SCHEDULER_POLL_SECONDS, 1)
        )


if __name__ == "__main__":
    run()

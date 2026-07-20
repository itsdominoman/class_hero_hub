from __future__ import annotations

import logging
import time
import uuid

from .database import SessionLocal, settings
from .messaging_notification_dispatch import process_notification_dispatch_batch
from .messaging_notifications import process_notification_scheduler_batch


logger = logging.getLogger(__name__)


def run() -> None:
    suffix = uuid.uuid4().hex[:12]
    scheduler_worker_id = f"notification-scheduler-{suffix}"
    dispatch_worker_id = f"notification-dispatch-{suffix}"
    while True:
        processed = 0
        if settings.MESSAGING_NOTIFICATION_SCHEDULER_ENABLED:
            try:
                processed = process_notification_scheduler_batch(
                    SessionLocal,
                    worker_id=scheduler_worker_id,
                )
            except Exception:
                logger.exception("Messaging notification scheduler batch failed")
        if settings.MESSAGING_NOTIFICATION_DISPATCH_ENABLED:
            try:
                processed += process_notification_dispatch_batch(
                    SessionLocal,
                    worker_id=dispatch_worker_id,
                )
            except Exception:
                logger.exception("Messaging notification provider batch failed")
        time.sleep(
            1
            if processed
            else max(settings.MESSAGING_NOTIFICATION_SCHEDULER_POLL_SECONDS, 1)
        )


if __name__ == "__main__":
    run()

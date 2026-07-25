from __future__ import annotations

import logging
import time
import uuid

from .database import SessionLocal, settings
from .messaging_notification_dispatch import process_notification_dispatch_batch
from .messaging_notifications import process_notification_scheduler_batch
from .messaging_production import record_worker_heartbeat
from .point_notification_summaries import process_point_summary_generation_batch


logger = logging.getLogger(__name__)


def run() -> None:
    suffix = uuid.uuid4().hex[:12]
    scheduler_worker_id = f"notification-scheduler-{suffix}"
    dispatch_worker_id = f"notification-dispatch-{suffix}"
    summary_school_cursor = 0
    while True:
        processed = 0
        error_code = None
        if settings.MESSAGING_NOTIFICATION_SCHEDULER_ENABLED:
            try:
                summary_batch = process_point_summary_generation_batch(
                    SessionLocal,
                    after_school_id=summary_school_cursor,
                    school_limit=settings.MESSAGING_NOTIFICATION_SCHEDULER_BATCH_SIZE,
                )
                summary_school_cursor = summary_batch.next_after_school_id
                processed += summary_batch.generated
                processed = process_notification_scheduler_batch(
                    SessionLocal,
                    worker_id=scheduler_worker_id,
                ) + processed
            except Exception as exc:
                error_code = exc.__class__.__name__
                logger.exception("Messaging notification scheduler batch failed")
        if settings.MESSAGING_NOTIFICATION_DISPATCH_ENABLED:
            try:
                processed += process_notification_dispatch_batch(
                    SessionLocal,
                    worker_id=dispatch_worker_id,
                )
            except Exception as exc:
                error_code = error_code or exc.__class__.__name__
                logger.exception("Messaging notification provider batch failed")
        with SessionLocal() as heartbeat_db:
            record_worker_heartbeat(
                heartbeat_db,
                worker_name="notification",
                instance_id=scheduler_worker_id,
                processed=processed,
                error_code=error_code,
            )
        time.sleep(
            1
            if processed
            else max(settings.MESSAGING_NOTIFICATION_SCHEDULER_POLL_SECONDS, 1)
        )


if __name__ == "__main__":
    run()

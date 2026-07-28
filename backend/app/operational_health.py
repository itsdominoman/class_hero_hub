from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import Session

from .database import SessionLocal, engine, settings
from .models_school import MessagingOperationsJob, MessagingWorkerHeartbeat, NotificationOutbox


EXPECTED_MIGRATION_REVISION = "a4e5f6b7c8d9"
WORKER_STALE_SECONDS = 120
QUEUE_BACKLOG_STALE_SECONDS = 300
BACKUP_MAX_AGE_SECONDS = 30 * 3600
BACKUP_MARKER_MAX_AGE_SECONDS = 26 * 3600
DISK_WARNING_PERCENT = 80
DISK_CRITICAL_PERCENT = 90

STATUS_ROOT = Path(os.getenv("OPERATIONS_STATUS_ROOT", "/app/host-status"))
BACKUP_STATUS_FILE = STATUS_ROOT / "backup-status" / "health.json"
SCHEDULED_STATUS_DIR = STATUS_ROOT / "scheduled-status"
DATA_PATH = Path(os.getenv("OPERATIONS_DISK_PATH", "/app/data"))


def _build_readiness_engine():
    if settings.DATABASE_URL.startswith("sqlite"):
        return engine
    return create_engine(
        settings.DATABASE_URL,
        connect_args={
            "connect_timeout": 2,
            "options": "-c statement_timeout=2000",
        },
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
        pool_timeout=2,
        pool_recycle=60,
    )


readiness_engine = _build_readiness_engine()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _age_seconds(now: datetime, value: datetime | None) -> int | None:
    if value is None:
        return None
    return max(0, int((now - _aware(value)).total_seconds()))


def _database_probe() -> str | None:
    with readiness_engine.connect() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(text("SET LOCAL statement_timeout = '2000ms'"))
        connection.execute(text("SELECT 1")).scalar_one()
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()


def readiness_payload(probe: Callable[[], str | None] | None = None) -> tuple[dict[str, Any], int]:
    try:
        revision = (probe or _database_probe)()
    except Exception:
        return {
            "status": "unavailable",
            "checks": {
                "database": "unavailable",
                "migration": "unknown",
            },
        }, 503

    migration_state = "current" if revision == EXPECTED_MIGRATION_REVISION else "outdated"
    return {
        "status": "ok" if migration_state == "current" else "degraded",
        "checks": {
            "database": "ok",
            "migration": migration_state,
        },
    }, 200 if migration_state == "current" else 503


def _state_counts(db: Session, model: Any) -> dict[str, int]:
    rows = db.query(model.state, func.count(model.id)).group_by(model.state).all()
    return {str(state): int(count) for state, count in rows}


def _backup_status(now: datetime) -> dict[str, Any]:
    base = {
        "state": "missing",
        "age_seconds": None,
        "marker_age_seconds": None,
        "max_age_seconds": BACKUP_MAX_AGE_SECONDS,
        "marker_max_age_seconds": BACKUP_MARKER_MAX_AGE_SECONDS,
    }
    try:
        payload = json.loads(BACKUP_STATUS_FILE.read_text(encoding="utf-8"))
        timestamp = datetime.fromisoformat(str(payload["timestamp"]).replace("Z", "+00:00"))
        marker_age = _age_seconds(now, timestamp)
        recorded_ages = [
            int(payload[key]["age_seconds"])
            for key in ("local", "off_host")
            if isinstance(payload.get(key), dict) and payload[key].get("age_seconds") is not None
        ]
        backup_age = max(recorded_ages) + int(marker_age or 0) if recorded_ages else None
        state = str(payload.get("state", "invalid"))
        if (
            state == "ok"
            and backup_age is not None
            and backup_age <= BACKUP_MAX_AGE_SECONDS
            and marker_age is not None
            and marker_age <= BACKUP_MARKER_MAX_AGE_SECONDS
        ):
            state = "ok"
        elif state == "ok":
            state = "stale"
        return {
            **base,
            "state": state,
            "age_seconds": backup_age,
            "marker_age_seconds": marker_age,
        }
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return base


def _scheduled_status(now: datetime) -> dict[str, Any]:
    jobs: list[dict[str, Any]] = []
    try:
        status_files = sorted(SCHEDULED_STATUS_DIR.glob("*.status"))[:50]
    except OSError:
        status_files = []
    for path in status_files:
        try:
            values = dict(
                token.split("=", 1)
                for token in path.read_text(encoding="utf-8").strip().split()
                if "=" in token
            )
            timestamp = datetime.fromisoformat(values["timestamp"].replace("Z", "+00:00"))
            age = _age_seconds(now, timestamp)
            job = values.get("job", path.stem)[:120]
            max_age = 35 * 86400 if "restore-rehearsal" in job else 8 * 86400 if "weekly" in job else 30 * 3600
            state = values.get("state", "invalid")
            stale = age is None or age > max_age
            jobs.append(
                {
                    "job": job,
                    "state": state,
                    "age_seconds": age,
                    "max_age_seconds": max_age,
                    "exit_code": int(values["exit_code"]) if values.get("exit_code", "").isdigit() else None,
                    "stale": stale,
                }
            )
        except (OSError, ValueError, KeyError):
            jobs.append(
                {
                    "job": path.stem[:120],
                    "state": "invalid",
                    "age_seconds": None,
                    "max_age_seconds": None,
                    "exit_code": None,
                    "stale": True,
                }
            )
    return {
        "jobs": jobs,
        "failed": [row["job"] for row in jobs if row["state"] != "ok"],
        "stale": [row["job"] for row in jobs if row["stale"]],
    }


def _disk_status() -> dict[str, Any]:
    try:
        usage = shutil.disk_usage(DATA_PATH)
        used_percent = round((usage.used / usage.total) * 100, 2) if usage.total else 0.0
        state = (
            "critical"
            if used_percent >= DISK_CRITICAL_PERCENT
            else "warning"
            if used_percent >= DISK_WARNING_PERCENT
            else "ok"
        )
        return {
            "state": state,
            "used_percent": used_percent,
            "warning_percent": DISK_WARNING_PERCENT,
            "critical_percent": DISK_CRITICAL_PERCENT,
        }
    except OSError:
        return {
            "state": "unavailable",
            "used_percent": None,
            "warning_percent": DISK_WARNING_PERCENT,
            "critical_percent": DISK_CRITICAL_PERCENT,
        }


def _worker_status(db: Session, now: datetime) -> list[dict[str, Any]]:
    expected: list[str] = []
    if settings.MESSAGING_PRODUCTION_WORKER_ENABLED:
        expected.append("production")
    if settings.MESSAGING_NOTIFICATION_SCHEDULER_ENABLED or settings.MESSAGING_NOTIFICATION_DISPATCH_ENABLED:
        expected.append("notification")
    rows = {row.worker_name: row for row in db.query(MessagingWorkerHeartbeat).all()}
    return [
        {
            "worker": worker,
            "state": "missing"
            if worker not in rows
            else "stale"
            if (_age_seconds(now, rows[worker].last_seen_at) or 0) > WORKER_STALE_SECONDS
            else "ok",
            "heartbeat_age_seconds": _age_seconds(now, rows[worker].last_seen_at) if worker in rows else None,
            "stale_after_seconds": WORKER_STALE_SECONDS,
            "last_success_age_seconds": _age_seconds(now, rows[worker].last_success_at) if worker in rows else None,
            "last_error_code": rows[worker].last_error_code if worker in rows else None,
            "processed_total": int(rows[worker].processed_total or 0) if worker in rows else 0,
        }
        for worker in expected
    ]


def operations_status(db: Session) -> dict[str, Any]:
    now = datetime.now(UTC)
    revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    migration_state = "current" if revision == EXPECTED_MIGRATION_REVISION else "outdated"

    job_counts = _state_counts(db, MessagingOperationsJob)
    notification_counts = _state_counts(db, NotificationOutbox)
    oldest_job = db.query(func.min(MessagingOperationsJob.created_at)).filter(
        MessagingOperationsJob.state.in_(("pending", "failed")),
        MessagingOperationsJob.next_attempt_at <= now,
    ).scalar()
    oldest_notification = db.query(func.min(NotificationOutbox.created_at)).filter(
        NotificationOutbox.state.in_(("pending", "failed")),
        NotificationOutbox.next_attempt_at <= now,
    ).scalar()
    queue_status = {
        "operations_jobs": {
            "states": job_counts,
            "dead": int(job_counts.get("dead", 0)),
            "oldest_ready_age_seconds": _age_seconds(now, oldest_job) or 0,
        },
        "notifications": {
            "states": notification_counts,
            "dead": int(notification_counts.get("dead", 0)),
            "oldest_ready_age_seconds": _age_seconds(now, oldest_notification) or 0,
        },
        "backlog_stale_after_seconds": QUEUE_BACKLOG_STALE_SECONDS,
    }
    workers = _worker_status(db, now)
    backup = _backup_status(now)
    scheduled = _scheduled_status(now)
    disk = _disk_status()

    alerts: list[str] = []
    if migration_state != "current":
        alerts.append("migration_outdated")
    if any(row["state"] != "ok" for row in workers):
        alerts.append("worker_stale_or_missing")
    if any(queue["dead"] for queue in (queue_status["operations_jobs"], queue_status["notifications"])):
        alerts.append("dead_letter_present")
    if any(
        queue["oldest_ready_age_seconds"] > QUEUE_BACKLOG_STALE_SECONDS
        for queue in (queue_status["operations_jobs"], queue_status["notifications"])
    ):
        alerts.append("queue_backlog_stale")
    if backup["state"] != "ok":
        alerts.append("backup_unhealthy_or_stale")
    if scheduled["failed"]:
        alerts.append("scheduled_job_failed")
    if scheduled["stale"]:
        alerts.append("scheduled_job_stale")
    if disk["state"] != "ok":
        alerts.append("disk_risk")

    return {
        "status": "degraded" if alerts else "ok",
        "generated_at": now,
        "database": {
            "state": "ok",
            "migration": migration_state,
            "revision": revision,
            "expected_revision": EXPECTED_MIGRATION_REVISION,
        },
        "workers": workers,
        "queues": queue_status,
        "backup": backup,
        "scheduled_jobs": scheduled,
        "disk": disk,
        "alerts": alerts,
    }


def worker_heartbeat_is_current(worker_name: str) -> bool:
    if worker_name == "production" and not settings.MESSAGING_PRODUCTION_WORKER_ENABLED:
        return True
    if (
        worker_name == "notification"
        and not settings.MESSAGING_NOTIFICATION_SCHEDULER_ENABLED
        and not settings.MESSAGING_NOTIFICATION_DISPATCH_ENABLED
    ):
        return True
    now = datetime.now(UTC)
    with SessionLocal() as db:
        row = db.query(MessagingWorkerHeartbeat).filter_by(worker_name=worker_name).first()
        age = _age_seconds(now, row.last_seen_at) if row else None
        return age is not None and age <= WORKER_STALE_SECONDS

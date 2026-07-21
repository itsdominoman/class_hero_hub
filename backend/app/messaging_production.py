"""Durable Messaging v1 retention, archive, export and operator job processing."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session, sessionmaker

from .legal_hold_service import held_message_ids
from .message_media_service import (
    MESSAGE_MEDIA_ARCHIVE_ROOT,
    archive_media_path,
    media_path,
)
from .models_school import (
    Conversation,
    Message,
    MessageMedia,
    MessageVoiceMedia,
    MessagingEvidenceExport,
    MessagingOperationsJob,
    MessagingRetentionPolicy,
    MessagingWorkerHeartbeat,
    NotificationDelivery,
    NotificationOutbox,
    SafeguardingReviewSession,
)
from .safeguarding_service import generate_requested_evidence_export
from .messaging_metrics import snapshot as messaging_metrics_snapshot


DEFAULT_RETENTION_RULES: dict[str, Any] = {
    "message_days": 2557,
    "media_days": 2557,
    "media_hot_days": 365,
    "receipt_days": 2557,
    "notification_history_days": 365,
    "safeguarding_audit_days": 3650,
    "moderation_history_days": 3650,
    "internal_note_days": 3650,
    "export_metadata_days": 3650,
    "export_artifact_minutes": 30,
    "revoked_device_days": 90,
    "review_session_days": 3650,
    "assertion_replay_days": 30,
    "operations_job_days": 365,
    "operational_log_days": 90,
    "preserve_export_artifact_on_hold": False,
    "delete_hot_after_verified_archive": True,
}
INTEGER_RULES = {key for key, value in DEFAULT_RETENTION_RULES.items() if isinstance(value, int) and not isinstance(value, bool)}
BOOLEAN_RULES = {key for key, value in DEFAULT_RETENTION_RULES.items() if isinstance(value, bool)}
MAX_JOB_ATTEMPTS = 5
BATCH_SIZE = 100


class ProductionJobError(Exception):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_rules(rules: dict[str, Any]) -> dict[str, Any]:
    if set(rules) != set(DEFAULT_RETENTION_RULES):
        missing = sorted(set(DEFAULT_RETENTION_RULES) - set(rules))
        extra = sorted(set(rules) - set(DEFAULT_RETENTION_RULES))
        raise ProductionJobError(f"Retention rules mismatch; missing={missing}, extra={extra}")
    clean: dict[str, Any] = {}
    for key in INTEGER_RULES:
        value = rules[key]
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 36500:
            raise ProductionJobError(f"{key} must be an integer between 1 and 36500")
        clean[key] = value
    for key in BOOLEAN_RULES:
        if not isinstance(rules[key], bool):
            raise ProductionJobError(f"{key} must be a boolean")
        clean[key] = rules[key]
    return clean


def current_policy(db: Session, *, school_id: int, at: datetime | None = None) -> MessagingRetentionPolicy | None:
    moment = at or now_utc()
    return db.query(MessagingRetentionPolicy).filter(
        MessagingRetentionPolicy.school_id == school_id,
        MessagingRetentionPolicy.effective_at <= moment,
        MessagingRetentionPolicy.cancelled_at.is_(None),
    ).order_by(
        MessagingRetentionPolicy.effective_at.desc(),
        MessagingRetentionPolicy.policy_version.desc(),
    ).first()


def create_policy(
    db: Session,
    *,
    school_id: int,
    membership_id: int,
    rules: dict[str, Any],
    effective_at: datetime,
    reason: str,
    acknowledged: bool,
) -> MessagingRetentionPolicy:
    clean_reason = " ".join((reason or "").split())
    if len(clean_reason) < 8 or len(clean_reason) > 2000 or not acknowledged:
        raise ProductionJobError("A meaningful reason and explicit school-policy acknowledgement are required")
    if effective_at.tzinfo is None:
        effective_at = effective_at.replace(tzinfo=timezone.utc)
    if effective_at < now_utc() - timedelta(minutes=5):
        raise ProductionJobError("Retention policy cannot be backdated")
    clean = validate_rules(rules)
    latest = db.query(func.max(MessagingRetentionPolicy.policy_version)).filter(
        MessagingRetentionPolicy.school_id == school_id
    ).scalar() or 0
    row = MessagingRetentionPolicy(
        school_id=school_id,
        policy_version=int(latest) + 1,
        effective_at=effective_at,
        rules=clean,
        reason=clean_reason,
        acknowledged_school_policy=True,
        created_by_membership_id=membership_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def enqueue_job(
    db: Session,
    *,
    school_id: int,
    membership_id: int,
    job_type: str,
    reason: str,
    policy_id: int | None = None,
    payload: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> MessagingOperationsJob:
    clean_reason = " ".join((reason or "").split())
    if len(clean_reason) < 8 or len(clean_reason) > 2000:
        raise ProductionJobError("A meaningful operator reason is required")
    row = MessagingOperationsJob(
        school_id=school_id,
        requested_by_membership_id=membership_id,
        job_type=job_type,
        operator_reason=clean_reason,
        policy_id=policy_id,
        payload=payload or {},
        progress={},
        dry_run=dry_run,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _eligible_messages(db: Session, *, policy: MessagingRetentionPolicy, cursor: int, limit: int):
    cutoff = now_utc() - timedelta(days=int(policy.rules["message_days"]))
    return db.query(Message).join(Conversation, Conversation.id == Message.conversation_id).filter(
        Message.school_id == policy.school_id,
        Message.id > cursor,
        Message.created_at <= cutoff,
        Message.retention_disposed_at.is_(None),
        Conversation.status.in_(("closed_assignment_ended", "closed_student_archived", "closed_restricted", "archived")),
        ~db.query(SafeguardingReviewSession.id).filter(
            SafeguardingReviewSession.conversation_id == Conversation.id,
            SafeguardingReviewSession.ended_at.is_(None),
            SafeguardingReviewSession.revoked_at.is_(None),
            SafeguardingReviewSession.expires_at > now_utc(),
        ).exists(),
        ~db.query(MessagingEvidenceExport.id).filter(
            MessagingEvidenceExport.conversation_id == Conversation.id,
            MessagingEvidenceExport.state.in_(("requested", "generating", "ready")),
            MessagingEvidenceExport.expires_at > now_utc(),
        ).exists(),
    ).order_by(Message.id).limit(limit).all()


def retention_preview(db: Session, job: MessagingOperationsJob) -> dict[str, Any]:
    policy = db.query(MessagingRetentionPolicy).filter(
        MessagingRetentionPolicy.id == job.policy_id,
        MessagingRetentionPolicy.school_id == job.school_id,
        MessagingRetentionPolicy.cancelled_at.is_(None),
    ).first()
    if policy is None or aware(policy.effective_at) > now_utc():
        raise ProductionJobError("An effective retention policy is required")
    cursor = 0
    message_count = held_count = body_bytes = 0
    while True:
        rows = _eligible_messages(db, policy=policy, cursor=cursor, limit=500)
        if not rows:
            break
        cursor = int(rows[-1].id)
        held = held_message_ids(db, school_id=job.school_id, message_ids=[int(row.id) for row in rows])
        held_count += len(held)
        for row in rows:
            if int(row.id) not in held:
                message_count += 1
                body_bytes += len((row.body or "").encode("utf-8"))
    media_cutoff = now_utc() - timedelta(days=int(policy.rules["media_days"]))
    photo_count, photo_bytes = db.query(
        func.count(MessageMedia.id), func.coalesce(func.sum(MessageMedia.full_bytes), 0)
    ).join(Message, Message.id == MessageMedia.message_id).join(
        Conversation, Conversation.id == Message.conversation_id
    ).filter(
        MessageMedia.school_id == job.school_id,
        MessageMedia.state.in_(("attached", "archived")),
        MessageMedia.created_at <= media_cutoff,
        Conversation.status != "active",
    ).one()
    voice_count, voice_bytes = db.query(
        func.count(MessageVoiceMedia.id), func.coalesce(func.sum(MessageVoiceMedia.size_bytes), 0)
    ).join(Message, Message.id == MessageVoiceMedia.message_id).join(
        Conversation, Conversation.id == Message.conversation_id
    ).filter(
        MessageVoiceMedia.school_id == job.school_id,
        MessageVoiceMedia.state.in_(("attached", "archived")),
        MessageVoiceMedia.created_at <= media_cutoff,
        Conversation.status != "active",
    ).one()
    result = {
        "policy_id": str(policy.public_id),
        "policy_version": policy.policy_version,
        "as_of": now_utc().isoformat(),
        "messages": message_count,
        "message_body_bytes": body_bytes,
        "held_messages_excluded": held_count,
        "photos": int(photo_count or 0),
        "photo_bytes": int(photo_bytes or 0),
        "voice_notes": int(voice_count or 0),
        "voice_bytes": int(voice_bytes or 0),
    }
    result["preview_sha256"] = canonical_hash(result)
    return result


def retention_execute(db: Session, job: MessagingOperationsJob) -> dict[str, Any]:
    payload = job.payload or {}
    preview_id = payload.get("preview_job_id")
    supplied_hash = payload.get("preview_sha256")
    try:
        preview_public_id = uuid.UUID(str(preview_id))
    except (TypeError, ValueError) as exc:
        raise ProductionJobError("A valid preview job identifier is required") from exc
    preview = db.query(MessagingOperationsJob).filter(
        MessagingOperationsJob.public_id == preview_public_id,
        MessagingOperationsJob.school_id == job.school_id,
        MessagingOperationsJob.job_type == "retention_preview",
        MessagingOperationsJob.state == "succeeded",
        MessagingOperationsJob.policy_id == job.policy_id,
    ).first()
    if preview is None or not supplied_hash or preview.progress.get("preview_sha256") != supplied_hash:
        raise ProductionJobError("A matching completed preview and exact preview hash are required")
    policy = db.query(MessagingRetentionPolicy).filter(
        MessagingRetentionPolicy.id == job.policy_id,
        MessagingRetentionPolicy.school_id == job.school_id,
        MessagingRetentionPolicy.cancelled_at.is_(None),
    ).first()
    if policy is None or aware(policy.effective_at) > now_utc():
        raise ProductionJobError("Retention policy is not effective")
    cursor = int(job.last_cursor or 0)
    disposed = 0
    while True:
        db.refresh(job)
        if job.cancellation_requested_at is not None:
            raise InterruptedError("Cancellation requested")
        rows = _eligible_messages(db, policy=policy, cursor=cursor, limit=BATCH_SIZE)
        if not rows:
            break
        cursor = int(rows[-1].id)
        held = held_message_ids(db, school_id=job.school_id, message_ids=[int(row.id) for row in rows])
        candidates = [row for row in rows if int(row.id) not in held]
        if db.bind and db.bind.dialect.name == "postgresql":
            db.execute(text("SET LOCAL chh.retention_worker = 'on'"))
        for row in candidates:
            digest = hashlib.sha256((row.body or "").encode("utf-8")).hexdigest()
            db.execute(text(
                "UPDATE messages SET body = NULL, retention_disposed_at = :now, "
                "retention_policy_version = :version, retention_content_sha256 = :digest WHERE id = :id"
            ), {"now": now_utc(), "version": policy.policy_version, "digest": digest, "id": row.id})
            disposed += 1
        job.last_cursor = str(cursor)
        job.progress = {**(job.progress or {}), "messages_disposed": disposed, "last_message_id": cursor}
        db.commit()
    return {**(job.progress or {}), "messages_disposed": disposed, "preview_sha256": supplied_hash}


def _copy_verified(source: Path, destination: Path, expected_hash: str) -> str:
    if not source.is_file():
        raise ProductionJobError("Hot media source is missing")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        shutil.copyfile(source, temporary)
        digest = file_sha256(temporary)
        if digest != expected_hash:
            raise ProductionJobError("Archive verification hash mismatch")
        os.replace(temporary, destination)
        if file_sha256(destination) != expected_hash:
            raise ProductionJobError("Archive verification hash mismatch")
        return digest
    finally:
        temporary.unlink(missing_ok=True)


def archive_media(db: Session, job: MessagingOperationsJob) -> dict[str, Any]:
    policy = current_policy(db, school_id=job.school_id)
    if policy is None:
        raise ProductionJobError("An effective retention policy is required")
    cutoff = now_utc() - timedelta(days=int(policy.rules["media_hot_days"]))
    photos = db.query(MessageMedia).filter(
        MessageMedia.school_id == job.school_id,
        MessageMedia.state == "attached",
        MessageMedia.created_at <= cutoff,
    ).order_by(MessageMedia.id).limit(BATCH_SIZE).all()
    voices = db.query(MessageVoiceMedia).filter(
        MessageVoiceMedia.school_id == job.school_id,
        MessageVoiceMedia.state == "attached",
        MessageVoiceMedia.created_at <= cutoff,
    ).order_by(MessageVoiceMedia.id).limit(BATCH_SIZE).all()
    archived_photos = archived_voices = 0
    delete_hot = bool(policy.rules["delete_hot_after_verified_archive"])
    for row in photos:
        full_key = f"school-{row.school_id}/photo/{row.public_id}-full"
        thumb_key = f"school-{row.school_id}/photo/{row.public_id}-thumb"
        full_hash = _copy_verified(media_path(row.full_storage_key), archive_media_path(full_key), row.checksum_sha256)
        thumb_source = media_path(row.thumbnail_storage_key)
        thumb_hash = file_sha256(thumb_source)
        _copy_verified(thumb_source, archive_media_path(thumb_key), thumb_hash)
        row.archive_full_storage_key = full_key
        row.archive_thumbnail_storage_key = thumb_key
        row.archive_full_sha256 = full_hash
        row.archive_thumbnail_sha256 = thumb_hash
        row.archived_at = row.archive_verified_at = now_utc()
        row.state = "archived"
        db.commit()
        if delete_hot:
            media_path(row.full_storage_key).unlink(missing_ok=True)
            media_path(row.thumbnail_storage_key).unlink(missing_ok=True)
            row.full_storage_key = row.thumbnail_storage_key = None
            row.hot_deleted_at = now_utc()
            db.commit()
        archived_photos += 1
    for row in voices:
        key = f"school-{row.school_id}/voice/{row.public_id}.m4a"
        digest = _copy_verified(media_path(row.storage_key), archive_media_path(key), row.checksum_sha256)
        row.archive_storage_key = key
        row.archive_sha256 = digest
        row.archived_at = row.archive_verified_at = now_utc()
        row.state = "archived"
        db.commit()
        if delete_hot:
            media_path(row.storage_key).unlink(missing_ok=True)
            row.storage_key = None
            row.hot_deleted_at = now_utc()
            db.commit()
        archived_voices += 1
    return {"photos_archived": archived_photos, "voice_notes_archived": archived_voices}


def _claim_job(db: Session, *, worker_id: str, lease_seconds: int) -> tuple[MessagingOperationsJob | None, int]:
    now = now_utc()
    recovered = db.query(MessagingOperationsJob).filter(
        MessagingOperationsJob.state == "leased",
        MessagingOperationsJob.lease_expires_at <= now,
    ).update({
        MessagingOperationsJob.state: "pending",
        MessagingOperationsJob.lease_owner: None,
        MessagingOperationsJob.lease_expires_at: None,
        MessagingOperationsJob.last_error_code: "lease_expired",
    }, synchronize_session=False)
    row = db.query(MessagingOperationsJob).filter(
        MessagingOperationsJob.state.in_(("pending", "failed")),
        MessagingOperationsJob.next_attempt_at <= now,
    ).order_by(MessagingOperationsJob.created_at, MessagingOperationsJob.id).with_for_update(skip_locked=True).first()
    if row is None:
        db.commit()
        return None, int(recovered or 0)
    row.state = "leased"
    row.lease_owner = worker_id
    row.lease_expires_at = now + timedelta(seconds=lease_seconds)
    row.attempt_count += 1
    db.commit()
    db.refresh(row)
    return row, int(recovered or 0)


def _finish_job(db: Session, job: MessagingOperationsJob, *, state: str, progress: dict[str, Any] | None = None, error: Exception | None = None) -> None:
    row = db.query(MessagingOperationsJob).filter(MessagingOperationsJob.id == job.id).with_for_update().one()
    row.lease_owner = None
    row.lease_expires_at = None
    if state == "failed" and row.attempt_count >= MAX_JOB_ATTEMPTS:
        row.state = "dead"
    else:
        row.state = state
    if progress is not None:
        row.progress = progress
    if row.state in ("succeeded", "dead", "cancelled"):
        row.completed_at = now_utc()
    if error is not None:
        row.last_error_code = error.__class__.__name__[:80]
        row.last_error_detail = str(error)[:500]
        row.next_attempt_at = now_utc() + timedelta(seconds=min(30 * 2 ** max(row.attempt_count - 1, 0), 3600))
    db.commit()


def _heartbeat(db: Session, *, worker_id: str, success: bool, recovered: int, error_code: str | None = None) -> None:
    row = db.query(MessagingWorkerHeartbeat).filter(MessagingWorkerHeartbeat.worker_name == "production").first()
    if row is None:
        row = MessagingWorkerHeartbeat(worker_name="production", instance_id=worker_id)
        db.add(row)
    row.instance_id = worker_id
    row.last_seen_at = now_utc()
    row.recovered_leases_total = int(row.recovered_leases_total or 0) + recovered
    if success:
        row.last_success_at = now_utc()
        row.processed_total = int(row.processed_total or 0) + 1
        row.last_error_code = None
    elif error_code:
        row.last_error_code = error_code[:80]
    db.commit()


def process_one_job(SessionFactory: sessionmaker, *, worker_id: str, lease_seconds: int = 300) -> int:
    with SessionFactory() as db:
        job, recovered = _claim_job(db, worker_id=worker_id, lease_seconds=lease_seconds)
        if job is None:
            _heartbeat(db, worker_id=worker_id, success=False, recovered=recovered)
            return 0
        try:
            if job.cancellation_requested_at is not None:
                _finish_job(db, job, state="cancelled")
            elif job.job_type == "retention_preview":
                _finish_job(db, job, state="succeeded", progress=retention_preview(db, job))
            elif job.job_type == "retention_execute":
                _finish_job(db, job, state="succeeded", progress=retention_execute(db, job))
            elif job.job_type == "archive_media":
                _finish_job(db, job, state="succeeded", progress=archive_media(db, job))
            elif job.job_type == "evidence_export":
                export = generate_requested_evidence_export(db, export_id=job.export_id)
                _finish_job(db, job, state="succeeded", progress={
                    "export_id": str(export.public_id),
                    "artifact_sha256": export.artifact_sha256,
                    "manifest_sha256": export.manifest_sha256,
                    "size_bytes": export.size_bytes,
                })
            else:
                raise ProductionJobError("Unsupported job type")
            _heartbeat(db, worker_id=worker_id, success=True, recovered=recovered)
            return 1
        except InterruptedError:
            db.rollback()
            _finish_job(db, job, state="cancelled")
            _heartbeat(db, worker_id=worker_id, success=True, recovered=recovered)
            return 1
        except Exception as exc:
            db.rollback()
            _finish_job(db, job, state="failed", error=exc)
            _heartbeat(db, worker_id=worker_id, success=False, recovered=recovered, error_code=exc.__class__.__name__)
            return 1


def operations_summary(db: Session, *, school_id: int) -> dict[str, Any]:
    now = now_utc()
    job_counts = dict(db.query(MessagingOperationsJob.state, func.count(MessagingOperationsJob.id)).filter(
        MessagingOperationsJob.school_id == school_id
    ).group_by(MessagingOperationsJob.state).all())
    outbox_counts = dict(db.query(NotificationOutbox.state, func.count(NotificationOutbox.id)).filter(
        NotificationOutbox.school_id == school_id
    ).group_by(NotificationOutbox.state).all())
    category_counts = dict(db.query(NotificationOutbox.event_category, func.count(NotificationOutbox.id)).filter(
        NotificationOutbox.school_id == school_id
    ).group_by(NotificationOutbox.event_category).all())
    oldest = db.query(func.min(NotificationOutbox.created_at)).filter(
        NotificationOutbox.school_id == school_id,
        NotificationOutbox.state.in_(("held", "pending", "leased", "failed")),
    ).scalar()
    heartbeats = db.query(MessagingWorkerHeartbeat).all()
    disk = shutil.disk_usage(MESSAGE_MEDIA_ARCHIVE_ROOT)
    migration_revision = None
    try:
        migration_revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        db.rollback()
    pool = getattr(db.get_bind(), "pool", None)
    checked_out = int(pool.checkedout()) if pool is not None and hasattr(pool, "checkedout") else None
    pool_size = int(pool.size()) if pool is not None and hasattr(pool, "size") else None
    overflow = int(pool.overflow()) if pool is not None and hasattr(pool, "overflow") else None
    capacity = (pool_size + max(overflow or 0, 0)) if pool_size is not None else None
    saturation = round((checked_out / capacity) * 100, 2) if checked_out is not None and capacity else None
    backup_marker = Path(os.getenv("BACKUP_HEALTH_MARKER_FILE", "/app/data/backup-health.json"))
    backup_age_seconds = int(now.timestamp() - backup_marker.stat().st_mtime) if backup_marker.is_file() else None
    return {
        "generated_at": now,
        "jobs": {str(key): int(value) for key, value in job_counts.items()},
        "notification_outbox": {str(key): int(value) for key, value in outbox_counts.items()},
        "notification_categories": {str(key): int(value) for key, value in category_counts.items()},
        "oldest_notification_age_seconds": int((now - aware(oldest)).total_seconds()) if oldest else 0,
        "worker_heartbeats": [{
            "worker": row.worker_name,
            "last_seen_at": row.last_seen_at,
            "last_success_at": row.last_success_at,
            "last_error_code": row.last_error_code,
            "processed_total": int(row.processed_total or 0),
            "recovered_leases_total": int(row.recovered_leases_total or 0),
        } for row in heartbeats],
        "archive_disk_used_percent": round((disk.used / disk.total) * 100, 2) if disk.total else 0,
        "migration_revision": migration_revision,
        "database_pool": {"checked_out": checked_out, "capacity": capacity, "saturation_percent": saturation},
        "backup_marker_age_seconds": backup_age_seconds,
        "request_metrics": messaging_metrics_snapshot(),
        "alerts": {
            "dead_jobs": int(job_counts.get("dead", 0)) > 0,
            "dead_notifications": int(outbox_counts.get("dead", 0)) > 0,
            "worker_stale": any((now - aware(row.last_seen_at)).total_seconds() > 120 for row in heartbeats) or not heartbeats,
            "notification_backlog_old": bool(oldest and (now - aware(oldest)).total_seconds() > 300),
            "archive_disk_high": bool(disk.total and disk.used / disk.total >= 0.80),
            "database_pool_high": bool(saturation is not None and saturation >= 80),
            "backup_marker_stale_or_missing": backup_age_seconds is None or backup_age_seconds > 26 * 3600,
        },
    }

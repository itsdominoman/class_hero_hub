from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..messaging_production import (
    DEFAULT_RETENTION_RULES,
    ProductionJobError,
    create_policy,
    current_policy,
    enqueue_job,
    now_utc,
    operations_summary,
    validate_rules,
)
from ..models_school import (
    Membership,
    MessagingEvidenceExport,
    MessagingOperationsJob,
    MessagingOperatorAction,
    MessagingRetentionPolicy,
    NotificationDelivery,
    NotificationOutbox,
    School,
    User,
)
from ..school_governance import GovernanceConflict, GovernanceForbidden, require_owner
from ..school_scope import require_platform_admin, require_school_role


router = APIRouter(dependencies=[Depends(require_school_role("school_admin"))])
platform_router = APIRouter(dependencies=[Depends(require_platform_admin)])


class PolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rules: dict[str, Any]
    effective_at: datetime
    reason: str = Field(min_length=8, max_length=2000)
    acknowledged_school_policy: bool


class JobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=8, max_length=2000)


class ExecuteRequest(JobRequest):
    preview_job_id: UUID
    preview_sha256: str = Field(min_length=64, max_length=64, pattern="^[0-9a-f]{64}$")


class OperatorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=8, max_length=2000)


class NotificationActionRequest(OperatorRequest):
    target_ids: list[UUID] = Field(min_length=1, max_length=50)


def _require_owner(db: Session, membership: Membership) -> None:
    try:
        require_owner(db, membership)
    except GovernanceForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except GovernanceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


def _job_payload(row: MessagingOperationsJob) -> dict[str, Any]:
    return {
        "id": str(row.public_id),
        "job_type": row.job_type,
        "state": row.state,
        "dry_run": row.dry_run,
        "policy_id": row.policy_id,
        "export_id": row.export_id,
        "reason": row.operator_reason,
        "progress": row.progress,
        "attempt_count": row.attempt_count,
        "last_error_code": row.last_error_code,
        "last_error_detail": row.last_error_detail,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "completed_at": row.completed_at,
    }


def _policy_payload(row: MessagingRetentionPolicy) -> dict[str, Any]:
    return {
        "id": str(row.public_id),
        "version": row.policy_version,
        "effective_at": row.effective_at,
        "rules": row.rules,
        "reason": row.reason,
        "created_by_membership_id": row.created_by_membership_id,
        "created_at": row.created_at,
        "cancelled_at": row.cancelled_at,
        "cancellation_reason": row.cancellation_reason,
    }


@router.get("/operations")
def summary(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    return {"health": operations_summary(db, school_id=membership.school_id)}


@router.get("/operations/advanced")
def advanced_summary(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    _require_owner(db, membership)
    policy = current_policy(db, school_id=membership.school_id)
    jobs = db.query(MessagingOperationsJob).filter(
        MessagingOperationsJob.school_id == membership.school_id
    ).order_by(MessagingOperationsJob.created_at.desc(), MessagingOperationsJob.id.desc()).limit(100).all()
    dead_notifications = db.query(NotificationOutbox).filter(
        NotificationOutbox.school_id == membership.school_id,
        NotificationOutbox.state.in_(("failed", "dead")),
    ).order_by(NotificationOutbox.created_at.desc(), NotificationOutbox.id.desc()).limit(50).all()
    return {
        "health": operations_summary(db, school_id=membership.school_id),
        "active_retention_policy": _policy_payload(policy) if policy else None,
        "jobs": [_job_payload(row) for row in jobs],
        "failed_notifications": [{
            "event_id": str(row.event_id),
            "state": row.state,
            "recipient_kind": row.recipient_kind,
            "attempt_count": row.attempt_count,
            "last_error_code": row.last_error_code,
            "created_at": row.created_at,
        } for row in dead_notifications],
    }


@router.get("/operations/retention-policies")
def policies(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    rows = db.query(MessagingRetentionPolicy).filter(
        MessagingRetentionPolicy.school_id == membership.school_id
    ).order_by(MessagingRetentionPolicy.policy_version.desc()).all()
    return {"defaults": DEFAULT_RETENTION_RULES, "policies": [_policy_payload(row) for row in rows]}


@router.post("/operations/retention-policies", status_code=status.HTTP_201_CREATED)
def add_policy(
    payload: PolicyRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    _require_owner(db, membership)
    try:
        row = create_policy(
            db,
            school_id=membership.school_id,
            membership_id=membership.id,
            rules=payload.rules,
            effective_at=payload.effective_at,
            reason=payload.reason,
            acknowledged=payload.acknowledged_school_policy,
        )
        return _policy_payload(row)
    except ProductionJobError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


def _policy_or_409(db: Session, school_id: int) -> MessagingRetentionPolicy:
    row = current_policy(db, school_id=school_id)
    if row is None:
        raise HTTPException(status_code=409, detail="An effective retention policy is required")
    return row


@router.post("/operations/retention/preview", status_code=status.HTTP_202_ACCEPTED)
def preview_retention(
    payload: JobRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    _require_owner(db, membership)
    policy = _policy_or_409(db, membership.school_id)
    return _job_payload(enqueue_job(
        db,
        school_id=membership.school_id,
        membership_id=membership.id,
        job_type="retention_preview",
        reason=payload.reason,
        policy_id=policy.id,
        dry_run=True,
    ))


@router.post("/operations/retention/execute", status_code=status.HTTP_202_ACCEPTED)
def execute_retention(
    payload: ExecuteRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    _require_owner(db, membership)
    policy = _policy_or_409(db, membership.school_id)
    preview = db.query(MessagingOperationsJob).filter(
        MessagingOperationsJob.public_id == payload.preview_job_id,
        MessagingOperationsJob.school_id == membership.school_id,
        MessagingOperationsJob.job_type == "retention_preview",
        MessagingOperationsJob.state == "succeeded",
        MessagingOperationsJob.policy_id == policy.id,
    ).first()
    if preview is None or preview.progress.get("preview_sha256") != payload.preview_sha256:
        raise HTTPException(status_code=409, detail="Preview confirmation does not match the active policy")
    return _job_payload(enqueue_job(
        db,
        school_id=membership.school_id,
        membership_id=membership.id,
        job_type="retention_execute",
        reason=payload.reason,
        policy_id=policy.id,
        payload={"preview_job_id": str(payload.preview_job_id), "preview_sha256": payload.preview_sha256},
    ))


@router.post("/operations/archive", status_code=status.HTTP_202_ACCEPTED)
def start_archive(
    payload: JobRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    _require_owner(db, membership)
    policy = _policy_or_409(db, membership.school_id)
    return _job_payload(enqueue_job(
        db,
        school_id=membership.school_id,
        membership_id=membership.id,
        job_type="archive_media",
        reason=payload.reason,
        policy_id=policy.id,
    ))


@router.post("/operations/jobs/{job_id}/cancel")
def cancel_job(
    job_id: UUID,
    payload: OperatorRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    _require_owner(db, membership)
    row = db.query(MessagingOperationsJob).filter(
        MessagingOperationsJob.public_id == job_id,
        MessagingOperationsJob.school_id == membership.school_id,
    ).with_for_update().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if row.state in ("succeeded", "cancelled"):
        raise HTTPException(status_code=409, detail="Job is already terminal")
    if row.state in ("pending", "failed", "dead"):
        row.state = "cancelled"
        row.completed_at = now_utc()
        row.lease_owner = row.lease_expires_at = None
    else:
        row.cancellation_requested_at = now_utc()
    db.add(MessagingOperatorAction(
        school_id=membership.school_id,
        actor_membership_id=membership.id,
        queue_kind={"retention_preview": "retention", "retention_execute": "retention", "archive_media": "archive", "evidence_export": "export"}[row.job_type],
        action="cancel",
        target_ref=str(row.public_id),
        reason=payload.reason.strip(),
    ))
    db.commit()
    return _job_payload(row)


@router.post("/operations/jobs/{job_id}/retry")
def retry_job(
    job_id: UUID,
    payload: OperatorRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    _require_owner(db, membership)
    row = db.query(MessagingOperationsJob).filter(
        MessagingOperationsJob.public_id == job_id,
        MessagingOperationsJob.school_id == membership.school_id,
        MessagingOperationsJob.state.in_(("failed", "dead")),
    ).with_for_update().first()
    if row is None:
        raise HTTPException(status_code=409, detail="Only failed or dead jobs can be retried")
    if row.job_type == "evidence_export":
        export = db.query(MessagingEvidenceExport).filter(MessagingEvidenceExport.id == row.export_id).first()
        if export is None or export.expires_at <= now_utc():
            raise HTTPException(status_code=409, detail="Evidence export request has expired")
        export.state = "requested"
        export.failure_code = None
    row.state = "pending"
    row.next_attempt_at = now_utc()
    row.completed_at = None
    row.last_error_code = row.last_error_detail = None
    row.lease_owner = row.lease_expires_at = None
    db.add(MessagingOperatorAction(
        school_id=membership.school_id,
        actor_membership_id=membership.id,
        queue_kind={"retention_preview": "retention", "retention_execute": "retention", "archive_media": "archive", "evidence_export": "export"}[row.job_type],
        action="retry",
        target_ref=str(row.public_id),
        reason=payload.reason.strip(),
    ))
    db.commit()
    return _job_payload(row)


def _notification_action(
    db: Session,
    *,
    school_id: int,
    membership_id: int,
    target_ids: list[UUID],
    action: str,
    reason: str,
) -> int:
    rows = db.query(NotificationOutbox).filter(
        NotificationOutbox.school_id == school_id,
        NotificationOutbox.event_id.in_(target_ids),
    ).with_for_update().all()
    if len(rows) != len(set(target_ids)):
        raise HTTPException(status_code=404, detail="One or more notification targets were not found")
    changed = 0
    for row in rows:
        if row.state == "leased":
            raise HTTPException(status_code=409, detail="A leased notification cannot be changed")
        if action == "retry":
            if row.state not in ("failed", "dead", "cancelled"):
                raise HTTPException(status_code=409, detail="Only failed, dead or cancelled notifications can be retried")
            row.state = "pending"
            row.scheduler_check_at = row.next_attempt_at = now_utc()
            row.completed_at = None
            row.last_error_code = None
            row.lease_owner = row.lease_expires_at = None
            for delivery in db.query(NotificationDelivery).filter(
                NotificationDelivery.outbox_id == row.id,
                NotificationDelivery.state.in_(("failed", "dead", "cancelled")),
            ).all():
                delivery.state = "pending"
                delivery.next_attempt_at = now_utc()
                delivery.completed_at = None
                delivery.last_error_code = None
                delivery.lease_owner = delivery.lease_expires_at = None
        else:
            if row.state in ("provider_accepted", "dispatched", "cancelled"):
                raise HTTPException(status_code=409, detail="Notification is already terminal")
            row.state = "cancelled"
            row.completed_at = now_utc()
            row.last_error_code = "operator_cancelled"
            row.lease_owner = row.lease_expires_at = None
        db.add(MessagingOperatorAction(
            school_id=school_id,
            actor_membership_id=membership_id,
            queue_kind="notification",
            action=action,
            target_ref=str(row.event_id),
            reason=reason.strip(),
        ))
        changed += 1
    db.commit()
    return changed


@router.post("/operations/notifications/retry")
def retry_notifications(
    payload: NotificationActionRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    _require_owner(db, membership)
    return {"updated": _notification_action(db, school_id=membership.school_id, membership_id=membership.id, target_ids=payload.target_ids, action="retry", reason=payload.reason)}


@router.post("/operations/notifications/cancel")
def cancel_notifications(
    payload: NotificationActionRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    _require_owner(db, membership)
    return {"updated": _notification_action(db, school_id=membership.school_id, membership_id=membership.id, target_ids=payload.target_ids, action="cancel", reason=payload.reason)}


@platform_router.get("/messaging-operations")
def platform_operations(db: Session = Depends(get_db)):
    schools = db.query(School).filter(School.status.in_(("pending_setup", "active"))).order_by(School.id).all()
    return {"schools": [{
        "school_id": school.id,
        "school_name": school.name,
        "health": operations_summary(db, school_id=school.id),
    } for school in schools]}

from __future__ import annotations

import logging
from datetime import datetime, timezone
from math import ceil
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from .. import auth, mailer, models, schemas

router = APIRouter()
logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalized_email(value: str | None) -> str:
    return auth.normalize_email(value)


def _mask_google_sub(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if len(value) <= 8:
        return f"{value[:2]}…{value[-2:]}" if len(value) > 4 else value
    return f"{value[:6]}…{value[-4:]}"


def _latest_by_email(rows: list[Any], email_getter) -> dict[str, Any]:
    latest: dict[str, Any] = {}
    for row in rows:
        email = _normalized_email(email_getter(row))
        if not email or email in latest:
            continue
        latest[email] = row
    return latest


def _family_summary(db: Session, family_id: int) -> dict[str, Any]:
    family = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not family:
        return {
            "family": None,
            "children_count": 0,
            "coparents_count": 0,
            "parent_count": 0,
            "active_parent_count": 0,
        }

    parent_count = db.query(func.count(models.ParentUser.id)).filter(
        models.ParentUser.family_id == family_id
    ).scalar() or 0

    active_parent_count = auth.count_active_parents_in_family(db, family_id)

    child_count = db.query(func.count(models.Child.id)).filter(
        models.Child.family_id == family_id
    ).scalar() or 0

    return {
        "family": family,
        "children_count": child_count,
        "parent_count": parent_count,
        "active_parent_count": active_parent_count,
    }


def _build_user_record(
    db: Session,
    normalized_email: str,
    parent: models.ParentUser | None,
    approval: models.ApprovedParentEmail | None,
    registration_request: models.RegistrationRequest | None,
    accepted_invite: models.FamilyInvite | None,
) -> dict[str, Any]:
    family = parent.family if parent and parent.family_id else None
    family_data = _family_summary(db, family.id) if family else {
        "family": None,
        "children_count": 0,
        "parent_count": 0,
        "active_parent_count": 0,
    }

    is_bootstrap_admin = bool(parent and auth.is_admin(parent))
    family_status = (family.status if family else None) or None
    family_suspended_at = family.suspended_at if family else None
    family_suspend_reason = family.suspend_reason if family else None
    family_restored_at = family.restored_at if family else None
    family_restored_by_parent_id = family.restored_by_parent_id if family else None
    family_orphaned = bool(family and family_status == "active" and family_data["active_parent_count"] == 0)

    approval_status = approval.status if approval else None
    parent_status = (parent.status if parent else None) or None

    if is_bootstrap_admin:
        user_status = "bootstrap"
    elif parent_status == "revoked" or approval_status == "revoked":
        user_status = "revoked"
    elif family_status == "suspended" and parent:
        user_status = "suspended"
    else:
        user_status = "active"

    if approval:
        source = approval.source
    elif accepted_invite:
        source = "invite"
    elif is_bootstrap_admin:
        source = "bootstrap"
    elif parent:
        source = "manual_admin"
    else:
        source = None

    revoked_at = (parent.revoked_at if parent and parent.revoked_at else None) or (
        approval.revoked_at if approval and approval.revoked_at else None
    )
    restored_at = (parent.restored_at if parent and parent.restored_at else None) or (
        approval.restored_at if approval and approval.restored_at else None
    )
    restored_by_parent_id = (parent.restored_by_parent_id if parent else None) or (
        approval.restored_by_parent_id if approval else None
    )
    approved_at = approval.approved_at if approval else None
    last_login_at = parent.last_login_at if parent else None
    created_at = (parent.created_at if parent else None) or (
        approval.created_at if approval else None
    ) or (registration_request.created_at if registration_request else None)

    registration_request_id = registration_request.id if registration_request else None
    registration_request_status = registration_request.status if registration_request else None
    registration_request_family_name = registration_request.family_name if registration_request else None
    registration_request_message = registration_request.message if registration_request else None

    if parent:
        if parent_status == "active":
            coparents_count = max(family_data["active_parent_count"] - 1, 0)
        else:
            coparents_count = family_data["active_parent_count"]
    else:
        coparents_count = family_data["active_parent_count"]

    can_suspend_family = bool(family and family_status != "suspended")
    can_restore_family = bool(family and family_status == "suspended")

    if is_bootstrap_admin:
        can_revoke_reason = "bootstrap_admin"
    elif parent_status == "revoked" or approval_status == "revoked":
        can_revoke_reason = "already_revoked"
    elif parent is None:
        can_revoke_reason = "no_parent_user"
    elif family is not None and family_status == "active" and auth.count_active_parents_in_family(db, family.id, exclude_parent_id=parent.id if parent else None) == 0:
        can_revoke_reason = "only_active_parent"
    else:
        can_revoke_reason = "unknown"

    can_restore = bool(parent_status == "revoked" or approval_status == "revoked")
    can_revoke = bool(
        not is_bootstrap_admin
        and user_status == "active"
        and (family is None or family_status != "suspended")
        and (family is None or auth.count_active_parents_in_family(db, family.id, exclude_parent_id=parent.id if parent else None) > 0 or parent is None)
        and (approval is not None or parent is not None)
    )

    return {
        "normalized_email": normalized_email,
        "email": parent.email if parent else (approval.email if approval else normalized_email),
        "parent_user_id": parent.id if parent else None,
        "name": parent.name if parent else None,
        "family_id": parent.family_id if parent else None,
        "family_status": family_status,
        "family_suspended_at": family_suspended_at,
        "family_suspend_reason": family_suspend_reason,
        "family_restored_at": family_restored_at,
        "family_restored_by_parent_id": family_restored_by_parent_id,
        "family_orphaned": family_orphaned,
        "user_status": user_status,
        "approval_status": approval_status,
        "source": source,
        "approved_at": approved_at,
        "revoked_at": revoked_at,
        "restored_at": restored_at,
        "restored_by_parent_id": restored_by_parent_id,
        "last_login_at": last_login_at,
        "created_at": created_at,
        "children_count": family_data["children_count"],
        "coparents_count": coparents_count,
        "registration_request_id": registration_request_id,
        "registration_request_status": registration_request_status,
        "registration_request_family_name": registration_request_family_name,
        "registration_request_message": registration_request_message,
        "is_bootstrap_admin": is_bootstrap_admin,
        "can_revoke": can_revoke,
        "can_revoke_reason": can_revoke_reason,
        "can_restore": can_restore,
        "can_suspend_family": can_suspend_family,
        "can_restore_family": can_restore_family,
        "google_sub_masked": _mask_google_sub(parent.google_sub) if parent else None,
    }


def _load_user_contexts(db: Session) -> list[dict[str, Any]]:
    parents = db.query(models.ParentUser).all()
    approvals = db.query(models.ApprovedParentEmail).all()
    requests = (
        db.query(models.RegistrationRequest)
        .order_by(models.RegistrationRequest.created_at.desc())
        .all()
    )
    invites = (
        db.query(models.FamilyInvite)
        .filter(models.FamilyInvite.accepted_at.is_not(None))
        .order_by(models.FamilyInvite.accepted_at.desc())
        .all()
    )

    parent_map = { _normalized_email(parent.email): parent for parent in parents }
    approval_map = { _normalized_email(approval.normalized_email or approval.email): approval for approval in approvals }
    request_map = _latest_by_email(requests, lambda row: row.email)
    invite_map = _latest_by_email(invites, lambda row: row.email)

    candidate_emails = set(parent_map) | set(approval_map)
    records: list[dict[str, Any]] = []

    for normalized_email in sorted(candidate_emails):
        parent = parent_map.get(normalized_email)
        approval = approval_map.get(normalized_email)
        registration_request = request_map.get(normalized_email)
        accepted_invite = invite_map.get(normalized_email)
        records.append(
            _build_user_record(
                db,
                normalized_email=normalized_email,
                parent=parent,
                approval=approval,
                registration_request=registration_request,
                accepted_invite=accepted_invite,
            )
        )

    return records


def _matches_status_filter(record: dict[str, Any], status_filter: str | None) -> bool:
    if not status_filter or status_filter == "all":
        return True

    value = status_filter.lower()
    if value in {"active", "revoked", "bootstrap", "suspended"}:
        return record["user_status"] == value
    if value == "invited":
        return record["source"] == "invite"
    if value == "registration-approved":
        return record["source"] in {"registration_request", "manual_admin"}
    if value == "approved-only":
        return record["approval_status"] == "active" and record["parent_user_id"] is None
    return record["user_status"] == value


def _matches_source_filter(record: dict[str, Any], source_filter: str | None) -> bool:
    if not source_filter or source_filter == "all":
        return True
    return (record.get("source") or "") == source_filter.lower()


def _matches_family_status_filter(record: dict[str, Any], family_status_filter: str | None) -> bool:
    if not family_status_filter or family_status_filter == "all":
        return True
    return (record.get("family_status") or "") == family_status_filter.lower()


def _matches_search(record: dict[str, Any], search: str | None) -> bool:
    if not search:
        return True
    needle = search.strip().lower()
    if not needle:
        return True

    haystack = [
        record.get("email"),
        record.get("normalized_email"),
        record.get("name"),
        str(record.get("family_id")) if record.get("family_id") is not None else None,
        record.get("registration_request_family_name"),
        record.get("registration_request_message"),
        record.get("source"),
        record.get("approval_status"),
        record.get("user_status"),
        record.get("family_status"),
    ]
    return any(needle in str(value).lower() for value in haystack if value is not None)


def _sort_value(record: dict[str, Any], sort_by: str) -> Any:
    if sort_by in {"email", "name", "source", "approval_status", "user_status", "family_status"}:
        value = record.get(sort_by)
        return (value or "").lower()
    if sort_by in {"family_id", "children_count", "coparents_count"}:
        return record.get(sort_by) if record.get(sort_by) is not None else -1
    if sort_by in {
        "created_at",
        "last_login_at",
        "approved_at",
        "revoked_at",
        "restored_at",
        "family_suspended_at",
        "family_restored_at",
    }:
        value = record.get(sort_by)
        return value.timestamp() if value else float("-inf")
    return record.get("created_at").timestamp() if record.get("created_at") else float("-inf")


def _paginate_records(
    records: list[dict[str, Any]],
    page: int,
    page_size: int,
    sort_by: str,
    sort_dir: str,
) -> tuple[list[dict[str, Any]], int, int]:
    reverse = sort_dir.lower() != "asc"
    sorted_records = sorted(records, key=lambda record: _sort_value(record, sort_by), reverse=reverse)
    total = len(sorted_records)
    total_pages = max(1, ceil(total / page_size)) if total else 1
    start = (page - 1) * page_size
    end = start + page_size
    return sorted_records[start:end], total, total_pages


def _load_admin_user_record(db: Session, normalized_email: str) -> dict[str, Any]:
    parent = auth.get_parent_by_email(db, normalized_email)
    approval = auth.get_approval_by_email(db, normalized_email)
    registration_request = (
        db.query(models.RegistrationRequest)
        .filter(models.RegistrationRequest.normalized_email == normalized_email)
        .order_by(models.RegistrationRequest.created_at.desc())
        .first()
    )
    accepted_invite = (
        db.query(models.FamilyInvite)
        .filter(
            func.lower(models.FamilyInvite.email) == normalized_email,
            models.FamilyInvite.accepted_at.is_not(None),
        )
        .order_by(models.FamilyInvite.accepted_at.desc())
        .first()
    )

    if not parent and not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return _build_user_record(
        db,
        normalized_email=normalized_email,
        parent=parent,
        approval=approval,
        registration_request=registration_request,
        accepted_invite=accepted_invite,
    )


def _ensure_not_bootstrap(record: dict[str, Any]) -> None:
    if record["is_bootstrap_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap admin accounts cannot be modified from this screen.",
        )


def _ensure_revoke_allowed(record: dict[str, Any]) -> None:
    _ensure_not_bootstrap(record)
    if record["parent_user_id"] is None and record["approval_status"] != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not currently active")

    if record["family_id"] is not None and record["family_status"] == "active" and record["can_revoke_reason"] == "only_active_parent":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke the only active parent for this family. Suspend the family instead if you want to pause the whole account.",
        )

    if record["user_status"] != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not currently active")


def _ensure_restore_allowed(record: dict[str, Any]) -> None:
    _ensure_not_bootstrap(record)
    if not record["can_restore"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not revoked")


def _apply_parent_revoke(
    db: Session,
    record: dict[str, Any],
    current_admin: models.ParentUser,
    revoke_reason: str | None,
) -> None:
    now = _now()
    parent = auth.get_parent_by_email(db, record["normalized_email"])
    approval = auth.get_approval_by_email(db, record["normalized_email"])

    if parent:
        parent.status = "revoked"
        parent.revoked_at = now
        parent.revoked_by_parent_id = current_admin.id
        parent.revoke_reason = revoke_reason

    if approval:
        approval.status = "revoked"
        approval.revoked_at = now
        approval.revoked_by_parent_id = current_admin.id
        approval.revoke_reason = revoke_reason

    db.commit()


def _apply_parent_restore(
    db: Session,
    record: dict[str, Any],
    current_admin: models.ParentUser,
) -> None:
    now = _now()
    parent = auth.get_parent_by_email(db, record["normalized_email"])
    approval = auth.get_approval_by_email(db, record["normalized_email"])

    if parent:
        parent.status = "active"
        parent.restored_at = now
        parent.restored_by_parent_id = current_admin.id

    if approval:
        approval.status = "active"
        approval.restored_at = now
        approval.restored_by_parent_id = current_admin.id

    db.commit()


def _family_detail(db: Session, family_id: int) -> schemas.AdminFamilySummary:
    family_summary = _family_summary(db, family_id)
    family = family_summary["family"]
    if not family:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")

    return schemas.AdminFamilySummary(
        family_id=family.id,
        status=(family.status or "active"),
        suspended_at=family.suspended_at,
        suspend_reason=family.suspend_reason,
        restored_at=family.restored_at,
        restored_by_parent_id=family.restored_by_parent_id,
        parent_count=family_summary["parent_count"],
        active_parent_count=family_summary["active_parent_count"],
        child_count=family_summary["children_count"],
    )


@router.get("/registration-requests", response_model=list[schemas.RegistrationRequest])
async def list_registration_requests(
    db: Session = Depends(get_db),
    current_admin: models.ParentUser = Depends(auth.get_current_admin),
):
    return db.query(models.RegistrationRequest).order_by(models.RegistrationRequest.created_at.desc()).all()


@router.post("/registration-requests/{request_id}/approve", response_model=schemas.RegistrationRequest)
async def approve_registration_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_admin: models.ParentUser = Depends(auth.get_current_admin),
):
    reg_request = db.query(models.RegistrationRequest).filter(models.RegistrationRequest.id == request_id).first()
    if not reg_request:
        raise HTTPException(status_code=404, detail="Registration request not found")

    if reg_request.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {reg_request.status}")

    reg_request.status = "approved"
    reg_request.approved_at = _now()
    reg_request.approved_by_parent_id = current_admin.id

    approved_email = db.query(models.ApprovedParentEmail).filter(
        models.ApprovedParentEmail.normalized_email == reg_request.normalized_email
    ).first()

    if approved_email:
        approved_email.status = "active"
        approved_email.approved_at = _now()
        approved_email.approved_by_parent_id = current_admin.id
        approved_email.source = "registration_request"
        approved_email.restored_at = _now()
        approved_email.restored_by_parent_id = current_admin.id
    else:
        approved_email = models.ApprovedParentEmail(
            email=reg_request.email,
            normalized_email=reg_request.normalized_email,
            approved_by_parent_id=current_admin.id,
            source="registration_request",
            status="active",
            restored_at=_now(),
            restored_by_parent_id=current_admin.id,
        )
        db.add(approved_email)

    parent = auth.get_parent_by_email(db, reg_request.normalized_email)
    if parent:
        parent.status = "active"
        parent.restored_at = _now()
        parent.restored_by_parent_id = current_admin.id

    db.commit()
    db.refresh(reg_request)

    mailer.send_approval_email(reg_request.email, reg_request.name)
    return reg_request


@router.post("/registration-requests/{request_id}/reject", response_model=schemas.RegistrationRequest)
async def reject_registration_request(
    request_id: int,
    review_data: schemas.RegistrationRequestReview,
    db: Session = Depends(get_db),
    current_admin: models.ParentUser = Depends(auth.get_current_admin),
):
    reg_request = db.query(models.RegistrationRequest).filter(models.RegistrationRequest.id == request_id).first()
    if not reg_request:
        raise HTTPException(status_code=404, detail="Registration request not found")

    if reg_request.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {reg_request.status}")

    reg_request.status = "rejected"
    reg_request.rejected_at = _now()
    reg_request.rejection_reason = review_data.rejection_reason

    db.commit()
    db.refresh(reg_request)
    return reg_request


@router.get("/users", response_model=schemas.AdminUsersResponse)
async def list_admin_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    source: Optional[str] = Query(None),
    family_status: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    db: Session = Depends(get_db),
    current_admin: models.ParentUser = Depends(auth.get_current_admin),
):
    records = _load_user_contexts(db)

    filtered = [
        record
        for record in records
        if _matches_search(record, search)
        and _matches_status_filter(record, status_filter)
        and _matches_source_filter(record, source)
        and _matches_family_status_filter(record, family_status)
    ]

    allowed_sort_fields = {
        "created_at",
        "last_login_at",
        "email",
        "name",
        "family_id",
        "status",
        "user_status",
        "source",
        "approval_status",
        "family_status",
        "children_count",
        "coparents_count",
    }
    sort_field = "user_status" if sort_by == "status" else (sort_by if sort_by in allowed_sort_fields else "created_at")
    page_items, total, total_pages = _paginate_records(filtered, page, page_size, sort_field, sort_dir)

    return schemas.AdminUsersResponse(
        items=[schemas.AdminUserRecord.model_validate(record) for record in page_items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/users/{normalized_email}", response_model=schemas.AdminUserRecord)
async def get_admin_user(
    normalized_email: str,
    db: Session = Depends(get_db),
    current_admin: models.ParentUser = Depends(auth.get_current_admin),
):
    record = _load_admin_user_record(db, _normalized_email(normalized_email))
    return schemas.AdminUserRecord.model_validate(record)


@router.post("/users/{normalized_email}/revoke", response_model=schemas.AdminUserRecord)
async def revoke_admin_user(
    normalized_email: str,
    payload: schemas.AdminAccessActionRequest,
    db: Session = Depends(get_db),
    current_admin: models.ParentUser = Depends(auth.get_current_admin),
):
    record = _load_admin_user_record(db, _normalized_email(normalized_email))
    _ensure_revoke_allowed(record)
    _apply_parent_revoke(db, record, current_admin, payload.revoke_reason)
    updated = _load_admin_user_record(db, record["normalized_email"])
    return schemas.AdminUserRecord.model_validate(updated)


@router.post("/users/{normalized_email}/restore", response_model=schemas.AdminUserRecord)
async def restore_admin_user(
    normalized_email: str,
    db: Session = Depends(get_db),
    current_admin: models.ParentUser = Depends(auth.get_current_admin),
):
    record = _load_admin_user_record(db, _normalized_email(normalized_email))
    _ensure_restore_allowed(record)
    _apply_parent_restore(db, record, current_admin)
    updated = _load_admin_user_record(db, record["normalized_email"])
    return schemas.AdminUserRecord.model_validate(updated)


@router.get("/families/{family_id}", response_model=schemas.AdminFamilySummary)
async def get_admin_family(
    family_id: int,
    db: Session = Depends(get_db),
    current_admin: models.ParentUser = Depends(auth.get_current_admin),
):
    return _family_detail(db, family_id)


@router.post("/families/{family_id}/suspend", response_model=schemas.AdminFamilySummary)
async def suspend_admin_family(
    family_id: int,
    payload: schemas.AdminFamilyActionRequest,
    db: Session = Depends(get_db),
    current_admin: models.ParentUser = Depends(auth.get_current_admin),
):
    family_summary = _family_summary(db, family_id)
    family = family_summary["family"]
    if not family:
        raise HTTPException(status_code=404, detail="Family not found")

    if (family.status or "active") == "suspended":
        raise HTTPException(status_code=400, detail="Family is already suspended")

    family.status = "suspended"
    family.suspended_at = _now()
    family.suspended_by_parent_id = current_admin.id
    family.suspend_reason = payload.suspend_reason
    db.commit()
    return _family_detail(db, family_id)


@router.post("/families/{family_id}/restore", response_model=schemas.AdminFamilySummary)
async def restore_admin_family(
    family_id: int,
    db: Session = Depends(get_db),
    current_admin: models.ParentUser = Depends(auth.get_current_admin),
):
    family_summary = _family_summary(db, family_id)
    family = family_summary["family"]
    if not family:
        raise HTTPException(status_code=404, detail="Family not found")

    if (family.status or "active") != "suspended":
        raise HTTPException(status_code=400, detail="Family is not suspended")

    family.status = "active"
    family.restored_at = _now()
    family.restored_by_parent_id = current_admin.id
    db.commit()
    return _family_detail(db, family_id)

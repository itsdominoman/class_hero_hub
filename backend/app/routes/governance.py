from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from .. import invite_tokens
from ..database import get_db
from ..models_school import Membership, School, SchoolSystemOwnerEvent, StaffInvite, User
from ..school_governance import (
    GovernanceConflict,
    GovernanceForbidden,
    owner_state,
    require_owner,
    transfer_owner,
)
from ..school_scope import require_school_role, write_audit
from ..staff_invite_service import issue_staff_invite


router = APIRouter(dependencies=[Depends(require_school_role("school_admin"))])


class TransferRequest(BaseModel):
    target_membership_id: int
    confirmation_membership_id: int
    reason: str = Field(min_length=8, max_length=2000)


class GovernanceInviteRequest(BaseModel):
    email: EmailStr
    role: Literal["teacher", "school_admin"]
    reason: str = Field(min_length=8, max_length=1000)


class StaffStatusRequest(BaseModel):
    status: Literal["active", "inactive"]
    reason: str = Field(min_length=8, max_length=1000)


class AddRoleRequest(BaseModel):
    role: Literal["teacher", "school_admin"]
    reason: str = Field(min_length=8, max_length=1000)


def _error(exc: Exception) -> None:
    if isinstance(exc, GovernanceForbidden):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, GovernanceConflict):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    raise exc


def _member_payload(membership: Membership, user: User) -> dict:
    return {
        "membership_id": membership.id,
        "display_name": user.name,
        "display_name_ar": user.name_ar,
        "role": membership.role,
        "membership_status": membership.status,
        "user_status": user.status,
        "created_at": membership.created_at,
    }


@router.get("/governance")
def governance_summary(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    state = owner_state(db, school_id=membership.school_id, record_recovery=True)
    staff_rows = (
        db.query(Membership, User)
        .join(User, User.id == Membership.user_id)
        .filter(
            Membership.school_id == membership.school_id,
            Membership.role.in_(("school_admin", "teacher")),
        )
        .order_by(User.name, Membership.role, Membership.id)
        .all()
    )
    history = (
        db.query(SchoolSystemOwnerEvent)
        .filter(SchoolSystemOwnerEvent.school_id == membership.school_id)
        .order_by(SchoolSystemOwnerEvent.occurred_at.desc(), SchoolSystemOwnerEvent.id.desc())
        .limit(50)
        .all()
    )
    return {
        "terminology": "System Owner",
        "meaning": "The school-nominated operational lead for Class Hero Hub; this does not imply principal or legal ownership.",
        "recovery_required": state.recovery_required,
        "is_current_owner": bool(state.row and state.row.membership_id == membership.id and not state.recovery_required),
        "owner": _member_payload(state.membership, state.user) if state.membership and state.user else None,
        "owner_version": state.row.owner_version if state.row else None,
        "owner_since": state.row.owner_since if state.row else None,
        "staff": [_member_payload(row, user) for row, user in staff_rows],
        "history": [
            {
                "event_id": str(row.event_id),
                "action": row.action,
                "previous_membership_id": row.previous_membership_id,
                "new_membership_id": row.new_membership_id,
                "actor_kind": row.actor_kind,
                "reason": row.reason,
                "owner_version": row.owner_version,
                "occurred_at": row.occurred_at,
            }
            for row in history
        ],
        "recovery_guidance": "If the current owner is inactive, a platform administrator must perform an audited emergency recovery to another active school administrator.",
    }


@router.post("/governance/transfer")
def transfer(
    payload: TransferRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    try:
        row = transfer_owner(
            db,
            actor_membership=membership,
            target_membership_id=payload.target_membership_id,
            confirmation_membership_id=payload.confirmation_membership_id,
            reason=payload.reason,
        )
    except (GovernanceConflict, GovernanceForbidden) as exc:
        _error(exc)
    write_audit(
        db,
        membership.user_id,
        "school.system_owner.transferred",
        row,
        {"new_membership_id": row.membership_id, "reason": payload.reason.strip(), "owner_version": row.owner_version},
        school_id=membership.school_id,
    )
    db.commit()
    return {"status": "transferred", "membership_id": row.membership_id, "owner_version": row.owner_version}


@router.post("/governance/invites", status_code=status.HTTP_201_CREATED)
def create_invite(
    payload: GovernanceInviteRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    try:
        require_owner(db, membership)
    except (GovernanceConflict, GovernanceForbidden) as exc:
        _error(exc)
    school = db.query(School).filter(School.id == membership.school_id).one()
    actor = db.query(User).filter(User.id == membership.user_id).one()
    row, _token, warning = issue_staff_invite(
        db,
        school=school,
        email=str(payload.email),
        actor=actor,
        role=payload.role,
    )
    write_audit(
        db,
        membership.user_id,
        "school.staff_invite.created",
        row,
        {"role": payload.role, "reason": payload.reason.strip()},
        school_id=membership.school_id,
    )
    db.commit()
    result = {"id": row.id, "role": row.role, "status": row.send_status, "expires_at": row.expires_at}
    if warning:
        result["warning"] = warning
    return result


@router.post("/governance/staff/{target_membership_id}/status")
def set_staff_status(
    target_membership_id: int,
    payload: StaffStatusRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    try:
        owner = require_owner(db, membership)
    except (GovernanceConflict, GovernanceForbidden) as exc:
        _error(exc)
    target = (
        db.query(Membership)
        .filter(Membership.id == target_membership_id, Membership.school_id == membership.school_id)
        .with_for_update()
        .first()
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Staff membership not found")
    if target.id == owner.membership_id and payload.status != "active":
        raise HTTPException(status_code=409, detail="Transfer System Owner before deactivating this membership")
    target.status = payload.status
    if payload.status == "active":
        target.revoked_at = None
        target.revoked_by_user_id = None
    else:
        target.revoked_at = invite_tokens.now_utc()
        target.revoked_by_user_id = membership.user_id
    write_audit(
        db,
        membership.user_id,
        "school.staff_access.updated",
        target,
        {"status": payload.status, "reason": payload.reason.strip()},
        school_id=membership.school_id,
    )
    db.commit()
    return {"membership_id": target.id, "status": target.status}


@router.post("/governance/staff/{source_membership_id}/roles", status_code=status.HTTP_201_CREATED)
def add_staff_role(
    source_membership_id: int,
    payload: AddRoleRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    try:
        require_owner(db, membership)
    except (GovernanceConflict, GovernanceForbidden) as exc:
        _error(exc)
    source = (
        db.query(Membership)
        .filter(Membership.id == source_membership_id, Membership.school_id == membership.school_id)
        .first()
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Staff membership not found")
    target = (
        db.query(Membership)
        .filter(
            Membership.school_id == membership.school_id,
            Membership.user_id == source.user_id,
            Membership.role == payload.role,
        )
        .first()
    )
    if target is None:
        target = Membership(
            school_id=membership.school_id,
            user_id=source.user_id,
            role=payload.role,
            status="active",
            created_by_user_id=membership.user_id,
        )
        db.add(target)
        db.flush()
    else:
        target.status = "active"
        target.revoked_at = None
        target.revoked_by_user_id = None
    write_audit(
        db,
        membership.user_id,
        "school.staff_role.assigned",
        target,
        {"role": payload.role, "reason": payload.reason.strip()},
        school_id=membership.school_id,
    )
    db.commit()
    db.refresh(target)
    return {"membership_id": target.id, "role": target.role, "status": target.status}

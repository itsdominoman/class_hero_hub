from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import auth, invite_tokens
from ..database import get_db
from ..mailer import send_staff_invite
from ..models_school import Membership, School, SchoolMessagingPolicy, StaffInvite, Student, User
from ..school_scope import require_platform_admin, write_audit
from ..school_governance import GovernanceConflict, bootstrap_system_owner, platform_recover_owner
from ..staff_invite_service import issue_staff_invite

router = APIRouter(dependencies=[Depends(require_platform_admin)])
invite_router = APIRouter()
SCHOOL_ADMIN_ROLE = "school_admin"
TEACHER_ROLE = "teacher"


class CreateSchoolRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    name_ar: str | None = Field(default=None, max_length=200)
    timezone: str = Field(default="Asia/Muscat", min_length=1, max_length=80)
    locale_default: str = Field(default="en", pattern="^(en|ar)$")
    admin_email: EmailStr


class InviteRequest(BaseModel):
    email: EmailStr


class ReasonRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class OwnerRecoveryRequest(BaseModel):
    target_membership_id: int
    reason: str = Field(min_length=8, max_length=2000)


class ExchangeInviteRequest(BaseModel):
    token: str = Field(min_length=1)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_email(email: str) -> str:
    return auth.normalize_email(email)


def _slug_base(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "school"


def _unique_school_slug(db: Session, name: str) -> str:
    base = _slug_base(name)
    slug = base
    suffix = 2
    while db.query(School).filter(School.slug == slug).first() is not None:
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def _issue_staff_invite(db: Session, school: School, email: str, actor: User, role: str = SCHOOL_ADMIN_ROLE) -> tuple[StaffInvite, str, str | None]:
    return issue_staff_invite(db, school=school, email=email, actor=actor, role=role, send=send_staff_invite)


def _role_counts(db: Session, school_id: int) -> dict[str, int]:
    rows = (
        db.query(Membership.role, func.count(Membership.id))
        .filter(
            Membership.school_id == school_id,
            Membership.status == "active",
            Membership.revoked_at.is_(None),
        )
        .group_by(Membership.role)
        .all()
    )
    return {role: count for role, count in rows}


def _invite_status(staff_invite: StaffInvite) -> str:
    if staff_invite.revoked_at is not None:
        return "revoked"
    if staff_invite.accepted_at is not None:
        return "accepted"
    expires_at = invite_tokens.as_utc_aware(staff_invite.expires_at)
    if expires_at is None or expires_at <= invite_tokens.now_utc():
        return "expired"
    return "pending"


def _invite_payload(staff_invite: StaffInvite) -> dict[str, Any]:
    return {
        "id": staff_invite.id,
        "school_id": staff_invite.school_id,
        "email": staff_invite.email,
        "role": staff_invite.role,
        "created_at": staff_invite.created_at,
        "expires_at": staff_invite.expires_at,
        "revoked_at": staff_invite.revoked_at,
        "accepted_at": staff_invite.accepted_at,
        "accepted_by_user_id": staff_invite.accepted_by_user_id,
        "send_status": staff_invite.send_status,
        "last_send_error": staff_invite.last_send_error,
        "status": _invite_status(staff_invite),
    }


def _school_payload(db: Session, school: School, *, include_invites: bool = False) -> dict[str, Any]:
    payload = {
        "id": school.id,
        "name": school.name,
        "name_ar": school.name_ar,
        "slug": school.slug,
        "timezone": school.timezone,
        "locale_default": school.locale_default,
        "status": school.status,
        "created_at": school.created_at,
        "suspended_at": school.suspended_at,
        "suspend_reason": school.suspend_reason,
        "counts": {
            "memberships_by_role": _role_counts(db, school.id),
            "students": db.query(Student).filter(Student.school_id == school.id, Student.status != "archived").count(),
        },
        "setup_flags": {
            "has_school_admin": db.query(Membership)
            .filter(
                Membership.school_id == school.id,
                Membership.role == SCHOOL_ADMIN_ROLE,
                Membership.status == "active",
                Membership.revoked_at.is_(None),
            )
            .first()
            is not None,
            "students_configured": db.query(Student).filter(Student.school_id == school.id, Student.status != "archived").first() is not None,
        },
    }
    if include_invites:
        invites = (
            db.query(StaffInvite)
            .filter(StaffInvite.school_id == school.id)
            .order_by(StaffInvite.created_at.desc(), StaffInvite.id.desc())
            .all()
        )
        payload["invites"] = [_invite_payload(invite) for invite in invites]
    return payload


def _get_school_or_404(db: Session, school_id: int) -> School:
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")
    return school


@router.post("/schools", status_code=status.HTTP_201_CREATED)
def create_school(
    payload: CreateSchoolRequest,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    school = School(
        name=payload.name.strip(),
        name_ar=_clean_text(payload.name_ar),
        slug=_unique_school_slug(db, payload.name),
        timezone=payload.timezone.strip(),
        locale_default=payload.locale_default,
        status="pending_setup",
    )
    db.add(school)
    db.flush()
    db.add(SchoolMessagingPolicy(school_id=school.id))
    db.commit()
    db.refresh(school)
    staff_invite, _raw_token, warning = _issue_staff_invite(db, school, str(payload.admin_email), current_user)
    write_audit(
        db,
        current_user,
        "platform.school.created",
        school,
        {"admin_email": staff_invite.email, "invite_id": staff_invite.id},
        school_id=school.id,
    )
    db.commit()
    response = _school_payload(db, school, include_invites=True)
    if warning:
        response["warning"] = warning
    return response


@router.get("/schools")
def list_schools(
    db: Session = Depends(get_db),
):
    schools = db.query(School).order_by(School.created_at.desc(), School.id.desc()).all()
    return [_school_payload(db, school) for school in schools]


@router.get("/schools/{school_id}")
def get_school(
    school_id: int,
    db: Session = Depends(get_db),
):
    return _school_payload(db, _get_school_or_404(db, school_id), include_invites=True)


@router.post("/schools/{school_id}/suspend")
def suspend_school(
    school_id: int,
    payload: ReasonRequest,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    school = _get_school_or_404(db, school_id)
    school.status = "suspended"
    school.suspended_at = invite_tokens.now_utc()
    school.suspended_by_user_id = current_user.id
    school.suspend_reason = payload.reason.strip()
    db.commit()
    db.refresh(school)
    write_audit(
        db,
        current_user,
        "platform.school.suspended",
        school,
        {"reason": school.suspend_reason},
        school_id=school.id,
    )
    db.commit()
    return _school_payload(db, school, include_invites=True)


@router.post("/schools/{school_id}/reactivate")
def reactivate_school(
    school_id: int,
    payload: ReasonRequest,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    school = _get_school_or_404(db, school_id)
    previous_reason = school.suspend_reason
    school.status = "active"
    school.suspended_at = None
    school.suspended_by_user_id = None
    school.suspend_reason = None
    db.commit()
    db.refresh(school)
    write_audit(
        db,
        current_user,
        "platform.school.reactivated",
        school,
        {"reason": payload.reason.strip(), "previous_suspend_reason": previous_reason},
        school_id=school.id,
    )
    db.commit()
    return _school_payload(db, school, include_invites=True)


@router.post("/schools/{school_id}/invites", status_code=status.HTTP_201_CREATED)
def create_school_invite(
    school_id: int,
    payload: InviteRequest,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    school = _get_school_or_404(db, school_id)
    staff_invite, _raw_token, warning = _issue_staff_invite(db, school, str(payload.email), current_user)
    write_audit(
        db,
        current_user,
        "platform.staff_invite.created",
        staff_invite,
        {"email": staff_invite.email, "role": staff_invite.role},
        school_id=school.id,
    )
    db.commit()
    response = _invite_payload(staff_invite)
    if warning:
        response["warning"] = warning
    return response


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invite(
    invite_id: int,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    staff_invite = db.query(StaffInvite).filter(StaffInvite.id == invite_id).first()
    if not staff_invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    if staff_invite.accepted_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invite already accepted")
    if staff_invite.revoked_at is None:
        staff_invite.revoked_at = invite_tokens.now_utc()
        db.commit()
        write_audit(
            db,
            current_user,
            "platform.staff_invite.revoked",
            staff_invite,
            {"email": staff_invite.email, "role": staff_invite.role},
            school_id=staff_invite.school_id,
        )
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@invite_router.post("/exchange")
def exchange_staff_invite(
    payload: ExchangeInviteRequest,
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    invite_tokens.register_exchange_attempt(request)
    token_hash = invite_tokens.hash_token(payload.token.strip())
    staff_invite = db.query(StaffInvite).filter(StaffInvite.token_hash == token_hash).first()
    current = invite_tokens.now_utc()

    if not staff_invite:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired invite")
    if staff_invite.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite revoked")
    if staff_invite.accepted_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite already used")
    expires_at = invite_tokens.as_utc_aware(staff_invite.expires_at)
    if expires_at is None or expires_at <= current:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite expired")
    if _normalize_email(current_user.email) != _normalize_email(staff_invite.email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This invite was issued for a different email address")

    school = _get_school_or_404(db, staff_invite.school_id)
    if (school.status or "").lower() == "suspended":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This school account is currently suspended.")
    membership = (
        db.query(Membership)
        .filter(
            Membership.school_id == school.id,
            Membership.user_id == current_user.id,
            Membership.role == staff_invite.role,
        )
        .first()
    )
    if membership is None:
        membership = Membership(
            school_id=school.id,
            user_id=current_user.id,
            role=staff_invite.role,
            status="active",
            created_by_user_id=staff_invite.invited_by_user_id,
        )
        db.add(membership)
    else:
        membership.status = "active"
        membership.revoked_at = None
        membership.revoked_by_user_id = None

    staff_invite.accepted_at = current
    staff_invite.accepted_by_user_id = current_user.id
    if staff_invite.role == SCHOOL_ADMIN_ROLE and (school.status or "").lower() == "pending_setup":
        school.status = "active"

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Membership already exists")

    db.refresh(membership)
    db.refresh(staff_invite)
    if staff_invite.role == SCHOOL_ADMIN_ROLE:
        try:
            bootstrap_system_owner(
                db,
                school=school,
                membership=membership,
                actor_user_id=current_user.id,
            )
        except GovernanceConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    write_audit(
        db,
        current_user,
        "staff_invite.accepted",
        staff_invite,
        {"email": staff_invite.email, "role": staff_invite.role, "membership_id": membership.id},
        school_id=school.id,
    )
    db.commit()
    return {
        "status": "accepted",
        "school": {"id": school.id, "name": school.name, "status": school.status},
        "membership": {"id": membership.id, "role": membership.role},
        "landing_path": "/teach" if membership.role == TEACHER_ROLE else "/school",
    }


@router.post("/schools/{school_id}/system-owner/recover")
def recover_system_owner(
    school_id: int,
    payload: OwnerRecoveryRequest,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    _get_school_or_404(db, school_id)
    try:
        row = platform_recover_owner(
            db,
            school_id=school_id,
            target_membership_id=payload.target_membership_id,
            actor_user_id=current_user.id,
            reason=payload.reason,
        )
    except GovernanceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    write_audit(
        db,
        current_user,
        "platform.system_owner.recovered",
        row,
        {
            "new_membership_id": row.membership_id,
            "owner_version": row.owner_version,
            "reason": payload.reason.strip(),
        },
        school_id=school_id,
    )
    db.commit()
    return {"status": "recovered", "membership_id": row.membership_id, "owner_version": row.owner_version}

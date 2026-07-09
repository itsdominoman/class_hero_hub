from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from .. import auth, invite_tokens
from ..database import get_db
from ..models_school import ClassSection, Enrolment, GuardianInvite, GuardianLink, Membership, School, Student, StudentGuardianContact, User
from ..school_scope import open_interval_expression, write_audit
from ..security import BoundedInMemoryRateLimiter, get_client_ip_from_scope

router = APIRouter()

JOIN_RATE_LIMITER = BoundedInMemoryRateLimiter(60, 10)
GENERIC_JOIN_ERROR = "This code is not valid or has expired. Please contact the school office."


class ConfirmRequest(BaseModel):
    code: str = Field(min_length=1)
    relationship: str = Field(default="guardian")

    @field_validator("relationship")
    @classmethod
    def validate_relationship(cls, value: str) -> str:
        cleaned = (value or "").strip().lower()
        if cleaned not in {"mother", "father", "guardian", "other"}:
            raise ValueError("relationship must be mother, father, guardian, or other")
        return cleaned


def _rate_limit(request: Request) -> None:
    client_ip = get_client_ip_from_scope(request.scope) or "unknown"
    if not JOIN_RATE_LIMITER.allow(client_ip, now=invite_tokens.now_utc()):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Please try again in a minute.")


def _generic_error() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=GENERIC_JOIN_ERROR)


def _valid_invite(db: Session, code: str) -> GuardianInvite:
    normalized = invite_tokens.normalize_short_code(code)
    if len(normalized) != 8:
        raise _generic_error()
    invite = db.query(GuardianInvite).filter(GuardianInvite.token_hash == invite_tokens.hash_token(normalized)).first()
    if not invite:
        raise _generic_error()
    if invite.revoked_at is not None or invite.claimed_at is not None:
        raise _generic_error()
    expires_at = invite_tokens.as_utc_aware(invite.expires_at)
    if expires_at is None or expires_at <= invite_tokens.now_utc():
        raise _generic_error()
    school = db.query(School).filter(School.id == invite.school_id).first()
    student = db.query(Student).filter(Student.id == invite.student_id, Student.school_id == invite.school_id).first()
    if not school or not student or (school.status or "").lower() == "suspended" or student.status != "active":
        raise _generic_error()
    return invite


def _current_class_name(db: Session, school_id: int, student_id: int) -> str | None:
    enrolment = (
        db.query(Enrolment)
        .filter(
            Enrolment.school_id == school_id,
            Enrolment.student_id == student_id,
            Enrolment.class_section_id.is_not(None),
            *open_interval_expression(Enrolment),
        )
        .order_by(Enrolment.id.desc())
        .first()
    )
    if not enrolment:
        return None
    section = db.query(ClassSection).filter(ClassSection.id == enrolment.class_section_id, ClassSection.school_id == school_id).first()
    return section.name if section else None


def _success_payload(db: Session, link: GuardianLink, student: Student) -> dict[str, Any]:
    return {
        "status": "linked",
        "student_first_name": student.preferred_name or student.first_name,
        "class_section_name": _current_class_name(db, student.school_id, student.id),
        "link_id": link.id,
    }


def _ensure_guardian_membership(db: Session, school_id: int, user_id: int, created_by_user_id: int | None) -> Membership:
    membership = (
        db.query(Membership)
        .filter(Membership.school_id == school_id, Membership.user_id == user_id, Membership.role == "guardian")
        .first()
    )
    if membership:
        membership.status = "active"
        membership.revoked_at = None
        membership.revoked_by_user_id = None
        return membership
    membership = Membership(
        school_id=school_id,
        user_id=user_id,
        role="guardian",
        status="active",
        created_by_user_id=created_by_user_id,
    )
    db.add(membership)
    db.flush()
    return membership


@router.get("/guardian")
def preview_guardian_join(code: str | None = None, c: str | None = None, request: Request = None, db: Session = Depends(get_db)):
    _rate_limit(request)
    invite = _valid_invite(db, code or c or "")
    school = db.query(School).filter(School.id == invite.school_id).one()
    return {
        "school_name": school.name,
        "school_name_ar": school.name_ar,
        "auth_required": True,
    }


@router.get("/guardian/details")
def guardian_join_details(
    code: str | None = None,
    c: str | None = None,
    request: Request = None,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    _rate_limit(request)
    invite = _valid_invite(db, code or c or "")
    student = db.query(Student).filter(Student.id == invite.student_id, Student.school_id == invite.school_id).one()
    existing_link = (
        db.query(GuardianLink)
        .filter(
            GuardianLink.school_id == invite.school_id,
            GuardianLink.student_id == invite.student_id,
            GuardianLink.user_id == current_user.id,
            GuardianLink.status == "active",
            GuardianLink.revoked_at.is_(None),
        )
        .first()
    )
    return {
        "student_first_name": student.preferred_name or student.first_name,
        "class_section_name": _current_class_name(db, invite.school_id, invite.student_id),
        "relationship": invite.relationship or "guardian",
        "already_linked": existing_link is not None,
    }


@router.post("/guardian/confirm")
def confirm_guardian_join(
    payload: ConfirmRequest,
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    _rate_limit(request)
    normalized = invite_tokens.normalize_short_code(payload.code)
    invite = _valid_invite(db, normalized)
    student = db.query(Student).filter(Student.id == invite.student_id, Student.school_id == invite.school_id).one()

    existing_link = (
        db.query(GuardianLink)
        .filter(GuardianLink.school_id == invite.school_id, GuardianLink.student_id == invite.student_id, GuardianLink.user_id == current_user.id)
        .first()
    )
    if existing_link and existing_link.status == "active" and existing_link.revoked_at is None:
        return _success_payload(db, existing_link, student)

    contact = None
    email_matched_contact = None
    if invite.student_guardian_contact_id is not None:
        contact = (
            db.query(StudentGuardianContact)
            .filter(
                StudentGuardianContact.id == invite.student_guardian_contact_id,
                StudentGuardianContact.school_id == invite.school_id,
                StudentGuardianContact.student_id == invite.student_id,
            )
            .first()
        )
        if contact and contact.email:
            email_matched_contact = auth.normalize_email(current_user.email) == auth.normalize_email(contact.email)

    current = invite_tokens.now_utc()
    invite.claimed_at = current
    invite.claimed_by_user_id = current_user.id
    if existing_link:
        existing_link.status = "active"
        existing_link.revoked_at = None
        existing_link.revoked_by_user_id = None
        existing_link.relationship = payload.relationship
        existing_link.display_name = invite.guardian_name or (contact.name if contact else None) or current_user.name
        existing_link.source_guardian_invite_id = invite.id
        existing_link.student_guardian_contact_id = contact.id if contact else None
        existing_link.email_matched_contact = email_matched_contact
        link = existing_link
    else:
        link = GuardianLink(
            school_id=invite.school_id,
            student_id=invite.student_id,
            user_id=current_user.id,
            relationship=payload.relationship,
            display_name=invite.guardian_name or (contact.name if contact else None) or current_user.name,
            source_guardian_invite_id=invite.id,
            student_guardian_contact_id=contact.id if contact else None,
            email_matched_contact=email_matched_contact,
            status="active",
        )
        db.add(link)
        db.flush()
    _ensure_guardian_membership(db, invite.school_id, current_user.id, invite.created_by_user_id)
    if contact and contact.status == "draft":
        contact.status = "linked"
    write_audit(
        db,
        current_user.id,
        "school.guardian_invite.claimed",
        invite,
        {
            "student_id": invite.student_id,
            "guardian_link_id": link.id,
            "contact_id": contact.id if contact else None,
            "email_matched_contact": email_matched_contact,
        },
        school_id=invite.school_id,
    )
    db.commit()
    db.refresh(link)
    return _success_payload(db, link, student)

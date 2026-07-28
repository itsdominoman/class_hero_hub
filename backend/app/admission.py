from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import parse_qs, unquote, urlparse

from sqlalchemy import exists, func
from sqlalchemy.orm import Query, Session

from . import invite_tokens
from .models_school import (
    GuardianInvite,
    GuardianLink,
    Membership,
    PlatformAdmin,
    School,
    StaffInvite,
    Student,
    User,
    UserRefreshSession,
)

NOT_AUTHORISED_DETAIL = "This account is not authorised for Class Hero Hub."
STAFF_ROLES = ("school_admin", "teacher")
PENDING_STAFF_INVITE = "staff_invite"
PENDING_GUARDIAN_INVITE = "guardian_invite"


@dataclass(frozen=True)
class AdmissionContext:
    kind: str
    token_hash: str
    expires_at: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _active_school_filter():
    return func.lower(func.coalesce(School.status, "")) != "suspended"


def unauthorised_user_query(db: Session) -> Query:
    platform_admin = exists().where(
        PlatformAdmin.user_id == User.id,
        PlatformAdmin.revoked_at.is_(None),
    )
    staff_membership = exists().where(
        Membership.user_id == User.id,
        Membership.role.in_(STAFF_ROLES),
        Membership.status == "active",
        Membership.revoked_at.is_(None),
        Membership.school_id == School.id,
        _active_school_filter(),
    )
    guardian_link = exists().where(
        GuardianLink.user_id == User.id,
        GuardianLink.status == "active",
        GuardianLink.revoked_at.is_(None),
        GuardianLink.student_id == Student.id,
        GuardianLink.school_id == Student.school_id,
        GuardianLink.school_id == School.id,
        Student.status == "active",
        _active_school_filter(),
    )
    return db.query(User).filter(~platform_admin, ~staff_membership, ~guardian_link)


def has_active_entitlement(db: Session, user_id: int) -> bool:
    return (
        unauthorised_user_query(db)
        .filter(User.id == user_id)
        .first()
        is None
    )


def _valid_staff_invite(
    db: Session,
    *,
    token_hash: str,
    email: str,
    current: datetime,
) -> StaffInvite | None:
    return (
        db.query(StaffInvite)
        .join(School, School.id == StaffInvite.school_id)
        .filter(
            StaffInvite.token_hash == token_hash,
            func.lower(StaffInvite.email) == email.strip().lower(),
            StaffInvite.role.in_(STAFF_ROLES),
            StaffInvite.revoked_at.is_(None),
            StaffInvite.accepted_at.is_(None),
            StaffInvite.expires_at > current,
            _active_school_filter(),
        )
        .first()
    )


def _valid_guardian_invite(
    db: Session,
    *,
    token_hash: str,
    current: datetime,
) -> GuardianInvite | None:
    return (
        db.query(GuardianInvite)
        .join(
            Student,
            (Student.id == GuardianInvite.student_id)
            & (Student.school_id == GuardianInvite.school_id),
        )
        .join(School, School.id == GuardianInvite.school_id)
        .filter(
            GuardianInvite.token_hash == token_hash,
            GuardianInvite.revoked_at.is_(None),
            GuardianInvite.claimed_at.is_(None),
            GuardianInvite.expires_at > current,
            Student.status == "active",
            _active_school_filter(),
        )
        .first()
    )


def invite_context_for_return_path(
    db: Session,
    *,
    email: str,
    return_to: str | None,
    current: datetime | None = None,
) -> AdmissionContext | None:
    parsed = urlparse((return_to or "").strip())
    if parsed.scheme or parsed.netloc:
        return None
    now = current or _now()

    if parsed.path.startswith("/invite/"):
        raw_token = unquote(parsed.path.removeprefix("/invite/")).strip()
        if not raw_token or "/" in raw_token:
            return None
        token_hash = invite_tokens.hash_token(raw_token)
        invite = _valid_staff_invite(
            db,
            token_hash=token_hash,
            email=email,
            current=now,
        )
        if invite is not None:
            return AdmissionContext(
                kind=PENDING_STAFF_INVITE,
                token_hash=token_hash,
                expires_at=invite_tokens.as_utc_aware(invite.expires_at) or now,
            )

    if parsed.path == "/join":
        raw_code = (parse_qs(parsed.query).get("c") or [""])[0]
        normalized = invite_tokens.normalize_short_code(raw_code)
        if len(normalized) != 8:
            return None
        token_hash = invite_tokens.hash_token(normalized)
        invite = _valid_guardian_invite(db, token_hash=token_hash, current=now)
        if invite is not None:
            return AdmissionContext(
                kind=PENDING_GUARDIAN_INVITE,
                token_hash=token_hash,
                expires_at=invite_tokens.as_utc_aware(invite.expires_at) or now,
            )
    return None


def pending_session_is_valid(
    db: Session,
    session: UserRefreshSession,
    user: User,
    *,
    current: datetime | None = None,
) -> bool:
    now = current or _now()
    expires_at = invite_tokens.as_utc_aware(session.admission_expires_at)
    if (
        not session.admission_kind
        or not session.admission_token_hash
        or expires_at is None
        or expires_at <= now
    ):
        return False
    if session.admission_kind == PENDING_STAFF_INVITE:
        return (
            _valid_staff_invite(
                db,
                token_hash=session.admission_token_hash,
                email=user.email,
                current=now,
            )
            is not None
        )
    if session.admission_kind == PENDING_GUARDIAN_INVITE:
        return (
            _valid_guardian_invite(
                db,
                token_hash=session.admission_token_hash,
                current=now,
            )
            is not None
        )
    return False


def pending_session_matches(
    db: Session,
    session: UserRefreshSession,
    user: User,
    *,
    kind: str,
    raw_token: str,
) -> bool:
    normalized = (
        invite_tokens.normalize_short_code(raw_token)
        if kind == PENDING_GUARDIAN_INVITE
        else raw_token.strip()
    )
    return (
        session.admission_kind == kind
        and session.admission_token_hash is not None
        and session.admission_token_hash == invite_tokens.hash_token(normalized)
        and pending_session_is_valid(db, session, user)
    )

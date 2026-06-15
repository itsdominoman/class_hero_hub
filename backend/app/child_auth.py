from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from .database import get_db, settings
from . import auth, models
from .security import BoundedInMemoryRateLimiter, get_client_ip_from_scope

CHILD_SESSION_COOKIE = "child_session"
CHILD_SESSION_TTL = timedelta(days=30)
CHILD_INVITE_TTL = timedelta(days=1)
EXCHANGE_RATE_LIMIT_WINDOW_SECONDS = 60
EXCHANGE_RATE_LIMIT_MAX_ATTEMPTS = 20

_exchange_rate_limiter = BoundedInMemoryRateLimiter(
    EXCHANGE_RATE_LIMIT_WINDOW_SECONDS,
    EXCHANGE_RATE_LIMIT_MAX_ATTEMPTS,
)


@dataclass
class ChildSessionContext:
    session: models.ChildDeviceSession
    child: models.Child


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def _cookie_max_age(expires_at: datetime) -> int:
    aware_expires_at = _as_utc_aware(expires_at)
    if aware_expires_at is None:
        return 0
    remaining = int((aware_expires_at - now_utc()).total_seconds())
    return max(0, remaining)


def _ensure_child_family_active(db: Session, child: models.Child) -> None:
    family = child.family
    if family and (family.status or "active").lower() == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This family account is currently suspended. Please contact support@familyherohub.com.",
        )
    if family and auth.count_active_parents_in_family(db, family.id) == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This family account currently has no active parent. Please contact support@familyherohub.com.",
        )


def set_child_session_cookie(response: Response, raw_token: str, expires_at: datetime) -> None:
    response.set_cookie(
        key=CHILD_SESSION_COOKIE,
        value=raw_token,
        httponly=True,
        max_age=_cookie_max_age(expires_at),
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )


def clear_child_session_cookie(response: Response) -> None:
    response.delete_cookie(CHILD_SESSION_COOKIE, path="/")


def _revoke_active_invites(db: Session, child: models.Child, family_id: int) -> int:
    active_invites = db.query(models.ChildDeviceInvite).filter(
        models.ChildDeviceInvite.child_id == child.id,
        models.ChildDeviceInvite.family_id == family_id,
        models.ChildDeviceInvite.revoked_at.is_(None),
        models.ChildDeviceInvite.used_at.is_(None),
        models.ChildDeviceInvite.expires_at > now_utc(),
    ).all()
    revoked_count = 0
    for invite in active_invites:
        invite.revoked_at = now_utc()
        revoked_count += 1
    return revoked_count


def issue_child_device_invite(
    db: Session,
    child: models.Child,
    family_id: int,
    parent_id: int,
) -> tuple[models.ChildDeviceInvite, str]:
    _revoke_active_invites(db, child, family_id)
    raw_token = generate_token()
    invite = models.ChildDeviceInvite(
        family_id=family_id,
        child_id=child.id,
        created_by_parent_id=parent_id,
        token_hash=hash_token(raw_token),
        expires_at=now_utc() + CHILD_INVITE_TTL,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite, raw_token


def revoke_child_device_access(db: Session, child: models.Child, family_id: int) -> tuple[int, int]:
    revoked_invites = 0
    revoked_sessions = 0
    now = now_utc()

    invites = db.query(models.ChildDeviceInvite).filter(
        models.ChildDeviceInvite.child_id == child.id,
        models.ChildDeviceInvite.family_id == family_id,
        models.ChildDeviceInvite.revoked_at.is_(None),
    ).all()
    for invite in invites:
        invite.revoked_at = now
        revoked_invites += 1

    sessions = db.query(models.ChildDeviceSession).filter(
        models.ChildDeviceSession.child_id == child.id,
        models.ChildDeviceSession.family_id == family_id,
        models.ChildDeviceSession.revoked_at.is_(None),
    ).all()
    for session in sessions:
        session.revoked_at = now
        revoked_sessions += 1

    db.commit()
    return revoked_invites, revoked_sessions


def _rate_limit_exchange(request: Request) -> None:
    client_ip = get_client_ip_from_scope(request.scope) or "unknown"
    if not _exchange_rate_limiter.allow(client_ip, now=now_utc()):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many child link attempts")


def exchange_child_link(db: Session, raw_token: str) -> tuple[models.ChildDeviceInvite, models.ChildDeviceSession, str]:
    token_hash = hash_token(raw_token)
    current = now_utc()

    invite = db.query(models.ChildDeviceInvite).filter(
        models.ChildDeviceInvite.token_hash == token_hash,
    ).first()
    if not invite:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired child link")

    if invite.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired child link")
    if invite.used_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Child link already used")
    invite_expires_at = _as_utc_aware(invite.expires_at)
    if invite_expires_at is None or invite_expires_at <= current:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Child link expired")

    child = db.query(models.Child).filter(
        models.Child.id == invite.child_id,
        models.Child.family_id == invite.family_id,
        models.Child.active.is_(True),
    ).first()
    if not child:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired child link")
    _ensure_child_family_active(db, child)

    invite.used_at = current
    session_raw_token = generate_token()
    session = models.ChildDeviceSession(
        family_id=invite.family_id,
        child_id=invite.child_id,
        invite_id=invite.id,
        session_hash=hash_token(session_raw_token),
        expires_at=current + CHILD_SESSION_TTL,
        last_seen_at=current,
    )
    db.add(session)
    db.commit()
    db.refresh(invite)
    db.refresh(session)
    return invite, session, session_raw_token


def resolve_child_session(db: Session, raw_token: str) -> ChildSessionContext:
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Child session missing")

    current = now_utc()
    session = db.query(models.ChildDeviceSession).filter(
        models.ChildDeviceSession.session_hash == hash_token(raw_token),
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid child session")
    if session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid child session")
    session_expires_at = _as_utc_aware(session.expires_at)
    if session_expires_at is None or session_expires_at <= current:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Child session expired")

    child = db.query(models.Child).filter(
        models.Child.id == session.child_id,
        models.Child.family_id == session.family_id,
        models.Child.active.is_(True),
    ).first()
    if not child:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid child session")
    _ensure_child_family_active(db, child)

    session.last_seen_at = current
    db.commit()
    return ChildSessionContext(session=session, child=child)


def get_current_child_session(request: Request, db: Session = Depends(get_db)) -> ChildSessionContext:
    raw_token = request.cookies.get(CHILD_SESSION_COOKIE)
    return resolve_child_session(db, raw_token)


def get_current_child(request: Request, db: Session = Depends(get_db)) -> models.Child:
    return get_current_child_session(request, db).child


def register_exchange_attempt(request: Request) -> None:
    _rate_limit_exchange(request)

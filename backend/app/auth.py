from datetime import datetime, timedelta, timezone
from typing import Optional

import hashlib
import hmac
import httpx
import logging
import secrets
import uuid
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import get_db, settings
from .models_school import PlatformAdmin, User, UserRefreshSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
logger = logging.getLogger(__name__)


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def is_platform_admin_bootstrap_email(email: str | None) -> bool:
    allowed_emails = [normalize_email(e) for e in settings.PLATFORM_ADMIN_EMAILS.split(",")]
    return normalize_email(email) in allowed_emails


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    issued_at = datetime.now(timezone.utc)
    if expires_delta:
        expire = issued_at + expires_delta
    else:
        expire = issued_at + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": issued_at})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM)


def parent_session_cookie_max_age_seconds() -> int:
    return max(0, int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60)


def refresh_session_cookie_max_age_seconds() -> int:
    return max(0, int(settings.REFRESH_TOKEN_IDLE_DAYS) * 86400)


def _as_utc_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _legacy_access_allowed(now: datetime | None = None) -> bool:
    raw_deadline = (settings.LEGACY_ACCESS_TOKEN_ACCEPT_UNTIL or "").strip()
    if not raw_deadline:
        return settings.APP_ENV == "test"
    try:
        deadline = datetime.fromisoformat(raw_deadline.replace("Z", "+00:00"))
    except ValueError:
        logger.error("LEGACY_ACCESS_TOKEN_ACCEPT_UNTIL is not a valid ISO-8601 timestamp")
        return False
    return (now or datetime.now(timezone.utc)) <= (_as_utc_aware(deadline) or deadline)


def _refresh_signature(session_id: str, generation: int) -> str:
    message = f"refresh:{session_id}:{generation}".encode("utf-8")
    return hmac.new(settings.JWT_SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _refresh_token(session_id: str, generation: int) -> str:
    return f"{session_id}.{generation}.{_refresh_signature(session_id, generation)}"


def _refresh_token_hash(raw_token: str) -> str:
    return hmac.new(
        settings.JWT_SECRET.encode("utf-8"),
        f"refresh-hash:{raw_token}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _parse_refresh_token(raw_token: str) -> tuple[str, int] | None:
    try:
        session_id, generation_raw, supplied_signature = raw_token.split(".", 2)
        generation = int(generation_raw)
    except (AttributeError, TypeError, ValueError):
        return None
    if generation < 1 or not session_id:
        return None
    expected_signature = _refresh_signature(session_id, generation)
    if not hmac.compare_digest(supplied_signature, expected_signature):
        return None
    return session_id, generation


def refresh_session_id(raw_token: str | None) -> str | None:
    parsed = _parse_refresh_token(raw_token or "")
    return parsed[0] if parsed else None


def request_session_id(request: Request) -> str | None:
    session_id = refresh_session_id(request.cookies.get("refresh_token"))
    if session_id:
        return session_id
    token = _get_request_token(request)
    if not token:
        return None
    try:
        return decode_access_token(token).get("sid")
    except HTTPException:
        return None


def _request_user_agent_hash(request: Request) -> str | None:
    user_agent = (request.headers.get("user-agent") or "").strip()
    return hashlib.sha256(user_agent.encode("utf-8")).hexdigest() if user_agent else None


def create_refresh_session(
    db: Session,
    user: User,
    request: Request,
    *,
    client_type: str,
) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    session_id = str(uuid.uuid4())
    refresh_token = _refresh_token(session_id, 1)
    absolute_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_ABSOLUTE_DAYS)
    session = UserRefreshSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=_refresh_token_hash(refresh_token),
        generation=1,
        client_type=client_type,
        user_agent_hash=_request_user_agent_hash(request),
        created_at=now,
        last_used_at=now,
        expires_at=min(now + timedelta(days=settings.REFRESH_TOKEN_IDLE_DAYS), absolute_expires_at),
        absolute_expires_at=absolute_expires_at,
    )
    db.add(session)
    db.commit()
    return issue_session_access_token(user, session), refresh_token


def issue_session_access_token(user: User, session: UserRefreshSession) -> str:
    return create_access_token(
        {
            "sub": normalize_email(user.email),
            "uid": user.id,
            "sid": session.id,
            "rgen": session.generation,
            "typ": "access",
        }
    )


def rotate_refresh_session(
    db: Session,
    raw_token: str,
) -> tuple[User, str, str]:
    parsed = _parse_refresh_token(raw_token)
    if parsed is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh session")
    session_id, _ = parsed
    now = datetime.now(timezone.utc)
    session = (
        db.query(UserRefreshSession)
        .filter(UserRefreshSession.id == session_id)
        .with_for_update()
        .first()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh session")

    expires_at = _as_utc_aware(session.expires_at)
    absolute_expires_at = _as_utc_aware(session.absolute_expires_at)
    if session.revoked_at is not None or not expires_at or not absolute_expires_at:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session revoked")
    if expires_at <= now or absolute_expires_at <= now:
        session.revoked_at = now
        session.revoke_reason = "expired"
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session expired")

    user = db.query(User).filter(User.id == session.user_id).first()
    if user is None or (user.status or "active").lower() != "active":
        session.revoked_at = now
        session.revoke_reason = "account_inactive"
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not active")

    token_hash = _refresh_token_hash(raw_token)
    if hmac.compare_digest(token_hash, session.refresh_token_hash):
        session.previous_refresh_token_hash = session.refresh_token_hash
        session.previous_valid_until = now + timedelta(seconds=settings.REFRESH_TOKEN_REUSE_GRACE_SECONDS)
        session.generation += 1
        rotated_token = _refresh_token(session.id, session.generation)
        session.refresh_token_hash = _refresh_token_hash(rotated_token)
        session.last_used_at = now
        session.expires_at = min(
            now + timedelta(days=settings.REFRESH_TOKEN_IDLE_DAYS),
            absolute_expires_at,
        )
        db.commit()
        return user, issue_session_access_token(user, session), rotated_token

    previous_valid_until = _as_utc_aware(session.previous_valid_until)
    if (
        session.previous_refresh_token_hash
        and previous_valid_until
        and now <= previous_valid_until
        and hmac.compare_digest(token_hash, session.previous_refresh_token_hash)
    ):
        current_token = _refresh_token(session.id, session.generation)
        return user, issue_session_access_token(user, session), current_token

    session.revoked_at = now
    session.revoke_reason = "refresh_reuse"
    db.commit()
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session reuse detected")


def revoke_refresh_session(db: Session, session_id: str | None, reason: str) -> None:
    if not session_id:
        return
    session = db.query(UserRefreshSession).filter(UserRefreshSession.id == session_id).first()
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        session.revoke_reason = reason
        db.commit()


def revoke_all_refresh_sessions(db: Session, user_id: int, reason: str) -> None:
    now = datetime.now(timezone.utc)
    sessions = (
        db.query(UserRefreshSession)
        .filter(UserRefreshSession.user_id == user_id, UserRefreshSession.revoked_at.is_(None))
        .all()
    )
    for session in sessions:
        session.revoked_at = now
        session.revoke_reason = reason
    db.commit()


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def legacy_user_from_token(token: str, db: Session) -> User:
    payload = decode_access_token(token)
    if payload.get("typ") == "access" or payload.get("sid"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid legacy token")
    if not _legacy_access_allowed():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Legacy session transition ended")
    email = normalize_email(payload.get("sub"))
    user = db.query(User).filter(func.lower(User.email) == email).first() if email else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if (user.status or "active").lower() != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not active")
    return user


def _get_request_token(request: Request) -> str | None:
    token = request.cookies.get("access_token")
    if token:
        return token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]

    return None


def _ensure_bootstrap_platform_admin(db: Session, user: User) -> None:
    if (
        not settings.PLATFORM_ADMIN_BOOTSTRAP_ENABLED
        or not is_platform_admin_bootstrap_email(user.email)
    ):
        return

    platform_admin = db.query(PlatformAdmin).filter(PlatformAdmin.user_id == user.id).first()
    if platform_admin is not None:
        return

    if db.query(PlatformAdmin.id).first() is not None:
        return

    platform_admin = PlatformAdmin(user_id=user.id, granted_by_user_id=None)
    db.add(platform_admin)
    db.commit()
    db.refresh(platform_admin)

    from .school_scope import write_audit

    write_audit(
        db,
        user,
        "platform_admin.bootstrap",
        platform_admin,
        {"source": "bootstrap", "condition": "explicit_first_run"},
    )
    db.commit()


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _get_request_token(request)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    email: str = normalize_email(payload.get("sub"))
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if (user.status or "active").lower() != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not active")

    session_id = payload.get("sid")
    if payload.get("typ") == "access" and session_id:
        session = db.query(UserRefreshSession).filter(UserRefreshSession.id == session_id).first()
        if (
            session is None
            or session.user_id != user.id
            or session.revoked_at is not None
            or _as_utc_aware(session.absolute_expires_at) <= datetime.now(timezone.utc)
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked")
    elif not _legacy_access_allowed():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Legacy session transition ended")

    _ensure_bootstrap_platform_admin(db, user)
    return user


async def verify_google_token(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={token}")
        if response.status_code != 200:
            return None
        return response.json()


def verify_google_id_token(token: str) -> dict | None:
    """Verify a native Google ID token against CHH's configured web client."""
    if not token or not settings.GOOGLE_CLIENT_ID:
        logger.warning("Native Google token verification rejected: missing token or client configuration")
        return None

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        claims = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            audience=settings.GOOGLE_CLIENT_ID,
        )
    except ImportError:
        logger.warning("Native Google token verification unavailable: google-auth is not installed")
        return None
    except Exception as exc:
        logger.warning("Native Google token verification rejected (%s)", exc.__class__.__name__)
        return None

    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        logger.warning("Native Google token verification rejected: invalid issuer")
        return None
    if claims.get("aud") != settings.GOOGLE_CLIENT_ID:
        logger.warning("Native Google token verification rejected: invalid audience")
        return None
    if claims.get("email_verified") is not True:
        logger.warning("Native Google token verification rejected: unverified email")
        return None
    if not normalize_email(claims.get("email")):
        logger.warning("Native Google token verification rejected: missing email")
        return None

    try:
        expires_at = datetime.fromtimestamp(float(claims["exp"]), tz=timezone.utc)
    except (KeyError, TypeError, ValueError, OverflowError):
        logger.warning("Native Google token verification rejected: invalid expiry")
        return None
    if expires_at <= datetime.now(timezone.utc):
        logger.warning("Native Google token verification rejected: expired token")
        return None

    return claims


CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
INVITE_COOKIE_NAME = "invite_token"


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response, token: str):
    max_age = refresh_session_cookie_max_age_seconds()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        max_age=max_age,
        expires=max_age,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )


def clear_csrf_cookie(response):
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")


def validate_csrf_request(request: Request):
    if request.method.upper() in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return

    exempt_paths = {"/api/dev/qa-login"}
    if request.url.path in exempt_paths:
        return

    if not request.cookies.get("access_token"):
        return

    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)

    if not cookie_token or not header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing CSRF token",
        )

    if not hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )

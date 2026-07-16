from datetime import datetime, timedelta, timezone
from typing import Optional

import hmac
import httpx
import logging
import secrets
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import get_db, settings
from .models_school import PlatformAdmin, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
logger = logging.getLogger(__name__)


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def is_platform_admin_bootstrap_email(email: str | None) -> bool:
    allowed_emails = [normalize_email(e) for e in settings.PLATFORM_ADMIN_EMAILS.split(",")]
    return normalize_email(email) in allowed_emails


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM)


def parent_session_cookie_max_age_seconds() -> int:
    return max(0, int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60)


def _get_request_token(request: Request) -> str | None:
    token = request.cookies.get("access_token")
    if token:
        return token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]

    return None


def _ensure_bootstrap_platform_admin(db: Session, user: User) -> None:
    if not is_platform_admin_bootstrap_email(user.email):
        return

    platform_admin = db.query(PlatformAdmin).filter(PlatformAdmin.user_id == user.id).first()
    if platform_admin and platform_admin.revoked_at is None:
        return

    if platform_admin:
        platform_admin.revoked_at = None
        db.commit()
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
        {"source": "bootstrap"},
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

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        email: str = normalize_email(payload.get("sub"))
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if (user.status or "active").lower() != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not active")

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
    max_age = parent_session_cookie_max_age_seconds()
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

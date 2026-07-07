from __future__ import annotations

import hmac
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import auth
from ..database import get_db, settings
from ..models_school import PlatformAdmin, User
from ..school_scope import write_audit
from ..security import BoundedInMemoryRateLimiter, get_client_ip_from_scope, parse_csv_values

router = APIRouter()
logger = logging.getLogger(__name__)
QA_TOKEN_ATTEMPT_WINDOW_SECONDS = 60
QA_TOKEN_ATTEMPT_MAX = 12

_qa_login_rate_limiter = BoundedInMemoryRateLimiter(QA_TOKEN_ATTEMPT_WINDOW_SECONDS, QA_TOKEN_ATTEMPT_MAX)


def _runtime_environment() -> str:
    return settings.runtime_environment


def _host_from_url(value: str | None) -> str:
    parsed = urlparse((value or "").strip())
    return (parsed.hostname or "").strip().lower()


def _request_host(request: Request) -> str:
    host = (request.headers.get("host") or "").split(",")[0].strip().lower()
    if host:
        return host
    return (request.url.hostname or "").strip().lower()


def _blocked_hostnames() -> set[str]:
    return {hostname.lower() for hostname in parse_csv_values(settings.QA_BLOCKED_HOSTNAMES)}


def _request_context_hostnames(request: Request) -> set[str]:
    request_hosts = {
        _request_host(request),
        _host_from_url(request.headers.get("origin")),
        _host_from_url(request.headers.get("referer")),
    }
    return {host for host in request_hosts if host}


def _is_blocked_context(request: Request) -> bool:
    blocked = _blocked_hostnames()
    return any(host in blocked for host in _request_context_hostnames(request))


def _rate_limit_qa_login(request: Request) -> None:
    client_ip = get_client_ip_from_scope(request.scope) or "unknown"
    if not _qa_login_rate_limiter.allow(client_ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many QA login attempts")


def _token_matches(expected_token: str, provided_token: str) -> bool:
    if not expected_token or not provided_token:
        return False
    return hmac.compare_digest(provided_token, expected_token)


async def _qa_login_from_request(request: Request, db: Session) -> JSONResponse:
    if _runtime_environment() == "production":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    if not settings.QA_LOGIN_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    configured_token = (settings.QA_LOGIN_TOKEN or "").strip()
    if not configured_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    if _is_blocked_context(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="QA login refused")

    _rate_limit_qa_login(request)

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    provided_token = (payload.get("token") or "").strip()
    if not _token_matches(configured_token, provided_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="QA login refused")

    email = auth.normalize_email(settings.QA_LOGIN_EMAIL)
    name = (settings.QA_LOGIN_NAME or "QA Platform Admin").strip() or "QA Platform Admin"
    now = datetime.now(timezone.utc)

    user = db.query(User).filter(func.lower(User.email) == email).first()
    reused = user is not None
    if user is None:
        user = User(
            email=email,
            name=name,
            google_sub=f"qa-login:{email}",
            last_login_at=now,
        )
        db.add(user)
    else:
        user.name = name
        user.google_sub = f"qa-login:{email}"
        user.last_login_at = now
    db.commit()
    db.refresh(user)

    platform_admin = db.query(PlatformAdmin).filter(PlatformAdmin.user_id == user.id).first()
    if not platform_admin:
        platform_admin = PlatformAdmin(user_id=user.id, granted_by_user_id=None)
        db.add(platform_admin)
        db.commit()
        db.refresh(platform_admin)
        write_audit(db, user, "platform_admin.qa_bootstrap", platform_admin, {"source": "qa-login"})
    elif platform_admin.revoked_at is not None:
        platform_admin.revoked_at = None
        db.commit()

    access_token = auth.create_access_token(data={"sub": user.email})
    session_max_age = auth.parent_session_cookie_max_age_seconds()
    response = JSONResponse(
        content={
            "status": "ok",
            "email": email,
            "user_id": user.id,
            "is_platform_admin": True,
            "reused": reused,
        }
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=session_max_age,
        expires=session_max_age,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )
    auth.set_csrf_cookie(response, auth.create_csrf_token())
    logger.info("QA login issued for %s", email)
    return response


@router.post("/qa-login")
async def qa_login(request: Request, db: Session = Depends(get_db)):
    return await _qa_login_from_request(request, db)

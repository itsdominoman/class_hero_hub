from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import auth, models
from .. import child_auth
from ..database import get_db, settings
from ..services.qa_seed import ensure_qa_child_session, seed_qa_child_dashboard, seed_qa_parent_dashboard

router = APIRouter()
logger = logging.getLogger(__name__)

PRODUCTION_HOSTS = {"familyherohub.com", "www.familyherohub.com"}


def _runtime_environment() -> str:
    return (
        getattr(settings, "ENVIRONMENT", "")
        or getattr(settings, "APP_ENV", "")
        or ""
    ).strip().lower()


def _host_from_url(value: str | None) -> str:
    parsed = urlparse((value or "").strip())
    return (parsed.hostname or "").strip().lower()


def _request_host(request: Request) -> str:
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip().lower()
    if forwarded_host:
        return forwarded_host
    host = (request.headers.get("host") or "").split(",")[0].strip().lower()
    if host:
        return host
    return (request.url.hostname or "").strip().lower()


def _is_production_context(request: Request) -> bool:
    request_hosts = {
        _request_host(request),
        _host_from_url(request.headers.get("origin")),
        _host_from_url(request.headers.get("referer")),
        _host_from_url(settings.PUBLIC_APP_URL),
        _host_from_url(settings.API_BASE_URL),
    }
    return any(host in PRODUCTION_HOSTS for host in request_hosts if host)


async def _qa_login_from_request(request: Request, db: Session) -> JSONResponse:
    if _runtime_environment() == "production":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    if not settings.QA_LOGIN_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    configured_token = (settings.QA_LOGIN_TOKEN or "").strip()
    if not configured_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    if _is_production_context(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="QA login refused")

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    provided_token = (payload.get("token") or "").strip()
    if not provided_token or provided_token != configured_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="QA login refused")

    email = auth.normalize_email(settings.QA_LOGIN_EMAIL)
    name = (settings.QA_LOGIN_NAME or "QA Parent").strip() or "QA Parent"

    parent = db.query(models.ParentUser).filter(func.lower(models.ParentUser.email) == email).first()
    if parent and auth.is_parent_revoked(parent):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been revoked")

    if parent is None:
        family = models.Family()
        db.add(family)
        db.flush()
        parent = models.ParentUser(
            email=email,
            name=name,
            google_sub=f"qa-login:{email}",
            family_id=family.id,
            last_login_at=datetime.now(timezone.utc),
        )
        db.add(parent)
        db.commit()
        db.refresh(parent)
        reused = False
    else:
        parent.name = name
        parent.google_sub = f"qa-login:{email}"
        parent.last_login_at = datetime.now(timezone.utc)
        if parent.family_id is None:
            family = models.Family()
            db.add(family)
            db.flush()
            parent.family_id = family.id
        db.commit()
        db.refresh(parent)
        reused = True

    seed_qa_parent_dashboard(db, parent)
    db.refresh(parent)

    access_token = auth.create_access_token(data={"sub": parent.email})
    response = JSONResponse(content={
        "status": "ok",
        "email": email,
        "parent_id": parent.id,
        "family_id": parent.family_id,
        "reused": reused,
    })
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=1800,
        expires=1800,
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


def _qa_child_login_enabled() -> bool:
    return bool(settings.QA_CHILD_LOGIN_ENABLED or settings.QA_LOGIN_ENABLED)


def _qa_child_login_token() -> str:
    return (settings.QA_CHILD_LOGIN_TOKEN or settings.QA_LOGIN_TOKEN or "").strip()


async def _qa_child_login_from_request(request: Request, db: Session) -> JSONResponse:
    if _runtime_environment() == "production":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    if not _qa_child_login_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    configured_token = _qa_child_login_token()
    if not configured_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    if _is_production_context(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="QA child login refused")

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    provided_token = (payload.get("token") or "").strip()
    if not provided_token or provided_token != configured_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="QA child login refused")

    try:
        seed = seed_qa_child_dashboard(db)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    session, raw_token = ensure_qa_child_session(db, seed.child)

    response = JSONResponse(content={
        "status": "ok",
        "parent_email": seed.parent.email,
        "family_id": seed.family.id,
        "child_id": seed.child.id,
        "child_name": seed.child.display_name,
        "child_route": seed.child_route,
        "reused": seed.reused,
    })
    child_auth.set_child_session_cookie(response, raw_token, session.expires_at)
    logger.info("QA child login issued for %s child=%s", seed.parent.email, seed.child.id)
    return response


@router.post("/qa-child-login")
async def qa_child_login(request: Request, db: Session = Depends(get_db)):
    return await _qa_child_login_from_request(request, db)

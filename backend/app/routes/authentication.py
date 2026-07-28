import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import admission, auth, invite_tokens, schemas
from ..database import get_db, settings
from ..mailer import MagicLoginEmail, send_magic_login
from ..models_school import MagicLoginToken, User
from ..security import BoundedInMemoryRateLimiter, get_client_ip_from_scope

router = APIRouter()
logger = logging.getLogger(__name__)

MAGIC_LOGIN_TTL = timedelta(minutes=15)
MAGIC_REQUEST_RATE_LIMIT = BoundedInMemoryRateLimiter(60, 5)
MAGIC_EXCHANGE_RATE_LIMIT = BoundedInMemoryRateLimiter(60, 20)
GOOGLE_NATIVE_LOGIN_RATE_LIMIT = BoundedInMemoryRateLimiter(60, 12)


class MagicLoginRequest(BaseModel):
    email: EmailStr
    return_to: str | None = Field(default=None, alias="returnTo")


class MagicLoginExchangeRequest(BaseModel):
    token: str = Field(min_length=1)


class RefreshSessionRequest(BaseModel):
    refresh_token: str | None = None

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/me", response_model=schemas.MeResponse)
async def get_me(
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    from ..main import _me_payload

    return _me_payload(current_user, db)


def _safe_return_path(value: str | None) -> str | None:
    candidate = (value or "").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return None
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc:
        return None
    return candidate


def _magic_login_url(raw_token: str) -> str:
    return f"{settings.PUBLIC_APP_URL.rstrip('/')}/login?{urlencode({'magicToken': raw_token})}"


def _rate_limit(limiter: BoundedInMemoryRateLimiter, request: Request, message: str) -> None:
    client_ip = get_client_ip_from_scope(request.scope) or "unknown"
    if not limiter.allow(client_ip, now=invite_tokens.now_utc()):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message)


def _set_browser_session_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    access_max_age = auth.parent_session_cookie_max_age_seconds()
    refresh_max_age = auth.refresh_session_cookie_max_age_seconds()
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=access_max_age,
        expires=access_max_age,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=refresh_max_age,
        expires=refresh_max_age,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/api/auth",
    )
    auth.set_csrf_cookie(response, auth.create_csrf_token())


def _clear_browser_session_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth")
    auth.clear_csrf_cookie(response)


def _issue_session_response(
    user: User,
    return_to: str | None,
    *,
    redirect: bool,
    request: Request,
    db: Session,
    admission_context: admission.AdmissionContext | None = None,
) -> Response:
    auth.revoke_refresh_session(db, auth.request_session_id(request), "session_replaced")
    access_token, refresh_token = auth.create_refresh_session(
        db,
        user,
        request,
        client_type="browser",
        admission_context=admission_context,
    )
    if redirect:
        response: Response = RedirectResponse(f"{settings.PUBLIC_APP_URL.rstrip('/')}{return_to or ''}", status_code=status.HTTP_302_FOUND)
    else:
        response = JSONResponse({"status": "signed_in", "return_to": return_to or None}, status_code=status.HTTP_200_OK)
    _set_browser_session_cookies(response, access_token, refresh_token)
    return response


def _resolve_login_identity(
    db: Session,
    *,
    email: str,
    name: str | None,
    google_sub: str | None,
    return_to: str | None,
    current: datetime,
) -> tuple[User, admission.AdmissionContext | None]:
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user is not None and (user.status or "active").lower() != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not active")

    admission_context = None
    if user is None or not admission.has_active_entitlement(db, user.id):
        admission_context = admission.invite_context_for_return_path(
            db,
            email=email,
            return_to=return_to,
            current=current,
        )
        if admission_context is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=admission.NOT_AUTHORISED_DETAIL,
            )

    if user is None:
        user = User(email=email, name=name or email, status="active")
        db.add(user)
        db.flush()
    user.email = email
    if name:
        user.name = name
    if google_sub:
        user.google_sub = google_sub
    user.last_login_at = current
    return user, admission_context


def _identity_can_request_magic_link(
    db: Session,
    *,
    email: str,
    return_to: str | None,
) -> bool:
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if (
        user is not None
        and (user.status or "active").lower() == "active"
        and admission.has_active_entitlement(db, user.id)
    ):
        return True
    return (
        admission.invite_context_for_return_path(
            db,
            email=email,
            return_to=return_to,
        )
        is not None
    )


def _exchange_magic_login(
    raw_token: str,
    db: Session,
) -> tuple[User, str | None, admission.AdmissionContext | None]:
    token_hash = invite_tokens.hash_token(raw_token.strip())
    current = invite_tokens.now_utc()
    token = db.query(MagicLoginToken).filter(MagicLoginToken.token_hash == token_hash).first()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired sign-in link")
    if token.used_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Sign-in link already used")
    expires_at = invite_tokens.as_utc_aware(token.expires_at)
    if expires_at is None or expires_at <= current:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Sign-in link expired")

    return_to = _safe_return_path(token.return_to)
    user, admission_context = _resolve_login_identity(
        db,
        email=token.email,
        name=token.email,
        google_sub=None,
        return_to=return_to,
        current=current,
    )
    token.used_at = current
    db.commit()
    db.refresh(user)
    return user, return_to, admission_context


@router.post("/magic-link/request")
async def request_magic_link(payload: MagicLoginRequest, request: Request, db: Session = Depends(get_db)):
    _rate_limit(MAGIC_REQUEST_RATE_LIMIT, request, "Too many sign-in link requests")
    email = auth.normalize_email(str(payload.email))
    return_to = _safe_return_path(payload.return_to)
    if not _identity_can_request_magic_link(db, email=email, return_to=return_to):
        return {"status": "sent"}
    raw_token = invite_tokens.generate_token()
    record = MagicLoginToken(
        email=email,
        token_hash=invite_tokens.hash_token(raw_token),
        return_to=return_to,
        expires_at=invite_tokens.now_utc() + MAGIC_LOGIN_TTL,
        requested_ip=get_client_ip_from_scope(request.scope),
    )
    db.add(record)
    db.commit()
    try:
        send_magic_login(MagicLoginEmail(to_email=email, login_url=_magic_login_url(raw_token)))
        return {"status": "sent"}
    except Exception as exc:
        logger.exception("Failed to send magic login email to %s", email)
        return {"status": "created", "warning": f"Sign-in link was created, but email could not be sent: {str(exc)[:200]}"}


@router.get("/magic-link/exchange")
async def exchange_magic_link_get(token: str, request: Request, db: Session = Depends(get_db)):
    _rate_limit(MAGIC_EXCHANGE_RATE_LIMIT, request, "Too many sign-in link attempts")
    token_hash = invite_tokens.hash_token(token.strip())
    current = invite_tokens.now_utc()
    stored = db.query(MagicLoginToken).filter(MagicLoginToken.token_hash == token_hash).first()
    if not stored:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired sign-in link")
    if stored.used_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Sign-in link already used")
    expires_at = invite_tokens.as_utc_aware(stored.expires_at)
    if expires_at is None or expires_at <= current:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Sign-in link expired")
    if not _identity_can_request_magic_link(
        db,
        email=stored.email,
        return_to=_safe_return_path(stored.return_to),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=admission.NOT_AUTHORISED_DETAIL,
        )
    return {"status": "ready", "return_to": _safe_return_path(stored.return_to)}


@router.post("/magic-link/exchange")
async def exchange_magic_link_post(payload: MagicLoginExchangeRequest, request: Request, db: Session = Depends(get_db)):
    _rate_limit(MAGIC_EXCHANGE_RATE_LIMIT, request, "Too many sign-in link attempts")
    user, return_to, admission_context = _exchange_magic_login(payload.token, db)
    response = _issue_session_response(
        user,
        return_to,
        redirect=False,
        request=request,
        db=db,
        admission_context=admission_context,
    )
    return response


@router.get("/google/login")
async def google_login(request: Request):
    return_to = _safe_return_path(request.query_params.get("return_to"))
    if return_to:
        request.session["post_auth_redirect"] = return_to
    return await oauth.google.authorize_redirect(request, settings.GOOGLE_REDIRECT_URI)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Google auth failed: {str(exc)}")

    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user info from Google")

    email = auth.normalize_email(user_info.get("email"))
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No email from Google")

    return_to = _safe_return_path(request.session.pop("post_auth_redirect", None))
    user, admission_context = _resolve_login_identity(
        db,
        email=email,
        name=user_info.get("name"),
        google_sub=user_info.get("sub"),
        return_to=return_to,
        current=datetime.now(timezone.utc),
    )
    return _issue_session_response(
        user,
        return_to,
        redirect=True,
        request=request,
        db=db,
        admission_context=admission_context,
    )


@router.post("/google/native", response_model=schemas.NativeGoogleLoginResponse)
async def google_native_login(
    payload: schemas.NativeGoogleLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Exchange a verified Android Credential Manager ID token for a CHH JWT."""
    _rate_limit(GOOGLE_NATIVE_LOGIN_RATE_LIMIT, request, "Too many Google native login attempts")
    claims = auth.verify_google_id_token(payload.id_token)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google ID token")

    email = auth.normalize_email(claims.get("email"))
    return_to = _safe_return_path(payload.return_to)
    user, admission_context = _resolve_login_identity(
        db,
        email=email,
        name=claims.get("name"),
        google_sub=claims.get("sub"),
        return_to=return_to,
        current=datetime.now(timezone.utc),
    )
    auth.revoke_refresh_session(db, auth.request_session_id(request), "session_replaced")
    access_token, refresh_token = auth.create_refresh_session(
        db,
        user,
        request,
        client_type="android",
        admission_context=admission_context,
    )
    return schemas.NativeGoogleLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=auth.parent_session_cookie_max_age_seconds(),
    )


@router.post("/refresh")
async def refresh_session(
    request: Request,
    payload: RefreshSessionRequest | None = None,
    db: Session = Depends(get_db),
):
    supplied_refresh = (payload.refresh_token if payload else None) or request.cookies.get("refresh_token")
    native_request = bool((payload and payload.refresh_token) or request.headers.get("Authorization"))
    if supplied_refresh:
        _, access_token, refresh_token = auth.rotate_refresh_session(db, supplied_refresh)
    else:
        legacy_token = auth._get_request_token(request)
        if not legacy_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh session")
        user = auth.legacy_user_from_token(legacy_token, db)
        access_token, refresh_token = auth.create_refresh_session(
            db,
            user,
            request,
            client_type="android" if native_request else "browser",
        )

    content = {
        "access_token": access_token if native_request else None,
        "refresh_token": refresh_token if native_request else None,
        "token_type": "bearer",
        "expires_in": auth.parent_session_cookie_max_age_seconds(),
    }
    response = JSONResponse(content)
    if not native_request:
        _set_browser_session_cookies(response, access_token, refresh_token)
    return response


@router.post("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    auth.revoke_refresh_session(db, auth.request_session_id(request), "logout")
    response = JSONResponse({"message": "Logged out"})
    _clear_browser_session_cookies(response)
    return response


@router.post("/logout-all")
async def logout_all(
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    auth.revoke_all_refresh_sessions(db, current_user.id, "logout_all")
    response = JSONResponse({"message": "Logged out on all devices"})
    _clear_browser_session_cookies(response)
    return response

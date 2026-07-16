import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import auth, invite_tokens, schemas
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


def _issue_session_response(user: User, return_to: str | None, *, redirect: bool) -> Response:
    access_token = auth.create_access_token(data={"sub": user.email})
    session_max_age = auth.parent_session_cookie_max_age_seconds()
    if redirect:
        response: Response = RedirectResponse(f"{settings.PUBLIC_APP_URL.rstrip('/')}{return_to or ''}", status_code=status.HTTP_302_FOUND)
    else:
        response = JSONResponse({"status": "signed_in", "return_to": return_to or None}, status_code=status.HTTP_200_OK)
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
    return response


def _exchange_magic_login(raw_token: str, db: Session) -> tuple[User, str | None]:
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

    user = db.query(User).filter(func.lower(User.email) == token.email).first()
    if user is None:
        user = User(email=token.email, name=token.email, last_login_at=current)
        db.add(user)
    else:
        if (user.status or "active").lower() != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not active")
        user.email = token.email
        user.last_login_at = current
    token.used_at = current
    db.commit()
    db.refresh(user)
    return user, _safe_return_path(token.return_to)


@router.post("/magic-link/request")
async def request_magic_link(payload: MagicLoginRequest, request: Request, db: Session = Depends(get_db)):
    _rate_limit(MAGIC_REQUEST_RATE_LIMIT, request, "Too many sign-in link requests")
    email = auth.normalize_email(str(payload.email))
    raw_token = invite_tokens.generate_token()
    record = MagicLoginToken(
        email=email,
        token_hash=invite_tokens.hash_token(raw_token),
        return_to=_safe_return_path(payload.return_to),
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
    return {"status": "ready", "return_to": _safe_return_path(stored.return_to)}


@router.post("/magic-link/exchange")
async def exchange_magic_link_post(payload: MagicLoginExchangeRequest, request: Request, db: Session = Depends(get_db)):
    _rate_limit(MAGIC_EXCHANGE_RATE_LIMIT, request, "Too many sign-in link attempts")
    user, return_to = _exchange_magic_login(payload.token, db)
    response = _issue_session_response(user, return_to, redirect=False)
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

    now = datetime.now(timezone.utc)
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user:
        user = User(
            email=email,
            name=user_info.get("name"),
            google_sub=user_info.get("sub"),
            last_login_at=now,
        )
        db.add(user)
    else:
        user.email = email
        user.google_sub = user_info.get("sub")
        user.name = user_info.get("name")
        user.last_login_at = now
    db.commit()
    db.refresh(user)

    access_token = auth.create_access_token(data={"sub": user.email})
    session_max_age = auth.parent_session_cookie_max_age_seconds()

    response = Response(status_code=status.HTTP_302_FOUND)
    return_to = _safe_return_path(request.session.pop("post_auth_redirect", None))
    response.headers["Location"] = f"{settings.PUBLIC_APP_URL.rstrip('/')}{return_to or ''}"
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
    return response


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
    now = datetime.now(timezone.utc)
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user is None:
        user = User(
            email=email,
            name=claims.get("name"),
            google_sub=claims.get("sub"),
            last_login_at=now,
        )
        db.add(user)
    else:
        if (user.status or "active").lower() != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not active")
        user.email = email
        user.name = claims.get("name")
        user.google_sub = claims.get("sub")
        user.last_login_at = now
    db.commit()

    access_token = auth.create_access_token(data={"sub": user.email})
    return schemas.NativeGoogleLoginResponse(
        access_token=access_token,
        expires_in=auth.parent_session_cookie_max_age_seconds(),
    )


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    auth.clear_csrf_cookie(response)
    return {"message": "Logged out"}

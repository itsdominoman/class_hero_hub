from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import get_db, settings
from . import models, schemas
import httpx
import secrets
import hmac

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()

def ensure_parent_family(db: Session, parent: models.ParentUser) -> models.ParentUser:
    if parent.family_id is not None:
        return parent

    family = models.Family()
    db.add(family)
    db.flush()
    parent.family_id = family.id
    db.commit()
    db.refresh(parent)
    return parent

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_parent(request: Request, db: Session = Depends(get_db)):
    # Check for token in cookie first, then Authorization header
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token and settings.DEV_AUTH_ENABLED:
        # Fallback for development if enabled
        dev_email = normalize_email(settings.DEV_AUTH_PARENT_EMAIL)
        parent = db.query(models.ParentUser).filter(func.lower(models.ParentUser.email) == dev_email).first()
        if parent:
            return ensure_parent_family(db, parent)
        else:
            # Create dev parent if not exists
            family = models.Family()
            db.add(family)
            db.flush()
            new_parent = models.ParentUser(
                email=dev_email,
                name="Dev Parent",
                google_sub="dev_sub",
                family_id=family.id,
            )
            db.add(new_parent)
            db.commit()
            db.refresh(new_parent)
            return new_parent

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = normalize_email(payload.get("sub"))
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    parent = db.query(models.ParentUser).filter(func.lower(models.ParentUser.email) == email).first()
    if parent is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Parent not found")
    
    # Verify allowlist or family membership
    allowed_emails = [normalize_email(e) for e in settings.PARENT_EMAILS.split(",")]
    is_allowed = normalize_email(parent.email) in allowed_emails
    
    # If not in bootstrap allowlist, they must already have a family assigned (via invite)
    if not is_allowed and parent.family_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not in allowlist")

    return ensure_parent_family(db, parent)

def is_admin(parent: models.ParentUser) -> bool:
    """
    Check if a parent is an admin based on the bootstrap PARENT_EMAILS list.
    """
    allowed_emails = [normalize_email(e) for e in settings.PARENT_EMAILS.split(",")]
    return normalize_email(parent.email) in allowed_emails

async def get_current_admin(current_parent: models.ParentUser = Depends(get_current_parent)):
    if not is_admin(current_parent):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_parent

async def verify_google_token(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={token}")
        if response.status_code != 200:
            return None
        return response.json()


CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
INVITE_COOKIE_NAME = "invite_token"


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response, token: str):
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        max_age=1800,
        expires=1800,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )


def clear_csrf_cookie(response):
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")


def validate_csrf_request(request: Request):
    """
    Double-submit CSRF protection for cookie-authenticated unsafe requests.

    Browser attackers can cause a victim's cookies to be sent, but they cannot
    read our csrf_token cookie from another site and mirror it into X-CSRF-Token.
    """
    if request.method.upper() in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return

    exempt_paths = {
        "/api/child-link/exchange",
    }

    if request.url.path in exempt_paths:
        return

    # Only enforce when one of our auth cookies is present.
    # This avoids changing behavior for unauthenticated bad requests.
    has_auth_cookie = bool(
        request.cookies.get("access_token")
        or request.cookies.get("child_session")
    )
    if not has_auth_cookie:
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

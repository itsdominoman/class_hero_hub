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
    
    # Verify allowlist
    allowed_emails = [normalize_email(e) for e in settings.PARENT_EMAILS.split(",")]
    if normalize_email(parent.email) not in allowed_emails:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not in allowlist")

    return ensure_parent_family(db, parent)

async def verify_google_token(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={token}")
        if response.status_code != 200:
            return None
        return response.json()

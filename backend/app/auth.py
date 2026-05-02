from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db, settings
from . import models, schemas
import httpx

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

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
        parent = db.query(models.ParentUser).filter(models.ParentUser.email == settings.DEV_AUTH_PARENT_EMAIL).first()
        if parent:
            return parent
        else:
            # Create dev parent if not exists
            new_parent = models.ParentUser(
                email=settings.DEV_AUTH_PARENT_EMAIL,
                name="Dev Parent",
                google_sub="dev_sub"
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
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    parent = db.query(models.ParentUser).filter(models.ParentUser.email == email).first()
    if parent is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Parent not found")
    
    # Verify allowlist
    allowed_emails = [e.strip() for e in settings.PARENT_EMAILS.split(",")]
    if parent.email not in allowed_emails:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not in allowlist")

    return parent

async def verify_google_token(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={token}")
        if response.status_code != 200:
            return None
        return response.json()

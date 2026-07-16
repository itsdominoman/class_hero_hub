from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None
    locale: str = "en"

    class Config:
        from_attributes = True


class MeMembership(BaseModel):
    school_id: int
    school_name: str
    role: str


class MeResponse(BaseModel):
    user: UserPublic
    is_platform_admin: bool
    memberships: list[MeMembership]


class NativeGoogleLoginRequest(BaseModel):
    id_token: str


class NativeGoogleLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthUser(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None
    google_sub: Optional[str] = None
    locale: str = "en"
    status: str = "active"
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True

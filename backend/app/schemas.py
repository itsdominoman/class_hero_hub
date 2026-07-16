from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
    membership_id: int
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


class SchoolMessagingPolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_policy_version: int = Field(ge=1)
    enabled: bool
    guardian_replies_enabled: bool
    delivery_receipts_visible: bool
    read_receipts_visible: bool
    allow_staff_out_of_hours_opt_in: bool
    teachers_may_mark_urgent: bool
    notification_preview_mode: str = Field(pattern="^(generic|sender_only|body)$")
    retention_days: int = Field(ge=30, le=36500)
    email_mode: str = Field(pattern="^(off|immediate|digest)$")


class SchoolMessagingPolicyResponse(BaseModel):
    school_id: int
    global_enabled: bool
    effective_enabled: bool
    enabled: bool
    guardian_replies_enabled: bool
    delivery_receipts_visible: bool
    read_receipts_visible: bool
    allow_staff_out_of_hours_opt_in: bool
    teachers_may_mark_urgent: bool
    notification_preview_mode: str
    retention_days: int
    email_mode: str
    policy_version: int
    created_at: datetime | None
    updated_at: datetime | None

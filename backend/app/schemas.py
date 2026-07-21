from datetime import date, datetime, time
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


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
    contact_hours_enabled: bool
    notification_delay_mode: str
    notification_preview_mode: str
    retention_days: int
    email_mode: str
    policy_version: int
    created_at: datetime | None
    updated_at: datetime | None


class SchoolPointsNotificationPolicyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_policy_version: int = Field(ge=1)
    mode: Literal["summaries", "immediate", "off"]
    daily_enabled: bool
    weekly_enabled: bool
    monthly_enabled: bool
    week_starts_on: int = Field(ge=1, le=7)
    week_ends_on: int = Field(ge=1, le=7)
    weekly_summary_day: int = Field(ge=1, le=7)
    daily_summary_time: time
    weekly_summary_time: time
    monthly_summary_time: time
    school_timezone: str = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def local_times_only(self):
        for value in (self.daily_summary_time, self.weekly_summary_time, self.monthly_summary_time):
            if value.tzinfo is not None:
                raise ValueError("Summary times must use school-local wall-clock times")
        return self


class SchoolPointsNotificationPolicyResponse(BaseModel):
    school_id: int
    school_timezone: str
    mode: str
    daily_enabled: bool
    weekly_enabled: bool
    monthly_enabled: bool
    week_starts_on: int
    week_ends_on: int
    weekly_summary_day: int
    daily_summary_time: time
    weekly_summary_time: time
    monthly_summary_time: time
    policy_version: int
    created_at: datetime | None
    updated_at: datetime | None


class SchoolContactWindowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weekday: int = Field(ge=1, le=7)
    start_local: time
    end_local: time

    @model_validator(mode="after")
    def nonempty(self):
        if self.start_local.tzinfo is not None or self.end_local.tzinfo is not None:
            raise ValueError("Contact windows must use school-local wall-clock times")
        if self.start_local == self.end_local:
            raise ValueError("Contact window start and end must differ")
        return self


class SchoolContactExceptionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_date: date
    kind: Literal["closed", "custom"]
    start_local: time | None = None
    end_local: time | None = None
    label: str | None = Field(default=None, max_length=160)
    label_ar: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def valid_window_shape(self):
        if (
            self.start_local is not None
            and self.start_local.tzinfo is not None
        ) or (
            self.end_local is not None
            and self.end_local.tzinfo is not None
        ):
            raise ValueError("Contact exceptions must use school-local wall-clock times")
        if self.kind == "closed":
            if self.start_local is not None or self.end_local is not None:
                raise ValueError("Closed exceptions cannot include an opening window")
        elif (
            self.start_local is None
            or self.end_local is None
            or self.start_local == self.end_local
        ):
            raise ValueError("Custom exceptions require a non-empty opening window")
        return self


class SchoolContactHoursUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_policy_version: int = Field(ge=1)
    enabled: bool
    notification_delay_mode: Literal["delay_notifications_only"]
    allow_staff_out_of_hours_opt_in: bool
    teachers_may_mark_urgent: bool
    weekly_windows: list[SchoolContactWindowInput] = Field(max_length=7)
    exceptions: list[SchoolContactExceptionInput] = Field(max_length=366)

    @model_validator(mode="after")
    def valid_schedule(self):
        weekdays = [window.weekday for window in self.weekly_windows]
        if len(weekdays) != len(set(weekdays)):
            raise ValueError("Only one contact window is allowed per weekday")
        exception_dates = [exception.local_date for exception in self.exceptions]
        if len(exception_dates) != len(set(exception_dates)):
            raise ValueError("Only one contact-hours exception is allowed per date")
        if self.enabled and not self.weekly_windows:
            raise ValueError("Enabled contact hours require at least one open weekday")
        return self


class SchoolContactHoursResponse(BaseModel):
    school_id: int
    school_timezone: str
    policy_version: int
    enabled: bool
    notification_delay_mode: str
    allow_staff_out_of_hours_opt_in: bool
    teachers_may_mark_urgent: bool
    weekly_windows: list[SchoolContactWindowInput]
    exceptions: list[SchoolContactExceptionInput]


class StaffMessagingPreferenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_preference_version: int = Field(ge=1)
    out_of_hours_notifications_enabled: bool


class StaffMessagingPreferenceResponse(BaseModel):
    allowed_by_school: bool
    stored_out_of_hours_notifications_enabled: bool
    effective_out_of_hours_notifications_enabled: bool
    preference_version: int


class NotificationOutboxStatusResponse(BaseModel):
    counts: dict[str, int]
    oldest_held_at: datetime | None
    next_eligible_at: datetime | None

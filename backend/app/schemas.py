from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime, date, time
from typing import Optional, List, Literal
from .models import TransactionType, JarType, RedemptionStatus, PetStage

class ParentUserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class ParentUser(ParentUserBase):
    id: int
    family_id: Optional[int] = None
    is_admin: bool = False
    status: str = "active"
    revoked_at: Optional[datetime] = None
    revoked_by_parent_id: Optional[int] = None
    revoke_reason: Optional[str] = None
    restored_at: Optional[datetime] = None
    restored_by_parent_id: Optional[int] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class FamilyBase(BaseModel):
    timezone: str = "Asia/Muscat"
    week_start_day: int = 6

class Family(FamilyBase):
    id: int
    status: str = "active"
    suspended_at: Optional[datetime] = None
    suspended_by_parent_id: Optional[int] = None
    suspend_reason: Optional[str] = None
    restored_at: Optional[datetime] = None
    restored_by_parent_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChildBase(BaseModel):
    display_name: str
    avatar_name: Optional[str] = None
    active: bool = True

class ChildCreate(ChildBase):
    pass

class Child(ChildBase):
    id: int
    family_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class CalendarEntryBase(BaseModel):
    title: str
    description: Optional[str] = None
    entry_type: str = "task"
    is_rewardable: bool = False
    points_value: Optional[int] = None
    recurrence_type: str = "none"
    recurrence_days: Optional[str] = None
    start_date: date
    start_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    is_active: bool = True

class CalendarEntryCreate(CalendarEntryBase):
    child_id: int

class CalendarEntry(CalendarEntryBase):
    id: int
    family_id: int
    child_id: int
    created_by_parent_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class CalendarCompletionBase(BaseModel):
    entry_id: int
    child_id: int
    occurrence_date: date
    status: str = "pending"

class CalendarCompletionCreate(CalendarCompletionBase):
    pass

class CalendarCompletion(CalendarCompletionBase):
    id: int
    completed_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by_parent_id: Optional[int] = None
    base_points: Optional[int] = None
    bonus_multiplier_applied: float = 1.0
    points_awarded: Optional[int] = None
    transaction_id: Optional[int] = None
    streak_source_id: Optional[int] = None

    class Config:
        from_attributes = True

class SchoolItemBase(BaseModel):
    class_name: str
    needed_item: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

class SchoolItemUpsert(SchoolItemBase):
    id: Optional[int] = None

class SchoolItem(SchoolItemBase):
    id: int
    family_id: int
    child_id: int
    weekday: int
    created_by_parent_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class WeeklyStreakBase(BaseModel):
    child_id: int
    week_start_date: date
    week_end_date: date
    bonus_date: date
    required_task_count: int
    completed_task_count: int
    streak_earned: bool = False
    bonus_multiplier: float = 2.0

class WeeklyStreak(WeeklyStreakBase):
    id: int
    family_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class LedgerTransactionBase(BaseModel):
    jar: JarType
    transaction_type: TransactionType
    points: int
    description: str
    locked_until: Optional[datetime] = None

class LedgerTransactionCreate(LedgerTransactionBase):
    pass

class LedgerTransaction(LedgerTransactionBase):
    id: int
    child_id: int
    created_by_parent_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class LedgerSummary(BaseModel):
    gained: int
    lost: int
    spent: int
    net: int
    saved_in: int
    saved_out: int
    held: int
    released: int
    transaction_count: int

    class Config:
        from_attributes = True

class RedemptionRequestBase(BaseModel):
    points: int
    title: str
    description: str

class RedemptionRequestCreate(RedemptionRequestBase):
    pass

class RedemptionRequest(RedemptionRequestBase):
    id: int
    child_id: int
    status: RedemptionStatus
    parent_note: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by_parent_id: Optional[int] = None

    class Config:
        from_attributes = True

class ChildDeviceInviteCreateResponse(BaseModel):
    id: int
    child_id: int
    child_name: str
    invite_token: str
    invite_url: str
    expires_at: datetime

class ChildDeviceInviteRevokeResponse(BaseModel):
    revoked_invites: int
    revoked_sessions: int

class ChildLinkExchangeRequest(BaseModel):
    token: str

class ChildLinkExchangeResponse(BaseModel):
    child: Child
    session_expires_at: datetime

class PetProgressBase(BaseModel):
    lifetime_points: int
    current_stage: PetStage

class PetProgress(PetProgressBase):
    id: int
    child_id: int
    updated_at: datetime

    class Config:
        from_attributes = True

class ChildSummary(BaseModel):
    child: Child
    spending_balance: int
    savings_balance: int
    locked_savings: int
    available_savings: int
    available_spending: int
    pending_redemptions: int
    pet_progress: PetProgress

class AwardRequest(BaseModel):
    points: int
    description: str
    jar: JarType = JarType.spending

class PenaltyRequest(BaseModel):
    points: int
    description: str
    jar: JarType = JarType.spending

class SavingsDepositRequest(BaseModel):
    points: int
    description: str

class SavingsWithdrawRequest(BaseModel):
    points: int
    description: str

class RedemptionReviewRequest(BaseModel):
    parent_note: Optional[str] = None

class PresetBehaviourBase(BaseModel):
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    points: int
    is_active: bool = True

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty")
        return value

    @field_validator("points")
    @classmethod
    def points_must_not_be_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("Points cannot be zero")
        return value

class PresetBehaviourCreate(PresetBehaviourBase):
    pass

class PresetBehaviour(PresetBehaviourBase):
    id: int
    parent_id: int
    family_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class RewardBase(BaseModel):
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    points: int
    is_active: bool = True

    @field_validator("title")
    @classmethod
    def reward_title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty")
        return value

    @field_validator("points")
    @classmethod
    def reward_points_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Points must be positive")
        return value

class RewardCreate(RewardBase):
    pass

class Reward(RewardBase):
    id: int
    parent_id: int
    family_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class FamilyMember(BaseModel):
    id: int
    email: str
    name: Optional[str]
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True

class FamilyInviteCreate(BaseModel):
    email: EmailStr

class FamilyInvite(BaseModel):
    id: int
    email: str
    status: str
    created_at: datetime
    expires_at: Optional[datetime]
    accepted_at: Optional[datetime]

    class Config:
        from_attributes = True

class RegistrationRequestBase(BaseModel):
    email: EmailStr
    name: str
    family_name: str
    message: Optional[str] = None

class RegistrationRequestCreate(RegistrationRequestBase):
    pass

class RegistrationRequest(RegistrationRequestBase):
    id: int
    status: str
    created_at: datetime
    approved_at: Optional[datetime]
    rejected_at: Optional[datetime]

    class Config:
        from_attributes = True

class RegistrationRequestReview(BaseModel):
    rejection_reason: Optional[str] = None

class ApprovedParentEmail(BaseModel):
    id: int
    email: str
    source: str
    status: str
    approved_at: datetime
    revoked_at: Optional[datetime] = None
    revoked_by_parent_id: Optional[int] = None
    revoke_reason: Optional[str] = None
    restored_at: Optional[datetime] = None
    restored_by_parent_id: Optional[int] = None

    class Config:
        from_attributes = True


class AdminAccessActionRequest(BaseModel):
    revoke_reason: Optional[str] = None


class AdminFamilyActionRequest(BaseModel):
    suspend_reason: Optional[str] = None


class AdminUserRecord(BaseModel):
    normalized_email: str
    email: Optional[str] = None
    parent_user_id: Optional[int] = None
    name: Optional[str] = None
    family_id: Optional[int] = None
    family_status: Optional[str] = None
    family_suspended_at: Optional[datetime] = None
    family_suspend_reason: Optional[str] = None
    user_status: str
    approval_status: Optional[str] = None
    source: Optional[str] = None
    approved_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    restored_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    children_count: int = 0
    coparents_count: int = 0
    family_orphaned: bool = False
    registration_request_id: Optional[int] = None
    registration_request_status: Optional[str] = None
    registration_request_family_name: Optional[str] = None
    registration_request_message: Optional[str] = None
    is_bootstrap_admin: bool = False
    can_revoke: bool = False
    can_revoke_reason: Optional[str] = None
    can_restore: bool = False
    can_suspend_family: bool = False
    can_restore_family: bool = False
    google_sub_masked: Optional[str] = None
    restored_by_parent_id: Optional[int] = None
    family_restored_at: Optional[datetime] = None
    family_restored_by_parent_id: Optional[int] = None

    class Config:
        from_attributes = True


class AdminUsersResponse(BaseModel):
    items: List[AdminUserRecord]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminFamilySummary(BaseModel):
    family_id: int
    status: str
    suspended_at: Optional[datetime] = None
    suspend_reason: Optional[str] = None
    restored_at: Optional[datetime] = None
    restored_by_parent_id: Optional[int] = None
    parent_count: int
    active_parent_count: int
    child_count: int

    class Config:
        from_attributes = True

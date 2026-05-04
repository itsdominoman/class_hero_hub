from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional, List
from .models import TransactionType, JarType, RedemptionStatus, PetStage

class ParentUserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class ParentUser(ParentUserBase):
    id: int
    family_id: Optional[int] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None

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

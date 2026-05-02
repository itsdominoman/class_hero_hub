from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from .models import TransactionType, JarType, RedemptionStatus, PetStage

class ParentUserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class ParentUser(ParentUserBase):
    id: int
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
    created_by_parent_id: int
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

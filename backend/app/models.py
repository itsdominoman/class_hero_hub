from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Date, Time, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

class TransactionType(enum.Enum):
    award = "award"
    penalty = "penalty"
    savings_deposit = "savings_deposit"
    savings_withdrawal = "savings_withdrawal"
    redemption_hold = "redemption_hold"
    redemption_approved = "redemption_approved"
    redemption_rejected = "redemption_rejected"
    adjustment = "adjustment"
    calendar_task = "calendar_task"

class JarType(enum.Enum):
    spending = "spending"
    savings = "savings"

class RedemptionStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class PetStage(enum.Enum):
    egg = "egg"
    hatchling = "hatchling"
    cub = "cub"
    hero = "hero"
    beast = "beast"

class ParentUser(Base):
    __tablename__ = "parent_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    google_sub = Column(String, unique=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True)
    status = Column(String, default="active")
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_parent_id = Column(Integer, ForeignKey("parent_users.id"), nullable=True)
    revoke_reason = Column(String, nullable=True)
    restored_at = Column(DateTime(timezone=True), nullable=True)
    restored_by_parent_id = Column(Integer, ForeignKey("parent_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), onupdate=func.now())

    family = relationship("Family", back_populates="parents", foreign_keys=[family_id])

    @property
    def is_admin(self) -> bool:
        from .database import settings
        from .auth import normalize_email
        allowed_emails = [normalize_email(e) for e in settings.PARENT_EMAILS.split(",")]
        return normalize_email(self.email) in allowed_emails

class Family(Base):
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, index=True)
    timezone = Column(String, default="Asia/Muscat")
    week_start_day = Column(Integer, default=6) # 0=Monday, 6=Sunday
    status = Column(String, default="active")
    suspended_at = Column(DateTime(timezone=True), nullable=True)
    suspended_by_parent_id = Column(Integer, ForeignKey("parent_users.id"), nullable=True)
    suspend_reason = Column(String, nullable=True)
    restored_at = Column(DateTime(timezone=True), nullable=True)
    restored_by_parent_id = Column(Integer, ForeignKey("parent_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parents = relationship("ParentUser", back_populates="family", foreign_keys="ParentUser.family_id")
    children = relationship("Child", back_populates="family")
    presets = relationship("PresetBehaviour", back_populates="family")
    rewards = relationship("Reward", back_populates="family")
    invites = relationship("FamilyInvite", back_populates="family")
    calendar_entries = relationship("CalendarEntry", back_populates="family")
    weekly_streaks = relationship("WeeklyStreak", back_populates="family")
    school_items = relationship("SchoolItem", back_populates="family")

class FamilyInvite(Base):
    __tablename__ = "family_invites"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"))
    email = Column(String, index=True)
    role = Column(String, default="parent")
    status = Column(String, default="pending") # pending, accepted, revoked, expired
    token_hash = Column(String, unique=True, index=True, nullable=True)
    invited_by_parent_id = Column(Integer, ForeignKey("parent_users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    accepted_by_parent_id = Column(Integer, ForeignKey("parent_users.id"), nullable=True)

    family = relationship("Family", back_populates="invites")
    invited_by = relationship("ParentUser", foreign_keys=[invited_by_parent_id])
    accepted_by = relationship("ParentUser", foreign_keys=[accepted_by_parent_id])

class ChildDeviceInvite(Base):
    __tablename__ = "child_device_invites"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"))
    child_id = Column(Integer, ForeignKey("children.id"))
    created_by_parent_id = Column(Integer, ForeignKey("parent_users.id"))
    token_hash = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)

class ChildDeviceSession(Base):
    __tablename__ = "child_device_sessions"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"))
    child_id = Column(Integer, ForeignKey("children.id"))
    invite_id = Column(Integer, ForeignKey("child_device_invites.id"), nullable=True)
    session_hash = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True)
    display_name = Column(String)
    avatar_name = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    family = relationship("Family", back_populates="children")
    transactions = relationship("LedgerTransaction", back_populates="child")
    redemptions = relationship("RedemptionRequest", back_populates="child")
    pet_progress = relationship("PetProgress", back_populates="child", uselist=False)
    calendar_entries = relationship("CalendarEntry", back_populates="child")
    calendar_completions = relationship("CalendarCompletion", back_populates="child")
    weekly_streaks = relationship("WeeklyStreak", back_populates="child")
    school_items = relationship("SchoolItem", back_populates="child")

class CalendarEntry(Base):
    __tablename__ = "calendar_entries"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"))
    child_id = Column(Integer, ForeignKey("children.id"))
    created_by_parent_id = Column(Integer, ForeignKey("parent_users.id"))
    title = Column(String)
    description = Column(String, nullable=True)
    entry_type = Column(String, default="task") # "event" or "task"
    is_rewardable = Column(Boolean, default=False)
    points_value = Column(Integer, nullable=True)
    
    # Recurrence
    recurrence_type = Column(String, default="none") # "none", "daily", "weekly"
    recurrence_days = Column(String, nullable=True) # e.g., "0,2,4" for Mon, Wed, Fri
    
    # Timing (Local Family Time)
    start_date = Column(Date)
    start_time = Column(Time, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    family = relationship("Family", back_populates="calendar_entries")
    child = relationship("Child", back_populates="calendar_entries")
    created_by = relationship("ParentUser")
    completions = relationship("CalendarCompletion", back_populates="entry")

class SchoolItem(Base):
    __tablename__ = "school_items"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"))
    child_id = Column(Integer, ForeignKey("children.id"))
    weekday = Column(Integer) # 0 = Monday, 6 = Sunday
    class_name = Column(String)
    needed_item = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_by_parent_id = Column(Integer, ForeignKey("parent_users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    family = relationship("Family", back_populates="school_items")
    child = relationship("Child", back_populates="school_items")
    created_by = relationship("ParentUser")

class CalendarCompletion(Base):
    __tablename__ = "calendar_task_completions"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("calendar_entries.id"))
    child_id = Column(Integer, ForeignKey("children.id"))
    occurrence_date = Column(Date) # The local family date this was for
    
    status = Column(String, default="pending") # "pending", "approved", "rejected"
    completed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_parent_id = Column(Integer, ForeignKey("parent_users.id"), nullable=True)
    
    # Audit trail
    base_points = Column(Integer, nullable=True)
    bonus_multiplier_applied = Column(Float, default=1.0)
    points_awarded = Column(Integer, nullable=True)
    transaction_id = Column(Integer, ForeignKey("ledger_transactions.id"), nullable=True)
    streak_source_id = Column(Integer, ForeignKey("weekly_streaks.id"), nullable=True)

    entry = relationship("CalendarEntry", back_populates="completions")
    child = relationship("Child", back_populates="calendar_completions")
    reviewed_by = relationship("ParentUser")

    __table_args__ = (UniqueConstraint('entry_id', 'child_id', 'occurrence_date', name='_task_occurrence_uc'),)

class WeeklyStreak(Base):
    __tablename__ = "weekly_streaks"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"))
    child_id = Column(Integer, ForeignKey("children.id"))
    week_start_date = Column(Date)
    week_end_date = Column(Date)
    bonus_date = Column(Date)
    
    required_task_count = Column(Integer, default=0)
    completed_task_count = Column(Integer, default=0)
    streak_earned = Column(Boolean, default=False)
    
    bonus_multiplier = Column(Float, default=2.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    family = relationship("Family", back_populates="weekly_streaks")
    child = relationship("Child", back_populates="weekly_streaks")

    __table_args__ = (UniqueConstraint('child_id', 'week_start_date', name='_child_week_streak_uc'),)

class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"))
    jar = Column(Enum(JarType))
    transaction_type = Column(Enum(TransactionType))
    points = Column(Integer)
    description = Column(String)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_by_parent_id = Column(Integer, ForeignKey("parent_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    child = relationship("Child", back_populates="transactions")

class RedemptionRequest(Base):
    __tablename__ = "redemption_requests"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"))
    points = Column(Integer)
    title = Column(String)
    description = Column(String)
    status = Column(Enum(RedemptionStatus), default=RedemptionStatus.pending)
    parent_note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_parent_id = Column(Integer, ForeignKey("parent_users.id"), nullable=True)

    child = relationship("Child", back_populates="redemptions")

class PetProgress(Base):
    __tablename__ = "pet_progress"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"), unique=True)
    lifetime_points = Column(Integer, default=0)
    current_stage = Column(Enum(PetStage), default=PetStage.egg)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    child = relationship("Child", back_populates="pet_progress")

class PresetBehaviour(Base):
    __tablename__ = "preset_behaviours"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parent_users.id"))
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True)
    title = Column(String)
    description = Column(String, nullable=True)
    icon = Column(String, nullable=True)
    points = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parent = relationship("ParentUser")
    family = relationship("Family", back_populates="presets")

class Reward(Base):
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parent_users.id"))
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True)
    title = Column(String)
    description = Column(String, nullable=True)
    icon = Column(String, nullable=True)
    points = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parent = relationship("ParentUser")
    family = relationship("Family", back_populates="rewards")

class RegistrationRequest(Base):
    __tablename__ = "registration_requests"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    normalized_email = Column(String, index=True)
    name = Column(String)
    family_name = Column(String)
    message = Column(String, nullable=True)
    status = Column(String, default="pending") # pending, approved, rejected, expired
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_parent_id = Column(Integer, ForeignKey("parent_users.id"), nullable=True)
    rejection_reason = Column(String, nullable=True)

class ApprovedParentEmail(Base):
    __tablename__ = "approved_parent_emails"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    normalized_email = Column(String, unique=True, index=True)
    approved_by_parent_id = Column(Integer, ForeignKey("parent_users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(String, default="registration_request") # bootstrap, registration_request, invite, manual_admin
    status = Column(String, default="active") # active, revoked
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_parent_id = Column(Integer, ForeignKey("parent_users.id"), nullable=True)
    revoke_reason = Column(String, nullable=True)
    restored_at = Column(DateTime(timezone=True), nullable=True)
    restored_by_parent_id = Column(Integer, ForeignKey("parent_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

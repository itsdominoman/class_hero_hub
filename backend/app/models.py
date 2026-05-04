from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), onupdate=func.now())

    family = relationship("Family", back_populates="parents")

class Family(Base):
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parents = relationship("ParentUser", back_populates="family")
    children = relationship("Child", back_populates="family")
    presets = relationship("PresetBehaviour", back_populates="family")
    rewards = relationship("Reward", back_populates="family")
    invites = relationship("FamilyInvite", back_populates="family")

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

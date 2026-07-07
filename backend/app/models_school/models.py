from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, event
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    google_sub = Column(String, unique=True, index=True, nullable=True)
    locale = Column(String, default="en")
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    name_ar = Column(String, nullable=True)
    slug = Column(String, unique=True, index=True)
    timezone = Column(String, default="Asia/Muscat")
    locale_default = Column(String, default="en")
    points_label = Column(String, default="Points")
    status = Column(String, default="pending_setup")
    suspended_at = Column(DateTime(timezone=True), nullable=True)
    suspended_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    suspend_reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String)
    status = Column(String, default="active")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("school_id", "user_id", "role", name="uq_memberships_school_user_role"),
    )


class PlatformAdmin(Base):
    __tablename__ = "platform_admins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    granted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    entity_type = Column(String)
    entity_id = Column(Integer, nullable=True)
    detail = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


@event.listens_for(AuditLog, "before_update", propagate=True)
def _prevent_audit_log_update(mapper, connection, target):
    raise ValueError("AuditLog rows are append-only")

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from . import invite_tokens
from .models_school import (
    Membership,
    MessagingPermissionGrant,
    MessagingRetentionPolicy,
    School,
    SchoolSystemOwner,
    SchoolSystemOwnerEvent,
    User,
)


OWNER_BOOTSTRAP_PERMISSIONS = (
    "messaging.manage_safeguarding_permissions",
    "messaging.manage_legal_holds",
)


class GovernanceError(Exception):
    pass


class GovernanceForbidden(GovernanceError):
    pass


class GovernanceConflict(GovernanceError):
    pass


@dataclass(frozen=True)
class OwnerState:
    row: SchoolSystemOwner | None
    membership: Membership | None
    user: User | None
    recovery_required: bool


def _active_admin(db: Session, *, school_id: int, membership_id: int) -> tuple[Membership, User] | None:
    result = (
        db.query(Membership, User)
        .join(User, User.id == Membership.user_id)
        .filter(
            Membership.id == membership_id,
            Membership.school_id == school_id,
            Membership.role == "school_admin",
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            User.status == "active",
        )
        .first()
    )
    return result if result is not None else None


def owner_state(db: Session, *, school_id: int, record_recovery: bool = False) -> OwnerState:
    row = db.query(SchoolSystemOwner).filter(SchoolSystemOwner.school_id == school_id).first()
    if row is None:
        return OwnerState(None, None, None, True)
    active = _active_admin(db, school_id=school_id, membership_id=row.membership_id)
    if active is not None:
        return OwnerState(row, active[0], active[1], False)
    if record_recovery:
        existing = (
            db.query(SchoolSystemOwnerEvent.id)
            .filter(
                SchoolSystemOwnerEvent.school_id == school_id,
                SchoolSystemOwnerEvent.action == "recovery_required",
                SchoolSystemOwnerEvent.owner_version == row.owner_version,
            )
            .first()
        )
        if existing is None:
            db.add(
                SchoolSystemOwnerEvent(
                    school_id=school_id,
                    action="recovery_required",
                    previous_membership_id=row.membership_id,
                    actor_kind="system",
                    reason="Current System Owner is inactive or no longer an active administrator.",
                    owner_version=row.owner_version,
                )
            )
            db.commit()
    return OwnerState(row, None, None, True)


def _ensure_owner_permissions(db: Session, *, school_id: int, membership_id: int) -> None:
    for permission in OWNER_BOOTSTRAP_PERMISSIONS:
        exists = (
            db.query(MessagingPermissionGrant.id)
            .filter(
                MessagingPermissionGrant.school_id == school_id,
                MessagingPermissionGrant.membership_id == membership_id,
                MessagingPermissionGrant.permission == permission,
                MessagingPermissionGrant.revoked_at.is_(None),
            )
            .first()
        )
        if exists is None:
            db.add(
                MessagingPermissionGrant(
                    school_id=school_id,
                    membership_id=membership_id,
                    permission=permission,
                    granted_by_membership_id=membership_id,
                    grant_reason="System Owner governance bootstrap",
                )
            )


def bootstrap_system_owner(
    db: Session,
    *,
    school: School,
    membership: Membership,
    actor_user_id: int | None,
) -> SchoolSystemOwner:
    if membership.school_id != school.id or membership.role != "school_admin":
        raise GovernanceConflict("Only the first active school administrator can become System Owner")
    db.query(School).filter(School.id == school.id).with_for_update().one()
    current = db.query(SchoolSystemOwner).filter(SchoolSystemOwner.school_id == school.id).first()
    if current is not None:
        return current
    active = _active_admin(db, school_id=school.id, membership_id=membership.id)
    if active is None:
        raise GovernanceConflict("System Owner must be an active school administrator")
    row = SchoolSystemOwner(school_id=school.id, membership_id=membership.id, owner_version=1)
    db.add(row)
    db.add(
        SchoolSystemOwnerEvent(
            school_id=school.id,
            action="bootstrap",
            new_membership_id=membership.id,
            actor_kind="system",
            actor_user_id=actor_user_id,
            reason="First active school administrator accepted the school invitation.",
            owner_version=1,
        )
    )
    _ensure_owner_permissions(db, school_id=school.id, membership_id=membership.id)
    if db.query(MessagingRetentionPolicy.id).filter(
        MessagingRetentionPolicy.school_id == school.id
    ).first() is None:
        from .messaging_production import DEFAULT_RETENTION_RULES

        db.add(MessagingRetentionPolicy(
            school_id=school.id,
            policy_version=1,
            effective_at=invite_tokens.now_utc(),
            rules=DEFAULT_RETENTION_RULES,
            reason="Default Messaging v1 production retention baseline.",
            acknowledged_school_policy=True,
            created_by_membership_id=membership.id,
        ))
    db.commit()
    db.refresh(row)
    return row


def require_owner(db: Session, membership: Membership) -> SchoolSystemOwner:
    state = owner_state(db, school_id=membership.school_id, record_recovery=True)
    if state.recovery_required or state.row is None:
        raise GovernanceConflict("System Owner recovery is required")
    if state.row.membership_id != membership.id:
        raise GovernanceForbidden("Only the current System Owner may perform this action")
    return state.row


def transfer_owner(
    db: Session,
    *,
    actor_membership: Membership,
    target_membership_id: int,
    confirmation_membership_id: int,
    reason: str,
) -> SchoolSystemOwner:
    clean_reason = (reason or "").strip()
    if len(clean_reason) < 8 or len(clean_reason) > 2000:
        raise GovernanceConflict("A meaningful transfer reason is required")
    if confirmation_membership_id != target_membership_id:
        raise GovernanceConflict("Transfer confirmation does not match the selected administrator")
    db.query(School).filter(School.id == actor_membership.school_id).with_for_update().one()
    row = require_owner(db, actor_membership)
    if target_membership_id == row.membership_id:
        raise GovernanceConflict("The selected administrator is already the System Owner")
    target = _active_admin(
        db,
        school_id=actor_membership.school_id,
        membership_id=target_membership_id,
    )
    if target is None:
        raise GovernanceConflict("The new System Owner must be an active administrator in this school")
    previous_id = row.membership_id
    row.membership_id = target_membership_id
    row.owner_version += 1
    row.owner_since = invite_tokens.now_utc()
    db.add(
        SchoolSystemOwnerEvent(
            school_id=actor_membership.school_id,
            action="transfer",
            previous_membership_id=previous_id,
            new_membership_id=target_membership_id,
            actor_kind="school_owner",
            actor_user_id=actor_membership.user_id,
            actor_membership_id=actor_membership.id,
            reason=clean_reason,
            owner_version=row.owner_version,
        )
    )
    _ensure_owner_permissions(
        db,
        school_id=actor_membership.school_id,
        membership_id=target_membership_id,
    )
    db.commit()
    db.refresh(row)
    return row


def platform_recover_owner(
    db: Session,
    *,
    school_id: int,
    target_membership_id: int,
    actor_user_id: int,
    reason: str,
) -> SchoolSystemOwner:
    clean_reason = (reason or "").strip()
    if len(clean_reason) < 8 or len(clean_reason) > 2000:
        raise GovernanceConflict("A meaningful emergency recovery reason is required")
    db.query(School).filter(School.id == school_id).with_for_update().one()
    target = _active_admin(db, school_id=school_id, membership_id=target_membership_id)
    if target is None:
        raise GovernanceConflict("Recovery target must be an active administrator in this school")
    row = db.query(SchoolSystemOwner).filter(SchoolSystemOwner.school_id == school_id).first()
    previous_id = row.membership_id if row is not None else None
    version = (row.owner_version + 1) if row is not None else 1
    if row is None:
        row = SchoolSystemOwner(
            school_id=school_id,
            membership_id=target_membership_id,
            owner_version=version,
        )
        db.add(row)
    else:
        row.membership_id = target_membership_id
        row.owner_version = version
        row.owner_since = invite_tokens.now_utc()
    db.add(
        SchoolSystemOwnerEvent(
            school_id=school_id,
            action="platform_recovery",
            previous_membership_id=previous_id,
            new_membership_id=target_membership_id,
            actor_kind="platform_admin",
            actor_user_id=actor_user_id,
            reason=clean_reason,
            owner_version=version,
        )
    )
    _ensure_owner_permissions(db, school_id=school_id, membership_id=target_membership_id)
    db.commit()
    db.refresh(row)
    return row

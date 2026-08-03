"""Canonical school capability registry and dynamic entitlement enforcement."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Iterable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .auth import get_current_user
from .database import get_db
from .models_school import GuardianLink, Membership, SchoolEntitlement, User
from .school_scope import _school_id_from_request


HOMEWORK_DIARY = "homework_diary"
NOTICES_CALENDAR = "notices_calendar"
BEHAVIOUR_POINTS = "behaviour_points"
POSITIVE_RECOGNITION = "positive_recognition"
SURVEYS_POLLS = "surveys_polls"
SCHOOL_CHATS = "school_chats"
CHAT_PHOTOS = "chat_photos"
VOICE_NOTES = "voice_notes"
FAMILY_CONNECTION = "family_connection"
SCHOOL_FAMILY_UPDATES = "school_family_updates"
UPDATE_PHOTOS = "update_photos"
REPORTS_INSIGHTS = "reports_insights"
SAFEGUARDING = "safeguarding"
STUDENT_STAFF_IMPORT_EXPORT = "student_staff_import_export"


@dataclass(frozen=True)
class CapabilityDefinition:
    key: str
    dependencies: tuple[str, ...] = ()


CAPABILITY_REGISTRY: tuple[CapabilityDefinition, ...] = (
    CapabilityDefinition(HOMEWORK_DIARY),
    CapabilityDefinition(NOTICES_CALENDAR),
    CapabilityDefinition(BEHAVIOUR_POINTS),
    CapabilityDefinition(POSITIVE_RECOGNITION, (BEHAVIOUR_POINTS,)),
    CapabilityDefinition(SURVEYS_POLLS),
    CapabilityDefinition(SCHOOL_CHATS),
    CapabilityDefinition(CHAT_PHOTOS, (SCHOOL_CHATS,)),
    CapabilityDefinition(VOICE_NOTES, (SCHOOL_CHATS,)),
    CapabilityDefinition(FAMILY_CONNECTION),
    CapabilityDefinition(SCHOOL_FAMILY_UPDATES, (FAMILY_CONNECTION,)),
    CapabilityDefinition(UPDATE_PHOTOS, (SCHOOL_FAMILY_UPDATES,)),
    CapabilityDefinition(REPORTS_INSIGHTS),
    CapabilityDefinition(SAFEGUARDING),
    CapabilityDefinition(STUDENT_STAFF_IMPORT_EXPORT),
)
CAPABILITIES = {definition.key: definition for definition in CAPABILITY_REGISTRY}

FOUNDATION_CAPABILITIES: tuple[str, ...] = (
    "identity_and_access",
    "school_structure",
    "people_and_assignments",
    "security_and_auditing",
    "entitlement_management",
)

FAMILY_CATEGORY_CAPABILITY = {
    "homework": HOMEWORK_DIARY,
    "notice": NOTICES_CALENDAR,
    "calendar": NOTICES_CALENDAR,
    "points": BEHAVIOUR_POINTS,
    "update": SCHOOL_FAMILY_UPDATES,
    "survey": SURVEYS_POLLS,
}


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def entitlement_is_effective(row: SchoolEntitlement | None, *, on_date: date | None = None) -> bool:
    if row is None or not bool(row.enabled):
        return False
    current = on_date or utc_today()
    return row.effective_from <= current and (row.expires_on is None or row.expires_on >= current)


def entitlement_rows(db: Session, school_id: int) -> dict[str, SchoolEntitlement]:
    return {
        row.capability: row
        for row in db.query(SchoolEntitlement)
        .filter(SchoolEntitlement.school_id == school_id)
        .all()
    }


def enabled_capabilities(db: Session, school_id: int, *, on_date: date | None = None) -> set[str]:
    rows = entitlement_rows(db, school_id)
    effective = {
        key for key, row in rows.items()
        if key in CAPABILITIES and entitlement_is_effective(row, on_date=on_date)
    }
    changed = True
    while changed:
        changed = False
        for key in tuple(effective):
            if any(dependency not in effective for dependency in CAPABILITIES[key].dependencies):
                effective.remove(key)
                changed = True
    return effective


def capability_enabled(db: Session, school_id: int, capability: str, *, on_date: date | None = None) -> bool:
    if capability not in CAPABILITIES:
        raise ValueError(f"Unknown school capability: {capability}")
    return capability in enabled_capabilities(db, school_id, on_date=on_date)


def capabilities_enabled(db: Session, school_id: int, capabilities: Iterable[str]) -> bool:
    effective = enabled_capabilities(db, school_id)
    return all(capability in effective for capability in capabilities)


def capability_unavailable(capability: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "capability_not_enabled", "capability": capability},
    )


def ensure_capability(db: Session, school_id: int, capability: str) -> None:
    if not capability_enabled(db, school_id, capability):
        raise capability_unavailable(capability)


def ensure_capabilities(db: Session, school_id: int, *capabilities: str) -> None:
    effective = enabled_capabilities(db, school_id)
    for capability in capabilities:
        if capability not in effective:
            raise capability_unavailable(capability)


def require_school_entitlement(capability: str):
    if capability not in CAPABILITIES:
        raise ValueError(f"Unknown school capability: {capability}")

    def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> None:
        try:
            school_id = _school_id_from_request(request)
        except HTTPException as exc:
            if exc.status_code != status.HTTP_400_BAD_REQUEST or exc.detail != "School context required":
                raise
            school_ids = {
                row[0]
                for row in db.query(Membership.school_id)
                .filter(
                    Membership.user_id == current_user.id,
                    Membership.status == "active",
                    Membership.revoked_at.is_(None),
                )
                .all()
            }
            school_ids.update(
                row[0]
                for row in db.query(GuardianLink.school_id)
                .filter(
                    GuardianLink.user_id == current_user.id,
                    GuardianLink.status == "active",
                    GuardianLink.revoked_at.is_(None),
                )
                .all()
            )
            if len(school_ids) != 1:
                raise
            school_id = next(iter(school_ids))
        ensure_capability(db, school_id, capability)

    return dependency


def require_school_entitlements(*capabilities: str):
    for capability in capabilities:
        if capability not in CAPABILITIES:
            raise ValueError(f"Unknown school capability: {capability}")

    single_dependencies = [require_school_entitlement(capability) for capability in capabilities]

    def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> None:
        for single_dependency in single_dependencies:
            single_dependency(request=request, current_user=current_user, db=db)

    return dependency

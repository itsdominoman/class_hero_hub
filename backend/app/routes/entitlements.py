from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from ..database import get_db
from ..entitlement_service import (
    CAPABILITIES,
    CAPABILITY_REGISTRY,
    FOUNDATION_CAPABILITIES,
    enabled_capabilities,
    entitlement_rows,
    utc_today,
)
from ..models_school import (
    Membership,
    School,
    SchoolEntitlement,
    SchoolEntitlementEvent,
    User,
)
from ..school_scope import (
    require_manage_school_entitlements,
    require_school_role,
    write_audit,
)


platform_router = APIRouter(dependencies=[Depends(require_manage_school_entitlements)])
school_router = APIRouter(dependencies=[Depends(require_school_role("school_admin"))])


class EntitlementUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    source: Literal["pilot", "trial", "paid", "complimentary"]
    effective_from: date
    expires_on: date | None = None
    internal_note: str | None = Field(default=None, max_length=2000)
    expected_entitlement_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def valid_dates(self):
        if self.expires_on is not None and self.expires_on < self.effective_from:
            raise ValueError("Expiry date cannot be before the effective date")
        return self


@dataclass(frozen=True)
class _Window:
    enabled: bool
    effective_from: date
    expires_on: date | None


def _school(db: Session, school_id: int) -> School:
    row = db.query(School).filter(School.id == school_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")
    return row


def _validate_combination(rows: dict[str, SchoolEntitlement], capability: str, body: EntitlementUpdate) -> None:
    windows = {
        key: _Window(bool(row.enabled), row.effective_from, row.expires_on)
        for key, row in rows.items()
        if key in CAPABILITIES
    }
    windows[capability] = _Window(body.enabled, body.effective_from, body.expires_on)
    for child_key, definition in CAPABILITIES.items():
        child = windows.get(child_key)
        if child is None or not child.enabled:
            continue
        for dependency_key in definition.dependencies:
            parent = windows.get(dependency_key)
            if parent is None or not parent.enabled:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "entitlement_dependency_required",
                        "capability": child_key,
                        "dependency": dependency_key,
                    },
                )
            if parent.effective_from > child.effective_from:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "entitlement_dependency_window",
                        "capability": child_key,
                        "dependency": dependency_key,
                    },
                )
            if child.expires_on is None and parent.expires_on is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "entitlement_dependency_window",
                        "capability": child_key,
                        "dependency": dependency_key,
                    },
                )
            if (
                child.expires_on is not None
                and parent.expires_on is not None
                and parent.expires_on < child.expires_on
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "entitlement_dependency_window",
                        "capability": child_key,
                        "dependency": dependency_key,
                    },
                )


def _last_event(db: Session, row: SchoolEntitlement) -> tuple[SchoolEntitlementEvent | None, User | None]:
    result = (
        db.query(SchoolEntitlementEvent, User)
        .join(User, User.id == SchoolEntitlementEvent.actor_user_id)
        .filter(SchoolEntitlementEvent.entitlement_id == row.id)
        .order_by(SchoolEntitlementEvent.occurred_at.desc(), SchoolEntitlementEvent.id.desc())
        .first()
    )
    return result if result is not None else (None, None)


def _payloads(db: Session, school_id: int, *, include_internal: bool) -> list[dict]:
    rows = entitlement_rows(db, school_id)
    effective = enabled_capabilities(db, school_id)
    payloads = []
    for definition in CAPABILITY_REGISTRY:
        row = rows.get(definition.key)
        event, actor = _last_event(db, row) if row is not None else (None, None)
        payload = {
            "capability": definition.key,
            "dependencies": list(definition.dependencies),
            "enabled": bool(row.enabled) if row is not None else False,
            "effective_enabled": definition.key in effective,
            "source": row.source if row is not None else None,
            "effective_from": row.effective_from if row is not None else None,
            "expires_on": row.expires_on if row is not None else None,
            "entitlement_version": row.entitlement_version if row is not None else None,
            "last_changed_at": event.occurred_at if event is not None else None,
        }
        if include_internal:
            payload["internal_note"] = row.internal_note if row is not None else None
            payload["last_actor"] = (
                {"id": actor.id, "name": actor.name, "email": actor.email}
                if actor is not None
                else None
            )
        payloads.append(payload)
    return payloads


def _response(db: Session, school: School, *, include_internal: bool) -> dict:
    return {
        "school": {"id": school.id, "name": school.name, "name_ar": school.name_ar},
        "foundation": list(FOUNDATION_CAPABILITIES),
        "entitlements": _payloads(db, school.id, include_internal=include_internal),
    }


@platform_router.get("/schools/{school_id}/entitlements")
def platform_entitlements(school_id: int, db: Session = Depends(get_db)):
    return _response(db, _school(db, school_id), include_internal=True)


@platform_router.put("/schools/{school_id}/entitlements/{capability}")
def update_entitlement(
    school_id: int,
    capability: str,
    body: EntitlementUpdate,
    actor: User = Depends(require_manage_school_entitlements),
    db: Session = Depends(get_db),
):
    school = _school(db, school_id)
    if capability not in CAPABILITIES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capability not found")
    rows = entitlement_rows(db, school_id)
    row = rows.get(capability)
    if row is not None:
        row = (
            db.query(SchoolEntitlement)
            .filter(SchoolEntitlement.id == row.id)
            .with_for_update()
            .one()
        )
        rows[capability] = row
        if body.expected_entitlement_version != row.entitlement_version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "entitlement_version_conflict",
                    "current_version": row.entitlement_version,
                },
            )
    elif body.expected_entitlement_version is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "entitlement_version_conflict", "current_version": None},
        )

    _validate_combination(rows, capability, body)
    note = (body.internal_note or "").strip() or None
    previous_enabled = bool(row.enabled) if row is not None else None
    if row is None:
        row = SchoolEntitlement(
            school_id=school_id,
            capability=capability,
            entitlement_version=1,
            updated_by_user_id=actor.id,
        )
        db.add(row)
        action = "created"
    else:
        row.entitlement_version += 1
        action = "enabled" if body.enabled and not previous_enabled else "disabled" if not body.enabled and previous_enabled else "updated"

    row.enabled = body.enabled
    row.source = body.source
    row.effective_from = body.effective_from
    row.expires_on = body.expires_on
    row.internal_note = note
    row.updated_by_user_id = actor.id
    db.flush()
    event = SchoolEntitlementEvent(
        school_id=school_id,
        entitlement_id=row.id,
        capability=capability,
        enabled=body.enabled,
        source=body.source,
        effective_from=body.effective_from,
        expires_on=body.expires_on,
        internal_note=note,
        entitlement_version=row.entitlement_version,
        action=action,
        actor_user_id=actor.id,
    )
    db.add(event)
    write_audit(
        db,
        actor,
        "platform.school_entitlement.changed",
        row,
        {
            "capability": capability,
            "enabled": body.enabled,
            "source": body.source,
            "effective_from": body.effective_from.isoformat(),
            "expires_on": body.expires_on.isoformat() if body.expires_on else None,
            "entitlement_version": row.entitlement_version,
            "internal_note_changed": True,
        },
        school_id=school_id,
    )
    db.commit()
    db.refresh(row)
    return next(item for item in _payloads(db, school_id, include_internal=True) if item["capability"] == capability)


@school_router.get("/entitlements")
def school_entitlements(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    return _response(db, _school(db, membership.school_id), include_internal=False)

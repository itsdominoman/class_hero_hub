from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..feature_control_service import (
    VOICE_NOTES_DISCLOSURE_VERSION,
    VOICE_NOTES_FEATURE,
)
from ..models_school import (
    Membership,
    SchoolFeatureControl,
    SchoolFeatureControlAuditEvent,
)
from ..school_scope import require_school_role, write_audit


router = APIRouter(dependencies=[Depends(require_school_role("school_admin"))])


class FeatureControlUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    expected_control_version: int = Field(ge=1)
    disclosure_version: str = Field(min_length=1, max_length=40)
    acknowledged: bool


def _payload(row: SchoolFeatureControl) -> dict:
    return {
        "feature": row.feature,
        "enabled": bool(row.enabled),
        "control_version": row.control_version,
        "disclosure_version": VOICE_NOTES_DISCLOSURE_VERSION,
        "updated_at": row.updated_at,
        "acknowledgement_items": [
            "applicable_law",
            "guardian_consent",
            "staff_acceptable_use",
            "safeguarding",
            "retention_deletion",
            "accessibility",
        ],
    }


def _ensure_voice_control(db: Session, membership: Membership) -> SchoolFeatureControl:
    row = (
        db.query(SchoolFeatureControl)
        .filter(
            SchoolFeatureControl.school_id == membership.school_id,
            SchoolFeatureControl.feature == VOICE_NOTES_FEATURE,
        )
        .first()
    )
    if row is not None:
        return row
    row = SchoolFeatureControl(
        school_id=membership.school_id,
        feature=VOICE_NOTES_FEATURE,
        enabled=False,
        control_version=1,
        disclosure_version=VOICE_NOTES_DISCLOSURE_VERSION,
        updated_by_membership_id=membership.id,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        membership.user_id,
        "feature_control.defaulted_disabled",
        ("school_feature_controls", row.id),
        {"feature": VOICE_NOTES_FEATURE, "control_version": 1},
        school_id=membership.school_id,
    )
    db.commit()
    db.refresh(row)
    return row


@router.get("/feature-controls")
def get_feature_controls(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    return {"voice_notes": _payload(_ensure_voice_control(db, membership))}


@router.put("/feature-controls/voice-notes")
def update_voice_notes_control(
    body: FeatureControlUpdate,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    if body.disclosure_version != VOICE_NOTES_DISCLOSURE_VERSION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The compliance disclosure changed; review it again",
        )
    if not body.acknowledged:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Compliance acknowledgement is required",
        )
    _ensure_voice_control(db, membership)
    row = (
        db.query(SchoolFeatureControl)
        .filter(
            SchoolFeatureControl.school_id == membership.school_id,
            SchoolFeatureControl.feature == VOICE_NOTES_FEATURE,
        )
        .with_for_update()
        .one()
    )
    if row.control_version != body.expected_control_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "feature_control_version_conflict",
                "current_version": row.control_version,
            },
        )
    if bool(row.enabled) == body.enabled:
        return _payload(row)

    row.enabled = body.enabled
    row.control_version += 1
    row.disclosure_version = VOICE_NOTES_DISCLOSURE_VERSION
    row.updated_by_membership_id = membership.id
    db.flush()
    db.add(
        SchoolFeatureControlAuditEvent(
            school_id=membership.school_id,
            feature=VOICE_NOTES_FEATURE,
            enabled=body.enabled,
            control_version=row.control_version,
            disclosure_version=VOICE_NOTES_DISCLOSURE_VERSION,
            acknowledging_user_id=membership.user_id,
            acknowledging_membership_id=membership.id,
        )
    )
    write_audit(
        db,
        membership.user_id,
        "feature_control.updated",
        ("school_feature_controls", row.id),
        {
            "feature": VOICE_NOTES_FEATURE,
            "enabled": body.enabled,
            "control_version": row.control_version,
            "disclosure_version": VOICE_NOTES_DISCLOSURE_VERSION,
            "acknowledgement_recorded": True,
        },
        school_id=membership.school_id,
    )
    db.commit()
    db.refresh(row)
    return _payload(row)

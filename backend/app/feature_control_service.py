"""Reusable school compliance/feature-control primitives."""
from __future__ import annotations

from sqlalchemy.orm import Session

from .entitlement_service import VOICE_NOTES, capability_enabled
from .models_school import SchoolFeatureControl


VOICE_NOTES_FEATURE = "voice_notes"
VOICE_NOTES_DISCLOSURE_VERSION = "voice-notes-2026-07-v1"


def voice_notes_enabled(
    db: Session,
    school_id: int,
    *,
    entitlement_enabled: bool | None = None,
) -> bool:
    if entitlement_enabled is None:
        entitlement_enabled = capability_enabled(db, school_id, VOICE_NOTES)
    if not entitlement_enabled:
        return False
    row = (
        db.query(SchoolFeatureControl.enabled)
        .filter(
            SchoolFeatureControl.school_id == school_id,
            SchoolFeatureControl.feature == VOICE_NOTES_FEATURE,
        )
        .first()
    )
    return bool(row and row[0])

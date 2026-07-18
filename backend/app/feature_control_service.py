"""Reusable school compliance/feature-control primitives."""
from __future__ import annotations

from sqlalchemy.orm import Session

from .models_school import SchoolFeatureControl


VOICE_NOTES_FEATURE = "voice_notes"
VOICE_NOTES_DISCLOSURE_VERSION = "voice-notes-2026-07-v1"


def voice_notes_enabled(db: Session, school_id: int) -> bool:
    row = (
        db.query(SchoolFeatureControl.enabled)
        .filter(
            SchoolFeatureControl.school_id == school_id,
            SchoolFeatureControl.feature == VOICE_NOTES_FEATURE,
        )
        .first()
    )
    return bool(row and row[0])

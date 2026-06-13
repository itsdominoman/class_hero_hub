"""B2 — school-bag "pack for tomorrow" checklist logic.

A `SchoolItemCheck` row means "this item was packed for this date". Absence of
a row = not packed (the implicit daily reset). A date's checklist is editable
only while the date is still in the future relative to the family's local
"today"; once that school day has begun it is locked (read-only). This keeps
the midnight boundary in the family timezone, reusing
`calendar_service.get_family_today`.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from .. import models


class SchoolCheckError(Exception):
    """Raised when a pack/unpack action is not allowed. ``code`` is a stable
    machine-readable reason the frontend maps to a localized message."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def is_date_locked(check_date: date, family_today: date) -> bool:
    """A checklist is read-only once its date has begun. Children may pack /
    unpack only while the target date is still in the future."""
    return check_date <= family_today


def family_has_school_items(db: Session, family_id: int) -> bool:
    """True if any child in the family has at least one active school item
    configured (on any weekday). Feeds the parent dashboard's decision to show
    or hide the "School items missing" summary tile — families that have never
    set up the feature shouldn't see a permanent "0" tile."""
    return (
        db.query(models.SchoolItem.id)
        .filter(
            models.SchoolItem.family_id == family_id,
            models.SchoolItem.is_active.is_(True),
        )
        .first()
        is not None
    )


def packed_item_ids(db: Session, child_id: int, item_ids: list[int], check_date: date) -> set[int]:
    if not item_ids:
        return set()
    rows = (
        db.query(models.SchoolItemCheck.school_item_id)
        .filter(
            models.SchoolItemCheck.child_id == child_id,
            models.SchoolItemCheck.check_date == check_date,
            models.SchoolItemCheck.school_item_id.in_(item_ids),
        )
        .all()
    )
    return {row[0] for row in rows}


def _require_item_for_child(db: Session, child_id: int, item_id: int) -> models.SchoolItem:
    item = (
        db.query(models.SchoolItem)
        .filter(
            models.SchoolItem.id == item_id,
            models.SchoolItem.child_id == child_id,
            models.SchoolItem.is_active.is_(True),
        )
        .first()
    )
    if item is None:
        raise SchoolCheckError("item_not_found")
    return item


def set_packed(
    db: Session,
    child_id: int,
    item_id: int,
    check_date: date,
    family_today: date,
    packed: bool,
) -> models.SchoolItemCheck | None:
    """Pack (packed=True) or unpack (packed=False) an item for a date.

    Idempotent: packing an already-packed item is a no-op, and unpacking a
    not-packed item is a no-op. Validates ownership, that the date matches the
    item's weekday, and that the date is not yet locked. Raises SchoolCheckError
    otherwise. Returns the check row when packed, or None when unpacked.
    """
    item = _require_item_for_child(db, child_id, item_id)

    if check_date.weekday() != item.weekday:
        raise SchoolCheckError("weekday_mismatch")

    if is_date_locked(check_date, family_today):
        raise SchoolCheckError("checklist_locked")

    existing = (
        db.query(models.SchoolItemCheck)
        .filter(
            models.SchoolItemCheck.school_item_id == item_id,
            models.SchoolItemCheck.check_date == check_date,
        )
        .first()
    )

    if packed:
        if existing is None:
            existing = models.SchoolItemCheck(
                school_item_id=item_id,
                child_id=child_id,
                check_date=check_date,
            )
            db.add(existing)
            db.commit()
            db.refresh(existing)
        return existing

    if existing is not None:
        db.delete(existing)
        db.commit()
    return None

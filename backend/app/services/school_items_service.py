"""B2 — school-bag "pack for tomorrow" checklist logic.

A `SchoolItemCheck` row means "this item was packed for this date". Absence of
a row = not packed (the implicit daily reset). A date's checklist is editable
only while the date is still in the future relative to the family's local
"today"; once that school day has begun it is locked (read-only). This keeps
the midnight boundary in the family timezone, reusing
`calendar_service.get_family_today`.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from .. import models


class SchoolCheckError(Exception):
    """Raised when a pack/unpack action is not allowed. ``code`` is a stable
    machine-readable reason the frontend maps to a localized message."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# D3 — time-windowed visibility for the parent "School Bag" summary, in the
# family's LOCAL time (derived from calendar_service.get_family_now). These are
# deliberately family-wide named constants, not per-child/per-family settings:
# 6pm is a parent reminder/nudge, not a child-facing deadline. Adjust here if
# the chosen hours don't feel right in practice.
#
# Boundaries (local family clock):
#   - "Needed today"   visible from midnight onward each day (the morning
#     accountability question: "did you pack what you needed last night?").
#   - "Pack for tomorrow" visible from 6pm to midnight ("tonight's checklist").
#
# The functions below are intentionally PURE (functions of local time / counts
# only, no DB) so a future push-notification scheduler can reuse the exact same
# relevance rules — evening "time to pack" + morning "what's still missing" —
# without re-deriving them. See PLAN.md "Scope C — Future".
NEEDED_TODAY_VISIBLE_FROM_HOUR = 0    # midnight
PACK_TOMORROW_VISIBLE_FROM_HOUR = 18  # 6pm

# Tile modes the summary endpoint resolves for the dashboard tile / a future
# notification trigger. "missing_today" = morning "you didn't pack X";
# "pack_tomorrow" = evening "pack the bag"; "none" = nothing to surface now.
TILE_MODE_MISSING_TODAY = "missing_today"
TILE_MODE_PACK_TOMORROW = "pack_tomorrow"
TILE_MODE_NONE = "none"


def needed_today_window_open(now_local: datetime) -> bool:
    """Whether the 'Needed today' section is within its visible window."""
    return now_local.hour >= NEEDED_TODAY_VISIBLE_FROM_HOUR


def pack_tomorrow_window_open(now_local: datetime) -> bool:
    """Whether the 'Pack for tomorrow' section is within its visible window."""
    return now_local.hour >= PACK_TOMORROW_VISIBLE_FROM_HOUR


def compute_tile_state(
    now_local: datetime,
    missing_today_count: int,
    pack_tomorrow_unpacked_count: int,
) -> tuple[str, int]:
    """Resolve the single dashboard-tile number + mode from the current local
    time and the family's aggregate counts. Pure: same inputs → same output, so
    a notification scheduler can call it directly.

    Morning accountability ("missing_today") takes priority over the evening
    "pack_tomorrow" nudge when both windows are open and both have content. When
    nothing is currently relevant the mode is "none" (caller hides the tile),
    which is how the tile naturally empties as items get resolved rather than
    persisting an "all packed" badge all morning."""
    if needed_today_window_open(now_local) and missing_today_count > 0:
        return TILE_MODE_MISSING_TODAY, missing_today_count
    if pack_tomorrow_window_open(now_local) and pack_tomorrow_unpacked_count > 0:
        return TILE_MODE_PACK_TOMORROW, pack_tomorrow_unpacked_count
    return TILE_MODE_NONE, 0


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
    enforce_lock: bool = True,
) -> models.SchoolItemCheck | None:
    """Pack (packed=True) or unpack (packed=False) an item for a date.

    Idempotent: packing an already-packed item is a no-op, and unpacking a
    not-packed item is a no-op. Validates ownership, that the date matches the
    item's weekday, and (when ``enforce_lock``) that the date is not yet locked.
    Raises SchoolCheckError otherwise. Returns the check row when packed, or None
    when unpacked.

    ``enforce_lock=False`` is the D2 parent override: once a school day has begun
    its checklist is locked for the CHILD (accountability for what they did the
    night before), but a parent may still mark a "Needed today" item packed to
    reflect that the child packed it this morning. Writes the same shared
    ``school_item_checks`` row, so the new state is consistent everywhere the
    data is read."""
    item = _require_item_for_child(db, child_id, item_id)

    if check_date.weekday() != item.weekday:
        raise SchoolCheckError("weekday_mismatch")

    if enforce_lock and is_date_locked(check_date, family_today):
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

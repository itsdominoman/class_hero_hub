from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import auth, child_auth, models, schemas
from ..services import calendar_service, school_items_service

router = APIRouter()
child_router = APIRouter()

LEGACY_SCHOOL_MARKER = "[[school-item]]"


def _parse_recurrence_days(value: str | None, fallback_date: date | None = None) -> list[int]:
    if value:
        days = [
            int(item)
            for item in value.split(",")
            if item.strip().isdigit() and 0 <= int(item) <= 6
        ]
        if days:
            return days
    if fallback_date is not None:
        return [fallback_date.weekday()]
    return []


def _legacy_school_item_text(description: str | None) -> str | None:
    if not description or not description.startswith(LEGACY_SCHOOL_MARKER):
        return None
    cleaned = description.replace(LEGACY_SCHOOL_MARKER, "", 1).strip()
    return cleaned or None


def _require_child_for_parent(
    db: Session,
    current_parent: models.ParentUser,
    child_id: int,
) -> models.Child:
    child = db.query(models.Child).filter(
        models.Child.id == child_id,
        models.Child.family_id == current_parent.family_id,
        models.Child.active.is_(True),
    ).first()
    if not child:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")
    return child


def _school_items_query(db: Session, child_id: int, weekday: int):
    return (
        db.query(models.SchoolItem)
        .filter(
            models.SchoolItem.child_id == child_id,
            models.SchoolItem.weekday == weekday,
            models.SchoolItem.is_active.is_(True),
        )
        .order_by(models.SchoolItem.sort_order.asc(), models.SchoolItem.id.asc())
    )


def _migrate_legacy_school_items_for_child(db: Session, child: models.Child) -> None:
    legacy_entries = (
        db.query(models.CalendarEntry)
        .filter(
            models.CalendarEntry.child_id == child.id,
            models.CalendarEntry.family_id == child.family_id,
            models.CalendarEntry.is_active.is_(True),
            models.CalendarEntry.description.isnot(None),
            models.CalendarEntry.description.like(f"{LEGACY_SCHOOL_MARKER}%"),
        )
        .order_by(models.CalendarEntry.created_at.asc(), models.CalendarEntry.id.asc())
        .all()
    )

    if not legacy_entries:
        return

    existing_items = db.query(models.SchoolItem).filter(
        models.SchoolItem.child_id == child.id,
        models.SchoolItem.is_active.is_(True),
    ).all()
    existing_lookup = {
        (item.weekday, item.class_name.strip().lower(), (item.needed_item or "").strip().lower())
        for item in existing_items
    }
    next_sort_order = defaultdict(int)
    for item in existing_items:
        next_sort_order[item.weekday] = max(next_sort_order[item.weekday], (item.sort_order or 0) + 1)

    migrated = False
    for entry in legacy_entries:
        needed_item = _legacy_school_item_text(entry.description)
        weekdays = _parse_recurrence_days(entry.recurrence_days, entry.start_date)
        if not weekdays:
            continue

        class_name = (entry.title or "").strip()
        if not class_name:
            continue

        for weekday in weekdays:
            key = (weekday, class_name.lower(), (needed_item or "").strip().lower())
            if key in existing_lookup:
                continue

            school_item = models.SchoolItem(
                family_id=entry.family_id,
                child_id=entry.child_id,
                weekday=weekday,
                class_name=class_name,
                needed_item=needed_item,
                sort_order=next_sort_order[weekday],
                is_active=True,
                created_by_parent_id=entry.created_by_parent_id,
            )
            next_sort_order[weekday] += 1
            db.add(school_item)
            existing_lookup.add(key)
            migrated = True

        entry.is_active = False
        migrated = True

    if migrated:
        db.commit()


def _serialize_school_items(items: list[models.SchoolItem]) -> list[schemas.SchoolItem]:
    return [schemas.SchoolItem.model_validate(item) for item in items]


def _school_items_for_date(db: Session, child: models.Child, target_date: date) -> list[schemas.SchoolItem]:
    _migrate_legacy_school_items_for_child(db, child)
    return _serialize_school_items(_school_items_query(db, child.id, target_date.weekday()).all())


def _school_items_for_date_with_packing(
    db: Session,
    child: models.Child,
    target_date: date,
    family_today: date,
) -> list[schemas.SchoolItemForDate]:
    """School items for a date, annotated with B2 packing state. `locked` means
    the date has begun (>= family today) so the checklist is read-only."""
    _migrate_legacy_school_items_for_child(db, child)
    items = _school_items_query(db, child.id, target_date.weekday()).all()
    packed_ids = school_items_service.packed_item_ids(
        db, child.id, [item.id for item in items], target_date
    )
    locked = school_items_service.is_date_locked(target_date, family_today)
    return [
        schemas.SchoolItemForDate(
            **schemas.SchoolItem.model_validate(item).model_dump(),
            check_date=target_date,
            packed=item.id in packed_ids,
            locked=locked,
        )
        for item in items
    ]


@router.get("/", response_model=List[schemas.SchoolItem])
async def get_school_items(
    child_id: int = Query(...),
    weekday: int = Query(..., ge=0, le=6),
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    child = _require_child_for_parent(db, current_parent, child_id)
    _migrate_legacy_school_items_for_child(db, child)
    return _serialize_school_items(_school_items_query(db, child.id, weekday).all())


@router.put("/", response_model=List[schemas.SchoolItem])
async def replace_school_items(
    items: List[schemas.SchoolItemUpsert],
    child_id: int = Query(...),
    weekday: int = Query(..., ge=0, le=6),
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    child = _require_child_for_parent(db, current_parent, child_id)
    _migrate_legacy_school_items_for_child(db, child)

    existing_items = _school_items_query(db, child.id, weekday).all()
    existing_by_id = {item.id: item for item in existing_items}
    kept_ids: set[int] = {item_in.id for item_in in items if item_in.id is not None}
    saved_items: list[models.SchoolItem] = []

    for index, item_in in enumerate(items):
        class_name = item_in.class_name.strip()
        if not class_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Class name is required")

        needed_item = item_in.needed_item.strip() if item_in.needed_item else None

        if item_in.id is not None:
            school_item = existing_by_id.get(item_in.id)
            if not school_item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School item not found")
            school_item.class_name = class_name
            school_item.needed_item = needed_item or None
            school_item.sort_order = index
            school_item.is_active = bool(item_in.is_active)
        else:
            school_item = models.SchoolItem(
                family_id=current_parent.family_id,
                child_id=child.id,
                weekday=weekday,
                class_name=class_name,
                needed_item=needed_item or None,
                sort_order=index,
                is_active=True,
                created_by_parent_id=current_parent.id,
            )
            db.add(school_item)
        saved_items.append(school_item)

    for existing_item in existing_items:
        if existing_item.id not in kept_ids:
            db.delete(existing_item)

    db.commit()
    for item in saved_items:
        db.refresh(item)

    return _serialize_school_items(
        _school_items_query(db, child.id, weekday).all()
    )


@router.get("/configured", response_model=schemas.SchoolItemsConfigured)
async def get_school_items_configured(
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    """Whether this family has set up any school items at all. The parent
    dashboard uses this to hide the school summary tile for families not using
    the feature (rather than showing a permanent "0")."""
    configured = school_items_service.family_has_school_items(db, current_parent.family_id)
    return schemas.SchoolItemsConfigured(configured=configured)


@router.get("/today", response_model=List[schemas.SchoolItemForDate])
async def get_school_items_today(
    child_id: int = Query(...),
    offset: int = Query(0, ge=0, le=1),
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    child = _require_child_for_parent(db, current_parent, child_id)
    family = child.family
    if not family:
        return []

    family_today = calendar_service.get_family_today(family.timezone)
    target_date = family_today + timedelta(days=offset)
    return _school_items_for_date_with_packing(db, child, target_date, family_today)


def _build_school_summary(
    db: Session,
    family: models.Family,
) -> schemas.SchoolSummary:
    """D3 — assemble the time-windowed parent School Bag summary. Pure window /
    tile rules live in school_items_service (reusable for notifications); this
    function only does the DB gathering and stitches them together.

    - "Needed today" (today's items) is included per child only when its window
      is open AND the child still has an unpacked item — resolved children drop
      out so the section empties as the morning progresses.
    - "Pack for tomorrow" (tomorrow's items) is included per child only when its
      window is open and the child has items for tomorrow (all-packed children
      still show, as a positive evening checklist)."""
    now_local = calendar_service.get_family_now(family.timezone)
    family_today = now_local.date()
    tomorrow = family_today + timedelta(days=1)

    configured = school_items_service.family_has_school_items(db, family.id)
    show_needed_today = school_items_service.needed_today_window_open(now_local)
    show_pack_tomorrow = school_items_service.pack_tomorrow_window_open(now_local)

    children = (
        db.query(models.Child)
        .filter(models.Child.family_id == family.id, models.Child.active.is_(True))
        .order_by(models.Child.id.asc())
        .all()
    )

    needed_today: list[schemas.SchoolSummaryChild] = []
    pack_tomorrow: list[schemas.SchoolSummaryChild] = []
    missing_today_count = 0
    pack_tomorrow_unpacked_count = 0

    if show_needed_today:
        for child in children:
            items = _school_items_for_date_with_packing(db, child, family_today, family_today)
            missing = [item for item in items if not item.packed]
            if missing:  # resolved children drop out of the section entirely
                needed_today.append(
                    schemas.SchoolSummaryChild(child_id=child.id, items=items)
                )
                missing_today_count += len(missing)

    if show_pack_tomorrow:
        for child in children:
            items = _school_items_for_date_with_packing(db, child, tomorrow, family_today)
            if items:
                pack_tomorrow.append(
                    schemas.SchoolSummaryChild(child_id=child.id, items=items)
                )
                pack_tomorrow_unpacked_count += sum(1 for item in items if not item.packed)

    tile_mode, tile_count = school_items_service.compute_tile_state(
        now_local, missing_today_count, pack_tomorrow_unpacked_count
    )

    return schemas.SchoolSummary(
        configured=configured,
        show_needed_today=show_needed_today,
        show_pack_tomorrow=show_pack_tomorrow,
        tile_count=tile_count,
        tile_mode=tile_mode,
        needed_today=needed_today,
        pack_tomorrow=pack_tomorrow,
    )


@router.get("/summary", response_model=schemas.SchoolSummary)
async def get_school_summary(
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    """D3 — the parent dashboard's single source for the School Bag tile + modal.
    Time-windowed in the family's local timezone so the client only receives the
    sections it should currently show."""
    family = db.query(models.Family).filter(models.Family.id == current_parent.family_id).first()
    if not family:
        return schemas.SchoolSummary(
            configured=False,
            show_needed_today=False,
            show_pack_tomorrow=False,
            tile_count=0,
            tile_mode=school_items_service.TILE_MODE_NONE,
            needed_today=[],
            pack_tomorrow=[],
        )
    return _build_school_summary(db, family)


@router.post("/{item_id}/pack", response_model=schemas.SchoolItemCheckState)
async def parent_pack_today_item(
    item_id: int,
    req: schemas.ParentPackTodayRequest,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    """D2 — parent marks a still-missing "Needed today" item as packed for today.

    Unlike the child pack route this bypasses the midnight lock (the child's own
    today checklist stays locked read-only — their record of last night), and
    only ever targets today: the parent is confirming current reality after the
    school day has begun. Writes the shared school_item_checks row so the
    resolution is reflected everywhere the data is read."""
    child = _require_child_for_parent(db, current_parent, req.child_id)
    family_today = _child_family_today(child)
    try:
        school_items_service.set_packed(
            db, child.id, item_id, family_today, family_today, packed=True, enforce_lock=False
        )
    except school_items_service.SchoolCheckError as exc:
        status_code = {
            "item_not_found": status.HTTP_404_NOT_FOUND,
            "weekday_mismatch": status.HTTP_400_BAD_REQUEST,
        }.get(exc.code, status.HTTP_400_BAD_REQUEST)
        raise HTTPException(status_code=status_code, detail=exc.code)

    return schemas.SchoolItemCheckState(
        school_item_id=item_id,
        check_date=family_today,
        packed=True,
        locked=school_items_service.is_date_locked(family_today, family_today),
    )


@child_router.get("/today", response_model=List[schemas.SchoolItemForDate])
async def get_my_school_items_today(
    offset: int = Query(0, ge=0, le=1),
    db: Session = Depends(get_db),
    current_child: models.Child = Depends(child_auth.get_current_child),
):
    child = current_child
    family = child.family
    if not family:
        return []

    family_today = calendar_service.get_family_today(family.timezone)
    target_date = family_today + timedelta(days=offset)
    return _school_items_for_date_with_packing(db, child, target_date, family_today)


def _child_family_today(child: models.Child) -> date:
    family = child.family
    timezone = family.timezone if family else "UTC"
    return calendar_service.get_family_today(timezone)


def _pack_state_or_error(
    db: Session,
    child: models.Child,
    item_id: int,
    check_date: date,
    packed: bool,
) -> schemas.SchoolItemCheckState:
    family_today = _child_family_today(child)
    try:
        school_items_service.set_packed(
            db, child.id, item_id, check_date, family_today, packed=packed
        )
    except school_items_service.SchoolCheckError as exc:
        status_code = {
            "item_not_found": status.HTTP_404_NOT_FOUND,
            "checklist_locked": status.HTTP_409_CONFLICT,
            "weekday_mismatch": status.HTTP_400_BAD_REQUEST,
        }.get(exc.code, status.HTTP_400_BAD_REQUEST)
        raise HTTPException(status_code=status_code, detail=exc.code)

    return schemas.SchoolItemCheckState(
        school_item_id=item_id,
        check_date=check_date,
        packed=packed,
        locked=school_items_service.is_date_locked(check_date, family_today),
    )


@child_router.post("/{item_id}/pack", response_model=schemas.SchoolItemCheckState)
async def pack_my_school_item(
    item_id: int,
    req: schemas.SchoolItemPackRequest,
    db: Session = Depends(get_db),
    current_child: models.Child = Depends(child_auth.get_current_child),
):
    return _pack_state_or_error(db, current_child, item_id, req.check_date, packed=True)


@child_router.delete("/{item_id}/pack", response_model=schemas.SchoolItemCheckState)
async def unpack_my_school_item(
    item_id: int,
    check_date: date = Query(...),
    db: Session = Depends(get_db),
    current_child: models.Child = Depends(child_auth.get_current_child),
):
    return _pack_state_or_error(db, current_child, item_id, check_date, packed=False)

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import auth, child_auth, models, schemas
from ..services import calendar_service

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


@router.get("/today", response_model=List[schemas.SchoolItem])
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

    target_date = calendar_service.get_family_today(family.timezone) + timedelta(days=offset)
    return _school_items_for_date(db, child, target_date)


@child_router.get("/today", response_model=List[schemas.SchoolItem])
async def get_my_school_items_today(
    offset: int = Query(0, ge=0, le=1),
    db: Session = Depends(get_db),
    current_child: models.Child = Depends(child_auth.get_current_child),
):
    child = current_child
    family = child.family
    if not family:
        return []

    target_date = calendar_service.get_family_today(family.timezone) + timedelta(days=offset)
    return _school_items_for_date(db, child, target_date)

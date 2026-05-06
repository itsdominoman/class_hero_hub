from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timezone
from ..database import get_db
from .. import models, schemas, child_auth
from ..services import calendar_service

router = APIRouter()
LEGACY_SCHOOL_MARKER = "[[school-item]]"


def _is_legacy_school_entry(entry: models.CalendarEntry) -> bool:
    return bool(entry.description and entry.description.startswith(LEGACY_SCHOOL_MARKER))

@router.get("/", response_model=List[dict])
async def get_my_calendar(
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: Session = Depends(get_db),
    current_child: models.Child = Depends(child_auth.get_current_child)
):
    entries = db.query(models.CalendarEntry).filter(
        models.CalendarEntry.child_id == current_child.id,
        models.CalendarEntry.is_active == True
    ).all()
    entries = [entry for entry in entries if not _is_legacy_school_entry(entry)]

    resolved = []
    for entry in entries:
        dates = calendar_service.resolve_occurrences(entry, from_date, to_date)
        for d in dates:
            completion = db.query(models.CalendarCompletion).filter(
                models.CalendarCompletion.entry_id == entry.id,
                models.CalendarCompletion.occurrence_date == d
            ).first()
            
            resolved.append({
                "entry": schemas.CalendarEntry.model_validate(entry),
                "occurrence_date": d,
                "completion": schemas.CalendarCompletion.model_validate(completion) if completion else None
            })
    
    return sorted(resolved, key=lambda x: (x["occurrence_date"], x["entry"].start_time or datetime.min.time()))

@router.post("/{entry_id}/complete", response_model=schemas.CalendarCompletion)
async def child_complete_task(
    entry_id: int,
    occurrence_date: date,
    db: Session = Depends(get_db),
    current_child: models.Child = Depends(child_auth.get_current_child)
):
    entry = db.query(models.CalendarEntry).filter(
        models.CalendarEntry.id == entry_id,
        models.CalendarEntry.child_id == current_child.id,
        models.CalendarEntry.is_active == True
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Task not found")

    if entry.entry_type != "task":
        raise HTTPException(status_code=400, detail="Only tasks can be completed")

    # Check for existing completion
    existing = db.query(models.CalendarCompletion).filter(
        models.CalendarCompletion.entry_id == entry_id,
        models.CalendarCompletion.child_id == current_child.id,
        models.CalendarCompletion.occurrence_date == occurrence_date
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already completed for this date")

    completion = models.CalendarCompletion(
        entry_id=entry_id,
        child_id=current_child.id,
        occurrence_date=occurrence_date,
        status="pending",
        completed_at=datetime.now(timezone.utc)
    )
    db.add(completion)
    db.commit()
    db.refresh(completion)
    return completion

@router.get("/streak", response_model=Optional[schemas.WeeklyStreak])
async def get_my_current_streak(
    db: Session = Depends(get_db),
    current_child: models.Child = Depends(child_auth.get_current_child)
):
    # This might need family timezone to determine "current" week
    family = db.query(models.Family).get(current_child.family_id)
    today = calendar_service.get_family_today(family.timezone)
    week_start, _ = calendar_service.get_week_bounds(today, family.week_start_day)
    
    return db.query(models.WeeklyStreak).filter(
        models.WeeklyStreak.child_id == current_child.id,
        models.WeeklyStreak.week_start_date == week_start
    ).first()

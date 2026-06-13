from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timezone, timedelta
from ..database import get_db
from .. import models, schemas, auth
from ..services import calendar_service, points_service

router = APIRouter()
LEGACY_SCHOOL_MARKER = "[[school-item]]"


def _is_legacy_school_entry(entry: models.CalendarEntry) -> bool:
    return bool(entry.description and entry.description.startswith(LEGACY_SCHOOL_MARKER))


def _family_timezone(db: Session, family_id: int) -> str:
    family = db.query(models.Family).filter(models.Family.id == family_id).first()
    return family.timezone if family and family.timezone else "UTC"


def _resolve_child_occurrences(
    db: Session,
    child_id: int,
    from_date: date,
    to_date: date,
) -> list[dict]:
    """Resolve a child's active (non-legacy) calendar entries into dated
    occurrences over [from_date, to_date], each annotated with its completion.
    Shared by the per-child list endpoint and the dashboard summary so both read
    occurrences the same way."""
    entries = db.query(models.CalendarEntry).filter(
        models.CalendarEntry.child_id == child_id,
        models.CalendarEntry.is_active == True
    ).all()
    entries = [entry for entry in entries if not _is_legacy_school_entry(entry)]

    resolved = []
    for entry in entries:
        for d in calendar_service.resolve_occurrences(entry, from_date, to_date):
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


@router.get("/", response_model=List[dict])
async def get_calendar(
    child_id: int,
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    # Verify child belongs to family
    child = db.query(models.Child).filter(
        models.Child.id == child_id,
        models.Child.family_id == current_parent.family_id
    ).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    return _resolve_child_occurrences(db, child_id, from_date, to_date)


@router.get("/summary", response_model=schemas.CalendarSummary)
async def get_calendar_summary(
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    """E1 — the parent dashboard "Today" tile + modal. Returns today's per-child
    events/tasks (primary) and a lighter tomorrow look-ahead, plus the badge
    count (today's events + outstanding tasks) and whether the family has ever
    configured any calendar entry (hide-when-unused, like the school bag tile).
    """
    family_id = current_parent.family_id
    today = calendar_service.get_family_today(_family_timezone(db, family_id))
    tomorrow = today + timedelta(days=1)

    configured = db.query(models.CalendarEntry.id).filter(
        models.CalendarEntry.family_id == family_id,
        models.CalendarEntry.is_active == True
    ).first() is not None

    children = db.query(models.Child).filter(
        models.Child.family_id == family_id,
        models.Child.active == True
    ).order_by(models.Child.id.asc()).all()

    today_by_child: list[schemas.CalendarSummaryChild] = []
    tomorrow_by_child: list[schemas.CalendarSummaryChild] = []
    tile_count = 0

    for child in children:
        today_items = _resolve_child_occurrences(db, child.id, today, today)
        tomorrow_items = _resolve_child_occurrences(db, child.id, tomorrow, tomorrow)

        if today_items:
            today_by_child.append(
                schemas.CalendarSummaryChild(child_id=child.id, items=today_items)
            )
            tile_count += calendar_service.count_attention_items(
                [
                    (occ["entry"].entry_type, occ["completion"].status if occ["completion"] else None)
                    for occ in today_items
                ]
            )
        if tomorrow_items:
            tomorrow_by_child.append(
                schemas.CalendarSummaryChild(child_id=child.id, items=tomorrow_items)
            )

    return schemas.CalendarSummary(
        configured=configured,
        tile_count=tile_count,
        today=today_by_child,
        tomorrow=tomorrow_by_child,
    )

@router.post("/", response_model=schemas.CalendarEntry)
async def create_calendar_entry(
    entry_in: schemas.CalendarEntryCreate,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    # Verify child
    child = db.query(models.Child).filter(
        models.Child.id == entry_in.child_id,
        models.Child.family_id == current_parent.family_id
    ).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    db_entry = models.CalendarEntry(
        **entry_in.model_dump(),
        family_id=current_parent.family_id,
        created_by_parent_id=current_parent.id
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

@router.patch("/{entry_id}", response_model=schemas.CalendarEntry)
async def update_calendar_entry(
    entry_id: int,
    entry_in: schemas.CalendarEntryBase,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    db_entry = db.query(models.CalendarEntry).filter(
        models.CalendarEntry.id == entry_id,
        models.CalendarEntry.family_id == current_parent.family_id
    ).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    for field, value in entry_in.model_dump(exclude_unset=True).items():
        setattr(db_entry, field, value)

    db.commit()
    db.refresh(db_entry)
    return db_entry

@router.delete("/{entry_id}")
async def delete_calendar_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    db_entry = db.query(models.CalendarEntry).filter(
        models.CalendarEntry.id == entry_id,
        models.CalendarEntry.family_id == current_parent.family_id
    ).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    db_entry.is_active = False
    db.commit()
    return {"status": "success"}

@router.post("/{entry_id}/complete", response_model=schemas.CalendarCompletion)
async def parent_complete_task(
    entry_id: int,
    occurrence_date: date,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    db_entry = db.query(models.CalendarEntry).filter(
        models.CalendarEntry.id == entry_id,
        models.CalendarEntry.family_id == current_parent.family_id
    ).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Check if already completed
    existing = db.query(models.CalendarCompletion).filter(
        models.CalendarCompletion.entry_id == entry_id,
        models.CalendarCompletion.occurrence_date == occurrence_date
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already completed for this date")

    completion = models.CalendarCompletion(
        entry_id=entry_id,
        child_id=db_entry.child_id,
        occurrence_date=occurrence_date,
        status="approved",
        completed_at=datetime.now(timezone.utc),
        reviewed_at=datetime.now(timezone.utc),
        reviewed_by_parent_id=current_parent.id,
        base_points=db_entry.points_value if db_entry.is_rewardable else 0
    )

    if db_entry.is_rewardable and db_entry.points_value:
        # Check for streak bonus
        family = db.query(models.Family).get(current_parent.family_id)
        multiplier = 1.0
        streak_id = None
        
        # Look for a streak that earned a bonus for this day
        streak = db.query(models.WeeklyStreak).filter(
            models.WeeklyStreak.child_id == db_entry.child_id,
            models.WeeklyStreak.bonus_date == occurrence_date,
            models.WeeklyStreak.streak_earned == True
        ).first()
        
        if streak:
            multiplier = streak.bonus_multiplier
            streak_id = streak.id
        
        awarded = int(db_entry.points_value * multiplier)
        completion.bonus_multiplier_applied = multiplier
        completion.points_awarded = awarded
        completion.streak_source_id = streak_id

        # Create Ledger Transaction
        tx = models.LedgerTransaction(
            child_id=db_entry.child_id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.calendar_task,
            points=awarded,
            description=f"Calendar: {db_entry.title}",
            created_by_parent_id=current_parent.id
        )
        db.add(tx)
        db.flush()
        completion.transaction_id = tx.id
        
        # Update Pet Progress
        points_service.update_pet_progress(db, db_entry.child_id, awarded, True)

    db.add(completion)
    db.commit()
    db.refresh(completion)
    return completion

@router.post("/completions/{completion_id}/approve", response_model=schemas.CalendarCompletion)
async def approve_completion(
    completion_id: int,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    completion = db.query(models.CalendarCompletion).get(completion_id)
    if not completion:
        raise HTTPException(status_code=404, detail="Completion not found")
    
    entry = db.query(models.CalendarEntry).get(completion.entry_id)
    if entry.family_id != current_parent.family_id:
        raise HTTPException(status_code=404, detail="Completion not found")

    if completion.status != "pending":
        raise HTTPException(status_code=400, detail="Completion is not pending")

    completion.status = "approved"
    completion.reviewed_at = datetime.now(timezone.utc)
    completion.reviewed_by_parent_id = current_parent.id
    completion.base_points = entry.points_value if entry.is_rewardable else 0

    if entry.is_rewardable and entry.points_value:
        # Streak logic
        multiplier = 1.0
        streak_id = None
        streak = db.query(models.WeeklyStreak).filter(
            models.WeeklyStreak.child_id == entry.child_id,
            models.WeeklyStreak.bonus_date == completion.occurrence_date,
            models.WeeklyStreak.streak_earned == True
        ).first()
        
        if streak:
            multiplier = streak.bonus_multiplier
            streak_id = streak.id
            
        awarded = int(entry.points_value * multiplier)
        completion.bonus_multiplier_applied = multiplier
        completion.points_awarded = awarded
        completion.streak_source_id = streak_id

        tx = models.LedgerTransaction(
            child_id=entry.child_id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.calendar_task,
            points=awarded,
            description=f"Calendar: {entry.title}",
            created_by_parent_id=current_parent.id
        )
        db.add(tx)
        db.flush()
        completion.transaction_id = tx.id
        points_service.update_pet_progress(db, entry.child_id, awarded, True)

    db.commit()
    db.refresh(completion)
    return completion

@router.post("/completions/{completion_id}/reject", response_model=schemas.CalendarCompletion)
async def reject_completion(
    completion_id: int,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    completion = db.query(models.CalendarCompletion).get(completion_id)
    if not completion:
        raise HTTPException(status_code=404, detail="Completion not found")
    
    entry = db.query(models.CalendarEntry).get(completion.entry_id)
    if entry.family_id != current_parent.family_id:
        raise HTTPException(status_code=404, detail="Completion not found")

    if completion.status != "pending":
        raise HTTPException(status_code=400, detail="Completion is not pending")

    completion.status = "rejected"
    completion.reviewed_at = datetime.now(timezone.utc)
    completion.reviewed_by_parent_id = current_parent.id
    db.commit()
    db.refresh(completion)
    return completion

@router.get("/streaks", response_model=List[schemas.WeeklyStreak])
async def get_streaks(
    child_id: int,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    child = db.query(models.Child).filter(
        models.Child.id == child_id,
        models.Child.family_id == current_parent.family_id
    ).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    return db.query(models.WeeklyStreak).filter(
        models.WeeklyStreak.child_id == child_id
    ).order_by(models.WeeklyStreak.week_start_date.desc()).limit(5).all()

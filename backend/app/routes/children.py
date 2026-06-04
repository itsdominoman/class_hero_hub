from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import models, schemas, auth
from ..services import points_service

router = APIRouter()

@router.get("/", response_model=List[schemas.ChildSummary])
async def get_children(
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    children = db.query(models.Child).filter(models.Child.family_id == current_parent.family_id).all()
    summaries = []
    for child in children:
        summary = points_service.get_child_summary(db, child.id)
        summaries.append(summary)
    return summaries

@router.post("/", response_model=schemas.Child)
async def create_child(
    child: schemas.ChildCreate,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    db_child = models.Child(
        **child.dict(),
        family_id=current_parent.family_id
    )
    db.add(db_child)
    db.commit()
    db.refresh(db_child)
    
    # Initialize pet progress
    points_service.update_pet_progress(db, db_child.id, 0, False)
    
    return db_child

@router.get("/{child_id}", response_model=schemas.ChildSummary)
async def get_child(
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

    summary = points_service.get_child_summary(db, child.id)
    return summary

@router.patch("/{child_id}", response_model=schemas.Child)
async def update_child(
    child_id: int,
    child_update: schemas.ChildUpdate,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    db_child = db.query(models.Child).filter(
        models.Child.id == child_id,
        models.Child.family_id == current_parent.family_id
    ).first()
    if not db_child:
        raise HTTPException(status_code=404, detail="Child not found")
    
    for key, value in child_update.dict(exclude_unset=True).items():
        setattr(db_child, key, value)
    
    db.commit()
    db.refresh(db_child)
    return db_child

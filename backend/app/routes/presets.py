from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import models, schemas, auth

router = APIRouter()

@router.get("/", response_model=List[schemas.PresetBehaviour])
async def get_presets(
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    return db.query(models.PresetBehaviour).filter(
        models.PresetBehaviour.parent_id == current_parent.id
    ).all()

@router.post("/", response_model=schemas.PresetBehaviour)
async def create_preset(
    preset: schemas.PresetBehaviourCreate,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    db_preset = models.PresetBehaviour(
        **preset.model_dump(),
        parent_id=current_parent.id
    )
    db.add(db_preset)
    db.commit()
    db.refresh(db_preset)
    return db_preset

@router.patch("/{preset_id}", response_model=schemas.PresetBehaviour)
async def update_preset(
    preset_id: int,
    preset_update: schemas.PresetBehaviourCreate,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    db_preset = db.query(models.PresetBehaviour).filter(
        models.PresetBehaviour.id == preset_id,
        models.PresetBehaviour.parent_id == current_parent.id
    ).first()
    
    if not db_preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    for key, value in preset_update.model_dump().items():
        setattr(db_preset, key, value)
    
    db.commit()
    db.refresh(db_preset)
    return db_preset

@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preset(
    preset_id: int,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    db_preset = db.query(models.PresetBehaviour).filter(
        models.PresetBehaviour.id == preset_id,
        models.PresetBehaviour.parent_id == current_parent.id
    ).first()
    
    if not db_preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    db.delete(db_preset)
    db.commit()
    return None

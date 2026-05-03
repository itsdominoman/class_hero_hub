from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas, auth
from ..services.rewards_service import get_family_rewards

router = APIRouter()


@router.get("/", response_model=List[schemas.Reward])
async def get_rewards(
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    return get_family_rewards(db, current_parent.family_id)


@router.post("/", response_model=schemas.Reward)
async def create_reward(
    reward: schemas.RewardCreate,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    db_reward = models.Reward(
        **reward.model_dump(),
        parent_id=current_parent.id,
        family_id=current_parent.family_id,
    )
    db.add(db_reward)
    db.commit()
    db.refresh(db_reward)
    return db_reward


@router.patch("/{reward_id}", response_model=schemas.Reward)
async def update_reward(
    reward_id: int,
    reward_update: schemas.RewardCreate,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    db_reward = db.query(models.Reward).filter(
        models.Reward.id == reward_id,
        models.Reward.family_id == current_parent.family_id,
    ).first()
    if not db_reward:
        raise HTTPException(status_code=404, detail="Reward not found")

    for key, value in reward_update.model_dump().items():
        setattr(db_reward, key, value)

    db.commit()
    db.refresh(db_reward)
    return db_reward


@router.delete("/{reward_id}", status_code=204)
async def delete_reward(
    reward_id: int,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    db_reward = db.query(models.Reward).filter(
        models.Reward.id == reward_id,
        models.Reward.family_id == current_parent.family_id,
    ).first()
    if not db_reward:
        raise HTTPException(status_code=404, detail="Reward not found")

    db.delete(db_reward)
    db.commit()
    return None

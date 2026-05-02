from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models, schemas
from datetime import datetime, timedelta

PET_THRESHOLDS = {
    models.PetStage.egg: 0,
    models.PetStage.hatchling: 50,
    models.PetStage.cub: 150,
    models.PetStage.hero: 300,
    models.PetStage.beast: 600
}

def calculate_balances(db: Session, child_id: int):
    # Spending Balance (includes deductions for pending redemptions if they are in ledger)
    spending_balance = db.query(func.sum(models.LedgerTransaction.points)).filter(
        models.LedgerTransaction.child_id == child_id,
        models.LedgerTransaction.jar == models.JarType.spending
    ).scalar() or 0

    # Savings Balance
    savings_balance = db.query(func.sum(models.LedgerTransaction.points)).filter(
        models.LedgerTransaction.child_id == child_id,
        models.LedgerTransaction.jar == models.JarType.savings
    ).scalar() or 0

    # Locked Savings
    now = datetime.utcnow()
    locked_savings = db.query(func.sum(models.LedgerTransaction.points)).filter(
        models.LedgerTransaction.child_id == child_id,
        models.LedgerTransaction.jar == models.JarType.savings,
        models.LedgerTransaction.locked_until > now
    ).scalar() or 0

    # Pending redemptions (just for display/info)
    pending_redemptions = db.query(func.sum(models.RedemptionRequest.points)).filter(
        models.RedemptionRequest.child_id == child_id,
        models.RedemptionRequest.status == models.RedemptionStatus.pending
    ).scalar() or 0

    available_savings = savings_balance - locked_savings
    available_spending = spending_balance # already includes holds if we create them in ledger

    return {
        "spending_balance": spending_balance,
        "savings_balance": savings_balance,
        "locked_savings": locked_savings,
        "available_savings": available_savings,
        "available_spending": available_spending,
        "pending_redemptions": pending_redemptions
    }

def update_pet_progress(db: Session, child_id: int, points_change: int, is_award: bool):
    pet = db.query(models.PetProgress).filter(models.PetProgress.child_id == child_id).first()
    if not pet:
        pet = models.PetProgress(child_id=child_id, lifetime_points=0, current_stage=models.PetStage.egg)
        db.add(pet)
        db.flush()

    if is_award and points_change > 0:
        pet.lifetime_points += points_change

    # Update stage
    new_stage = models.PetStage.egg
    for stage, threshold in sorted(PET_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
        if pet.lifetime_points >= threshold:
            new_stage = stage
            break
    
    pet.current_stage = new_stage
    db.commit()
    return pet

def get_child_summary(db: Session, child_id: int):
    child = db.query(models.Child).filter(models.Child.id == child_id).first()
    if not child:
        return None
    
    balances = calculate_balances(db, child_id)
    pet = db.query(models.PetProgress).filter(models.PetProgress.child_id == child_id).first()
    if not pet:
        pet = update_pet_progress(db, child_id, 0, False)

    return {
        "child": child,
        **balances,
        "pet_progress": pet
    }

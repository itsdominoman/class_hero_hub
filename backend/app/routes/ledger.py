from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Literal
from ..database import get_db
from .. import models, schemas, auth
from ..services import points_service
from .family_scope import get_family_child_or_404
from datetime import datetime

router = APIRouter()


def _child_week_start_day(child: models.Child) -> int:
    if child.family and child.family.week_start_day is not None:
        return child.family.week_start_day
    return 6


def _balance_for_adjustment_jar(balances: dict[str, int], jar: models.JarType) -> int:
    if jar == models.JarType.savings:
        return balances["savings_balance"]
    return balances["spending_balance"]


@router.get("/{child_id}/ledger", response_model=List[schemas.LedgerTransaction])
async def get_ledger(
    child_id: int,
    period: Literal["day", "week", "month"] = Query("month"),
    tx_type: Literal["all", "earned", "spent", "saved", "held", "released", "adjustment"] = Query("all", alias="type"),
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    child = get_family_child_or_404(db, child_id, current_parent)
    return points_service.get_ledger_transactions(
        db,
        child.id,
        period=period,
        tx_type=tx_type,
        week_start_day=_child_week_start_day(child),
    )


@router.get("/{child_id}/ledger/summary", response_model=schemas.LedgerSummary)
async def get_ledger_summary(
    child_id: int,
    period: Literal["day", "week", "month"] = Query("month"),
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    child = get_family_child_or_404(db, child_id, current_parent)
    return points_service.get_ledger_summary(
        db,
        child.id,
        period=period,
        week_start_day=_child_week_start_day(child),
    )


@router.post("/{child_id}/award", response_model=schemas.LedgerTransaction)
async def award_points(
    child_id: int,
    req: schemas.AwardRequest,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    if req.points <= 0:
        raise HTTPException(status_code=400, detail="Points must be positive")

    child = get_family_child_or_404(db, child_id, current_parent)

    locked_until = None
    if req.jar == models.JarType.savings:
        locked_until = datetime.utcnow() + points_service.SAVINGS_LOCK_DAYS_DELTA

    transaction = models.LedgerTransaction(
        child_id=child.id,
        jar=req.jar,
        transaction_type=models.TransactionType.award,
        points=req.points,
        description=req.description,
        locked_until=locked_until,
        created_by_parent_id=current_parent.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    # Update pet progress (awards increase lifetime points)
    points_service.update_pet_progress(db, child.id, req.points, True)

    return transaction


@router.post("/{child_id}/penalty", response_model=schemas.LedgerTransaction)
async def penalty_points(
    child_id: int,
    req: schemas.PenaltyRequest,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    if req.points <= 0:
        raise HTTPException(status_code=400, detail="Points must be positive")

    child = get_family_child_or_404(db, child_id, current_parent)

    # Check balance
    balances = points_service.calculate_balances(db, child.id)
    current_balance = balances["spending_balance"] if req.jar == models.JarType.spending else balances["savings_balance"]

    if current_balance < req.points:
        raise HTTPException(status_code=400, detail="Insufficient points for penalty")

    transaction = models.LedgerTransaction(
        child_id=child.id,
        jar=req.jar,
        transaction_type=models.TransactionType.penalty,
        points=-req.points,
        description=req.description,
        created_by_parent_id=current_parent.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction


@router.post("/{child_id}/ledger/{tx_id}/reverse", response_model=schemas.LedgerTransaction)
async def reverse_ledger_entry(
    child_id: int,
    tx_id: int,
    req: schemas.CorrectionRequest,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    """Correct a points-log entry by adding a linked balancing row, keeping the
    original for history. Only plain spending award/penalty/adjustment entries
    within the correction window and without downstream effects are eligible."""
    child = get_family_child_or_404(db, child_id, current_parent)

    try:
        reversal = points_service.correct_transaction(
            db,
            child.id,
            tx_id,
            reason=req.reason,
            created_by_parent_id=current_parent.id,
        )
    except points_service.CorrectionError as exc:
        raise HTTPException(status_code=400, detail=exc.code)

    if reversal is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return reversal


@router.post("/{child_id}/savings/deposit", response_model=List[schemas.LedgerTransaction])
async def deposit_to_savings(
    child_id: int,
    req: schemas.SavingsDepositRequest,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    if req.points <= 0:
        raise HTTPException(status_code=400, detail="Points must be positive")

    child = get_family_child_or_404(db, child_id, current_parent)

    balances = points_service.calculate_balances(db, child.id)
    if balances["spending_balance"] < req.points:
        raise HTTPException(status_code=400, detail="Insufficient spending points")

    return points_service.create_savings_deposit(
        db,
        child.id,
        req.points,
        req.description,
        created_by_parent_id=current_parent.id,
    )


@router.post("/{child_id}/savings/withdraw", response_model=List[schemas.LedgerTransaction])
async def withdraw_from_savings(
    child_id: int,
    req: schemas.SavingsWithdrawRequest,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    if req.points <= 0:
        raise HTTPException(status_code=400, detail="Points must be positive")

    child = get_family_child_or_404(db, child_id, current_parent)

    balances = points_service.calculate_balances(db, child.id)
    if balances["available_savings"] < req.points:
        raise HTTPException(status_code=400, detail="Insufficient available (unlocked) savings points")

    # 1. Remove from savings
    savings_tx = models.LedgerTransaction(
        child_id=child.id,
        jar=models.JarType.savings,
        transaction_type=models.TransactionType.savings_withdrawal,
        points=-req.points,
        description=f"Transfer to Spending: {req.description}",
        created_by_parent_id=current_parent.id,
    )

    # 2. Add to spending
    spending_tx = models.LedgerTransaction(
        child_id=child.id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.savings_withdrawal,
        points=req.points,
        description=f"Transfer from Savings: {req.description}",
        created_by_parent_id=current_parent.id,
    )

    db.add(savings_tx)
    db.add(spending_tx)
    db.commit()
    db.refresh(savings_tx)
    db.refresh(spending_tx)

    return [savings_tx, spending_tx]


@router.post("/{child_id}/adjustment", response_model=schemas.LedgerTransaction)
async def admin_adjustment(
    child_id: int,
    points: int,
    description: str,
    jar: models.JarType,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    child = get_family_child_or_404(db, child_id, current_parent)

    if points < 0:
        balances = points_service.calculate_balances(db, child.id)
        current_balance = _balance_for_adjustment_jar(balances, jar)
        if current_balance < abs(points):
            detail = "Insufficient savings points" if jar == models.JarType.savings else "Insufficient spending points"
            raise HTTPException(status_code=400, detail=detail)

    transaction = models.LedgerTransaction(
        child_id=child.id,
        jar=jar,
        transaction_type=models.TransactionType.adjustment,
        points=points,
        description=description,
        created_by_parent_id=current_parent.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction

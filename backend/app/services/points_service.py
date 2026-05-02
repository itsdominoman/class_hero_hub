from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models, schemas
from datetime import datetime, timedelta

PET_THRESHOLDS = {
    models.PetStage.egg: 0,
    models.PetStage.hatchling: 50,
    models.PetStage.cub: 150,
    models.PetStage.hero: 300,
    models.PetStage.beast: 600,
}


def calculate_balances(db: Session, child_id: int):
    # Spending balance includes the redemption hold as the single deduction.
    # Keep legacy approved rows out of the total in case older data exists.
    spending_balance = db.query(func.sum(models.LedgerTransaction.points)).filter(
        models.LedgerTransaction.child_id == child_id,
        models.LedgerTransaction.jar == models.JarType.spending,
        models.LedgerTransaction.transaction_type != models.TransactionType.redemption_approved,
    ).scalar() or 0

    # Savings Balance
    savings_balance = db.query(func.sum(models.LedgerTransaction.points)).filter(
        models.LedgerTransaction.child_id == child_id,
        models.LedgerTransaction.jar == models.JarType.savings,
    ).scalar() or 0

    # Locked Savings
    now = datetime.utcnow()
    locked_savings = db.query(func.sum(models.LedgerTransaction.points)).filter(
        models.LedgerTransaction.child_id == child_id,
        models.LedgerTransaction.jar == models.JarType.savings,
        models.LedgerTransaction.locked_until > now,
    ).scalar() or 0

    # Pending redemptions (just for display/info)
    pending_redemptions = db.query(func.sum(models.RedemptionRequest.points)).filter(
        models.RedemptionRequest.child_id == child_id,
        models.RedemptionRequest.status == models.RedemptionStatus.pending,
    ).scalar() or 0

    available_savings = savings_balance - locked_savings
    available_spending = spending_balance

    return {
        "spending_balance": spending_balance,
        "savings_balance": savings_balance,
        "locked_savings": locked_savings,
        "available_savings": available_savings,
        "available_spending": available_spending,
        "pending_redemptions": pending_redemptions,
    }


def get_period_bounds(period: str, now: datetime | None = None) -> tuple[datetime, datetime]:
    current = now or datetime.utcnow()
    today = current.date()

    if period == "day":
        start = datetime.combine(today, datetime.min.time())
        end = start + timedelta(days=1)
        return start, end

    if period == "week":
        week_start = today - timedelta(days=today.weekday())
        start = datetime.combine(week_start, datetime.min.time())
        end = start + timedelta(days=7)
        return start, end

    if period == "month":
        start = datetime(current.year, current.month, 1)
        if current.month == 12:
            end = datetime(current.year + 1, 1, 1)
        else:
            end = datetime(current.year, current.month + 1, 1)
        return start, end

    raise ValueError(f"Unsupported period: {period}")


def _matches_activity_type(transaction: models.LedgerTransaction, tx_type: str) -> bool:
    if tx_type == "all":
        return True
    if tx_type == "earned":
        return transaction.transaction_type == models.TransactionType.award or (
            transaction.transaction_type == models.TransactionType.adjustment and transaction.points > 0
        )
    if tx_type == "spent":
        return transaction.transaction_type == models.TransactionType.redemption_hold
    if tx_type == "saved":
        return transaction.transaction_type in {
            models.TransactionType.savings_deposit,
            models.TransactionType.savings_withdrawal,
        }
    if tx_type == "held":
        return transaction.transaction_type == models.TransactionType.redemption_hold
    if tx_type == "released":
        return transaction.transaction_type == models.TransactionType.redemption_rejected
    if tx_type == "adjustment":
        return transaction.transaction_type == models.TransactionType.adjustment
    return False


def get_ledger_transactions(db: Session, child_id: int, period: str = "month", tx_type: str = "all", now: datetime | None = None):
    start, end = get_period_bounds(period, now=now)
    transactions = (
        db.query(models.LedgerTransaction)
        .filter(
            models.LedgerTransaction.child_id == child_id,
            models.LedgerTransaction.created_at >= start,
            models.LedgerTransaction.created_at < end,
        )
        .order_by(models.LedgerTransaction.created_at.desc())
        .all()
    )

    return [tx for tx in transactions if _matches_activity_type(tx, tx_type)]


def get_ledger_summary(db: Session, child_id: int, period: str = "month", now: datetime | None = None):
    start, end = get_period_bounds(period, now=now)
    transactions = (
        db.query(models.LedgerTransaction)
        .filter(
            models.LedgerTransaction.child_id == child_id,
            models.LedgerTransaction.created_at >= start,
            models.LedgerTransaction.created_at < end,
        )
        .order_by(models.LedgerTransaction.created_at.desc())
        .all()
    )

    totals = {
        "gained": 0,
        "lost": 0,
        "spent": 0,
        "saved_in": 0,
        "saved_out": 0,
        "held": 0,
        "released": 0,
        "transaction_count": len(transactions),
    }

    for transaction in transactions:
        tx_type = transaction.transaction_type
        points = transaction.points or 0

        if tx_type == models.TransactionType.award or (tx_type == models.TransactionType.adjustment and points > 0):
            totals["gained"] += points
        elif tx_type == models.TransactionType.penalty or (tx_type == models.TransactionType.adjustment and points < 0):
            totals["lost"] += abs(points)
        elif tx_type == models.TransactionType.redemption_hold and transaction.jar == models.JarType.spending and points < 0:
            # Option B: the hold is the single deduction, so count it as spent.
            totals["spent"] += abs(points)
        elif tx_type == models.TransactionType.savings_deposit and transaction.jar == models.JarType.savings and points > 0:
            totals["saved_in"] += points
        elif tx_type == models.TransactionType.savings_withdrawal and transaction.jar == models.JarType.savings and points < 0:
            totals["saved_out"] += abs(points)
        elif tx_type == models.TransactionType.redemption_rejected and transaction.jar == models.JarType.spending and points > 0:
            totals["released"] += points

    totals["net"] = totals["gained"] - totals["lost"] - totals["spent"]
    return totals


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
        "pet_progress": pet,
    }

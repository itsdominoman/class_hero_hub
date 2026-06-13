from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models, schemas
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

PET_THRESHOLDS = {
    models.PetStage.egg: 0,
    models.PetStage.hatchling: 50,
    models.PetStage.cub: 150,
    models.PetStage.hero: 300,
    models.PetStage.beast: 600,
}

SAVINGS_LOCK_DAYS = 30
SAVINGS_LOCK_DAYS_DELTA = timedelta(days=SAVINGS_LOCK_DAYS)

# A6 — parent "Correct this entry". A correction is a linked reversing row
# (transaction_type=reversal, source_transaction_id -> original). Only plain
# spending-jar award/penalty/adjustment entries that have no downstream rows
# and are still inside the window may be corrected.
CORRECTION_WINDOW = timedelta(days=7)
CORRECTABLE_TYPES = {
    models.TransactionType.award,
    models.TransactionType.penalty,
    models.TransactionType.adjustment,
}
SAVINGS_BONUS_RATE_BPS = 1000
SAVINGS_BONUS_ROUND_UP_REMAINDER = 6
# Rollout cutoff: bonus applies to deposits that were still locked when this feature shipped,
# and to all future deposits. Older already-unlocked savings are intentionally not backfilled.
SAVINGS_BONUS_ROLLOUT_CUTOFF = datetime(2026, 6, 3, 0, 0, 0)


def calculate_savings_bonus(points: int) -> int:
    if points <= 0:
        return 0
    raw_bonus_units = points * SAVINGS_BONUS_RATE_BPS
    whole_points = raw_bonus_units // 10000
    remainder = raw_bonus_units % 10000
    return whole_points + (1 if remainder >= SAVINGS_BONUS_ROUND_UP_REMAINDER * 1000 else 0)


def _source_processed(db: Session, source_transaction_id: int) -> bool:
    return (
        db.query(models.LedgerTransaction.id)
        .filter(models.LedgerTransaction.source_transaction_id == source_transaction_id)
        .first()
        is not None
    )


def mature_savings_deposits(db: Session, child_id: int | None = None, now: datetime | None = None) -> list[models.LedgerTransaction]:
    current = now or datetime.utcnow()
    query = db.query(models.LedgerTransaction).filter(
        models.LedgerTransaction.jar == models.JarType.savings,
        models.LedgerTransaction.points > 0,
        models.LedgerTransaction.locked_until.isnot(None),
        models.LedgerTransaction.locked_until <= current,
        models.LedgerTransaction.locked_until > SAVINGS_BONUS_ROLLOUT_CUTOFF,
        models.LedgerTransaction.transaction_type.in_(
            [models.TransactionType.savings_deposit, models.TransactionType.award]
        ),
    )
    if child_id is not None:
        query = query.filter(models.LedgerTransaction.child_id == child_id)

    matured_rows: list[models.LedgerTransaction] = []
    for deposit in query.order_by(models.LedgerTransaction.locked_until.asc(), models.LedgerTransaction.id.asc()).all():
        if _source_processed(db, deposit.id):
            continue

        principal = deposit.points or 0
        bonus = calculate_savings_bonus(principal)
        description = deposit.description or "Saved points"
        common_kwargs = {
            "child_id": deposit.child_id,
            "source_transaction_id": deposit.id,
            "created_by_parent_id": deposit.created_by_parent_id,
        }

        matured_rows.extend(
            [
                models.LedgerTransaction(
                    **common_kwargs,
                    jar=models.JarType.savings,
                    transaction_type=models.TransactionType.savings_maturity,
                    points=-principal,
                    description=f"Savings unlocked: {description}",
                ),
                models.LedgerTransaction(
                    **common_kwargs,
                    jar=models.JarType.spending,
                    transaction_type=models.TransactionType.savings_maturity,
                    points=principal,
                    description=f"Savings returned to available points: {description}",
                ),
            ]
        )
        if bonus > 0:
            matured_rows.append(
                models.LedgerTransaction(
                    **common_kwargs,
                    jar=models.JarType.spending,
                    transaction_type=models.TransactionType.savings_bonus,
                    points=bonus,
                    description=f"Savings bonus: {description}",
                )
            )

    if matured_rows:
        db.add_all(matured_rows)
        db.commit()

    return matured_rows


def create_savings_deposit(
    db: Session,
    child_id: int,
    points: int,
    description: str,
    created_by_parent_id: int | None = None,
) -> list[models.LedgerTransaction]:
    spending_tx = models.LedgerTransaction(
        child_id=child_id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.savings_deposit,
        points=-points,
        description=f"Transfer to Savings: {description}",
        created_by_parent_id=created_by_parent_id,
    )

    savings_tx = models.LedgerTransaction(
        child_id=child_id,
        jar=models.JarType.savings,
        transaction_type=models.TransactionType.savings_deposit,
        points=points,
        description=f"Transfer from Spending: {description}",
        locked_until=datetime.utcnow() + SAVINGS_LOCK_DAYS_DELTA,
        created_by_parent_id=created_by_parent_id,
    )

    db.add(spending_tx)
    db.add(savings_tx)
    db.commit()
    db.refresh(spending_tx)
    db.refresh(savings_tx)
    return [spending_tx, savings_tx]


class CorrectionError(Exception):
    """Raised when a ledger entry cannot be corrected. ``code`` is a stable
    machine-readable reason the frontend maps to a localized message."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    return value


def correct_transaction(
    db: Session,
    child_id: int,
    tx_id: int,
    reason: str | None = None,
    created_by_parent_id: int | None = None,
    now: datetime | None = None,
) -> models.LedgerTransaction | None:
    """Create a linked reversing entry that cancels ``tx_id`` while keeping the
    original row for history. Returns ``None`` if the entry does not exist for
    this child (route turns that into a 404); raises ``CorrectionError`` for an
    ineligible entry. Deliberately does NOT touch pet progress: lifetime points
    are a monotonic high-water-mark and never regress on a correction."""
    current = now or datetime.utcnow()

    tx = (
        db.query(models.LedgerTransaction)
        .filter(
            models.LedgerTransaction.id == tx_id,
            models.LedgerTransaction.child_id == child_id,
        )
        .first()
    )
    if tx is None:
        return None

    # Eligible kinds only: a plain award / penalty / adjustment.
    if tx.transaction_type not in CORRECTABLE_TYPES:
        raise CorrectionError("correction_ineligible_type")
    # Savings-jar entries spawn maturity/bonus rows downstream — refuse.
    if tx.jar != models.JarType.spending:
        raise CorrectionError("correction_ineligible_type")
    # An entry that is itself derived from / a correction of another entry.
    if tx.source_transaction_id is not None:
        raise CorrectionError("correction_ineligible_type")
    # Already corrected, or it spawned downstream rows (e.g. a matured deposit).
    if _source_processed(db, tx.id):
        raise CorrectionError("correction_already_processed")
    # Time window: corrections are only allowed for a week after the entry.
    if current - _to_naive_utc(tx.created_at) > CORRECTION_WINDOW:
        raise CorrectionError("correction_window_expired")

    reversal_points = -(tx.points or 0)
    balances = calculate_balances(db, child_id, now=current)
    projected_available_spending = balances["available_spending"] + reversal_points
    if projected_available_spending < 0:
        raise CorrectionError("correction_insufficient_available_balance")

    reversal = models.LedgerTransaction(
        child_id=tx.child_id,
        jar=tx.jar,
        transaction_type=models.TransactionType.reversal,
        points=reversal_points,
        description=(reason or "").strip(),
        source_transaction_id=tx.id,
        created_by_parent_id=created_by_parent_id,
    )
    db.add(reversal)
    db.commit()
    db.refresh(reversal)
    return reversal


def calculate_balances(db: Session, child_id: int, now: datetime | None = None):
    mature_savings_deposits(db, child_id, now=now)

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
    now = now or datetime.utcnow()
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


def _as_utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(ZoneInfo("UTC"))


def get_savings_unlock_schedule(
    db: Session,
    child_id: int,
    family_timezone: str = "UTC",
    now: datetime | None = None,
) -> list[dict]:
    current = now or datetime.utcnow()
    family_zone = ZoneInfo(family_timezone or "UTC")
    unlock_rows = (
        db.query(models.LedgerTransaction)
        .filter(
            models.LedgerTransaction.child_id == child_id,
            models.LedgerTransaction.jar == models.JarType.savings,
            models.LedgerTransaction.points > 0,
            models.LedgerTransaction.locked_until > current,
            models.LedgerTransaction.transaction_type.in_(
                [models.TransactionType.savings_deposit, models.TransactionType.award]
            ),
        )
        .order_by(models.LedgerTransaction.locked_until.asc())
        .all()
    )

    grouped: dict = {}
    for transaction in unlock_rows:
        unlock_date = _as_utc_aware(transaction.locked_until).astimezone(family_zone).date()
        principal = transaction.points or 0
        bonus = calculate_savings_bonus(principal)
        current_group = grouped.get(unlock_date, {"points": 0, "principal_points": 0, "bonus_points": 0})
        current_group["points"] += principal + bonus
        current_group["principal_points"] += principal
        current_group["bonus_points"] += bonus
        grouped[unlock_date] = current_group

    return [
        {"unlock_date": unlock_date, **values}
        for unlock_date, values in sorted(grouped.items())
    ]


def _normalize_week_start_day(week_start_day: int | None) -> int:
    if week_start_day is None or week_start_day < 0 or week_start_day > 6:
        return 6
    return week_start_day


def get_period_bounds(period: str, now: datetime | None = None, week_start_day: int | None = 6) -> tuple[datetime, datetime]:
    current = now or datetime.utcnow()
    today = current.date()

    if period == "day":
        start = datetime.combine(today, datetime.min.time())
        end = start + timedelta(days=1)
        return start, end

    if period == "week":
        normalized_week_start = _normalize_week_start_day(week_start_day)
        days_since_start = (today.weekday() - normalized_week_start) % 7
        week_start = today - timedelta(days=days_since_start)
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
        return transaction.transaction_type in {models.TransactionType.award, models.TransactionType.savings_bonus} or (
            transaction.transaction_type == models.TransactionType.adjustment and transaction.points > 0
        )
    if tx_type == "spent":
        return transaction.transaction_type == models.TransactionType.redemption_hold
    if tx_type == "saved":
        return transaction.transaction_type in {
            models.TransactionType.savings_deposit,
            models.TransactionType.savings_withdrawal,
            models.TransactionType.savings_maturity,
            models.TransactionType.savings_bonus,
        }
    if tx_type == "held":
        return transaction.transaction_type == models.TransactionType.redemption_hold
    if tx_type == "released":
        return transaction.transaction_type == models.TransactionType.redemption_rejected
    if tx_type == "adjustment":
        return transaction.transaction_type == models.TransactionType.adjustment
    return False


def get_ledger_transactions(
    db: Session,
    child_id: int,
    period: str = "month",
    tx_type: str = "all",
    now: datetime | None = None,
    week_start_day: int | None = 6,
):
    start, end = get_period_bounds(period, now=now, week_start_day=week_start_day)
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


def get_ledger_summary(
    db: Session,
    child_id: int,
    period: str = "month",
    now: datetime | None = None,
    week_start_day: int | None = 6,
):
    start, end = get_period_bounds(period, now=now, week_start_day=week_start_day)
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

        if tx_type in {models.TransactionType.award, models.TransactionType.savings_bonus} or (
            tx_type in {models.TransactionType.adjustment, models.TransactionType.reversal} and points > 0
        ):
            totals["gained"] += points
        elif tx_type == models.TransactionType.penalty or (
            tx_type in {models.TransactionType.adjustment, models.TransactionType.reversal} and points < 0
        ):
            totals["lost"] += abs(points)
        elif tx_type == models.TransactionType.redemption_hold and transaction.jar == models.JarType.spending and points < 0:
            # Option B: the hold is the single deduction, so count it as spent.
            totals["spent"] += abs(points)
        elif tx_type == models.TransactionType.savings_deposit and transaction.jar == models.JarType.savings and points > 0:
            totals["saved_in"] += points
        elif tx_type in {
            models.TransactionType.savings_withdrawal,
            models.TransactionType.savings_maturity,
        } and transaction.jar == models.JarType.savings and points < 0:
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
        "savings_unlock_schedule": get_savings_unlock_schedule(
            db,
            child_id,
            child.family.timezone if child.family else "UTC",
        ),
    }

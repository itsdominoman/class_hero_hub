from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from . import points_service


SUPPORTED_CURRENCY_EXPONENTS = schemas.SUPPORTED_ALLOWANCE_CURRENCIES
DEFAULT_CURRENCY = "OMR"
DEFAULT_PERIOD = "weekly"
DEFAULT_POINT_GOAL = 100


def currency_exponent(currency: str) -> int:
    normalized = currency.strip().upper()
    if normalized not in SUPPORTED_CURRENCY_EXPONENTS:
        raise ValueError("Currency is not supported")
    return SUPPORTED_CURRENCY_EXPONENTS[normalized]


def default_settings_for_child(child: models.Child) -> schemas.AllowanceSettings:
    currency = DEFAULT_CURRENCY
    return schemas.AllowanceSettings(
        id=None,
        family_id=child.family_id,
        child_id=child.id,
        is_enabled=False,
        currency=currency,
        allowance_amount_minor=0,
        currency_exponent=currency_exponent(currency),
        period=DEFAULT_PERIOD,
        point_goal=DEFAULT_POINT_GOAL,
        created_by_parent_id=None,
        updated_by_parent_id=None,
        created_at=None,
        updated_at=None,
    )


def get_settings(db: Session, child: models.Child) -> models.ChildAllowanceSetting | None:
    return (
        db.query(models.ChildAllowanceSetting)
        .filter(
            models.ChildAllowanceSetting.child_id == child.id,
            models.ChildAllowanceSetting.family_id == child.family_id,
        )
        .first()
    )


def get_settings_response(db: Session, child: models.Child) -> schemas.AllowanceSettings:
    setting = get_settings(db, child)
    if not setting:
        return default_settings_for_child(child)
    return schemas.AllowanceSettings.model_validate(setting)


def upsert_settings(
    db: Session,
    child: models.Child,
    parent: models.ParentUser,
    payload: schemas.AllowanceSettingsUpsert,
) -> models.ChildAllowanceSetting:
    normalized_currency = payload.currency.strip().upper()
    exponent = currency_exponent(normalized_currency)
    setting = get_settings(db, child)

    if not setting:
        setting = models.ChildAllowanceSetting(
            family_id=child.family_id,
            child_id=child.id,
            created_by_parent_id=parent.id,
        )
        db.add(setting)

    was_enabled = bool(setting.is_enabled)
    setting.is_enabled = payload.is_enabled
    setting.currency = normalized_currency
    setting.allowance_amount_minor = payload.allowance_amount_minor
    setting.currency_exponent = exponent
    setting.period = payload.period
    setting.point_goal = payload.point_goal
    if payload.is_enabled:
        if not was_enabled or setting.allowance_enabled_at is None:
            setting.allowance_enabled_at = datetime.utcnow()
    setting.updated_by_parent_id = parent.id

    db.commit()
    db.refresh(setting)
    return setting


def delete_settings(db: Session, child: models.Child) -> None:
    setting = get_settings(db, child)
    if setting:
        db.delete(setting)
        db.commit()


def _family_zone(family: models.Family | None) -> ZoneInfo:
    try:
        return ZoneInfo((family.timezone if family else None) or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def _period_bounds_for_setting(
    setting: schemas.AllowanceSettings,
    family: models.Family | None,
    now: datetime | None = None,
) -> tuple[date, date, datetime, datetime]:
    zone = _family_zone(family)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    local_now = current.astimezone(zone)
    today = local_now.date()

    if setting.period == "monthly":
        start_date = today.replace(day=1)
        if start_date.month == 12:
            end_date = date(start_date.year + 1, 1, 1)
        else:
            end_date = date(start_date.year, start_date.month + 1, 1)
    else:
        week_start_day = family.week_start_day if family and family.week_start_day is not None else 6
        days_since_start = (today.weekday() - week_start_day) % 7
        start_date = today - timedelta(days=days_since_start)
        end_date = start_date + timedelta(days=7)

    start_local = datetime.combine(start_date, time.min, tzinfo=zone)
    end_local = datetime.combine(end_date, time.min, tzinfo=zone)
    return start_date, end_date, start_local.astimezone(ZoneInfo("UTC")), end_local.astimezone(ZoneInfo("UTC"))


def _eligible_points_from_transaction(transaction: models.LedgerTransaction) -> int:
    tx_type = transaction.transaction_type
    points = transaction.points or 0

    if tx_type in {
        models.TransactionType.award,
        models.TransactionType.calendar_task,
        models.TransactionType.savings_bonus,
    }:
        return points
    if tx_type == models.TransactionType.adjustment:
        return points
    if tx_type == models.TransactionType.penalty:
        return points
    return 0


def _format_minor_amount(amount_minor: int, currency: str, exponent: int) -> str:
    unit = Decimal(10) ** exponent
    amount = Decimal(amount_minor) / unit
    text = f"{amount:.{exponent}f}".rstrip("0").rstrip(".")
    if not text:
        text = "0"
    return f"{text} {currency}"


def _format_point_value_display(amount_minor: int, point_goal: int, currency: str, exponent: int) -> str:
    unit = Decimal(10) ** exponent
    per_point = (Decimal(amount_minor) / Decimal(point_goal)) / unit
    text = f"{per_point.quantize(Decimal(10) ** -exponent, rounding=ROUND_HALF_UP):f}".rstrip("0").rstrip(".")
    if not text:
        text = "0"
    return f"{text} {currency}"


def _points_to_minor(points: int, setting: schemas.AllowanceSettings) -> int:
    safe_points = max(0, int(points or 0))
    if safe_points == 0 or setting.allowance_amount_minor <= 0:
        return 0
    return safe_points * setting.allowance_amount_minor // setting.point_goal


def _coerce_naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _sum_ledger_points(
    db: Session,
    child_id: int,
    *,
    start_utc: datetime | None = None,
    end_utc: datetime | None = None,
    jar: models.JarType | None = None,
    transaction_types: set[models.TransactionType] | None = None,
) -> int:
    query = db.query(func.sum(models.LedgerTransaction.points)).filter(models.LedgerTransaction.child_id == child_id)
    if jar is not None:
        query = query.filter(models.LedgerTransaction.jar == jar)
    if transaction_types is not None:
        query = query.filter(models.LedgerTransaction.transaction_type.in_(transaction_types))
    if start_utc is not None:
        query = query.filter(models.LedgerTransaction.created_at >= start_utc.replace(tzinfo=None))
    if end_utc is not None:
        query = query.filter(models.LedgerTransaction.created_at < end_utc.replace(tzinfo=None))
    return int(query.scalar() or 0)


def _pending_redemptions(db: Session, child_id: int) -> int:
    return int(
        db.query(func.sum(models.RedemptionRequest.points))
        .filter(
            models.RedemptionRequest.child_id == child_id,
            models.RedemptionRequest.status == models.RedemptionStatus.pending,
        )
        .scalar()
        or 0
    )


def _approved_redemptions_in_period(db: Session, child_id: int, start_utc: datetime, end_utc: datetime) -> int:
    query = (
        db.query(func.sum(models.RedemptionRequest.points))
        .filter(
            models.RedemptionRequest.child_id == child_id,
            models.RedemptionRequest.status == models.RedemptionStatus.approved,
            models.RedemptionRequest.reviewed_at.isnot(None),
            models.RedemptionRequest.reviewed_at >= start_utc,
            models.RedemptionRequest.reviewed_at < end_utc,
        )
    )
    return int(query.scalar() or 0)


def _build_allowance_summary(
    db: Session,
    child: models.Child,
    setting: schemas.AllowanceSettings,
    now: datetime | None = None,
    *,
    reveal_preview_when_disabled: bool = True,
) -> schemas.AllowancePreview:
    points_service.mature_savings_deposits(db, child.id, now=now)

    family = db.query(models.Family).filter(models.Family.id == child.family_id).first()
    period_start, period_end, start_utc, end_utc = _period_bounds_for_setting(setting, family, now=now)
    period_start_naive = start_utc.replace(tzinfo=None)
    period_end_naive = end_utc.replace(tzinfo=None)

    current_time = _coerce_naive_utc(now or datetime.now(timezone.utc)) or datetime.utcnow()
    current_spending_balance = _sum_ledger_points(db, child.id, jar=models.JarType.spending)
    current_savings_balance = _sum_ledger_points(db, child.id, jar=models.JarType.savings)
    raw_earned_points_period = sum(
        _eligible_points_from_transaction(tx)
        for tx in db.query(models.LedgerTransaction)
        .filter(
            models.LedgerTransaction.child_id == child.id,
            models.LedgerTransaction.created_at >= period_start_naive,
            models.LedgerTransaction.created_at < period_end_naive,
        )
        .all()
    )
    earned_points_period = max(0, raw_earned_points_period)
    spent_points_period = _approved_redemptions_in_period(db, child.id, period_start_naive, period_end_naive)
    pending_points = _pending_redemptions(db, child.id)
    saved_points = max(0, current_savings_balance)
    locked_saved_points = int(
        db.query(func.sum(models.LedgerTransaction.points))
        .filter(
            models.LedgerTransaction.child_id == child.id,
            models.LedgerTransaction.jar == models.JarType.savings,
            models.LedgerTransaction.locked_until > current_time,
        )
        .scalar()
        or 0
    )
    locked_saved_points = max(0, locked_saved_points)
    available_points = max(0, current_spending_balance)
    allowance_available_points = available_points
    carried_over_points = max(
        0,
        _sum_ledger_points(
            db,
            child.id,
            jar=models.JarType.spending,
            end_utc=period_start_naive,
        ),
    )

    show_preview = setting.is_enabled or reveal_preview_when_disabled
    point_value_display = _format_point_value_display(
        setting.allowance_amount_minor or 0,
        setting.point_goal,
        setting.currency,
        setting.currency_exponent,
    )

    progress_ratio = (earned_points_period / setting.point_goal) if setting.point_goal else 0.0
    progress_percent = progress_ratio * 100
    maxed_for_period = earned_points_period >= setting.point_goal
    earned_allowance_minor_period = _points_to_minor(earned_points_period, setting)
    spent_allowance_minor_period = _points_to_minor(spent_points_period, setting)
    pending_allowance_minor = _points_to_minor(pending_points, setting)
    carried_over_allowance_minor = _points_to_minor(carried_over_points, setting)
    available_allowance_minor = _points_to_minor(allowance_available_points, setting)
    saved_allowance_minor = _points_to_minor(saved_points, setting)
    locked_saved_allowance_minor = _points_to_minor(locked_saved_points, setting)
    eligible_transaction_start = period_start_naive
    included_transaction_count = sum(
        1
        for tx in db.query(models.LedgerTransaction)
        .filter(
            models.LedgerTransaction.child_id == child.id,
            models.LedgerTransaction.created_at >= eligible_transaction_start,
            models.LedgerTransaction.created_at < period_end_naive,
        )
        .all()
        if _eligible_points_from_transaction(tx) != 0
    )

    display_amount = _format_minor_amount(earned_allowance_minor_period, setting.currency, setting.currency_exponent)
    display_max_amount = _format_minor_amount(setting.allowance_amount_minor, setting.currency, setting.currency_exponent)
    max_amount_minor = setting.allowance_amount_minor

    if not show_preview:
        raw_earned_points_period = 0
        earned_points_period = 0
        spent_points_period = 0
        pending_points = 0
        carried_over_points = 0
        earned_allowance_minor_period = 0
        spent_allowance_minor_period = 0
        pending_allowance_minor = 0
        carried_over_allowance_minor = 0
        available_allowance_minor = 0
        saved_allowance_minor = 0
        locked_saved_allowance_minor = 0
        progress_ratio = 0.0
        progress_percent = 0.0
        maxed_for_period = False
        point_value_display = f"0 {setting.currency}"
        display_amount = f"0 {setting.currency}"
        display_max_amount = f"0 {setting.currency}"
        max_amount_minor = 0
        included_transaction_count = 0

    return schemas.AllowancePreview(
        settings=setting,
        period_start=period_start,
        period_end=period_end,
        next_reset_at=end_utc,
        allowance_enabled_at=setting.allowance_enabled_at,
        point_value_display=point_value_display,
        point_goal=setting.point_goal,
        progress_ratio=progress_ratio,
        progress_percent=progress_percent,
        maxed_for_period=maxed_for_period,
        raw_eligible_points=raw_earned_points_period,
        eligible_points=earned_points_period,
        raw_earned_points_period=raw_earned_points_period,
        earned_points_period=earned_points_period,
        earned_amount_minor=earned_allowance_minor_period,
        earned_allowance_minor_period=earned_allowance_minor_period,
        spent_points_period=spent_points_period,
        spent_allowance_minor_period=spent_allowance_minor_period,
        pending_points=pending_points,
        pending_allowance_minor=pending_allowance_minor,
        available_points=available_points,
        available_allowance_minor=available_allowance_minor,
        carried_over_points=carried_over_points,
        carried_over_allowance_minor=carried_over_allowance_minor,
        saved_points=saved_points,
        saved_allowance_minor=saved_allowance_minor,
        locked_saved_points=locked_saved_points,
        locked_saved_allowance_minor=locked_saved_allowance_minor,
        max_amount_minor=max_amount_minor,
        currency=setting.currency,
        currency_exponent=setting.currency_exponent,
        display_amount=display_amount,
        display_max_amount=display_max_amount,
        included_transaction_count=included_transaction_count,
    )


def preview_allowance(
    db: Session,
    child: models.Child,
    setting: schemas.AllowanceSettings,
    now: datetime | None = None,
) -> schemas.AllowancePreview:
    return _build_allowance_summary(db, child, setting, now=now, reveal_preview_when_disabled=True)


def get_allowance_summary(
    db: Session,
    child: models.Child,
    setting: schemas.AllowanceSettings,
    now: datetime | None = None,
    *,
    reveal_preview_when_disabled: bool = True,
) -> schemas.AllowancePreview:
    return _build_allowance_summary(
        db,
        child,
        setting,
        now=now,
        reveal_preview_when_disabled=reveal_preview_when_disabled,
    )

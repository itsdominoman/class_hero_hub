from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from .. import models, schemas


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

    setting.is_enabled = payload.is_enabled
    setting.currency = normalized_currency
    setting.allowance_amount_minor = payload.allowance_amount_minor
    setting.currency_exponent = exponent
    setting.period = payload.period
    setting.point_goal = payload.point_goal
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

    if tx_type in {models.TransactionType.award, models.TransactionType.calendar_task}:
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


def preview_allowance(
    db: Session,
    child: models.Child,
    setting: schemas.AllowanceSettings,
    now: datetime | None = None,
) -> schemas.AllowancePreview:
    family = db.query(models.Family).filter(models.Family.id == child.family_id).first()
    period_start, period_end, start_utc, end_utc = _period_bounds_for_setting(setting, family, now=now)

    transactions = (
        db.query(models.LedgerTransaction)
        .filter(
            models.LedgerTransaction.child_id == child.id,
            models.LedgerTransaction.created_at >= start_utc.replace(tzinfo=None),
            models.LedgerTransaction.created_at < end_utc.replace(tzinfo=None),
        )
        .all()
    )

    eligible_deltas = [_eligible_points_from_transaction(tx) for tx in transactions]
    raw_eligible_points = sum(eligible_deltas)
    eligible_points = max(0, raw_eligible_points)
    capped_points = min(eligible_points, setting.point_goal)
    progress_ratio = capped_points / setting.point_goal
    earned_amount_minor = int(setting.allowance_amount_minor * progress_ratio)

    return schemas.AllowancePreview(
        settings=setting,
        period_start=period_start,
        period_end=period_end,
        eligible_points=eligible_points,
        raw_eligible_points=raw_eligible_points,
        point_goal=setting.point_goal,
        progress_ratio=progress_ratio,
        earned_amount_minor=earned_amount_minor,
        max_amount_minor=setting.allowance_amount_minor,
        currency=setting.currency,
        currency_exponent=setting.currency_exponent,
        display_amount=_format_minor_amount(earned_amount_minor, setting.currency, setting.currency_exponent),
        display_max_amount=_format_minor_amount(setting.allowance_amount_minor, setting.currency, setting.currency_exponent),
        included_transaction_count=sum(1 for delta in eligible_deltas if delta != 0),
    )

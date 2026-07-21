from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import case, func
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .models_school import (
    BehaviourEvent,
    FhhLink,
    NotificationOutbox,
    PointNotificationSummary,
    School,
    SchoolPointsNotificationPolicy,
    Student,
)


UTC = timezone.utc
ELIGIBLE_SCHOOL_STATUSES = {"pending_setup", "active"}
SUMMARY_TYPES = ("daily", "weekly", "monthly")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SummaryPeriod:
    summary_type: str
    period_key: str
    period_start: datetime
    period_end: datetime
    eligible_at: datetime


@dataclass(frozen=True)
class GenerationBatchResult:
    generated: int
    scanned: int
    next_after_school_id: int


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _valid_instants(naive: datetime, zone: ZoneInfo) -> list[datetime]:
    instants: list[datetime] = []
    for fold in (0, 1):
        candidate = naive.replace(tzinfo=zone, fold=fold)
        instant = candidate.astimezone(UTC)
        if instant.astimezone(zone).replace(tzinfo=None) == naive and instant not in instants:
            instants.append(instant)
    return sorted(instants)


def resolve_local_wall_time(local_date: date, local_time: time, zone: ZoneInfo) -> datetime:
    """Resolve a wall time deterministically across DST gaps and folds."""
    naive = datetime.combine(local_date, local_time.replace(tzinfo=None))
    for minute in range(181):
        candidates = _valid_instants(naive + timedelta(minutes=minute), zone)
        if candidates:
            # A repeated summary time uses the later instant, so it cannot fire twice.
            return candidates[-1]
    raise ValueError("Summary time cannot be resolved in the school timezone")


def _local_midnight(local_date: date, zone: ZoneInfo) -> datetime:
    return resolve_local_wall_time(local_date, time(0, 0), zone)


def _week_date(local_date: date, target_weekday: int, *, on_or_before: bool = True) -> date:
    delta = (local_date.isoweekday() - target_weekday) % 7
    return local_date - timedelta(days=delta) if on_or_before else local_date + timedelta(days=(-delta) % 7)


def due_periods(
    school: School,
    policy: SchoolPointsNotificationPolicy,
    *,
    now: datetime,
) -> list[SummaryPeriod]:
    now = _aware(now).astimezone(UTC)
    try:
        zone = ZoneInfo(school.timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("School timezone is invalid") from exc
    local_now = now.astimezone(zone)
    local_date = local_now.date()
    periods: list[SummaryPeriod] = []

    if policy.daily_enabled:
        eligible = resolve_local_wall_time(local_date, policy.daily_summary_time, zone)
        if now >= eligible:
            periods.append(SummaryPeriod(
                "daily",
                local_date.isoformat(),
                _local_midnight(local_date, zone),
                eligible,
                eligible,
            ))

    if policy.weekly_enabled and local_date.isoweekday() == policy.weekly_summary_day:
        eligible = resolve_local_wall_time(local_date, policy.weekly_summary_time, zone)
        if now >= eligible:
            start_date = _week_date(local_date, policy.week_starts_on)
            end_offset = (policy.week_ends_on - policy.week_starts_on) % 7
            end_date = start_date + timedelta(days=end_offset)
            school_week_end = _local_midnight(end_date + timedelta(days=1), zone)
            # Events on days outside the configured school week are deliberately excluded.
            period_end = min(eligible, school_week_end)
            periods.append(SummaryPeriod(
                "weekly",
                f"{start_date.isoformat()}_{end_date.isoformat()}",
                _local_midnight(start_date, zone),
                period_end,
                eligible,
            ))

    last_day = calendar.monthrange(local_date.year, local_date.month)[1]
    if policy.monthly_enabled and local_date.day == last_day:
        eligible = resolve_local_wall_time(local_date, policy.monthly_summary_time, zone)
        if now >= eligible:
            month_start = date(local_date.year, local_date.month, 1)
            periods.append(SummaryPeriod(
                "monthly",
                f"{local_date.year:04d}-{local_date.month:02d}",
                _local_midnight(month_start, zone),
                eligible,
                eligible,
            ))
    return periods


def _insert_summaries(db: Session, values: list[dict]) -> None:
    if not values:
        return
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        statement = postgresql_insert(PointNotificationSummary).values(values).on_conflict_do_nothing(
            index_elements=["school_id", "student_id", "summary_type", "period_key"]
        )
    elif dialect == "sqlite":
        statement = sqlite_insert(PointNotificationSummary).values(values).on_conflict_do_nothing(
            index_elements=["school_id", "student_id", "summary_type", "period_key"]
        )
    else:
        statement = PointNotificationSummary.__table__.insert().values(values)
    db.execute(statement)
    db.flush()


def _aggregate_period(
    db: Session,
    *,
    school: School,
    policy: SchoolPointsNotificationPolicy,
    period: SummaryPeriod,
) -> int:
    aggregates = (
        db.query(
            BehaviourEvent.student_id,
            func.sum(case((BehaviourEvent.points_delta > 0, BehaviourEvent.points_delta), else_=0)).label("positive_total"),
            func.sum(case((BehaviourEvent.points_delta < 0, -BehaviourEvent.points_delta), else_=0)).label("needs_work_total"),
            func.count(BehaviourEvent.id).label("event_count"),
        )
        .join(Student, Student.id == BehaviourEvent.student_id)
        .filter(
            BehaviourEvent.school_id == school.id,
            BehaviourEvent.created_at >= period.period_start,
            BehaviourEvent.created_at <= period.period_end,
            BehaviourEvent.reversed_at.is_(None),
            Student.status == "active",
        )
        .group_by(BehaviourEvent.student_id)
        .order_by(BehaviourEvent.student_id)
        .all()
    )
    if not aggregates:
        return 0
    _insert_summaries(db, [
        {
            "school_id": school.id,
            "student_id": int(row.student_id),
            "summary_type": period.summary_type,
            "period_key": period.period_key,
            "period_start": period.period_start,
            "period_end": period.period_end,
            "eligible_at": period.eligible_at,
            "positive_total": int(row.positive_total or 0),
            "needs_work_total": int(row.needs_work_total or 0),
            "net_total": int(row.positive_total or 0) - int(row.needs_work_total or 0),
            "event_count": int(row.event_count),
            "policy_version": policy.policy_version,
        }
        for row in aggregates
    ])
    summaries = (
        db.query(PointNotificationSummary)
        .filter(
            PointNotificationSummary.school_id == school.id,
            PointNotificationSummary.summary_type == period.summary_type,
            PointNotificationSummary.period_key == period.period_key,
        )
        .order_by(PointNotificationSummary.student_id)
        .all()
    )
    links = (
        db.query(FhhLink)
        .join(Student, Student.id == FhhLink.student_id)
        .filter(
            FhhLink.school_id == school.id,
            FhhLink.student_id.in_([row.student_id for row in summaries]),
            FhhLink.status == "active",
            FhhLink.revoked_at.is_(None),
            Student.status == "active",
        )
        .order_by(FhhLink.id)
        .all()
    )
    summaries_by_student = {row.student_id: row for row in summaries}
    desired = {
        f"family:points:point_summary:{summaries_by_student[link.student_id].id}:summarized:v{policy.policy_version}:link:{link.id}"
        for link in links
    }
    existing = {
        row[0]
        for row in db.query(NotificationOutbox.dedupe_key)
        .filter(NotificationOutbox.dedupe_key.in_(desired))
        .all()
    } if desired else set()
    for link in links:
        summary = summaries_by_student[link.student_id]
        dedupe_key = f"family:points:point_summary:{summary.id}:summarized:v{policy.policy_version}:link:{link.id}"
        if dedupe_key in existing:
            continue
        db.add(NotificationOutbox(
            school_id=school.id,
            message_id=None,
            event_category="points",
            source_type="point_summary",
            source_id=summary.id,
            source_action="summarized",
            source_version=policy.policy_version,
            route_type="points",
            route_ref=str(summary.id),
            urgent=False,
            recipient_kind="fhh_link",
            recipient_fhh_link_id=link.id,
            channel="push",
            template_key=f"family.points.summary.{summary.summary_type}",
            template_args={
                "summary_type": summary.summary_type,
                "period_key": summary.period_key,
                "period_start": _aware(summary.period_start).astimezone(UTC).isoformat(),
                "period_end": _aware(summary.period_end).astimezone(UTC).isoformat(),
                "positive_total": summary.positive_total,
                "needs_work_total": summary.needs_work_total,
                "net_total": summary.net_total,
                "event_count": summary.event_count,
            },
            deep_link=f"fhh:points:{summary.summary_type}:{summary.period_key}",
            policy_version=policy.policy_version,
            state="pending",
            eligible_at=summary.eligible_at,
            scheduler_check_at=summary.eligible_at,
            next_attempt_at=summary.eligible_at,
            dedupe_key=dedupe_key,
        ))
    db.flush()
    return len(summaries)


def generate_due_point_summaries(
    db: Session,
    *,
    now: datetime | None = None,
    after_school_id: int = 0,
    school_limit: int = 100,
) -> GenerationBatchResult:
    now = _aware(now or datetime.now(UTC)).astimezone(UTC)
    rows = (
        db.query(SchoolPointsNotificationPolicy, School)
        .join(School, School.id == SchoolPointsNotificationPolicy.school_id)
        .filter(
            SchoolPointsNotificationPolicy.mode == "summaries",
            School.status.in_(ELIGIBLE_SCHOOL_STATUSES),
            School.id > after_school_id,
        )
        .order_by(School.id)
        .with_for_update(of=SchoolPointsNotificationPolicy, skip_locked=True)
        .limit(school_limit)
        .all()
    )
    generated = 0
    for policy, school in rows:
        try:
            for period in due_periods(school, policy, now=now):
                generated += _aggregate_period(db, school=school, policy=policy, period=period)
        except ValueError:
            logger.exception("Point summary policy could not be evaluated for school_id=%s", school.id)
    db.commit()
    next_after = int(rows[-1][1].id) if len(rows) == school_limit else 0
    return GenerationBatchResult(generated=generated, scanned=len(rows), next_after_school_id=next_after)


def process_point_summary_generation_batch(
    session_factory: Callable[[], Session],
    *,
    now: datetime | None = None,
    after_school_id: int = 0,
    school_limit: int = 100,
) -> GenerationBatchResult:
    db = session_factory()
    try:
        return generate_due_point_summaries(
            db,
            now=now,
            after_school_id=after_school_id,
            school_limit=school_limit,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def late_summary_periods(db: Session, event: BehaviourEvent) -> list[dict[str, str]]:
    occurred_at = _aware(event.created_at)
    school = db.query(School).filter(School.id == event.school_id).first()
    if school is None:
        return []
    try:
        local_date = occurred_at.astimezone(ZoneInfo(school.timezone)).date()
    except ZoneInfoNotFoundError:
        return []
    rows = (
        db.query(PointNotificationSummary.summary_type, PointNotificationSummary.period_key)
        .filter(
            PointNotificationSummary.school_id == event.school_id,
            PointNotificationSummary.student_id == event.student_id,
        )
        .order_by(PointNotificationSummary.summary_type)
        .all()
    )
    matched: list[dict[str, str]] = []
    for summary_type, period_key in rows:
        if summary_type == "daily" and period_key == local_date.isoformat():
            matched.append({"summary_type": summary_type, "period_key": period_key})
        elif summary_type == "monthly" and period_key == f"{local_date.year:04d}-{local_date.month:02d}":
            matched.append({"summary_type": summary_type, "period_key": period_key})
        elif summary_type == "weekly":
            try:
                start_text, end_text = period_key.split("_", 1)
                if date.fromisoformat(start_text) <= local_date <= date.fromisoformat(end_text):
                    matched.append({"summary_type": summary_type, "period_key": period_key})
            except ValueError:
                continue
    return matched

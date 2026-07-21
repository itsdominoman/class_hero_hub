from datetime import date, datetime, time, timezone

import pytest
from sqlalchemy import create_engine, event as sqlalchemy_event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.family_notifications import cancel_undispatched_immediate_points, enqueue_family_notifications
from app.models_school import (
    BehaviourCategory,
    BehaviourEvent,
    FhhLink,
    FhhLinkInvite,
    NotificationOutbox,
    PointNotificationSummary,
    School,
    SchoolPointsNotificationPolicy,
    Student,
    User,
)
from app.point_notification_summaries import due_periods, generate_due_point_summaries, late_summary_periods


UTC = timezone.utc


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _world(db, *, timezone_name="Asia/Muscat", week_start=7, week_end=4, weekly_day=4):
    user = User(email="points@test", name="Teacher", google_sub="points-teacher", status="active")
    school = School(name="Points School", slug=f"points-{timezone_name.replace('/', '-').lower()}-{week_start}", status="active", timezone=timezone_name)
    db.add_all([user, school]); db.flush()
    policy = SchoolPointsNotificationPolicy(
        school_id=school.id,
        mode="summaries",
        daily_enabled=True,
        weekly_enabled=True,
        monthly_enabled=True,
        week_starts_on=week_start,
        week_ends_on=week_end,
        weekly_summary_day=weekly_day,
        daily_summary_time=time(15, 15),
        weekly_summary_time=time(15, 30),
        monthly_summary_time=time(15, 30),
    )
    positive = BehaviourCategory(school_id=school.id, type="positive", label="Positive", points_value=1, active=True)
    needs_work = BehaviourCategory(school_id=school.id, type="needs_work", label="Needs work", points_value=-1, active=True)
    alice = Student(school_id=school.id, external_ref="A", first_name="Alice", last_name="A", status="active")
    bob = Student(school_id=school.id, external_ref="B", first_name="Bob", last_name="B", status="active")
    db.add_all([policy, positive, needs_work, alice, bob]); db.flush()
    links = []
    for index, student in enumerate((alice, bob), 1):
        invite = FhhLinkInvite(
            school_id=school.id, student_id=student.id, token_hash=f"invite-{school.id}-{index}",
            display_code_last4=f"00{index:02d}", created_by_user_id=user.id,
        )
        db.add(invite); db.flush()
        link = FhhLink(
            school_id=school.id, student_id=student.id, source_invite_id=invite.id,
            link_token_hash=f"link-{school.id}-{index}", fhh_child_ref=f"child-{index}", status="active",
        )
        db.add(link); db.flush(); links.append(link)
    db.commit()
    return school, policy, user, positive, needs_work, alice, bob, links


def _event(db, school, student, category, user, points, at):
    row = BehaviourEvent(
        school_id=school.id,
        student_id=student.id,
        category_id=category.id,
        actor_user_id=user.id,
        points_delta=points,
        note="Private detail that must never enter the summary payload",
        source="teacher",
        context_type="general",
        created_at=at,
    )
    db.add(row); db.flush()
    return row


def test_daily_mixed_totals_children_no_activity_idempotency_and_late_event(db):
    school, _policy, user, positive, needs_work, alice, bob, _links = _world(db)
    _event(db, school, alice, positive, user, 3, datetime(2026, 7, 21, 7, 0, tzinfo=UTC))
    _event(db, school, alice, positive, user, 5, datetime(2026, 7, 21, 8, 0, tzinfo=UTC))
    _event(db, school, alice, needs_work, user, -2, datetime(2026, 7, 21, 9, 0, tzinfo=UTC))
    _event(db, school, bob, positive, user, 1, datetime(2026, 7, 21, 10, 0, tzinfo=UTC))
    now = datetime(2026, 7, 21, 11, 16, tzinfo=UTC)
    first = generate_due_point_summaries(db, now=now)
    assert first.generated == 2
    summaries = db.query(PointNotificationSummary).filter_by(summary_type="daily").order_by(PointNotificationSummary.student_id).all()
    assert [(row.positive_total, row.needs_work_total, row.net_total, row.event_count) for row in summaries] == [(8, 2, 6, 3), (1, 0, 1, 1)]
    assert db.query(NotificationOutbox).count() == 2
    assert "Private detail" not in str([row.template_args for row in db.query(NotificationOutbox).all()])
    second = generate_due_point_summaries(db, now=now)
    assert second.generated == 2  # existing summaries are observed, never duplicated
    assert db.query(PointNotificationSummary).count() == 2
    assert db.query(NotificationOutbox).count() == 2
    late = _event(db, school, alice, positive, user, 4, datetime(2026, 7, 21, 12, 0, tzinfo=UTC))
    assert late_summary_periods(db, late) == [{"summary_type": "daily", "period_key": "2026-07-21"}]
    generate_due_point_summaries(db, now=datetime(2026, 7, 21, 13, 0, tzinfo=UTC))
    assert db.query(PointNotificationSummary).count() == 2


def test_no_activity_creates_no_summary(db):
    _world(db)
    result = generate_due_point_summaries(db, now=datetime(2026, 7, 21, 11, 16, tzinfo=UTC))
    assert result.generated == 0
    assert db.query(PointNotificationSummary).count() == 0


def test_uis_week_is_sunday_through_thursday_and_excludes_outside_days(db):
    school, _policy, user, positive, _needs_work, alice, _bob, _links = _world(db)
    _event(db, school, alice, positive, user, 99, datetime(2026, 7, 17, 8, 0, tzinfo=UTC))  # Friday before UIS week
    for day in range(19, 24):
        _event(db, school, alice, positive, user, 1, datetime(2026, 7, day, 8, 0, tzinfo=UTC))
    generate_due_point_summaries(db, now=datetime(2026, 7, 23, 11, 31, tzinfo=UTC))
    weekly = db.query(PointNotificationSummary).filter_by(summary_type="weekly").one()
    assert weekly.period_key == "2026-07-19_2026-07-23"
    assert weekly.positive_total == 5


def test_south_african_monday_friday_week_and_explicit_weekly_time(db):
    school, policy, _user, _positive, _needs_work, _alice, _bob, _links = _world(
        db, timezone_name="Africa/Johannesburg", week_start=1, week_end=5, weekly_day=5
    )
    policy.weekly_summary_time = time(14, 45)
    db.flush()
    before = due_periods(school, policy, now=datetime(2026, 7, 24, 12, 44, tzinfo=UTC))
    after = due_periods(school, policy, now=datetime(2026, 7, 24, 12, 45, tzinfo=UTC))
    assert not any(row.summary_type == "weekly" for row in before)
    weekly = next(row for row in after if row.summary_type == "weekly")
    assert weekly.period_key == "2026-07-20_2026-07-24"


@pytest.mark.parametrize(
    "local_date, expected_key",
    [(date(2027, 2, 28), "2027-02"), (date(2028, 2, 29), "2028-02"), (date(2026, 1, 31), "2026-01")],
)
def test_monthly_runs_on_calendar_end_including_weekends_without_holidays(db, local_date, expected_key):
    school, policy, _user, _positive, _needs_work, _alice, _bob, _links = _world(db)
    eligible_local = datetime.combine(local_date, time(15, 30), tzinfo=timezone.utc).replace(tzinfo=None)
    # Muscat is UTC+4 and has no DST.
    now = datetime(local_date.year, local_date.month, local_date.day, 11, 30, tzinfo=UTC)
    periods = due_periods(school, policy, now=now)
    monthly = next(row for row in periods if row.summary_type == "monthly")
    assert monthly.period_key == expected_key


def test_dst_gap_resolves_once_and_immediate_off_modes(db):
    school, policy, user, positive, _needs_work, alice, _bob, _links = _world(
        db, timezone_name="America/New_York", week_start=1, week_end=5, weekly_day=5
    )
    policy.daily_summary_time = time(2, 30)  # nonexistent on 2026-03-08; resolves to 03:00 EDT
    assert not due_periods(school, policy, now=datetime(2026, 3, 8, 6, 59, tzinfo=UTC))
    daily = next(row for row in due_periods(school, policy, now=datetime(2026, 3, 8, 7, 0, tzinfo=UTC)) if row.summary_type == "daily")
    assert daily.eligible_at == datetime(2026, 3, 8, 7, 0, tzinfo=UTC)
    point = _event(db, school, alice, positive, user, 1, datetime(2026, 3, 8, 6, 0, tzinfo=UTC))
    policy.mode = "immediate"
    db.flush()
    assert len(enqueue_family_notifications(db, category="points", source=point, action="awarded")) == 1
    policy.mode = "off"
    policy.policy_version += 1
    db.flush()
    point2 = _event(db, school, alice, positive, user, 1, datetime(2026, 3, 8, 6, 1, tzinfo=UTC))
    assert enqueue_family_notifications(db, category="points", source=point2, action="awarded") == []


def test_revoked_link_receives_no_summary_and_generation_is_set_based(db):
    school, _policy, user, positive, _needs_work, alice, bob, links = _world(db)
    links[1].status = "revoked"
    links[1].revoked_at = datetime(2026, 7, 21, 8, 0, tzinfo=UTC)
    _event(db, school, alice, positive, user, 1, datetime(2026, 7, 21, 7, 0, tzinfo=UTC))
    _event(db, school, bob, positive, user, 1, datetime(2026, 7, 21, 7, 0, tzinfo=UTC))
    statements = []
    def capture(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.lower())
    sqlalchemy_event.listen(db.get_bind(), "before_cursor_execute", capture)
    try:
        generate_due_point_summaries(db, now=datetime(2026, 7, 21, 11, 16, tzinfo=UTC))
    finally:
        sqlalchemy_event.remove(db.get_bind(), "before_cursor_execute", capture)
    assert db.query(PointNotificationSummary).count() == 2
    assert db.query(NotificationOutbox).count() == 1
    assert db.query(NotificationOutbox).one().recipient_fhh_link_id == links[0].id
    assert len([statement for statement in statements if "from behaviour_events" in statement]) == 1


def test_policy_change_cancels_only_undispatched_immediate_points(db):
    school, policy, user, positive, _needs_work, alice, _bob, _links = _world(db)
    policy.mode = "immediate"
    first = _event(db, school, alice, positive, user, 1, datetime(2026, 7, 21, 7, 0, tzinfo=UTC))
    second = _event(db, school, alice, positive, user, 1, datetime(2026, 7, 21, 7, 1, tzinfo=UTC))
    pending = enqueue_family_notifications(db, category="points", source=first, action="awarded")[0]
    accepted = enqueue_family_notifications(db, category="points", source=second, action="awarded")[0]
    accepted.state = "provider_accepted"
    accepted.provider_accepted_at = datetime(2026, 7, 21, 7, 2, tzinfo=UTC)
    accepted.completed_at = accepted.provider_accepted_at
    db.flush()
    assert cancel_undispatched_immediate_points(db, school_id=school.id, now=datetime(2026, 7, 21, 7, 3, tzinfo=UTC)) == 1
    db.expire_all()
    pending = db.query(NotificationOutbox).filter_by(id=pending.id).one()
    accepted = db.query(NotificationOutbox).filter_by(id=accepted.id).one()
    assert pending.state == "cancelled"
    assert pending.last_error_code == "points_policy_changed"
    assert accepted.state == "provider_accepted"

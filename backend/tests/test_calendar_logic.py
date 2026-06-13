import os
from datetime import date, time, datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, schemas, database
from app.database import Base, get_db
from app.services import calendar_service, points_service

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
database.engine = engine
database.SessionLocal = TestingSessionLocal

from app.main import app

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()

def test_parent_calendar_crud_and_isolation(db, client):
    # Setup Families
    f1 = models.Family(timezone="Asia/Muscat", week_start_day=6)
    f2 = models.Family(timezone="Asia/Muscat", week_start_day=6)
    db.add_all([f1, f2])
    db.commit()

    # Parents
    p1 = models.ParentUser(email="p1@f1.com", family_id=f1.id, google_sub="s1")
    p2 = models.ParentUser(email="p2@f2.com", family_id=f2.id, google_sub="s2")
    db.add_all([p1, p2])
    db.commit()

    # Children
    c1 = models.Child(display_name="C1", family_id=f1.id)
    c2 = models.Child(display_name="C2", family_id=f2.id)
    db.add_all([c1, c2])
    db.commit()

    # Mock Auth for P1
    from app.auth import get_current_parent
    app.dependency_overrides[get_current_parent] = lambda: p1

    # P1 creates entry for C1
    resp = client.post("/api/calendar/", json={
        "child_id": c1.id,
        "title": "C1 Task",
        "entry_type": "task",
        "is_rewardable": True,
        "points_value": 5,
        "start_date": "2026-05-06",
        "recurrence_type": "none"
    })
    assert resp.status_code == 200
    entry_id = resp.json()["id"]

    # P1 tries to create for C2 (Other family)
    resp = client.post("/api/calendar/", json={
        "child_id": c2.id,
        "title": "Evil Task",
        "entry_type": "task",
        "start_date": "2026-05-06",
        "recurrence_type": "none"
    })
    assert resp.status_code == 404

    # P1 lists calendar for C1
    resp = client.get(f"/api/calendar/?child_id={c1.id}&from_date=2026-05-01&to_date=2026-05-10")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["entry"]["title"] == "C1 Task"

    # P1 deletes entry
    client.delete(f"/api/calendar/{entry_id}")
    db.refresh(db.query(models.CalendarEntry).get(entry_id))
    assert db.query(models.CalendarEntry).get(entry_id).is_active == False

    del app.dependency_overrides[get_current_parent]

def test_child_calendar_completion_flow(db, client):
    family = models.Family(timezone="Asia/Muscat", week_start_day=6)
    db.add(family)
    db.commit()
    parent = models.ParentUser(email="p@f.com", family_id=family.id, google_sub="s")
    child = models.Child(display_name="Kid", family_id=family.id)
    db.add_all([parent, child])
    db.commit()

    entry = models.CalendarEntry(
        family_id=family.id, child_id=child.id, created_by_parent_id=parent.id,
        title="Brush Teeth", entry_type="task", is_rewardable=True, points_value=5,
        start_date=date(2026, 5, 6), recurrence_type="none"
    )
    db.add(entry)
    db.commit()

    # Mock Child Auth
    from app.child_auth import get_current_child
    app.dependency_overrides[get_current_child] = lambda: child

    # Child completes
    resp = client.post(f"/api/child/calendar/{entry.id}/complete?occurrence_date=2026-05-06")
    assert resp.status_code == 200
    completion_id = resp.json()["id"]
    assert resp.json()["status"] == "pending"

    # Verify no points yet
    balances = points_service.calculate_balances(db, child.id)
    assert balances["spending_balance"] == 0

    # Mock Parent Auth
    from app.auth import get_current_parent
    app.dependency_overrides[get_current_parent] = lambda: parent

    # Parent approves
    resp = client.post(f"/api/calendar/completions/{completion_id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert resp.json()["points_awarded"] == 5

    # Verify points awarded
    balances = points_service.calculate_balances(db, child.id)
    assert balances["spending_balance"] == 5

    del app.dependency_overrides[get_current_child]
    del app.dependency_overrides[get_current_parent]

def test_streak_bonus_multiplier(db, client):
    # Week start: May 3 (Sun)
    # Week end: May 9 (Sat)
    # Bonus day: May 10 (Sun)
    family = models.Family(timezone="Asia/Muscat", week_start_day=6)
    db.add(family)
    db.commit()
    parent = models.ParentUser(email="p@f.com", family_id=family.id, google_sub="s")
    child = models.Child(display_name="Kid", family_id=family.id)
    db.add_all([parent, child])
    db.commit()

    # Create a streak for previous week
    streak = models.WeeklyStreak(
        family_id=family.id, child_id=child.id,
        week_start_date=date(2026, 5, 3), week_end_date=date(2026, 5, 9),
        bonus_date=date(2026, 5, 10), streak_earned=True, bonus_multiplier=2.0
    )
    db.add(streak)
    db.commit()

    entry = models.CalendarEntry(
        family_id=family.id, child_id=child.id, created_by_parent_id=parent.id,
        title="Bonus Task", entry_type="task", is_rewardable=True, points_value=10,
        start_date=date(2026, 5, 10), recurrence_type="none"
    )
    db.add(entry)
    db.commit()

    from app.auth import get_current_parent
    app.dependency_overrides[get_current_parent] = lambda: parent

    # Parent completes directly on bonus day
    resp = client.post(f"/api/calendar/{entry.id}/complete?occurrence_date=2026-05-10")
    assert resp.status_code == 200
    assert resp.json()["points_awarded"] == 20 # 10 * 2.0
    assert resp.json()["bonus_multiplier_applied"] == 2.0
    assert resp.json()["streak_source_id"] == streak.id

    # Verify non-bonus day
    entry2 = models.CalendarEntry(
        family_id=family.id, child_id=child.id, created_by_parent_id=parent.id,
        title="Normal Task", entry_type="task", is_rewardable=True, points_value=10,
        start_date=date(2026, 5, 11), recurrence_type="none"
    )
    db.add(entry2)
    db.commit()
    
    resp = client.post(f"/api/calendar/{entry2.id}/complete?occurrence_date=2026-05-11")
    assert resp.status_code == 200
    assert resp.json()["points_awarded"] == 10
    assert resp.json()["bonus_multiplier_applied"] == 1.0

    del app.dependency_overrides[get_current_parent]


# E1 — "what's outstanding today" pure rules (no DB), so the dashboard tile and
# any future scheduler share one definition.

def test_task_is_outstanding():
    # Events are never "outstanding" (they just occur).
    assert calendar_service.task_is_outstanding("event", None) is False
    assert calendar_service.task_is_outstanding("event", "approved") is False
    # A task is outstanding until APPROVED — including child-claimed (pending)
    # and rejected.
    assert calendar_service.task_is_outstanding("task", None) is True
    assert calendar_service.task_is_outstanding("task", "pending") is True
    assert calendar_service.task_is_outstanding("task", "rejected") is True
    assert calendar_service.task_is_outstanding("task", "approved") is False


def test_count_attention_items():
    items = [
        ("event", None),          # +1 (events always count)
        ("event", "approved"),    # +1
        ("task", None),           # +1 (not done)
        ("task", "pending"),      # +1 (child claimed, still outstanding)
        ("task", "rejected"),     # +1
        ("task", "approved"),     # +0 (done)
    ]
    assert calendar_service.count_attention_items(items) == 5
    assert calendar_service.count_attention_items([]) == 0


# E1 — the dashboard summary endpoint.

def test_calendar_summary_endpoint(db, client):
    family = models.Family(timezone="Asia/Muscat", week_start_day=6)
    db.add(family)
    db.commit()
    parent = models.ParentUser(email="p@f.com", family_id=family.id, google_sub="s")
    child = models.Child(display_name="Kid", family_id=family.id)
    db.add_all([parent, child])
    db.commit()

    from app.auth import get_current_parent
    app.dependency_overrides[get_current_parent] = lambda: parent
    try:
        # No entries yet -> tile hidden (configured False), nothing to show.
        resp = client.get("/api/calendar/summary")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body == {"configured": False, "tile_count": 0, "today": [], "tomorrow": []}

        today = calendar_service.get_family_today(family.timezone)
        tomorrow = today + timedelta(days=1)

        def _entry(title, entry_type, start, rewardable=False, points=None):
            e = models.CalendarEntry(
                family_id=family.id, child_id=child.id, created_by_parent_id=parent.id,
                title=title, entry_type=entry_type, is_rewardable=rewardable,
                points_value=points, start_date=start, recurrence_type="none",
            )
            db.add(e)
            db.commit()
            db.refresh(e)
            return e

        today_event = _entry("Soccer", "event", today)
        today_task = _entry("Walk the dog", "task", today, rewardable=True, points=5)
        done_task = _entry("Brush teeth", "task", today, rewardable=True, points=2)
        _entry("Dentist", "event", tomorrow)

        # Mark one of today's tasks done (approved) — should drop from the count.
        resp = client.post(f"/api/calendar/{done_task.id}/complete?occurrence_date={today.isoformat()}")
        assert resp.status_code == 200

        resp = client.get("/api/calendar/summary")
        body = resp.json()
        assert body["configured"] is True
        # today: 1 event + 1 outstanding task + 0 (approved task excluded) = 2
        assert body["tile_count"] == 2
        assert [c["child_id"] for c in body["today"]] == [child.id]
        assert len(body["today"][0]["items"]) == 3  # all 3 of today's items listed
        assert [c["child_id"] for c in body["tomorrow"]] == [child.id]
        assert len(body["tomorrow"][0]["items"]) == 1
        # F1: the tomorrow occurrence carries the event title (the look-ahead
        # lists titles, not just counts) and is an event.
        tomorrow_item = body["tomorrow"][0]["items"][0]
        assert tomorrow_item["entry"]["title"] == "Dentist"
        assert tomorrow_item["entry"]["entry_type"] == "event"

        # A child-claimed (pending) completion still counts as outstanding.
        from datetime import datetime as _dt, timezone as _tz
        db.add(models.CalendarCompletion(
            entry_id=today_task.id, child_id=child.id, occurrence_date=today,
            status="pending", completed_at=_dt.now(_tz.utc),
        ))
        db.commit()
        resp = client.get("/api/calendar/summary")
        assert resp.json()["tile_count"] == 2  # unchanged: pending is still outstanding
        # G1: the Today modal resolves a child's claim in place, so the summary
        # must expose the pending completion's id + status per task (what the
        # Confirm/Reject buttons post to /completions/{id}/approve|reject).
        today_task_item = next(
            item for item in resp.json()["today"][0]["items"]
            if item["entry"]["id"] == today_task.id
        )
        assert today_task_item["completion"] is not None
        assert today_task_item["completion"]["status"] == "pending"
        assert isinstance(today_task_item["completion"]["id"], int)
    finally:
        del app.dependency_overrides[get_current_parent]

def test_duplicate_completion_blocked(db, client):
    family = models.Family()
    db.add(family)
    db.commit()
    parent = models.ParentUser(email="p@f.com", family_id=family.id, google_sub="s")
    child = models.Child(display_name="Kid", family_id=family.id)
    db.add_all([parent, child])
    db.commit()

    entry = models.CalendarEntry(
        family_id=family.id, child_id=child.id, created_by_parent_id=parent.id,
        title="Task", entry_type="task", is_rewardable=True, points_value=5,
        start_date=date(2026, 5, 6), recurrence_type="none"
    )
    db.add(entry)
    db.commit()

    from app.auth import get_current_parent
    app.dependency_overrides[get_current_parent] = lambda: parent

    # First completion
    resp = client.post(f"/api/calendar/{entry.id}/complete?occurrence_date=2026-05-06")
    assert resp.status_code == 200

    # Duplicate completion
    resp = client.post(f"/api/calendar/{entry.id}/complete?occurrence_date=2026-05-06")
    assert resp.status_code == 409
    assert "Already completed" in resp.json()["detail"]

    del app.dependency_overrides[get_current_parent]

def test_week_bounds_sunday_start():
    # May 6, 2026 is a Wednesday (2)
    ref_date = date(2026, 5, 6)
    # Sunday start (6)
    start, end = calendar_service.get_week_bounds(ref_date, 6)
    assert start == date(2026, 5, 3)  # Sunday
    assert end == date(2026, 5, 9)    # Saturday
    assert start.weekday() == 6
    assert end.weekday() == 5

def test_week_bounds_monday_start():
    # May 6, 2026 is a Wednesday (2)
    ref_date = date(2026, 5, 6)
    # Monday start (0)
    start, end = calendar_service.get_week_bounds(ref_date, 0)
    assert start == date(2026, 5, 4)  # Monday
    assert end == date(2026, 5, 10)   # Sunday
    assert start.weekday() == 0
    assert end.weekday() == 6

def test_bonus_date_calculation():
    week_start = date(2026, 5, 3)
    bonus_date = calendar_service.get_bonus_date(week_start)
    assert bonus_date == date(2026, 5, 10)

def test_resolve_occurrences_none():
    entry = models.CalendarEntry(
        start_date=date(2026, 5, 6),
        recurrence_type="none"
    )
    # Range includes entry
    occ = calendar_service.resolve_occurrences(entry, date(2026, 5, 1), date(2026, 5, 10))
    assert occ == [date(2026, 5, 6)]
    
    # Range excludes entry
    occ = calendar_service.resolve_occurrences(entry, date(2026, 5, 7), date(2026, 5, 10))
    assert occ == []

def test_resolve_occurrences_daily():
    entry = models.CalendarEntry(
        start_date=date(2026, 5, 1),
        recurrence_type="daily"
    )
    occ = calendar_service.resolve_occurrences(entry, date(2026, 5, 1), date(2026, 5, 3))
    assert occ == [date(2026, 5, 1), date(2026, 5, 2), date(2026, 5, 3)]

def test_resolve_occurrences_weekly():
    entry = models.CalendarEntry(
        start_date=date(2026, 5, 1), # Friday (4)
        recurrence_type="weekly",
        recurrence_days="0,2,4" # Mon, Wed, Fri
    )
    # May 1 (Fri), 2 (Sat), 3 (Sun), 4 (Mon), 5 (Tue), 6 (Wed)
    occ = calendar_service.resolve_occurrences(entry, date(2026, 5, 1), date(2026, 5, 6))
    assert occ == [date(2026, 5, 1), date(2026, 5, 4), date(2026, 5, 6)]

def test_calendar_completion_uniqueness(db):
    family = models.Family()
    db.add(family)
    db.commit()
    
    child = models.Child(family_id=family.id, display_name="Kid")
    db.add(child)
    db.commit()
    
    entry = models.CalendarEntry(family_id=family.id, child_id=child.id, title="Task", start_date=date(2026, 5, 6))
    db.add(entry)
    db.commit()
    
    # First completion
    comp1 = models.CalendarCompletion(entry_id=entry.id, child_id=child.id, occurrence_date=date(2026, 5, 6))
    db.add(comp1)
    db.commit()
    
    # Duplicate completion (same entry, child, date)
    comp2 = models.CalendarCompletion(entry_id=entry.id, child_id=child.id, occurrence_date=date(2026, 5, 6))
    db.add(comp2)
    with pytest.raises(IntegrityError):
        db.commit()

def test_family_defaults_and_backfill(db):
    # Test that new families get the expected defaults
    family = models.Family()
    db.add(family)
    db.commit()
    db.refresh(family)
    
    assert family.timezone == "Asia/Muscat"
    assert family.week_start_day == 6 # Sunday
    
    # Test Pydantic default
    f_schema = schemas.FamilyBase()
    assert f_schema.timezone == "Asia/Muscat"
    assert f_schema.week_start_day == 6

def test_weekly_streak_uniqueness(db):
    family = models.Family()
    db.add(family)
    db.commit()
    
    child = models.Child(family_id=family.id, display_name="Kid")
    db.add(child)
    db.commit()
    
    streak1 = models.WeeklyStreak(family_id=family.id, child_id=child.id, week_start_date=date(2026, 5, 3))
    db.add(streak1)
    db.commit()
    
    # Duplicate streak for same child and week
    streak2 = models.WeeklyStreak(family_id=family.id, child_id=child.id, week_start_date=date(2026, 5, 3))
    db.add(streak2)
    with pytest.raises(IntegrityError):
        db.commit()

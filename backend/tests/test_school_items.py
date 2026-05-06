from datetime import date
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("APP_ENV", "test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, database
from app.database import Base, get_db
from app.services import calendar_service

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


def _create_family_with_parent_and_child(db):
    family = models.Family(timezone="Asia/Muscat", week_start_day=6)
    db.add(family)
    db.commit()
    parent = models.ParentUser(email="parent@example.com", family_id=family.id, google_sub="google-sub")
    child = models.Child(display_name="Kid", family_id=family.id)
    db.add_all([parent, child])
    db.commit()
    return family, parent, child


def test_parent_can_replace_and_fetch_school_items(db, client):
    family, parent, child = _create_family_with_parent_and_child(db)

    from app.auth import get_current_parent
    app.dependency_overrides[get_current_parent] = lambda: parent

    resp = client.put(
        f"/api/school-items/?child_id={child.id}&weekday=2",
        json=[
            {"class_name": "Math", "needed_item": "Math book", "sort_order": 0},
            {"class_name": "P.E.", "needed_item": "Gym clothes", "sort_order": 1},
        ],
    )
    assert resp.status_code == 200
    assert [item["class_name"] for item in resp.json()] == ["Math", "P.E."]

    resp = client.get(f"/api/school-items/?child_id={child.id}&weekday=2")
    assert resp.status_code == 200
    assert [item["needed_item"] for item in resp.json()] == ["Math book", "Gym clothes"]

    del app.dependency_overrides[get_current_parent]


def test_parent_cannot_manage_other_family_child(db, client):
    family1, parent, child1 = _create_family_with_parent_and_child(db)
    family2 = models.Family(timezone="Asia/Muscat", week_start_day=6)
    db.add(family2)
    db.commit()
    child2 = models.Child(display_name="Other Kid", family_id=family2.id)
    db.add(child2)
    db.commit()

    from app.auth import get_current_parent
    app.dependency_overrides[get_current_parent] = lambda: parent

    resp = client.put(
        f"/api/school-items/?child_id={child2.id}&weekday=2",
        json=[{"class_name": "Science", "needed_item": "Science book", "sort_order": 0}],
    )
    assert resp.status_code == 404

    del app.dependency_overrides[get_current_parent]


def test_replace_updates_and_deletes_rows(db, client):
    family, parent, child = _create_family_with_parent_and_child(db)

    from app.auth import get_current_parent
    app.dependency_overrides[get_current_parent] = lambda: parent

    first = client.put(
        f"/api/school-items/?child_id={child.id}&weekday=2",
        json=[
            {"class_name": "Math", "needed_item": "Math book", "sort_order": 0},
            {"class_name": "English", "needed_item": "English book", "sort_order": 1},
        ],
    )
    assert first.status_code == 200
    first_items = first.json()
    math_id = first_items[0]["id"]

    second = client.put(
        f"/api/school-items/?child_id={child.id}&weekday=2",
        json=[
            {"id": math_id, "class_name": "Math", "needed_item": "Math workbook", "sort_order": 0},
        ],
    )
    assert second.status_code == 200
    assert len(second.json()) == 1
    assert second.json()[0]["needed_item"] == "Math workbook"

    del app.dependency_overrides[get_current_parent]


def test_today_endpoints_use_family_timezone(db, client, monkeypatch):
    family, parent, child = _create_family_with_parent_and_child(db)
    db.add(models.SchoolItem(
        family_id=family.id,
        child_id=child.id,
        weekday=2,
        class_name="Math",
        needed_item="Math book",
        sort_order=0,
        created_by_parent_id=parent.id,
    ))
    db.add(models.SchoolItem(
        family_id=family.id,
        child_id=child.id,
        weekday=3,
        class_name="Science",
        needed_item="Science book",
        sort_order=1,
        created_by_parent_id=parent.id,
    ))
    db.commit()

    called = {}

    def fake_get_family_today(timezone: str):
        called["timezone"] = timezone
        return date(2026, 5, 6)

    monkeypatch.setattr(calendar_service, "get_family_today", fake_get_family_today)

    from app.auth import get_current_parent
    from app.child_auth import get_current_child
    app.dependency_overrides[get_current_parent] = lambda: parent
    app.dependency_overrides[get_current_child] = lambda: child

    parent_resp = client.get(f"/api/school-items/today?child_id={child.id}&offset=0")
    assert parent_resp.status_code == 200
    assert parent_resp.json()[0]["class_name"] == "Math"
    assert called["timezone"] == family.timezone

    parent_tomorrow_resp = client.get(f"/api/school-items/today?child_id={child.id}&offset=1")
    assert parent_tomorrow_resp.status_code == 200
    assert parent_tomorrow_resp.json()[0]["class_name"] == "Science"
    assert called["timezone"] == family.timezone

    child_resp = client.get("/api/child/school-items/today?offset=0")
    assert child_resp.status_code == 200
    assert child_resp.json()[0]["class_name"] == "Math"
    assert called["timezone"] == family.timezone

    child_tomorrow_resp = client.get("/api/child/school-items/today?offset=1")
    assert child_tomorrow_resp.status_code == 200
    assert child_tomorrow_resp.json()[0]["class_name"] == "Science"
    assert called["timezone"] == family.timezone

    del app.dependency_overrides[get_current_parent]
    del app.dependency_overrides[get_current_child]


def test_today_endpoints_reject_invalid_offset(db, client):
    family, parent, child = _create_family_with_parent_and_child(db)

    from app.auth import get_current_parent
    from app.child_auth import get_current_child
    app.dependency_overrides[get_current_parent] = lambda: parent
    app.dependency_overrides[get_current_child] = lambda: child

    parent_resp = client.get(f"/api/school-items/today?child_id={child.id}&offset=2")
    assert parent_resp.status_code == 422

    child_resp = client.get("/api/child/school-items/today?offset=-1")
    assert child_resp.status_code == 422

    del app.dependency_overrides[get_current_parent]
    del app.dependency_overrides[get_current_child]


def test_child_cannot_fetch_another_childs_items(db, client):
    family = models.Family(timezone="Asia/Muscat", week_start_day=6)
    db.add(family)
    db.commit()
    parent = models.ParentUser(email="parent@example.com", family_id=family.id, google_sub="google-sub")
    child_one = models.Child(display_name="One", family_id=family.id)
    child_two = models.Child(display_name="Two", family_id=family.id)
    db.add_all([parent, child_one, child_two])
    db.commit()
    db.add(models.SchoolItem(
        family_id=family.id,
        child_id=child_two.id,
        weekday=2,
        class_name="Science",
        needed_item="Science book",
        sort_order=0,
        created_by_parent_id=parent.id,
    ))
    db.commit()

    from app.child_auth import get_current_child
    app.dependency_overrides[get_current_child] = lambda: child_one

    resp = client.get("/api/child/school-items/today")
    assert resp.status_code == 200
    assert resp.json() == []

    del app.dependency_overrides[get_current_child]


def test_legacy_school_items_migrate_and_are_hidden_from_calendar(db, client):
    family, parent, child = _create_family_with_parent_and_child(db)
    legacy_entry = models.CalendarEntry(
        family_id=family.id,
        child_id=child.id,
        created_by_parent_id=parent.id,
        title="History",
        description="[[school-item]]\nHistory book",
        entry_type="event",
        is_rewardable=False,
        start_date=date(2026, 5, 1),
        recurrence_type="weekly",
        recurrence_days="2",
    )
    db.add(legacy_entry)
    db.commit()

    from app.auth import get_current_parent
    app.dependency_overrides[get_current_parent] = lambda: parent

    school_resp = client.get(f"/api/school-items/?child_id={child.id}&weekday=2")
    assert school_resp.status_code == 200
    assert school_resp.json()[0]["class_name"] == "History"
    db.expire_all()
    assert db.query(models.CalendarEntry).get(legacy_entry.id).is_active is False

    calendar_resp = client.get(f"/api/calendar/?child_id={child.id}&from_date=2026-05-01&to_date=2026-05-10")
    assert calendar_resp.status_code == 200
    assert calendar_resp.json() == []

    del app.dependency_overrides[get_current_parent]

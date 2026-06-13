from datetime import date
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

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


# ---------------------------------------------------------------------------
# B2 — school-bag "pack for tomorrow" checklist
# ---------------------------------------------------------------------------
from datetime import timedelta

from app.services import school_items_service


def _make_school_item(db, child, weekday, class_name="Math", needed_item="Math book"):
    created_by = db.query(models.ParentUser).filter(
        models.ParentUser.family_id == child.family_id
    ).first()
    item = models.SchoolItem(
        family_id=child.family_id,
        child_id=child.id,
        weekday=weekday,
        class_name=class_name,
        needed_item=needed_item,
        sort_order=0,
        is_active=True,
        created_by_parent_id=created_by.id if created_by else None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def test_is_date_locked_boundary():
    today = date(2026, 6, 13)
    assert school_items_service.is_date_locked(today, today) is True          # today has begun
    assert school_items_service.is_date_locked(today - timedelta(days=1), today) is True   # past
    assert school_items_service.is_date_locked(today + timedelta(days=1), today) is False  # future = editable


def test_service_pack_and_unpack_future_date(db):
    family, parent, child = _create_family_with_parent_and_child(db)
    today = calendar_service.get_family_today(family.timezone)
    tomorrow = today + timedelta(days=1)
    item = _make_school_item(db, child, tomorrow.weekday())

    # Pack
    row = school_items_service.set_packed(db, child.id, item.id, tomorrow, today, packed=True)
    assert row is not None
    assert school_items_service.packed_item_ids(db, child.id, [item.id], tomorrow) == {item.id}

    # Idempotent pack
    school_items_service.set_packed(db, child.id, item.id, tomorrow, today, packed=True)
    assert db.query(models.SchoolItemCheck).count() == 1

    # Unpack
    assert school_items_service.set_packed(db, child.id, item.id, tomorrow, today, packed=False) is None
    assert school_items_service.packed_item_ids(db, child.id, [item.id], tomorrow) == set()
    # Idempotent unpack
    school_items_service.set_packed(db, child.id, item.id, tomorrow, today, packed=False)
    assert db.query(models.SchoolItemCheck).count() == 0


def test_service_rejects_locked_weekday_mismatch_and_missing(db):
    family, parent, child = _create_family_with_parent_and_child(db)
    today = calendar_service.get_family_today(family.timezone)
    tomorrow = today + timedelta(days=1)

    # Locked: packing for today (already begun)
    today_item = _make_school_item(db, child, today.weekday())
    with pytest.raises(school_items_service.SchoolCheckError) as exc:
        school_items_service.set_packed(db, child.id, today_item.id, today, today, packed=True)
    assert exc.value.code == "checklist_locked"

    # Weekday mismatch: item for tomorrow's weekday, packed for a date 2 days out
    tomorrow_item = _make_school_item(db, child, tomorrow.weekday())
    two_days = today + timedelta(days=2)
    if two_days.weekday() != tomorrow_item.weekday:
        with pytest.raises(school_items_service.SchoolCheckError) as exc:
            school_items_service.set_packed(db, child.id, tomorrow_item.id, two_days, today, packed=True)
        assert exc.value.code == "weekday_mismatch"

    # Missing / not owned
    with pytest.raises(school_items_service.SchoolCheckError) as exc:
        school_items_service.set_packed(db, child.id, 999999, tomorrow, today, packed=True)
    assert exc.value.code == "item_not_found"


def _override_child(child):
    from app.child_auth import get_current_child
    app.dependency_overrides[get_current_child] = lambda: child


def test_http_child_today_returns_packing_state_and_pack_unpack(db, client):
    family, parent, child = _create_family_with_parent_and_child(db)
    today = calendar_service.get_family_today(family.timezone)
    tomorrow = today + timedelta(days=1)
    item = _make_school_item(db, child, tomorrow.weekday())
    _override_child(child)
    try:
        # Tomorrow list: editable (locked=False), not yet packed
        resp = client.get("/api/child/school-items/today?offset=1")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body) == 1
        assert body[0]["packed"] is False
        assert body[0]["locked"] is False
        assert body[0]["check_date"] == tomorrow.isoformat()

        # Pack it
        resp = client.post(f"/api/child/school-items/{item.id}/pack", json={"check_date": tomorrow.isoformat()})
        assert resp.status_code == 200, resp.text
        assert resp.json()["packed"] is True

        # Reflected in the list
        resp = client.get("/api/child/school-items/today?offset=1")
        assert resp.json()[0]["packed"] is True

        # Unpack it
        resp = client.request("DELETE", f"/api/child/school-items/{item.id}/pack",
                              params={"check_date": tomorrow.isoformat()})
        assert resp.status_code == 200, resp.text
        assert resp.json()["packed"] is False
        resp = client.get("/api/child/school-items/today?offset=1")
        assert resp.json()[0]["packed"] is False
    finally:
        app.dependency_overrides.pop(__import__("app.child_auth", fromlist=["get_current_child"]).get_current_child, None)


def test_http_child_today_offset_zero_is_locked(db, client):
    family, parent, child = _create_family_with_parent_and_child(db)
    today = calendar_service.get_family_today(family.timezone)
    item = _make_school_item(db, child, today.weekday())
    _override_child(child)
    try:
        resp = client.get("/api/child/school-items/today?offset=0")
        assert resp.status_code == 200
        assert resp.json()[0]["locked"] is True

        # Packing for today is rejected (checklist has begun)
        resp = client.post(f"/api/child/school-items/{item.id}/pack", json={"check_date": today.isoformat()})
        assert resp.status_code == 409
        assert resp.json()["detail"] == "checklist_locked"
    finally:
        app.dependency_overrides.pop(__import__("app.child_auth", fromlist=["get_current_child"]).get_current_child, None)


def test_http_child_pack_unknown_item_404(db, client):
    family, parent, child = _create_family_with_parent_and_child(db)
    today = calendar_service.get_family_today(family.timezone)
    tomorrow = today + timedelta(days=1)
    _override_child(child)
    try:
        resp = client.post("/api/child/school-items/999999/pack", json={"check_date": tomorrow.isoformat()})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "item_not_found"
    finally:
        app.dependency_overrides.pop(__import__("app.child_auth", fromlist=["get_current_child"]).get_current_child, None)

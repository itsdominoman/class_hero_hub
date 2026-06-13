from datetime import date, datetime
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


# B1 follow-up — "does the family have any school items configured" existence
# check that drives whether the parent dashboard shows the school summary tile.

def test_service_family_has_school_items(db):
    family, parent, child = _create_family_with_parent_and_child(db)
    assert school_items_service.family_has_school_items(db, family.id) is False

    item = _make_school_item(db, child, 2)
    assert school_items_service.family_has_school_items(db, family.id) is True

    # Soft-deleting (is_active False) the only item => no longer "configured".
    item.is_active = False
    db.commit()
    assert school_items_service.family_has_school_items(db, family.id) is False


def test_service_family_has_school_items_scoped_per_family(db):
    family1, parent1, child1 = _create_family_with_parent_and_child(db)
    family2 = models.Family(timezone="Asia/Muscat", week_start_day=6)
    db.add(family2)
    db.commit()
    child2 = models.Child(display_name="Other", family_id=family2.id)
    db.add(child2)
    db.commit()

    _make_school_item(db, child1, 2)
    # family1 has an item, family2 does not — the check must not leak across.
    assert school_items_service.family_has_school_items(db, family1.id) is True
    assert school_items_service.family_has_school_items(db, family2.id) is False


def test_http_parent_school_items_configured(db, client):
    family, parent, child = _create_family_with_parent_and_child(db)

    from app.auth import get_current_parent
    app.dependency_overrides[get_current_parent] = lambda: parent
    try:
        resp = client.get("/api/school-items/configured")
        assert resp.status_code == 200
        assert resp.json() == {"configured": False}

        _make_school_item(db, child, 2)
        resp = client.get("/api/school-items/configured")
        assert resp.status_code == 200
        assert resp.json() == {"configured": True}
    finally:
        del app.dependency_overrides[get_current_parent]


# D3 — time-window pure functions (functions of local time only, so a future
# notification scheduler can reuse them). Tested directly with fixed datetimes.

def test_needed_today_window_open_all_day():
    # "Needed today" is visible from midnight onward — open at every hour.
    for hour in (0, 6, 12, 17, 18, 23):
        assert school_items_service.needed_today_window_open(datetime(2026, 6, 13, hour)) is True


def test_pack_tomorrow_window_open_from_6pm():
    assert school_items_service.pack_tomorrow_window_open(datetime(2026, 6, 13, 17, 59)) is False
    assert school_items_service.pack_tomorrow_window_open(datetime(2026, 6, 13, 18, 0)) is True
    assert school_items_service.pack_tomorrow_window_open(datetime(2026, 6, 13, 23, 30)) is True


def test_compute_tile_state():
    morning = datetime(2026, 6, 13, 8, 0)
    evening = datetime(2026, 6, 13, 20, 0)

    # Morning, items still missing today -> missing_today wins.
    assert school_items_service.compute_tile_state(morning, 3, 0) == ("missing_today", 3)
    # Morning, today resolved, pack-tomorrow window not open yet -> nothing.
    assert school_items_service.compute_tile_state(morning, 0, 5) == ("none", 0)
    # Evening, today resolved -> pack_tomorrow nudge.
    assert school_items_service.compute_tile_state(evening, 0, 5) == ("pack_tomorrow", 5)
    # Evening, both present -> missing_today takes priority.
    assert school_items_service.compute_tile_state(evening, 2, 5) == ("missing_today", 2)
    # Nothing anywhere -> none.
    assert school_items_service.compute_tile_state(evening, 0, 0) == ("none", 0)


# D2 — parent marks a "Needed today" (locked) item packed; overrides the lock.

def test_service_parent_override_bypasses_lock(db):
    family, parent, child = _create_family_with_parent_and_child(db)
    today = calendar_service.get_family_today(family.timezone)
    item = _make_school_item(db, child, today.weekday())

    # Child path is locked for today.
    with pytest.raises(school_items_service.SchoolCheckError) as exc:
        school_items_service.set_packed(db, child.id, item.id, today, today, packed=True)
    assert exc.value.code == "checklist_locked"

    # Parent override succeeds and writes the shared row.
    row = school_items_service.set_packed(
        db, child.id, item.id, today, today, packed=True, enforce_lock=False
    )
    assert row is not None
    assert school_items_service.packed_item_ids(db, child.id, [item.id], today) == {item.id}


def test_http_parent_pack_today_item(db, client):
    family, parent, child = _create_family_with_parent_and_child(db)
    today = calendar_service.get_family_today(family.timezone)
    item = _make_school_item(db, child, today.weekday())

    from app.auth import get_current_parent
    app.dependency_overrides[get_current_parent] = lambda: parent
    try:
        resp = client.post(
            f"/api/school-items/{item.id}/pack", json={"child_id": child.id}
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["packed"] is True
        assert body["locked"] is True  # today is locked for the child; parent overrode
        assert body["check_date"] == today.isoformat()

        # Reflected in the shared state (same row the child's view reads).
        assert school_items_service.packed_item_ids(db, child.id, [item.id], today) == {item.id}

        # Idempotent.
        resp = client.post(
            f"/api/school-items/{item.id}/pack", json={"child_id": child.id}
        )
        assert resp.status_code == 200
        assert db.query(models.SchoolItemCheck).count() == 1
    finally:
        del app.dependency_overrides[get_current_parent]


def test_http_parent_pack_rejects_other_family_child(db, client):
    family, parent, child = _create_family_with_parent_and_child(db)
    other_family = models.Family(timezone="Asia/Muscat", week_start_day=6)
    db.add(other_family)
    db.commit()
    other_child = models.Child(display_name="Stranger", family_id=other_family.id)
    db.add(other_child)
    db.commit()
    today = calendar_service.get_family_today(other_family.timezone)
    item = _make_school_item(db, other_child, today.weekday())

    from app.auth import get_current_parent
    app.dependency_overrides[get_current_parent] = lambda: parent
    try:
        resp = client.post(
            f"/api/school-items/{item.id}/pack", json={"child_id": other_child.id}
        )
        assert resp.status_code == 404  # child not in parent's family
    finally:
        del app.dependency_overrides[get_current_parent]


# D3 — the aggregate summary endpoint. "Needed today" is always within its
# window, so we can assert its drop-out behaviour deterministically; the
# evening "Pack for tomorrow" flag is derived from the real family clock.

def test_http_school_summary_needed_today_dropout(db, client):
    family, parent, child = _create_family_with_parent_and_child(db)
    now_local = calendar_service.get_family_now(family.timezone)
    today = now_local.date()
    item = _make_school_item(db, child, today.weekday())

    from app.auth import get_current_parent
    app.dependency_overrides[get_current_parent] = lambda: parent
    try:
        resp = client.get("/api/school-items/summary")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["configured"] is True
        assert body["show_needed_today"] is True
        # Window flag matches the family clock at request time.
        assert body["show_pack_tomorrow"] == (now_local.hour >= 18)
        # Child has an unpacked today item -> appears, tile flags it missing.
        assert [c["child_id"] for c in body["needed_today"]] == [child.id]
        assert body["tile_mode"] == "missing_today"
        assert body["tile_count"] == 1

        # Parent resolves it -> child drops out of needed_today.
        resp = client.post(
            f"/api/school-items/{item.id}/pack", json={"child_id": child.id}
        )
        assert resp.status_code == 200
        resp = client.get("/api/school-items/summary")
        body = resp.json()
        assert body["needed_today"] == []
        # Tile mode is none unless the evening pack-tomorrow window is open with
        # unpacked tomorrow items (no tomorrow items configured here).
        assert body["tile_mode"] == "none"
    finally:
        del app.dependency_overrides[get_current_parent]


def test_http_school_summary_unconfigured(db, client):
    family, parent, child = _create_family_with_parent_and_child(db)
    from app.auth import get_current_parent
    app.dependency_overrides[get_current_parent] = lambda: parent
    try:
        resp = client.get("/api/school-items/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["configured"] is False
        assert body["needed_today"] == []
        assert body["pack_tomorrow"] == []
        assert body["tile_mode"] == "none"
    finally:
        del app.dependency_overrides[get_current_parent]

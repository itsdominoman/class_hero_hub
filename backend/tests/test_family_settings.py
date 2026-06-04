import os
from datetime import date, datetime, timedelta, timezone

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database, models, schemas
from app.database import Base, get_db
from app.main import app
from app.services import allowance_service, calendar_service, points_service

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
database.engine = engine
database.SessionLocal = TestingSessionLocal


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def create_family(db, timezone="Asia/Muscat", week_start_day=6):
    family = models.Family(timezone=timezone, week_start_day=week_start_day)
    db.add(family)
    db.commit()
    db.refresh(family)
    return family


def create_parent(db, family, email="parent@example.com"):
    parent = models.ParentUser(
        email=email,
        name="Parent",
        google_sub=f"sub-{email}",
        family_id=family.id,
        status="active",
    )
    db.add(parent)
    db.commit()
    db.refresh(parent)
    return parent


def create_child(db, family, name="Kid"):
    child = models.Child(display_name=name, family_id=family.id, active=True)
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


def authenticate(client, parent):
    csrf_token = "test-csrf-token"
    client.cookies.set("access_token", auth.create_access_token({"sub": parent.email}))
    client.cookies.set("csrf_token", csrf_token)
    return {"X-CSRF-Token": csrf_token}


def clear_auth(client):
    client.cookies.clear()


def test_get_family_settings_returns_default_named_week_start_day(db, client):
    clear_auth(client)
    family = create_family(db)
    parent = create_parent(db, family)
    authenticate(client, parent)

    response = client.get("/api/family/settings")

    assert response.status_code == 200
    assert response.json() == {
        "timezone": "Asia/Muscat",
        "week_start_day": "sunday",
    }
    assert isinstance(response.json()["week_start_day"], str)


def test_parent_can_update_own_family_week_start_day(db, client):
    clear_auth(client)
    family = create_family(db)
    parent = create_parent(db, family)
    headers = authenticate(client, parent)

    response = client.patch(
        "/api/family/settings",
        headers=headers,
        json={"week_start_day": "monday"},
    )

    assert response.status_code == 200
    assert response.json()["week_start_day"] == "monday"
    db.refresh(family)
    assert family.week_start_day == 0


def test_invalid_week_start_day_is_rejected_without_changing_family(db, client):
    clear_auth(client)
    family = create_family(db, week_start_day=6)
    parent = create_parent(db, family)
    headers = authenticate(client, parent)

    response = client.patch(
        "/api/family/settings",
        headers=headers,
        json={"week_start_day": "funday"},
    )

    assert response.status_code == 422
    db.refresh(family)
    assert family.week_start_day == 6


def test_unauthenticated_user_cannot_read_or_update_family_settings(client):
    clear_auth(client)

    get_response = client.get("/api/family/settings")
    patch_response = client.patch("/api/family/settings", json={"week_start_day": "monday"})

    assert get_response.status_code == 401
    assert patch_response.status_code == 401


def test_endpoint_updates_only_current_parent_family(db, client):
    clear_auth(client)
    family_one = create_family(db, week_start_day=6)
    family_two = create_family(db, week_start_day=5)
    parent_one = create_parent(db, family_one, email="one@example.com")
    create_parent(db, family_two, email="two@example.com")
    headers = authenticate(client, parent_one)

    response = client.patch(
        "/api/family/settings",
        headers=headers,
        json={"week_start_day": "tuesday"},
    )

    assert response.status_code == 200
    db.refresh(family_one)
    db.refresh(family_two)
    assert family_one.week_start_day == 1
    assert family_two.week_start_day == 5


def test_weekly_ledger_filter_respects_family_week_start_day(db, client):
    clear_auth(client)
    family = create_family(db, week_start_day=6)
    child = create_child(db, family)
    now = datetime(2026, 5, 6, 12, 0, 0)
    rows = [
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=5,
            description="previous saturday",
            created_at=datetime(2026, 5, 2, 12, 0, 0),
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=10,
            description="current sunday",
            created_at=datetime(2026, 5, 3, 12, 0, 0),
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=20,
            description="current monday",
            created_at=datetime(2026, 5, 4, 12, 0, 0),
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=30,
            description="next sunday",
            created_at=datetime(2026, 5, 10, 12, 0, 0),
        ),
    ]
    db.add_all(rows)
    db.commit()

    transactions = points_service.get_ledger_transactions(
        db,
        child.id,
        period="week",
        now=now,
        week_start_day=family.week_start_day,
    )
    summary = points_service.get_ledger_summary(
        db,
        child.id,
        period="week",
        now=now,
        week_start_day=family.week_start_day,
    )

    descriptions = {transaction.description for transaction in transactions}
    assert descriptions == {"current sunday", "current monday"}
    assert summary["gained"] == 30
    assert summary["transaction_count"] == 2


def test_weekly_ledger_bounds_can_start_on_monday():
    now = datetime(2026, 5, 6, 12, 0, 0)

    start, end = points_service.get_period_bounds("week", now=now, week_start_day=0)

    assert start == datetime(2026, 5, 4, 0, 0, 0)
    assert end == start + timedelta(days=7)


def test_calendar_and_allowance_weekly_bounds_respect_week_start_day(db, client):
    clear_auth(client)
    family = create_family(db, week_start_day=5)
    child = create_child(db, family)
    setting = schemas.AllowanceSettings(
        family_id=family.id,
        child_id=child.id,
        is_enabled=True,
        currency="OMR",
        currency_exponent=3,
        allowance_amount_minor=10000,
        period="weekly",
        point_goal=100,
    )
    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc)

    calendar_start, calendar_end = calendar_service.get_week_bounds(date(2026, 5, 6), family.week_start_day)
    allowance_start, allowance_end, _, _ = allowance_service._period_bounds_for_setting(setting, family, now=now)

    assert calendar_start == date(2026, 5, 2)
    assert calendar_end == date(2026, 5, 8)
    assert allowance_start == date(2026, 5, 2)
    assert allowance_end == date(2026, 5, 9)

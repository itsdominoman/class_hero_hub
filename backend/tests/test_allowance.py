import os
from datetime import datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database, models
from app.database import Base, get_db
from app.main import app

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


def valid_payload(**overrides):
    payload = {
        "is_enabled": True,
        "currency": "OMR",
        "allowance_amount_minor": 10000,
        "period": "weekly",
        "point_goal": 100,
    }
    payload.update(overrides)
    return payload


def test_unauthenticated_access_blocked(db, client):
    family = create_family(db)
    child = create_child(db, family)

    response = client.get(f"/api/allowance/children/{child.id}/settings")

    assert response.status_code == 401


def test_parent_can_read_default_allowance_settings_for_child(db, client):
    family = create_family(db)
    parent = create_parent(db, family)
    child = create_child(db, family)
    authenticate(client, parent)

    response = client.get(f"/api/allowance/children/{child.id}/settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] is None
    assert payload["child_id"] == child.id
    assert payload["family_id"] == family.id
    assert payload["is_enabled"] is False
    assert payload["currency"] == "OMR"
    assert payload["currency_exponent"] == 3
    assert payload["allowance_amount_minor"] == 0
    assert payload["period"] == "weekly"
    assert payload["point_goal"] == 100


def test_parent_can_enable_save_and_update_allowance_settings(db, client):
    family = create_family(db)
    parent = create_parent(db, family)
    child = create_child(db, family)
    headers = authenticate(client, parent)

    create_response = client.put(
        f"/api/allowance/children/{child.id}/settings",
        headers=headers,
        json=valid_payload(currency="USD", allowance_amount_minor=2500, point_goal=50),
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["is_enabled"] is True
    assert created["currency"] == "USD"
    assert created["currency_exponent"] == 2
    assert created["allowance_amount_minor"] == 2500
    assert created["point_goal"] == 50
    assert created["allowance_enabled_at"] is not None
    assert created["created_by_parent_id"] == parent.id
    assert created["updated_by_parent_id"] == parent.id

    update_response = client.put(
        f"/api/allowance/children/{child.id}/settings",
        headers=headers,
        json=valid_payload(currency="GBP", allowance_amount_minor=5000, period="monthly", point_goal=200),
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == created["id"]
    assert updated["currency"] == "GBP"
    assert updated["currency_exponent"] == 2
    assert updated["period"] == "monthly"
    assert updated["point_goal"] == 200
    assert updated["allowance_enabled_at"] is not None


@pytest.mark.parametrize(
    "currency,exponent",
    [
        ("AED", 2),
        ("BDT", 2),
        ("JPY", 0),
        ("KWD", 3),
        ("OMR", 3),
        ("ZAR", 2),
    ],
)
def test_parent_can_save_global_allowance_currencies(db, client, currency, exponent):
    family = create_family(db)
    parent = create_parent(db, family)
    child = create_child(db, family)
    headers = authenticate(client, parent)

    response = client.put(
        f"/api/allowance/children/{child.id}/settings",
        headers=headers,
        json=valid_payload(currency=currency, allowance_amount_minor=1000),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["currency"] == currency
    assert payload["currency_exponent"] == exponent


def test_parent_can_disable_and_delete_allowance_settings(db, client):
    family = create_family(db)
    parent = create_parent(db, family)
    child = create_child(db, family)
    headers = authenticate(client, parent)

    disabled_response = client.put(
        f"/api/allowance/children/{child.id}/settings",
        headers=headers,
        json=valid_payload(is_enabled=False),
    )
    assert disabled_response.status_code == 200
    assert disabled_response.json()["is_enabled"] is False

    delete_response = client.delete(f"/api/allowance/children/{child.id}/settings", headers=headers)
    assert delete_response.status_code == 204

    default_response = client.get(f"/api/allowance/children/{child.id}/settings")
    assert default_response.status_code == 200
    assert default_response.json()["id"] is None
    assert default_response.json()["is_enabled"] is False


def test_disabling_allowance_preserves_enable_timestamp_for_history(db, client):
    family = create_family(db)
    parent = create_parent(db, family)
    child = create_child(db, family)
    headers = authenticate(client, parent)

    enabled_response = client.put(
        f"/api/allowance/children/{child.id}/settings",
        headers=headers,
        json=valid_payload(is_enabled=True),
    )
    assert enabled_response.status_code == 200
    enabled_payload = enabled_response.json()
    assert enabled_payload["allowance_enabled_at"] is not None

    disabled_response = client.put(
        f"/api/allowance/children/{child.id}/settings",
        headers=headers,
        json=valid_payload(is_enabled=False),
    )
    assert disabled_response.status_code == 200
    disabled_payload = disabled_response.json()
    assert disabled_payload["is_enabled"] is False
    assert disabled_payload["allowance_enabled_at"] is not None


def test_allowance_summary_uses_current_points_for_available_allowance_value(db, client):
    family = create_family(db, timezone="UTC", week_start_day=0)
    parent = create_parent(db, family)
    child = create_child(db, family)
    headers = authenticate(client, parent)

    response = client.put(
        f"/api/allowance/children/{child.id}/settings",
        headers=headers,
        json=valid_payload(period="monthly", point_goal=100, allowance_amount_minor=10000),
    )
    assert response.status_code == 200

    setting = db.query(models.ChildAllowanceSetting).filter_by(child_id=child.id).first()
    assert setting is not None
    now = datetime.utcnow().replace(microsecond=0)
    enabled_at = now - timedelta(days=2)
    setting.allowance_enabled_at = enabled_at
    db.commit()

    db.add_all([
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=80,
            description="Current period award",
            created_at=now,
            created_by_parent_id=parent.id,
        ),
    ])
    db.commit()

    summary_response = client.get(f"/api/allowance/children/{child.id}/summary", headers=headers)
    assert summary_response.status_code == 200
    payload = summary_response.json()

    assert payload["allowance_enabled_at"] is not None
    assert payload["available_points"] == 80
    assert payload["available_allowance_minor"] == 8000
    assert payload["earned_points_period"] == 80
    assert payload["earned_allowance_minor_period"] == 8000
    assert payload["carried_over_points"] == 0


def test_reward_hold_and_rejection_update_allowance_balance(db, client):
    family = create_family(db, timezone="UTC", week_start_day=0)
    parent = create_parent(db, family)
    child = create_child(db, family)
    headers = authenticate(client, parent)

    response = client.put(
        f"/api/allowance/children/{child.id}/settings",
        headers=headers,
        json=valid_payload(period="monthly", point_goal=100, allowance_amount_minor=10000),
    )
    assert response.status_code == 200

    setting = db.query(models.ChildAllowanceSetting).filter_by(child_id=child.id).first()
    assert setting is not None
    setting.allowance_enabled_at = datetime.utcnow().replace(microsecond=0) - timedelta(days=2)
    db.commit()

    db.add(
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=100,
            description="Allowance points",
            created_at=datetime.utcnow().replace(microsecond=0) - timedelta(days=1),
            created_by_parent_id=parent.id,
        )
    )
    db.commit()

    reward_request = client.post(
        f"/api/children/{child.id}/redemptions",
        headers=headers,
        json={"title": "Robux", "points": 30, "description": "Spend points"},
    )
    assert reward_request.status_code == 200

    summary_response = client.get(f"/api/allowance/children/{child.id}/summary", headers=headers)
    assert summary_response.status_code == 200
    payload = summary_response.json()
    assert payload["pending_points"] == 30
    assert payload["pending_allowance_minor"] == 3000
    assert payload["available_allowance_minor"] == 7000
    assert payload["earned_points_period"] == 100
    assert payload["earned_allowance_minor_period"] == 10000

    redemption_id = reward_request.json()["id"]
    reject_response = client.post(
        f"/api/redemptions/{redemption_id}/reject",
        headers=headers,
        json={"parent_note": "Not yet"},
    )
    assert reject_response.status_code == 200

    summary_response = client.get(f"/api/allowance/children/{child.id}/summary", headers=headers)
    assert summary_response.status_code == 200
    payload = summary_response.json()
    assert payload["pending_points"] == 0
    assert payload["available_allowance_minor"] == 10000
    assert payload["earned_points_period"] == 100
    assert payload["earned_allowance_minor_period"] == 10000


@pytest.mark.parametrize(
    "field,value",
    [
        ("currency", "ZZZ"),
        ("period", "daily"),
        ("point_goal", 0),
        ("allowance_amount_minor", -1),
    ],
)
def test_invalid_allowance_settings_rejected(db, client, field, value):
    family = create_family(db)
    parent = create_parent(db, family)
    child = create_child(db, family)
    headers = authenticate(client, parent)
    payload = valid_payload(**{field: value})

    response = client.put(f"/api/allowance/children/{child.id}/settings", headers=headers, json=payload)

    assert response.status_code == 422


def test_parent_cannot_access_other_family_child_allowance_settings(db, client):
    family = create_family(db)
    other_family = create_family(db)
    parent = create_parent(db, family)
    other_child = create_child(db, other_family)
    headers = authenticate(client, parent)

    get_response = client.get(f"/api/allowance/children/{other_child.id}/settings")
    put_response = client.put(
        f"/api/allowance/children/{other_child.id}/settings",
        headers=headers,
        json=valid_payload(),
    )
    preview_response = client.get(f"/api/allowance/children/{other_child.id}/preview")

    assert get_response.status_code == 404
    assert put_response.status_code == 404
    assert preview_response.status_code == 404


def test_preview_uses_period_ledger_and_excludes_rewards_and_savings(db, client):
    family = create_family(db, timezone="UTC", week_start_day=0)
    parent = create_parent(db, family)
    child = create_child(db, family)
    headers = authenticate(client, parent)

    settings_response = client.put(
        f"/api/allowance/children/{child.id}/settings",
        headers=headers,
        json=valid_payload(period="monthly", point_goal=200, allowance_amount_minor=10000),
    )
    assert settings_response.status_code == 200

    now = datetime.utcnow()
    db.add_all([
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=100,
            description="Award",
            created_at=now,
            created_by_parent_id=parent.id,
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.calendar_task,
            points=20,
            description="Calendar task",
            created_at=now,
            created_by_parent_id=parent.id,
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.penalty,
            points=-10,
            description="Penalty",
            created_at=now,
            created_by_parent_id=parent.id,
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.redemption_hold,
            points=-70,
            description="Reward hold excluded",
            created_at=now,
            created_by_parent_id=parent.id,
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.redemption_rejected,
            points=70,
            description="Reward release excluded",
            created_at=now,
            created_by_parent_id=parent.id,
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.savings_deposit,
            points=-30,
            description="Savings transfer excluded",
            created_at=now,
            created_by_parent_id=parent.id,
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.savings,
            transaction_type=models.TransactionType.savings_deposit,
            points=30,
            description="Savings transfer excluded",
            created_at=now,
            created_by_parent_id=parent.id,
        ),
    ])
    db.commit()

    response = client.get(f"/api/allowance/children/{child.id}/preview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["raw_eligible_points"] == 110
    assert payload["eligible_points"] == 110
    assert payload["point_goal"] == 200
    assert payload["earned_amount_minor"] == 5500
    assert payload["display_amount"] == "OMR ر.ع5.5"
    assert payload["display_max_amount"] == "OMR ر.ع10"
    assert payload["included_transaction_count"] == 3

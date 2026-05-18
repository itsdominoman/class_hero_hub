from __future__ import annotations

from urllib.parse import urlparse
import logging
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database, models
from app.services import calendar_service
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


def override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def configure_qa_child_login(
    monkeypatch,
    *,
    enabled: bool,
    runtime_environment: str,
    qa_child_token: str = "qa-child-token",
    qa_parent_token: str = "qa-parent-token",
    public_app_url: str = "http://127.0.0.1:5173",
    api_base_url: str = "http://127.0.0.1:8000",
):
    monkeypatch.setattr(database.settings, "QA_CHILD_LOGIN_ENABLED", enabled)
    monkeypatch.setattr(database.settings, "QA_LOGIN_ENABLED", enabled)
    monkeypatch.setattr(database.settings, "APP_ENV", runtime_environment)
    monkeypatch.setattr(database.settings, "ENVIRONMENT", runtime_environment)
    monkeypatch.setattr(database.settings, "QA_CHILD_LOGIN_TOKEN", qa_child_token)
    monkeypatch.setattr(database.settings, "QA_LOGIN_TOKEN", qa_parent_token)
    monkeypatch.setattr(database.settings, "PUBLIC_APP_URL", public_app_url)
    monkeypatch.setattr(database.settings, "API_BASE_URL", api_base_url)


def test_qa_child_login_disabled_by_default_returns_404(client, monkeypatch):
    configure_qa_child_login(monkeypatch, enabled=False, runtime_environment="development")

    response = client.post("/api/dev/qa-child-login", json={"token": "qa-child-token"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"


def test_qa_child_login_refuses_production_environment(client, monkeypatch):
    configure_qa_child_login(monkeypatch, enabled=True, runtime_environment="production")

    response = client.post("/api/dev/qa-child-login", json={"token": "qa-child-token"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"


@pytest.mark.parametrize(
    ("public_app_url", "api_base_url"),
    [
        ("https://familyherohub.com", "http://127.0.0.1:8000"),
        ("http://127.0.0.1:5173", "https://familyherohub.com"),
    ],
)
def test_qa_child_login_refuses_production_domains(client, monkeypatch, public_app_url, api_base_url):
    request_host = urlparse(public_app_url if "familyherohub.com" in public_app_url else api_base_url).hostname
    configure_qa_child_login(
        monkeypatch,
        enabled=True,
        runtime_environment="test",
        public_app_url=public_app_url,
        api_base_url=api_base_url,
    )

    response = client.post(
        "/api/dev/qa-child-login",
        headers={"Host": request_host or "familyherohub.com"},
        json={"token": "qa-child-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "QA child login refused"


def test_qa_child_login_rejects_missing_or_invalid_token(client, monkeypatch):
    configure_qa_child_login(monkeypatch, enabled=True, runtime_environment="development")

    missing_response = client.post("/api/dev/qa-child-login", json={})
    invalid_response = client.post("/api/dev/qa-child-login", json={"token": "wrong-token"})

    assert missing_response.status_code == 403
    assert missing_response.json()["detail"] == "QA child login refused"
    assert invalid_response.status_code == 403
    assert invalid_response.json()["detail"] == "QA child login refused"


def test_qa_child_login_seeds_a_deterministic_child_session(client, monkeypatch, caplog):
    configure_qa_child_login(monkeypatch, enabled=True, runtime_environment="development")

    with caplog.at_level(logging.INFO, logger="app.routes.dev"):
        response = client.post("/api/dev/qa-child-login", json={"token": "qa-child-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "ok",
        "parent_email": "qa-child-parent@dev.familyherohub.com",
        "family_id": 1,
        "child_id": 1,
        "child_name": "QA Seed Child",
        "child_route": "/child/1",
        "reused": False,
    }
    assert "QA child login issued for qa-child-parent@dev.familyherohub.com child=1" in caplog.text
    assert client.cookies.get("child_session")

    child_me = client.get("/api/child/me")
    assert child_me.status_code == 200
    assert child_me.json()["child"]["display_name"] == "QA Seed Child"
    assert child_me.json()["available_spending"] > 0

    rewards = client.get("/api/child/rewards")
    assert rewards.status_code == 200
    assert [reward["title"] for reward in rewards.json()] == [
        "QA Reward Short",
        "QA Reward Very Long Name Designed To Stress Mobile Card Wrapping",
        "QA Reward Long Description Stress Case",
        "QA Reward Bonus",
    ]

    allowance = client.get("/api/child/allowance")
    assert allowance.status_code == 200
    assert allowance.json()["settings"]["is_enabled"] is True
    assert allowance.json()["available_allowance_minor"] > 0

    redemptions = client.get("/api/child/redemptions")
    assert redemptions.status_code == 200
    assert [request["title"] for request in redemptions.json()] == [
        "QA Waiting Request",
        "QA Pending Request",
    ]

    ledger = client.get("/api/child/ledger")
    assert ledger.status_code == 200
    assert len(ledger.json()) == 9

    today = calendar_service.get_family_today("Europe/Berlin")
    calendar = client.get(
        f"/api/child/calendar?from_date={today.isoformat()}&to_date={today.isoformat()}"
    )
    assert calendar.status_code == 200
    assert {item["entry"]["title"] for item in calendar.json()} == {
        "QA Task Pack Bag",
        "QA Event Piano Lesson",
    }

    school_items = client.get("/api/child/school-items/today")
    assert school_items.status_code == 200
    assert [item["class_name"] for item in school_items.json()] == [
        "QA School Bag Pack"
    ]

    tomorrow_school_items = client.get("/api/child/school-items/today?offset=1")
    assert tomorrow_school_items.status_code == 200
    assert [item["class_name"] for item in tomorrow_school_items.json()] == [
        "QA School Bag Piano"
    ]

    db = TestingSessionLocal()
    try:
        assert db.query(models.ParentUser).filter_by(email="qa-child-parent@dev.familyherohub.com").count() == 1
        assert db.query(models.Family).count() == 1
        assert db.query(models.Child).count() == 1
        assert db.query(models.Reward).count() == 4
        assert db.query(models.CalendarEntry).count() == 2
        assert db.query(models.RedemptionRequest).count() == 2
        assert db.query(models.LedgerTransaction).count() == 9
        assert db.query(models.SchoolItem).count() == 2
        assert db.query(models.ChildAllowanceSetting).count() == 1
        assert db.query(models.PetProgress).count() == 1
        assert db.query(models.ChildDeviceSession).count() == 1
    finally:
        db.close()

    second_response = client.post("/api/dev/qa-child-login", json={"token": "qa-child-token"})
    assert second_response.status_code == 200
    assert second_response.json()["reused"] is True

    db = TestingSessionLocal()
    try:
        assert db.query(models.ParentUser).filter_by(email="qa-child-parent@dev.familyherohub.com").count() == 1
        assert db.query(models.Family).count() == 1
        assert db.query(models.Child).count() == 1
        assert db.query(models.Reward).count() == 4
        assert db.query(models.CalendarEntry).count() == 2
        assert db.query(models.RedemptionRequest).count() == 2
        assert db.query(models.LedgerTransaction).count() == 9
        assert db.query(models.SchoolItem).count() == 2
        assert db.query(models.ChildAllowanceSetting).count() == 1
        assert db.query(models.PetProgress).count() == 1
        assert db.query(models.ChildDeviceSession).count() == 1
    finally:
        db.close()

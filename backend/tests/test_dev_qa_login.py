import os
from urllib.parse import urlparse

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database, models
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


def configure_qa_login(
    monkeypatch,
    *,
    enabled: bool,
    runtime_environment: str,
    qa_token: str = "qa-token",
    public_app_url: str = "http://127.0.0.1:5173",
    api_base_url: str = "http://127.0.0.1:8000",
    qa_email: str = "qa-parent@dev.familyherohub.com",
    qa_name: str = "QA Parent",
):
    monkeypatch.setattr(database.settings, "QA_LOGIN_ENABLED", enabled)
    monkeypatch.setattr(database.settings, "APP_ENV", runtime_environment)
    monkeypatch.setattr(database.settings, "ENVIRONMENT", runtime_environment)
    monkeypatch.setattr(database.settings, "QA_LOGIN_TOKEN", qa_token)
    monkeypatch.setattr(database.settings, "QA_LOGIN_EMAIL", qa_email)
    monkeypatch.setattr(database.settings, "QA_LOGIN_NAME", qa_name)
    monkeypatch.setattr(database.settings, "PUBLIC_APP_URL", public_app_url)
    monkeypatch.setattr(database.settings, "API_BASE_URL", api_base_url)


def test_qa_login_disabled_by_default_returns_404(client, monkeypatch):
    configure_qa_login(monkeypatch, enabled=False, runtime_environment="development")

    response = client.post("/api/dev/qa-login", json={"token": "qa-token"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"


def test_qa_login_refuses_production_environment(client, monkeypatch):
    configure_qa_login(monkeypatch, enabled=True, runtime_environment="production")

    response = client.post("/api/dev/qa-login", json={"token": "qa-token"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"


@pytest.mark.parametrize(
    ("public_app_url", "api_base_url"),
    [
        ("https://familyherohub.com", "http://127.0.0.1:8000"),
        ("http://127.0.0.1:5173", "https://familyherohub.com"),
    ],
)
def test_qa_login_refuses_production_domains(client, monkeypatch, public_app_url, api_base_url):
    request_host = urlparse(public_app_url if "familyherohub.com" in public_app_url else api_base_url).hostname
    configure_qa_login(
        monkeypatch,
        enabled=True,
        runtime_environment="test",
        public_app_url=public_app_url,
        api_base_url=api_base_url,
    )

    response = client.post(
        "/api/dev/qa-login",
        headers={"Host": request_host or "familyherohub.com"},
        json={"token": "qa-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "QA login refused"


def test_qa_login_creates_reuses_qa_user_and_preserves_csrf(client, monkeypatch, caplog):
    configure_qa_login(monkeypatch, enabled=True, runtime_environment="development")

    with caplog.at_level(logging.INFO, logger="app.routes.dev"):
        response = client.post("/api/dev/qa-login", json={"token": "qa-token"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "email": "qa-parent@dev.familyherohub.com",
        "parent_id": 1,
        "family_id": 1,
        "reused": False,
    }
    assert "QA login issued for qa-parent@dev.familyherohub.com" in caplog.text
    assert client.cookies.get("access_token")
    assert client.cookies.get("csrf_token")

    me_response = client.get("/api/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "qa-parent@dev.familyherohub.com"

    second_response = client.post(
        "/api/dev/qa-login",
        headers={"X-CSRF-Token": client.cookies.get("csrf_token")},
        json={"token": "qa-token"},
    )
    assert second_response.status_code == 200
    assert second_response.json()["reused"] is True
    assert second_response.json()["parent_id"] == response.json()["parent_id"]
    assert second_response.json()["family_id"] == response.json()["family_id"]

    client.cookies.pop("csrf_token", None)
    logout_response = client.post("/api/auth/logout", json={})
    assert logout_response.status_code == 403
    assert logout_response.json()["detail"] == "Missing CSRF token"

    check_db = TestingSessionLocal()
    try:
        parent = check_db.query(models.ParentUser).filter_by(email="qa-parent@dev.familyherohub.com").one()
        assert parent.name == "QA Parent"
        assert parent.google_sub == "qa-login:qa-parent@dev.familyherohub.com"
        assert parent.family_id == 1
        assert parent.last_login_at is not None
    finally:
        check_db.close()

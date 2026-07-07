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

from app import database
from app.database import Base, get_db
from app.main import app
from app.models_school import PlatformAdmin, User
from app.routes import dev as dev_routes
from app.security import BoundedInMemoryRateLimiter

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
    qa_email: str = "qa-platform@dev.classherohub.com",
    qa_name: str = "QA Platform Admin",
):
    monkeypatch.setattr(database.settings, "QA_LOGIN_ENABLED", enabled)
    monkeypatch.setattr(database.settings, "APP_ENV", runtime_environment)
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


def test_qa_login_creates_reuses_user_platform_admin_and_preserves_csrf(client, monkeypatch, caplog):
    configure_qa_login(monkeypatch, enabled=True, runtime_environment="development")

    with caplog.at_level(logging.INFO, logger="app.routes.dev"):
        response = client.post("/api/dev/qa-login", json={"token": "qa-token"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "email": "qa-platform@dev.classherohub.com",
        "user_id": 1,
        "is_platform_admin": True,
        "reused": False,
    }
    assert "qa-token" not in caplog.text
    assert "QA login issued for qa-platform@dev.classherohub.com" in caplog.text
    assert client.cookies.get("access_token")
    assert client.cookies.get("csrf_token")

    me_response = client.get("/api/me")
    assert me_response.status_code == 200
    assert me_response.json()["user"]["email"] == "qa-platform@dev.classherohub.com"
    assert me_response.json()["is_platform_admin"] is True

    second_response = client.post(
        "/api/dev/qa-login",
        headers={"X-CSRF-Token": client.cookies.get("csrf_token")},
        json={"token": "qa-token"},
    )
    assert second_response.status_code == 200
    assert second_response.json()["reused"] is True
    assert second_response.json()["user_id"] == response.json()["user_id"]

    client.cookies.pop("csrf_token", None)
    logout_response = client.post("/api/auth/logout", json={})
    assert logout_response.status_code == 403
    assert logout_response.json()["detail"] == "Missing CSRF token"

    check_db = TestingSessionLocal()
    try:
        user = check_db.query(User).filter_by(email="qa-platform@dev.classherohub.com").one()
        assert user.name == "QA Platform Admin"
        assert user.google_sub == "qa-login:qa-platform@dev.classherohub.com"
        assert user.last_login_at is not None
        assert check_db.query(PlatformAdmin).filter_by(user_id=user.id).count() == 1
    finally:
        check_db.close()


def test_qa_login_ignores_spoofed_forwarded_host_and_proto(client, monkeypatch):
    configure_qa_login(monkeypatch, enabled=True, runtime_environment="development")

    response = client.post(
        "/api/dev/qa-login",
        headers={
            "Host": "localhost:8000",
            "Origin": "http://localhost:5173",
            "X-Forwarded-Host": "familyherohub.com",
            "X-Forwarded-Proto": "https",
        },
        json={"token": "qa-token"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_qa_login_rate_limit_uses_trusted_client_ip(client, monkeypatch):
    configure_qa_login(monkeypatch, enabled=True, runtime_environment="development")
    monkeypatch.setattr(dev_routes, "_qa_login_rate_limiter", BoundedInMemoryRateLimiter(60, 1))
    client_ips = iter(["203.0.113.20", "203.0.113.21"])
    monkeypatch.setattr(dev_routes, "get_client_ip_from_scope", lambda scope: next(client_ips))

    first_response = client.post("/api/dev/qa-login", json={"token": "qa-token"})
    second_response = client.post("/api/dev/qa-login", json={"token": "qa-token"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200

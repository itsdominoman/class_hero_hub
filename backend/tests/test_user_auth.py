import os
from datetime import timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database, invite_tokens
from app.database import Base, get_db
from app.main import app
from app.models_school import AuditLog, MagicLoginToken, Membership, PlatformAdmin, School, User
from app.routes import authentication as auth_routes
from app.school_scope import require_platform_admin, require_school_role
from app.security import BoundedInMemoryRateLimiter
from school_fixtures import seeded_schools  # noqa: F401


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


@pytest.fixture
def dependency_client():
    test_app = FastAPI()

    @test_app.get("/platform")
    def platform_route(current_user: User = Depends(require_platform_admin)):
        return {"user_id": current_user.id}

    @test_app.get("/schools/{school_id}/teacher")
    def teacher_route(membership: Membership = Depends(require_school_role("teacher"))):
        return {"membership_id": membership.id, "role": membership.role}

    @test_app.get("/school-header/teacher")
    def header_teacher_route(membership: Membership = Depends(require_school_role("teacher"))):
        return {"membership_id": membership.id, "school_id": membership.school_id}

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    test_app.dependency_overrides[get_db] = override_get_db
    return TestClient(test_app)


def authenticate(client: TestClient, email: str) -> None:
    client.cookies.set("access_token", auth.create_access_token({"sub": email}))


def test_google_callback_upserts_user(db, client, monkeypatch):
    async def fake_authorize_access_token(request):
        return {
            "userinfo": {
                "email": "oauth-user@example.com",
                "name": "OAuth User",
                "sub": "google-sub-oauth-user",
            }
        }

    monkeypatch.setattr(auth_routes.oauth.google, "authorize_access_token", fake_authorize_access_token)

    response = client.get("/api/auth/google/callback", follow_redirects=False)

    assert response.status_code == 302
    user = db.query(User).filter_by(email="oauth-user@example.com").one()
    assert user.google_sub == "google-sub-oauth-user"
    assert user.name == "OAuth User"
    assert user.last_login_at is not None


def magic_token_from_url(url: str) -> str:
    return url.split("token=", 1)[1]


def test_magic_link_request_and_exchange_create_normal_session(db, client, monkeypatch):
    sent = []
    monkeypatch.setattr(auth_routes, "MAGIC_REQUEST_RATE_LIMIT", BoundedInMemoryRateLimiter(60, 100))
    monkeypatch.setattr(auth_routes, "MAGIC_EXCHANGE_RATE_LIMIT", BoundedInMemoryRateLimiter(60, 100))
    monkeypatch.setattr("app.routes.authentication.send_magic_login", lambda email: sent.append(email))

    request_response = client.post(
        "/api/auth/magic-link/request",
        json={"email": "Magic-User@Example.COM", "returnTo": "/school"},
    )
    assert request_response.status_code == 200
    assert request_response.json()["status"] == "sent"
    assert sent[-1].to_email == "magic-user@example.com"

    token = magic_token_from_url(sent[-1].login_url)
    stored = db.query(MagicLoginToken).filter_by(email="magic-user@example.com").one()
    assert stored.token_hash == invite_tokens.hash_token(token)

    exchange = client.get(f"/api/auth/magic-link/exchange?token={token}", follow_redirects=False)
    assert exchange.status_code == 302
    assert exchange.headers["location"].endswith("/school")
    assert "access_token" in exchange.cookies

    user = db.query(User).filter_by(email="magic-user@example.com").one()
    assert user.last_login_at is not None


def test_magic_link_rejects_expiry_reuse_wrong_token_and_rate_limit(db, client, monkeypatch):
    sent = []
    monkeypatch.setattr(auth_routes, "MAGIC_REQUEST_RATE_LIMIT", BoundedInMemoryRateLimiter(60, 100))
    monkeypatch.setattr(auth_routes, "MAGIC_EXCHANGE_RATE_LIMIT", BoundedInMemoryRateLimiter(60, 100))
    monkeypatch.setattr("app.routes.authentication.send_magic_login", lambda email: sent.append(email))

    assert client.post("/api/auth/magic-link/request", json={"email": "reuse@example.com"}).status_code == 200
    token = magic_token_from_url(sent[-1].login_url)
    assert client.post("/api/auth/magic-link/exchange", json={"token": token}).status_code == 200
    client.cookies.clear()
    assert client.post("/api/auth/magic-link/exchange", json={"token": token}).status_code == 410
    assert client.post("/api/auth/magic-link/exchange", json={"token": "wrong-token"}).status_code == 401

    assert client.post("/api/auth/magic-link/request", json={"email": "expired@example.com"}).status_code == 200
    expired_token = magic_token_from_url(sent[-1].login_url)
    expired = db.query(MagicLoginToken).filter_by(email="expired@example.com").one()
    expired.expires_at = invite_tokens.now_utc() - timedelta(minutes=1)
    db.commit()
    assert client.post("/api/auth/magic-link/exchange", json={"token": expired_token}).status_code == 410

    monkeypatch.setattr(auth_routes, "MAGIC_REQUEST_RATE_LIMIT", BoundedInMemoryRateLimiter(60, 1))
    assert client.post("/api/auth/magic-link/request", json={"email": "limit1@example.com"}).status_code == 200
    assert client.post("/api/auth/magic-link/request", json={"email": "limit2@example.com"}).status_code == 429


def test_cookie_auth_resolves_user_for_me_v2(db, client, seeded_schools):
    alpha_teacher = seeded_schools["users"]["alpha_teacher"]
    authenticate(client, alpha_teacher.email)

    response = client.get("/api/me/v2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"] == {
        "id": alpha_teacher.id,
        "email": alpha_teacher.email,
        "name": alpha_teacher.name,
        "locale": "en",
    }
    assert payload["is_platform_admin"] is False
    assert payload["memberships"] == [
        {
            "school_id": seeded_schools["schools"]["alpha"].id,
            "school_name": "Alpha Academy",
            "role": "teacher",
        }
    ]


def test_api_me_serves_identity_v2_payload(db, client, seeded_schools):
    alpha_teacher = seeded_schools["users"]["alpha_teacher"]
    authenticate(client, alpha_teacher.email)

    response = client.get("/api/me")

    assert response.status_code == 200
    assert response.json()["user"]["email"] == alpha_teacher.email


def test_household_routes_do_not_resolve(client):
    assert client.get("/api/children").status_code == 404
    assert client.get("/api/family/settings").status_code == 404
    assert client.get("/api/allowance/children/1/settings").status_code == 404
    assert client.get("/api/school-items/configured").status_code == 404


def test_bootstrap_platform_admin_created_once(db, client, seeded_schools, monkeypatch):
    platform_user = seeded_schools["platform_user"]
    db.query(PlatformAdmin).delete()
    db.commit()
    monkeypatch.setattr(database.settings, "PLATFORM_ADMIN_EMAILS", platform_user.email)
    authenticate(client, platform_user.email)

    first_response = client.get("/api/me/v2")
    second_response = client.get("/api/me/v2")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["is_platform_admin"] is True
    assert second_response.json()["is_platform_admin"] is True
    assert db.query(PlatformAdmin).filter_by(user_id=platform_user.id).count() == 1
    assert db.query(AuditLog).filter_by(action="platform_admin.bootstrap").count() == 1


def test_require_platform_admin_rejects_normal_user(db, dependency_client, seeded_schools):
    authenticate(dependency_client, seeded_schools["users"]["alpha_teacher"].email)

    response = dependency_client.get("/platform")

    assert response.status_code == 403
    assert response.json()["detail"] == "Platform admin access required"


def test_require_school_role_allows_matching_active_membership(db, dependency_client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    alpha_teacher = seeded_schools["users"]["alpha_teacher"]
    authenticate(dependency_client, alpha_teacher.email)

    response = dependency_client.get(f"/schools/{alpha.id}/teacher")

    assert response.status_code == 200
    assert response.json()["role"] == "teacher"


def test_require_school_role_accepts_school_header(db, dependency_client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    alpha_teacher = seeded_schools["users"]["alpha_teacher"]
    authenticate(dependency_client, alpha_teacher.email)

    response = dependency_client.get(
        "/school-header/teacher",
        headers={"X-School-Id": str(alpha.id)},
    )

    assert response.status_code == 200
    assert response.json()["school_id"] == alpha.id


def test_require_school_role_rejects_inactive_membership(db, dependency_client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    alpha_teacher = seeded_schools["users"]["alpha_teacher"]
    membership = db.query(Membership).filter_by(
        school_id=alpha.id,
        user_id=alpha_teacher.id,
        role="teacher",
    ).one()
    membership.status = "revoked"
    db.commit()
    authenticate(dependency_client, alpha_teacher.email)

    response = dependency_client.get(f"/schools/{alpha.id}/teacher")

    assert response.status_code == 403
    assert response.json()["detail"] == "School role required"


def test_require_school_role_rejects_wrong_school(db, dependency_client, seeded_schools):
    beta = seeded_schools["schools"]["beta"]
    alpha_teacher = seeded_schools["users"]["alpha_teacher"]
    authenticate(dependency_client, alpha_teacher.email)

    response = dependency_client.get(f"/schools/{beta.id}/teacher")

    assert response.status_code == 403
    assert response.json()["detail"] == "School role required"


def test_require_school_role_rejects_suspended_school(db, dependency_client, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    alpha_teacher = seeded_schools["users"]["alpha_teacher"]
    alpha.status = "suspended"
    db.commit()
    authenticate(dependency_client, alpha_teacher.email)

    response = dependency_client.get(f"/schools/{alpha.id}/teacher")

    assert response.status_code == 403
    assert response.json()["detail"] == "This school account is currently suspended."

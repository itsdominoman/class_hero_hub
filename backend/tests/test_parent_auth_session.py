import os
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database, models
from app.database import Base, get_db
from app.main import app
from app.routes import authentication as auth_routes

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


def create_family(db):
    family = models.Family(timezone="Asia/Muscat", week_start_day=6)
    db.add(family)
    db.commit()
    db.refresh(family)
    return family


def create_parent(db, family, email="parent-session@example.com"):
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


def cookie_from_response(response, name: str) -> SimpleCookie:
    cookie = SimpleCookie()
    for header in response.headers.get_list("set-cookie"):
        if header.startswith(f"{name}="):
            cookie.load(header)
    assert name in cookie
    return cookie


def authenticate(client, parent):
    csrf_token = "test-csrf-token"
    client.cookies.set("access_token", auth.create_access_token({"sub": parent.email}))
    client.cookies.set("csrf_token", csrf_token)
    return {"X-CSRF-Token": csrf_token}


def test_create_access_token_expiry_uses_configured_minutes(monkeypatch):
    monkeypatch.setattr(database.settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 43200)
    before = datetime.now(timezone.utc)

    token = auth.create_access_token({"sub": "parent-session@example.com"})
    payload = jwt.decode(token, database.settings.SECRET_KEY, algorithms=[database.settings.ALGORITHM])
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

    assert before + timedelta(days=30) - timedelta(seconds=5) <= expires_at
    assert expires_at <= before + timedelta(days=30, seconds=5)


def test_google_callback_sets_parent_and_csrf_cookie_max_age_from_config(db, client, monkeypatch):
    monkeypatch.setattr(database.settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 43200)
    monkeypatch.setattr(database.settings, "PARENT_EMAILS", "oauth-parent@example.com")

    async def fake_authorize_access_token(request):
        return {
            "userinfo": {
                "email": "oauth-parent@example.com",
                "name": "OAuth Parent",
                "sub": "google-sub-oauth-parent",
            }
        }

    monkeypatch.setattr(auth_routes.oauth.google, "authorize_access_token", fake_authorize_access_token)

    response = client.get("/api/auth/google/callback", follow_redirects=False)

    assert response.status_code == 302
    access_cookie = cookie_from_response(response, "access_token")
    csrf_cookie = cookie_from_response(response, auth.CSRF_COOKIE_NAME)
    assert access_cookie["access_token"]["max-age"] == str(43200 * 60)
    assert csrf_cookie[auth.CSRF_COOKIE_NAME]["max-age"] == str(43200 * 60)
    assert access_cookie["access_token"]["httponly"] is True
    assert csrf_cookie[auth.CSRF_COOKIE_NAME]["httponly"] == ""


def test_logout_clears_access_and_csrf_cookies(db, client):
    family = create_family(db)
    parent = create_parent(db, family)
    headers = authenticate(client, parent)

    response = client.post("/api/auth/logout", headers=headers, json={})

    assert response.status_code == 200
    set_cookie = "\n".join(response.headers.get_list("set-cookie"))
    assert "access_token=\"\"" in set_cookie
    assert "csrf_token=\"\"" in set_cookie


def test_api_me_works_with_valid_access_cookie(db, client):
    family = create_family(db)
    parent = create_parent(db, family)
    authenticate(client, parent)

    response = client.get("/api/me")

    assert response.status_code == 200
    assert response.json()["email"] == parent.email


def test_expired_parent_jwt_is_rejected(db, client):
    family = create_family(db)
    parent = create_parent(db, family)
    expired_token = auth.create_access_token(
        {"sub": parent.email},
        expires_delta=timedelta(seconds=-1),
    )
    client.cookies.set("access_token", expired_token)

    response = client.get("/api/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


def test_parent_auth_accepts_authorization_bearer(db, client):
    family = create_family(db)
    parent = create_parent(db, family)
    token = auth.create_access_token({"sub": parent.email})

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == parent.email

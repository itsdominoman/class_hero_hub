import os
from datetime import timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database, invite_tokens
from app.database import Base, get_db
from app.main import app
from app.models_school import AuditLog, Membership, StaffInvite, User
from app.school_scope import require_school_role
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
def school_role_client():
    test_app = FastAPI()

    @test_app.get("/schools/{school_id}/admin-only")
    def admin_route(membership: Membership = Depends(require_school_role("school_admin"))):
        return {"membership_id": membership.id, "role": membership.role}

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    test_app.dependency_overrides[get_db] = override_get_db
    return TestClient(test_app)


def bearer(email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth.create_access_token({'sub': email})}"}


def create_user(db, email: str, name: str = "User") -> User:
    user = User(email=email, name=name, google_sub=f"sub-{email}")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def invite_token_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def create_platform_school(client, platform_user, sent_invites):
    response = client.post(
        "/api/platform/schools",
        headers=bearer(platform_user.email),
        json={
            "name": "Gamma School",
            "name_ar": "مدرسة جاما",
            "timezone": "Europe/Berlin",
            "locale_default": "en",
            "admin_email": "gamma-admin@example.com",
        },
    )
    assert response.status_code == 201
    assert sent_invites
    return response.json(), invite_token_from_url(sent_invites[-1].accept_url)


def test_platform_create_list_detail_suspend_reactivate_and_audit(db, client, seeded_schools, monkeypatch):
    sent_invites = []
    monkeypatch.setattr("app.routes.platform.send_staff_invite", lambda email: sent_invites.append(email))
    platform_user = seeded_schools["platform_user"]

    created, _token = create_platform_school(client, platform_user, sent_invites)

    assert created["name"] == "Gamma School"
    assert created["status"] == "pending_setup"
    assert created["counts"]["students"] == 0
    assert created["setup_flags"]["has_school_admin"] is False
    assert created["invites"][0]["email"] == "gamma-admin@example.com"
    assert sent_invites[-1].to_email == "gamma-admin@example.com"

    list_response = client.get("/api/platform/schools", headers=bearer(platform_user.email))
    assert list_response.status_code == 200
    assert any(school["id"] == created["id"] for school in list_response.json())

    detail_response = client.get(f"/api/platform/schools/{created['id']}", headers=bearer(platform_user.email))
    assert detail_response.status_code == 200
    assert detail_response.json()["invites"][0]["status"] == "pending"

    suspend_response = client.post(
        f"/api/platform/schools/{created['id']}/suspend",
        headers=bearer(platform_user.email),
        json={"reason": "Contract hold"},
    )
    assert suspend_response.status_code == 200
    assert suspend_response.json()["status"] == "suspended"
    assert suspend_response.json()["suspend_reason"] == "Contract hold"

    reactivate_response = client.post(
        f"/api/platform/schools/{created['id']}/reactivate",
        headers=bearer(platform_user.email),
        json={"reason": "Contract cleared"},
    )
    assert reactivate_response.status_code == 200
    assert reactivate_response.json()["status"] == "active"

    actions = {row.action for row in db.query(AuditLog).all()}
    assert {
        "platform.school.created",
        "platform.school.suspended",
        "platform.school.reactivated",
    }.issubset(actions)


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("post", "/api/platform/schools", {"name": "Denied", "admin_email": "x@example.com"}),
        ("get", "/api/platform/schools", None),
        ("get", "/api/platform/schools/1", None),
        ("post", "/api/platform/schools/1/suspend", {"reason": "No"}),
        ("post", "/api/platform/schools/1/reactivate", {"reason": "No"}),
        ("post", "/api/platform/schools/1/invites", {"email": "x@example.com"}),
        ("delete", "/api/platform/invites/1", None),
    ],
)
def test_non_platform_admin_forbidden_on_platform_routes(db, client, seeded_schools, method, path, json_body):
    alpha_admin = seeded_schools["users"]["alpha_admin"]

    kwargs = {"headers": bearer(alpha_admin.email)}
    if json_body is not None:
        kwargs["json"] = json_body
    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 403
    assert response.json()["detail"] == "Platform admin access required"


def test_staff_invite_lifecycle_exchange_expired_revoked_and_reused(db, client, seeded_schools, monkeypatch):
    sent_invites = []
    monkeypatch.setattr("app.routes.platform.send_staff_invite", lambda email: sent_invites.append(email))
    platform_user = seeded_schools["platform_user"]
    created, token = create_platform_school(client, platform_user, sent_invites)

    invited_user = create_user(db, "gamma-admin@example.com", "Gamma Admin")
    exchange_response = client.post(
        "/api/invites/exchange",
        headers=bearer(invited_user.email),
        json={"token": token},
    )
    assert exchange_response.status_code == 200
    assert exchange_response.json()["status"] == "accepted"
    assert exchange_response.json()["membership"]["role"] == "school_admin"

    membership = db.query(Membership).filter_by(
        school_id=created["id"],
        user_id=invited_user.id,
        role="school_admin",
    ).one()
    accepted_invite = db.query(StaffInvite).filter_by(id=created["invites"][0]["id"]).one()
    assert membership.status == "active"
    assert accepted_invite.accepted_by_user_id == invited_user.id

    reused_response = client.post(
        "/api/invites/exchange",
        headers=bearer(invited_user.email),
        json={"token": token},
    )
    assert reused_response.status_code == 410

    new_invite_response = client.post(
        f"/api/platform/schools/{created['id']}/invites",
        headers=bearer(platform_user.email),
        json={"email": "expired-admin@example.com"},
    )
    assert new_invite_response.status_code == 201
    expired_token = invite_token_from_url(sent_invites[-1].accept_url)
    expired_invite = db.query(StaffInvite).filter_by(id=new_invite_response.json()["id"]).one()
    expired_invite.expires_at = invite_tokens.now_utc() - timedelta(minutes=1)
    db.commit()
    expired_user = create_user(db, "expired-admin@example.com", "Expired Admin")
    expired_response = client.post(
        "/api/invites/exchange",
        headers=bearer(expired_user.email),
        json={"token": expired_token},
    )
    assert expired_response.status_code == 410

    revoked_invite_response = client.post(
        f"/api/platform/schools/{created['id']}/invites",
        headers=bearer(platform_user.email),
        json={"email": "revoked-admin@example.com"},
    )
    revoked_token = invite_token_from_url(sent_invites[-1].accept_url)
    delete_response = client.delete(
        f"/api/platform/invites/{revoked_invite_response.json()['id']}",
        headers=bearer(platform_user.email),
    )
    assert delete_response.status_code == 204
    revoked_user = create_user(db, "revoked-admin@example.com", "Revoked Admin")
    revoked_response = client.post(
        "/api/invites/exchange",
        headers=bearer(revoked_user.email),
        json={"token": revoked_token},
    )
    assert revoked_response.status_code == 410

    invalid_response = client.post(
        "/api/invites/exchange",
        headers=bearer(revoked_user.email),
        json={"token": "not-a-real-token"},
    )
    assert invalid_response.status_code == 401

    actions = {row.action for row in db.query(AuditLog).all()}
    assert {
        "platform.staff_invite.created",
        "platform.staff_invite.revoked",
        "staff_invite.accepted",
    }.issubset(actions)


def test_invite_exchange_requires_authenticated_user(client):
    response = client.post("/api/invites/exchange", json={"token": "anything"})

    assert response.status_code == 401


def test_suspension_blocks_school_admin_membership_end_to_end(
    db,
    client,
    school_role_client,
    seeded_schools,
    monkeypatch,
):
    sent_invites = []
    monkeypatch.setattr("app.routes.platform.send_staff_invite", lambda email: sent_invites.append(email))
    platform_user = seeded_schools["platform_user"]
    created, token = create_platform_school(client, platform_user, sent_invites)
    invited_user = create_user(db, "gamma-admin@example.com", "Gamma Admin")
    exchange_response = client.post(
        "/api/invites/exchange",
        headers=bearer(invited_user.email),
        json={"token": token},
    )
    assert exchange_response.status_code == 200

    allowed_response = school_role_client.get(
        f"/schools/{created['id']}/admin-only",
        headers=bearer(invited_user.email),
    )
    assert allowed_response.status_code == 200

    suspend_response = client.post(
        f"/api/platform/schools/{created['id']}/suspend",
        headers=bearer(platform_user.email),
        json={"reason": "Compliance hold"},
    )
    assert suspend_response.status_code == 200

    blocked_response = school_role_client.get(
        f"/schools/{created['id']}/admin-only",
        headers=bearer(invited_user.email),
    )
    assert blocked_response.status_code == 403
    assert blocked_response.json()["detail"] == "This school account is currently suspended."

import os
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("APP_ENV", "test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, child_auth, database, models
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


def create_parent(db, family, email, name, google_sub, status="active"):
    parent = models.ParentUser(
        email=email,
        name=name,
        google_sub=google_sub,
        family_id=family.id if family else None,
        status=status,
    )
    db.add(parent)
    db.commit()
    db.refresh(parent)
    return parent


def create_child(db, family, display_name="Kid"):
    child = models.Child(display_name=display_name, family_id=family.id)
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


def auth_cookie(email: str) -> str:
    return auth.create_access_token({"sub": email})


def override_admin(parent):
    app.dependency_overrides[auth.get_current_admin] = lambda: parent


def clear_admin_override():
    app.dependency_overrides.pop(auth.get_current_admin, None)


def test_admin_users_require_admin_auth(db, client):
    family = create_family(db)
    non_admin = create_parent(db, family, "member@example.com", "Member", "sub-member")

    app.dependency_overrides[auth.get_current_parent] = lambda: non_admin
    response = client.get("/api/admin/users")

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"
    app.dependency_overrides.pop(auth.get_current_parent, None)


def test_admin_users_support_pagination_and_search(db, client):
    family = create_family(db)
    admin = create_parent(db, family, "parent@example.com", "Admin", "sub-admin")

    alpha_family = create_family(db)
    alpha_parent = create_parent(db, alpha_family, "alpha@example.com", "Alpha Parent", "sub-alpha")
    models.ApprovedParentEmail(
        email="alpha@example.com",
        normalized_email="alpha@example.com",
        approved_by_parent_id=admin.id,
        source="registration_request",
        status="active",
    )
    db.commit()

    beta_approval = models.ApprovedParentEmail(
        email="beta@example.com",
        normalized_email="beta@example.com",
        approved_by_parent_id=admin.id,
        source="invite",
        status="active",
    )
    db.add(beta_approval)

    gamma_family = create_family(db)
    gamma_parent = create_parent(db, gamma_family, "gamma@example.com", "Gamma Parent", "sub-gamma")
    db.commit()

    request = models.RegistrationRequest(
        email="beta@example.com",
        normalized_email="beta@example.com",
        name="Beta Parent",
        family_name="Beta Family",
        message="Needs access for the Beta family",
        status="approved",
        approved_at=datetime.now(timezone.utc),
    )
    db.add(request)
    db.commit()

    override_admin(admin)

    response = client.get("/api/admin/users?page=1&page_size=1&sort_by=email&sort_dir=asc")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 3
    assert payload["page"] == 1
    assert payload["page_size"] == 1
    assert payload["total_pages"] >= 3
    assert len(payload["items"]) == 1

    response = client.get("/api/admin/users?search=Beta&status=active")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["normalized_email"] == "beta@example.com"
    assert payload["items"][0]["registration_request_family_name"] == "Beta Family"

    clear_admin_override()


def test_revoke_parent_blocks_login_and_restore_works(db, client):
    admin_family = create_family(db)
    admin = create_parent(db, admin_family, "parent@example.com", "Admin", "sub-admin")

    family = create_family(db)
    parent = create_parent(db, family, "revoke@example.com", "Target Parent", "sub-target")
    co_parent = create_parent(db, family, "coparent@example.com", "Co Parent", "sub-co")
    child = create_child(db, family)
    db.add(models.ApprovedParentEmail(
        email=parent.email,
        normalized_email=parent.email,
        approved_by_parent_id=admin.id,
        source="registration_request",
        status="active",
    ))
    db.commit()

    override_admin(admin)
    response = client.post(f"/api/admin/users/{quote(parent.email)}/revoke", json={"revoke_reason": "cleanup"})
    assert response.status_code == 200
    assert response.json()["user_status"] == "revoked"
    clear_admin_override()

    token = auth_cookie(parent.email)
    client.cookies.set("access_token", token)
    response = client.get("/api/me")
    assert response.status_code == 403
    assert "revoked" in response.json()["detail"].lower()

    client.cookies.clear()
    override_admin(admin)
    response = client.post(f"/api/admin/users/{quote(parent.email)}/restore")
    assert response.status_code == 200
    assert response.json()["user_status"] == "active"
    clear_admin_override()

    client.cookies.set("access_token", auth_cookie(parent.email))
    response = client.get("/api/me")
    assert response.status_code == 200
    assert response.json()["email"] == parent.email

    # unrelated child data remains intact
    assert db.query(models.Child).filter(models.Child.family_id == family.id).count() == 1


def test_revoked_approval_blocks_google_callback(db, client, monkeypatch):
    family = create_family(db)
    admin = create_parent(db, family, "parent@example.com", "Admin", "sub-admin")
    db.add(models.ApprovedParentEmail(
        email="blocked@example.com",
        normalized_email="blocked@example.com",
        approved_by_parent_id=admin.id,
        source="registration_request",
        status="revoked",
    ))
    db.commit()

    async def fake_authorize_access_token(request):
        return {
            "userinfo": {
                "email": "blocked@example.com",
                "name": "Blocked Parent",
                "sub": "google-sub-blocked",
            }
        }

    monkeypatch.setattr(auth_routes.oauth.google, "authorize_access_token", fake_authorize_access_token)

    response = client.get("/api/auth/google/callback", follow_redirects=False)
    assert response.status_code == 403
    assert "revoked" in response.json()["detail"].lower()


def test_only_active_parent_cannot_be_individually_revoked(db, client):
    admin_family = create_family(db)
    admin = create_parent(db, admin_family, "parent@example.com", "Admin", "sub-admin")

    family = create_family(db)
    parent = create_parent(db, family, "solo@example.com", "Solo Parent", "sub-solo")
    db.add(models.FamilyInvite(
        family_id=family.id,
        email=parent.email,
        role="parent",
        status="accepted",
        token_hash="solo-invite-token",
        invited_by_parent_id=admin.id,
        accepted_at=datetime.now(timezone.utc),
        accepted_by_parent_id=parent.id,
    ))
    db.add(models.ApprovedParentEmail(
        email=parent.email,
        normalized_email=parent.email,
        approved_by_parent_id=admin.id,
        source="registration_request",
        status="active",
    ))
    db.commit()

    override_admin(admin)
    response = client.get(f"/api/admin/users?search={quote(parent.email)}")
    assert response.status_code == 200
    payload = response.json()["items"]
    assert len(payload) == 1
    payload = payload[0]
    assert payload["can_revoke"] is False
    assert payload["can_revoke_reason"] == "only_active_parent"
    assert payload["coparents_count"] == 0

    response = client.post(f"/api/admin/users/{quote(parent.email)}/revoke", json={"revoke_reason": "should fail"})
    assert response.status_code == 400
    assert "only active parent" in response.json()["detail"].lower()

    response = client.post(f"/api/admin/families/{family.id}/suspend", json={"suspend_reason": "pause family"})
    assert response.status_code == 200
    assert response.json()["status"] == "suspended"
    clear_admin_override()


def test_bootstrap_admin_cannot_be_revoked(db, client):
    family = create_family(db)
    bootstrap = create_parent(db, family, "parent@example.com", "Bootstrap Admin", "sub-bootstrap")
    db.add(models.ApprovedParentEmail(
        email=bootstrap.email,
        normalized_email=bootstrap.email,
        approved_by_parent_id=bootstrap.id,
        source="bootstrap",
        status="active",
    ))
    db.commit()

    override_admin(bootstrap)
    response = client.post(f"/api/admin/users/{quote(bootstrap.email)}/revoke", json={"revoke_reason": "blocked"})
    assert response.status_code == 403
    assert "bootstrap admin" in response.json()["detail"].lower()
    clear_admin_override()


def test_coparent_revocation_and_family_suspend_restore(db, client):
    admin_family = create_family(db)
    admin = create_parent(db, admin_family, "parent@example.com", "Admin", "sub-admin")

    family = create_family(db)
    parent_one = create_parent(db, family, "one@example.com", "Parent One", "sub-one")
    parent_two = create_parent(db, family, "two@example.com", "Parent Two", "sub-two")
    child = create_child(db, family)

    reward = models.Reward(
        parent_id=parent_one.id,
        family_id=family.id,
        title="Movie Night",
        description="Family movie",
        points=10,
        is_active=True,
    )
    calendar_entry = models.CalendarEntry(
        family_id=family.id,
        child_id=child.id,
        created_by_parent_id=parent_one.id,
        title="Brush Teeth",
        entry_type="task",
        is_rewardable=True,
        points_value=5,
        start_date=date(2026, 5, 6),
        recurrence_type="none",
    )
    ledger_tx = models.LedgerTransaction(
        child_id=child.id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.award,
        points=15,
        description="Existing points",
        created_by_parent_id=parent_one.id,
    )
    db.add_all([
        reward,
        calendar_entry,
        ledger_tx,
        models.ApprovedParentEmail(
            email=parent_one.email,
            normalized_email=parent_one.email,
            approved_by_parent_id=admin.id,
            source="registration_request",
            status="active",
        ),
        models.ApprovedParentEmail(
            email=parent_two.email,
            normalized_email=parent_two.email,
            approved_by_parent_id=admin.id,
            source="registration_request",
            status="active",
        ),
    ])
    db.commit()

    before_counts = {
        "children": db.query(models.Child).count(),
        "rewards": db.query(models.Reward).count(),
        "calendar_entries": db.query(models.CalendarEntry).count(),
        "ledger_transactions": db.query(models.LedgerTransaction).count(),
    }

    override_admin(admin)
    response = client.post(f"/api/admin/users/{quote(parent_two.email)}/revoke", json={"revoke_reason": "coparent cleanup"})
    assert response.status_code == 200
    assert response.json()["user_status"] == "revoked"

    response = client.get(f"/api/admin/users?search={quote(parent_one.email)}")
    assert response.status_code == 200
    payload = response.json()["items"][0]
    assert payload["coparents_count"] == 0
    assert payload["can_revoke"] is False
    assert payload["can_revoke_reason"] == "only_active_parent"

    client.cookies.set("access_token", auth_cookie(parent_two.email))
    response = client.get("/api/me")
    assert response.status_code == 403
    client.cookies.set("access_token", auth_cookie(parent_one.email))
    response = client.get("/api/me")
    assert response.status_code == 200
    clear_admin_override()

    client.cookies.clear()
    override_admin(admin)
    response = client.post(f"/api/admin/families/{family.id}/suspend", json={"suspend_reason": "billing pause"})
    assert response.status_code == 200
    assert response.json()["status"] == "suspended"
    clear_admin_override()

    client.cookies.clear()
    client.cookies.set("child_session", "child-session-token")
    db.add(models.ChildDeviceSession(
        family_id=family.id,
        child_id=child.id,
        session_hash=child_auth.hash_token("child-session-token"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        last_seen_at=datetime.now(timezone.utc),
    ))
    db.commit()

    response = client.get("/api/child/me")
    assert response.status_code == 403
    assert "suspended" in response.json()["detail"].lower()

    client.cookies.clear()
    override_admin(admin)
    response = client.post(f"/api/admin/families/{family.id}/restore")
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    clear_admin_override()

    client.cookies.set("child_session", "child-session-token")
    response = client.get("/api/child/me")
    assert response.status_code == 200
    assert response.json()["child"]["display_name"] == child.display_name

    after_counts = {
        "children": db.query(models.Child).count(),
        "rewards": db.query(models.Reward).count(),
        "calendar_entries": db.query(models.CalendarEntry).count(),
        "ledger_transactions": db.query(models.LedgerTransaction).count(),
    }
    assert before_counts == after_counts


def test_orphaned_active_family_blocks_child_session_and_restore_parent_recovers(db, client):
    admin_family = create_family(db)
    admin = create_parent(db, admin_family, "parent@example.com", "Admin", "sub-admin")

    family = create_family(db)
    parent = create_parent(db, family, "orphan@example.com", "Orphan Parent", "sub-orphan", status="revoked")
    child = create_child(db, family)
    db.add(models.ApprovedParentEmail(
        email=parent.email,
        normalized_email=parent.email,
        approved_by_parent_id=admin.id,
        source="registration_request",
        status="active",
    ))
    session_token = "orphan-child-session"
    db.add(models.ChildDeviceSession(
        family_id=family.id,
        child_id=child.id,
        session_hash=child_auth.hash_token(session_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        last_seen_at=datetime.now(timezone.utc),
    ))
    db.commit()

    override_admin(admin)
    response = client.get(f"/api/admin/users?search={quote(parent.email)}")
    assert response.status_code == 200
    payload = response.json()["items"][0]
    assert payload["family_orphaned"] is True
    assert payload["family_status"] == "active"
    assert payload["can_revoke_reason"] == "already_revoked"
    clear_admin_override()

    client.cookies.set("child_session", session_token)
    response = client.get("/api/child/me")
    assert response.status_code == 403
    assert "no active parent" in response.json()["detail"].lower()

    client.cookies.clear()
    override_admin(admin)
    response = client.post(f"/api/admin/users/{quote(parent.email)}/restore")
    assert response.status_code == 200
    assert response.json()["user_status"] == "active"
    clear_admin_override()

    client.cookies.set("child_session", session_token)
    response = client.get("/api/child/me")
    assert response.status_code == 200
    assert response.json()["child"]["display_name"] == child.display_name

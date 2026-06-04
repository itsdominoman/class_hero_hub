import hashlib
import os
from datetime import datetime, timedelta, timezone

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


def create_family(db):
    family = models.Family(timezone="Asia/Muscat", week_start_day=6)
    db.add(family)
    db.commit()
    db.refresh(family)
    return family


def create_parent(db, family, email, name="Parent", status="active"):
    parent = models.ParentUser(
        email=email,
        name=name,
        google_sub=f"sub-{email}",
        family_id=family.id,
        status=status,
    )
    db.add(parent)
    db.commit()
    db.refresh(parent)
    return parent


def create_child(db, family):
    child = models.Child(display_name="Kid", family_id=family.id, active=True)
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


def authenticate(client, parent):
    csrf_token = "test-csrf-token"
    client.cookies.clear()
    client.cookies.set("access_token", auth.create_access_token({"sub": parent.email}))
    client.cookies.set("csrf_token", csrf_token)
    return {"X-CSRF-Token": csrf_token}


def create_invite(db, family, inviter, email="caregiver@example.com", token="invite-token"):
    invite = models.FamilyInvite(
        family_id=family.id,
        email=email,
        invited_by_parent_id=inviter.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite, token


def test_parent_can_list_family_grownups(db, client):
    family = create_family(db)
    owner = create_parent(db, family, "owner@example.com", "Owner")
    caregiver = create_parent(db, family, "caregiver@example.com", "Caregiver")
    authenticate(client, owner)

    response = client.get("/api/family/grownups")

    assert response.status_code == 200
    payload = response.json()
    assert [member["email"] for member in payload] == [owner.email, caregiver.email]
    assert payload[0]["can_remove"] is False
    assert payload[1]["can_remove"] is True


def test_parent_can_remove_another_caregiver_in_same_family(db, client):
    family = create_family(db)
    owner = create_parent(db, family, "owner@example.com")
    caregiver = create_parent(db, family, "caregiver@example.com")
    headers = authenticate(client, owner)

    response = client.delete(f"/api/family/grownups/{caregiver.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == caregiver.id
    assert response.json()["status"] == "revoked"
    db.refresh(caregiver)
    assert caregiver.status == "revoked"
    assert caregiver.revoked_at is not None
    assert caregiver.revoked_by_parent_id == owner.id
    assert caregiver.revoke_reason == "Removed from family"


def test_removed_caregiver_can_no_longer_access_family_data(db, client):
    family = create_family(db)
    owner = create_parent(db, family, "owner@example.com")
    caregiver = create_parent(db, family, "caregiver@example.com")
    create_child(db, family)

    authenticate(client, caregiver)
    before = client.get("/api/children/")
    assert before.status_code == 200

    headers = authenticate(client, owner)
    remove_response = client.delete(f"/api/family/grownups/{caregiver.id}", headers=headers)
    assert remove_response.status_code == 200

    authenticate(client, caregiver)
    after = client.get("/api/children/")
    assert after.status_code == 403
    assert after.json()["detail"] == "This account has been revoked"


def test_cannot_remove_grownup_from_another_family(db, client):
    family_one = create_family(db)
    family_two = create_family(db)
    owner = create_parent(db, family_one, "owner@example.com")
    other_parent = create_parent(db, family_two, "other@example.com")
    headers = authenticate(client, owner)

    response = client.delete(f"/api/family/grownups/{other_parent.id}", headers=headers)

    assert response.status_code == 404
    db.refresh(other_parent)
    assert other_parent.status == "active"


def test_cannot_remove_last_remaining_grownup(db, client):
    family = create_family(db)
    owner = create_parent(db, family, "owner@example.com")
    headers = authenticate(client, owner)

    response = client.delete(f"/api/family/grownups/{owner.id}", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot remove the only active grownup"
    db.refresh(owner)
    assert owner.status == "active"


def test_cannot_remove_self_when_another_grownup_exists(db, client):
    family = create_family(db)
    owner = create_parent(db, family, "owner@example.com")
    create_parent(db, family, "caregiver@example.com")
    headers = authenticate(client, owner)

    response = client.delete(f"/api/family/grownups/{owner.id}", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "You cannot remove yourself"


def test_non_owner_caregiver_cannot_remove_grownup(db, client):
    family = create_family(db)
    owner = create_parent(db, family, "owner@example.com")
    caregiver = create_parent(db, family, "caregiver@example.com")
    headers = authenticate(client, caregiver)

    response = client.delete(f"/api/family/grownups/{owner.id}", headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Only the family owner can remove grownups"


def test_unauthenticated_users_cannot_remove_grownups(db, client):
    family = create_family(db)
    owner = create_parent(db, family, "owner@example.com")

    response = client.delete(f"/api/family/grownups/{owner.id}")

    assert response.status_code == 401


def test_pending_invite_can_be_cancelled_with_delete_alias(db, client):
    family = create_family(db)
    owner = create_parent(db, family, "owner@example.com")
    invite, _ = create_invite(db, family, owner)
    headers = authenticate(client, owner)

    response = client.delete(f"/api/family/invites/{invite.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "revoked"
    db.refresh(invite)
    assert invite.status == "revoked"
    assert invite.revoked_at is not None


def test_cancelled_invite_cannot_be_accepted(db, client):
    family = create_family(db)
    owner = create_parent(db, family, "owner@example.com")
    invite, token = create_invite(db, family, owner)
    headers = authenticate(client, owner)

    cancel_response = client.delete(f"/api/family/invites/{invite.id}", headers=headers)
    assert cancel_response.status_code == 200

    verify_response = client.get(f"/api/auth/invite/verify/{token}")

    assert verify_response.status_code == 404
    assert verify_response.json()["detail"] == "Invite not found or already used"

import json
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, child_auth, database, models
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


def create_parent(db, family, email):
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


def create_child(db, family, display_name="Kid"):
    child = models.Child(display_name=display_name, family_id=family.id, active=True)
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


def create_child_session(db, child, parent):
    _, invite_token = child_auth.issue_child_device_invite(db, child, child.family_id, parent.id)
    _, session, session_token = child_auth.exchange_child_link(db, invite_token)
    return session, session_token


def authenticate(client, parent):
    csrf_token = "test-csrf-token"
    client.cookies.set("access_token", auth.create_access_token({"sub": parent.email}))
    client.cookies.set("csrf_token", csrf_token)
    return {"X-CSRF-Token": csrf_token}


def test_parent_can_list_linked_devices_for_own_child(db, client):
    family = create_family(db)
    parent = create_parent(db, family, "parent-devices@example.com")
    child = create_child(db, family)
    session, _ = create_child_session(db, child, parent)
    authenticate(client, parent)

    response = client.get(f"/api/children/{child.id}/devices")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": session.id,
            "child_id": child.id,
            "created_at": session.created_at.isoformat().replace("+00:00", "Z"),
            "expires_at": session.expires_at.isoformat().replace("+00:00", "Z"),
            "revoked_at": None,
            "last_seen_at": session.last_seen_at.isoformat().replace("+00:00", "Z"),
            "is_active": True,
            "label": "Linked device",
        }
    ]


def test_parent_cannot_list_devices_for_another_familys_child(db, client):
    family_one = create_family(db)
    family_two = create_family(db)
    parent_one = create_parent(db, family_one, "parent-one@example.com")
    parent_two = create_parent(db, family_two, "parent-two@example.com")
    child_two = create_child(db, family_two)
    create_child_session(db, child_two, parent_two)
    authenticate(client, parent_one)

    response = client.get(f"/api/children/{child_two.id}/devices")

    assert response.status_code == 404
    assert response.json()["detail"] == "Child not found"


def test_parent_can_unlink_one_child_device(db, client):
    family = create_family(db)
    parent = create_parent(db, family, "unlink-parent@example.com")
    child = create_child(db, family)
    session, _ = create_child_session(db, child, parent)
    headers = authenticate(client, parent)

    response = client.delete(f"/api/children/{child.id}/devices/{session.id}", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"id": session.id, "child_id": child.id, "revoked": True}

    db.expire_all()
    revoked_session = db.query(models.ChildDeviceSession).filter_by(id=session.id).one()
    assert revoked_session.revoked_at is not None

    second_response = client.delete(f"/api/children/{child.id}/devices/{session.id}", headers=headers)
    assert second_response.status_code == 200
    assert second_response.json() == {"id": session.id, "child_id": child.id, "revoked": True}


def test_unlinked_child_device_session_no_longer_works(db, client):
    family = create_family(db)
    parent = create_parent(db, family, "session-revoke-parent@example.com")
    child = create_child(db, family)
    session, session_token = create_child_session(db, child, parent)
    headers = authenticate(client, parent)

    response = client.delete(f"/api/children/{child.id}/devices/{session.id}", headers=headers)

    assert response.status_code == 200
    db.expire_all()
    with pytest.raises(HTTPException) as exc:
        child_auth.resolve_child_session(db, session_token)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid child session"


def test_unlinking_one_device_does_not_revoke_other_child_devices(db, client):
    family = create_family(db)
    parent = create_parent(db, family, "multi-device-parent@example.com")
    child = create_child(db, family)
    first_session, first_token = create_child_session(db, child, parent)
    second_session, second_token = create_child_session(db, child, parent)
    headers = authenticate(client, parent)

    response = client.delete(f"/api/children/{child.id}/devices/{first_session.id}", headers=headers)

    assert response.status_code == 200
    db.expire_all()
    first = db.query(models.ChildDeviceSession).filter_by(id=first_session.id).one()
    second = db.query(models.ChildDeviceSession).filter_by(id=second_session.id).one()
    assert first.revoked_at is not None
    assert second.revoked_at is None

    with pytest.raises(HTTPException):
        child_auth.resolve_child_session(db, first_token)
    assert child_auth.resolve_child_session(db, second_token).session.id == second_session.id

    list_response = client.get(f"/api/children/{child.id}/devices")
    assert list_response.status_code == 200
    assert [device["id"] for device in list_response.json()] == [second_session.id]


def test_unauthenticated_user_cannot_list_devices(db, client):
    family = create_family(db)
    parent = create_parent(db, family, "unauth-list-parent@example.com")
    child = create_child(db, family)
    create_child_session(db, child, parent)

    response = client.get(f"/api/children/{child.id}/devices")

    assert response.status_code == 401


def test_unauthenticated_user_cannot_unlink_devices(db, client):
    family = create_family(db)
    parent = create_parent(db, family, "unauth-delete-parent@example.com")
    child = create_child(db, family)
    session, _ = create_child_session(db, child, parent)

    response = client.delete(f"/api/children/{child.id}/devices/{session.id}")

    assert response.status_code == 401
    db.expire_all()
    stored_session = db.query(models.ChildDeviceSession).filter_by(id=session.id).one()
    assert stored_session.revoked_at is None


def test_device_api_does_not_expose_hashes_or_raw_tokens(db, client):
    family = create_family(db)
    parent = create_parent(db, family, "safe-device-parent@example.com")
    child = create_child(db, family)
    session, session_token = create_child_session(db, child, parent)
    invite = db.query(models.ChildDeviceInvite).filter_by(id=session.invite_id).one()
    authenticate(client, parent)

    response = client.get(f"/api/children/{child.id}/devices")

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert "session_hash" not in payload[0]
    assert "token_hash" not in payload[0]
    assert "invite_token" not in payload[0]
    assert "session_token" not in payload[0]

    serialized = json.dumps(payload)
    assert session.session_hash not in serialized
    assert invite.token_hash not in serialized
    assert session_token not in serialized

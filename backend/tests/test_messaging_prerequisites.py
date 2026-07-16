import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database, invite_tokens
from app.database import Base, get_db
from app.main import app
from app.models_school import (
    AuditLog,
    FhhLink,
    FhhLinkInvite,
    FhhMessagingIdentity,
    FhhMessagingIdentityLink,
    FhhMessagingLifecycleEvent,
    Membership,
    School,
    SchoolMessagingPolicy,
    Student,
    User,
)
from app.routes import integrations_fhh


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)


@pytest.fixture
def db(monkeypatch):
    database.engine = engine
    database.SessionLocal = Session
    monkeypatch.setattr(database.settings, "FHH_INTEGRATION_ENABLED", True)
    monkeypatch.setattr(database.settings, "FHH_INTEGRATION_SERVICE_TOKEN", "s" * 40)
    monkeypatch.setattr(database.settings, "FHH_INTEGRATION_ALLOWED_IPS", "")
    monkeypatch.setattr(database.settings, "MESSAGING_ENABLED", False)
    integrations_fhh.AUTH_LIMITER._attempts.clear()
    integrations_fhh.LINK_LIMITER._attempts.clear()
    Base.metadata.create_all(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    def override():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app, client=("127.0.0.1", 50000))
    app.dependency_overrides.clear()


def _admin_headers(user: User, school: School) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {auth.create_access_token({'sub': user.email})}",
        "X-School-Id": str(school.id),
    }


def _service_headers(link_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {'s' * 40}",
        "X-FHH-Link-Token": link_token,
    }


def _school_world(db):
    admin_one = User(email="admin-one@test", name="Admin One", google_sub="admin-one")
    admin_two = User(email="admin-two@test", name="Admin Two", google_sub="admin-two")
    school_one = School(name="One", slug="one", status="active")
    school_two = School(name="Two", slug="two", status="active")
    db.add_all([admin_one, admin_two, school_one, school_two])
    db.flush()
    membership_one = Membership(school_id=school_one.id, user_id=admin_one.id, role="school_admin", status="active")
    membership_two = Membership(school_id=school_two.id, user_id=admin_two.id, role="school_admin", status="active")
    student_one = Student(school_id=school_one.id, first_name="One", last_name="Student", status="active")
    student_two = Student(school_id=school_two.id, first_name="Two", last_name="Student", status="active")
    db.add_all([membership_one, membership_two, student_one, student_two])
    db.flush()

    links = []
    raw_tokens = []
    for school, student, admin, suffix in (
        (school_one, student_one, admin_one, "one"),
        (school_two, student_two, admin_two, "two"),
    ):
        invite = FhhLinkInvite(
            school_id=school.id,
            student_id=student.id,
            token_hash=f"invite-{suffix}",
            display_code_last4=suffix[-4:],
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            consumed_at=datetime.now(timezone.utc),
            consumed_by=f"fhh-child-{suffix}",
            created_by_user_id=admin.id,
        )
        db.add(invite)
        db.flush()
        raw_token = f"raw-link-token-{suffix}"
        link = FhhLink(
            school_id=school.id,
            student_id=student.id,
            source_invite_id=invite.id,
            link_token_hash=invite_tokens.hash_token(raw_token),
            fhh_child_ref=f"fhh-child-{suffix}",
        )
        db.add(link)
        db.flush()
        links.append(link)
        raw_tokens.append(raw_token)
    db.commit()
    return locals()


def _policy_update(version: int, *, enabled: bool = True) -> dict:
    return {
        "expected_policy_version": version,
        "enabled": enabled,
        "guardian_replies_enabled": True,
        "delivery_receipts_visible": True,
        "read_receipts_visible": False,
        "allow_staff_out_of_hours_opt_in": False,
        "teachers_may_mark_urgent": False,
        "notification_preview_mode": "generic",
        "retention_days": 2557,
        "email_mode": "off",
    }


def test_messaging_is_globally_and_per_school_disabled_by_default(db, client):
    world = _school_world(db)
    assert database.Settings(APP_ENV="test", _env_file=None).MESSAGING_ENABLED is False
    response = client.get(
        "/api/school/messaging-policy",
        headers=_admin_headers(world["admin_one"], world["school_one"]),
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["global_enabled"] is False
    assert response.json()["effective_enabled"] is False


def test_policy_update_is_school_scoped_versioned_and_audited(db, client):
    world = _school_world(db)
    one_headers = _admin_headers(world["admin_one"], world["school_one"])
    two_headers = _admin_headers(world["admin_two"], world["school_two"])
    assert client.get("/api/school/messaging-policy", headers=one_headers).status_code == 200
    updated = client.put("/api/school/messaging-policy", headers=one_headers, json=_policy_update(1))
    assert updated.status_code == 200
    assert updated.json()["policy_version"] == 2
    assert updated.json()["enabled"] is True
    assert updated.json()["effective_enabled"] is False
    other = client.get("/api/school/messaging-policy", headers=two_headers)
    assert other.status_code == 200 and other.json()["enabled"] is False
    assert (
        db.query(SchoolMessagingPolicy)
        .filter(SchoolMessagingPolicy.school_id == world["school_one"].id)
        .one()
        .updated_by_membership_id
        == world["membership_one"].id
    )
    audit = db.query(AuditLog).filter(AuditLog.action == "messaging.policy.updated").one()
    assert audit.school_id == world["school_one"].id
    assert audit.actor_user_id == world["admin_one"].id
    conflict = client.put("/api/school/messaging-policy", headers=one_headers, json=_policy_update(1, enabled=False))
    assert conflict.status_code == 409


def test_lifecycle_delivery_is_idempotent_private_and_cross_link_safe(db, client):
    world = _school_world(db)
    link_one, link_two = world["links"]
    token_one, token_two = world["raw_tokens"]
    event_id = uuid4()
    subject_ref = uuid4()
    body = {
        "event_id": str(event_id),
        "action": "parent_granted",
        "external_subject_ref": str(subject_ref),
        "display_name": "Verified Parent",
        "preferred_locale": "ar",
        "sync_version": 1,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    url = f"/api/integrations/fhh/links/{link_one.id}/messaging-lifecycle"
    first = client.post(url, headers=_service_headers(token_one), json=body)
    assert first.status_code == 200 and first.json()["duplicate"] is False
    duplicate = client.post(url, headers=_service_headers(token_one), json=body)
    assert duplicate.status_code == 200 and duplicate.json()["duplicate"] is True
    assert db.query(FhhMessagingIdentity).count() == 1
    assert db.query(FhhMessagingIdentityLink).count() == 1
    assert db.query(FhhMessagingLifecycleEvent).count() == 1

    wrong_token = client.post(url, headers=_service_headers(token_two), json={**body, "event_id": str(uuid4())})
    assert wrong_token.status_code == 404
    reused_elsewhere = client.post(
        f"/api/integrations/fhh/links/{link_two.id}/messaging-lifecycle",
        headers=_service_headers(token_two),
        json=body,
    )
    assert reused_elsewhere.status_code == 409
    forbidden = client.post(
        url,
        headers=_service_headers(token_one),
        json={**body, "event_id": str(uuid4()), "family_id": 99, "email": "leak@test"},
    )
    assert forbidden.status_code == 422
    assert "family" not in first.text.lower()
    assert "email" not in first.text.lower()


def test_revoked_link_cleanup_is_repeat_safe_and_cannot_be_regranted(db, client):
    world = _school_world(db)
    link = world["links"][0]
    token = world["raw_tokens"][0]
    grant = {
        "event_id": str(uuid4()),
        "action": "parent_granted",
        "external_subject_ref": str(uuid4()),
        "display_name": "Parent",
        "preferred_locale": "en",
        "sync_version": 1,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    url = f"/api/integrations/fhh/links/{link.id}/messaging-lifecycle"
    assert client.post(url, headers=_service_headers(token), json=grant).status_code == 200
    revoke = {
        "event_id": str(uuid4()),
        "action": "link_revoked",
        "sync_version": 2,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    assert client.post(url, headers=_service_headers(token), json=revoke).status_code == 200
    assert client.post(url, headers=_service_headers(token), json=revoke).json()["duplicate"] is True
    db.refresh(link)
    assert link.status == "revoked"
    assert db.query(FhhMessagingIdentityLink).one().status == "revoked"
    regrant = {**grant, "event_id": str(uuid4()), "sync_version": 3}
    assert client.post(url, headers=_service_headers(token), json=regrant).status_code == 410

import os
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database
from app.database import Base, get_db
from app.entitlement_service import (
    BEHAVIOUR_POINTS,
    POSITIVE_RECOGNITION,
    REPORTS_INSIGHTS,
    SCHOOL_CHATS,
    VOICE_NOTES,
    enabled_capabilities,
)
from app.feature_control_service import VOICE_NOTES_DISCLOSURE_VERSION
from app.main import app
from app.models_school import (
    AuditLog,
    Membership,
    PlatformAdmin,
    SchoolEntitlement,
    SchoolEntitlementEvent,
    SchoolFeatureControl,
    SchoolMessagingPolicy,
)
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


def bearer(email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth.create_access_token({'sub': email})}"}


def school_headers(user, school) -> dict[str, str]:
    return {**bearer(user.email), "X-School-Id": str(school.id)}


def test_effective_dates_and_dependencies_remove_incomplete_child_grants(db, seeded_schools):
    school = seeded_schools["schools"]["alpha"]
    today = date.today()
    behaviour = db.query(SchoolEntitlement).filter_by(
        school_id=school.id,
        capability=BEHAVIOUR_POINTS,
    ).one()
    recognition = db.query(SchoolEntitlement).filter_by(
        school_id=school.id,
        capability=POSITIVE_RECOGNITION,
    ).one()

    behaviour.effective_from = today + timedelta(days=1)
    recognition.effective_from = today - timedelta(days=1)
    db.commit()

    effective = enabled_capabilities(db, school.id, on_date=today)
    assert BEHAVIOUR_POINTS not in effective
    assert POSITIVE_RECOGNITION not in effective

    behaviour.effective_from = today - timedelta(days=2)
    behaviour.expires_on = today - timedelta(days=1)
    db.commit()
    assert BEHAVIOUR_POINTS not in enabled_capabilities(db, school.id, on_date=today)


def test_only_explicit_platform_authority_can_read_or_change_entitlements(db, client, seeded_schools):
    platform_user = seeded_schools["platform_user"]
    school = seeded_schools["schools"]["alpha"]
    path = f"/api/platform/schools/{school.id}/entitlements"

    denied = client.get(path, headers=bearer(platform_user.email))
    assert denied.status_code == 403

    authority = db.query(PlatformAdmin).filter_by(user_id=platform_user.id).one()
    authority.manage_school_entitlements = True
    db.commit()

    allowed = client.get(path, headers=bearer(platform_user.email))
    assert allowed.status_code == 200
    assert len(allowed.json()["entitlements"]) == 14
    assert allowed.json()["foundation"]


def test_school_admin_view_is_read_only_and_contains_no_internal_note(db, client, seeded_schools):
    school = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    headers = school_headers(admin, school)

    response = client.get("/api/school/entitlements", headers=headers)
    assert response.status_code == 200
    assert all("internal_note" not in row and "last_actor" not in row for row in response.json()["entitlements"])
    assert client.put(
        f"/api/school/entitlements/{REPORTS_INSIGHTS}",
        headers=headers,
        json={},
    ).status_code == 404


def test_update_is_versioned_append_only_audited_and_dependency_safe(db, client, seeded_schools):
    platform_user = seeded_schools["platform_user"]
    school = seeded_schools["schools"]["alpha"]
    authority = db.query(PlatformAdmin).filter_by(user_id=platform_user.id).one()
    authority.manage_school_entitlements = True
    db.commit()
    headers = bearer(platform_user.email)
    behaviour = db.query(SchoolEntitlement).filter_by(
        school_id=school.id,
        capability=BEHAVIOUR_POINTS,
    ).one()
    path = f"/api/platform/schools/{school.id}/entitlements/{BEHAVIOUR_POINTS}"
    payload = {
        "enabled": False,
        "source": "pilot",
        "effective_from": date.today().isoformat(),
        "expires_on": None,
        "internal_note": "Commercial grant changed after pilot review",
        "expected_entitlement_version": behaviour.entitlement_version,
    }

    blocked = client.put(path, headers=headers, json=payload)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "entitlement_dependency_required"

    recognition = db.query(SchoolEntitlement).filter_by(
        school_id=school.id,
        capability=POSITIVE_RECOGNITION,
    ).one()
    recognition.enabled = False
    db.commit()
    updated = client.put(path, headers=headers, json=payload)
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False
    assert updated.json()["entitlement_version"] == 2
    assert db.query(SchoolEntitlementEvent).filter_by(
        school_id=school.id,
        capability=BEHAVIOUR_POINTS,
        action="disabled",
    ).count() == 1
    assert db.query(AuditLog).filter_by(
        school_id=school.id,
        action="platform.school_entitlement.changed",
    ).count() == 1

    stale = client.put(path, headers=headers, json=payload)
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "entitlement_version_conflict"

    event = db.query(SchoolEntitlementEvent).filter_by(
        school_id=school.id,
        capability=BEHAVIOUR_POINTS,
        action="disabled",
    ).one()
    db.delete(event)
    with pytest.raises(ValueError, match="append-only"):
        db.flush()
    db.rollback()


def test_disabled_capability_returns_stable_403_before_report_data(db, client, seeded_schools):
    school = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    report_grant = db.query(SchoolEntitlement).filter_by(
        school_id=school.id,
        capability=REPORTS_INSIGHTS,
    ).one()
    report_grant.enabled = False
    db.commit()

    response = client.get(
        "/api/school/reports/behaviour/overview",
        headers=school_headers(admin, school),
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": {
            "code": "capability_not_enabled",
            "capability": REPORTS_INSIGHTS,
        }
    }


def test_operational_controls_remain_readable_and_restore_saved_effect(
    db,
    client,
    seeded_schools,
    monkeypatch,
):
    school = seeded_schools["schools"]["alpha"]
    admin = seeded_schools["users"]["alpha_admin"]
    membership = db.query(Membership).filter_by(
        school_id=school.id,
        user_id=admin.id,
        role="school_admin",
    ).one()
    db.add_all(
        [
            SchoolFeatureControl(
                school_id=school.id,
                feature="voice_notes",
                enabled=True,
                control_version=4,
                disclosure_version=VOICE_NOTES_DISCLOSURE_VERSION,
                updated_by_membership_id=membership.id,
            ),
            SchoolMessagingPolicy(
                school_id=school.id,
                enabled=True,
                delivery_receipts_visible=False,
                read_receipts_visible=True,
                policy_version=6,
                updated_by_membership_id=membership.id,
            ),
        ]
    )
    db.commit()
    monkeypatch.setattr(database.settings, "MESSAGING_ENABLED", True)

    for capability in (VOICE_NOTES, SCHOOL_CHATS):
        db.query(SchoolEntitlement).filter_by(
            school_id=school.id,
            capability=capability,
        ).one().enabled = False
    db.commit()
    headers = school_headers(admin, school)

    voice = client.get("/api/school/feature-controls", headers=headers)
    assert voice.status_code == 200
    assert voice.json()["voice_notes"]["enabled"] is True
    assert voice.json()["voice_notes"]["effective_enabled"] is False

    messaging = client.get("/api/school/messaging-policy", headers=headers)
    assert messaging.status_code == 200
    assert messaging.json()["enabled"] is True
    assert messaging.json()["effective_enabled"] is False
    assert messaging.json()["delivery_receipts_visible"] is False
    assert messaging.json()["read_receipts_visible"] is True

    voice_write = client.put(
        "/api/school/feature-controls/voice-notes",
        headers=headers,
        json={
            "enabled": False,
            "expected_control_version": 4,
            "disclosure_version": VOICE_NOTES_DISCLOSURE_VERSION,
            "acknowledged": True,
        },
    )
    assert voice_write.status_code == 403
    assert voice_write.json()["detail"]["capability"] == VOICE_NOTES

    messaging_payload = messaging.json()
    messaging_write = client.put(
        "/api/school/messaging-policy",
        headers=headers,
        json={
            "expected_policy_version": messaging_payload["policy_version"],
            "enabled": messaging_payload["enabled"],
            "guardian_replies_enabled": messaging_payload["guardian_replies_enabled"],
            "delivery_receipts_visible": True,
            "read_receipts_visible": messaging_payload["read_receipts_visible"],
            "allow_staff_out_of_hours_opt_in": messaging_payload["allow_staff_out_of_hours_opt_in"],
            "teachers_may_mark_urgent": messaging_payload["teachers_may_mark_urgent"],
            "notification_preview_mode": messaging_payload["notification_preview_mode"],
            "retention_days": messaging_payload["retention_days"],
            "email_mode": messaging_payload["email_mode"],
        },
    )
    assert messaging_write.status_code == 403
    assert messaging_write.json()["detail"]["capability"] == SCHOOL_CHATS

    for capability in (VOICE_NOTES, SCHOOL_CHATS):
        db.query(SchoolEntitlement).filter_by(
            school_id=school.id,
            capability=capability,
        ).one().enabled = True
    db.commit()

    restored_voice = client.get("/api/school/feature-controls", headers=headers).json()["voice_notes"]
    restored_messaging = client.get("/api/school/messaging-policy", headers=headers).json()
    assert restored_voice["enabled"] is True
    assert restored_voice["effective_enabled"] is True
    assert restored_messaging["enabled"] is True
    assert restored_messaging["effective_enabled"] is True
    assert restored_messaging["delivery_receipts_visible"] is False
    assert restored_messaging["read_receipts_visible"] is True

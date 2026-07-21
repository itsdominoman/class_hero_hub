import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database
from app.database import Base, get_db
from app.main import app
from app.models_school import (
    Membership,
    MessagingPermissionGrant,
    FhhLink,
    School,
    Survey,
    SurveyResponse,
    User,
)
from app.routes.surveys import QuestionInput, SurveyInput, _bind_household_ref
from app.survey_service import refresh_survey_state


engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
Session = sessionmaker(bind=engine)


@pytest.fixture
def db():
    database.engine = engine
    database.SessionLocal = Session
    Base.metadata.create_all(engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _headers(email: str, school_id: int) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {auth.create_access_token({'sub': email})}",
        "X-School-Id": str(school_id),
    }


def _world(db):
    school = School(name="Survey School", slug="survey-school", status="active")
    allowed_user = User(email="surveys@test.local", name="Survey Admin", google_sub="surveys-admin")
    denied_user = User(email="denied@test.local", name="Denied Admin", google_sub="denied-admin")
    db.add_all([school, allowed_user, denied_user])
    db.flush()
    allowed = Membership(school_id=school.id, user_id=allowed_user.id, role="school_admin", status="active")
    denied = Membership(school_id=school.id, user_id=denied_user.id, role="school_admin", status="active")
    db.add_all([allowed, denied])
    db.flush()
    db.add(
        MessagingPermissionGrant(
            school_id=school.id,
            membership_id=allowed.id,
            permission="surveys.manage",
            granted_by_membership_id=allowed.id,
            grant_reason="Focused survey integration test",
        )
    )
    db.commit()
    return school, allowed_user, denied_user


def _payload() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "title": "Pilot transport poll",
        "introduction": "Tell us how families travel to school.",
        "instructions": "Submit one response.",
        "audience_type": "whole_school",
        "target_ids": [],
        "anonymous": True,
        "response_mode": "household",
        "opens_at": (now - timedelta(minutes=5)).isoformat(),
        "closes_at": (now + timedelta(days=2)).isoformat(),
        "push_enabled": False,
        "dashboard_card_enabled": True,
        "notices_feed_enabled": True,
        "questions": [
            {
                "question_type": "single_choice",
                "prompt": "Usual journey",
                "required": True,
                "options": [{"label": "Bus"}, {"label": "Car"}],
            },
            {
                "question_type": "rating",
                "prompt": "Rate the service",
                "required": False,
                "scale_min": 1,
                "scale_max": 5,
            },
        ],
    }


def test_permission_gates_draft_publish_and_preserves_question_order(db, client):
    school, allowed_user, denied_user = _world(db)

    denied_headers = _headers(denied_user.email, school.id)
    assert client.get("/api/school/surveys/availability", headers=denied_headers).json() == {"available": False}
    assert client.post("/api/school/surveys", headers=denied_headers, json=_payload()).status_code == 403

    allowed_headers = _headers(allowed_user.email, school.id)
    created = client.post("/api/school/surveys", headers=allowed_headers, json=_payload())
    assert created.status_code == 201, created.text
    draft = created.json()
    assert draft["status"] == "draft"
    assert [question["sort_order"] for question in draft["questions"]] == [0, 1]
    assert draft["anonymous"] is True
    assert draft["response_mode"] == "household"

    published = client.post(f"/api/school/surveys/{draft['id']}/publish", headers=allowed_headers)
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "open"
    assert client.put(f"/api/school/surveys/{draft['id']}", headers=allowed_headers, json=_payload()).status_code == 409


def test_window_validation_lifecycle_and_duplicate_response_unit(db):
    question = QuestionInput(
        question_type="rating", prompt="Score", required=True, scale_min=1, scale_max=5
    )
    now = datetime.now(timezone.utc)
    body = SurveyInput(
        title="Valid", introduction="Valid intro", audience_type="whole_school",
        opens_at=now, closes_at=now + timedelta(hours=1), questions=[question]
    )
    assert body.questions[0].scale_max == 5

    survey = Survey(
        public_id=uuid4(), school_id=1, title="Lifecycle", introduction="Intro",
        audience_type="whole_school", anonymous=True, response_mode="guardian",
        opens_at=now - timedelta(hours=2), closes_at=now - timedelta(hours=1),
        status="open", created_by_membership_id=1,
    )
    assert refresh_survey_state(survey, now=now) is True
    assert survey.status == "closed"

    school = School(id=1, name="Unique School", slug="unique-school", status="active")
    user = User(id=1, email="unique@test.local", name="Admin", google_sub="unique-admin")
    membership = Membership(id=1, school_id=1, user_id=1, role="school_admin", status="active")
    survey.status = "closed"
    db.add_all([school, user, membership, survey])
    db.flush()
    db.add_all([
        SurveyResponse(survey_id=survey.id, response_key_hash="a" * 64),
        SurveyResponse(survey_id=survey.id, response_key_hash="a" * 64),
    ])
    with pytest.raises(IntegrityError):
        db.commit()


def test_household_evidence_is_bound_once_and_cannot_be_changed():
    link = FhhLink(fhh_household_ref=None)
    first = "a" * 64
    _bind_household_ref(link, first)
    assert link.fhh_household_ref == first
    _bind_household_ref(link, first)
    with pytest.raises(HTTPException) as caught:
        _bind_household_ref(link, "b" * 64)
    assert caught.value.status_code == 409

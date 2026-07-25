import csv
import io
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database
from app.database import Base, get_db
from app.main import app
from app.models_school import (
    AuditLog,
    Membership,
    MessagingPermissionGrant,
    FhhLink,
    School,
    Survey,
    SurveyAnswer,
    SurveyEvent,
    SurveyOption,
    SurveyQuestion,
    SurveyResponse,
    User,
)
from app.routes import surveys as survey_routes
from app.routes.surveys import (
    QuestionInput,
    SurveyInput,
    _answer_results,
    _bind_household_ref,
    _sanitise_csv_cell,
)
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

    survey.closes_at = now + timedelta(hours=1)
    survey.closed_at = now
    assert refresh_survey_state(survey, now=now) is False
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


def test_closed_survey_can_extend_closing_time_and_reopen(db, client):
    school, allowed_user, _ = _world(db)
    headers = _headers(allowed_user.email, school.id)
    created = client.post("/api/school/surveys", headers=headers, json=_payload()).json()
    survey_id = created["id"]

    assert client.post(f"/api/school/surveys/{survey_id}/publish", headers=headers).status_code == 200
    assert client.post(f"/api/school/surveys/{survey_id}/close", headers=headers).status_code == 200

    survey_public_id = UUID(survey_id)
    survey = db.query(Survey).filter(Survey.public_id == survey_public_id).one()
    previous_close = datetime.now(timezone.utc) - timedelta(minutes=5)
    survey.closes_at = previous_close
    db.commit()

    expired = client.post(f"/api/school/surveys/{survey_id}/reopen", headers=headers, json={})
    assert expired.status_code == 409
    assert expired.json()["detail"] == "Choose a future closing time before reopening"

    next_close = datetime.now(timezone.utc) + timedelta(days=1)
    reopened = client.post(
        f"/api/school/surveys/{survey_id}/reopen",
        headers=headers,
        json={"closes_at": next_close.isoformat()},
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "open"
    returned_close = datetime.fromisoformat(reopened.json()["closes_at"]).replace(tzinfo=timezone.utc)
    assert returned_close == next_close

    db.expire_all()
    survey = db.query(Survey).filter(Survey.public_id == survey_public_id).one()
    assert survey.status == "open"
    assert survey.closed_at is None
    event = db.query(SurveyEvent).filter_by(survey_id=survey.id, action="reopened").one()
    assert event.detail["previous_closes_at"] == previous_close.isoformat()
    assert event.detail["closes_at"] == next_close.isoformat()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("=1+1", "'=1+1"),
        ("+SUM(A1:A2)", "'+SUM(A1:A2)"),
        ("-2+3", "'-2+3"),
        ("@SUM(A1:A2)", "'@SUM(A1:A2)"),
        ("  =Survey description", "'  =Survey description"),
        ("\t@Respondent", "'\t@Respondent"),
        ('He said "yes", then added\nسطر جديد', 'He said "yes", then added\nسطر جديد'),
        ("نص عربي آمن", "نص عربي آمن"),
        ("Ordinary safe text", "Ordinary safe text"),
        (42, 42),
    ],
)
def test_survey_csv_cell_sanitiser(value, expected):
    assert _sanitise_csv_cell(value) == expected


@pytest.mark.parametrize("anonymous", [True, False], ids=["anonymous", "identified"])
def test_survey_csv_export_sanitises_untrusted_cells_without_changing_privacy_or_structure(
    db, client, anonymous
):
    school, allowed_user, _ = _world(db)
    membership = db.query(Membership).filter_by(school_id=school.id, user_id=allowed_user.id).one()
    opens_at = datetime(2026, 7, 24, 8, 0, tzinfo=timezone.utc)
    closes_at = datetime(2026, 7, 25, 8, 0, tzinfo=timezone.utc)
    submitted_at = datetime(2026, 7, 24, 10, 30, tzinfo=timezone.utc)
    survey = Survey(
        public_id=uuid4(),
        school_id=school.id,
        title="=Survey title",
        introduction="  =Survey description",
        audience_type="whole_school",
        anonymous=anonymous,
        response_mode="guardian",
        opens_at=opens_at,
        closes_at=closes_at,
        status="closed",
        created_by_membership_id=membership.id,
    )
    db.add(survey)
    db.flush()
    choice = SurveyQuestion(
        public_id=uuid4(),
        survey_id=survey.id,
        question_type="single_choice",
        prompt="+Choice question",
        required=True,
        sort_order=0,
    )
    formula_text = SurveyQuestion(
        public_id=uuid4(),
        survey_id=survey.id,
        question_type="short_text",
        prompt=" \t-Free-text question",
        required=True,
        sort_order=1,
    )
    safe_text = SurveyQuestion(
        public_id=uuid4(),
        survey_id=survey.id,
        question_type="long_text",
        prompt="سؤال عربي آمن",
        required=True,
        sort_order=2,
    )
    rating = SurveyQuestion(
        public_id=uuid4(),
        survey_id=survey.id,
        question_type="rating",
        prompt="@Rating question",
        required=True,
        sort_order=3,
        scale_min=1,
        scale_max=5,
    )
    db.add_all([choice, formula_text, safe_text, rating])
    db.flush()
    selected = SurveyOption(
        public_id=uuid4(),
        question_id=choice.id,
        label="+Selected option",
        sort_order=0,
    )
    db.add(selected)
    db.flush()
    survey_response = SurveyResponse(
        public_id=uuid4(),
        survey_id=survey.id,
        response_key_hash=("a" if anonymous else "b") * 64,
        respondent_label=None if anonymous else "@Permitted respondent",
        submitted_at=submitted_at,
    )
    db.add(survey_response)
    db.flush()
    safe_multiline = 'He said "yes", then added a comma,\nثم كتب سطراً عربياً'
    db.add_all(
        [
            SurveyAnswer(
                response_id=survey_response.id,
                question_id=choice.id,
                selected_option_ids=[selected.id],
            ),
            SurveyAnswer(
                response_id=survey_response.id,
                question_id=formula_text.id,
                answer_text="-Free-text answer",
            ),
            SurveyAnswer(
                response_id=survey_response.id,
                question_id=safe_text.id,
                answer_text=safe_multiline,
            ),
            SurveyAnswer(
                response_id=survey_response.id,
                question_id=rating.id,
                answer_number=4,
            ),
        ]
    )
    db.commit()

    response = client.get(
        f"/api/school/surveys/{survey.public_id}/export.csv",
        headers=_headers(allowed_user.email, school.id),
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
    expected_header = [
        "response_timestamp",
        *([] if anonymous else ["respondent"]),
        "'+Choice question",
        "' \t-Free-text question",
        "سؤال عربي آمن",
        "'@Rating question",
    ]
    expected_values = [
        *([] if anonymous else ["'@Permitted respondent"]),
        "'+Selected option",
        "'-Free-text answer",
        safe_multiline,
        "4",
    ]
    assert rows[:9] == [
        ["survey_title", "'=Survey title"],
        ["status", "closed"],
        ["audience", "whole_school"],
        ["anonymous", str(anonymous).lower()],
        ["response_mode", "guardian"],
        ["opens_at", survey.opens_at.isoformat()],
        ["closes_at", survey.closes_at.isoformat()],
        [],
        expected_header,
    ]
    assert datetime.fromisoformat(rows[5][1]) == survey.opens_at
    assert datetime.fromisoformat(rows[6][1]) == survey.closes_at
    assert datetime.fromisoformat(rows[9][0]) == survey_response.submitted_at
    assert rows[9][1:] == expected_values
    assert ("@Permitted respondent" not in response.text) if anonymous else True
    assert db.query(SurveyEvent).filter_by(survey_id=survey.id, action="exported").count() == 1
    audit = db.query(AuditLog).filter_by(action="school.survey.exported", entity_id=survey.id).one()
    assert audit.detail == {"format": "csv", "anonymous": anonymous}


def test_survey_results_use_fixed_batched_query_count_with_representative_answers(db):
    school, allowed_user, _ = _world(db)
    membership = db.query(Membership).filter_by(
        school_id=school.id, user_id=allowed_user.id
    ).one()
    now = datetime.now(timezone.utc)
    survey = Survey(
        school_id=school.id,
        title="Representative results",
        introduction="Aggregation coverage",
        audience_type="whole_school",
        anonymous=True,
        response_mode="guardian",
        opens_at=now - timedelta(days=1),
        closes_at=now + timedelta(days=1),
        status="open",
        created_by_membership_id=membership.id,
    )
    db.add(survey)
    db.flush()
    question_types = [
        ("single_choice", None, None),
        ("multiple_choice", None, None),
        ("yes_no", None, None),
        ("rating", 1, 5),
        ("short_text", None, None),
        ("long_text", None, None),
    ]
    questions = [
        SurveyQuestion(
            survey_id=survey.id,
            question_type=question_type,
            prompt=f"Question {index}",
            required=False,
            sort_order=index,
            scale_min=scale_min,
            scale_max=scale_max,
        )
        for index, (question_type, scale_min, scale_max) in enumerate(question_types)
    ]
    db.add_all(questions)
    db.flush()
    options = [
        SurveyOption(question_id=question.id, label=label, sort_order=sort_order)
        for question in questions[:2]
        for sort_order, label in enumerate(("First", "Second"))
    ]
    db.add_all(options)
    db.flush()
    options_by_question = {
        question.id: [row for row in options if row.question_id == question.id]
        for question in questions[:2]
    }
    for index in range(4):
        response = SurveyResponse(
            survey_id=survey.id,
            response_key_hash=f"{index:064x}",
            submitted_at=now + timedelta(minutes=index),
        )
        db.add(response)
        db.flush()
        db.add_all(
            [
                SurveyAnswer(
                    response_id=response.id,
                    question_id=questions[0].id,
                    selected_option_ids=[options_by_question[questions[0].id][index % 2].id],
                ),
                SurveyAnswer(
                    response_id=response.id,
                    question_id=questions[1].id,
                    selected_option_ids=[
                        row.id for row in options_by_question[questions[1].id]
                    ],
                ),
                SurveyAnswer(
                    response_id=response.id,
                    question_id=questions[2].id,
                    answer_boolean=index % 2 == 0,
                ),
                SurveyAnswer(
                    response_id=response.id,
                    question_id=questions[3].id,
                    answer_number=index + 1,
                ),
                SurveyAnswer(
                    response_id=response.id,
                    question_id=questions[4].id,
                    answer_text=f"Short {index}",
                ),
                SurveyAnswer(
                    response_id=response.id,
                    question_id=questions[5].id,
                    answer_text=f"Long {index}",
                ),
            ]
        )
    db.commit()
    questions = (
        db.query(SurveyQuestion)
        .filter(SurveyQuestion.survey_id == survey.id)
        .order_by(SurveyQuestion.sort_order)
        .all()
    )

    selects = []

    def count_selects(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    event.listen(engine, "before_cursor_execute", count_selects)
    try:
        results = _answer_results(db, questions)
    finally:
        event.remove(engine, "before_cursor_execute", count_selects)

    assert len(selects) == 5
    assert [row["answer_count"] for row in results] == [4] * 6
    assert results[0]["distribution"][0]["count"] == 2
    assert results[1]["distribution"] == [
        {
            "option_id": str(row.public_id),
            "label": row.label,
            "count": 4,
        }
        for row in options_by_question[questions[1].id]
    ]
    assert results[2]["distribution"] == [
        {"label": "Yes", "count": 2},
        {"label": "No", "count": 2},
    ]
    assert results[3]["average"] == 2.5


def test_survey_csv_export_batches_responses_and_answers(db, client, monkeypatch):
    school, allowed_user, _ = _world(db)
    membership = db.query(Membership).filter_by(
        school_id=school.id, user_id=allowed_user.id
    ).one()
    now = datetime.now(timezone.utc)
    survey = Survey(
        school_id=school.id,
        title="Bounded export",
        introduction="Representative export",
        audience_type="whole_school",
        anonymous=False,
        response_mode="guardian",
        opens_at=now - timedelta(days=2),
        closes_at=now - timedelta(days=1),
        status="closed",
        created_by_membership_id=membership.id,
    )
    db.add(survey)
    db.flush()
    question = SurveyQuestion(
        survey_id=survey.id,
        question_type="short_text",
        prompt="Comment",
        required=True,
        sort_order=0,
    )
    db.add(question)
    db.flush()
    for index in range(5):
        response = SurveyResponse(
            survey_id=survey.id,
            response_key_hash=f"{index + 10:064x}",
            respondent_label=f"Parent {index}",
            submitted_at=now + timedelta(minutes=index),
        )
        db.add(response)
        db.flush()
        db.add(
            SurveyAnswer(
                response_id=response.id,
                question_id=question.id,
                answer_text=f"Comment {index}",
            )
        )
    db.commit()
    monkeypatch.setattr(survey_routes, "CSV_EXPORT_BATCH_SIZE", 2)
    response_selects = []
    answer_selects = []

    def capture_batches(_connection, _cursor, statement, _parameters, _context, _many):
        normalised = " ".join(statement.lower().split())
        if "from survey_responses" in normalised:
            response_selects.append(statement)
        if "from survey_answers" in normalised:
            answer_selects.append(statement)

    event.listen(engine, "before_cursor_execute", capture_batches)
    try:
        response = client.get(
            f"/api/school/surveys/{survey.public_id}/export.csv",
            headers=_headers(allowed_user.email, school.id),
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture_batches)

    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert len(rows) == 14
    assert rows[9][1:] == ["Parent 0", "Comment 0"]
    assert rows[13][1:] == ["Parent 4", "Comment 4"]
    assert len(response_selects) == 3
    assert len(answer_selects) == 3


def test_household_evidence_is_bound_once_and_cannot_be_changed():
    link = FhhLink(fhh_household_ref=None)
    first = "a" * 64
    _bind_household_ref(link, first)
    assert link.fhh_household_ref == first
    _bind_household_ref(link, first)
    with pytest.raises(HTTPException) as caught:
        _bind_household_ref(link, "b" * 64)
    assert caught.value.status_code == 409

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event, current_thread
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, Request
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models_school import (
    AuditLog,
    FhhLink,
    FhhLinkInvite,
    FhhMessagingIdentity,
    FhhMessagingIdentityLink,
    Membership,
    School,
    Student,
    Survey,
    SurveyAnswer,
    SurveyEvent,
    SurveyOption,
    SurveyQuestion,
    SurveyResponse,
    User,
)
from app.routes import surveys as survey_routes


DATABASE_URL = os.getenv("MESSAGING_TEST_DATABASE_URL")
UTC = timezone.utc


@pytest.mark.skipif(not DATABASE_URL, reason="requires disposable PostgreSQL database")
def test_survey_result_aggregation_uses_fixed_postgresql_query_count():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    marker = uuid4()
    now = datetime.now(UTC)
    try:
        school = School(
            name="Survey aggregation",
            slug=f"survey-aggregation-{marker}",
            status="active",
        )
        admin = User(
            email=f"survey-aggregation-{marker}@test",
            name="Survey aggregation administrator",
            google_sub=f"survey-aggregation-{marker}",
        )
        session.add_all([school, admin])
        session.flush()
        membership = Membership(
            school_id=school.id,
            user_id=admin.id,
            role="school_admin",
            status="active",
        )
        session.add(membership)
        session.flush()
        survey = Survey(
            school_id=school.id,
            title="PostgreSQL aggregation",
            introduction="Representative data",
            audience_type="whole_school",
            anonymous=True,
            response_mode="guardian",
            opens_at=now - timedelta(hours=1),
            closes_at=now + timedelta(hours=1),
            status="open",
            created_by_membership_id=membership.id,
        )
        session.add(survey)
        session.flush()
        choice = SurveyQuestion(
            survey_id=survey.id,
            question_type="multiple_choice",
            prompt="Choices",
            required=True,
            sort_order=0,
        )
        rating = SurveyQuestion(
            survey_id=survey.id,
            question_type="rating",
            prompt="Rating",
            required=True,
            sort_order=1,
            scale_min=1,
            scale_max=5,
        )
        session.add_all([choice, rating])
        session.flush()
        options = [
            SurveyOption(
                question_id=choice.id,
                label=label,
                sort_order=index,
            )
            for index, label in enumerate(("First", "Second"))
        ]
        session.add_all(options)
        session.flush()
        for index in range(3):
            response = SurveyResponse(
                survey_id=survey.id,
                response_key_hash=f"{index + 100:064x}",
                submitted_at=now + timedelta(minutes=index),
            )
            session.add(response)
            session.flush()
            session.add_all(
                [
                    SurveyAnswer(
                        response_id=response.id,
                        question_id=choice.id,
                        selected_option_ids=[row.id for row in options],
                    ),
                    SurveyAnswer(
                        response_id=response.id,
                        question_id=rating.id,
                        answer_number=index + 2,
                    ),
                ]
            )
        session.commit()
        questions = (
            session.query(SurveyQuestion)
            .filter(SurveyQuestion.survey_id == survey.id)
            .order_by(SurveyQuestion.sort_order)
            .all()
        )
        selects = []

        def count_selects(
            _connection, _cursor, statement, _parameters, _context, _executemany
        ):
            if statement.lstrip().upper().startswith("SELECT"):
                selects.append(statement)

        event.listen(engine, "before_cursor_execute", count_selects)
        try:
            results = survey_routes._answer_results(session, questions)
        finally:
            event.remove(engine, "before_cursor_execute", count_selects)

        assert len(selects) == 5
        assert [row["count"] for row in results[0]["distribution"]] == [3, 3]
        assert results[1]["average"] == 3
    finally:
        session.close()
        engine.dispose()


@pytest.mark.skipif(not DATABASE_URL, reason="requires disposable PostgreSQL database")
def test_survey_close_and_response_submission_have_one_atomic_lock_order(monkeypatch):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    setup = Session()
    marker = uuid4()
    now = datetime.now(UTC)
    try:
        school = School(
            name="Survey concurrency",
            slug=f"survey-concurrency-{marker}",
            status="active",
        )
        admin = User(
            email=f"survey-concurrency-{marker}@test",
            name="Survey administrator",
            google_sub=f"survey-concurrency-{marker}",
        )
        setup.add_all([school, admin])
        setup.flush()
        membership = Membership(
            school_id=school.id,
            user_id=admin.id,
            role="school_admin",
            status="active",
        )
        student = Student(
            school_id=school.id,
            first_name="Survey",
            last_name="Student",
            status="active",
        )
        setup.add_all([membership, student])
        setup.flush()
        invite = FhhLinkInvite(
            school_id=school.id,
            student_id=student.id,
            token_hash=f"survey-invite-{marker}",
            display_code_last4="0725",
            created_by_user_id=admin.id,
        )
        setup.add(invite)
        setup.flush()
        link = FhhLink(
            school_id=school.id,
            student_id=student.id,
            source_invite_id=invite.id,
            link_token_hash=f"survey-link-{marker}",
            fhh_child_ref=f"survey-child-{marker}",
            status="active",
        )
        identity = FhhMessagingIdentity(
            school_id=school.id,
            external_subject_ref=uuid4(),
            display_name="Survey parent",
            preferred_locale="en",
            status="active",
        )
        setup.add_all([link, identity])
        setup.flush()
        setup.add(
            FhhMessagingIdentityLink(
                school_id=school.id,
                fhh_link_id=link.id,
                identity_id=identity.id,
                status="active",
                sync_version=1,
            )
        )

        surveys = []
        questions = []
        for title in ("Close wins", "Response wins"):
            survey = Survey(
                school_id=school.id,
                title=title,
                introduction="Concurrency ordering",
                audience_type="whole_school",
                anonymous=False,
                response_mode="guardian",
                opens_at=now - timedelta(hours=1),
                closes_at=now + timedelta(hours=1),
                status="open",
                created_by_membership_id=membership.id,
            )
            setup.add(survey)
            setup.flush()
            question = SurveyQuestion(
                survey_id=survey.id,
                question_type="rating",
                prompt="Rating",
                required=True,
                sort_order=0,
                scale_min=1,
                scale_max=5,
            )
            setup.add(question)
            setup.flush()
            surveys.append(survey)
            questions.append(question)
        setup.commit()
        membership_id = membership.id
        link_id = link.id
        identity_id = identity.id
        survey_ids = [survey.id for survey in surveys]
        survey_public_ids = [survey.public_id for survey in surveys]
        question_public_ids = [question.public_id for question in questions]
    finally:
        setup.close()

    def fake_actor(_request, db, _link_id, _token, _assertion, _body):
        return (
            db.query(FhhLink).filter(FhhLink.id == link_id).one(),
            db.query(FhhMessagingIdentity)
            .filter(FhhMessagingIdentity.id == identity_id)
            .one(),
            None,
        )

    monkeypatch.setattr(survey_routes, "_integration_actor", fake_actor)
    request = Request({"type": "http", "method": "POST", "path": "/", "headers": []})
    household_ref = "a" * 64

    def close(public_id: UUID):
        session = Session()
        try:
            member = session.query(Membership).filter(Membership.id == membership_id).one()
            return survey_routes.close_survey(public_id, member, session)
        finally:
            session.close()

    def respond(public_id: UUID, question_id: UUID, started: Event):
        session = Session()
        try:
            started.set()
            try:
                result = survey_routes.submit_parent_response(
                    link_id,
                    public_id,
                    survey_routes.ParentSubmission(
                        household_ref=household_ref,
                        answers=[
                            survey_routes.ParentAnswerInput(
                                question_id=question_id, value=4
                            )
                        ],
                    ),
                    request,
                    db=session,
                )
                return result
            except HTTPException as exc:
                session.rollback()
                return {"status_code": exc.status_code, "detail": exc.detail}
        finally:
            session.close()

    locked = Event()
    release = Event()
    lock_owner = {"thread": "close-wins"}

    def hold_winning_lock(
        _connection, _cursor, statement, _parameters, _context, _executemany
    ):
        if (
            current_thread().name.startswith(lock_owner["thread"])
            and "FROM surveys" in statement
            and "FOR UPDATE" in statement
        ):
            locked.set()
            assert release.wait(timeout=5)

    event.listen(engine, "after_cursor_execute", hold_winning_lock)
    try:
        with ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="close-wins"
        ) as executor:
            close_future = executor.submit(
                lambda: close(survey_public_ids[0])
            )
            assert locked.wait(timeout=5)
            response_started = Event()
            response_future = executor.submit(
                respond,
                survey_public_ids[0],
                question_public_ids[0],
                response_started,
            )
            assert response_started.wait(timeout=5)
            release.set()
            assert close_future.result(timeout=10)["status"] == "closed"
            rejected = response_future.result(timeout=10)
            assert rejected == {"status_code": 409, "detail": "Survey is closed"}

        verify = Session()
        try:
            assert (
                verify.query(SurveyResponse)
                .filter(SurveyResponse.survey_id == survey_ids[0])
                .count()
                == 0
            )
        finally:
            verify.close()

        locked.clear()
        release.clear()
        lock_owner["thread"] = "response-wins"
        response_started = Event()
        with ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="response-wins"
        ) as executor:
            response_future = executor.submit(
                respond,
                survey_public_ids[1],
                question_public_ids[1],
                response_started,
            )
            assert response_started.wait(timeout=5)
            assert locked.wait(timeout=5)
            close_started = Event()

            def close_after_response():
                close_started.set()
                return close(survey_public_ids[1])

            close_future = executor.submit(close_after_response)
            assert close_started.wait(timeout=5)
            release.set()
            submitted = response_future.result(timeout=10)
            assert submitted["status"] == "submitted"
            assert close_future.result(timeout=10)["status"] == "closed"

        verify = Session()
        try:
            persisted = (
                verify.query(SurveyResponse)
                .filter(SurveyResponse.survey_id == survey_ids[1])
                .one()
            )
            assert str(persisted.public_id) == submitted["response_id"]
            assert persisted.respondent_label == "Survey parent"
            assert persisted.submitted_at is not None
            assert (
                verify.query(SurveyEvent)
                .filter_by(survey_id=survey_ids[1], action="closed")
                .count()
                == 1
            )
            assert (
                verify.query(AuditLog)
                .filter_by(
                    action="school.survey.closed",
                    entity_id=survey_ids[1],
                )
                .count()
                == 1
            )
        finally:
            verify.close()
    finally:
        event.remove(engine, "after_cursor_execute", hold_winning_lock)
        engine.dispose()

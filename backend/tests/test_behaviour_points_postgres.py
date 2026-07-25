import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.behaviour_service import create_events
from app.models_school import (
    BehaviourAwardRequest,
    BehaviourCategory,
    BehaviourEvent,
    Membership,
    School,
    Student,
    User,
)


DATABASE_URL = os.getenv("BEHAVIOUR_TEST_DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="requires disposable PostgreSQL database")
def test_concurrent_duplicate_award_requests_converge_on_one_batch():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    setup = Session()
    marker = str(uuid4())
    try:
        school = School(name="Award concurrency", slug=f"award-concurrency-{marker}", status="active")
        teacher = User(
            email=f"award-concurrency-{marker}@test",
            name="Award concurrency teacher",
            google_sub=f"award-concurrency-{marker}",
        )
        setup.add_all([school, teacher])
        setup.flush()
        setup.add(Membership(
            school_id=school.id,
            user_id=teacher.id,
            role="teacher",
            status="active",
        ))
        student = Student(
            school_id=school.id,
            first_name="Concurrent",
            last_name="Learner",
            status="active",
        )
        category = BehaviourCategory(
            school_id=school.id,
            type="positive",
            label=f"Concurrent praise {marker}",
            points_value=1,
            active=True,
        )
        setup.add_all([student, category])
        setup.commit()
        school_id = school.id
        teacher_id = teacher.id
        student_id = student.id
        category_id = category.id
    finally:
        setup.close()

    barrier = Barrier(2)
    request_key = uuid4()

    def award() -> tuple[list[int], bool]:
        session = Session()
        try:
            actor = session.query(User).filter_by(id=teacher_id).one()
            barrier.wait(timeout=5)
            rows, replay = create_events(
                session,
                school_id=school_id,
                student_ids=[student_id],
                category_id=category_id,
                actor=actor,
                idempotency_key=request_key,
                note=None,
            )
            session.commit()
            return [row.id for row in rows], replay
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = [
                future.result(timeout=10)
                for future in (executor.submit(award), executor.submit(award))
            ]
        assert results[0][0] == results[1][0]
        assert sorted(result[1] for result in results) == [False, True]

        verify = Session()
        try:
            request = verify.query(BehaviourAwardRequest).filter_by(
                school_id=school_id,
                actor_user_id=teacher_id,
                idempotency_key=request_key,
            ).one()
            events = verify.query(BehaviourEvent).filter_by(award_request_id=request.id).all()
            assert len(events) == 1
            assert events[0].student_id == student_id
        finally:
            verify.close()
    finally:
        engine.dispose()

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.behaviour_service import create_events, reverse_event
from app.family_notifications import (
    cancel_reversed_behaviour_event_notifications,
    enqueue_family_notifications,
)
from app import messaging_notification_dispatch
from app.messaging_notification_dispatch import dispatch_claimed_rows
from app.models_school import (
    BehaviourAwardRequest,
    BehaviourCategory,
    BehaviourEvent,
    FhhLink,
    FhhLinkInvite,
    Membership,
    NotificationOutbox,
    School,
    SchoolPointsNotificationPolicy,
    Student,
    User,
)


DATABASE_URL = os.getenv("BEHAVIOUR_TEST_DATABASE_URL")
UTC = timezone.utc


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


def _immediate_notification_world(Session):
    setup = Session()
    marker = str(uuid4())
    now = datetime.now(UTC)
    try:
        school = School(name="Point delivery race", slug=f"point-delivery-race-{marker}", status="active")
        teacher = User(
            email=f"point-delivery-race-{marker}@test",
            name="Point delivery race teacher",
            google_sub=f"point-delivery-race-{marker}",
        )
        setup.add_all([school, teacher])
        setup.flush()
        setup.add_all([
            Membership(school_id=school.id, user_id=teacher.id, role="teacher", status="active"),
            SchoolPointsNotificationPolicy(school_id=school.id, mode="immediate"),
        ])
        student = Student(
            school_id=school.id,
            first_name="Race",
            last_name="Learner",
            status="active",
        )
        category = BehaviourCategory(
            school_id=school.id,
            type="positive",
            label=f"Race praise {marker}",
            points_value=1,
            active=True,
        )
        setup.add_all([student, category])
        setup.flush()
        invite = FhhLinkInvite(
            school_id=school.id,
            student_id=student.id,
            token_hash=f"race-invite-{marker}",
            display_code_last4="0101",
            created_by_user_id=teacher.id,
        )
        setup.add(invite)
        setup.flush()
        link = FhhLink(
            school_id=school.id,
            student_id=student.id,
            source_invite_id=invite.id,
            link_token_hash=f"race-link-{marker}",
            fhh_child_ref=f"race-child-{marker}",
            status="active",
        )
        event = BehaviourEvent(
            school_id=school.id,
            student_id=student.id,
            category_id=category.id,
            actor_user_id=teacher.id,
            points_delta=1,
            source="teacher",
            context_type="general",
            created_at=now,
        )
        setup.add_all([link, event])
        setup.flush()
        row = enqueue_family_notifications(
            setup,
            category="points",
            source=event,
            action="awarded",
            eligible_at=now,
        )[0]
        row.state = "leased"
        row.lease_owner = "notification-dispatch-race"
        row.lease_expires_at = now + timedelta(minutes=1)
        setup.commit()
        return school.id, teacher.id, event.id, row.id, now
    finally:
        setup.close()


class _UnusedPushProvider:
    def send(self, **_kwargs):
        raise AssertionError("CHH-device push must not be used for FHH point delivery")


class _RecordingBridgeProvider:
    def __init__(self):
        self.calls = []

    def send(self, **kwargs):
        self.calls.append(kwargs)
        return "accepted"


class _BlockingBridgeProvider(_RecordingBridgeProvider):
    def __init__(self):
        super().__init__()
        self.entered = Event()
        self.release = Event()

    def send(self, **kwargs):
        self.calls.append(kwargs)
        self.entered.set()
        assert self.release.wait(timeout=5)
        return "accepted"


@pytest.mark.skipif(not DATABASE_URL, reason="requires disposable PostgreSQL database")
def test_reversal_cancellation_wins_before_leased_immediate_provider_call(monkeypatch):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    school_id, teacher_id, event_id, row_id, now = _immediate_notification_world(Session)
    reversal_locked = Event()
    dispatcher_loaded = Event()
    allow_reversal_commit = Event()
    bridge = _RecordingBridgeProvider()
    original_revalidate = messaging_notification_dispatch.revalidate_family_notification

    def observed_revalidation(session, row):
        result = original_revalidate(session, row)
        if row.id == row_id:
            dispatcher_loaded.set()
        return result

    monkeypatch.setattr(
        messaging_notification_dispatch,
        "revalidate_family_notification",
        observed_revalidation,
    )

    def reverse():
        session = Session()
        try:
            actor = session.query(User).filter_by(id=teacher_id).one()
            event, _replay = reverse_event(
                session,
                school_id=school_id,
                event_id=event_id,
                actor=actor,
                reason="Incorrect award",
            )
            cancel_reversed_behaviour_event_notifications(session, event=event, now=event.reversed_at)
            reversal_locked.set()
            assert allow_reversal_commit.wait(timeout=5)
            session.commit()
        finally:
            session.close()

    def dispatch():
        session = Session()
        try:
            return dispatch_claimed_rows(
                session,
                row_ids=[row_id],
                worker_id="notification-dispatch-race",
                push_provider=_UnusedPushProvider(),
                bridge_provider=bridge,
                now=now + timedelta(seconds=1),
            )
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            reversal = executor.submit(reverse)
            assert reversal_locked.wait(timeout=5)
            delivery = executor.submit(dispatch)
            assert dispatcher_loaded.wait(timeout=5)
            allow_reversal_commit.set()
            reversal.result(timeout=10)
            assert delivery.result(timeout=10) == 1
        verify = Session()
        try:
            row = verify.query(NotificationOutbox).filter_by(id=row_id).one()
            assert bridge.calls == []
            assert row.state == "cancelled"
            assert row.provider_accepted_at is None
        finally:
            verify.close()
    finally:
        engine.dispose()


@pytest.mark.skipif(not DATABASE_URL, reason="requires disposable PostgreSQL database")
def test_provider_acceptance_commits_before_reversal_and_delivered_row_is_preserved():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    school_id, teacher_id, event_id, row_id, now = _immediate_notification_world(Session)
    bridge = _BlockingBridgeProvider()
    reversal_started = Event()

    def dispatch():
        session = Session()
        try:
            return dispatch_claimed_rows(
                session,
                row_ids=[row_id],
                worker_id="notification-dispatch-race",
                push_provider=_UnusedPushProvider(),
                bridge_provider=bridge,
                now=now + timedelta(seconds=1),
            )
        finally:
            session.close()

    def reverse():
        session = Session()
        try:
            actor = session.query(User).filter_by(id=teacher_id).one()
            reversal_started.set()
            event, _replay = reverse_event(
                session,
                school_id=school_id,
                event_id=event_id,
                actor=actor,
                reason="Incorrect award",
            )
            cancel_reversed_behaviour_event_notifications(session, event=event, now=event.reversed_at)
            session.commit()
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            delivery = executor.submit(dispatch)
            assert bridge.entered.wait(timeout=5)
            reversal = executor.submit(reverse)
            assert reversal_started.wait(timeout=5)
            bridge.release.set()
            assert delivery.result(timeout=10) == 1
            reversal.result(timeout=10)
        verify = Session()
        try:
            row = verify.query(NotificationOutbox).filter_by(id=row_id).one()
            event = verify.query(BehaviourEvent).filter_by(id=event_id).one()
            assert len(bridge.calls) == 1
            assert row.state == "provider_accepted"
            assert row.provider_accepted_at is not None
            assert row.last_error_code is None
            assert event.reversed_at is not None
        finally:
            verify.close()
    finally:
        engine.dispose()

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.messaging_service import send_text_message
from app.models_school import (
    Conversation,
    ConversationAccessGrant,
    ConversationParticipant,
    Membership,
    Message,
    School,
    SchoolMessagingPolicy,
    User,
)


DATABASE_URL = os.getenv("MESSAGING_TEST_DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="requires disposable PostgreSQL database")
def test_concurrent_sends_allocate_strict_monotonic_sequences():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    setup = Session()
    try:
        school = School(name="Concurrency", slug=f"concurrency-{uuid4()}", status="active")
        first_user = User(
            email=f"first-{uuid4()}@test", name="First", google_sub=f"first-{uuid4()}"
        )
        second_user = User(
            email=f"second-{uuid4()}@test", name="Second", google_sub=f"second-{uuid4()}"
        )
        setup.add_all([school, first_user, second_user])
        setup.flush()
        first_membership = Membership(
            school_id=school.id,
            user_id=first_user.id,
            role="teacher",
            status="active",
        )
        second_membership = Membership(
            school_id=school.id,
            user_id=second_user.id,
            role="teacher",
            status="active",
        )
        setup.add_all(
            [
                first_membership,
                second_membership,
                SchoolMessagingPolicy(school_id=school.id),
            ]
        )
        setup.flush()
        conversation = Conversation(
            school_id=school.id,
            kind="staff_direct",
            staff_membership_low_id=min(first_membership.id, second_membership.id),
            staff_membership_high_id=max(first_membership.id, second_membership.id),
        )
        setup.add(conversation)
        setup.flush()
        first_participant = ConversationParticipant(
            conversation_id=conversation.id,
            participant_kind="staff",
            user_id=first_user.id,
            membership_id=first_membership.id,
            side="staff",
            display_name_snapshot=first_user.name,
        )
        second_participant = ConversationParticipant(
            conversation_id=conversation.id,
            participant_kind="staff",
            user_id=second_user.id,
            membership_id=second_membership.id,
            side="staff",
            display_name_snapshot=second_user.name,
        )
        setup.add_all([first_participant, second_participant])
        setup.flush()
        setup.add_all(
            [
                ConversationAccessGrant(
                    conversation_id=conversation.id,
                    participant_id=first_participant.id,
                    source_type="school_admin_membership",
                    membership_id=first_membership.id,
                    grant_reason="staff_direct_membership",
                ),
                ConversationAccessGrant(
                    conversation_id=conversation.id,
                    participant_id=second_participant.id,
                    source_type="school_admin_membership",
                    membership_id=second_membership.id,
                    grant_reason="staff_direct_membership",
                ),
            ]
        )
        setup.commit()
        conversation_id = conversation.id
        participant_ids = (first_participant.id, second_participant.id)
    finally:
        setup.close()

    barrier = Barrier(2)

    def send(participant_id: int, body: str) -> int:
        session = Session()
        try:
            barrier.wait(timeout=5)
            message, _ = send_text_message(
                session,
                conversation_id=conversation_id,
                sender_participant_id=participant_id,
                client_message_id=uuid4(),
                body=body,
            )
            session.commit()
            return message.sequence
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(send, participant_ids[0], "One"),
            executor.submit(send, participant_ids[1], "Two"),
        ]
        assert sorted(future.result(timeout=10) for future in futures) == [1, 2]

    verify = Session()
    try:
        rows = (
            verify.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.sequence)
            .all()
        )
        assert [row.sequence for row in rows] == [1, 2]
        assert len({row.id for row in rows}) == 2
    finally:
        verify.close()
        engine.dispose()

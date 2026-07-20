import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.messaging_notifications import claim_notification_rows
from app.models_school import (
    Conversation,
    ConversationAccessGrant,
    ConversationParticipant,
    Membership,
    Message,
    NotificationOutbox,
    School,
    SchoolMessagingPolicy,
    User,
)


DATABASE_URL = os.getenv("MESSAGING_TEST_DATABASE_URL")
UTC = timezone.utc


@pytest.mark.skipif(not DATABASE_URL, reason="requires disposable PostgreSQL database")
def test_two_workers_claim_disjoint_outbox_rows_with_skip_locked():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    setup = Session()
    now = datetime(2026, 7, 20, 6, 0, tzinfo=UTC)
    try:
        school = School(
            name="Outbox concurrency",
            slug=f"outbox-concurrency-{uuid4()}",
            status="active",
        )
        first_user = User(
            email=f"outbox-first-{uuid4()}@test",
            name="First",
            google_sub=f"outbox-first-{uuid4()}",
        )
        second_user = User(
            email=f"outbox-second-{uuid4()}@test",
            name="Second",
            google_sub=f"outbox-second-{uuid4()}",
        )
        setup.add_all([school, first_user, second_user])
        setup.flush()
        first_membership = Membership(
            school_id=school.id,
            user_id=first_user.id,
            role="school_admin",
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
                SchoolMessagingPolicy(school_id=school.id, enabled=True),
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
        sender = ConversationParticipant(
            conversation_id=conversation.id,
            participant_kind="staff",
            user_id=first_user.id,
            membership_id=first_membership.id,
            side="staff",
            display_name_snapshot="First",
        )
        recipient = ConversationParticipant(
            conversation_id=conversation.id,
            participant_kind="chh_guardian",
            user_id=second_user.id,
            side="guardian",
            display_name_snapshot="Second",
        )
        setup.add_all([sender, recipient])
        setup.flush()
        setup.add(
            ConversationAccessGrant(
                conversation_id=conversation.id,
                participant_id=sender.id,
                source_type="school_admin_membership",
                membership_id=first_membership.id,
                grant_reason="test",
            )
        )
        message = Message(
            school_id=school.id,
            conversation_id=conversation.id,
            sequence=1,
            sender_participant_id=sender.id,
            sender_display_name_snapshot="First",
            client_message_id=uuid4(),
            body="Safe body is not copied into outbox",
            created_at=now,
        )
        setup.add(message)
        setup.flush()
        rows = []
        for channel in ("push", "email"):
            row = NotificationOutbox(
                school_id=school.id,
                message_id=message.id,
                recipient_kind="chh_user",
                recipient_user_id=second_user.id,
                recipient_participant_id=recipient.id,
                channel=channel,
                template_key="school_message.guardian",
                template_args={"message_id": str(message.public_id)},
                deep_link="/messages",
                policy_version=1,
                state="pending",
                eligible_at=now,
                scheduler_check_at=now,
                next_attempt_at=now,
                dedupe_key=f"postgres-claim:{message.id}:{channel}",
            )
            setup.add(row)
            rows.append(row)
        setup.commit()
        expected_ids = {row.id for row in rows}
    finally:
        setup.close()

    barrier = Barrier(2)

    def claim(worker_id: str) -> list[int]:
        session = Session()
        try:
            barrier.wait(timeout=5)
            return claim_notification_rows(
                session,
                worker_id=worker_id,
                limit=1,
                now=now,
            )
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            claims = [
                future.result(timeout=10)
                for future in (
                    executor.submit(claim, "worker-a"),
                    executor.submit(claim, "worker-b"),
                )
            ]
        assert all(len(result) == 1 for result in claims)
        assert {result[0] for result in claims} == expected_ids
    finally:
        engine.dispose()

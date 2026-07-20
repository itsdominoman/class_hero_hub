from __future__ import annotations

import os
import hashlib
import hmac
import json
from datetime import date, datetime, time, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.database import Base
from app.messaging_notifications import (
    ContactHoursConfiguration,
    claim_notification_rows,
    contact_hours_decision,
    enqueue_message_notifications,
    notification_timing_payload,
    reconcile_notification_rows,
)
from app.messaging_notification_dispatch import (
    ProviderError,
    SignedFhhBridgeProvider,
    claim_dispatch_rows,
    dispatch_claimed_rows,
    school_message_collapse_key,
)
from app.models_school import (
    Conversation,
    ConversationAccessGrant,
    ConversationParticipant,
    DevicePushRegistration,
    FhhLink,
    FhhLinkInvite,
    FhhMessagingIdentity,
    FhhMessagingIdentityLink,
    GuardianLink,
    Membership,
    Message,
    MessageMedia,
    MessageReceiptEvent,
    MessageVoiceMedia,
    NotificationDelivery,
    NotificationOutbox,
    School,
    SchoolContactException,
    SchoolContactWindow,
    SchoolMessagingPolicy,
    StaffMessagingPreference,
    Student,
    User,
)
from app.routes.notifications import (
    RegisterDeviceRequest,
    UnregisterDeviceRequest,
    notification_target,
    register_device,
    unregister_device,
)


UTC = timezone.utc
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine)


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(database.settings, "MESSAGING_ENABLED", True)
    monkeypatch.setattr(database.settings, "MESSAGING_NOTIFICATION_RECHECK_SECONDS", 300)
    monkeypatch.setattr(database.settings, "MESSAGING_NOTIFICATION_SCHEDULER_LEASE_SECONDS", 60)
    Base.metadata.create_all(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def _configuration(
    *,
    timezone_name: str = "Asia/Muscat",
    windows: dict[int, tuple[time, time]] | None = None,
    exceptions: dict[date, tuple[str, time | None, time | None]] | None = None,
    enabled: bool = True,
) -> ContactHoursConfiguration:
    school = SimpleNamespace(id=1, timezone=timezone_name)
    policy = SimpleNamespace(contact_hours_enabled=enabled)
    window_rows = {
        weekday: SimpleNamespace(
            weekday=weekday,
            start_local=value[0],
            end_local=value[1],
        )
        for weekday, value in (windows or {}).items()
    }
    exception_rows = {
        local_date: SimpleNamespace(
            local_date=local_date,
            kind=value[0],
            start_local=value[1],
            end_local=value[2],
        )
        for local_date, value in (exceptions or {}).items()
    }
    return ContactHoursConfiguration(
        school=school,
        policy=policy,
        windows=window_rows,
        exceptions=exception_rows,
        zone=ZoneInfo(timezone_name),
    )


def _muscat_week() -> dict[int, tuple[time, time]]:
    return {
        weekday: (time(7, 30), time(15, 0))
        for weekday in (1, 2, 3, 4, 7)
    }


def test_muscat_boundaries_and_weekend_next_window_are_utc_authoritative():
    configuration = _configuration(windows=_muscat_week())
    at_open = datetime(2026, 7, 19, 3, 30, tzinfo=UTC)  # Sunday 07:30
    before_close = datetime(2026, 7, 19, 10, 59, 59, tzinfo=UTC)
    at_close = datetime(2026, 7, 19, 11, 0, tzinfo=UTC)
    friday = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)

    assert contact_hours_decision(None, 1, at_utc=at_open, configuration=configuration).is_open
    assert contact_hours_decision(None, 1, at_utc=before_close, configuration=configuration).is_open
    closing = contact_hours_decision(None, 1, at_utc=at_close, configuration=configuration)
    weekend = contact_hours_decision(None, 1, at_utc=friday, configuration=configuration)
    assert not closing.is_open
    assert closing.eligible_at == datetime(2026, 7, 20, 3, 30, tzinfo=UTC)
    assert not weekend.is_open
    assert weekend.eligible_at == datetime(2026, 7, 26, 3, 30, tzinfo=UTC)


def test_exceptions_override_weekly_and_overnight_windows():
    closed_sunday = _configuration(
        windows=_muscat_week(),
        exceptions={date(2026, 7, 19): ("closed", None, None)},
    )
    decision = contact_hours_decision(
        None,
        1,
        at_utc=datetime(2026, 7, 19, 4, 0, tzinfo=UTC),
        configuration=closed_sunday,
    )
    assert not decision.is_open
    assert decision.eligible_at == datetime(2026, 7, 20, 3, 30, tzinfo=UTC)

    overnight = _configuration(windows={1: (time(22), time(2))})
    assert contact_hours_decision(
        None,
        1,
        at_utc=datetime(2026, 7, 20, 21, 0, tzinfo=UTC),  # Tuesday 01:00
        configuration=overnight,
    ).is_open
    overridden = _configuration(
        windows={1: (time(22), time(2))},
        exceptions={date(2026, 7, 21): ("closed", None, None)},
    )
    assert not contact_hours_decision(
        None,
        1,
        at_utc=datetime(2026, 7, 20, 21, 0, tzinfo=UTC),
        configuration=overridden,
    ).is_open


def test_dst_nonexistent_and_ambiguous_wall_times_are_deterministic():
    spring = _configuration(
        timezone_name="America/New_York",
        windows={7: (time(2, 30), time(4, 0))},
    )
    spring_decision = contact_hours_decision(
        None,
        1,
        at_utc=datetime(2026, 3, 8, 6, 55, tzinfo=UTC),
        configuration=spring,
    )
    assert not spring_decision.is_open
    assert spring_decision.eligible_at == datetime(2026, 3, 8, 7, 0, tzinfo=UTC)

    fall = _configuration(
        timezone_name="America/New_York",
        windows={7: (time(1, 30), time(2, 30))},
    )
    assert contact_hours_decision(
        None,
        1,
        at_utc=datetime(2026, 11, 1, 5, 45, tzinfo=UTC),
        configuration=fall,
    ).is_open
    assert contact_hours_decision(
        None,
        1,
        at_utc=datetime(2026, 11, 1, 6, 45, tzinfo=UTC),
        configuration=fall,
    ).is_open


def _world(db):
    school = School(
        name="Notification School",
        slug=f"notification-{uuid4()}",
        timezone="Asia/Muscat",
        status="active",
    )
    admin_user = User(
        email=f"admin-{uuid4()}@test",
        name="School Admin",
        google_sub=str(uuid4()),
    )
    guardian_user = User(
        email=f"guardian-{uuid4()}@test",
        name="Parent",
        google_sub=str(uuid4()),
    )
    db.add_all([school, admin_user, guardian_user])
    db.flush()
    membership = Membership(
        school_id=school.id,
        user_id=admin_user.id,
        role="school_admin",
        status="active",
    )
    student = Student(
        school_id=school.id,
        first_name="Student",
        last_name="Test",
        status="active",
    )
    policy = SchoolMessagingPolicy(
        school_id=school.id,
        enabled=True,
        contact_hours_enabled=True,
        policy_version=1,
    )
    db.add_all([membership, student, policy])
    db.flush()
    guardian_link = GuardianLink(
        school_id=school.id,
        student_id=student.id,
        user_id=guardian_user.id,
        relationship="guardian",
        display_name="Parent",
        status="active",
    )
    db.add(guardian_link)
    for weekday, (start_local, end_local) in _muscat_week().items():
        db.add(
            SchoolContactWindow(
                school_id=school.id,
                weekday=weekday,
                start_local=start_local,
                end_local=end_local,
            )
        )
    db.flush()
    conversation = Conversation(
        school_id=school.id,
        kind="guardian_direct",
        student_id=student.id,
        primary_staff_membership_id=membership.id,
        internal_guardian_user_id=guardian_user.id,
    )
    db.add(conversation)
    db.flush()
    staff = ConversationParticipant(
        conversation_id=conversation.id,
        participant_kind="staff",
        user_id=admin_user.id,
        membership_id=membership.id,
        side="staff",
        display_name_snapshot="School Admin",
    )
    guardian = ConversationParticipant(
        conversation_id=conversation.id,
        participant_kind="chh_guardian",
        user_id=guardian_user.id,
        side="guardian",
        display_name_snapshot="Parent",
    )
    db.add_all([staff, guardian])
    db.flush()
    db.add_all(
        [
            ConversationAccessGrant(
                conversation_id=conversation.id,
                participant_id=staff.id,
                source_type="school_admin_membership",
                membership_id=membership.id,
                grant_reason="conversation_created",
            ),
            ConversationAccessGrant(
                conversation_id=conversation.id,
                participant_id=guardian.id,
                source_type="guardian_link",
                guardian_link_id=guardian_link.id,
                grant_reason="conversation_created",
            ),
        ]
    )
    conversation.created_by_participant_id = guardian.id
    db.commit()
    return SimpleNamespace(
        school=school,
        policy=policy,
        admin_user=admin_user,
        membership=membership,
        guardian_link=guardian_link,
        conversation=conversation,
        staff=staff,
        guardian=guardian,
    )


def _message(db, world, *, sender, created_at, urgent=False):
    message = Message(
        school_id=world.school.id,
        conversation_id=world.conversation.id,
        sequence=world.conversation.last_message_sequence + 1,
        sender_participant_id=sender.id,
        sender_display_name_snapshot=sender.display_name_snapshot,
        client_message_id=uuid4(),
        body="Committed message",
        urgent=urgent,
        created_at=created_at,
    )
    db.add(message)
    db.flush()
    world.conversation.last_message_sequence = message.sequence
    world.conversation.last_message_at = created_at
    return message


def _fhh_direction_world(db):
    world = _world(db)
    world.policy.contact_hours_enabled = False
    teacher_user = User(
        email=f"direction-teacher-{uuid4()}@test",
        name="Direction Teacher",
        google_sub=str(uuid4()),
    )
    db.add(teacher_user)
    db.flush()
    teacher_membership = Membership(
        school_id=world.school.id,
        user_id=teacher_user.id,
        role="teacher",
        status="active",
    )
    alternate_admin_membership = Membership(
        school_id=world.school.id,
        user_id=teacher_user.id,
        role="school_admin",
        status="active",
    )
    db.add_all([teacher_membership, alternate_admin_membership])
    db.flush()
    invite = FhhLinkInvite(
        school_id=world.school.id,
        student_id=world.conversation.student_id,
        token_hash=f"direction-invite-{uuid4()}",
        display_code_last4="4312",
        expires_at=datetime.now(UTC) + timedelta(days=1),
        consumed_at=datetime.now(UTC),
        consumed_by="opaque-child",
        created_by_user_id=world.admin_user.id,
    )
    db.add(invite)
    db.flush()
    link = FhhLink(
        school_id=world.school.id,
        student_id=world.conversation.student_id,
        source_invite_id=invite.id,
        link_token_hash=f"direction-link-{uuid4()}",
        fhh_child_ref="opaque-child",
        status="active",
    )
    identities = [
        FhhMessagingIdentity(
            school_id=world.school.id,
            external_subject_ref=uuid4(),
            display_name=f"Verified Parent {index}",
            preferred_locale="en",
            status="active",
        )
        for index in (1, 2)
    ]
    db.add_all([link, *identities])
    db.flush()
    for identity in identities:
        db.add(
            FhhMessagingIdentityLink(
                school_id=world.school.id,
                fhh_link_id=link.id,
                identity_id=identity.id,
                status="active",
                sync_version=1,
            )
        )
    dual_guardian_link = GuardianLink(
        school_id=world.school.id,
        student_id=world.conversation.student_id,
        user_id=teacher_user.id,
        relationship="guardian",
        display_name="Direction Teacher",
        status="active",
    )
    db.add(dual_guardian_link)
    db.flush()
    conversation = Conversation(
        school_id=world.school.id,
        kind="student_staff",
        student_id=world.conversation.student_id,
        primary_staff_membership_id=teacher_membership.id,
    )
    db.add(conversation)
    db.flush()
    teacher = ConversationParticipant(
        conversation_id=conversation.id,
        participant_kind="staff",
        user_id=teacher_user.id,
        membership_id=teacher_membership.id,
        side="staff",
        display_name_snapshot="Direction Teacher",
    )
    alternate_admin = ConversationParticipant(
        conversation_id=conversation.id,
        participant_kind="staff",
        user_id=teacher_user.id,
        membership_id=alternate_admin_membership.id,
        side="staff",
        display_name_snapshot="Direction Teacher",
    )
    administrator = ConversationParticipant(
        conversation_id=conversation.id,
        participant_kind="staff",
        user_id=world.admin_user.id,
        membership_id=world.membership.id,
        side="staff",
        display_name_snapshot="School Admin",
    )
    parents = [
        ConversationParticipant(
            conversation_id=conversation.id,
            participant_kind="fhh_parent",
            external_participant_id=identity.id,
            side="guardian",
            display_name_snapshot=identity.display_name,
        )
        for identity in identities
    ]
    dual_guardian = ConversationParticipant(
        conversation_id=conversation.id,
        participant_kind="chh_guardian",
        user_id=teacher_user.id,
        side="guardian",
        display_name_snapshot="Direction Teacher",
    )
    db.add_all([teacher, alternate_admin, administrator, *parents, dual_guardian])
    db.flush()
    for participant, membership in (
        (teacher, teacher_membership),
        (alternate_admin, alternate_admin_membership),
        (administrator, world.membership),
    ):
        db.add(
            ConversationAccessGrant(
                conversation_id=conversation.id,
                participant_id=participant.id,
                source_type="school_admin_membership",
                membership_id=membership.id,
                grant_reason="direction_test",
            )
        )
    for parent in parents:
        db.add(
            ConversationAccessGrant(
                conversation_id=conversation.id,
                participant_id=parent.id,
                source_type="fhh_link",
                fhh_link_id=link.id,
                grant_reason="direction_test",
            )
        )
    db.add(
        ConversationAccessGrant(
            conversation_id=conversation.id,
            participant_id=dual_guardian.id,
            source_type="guardian_link",
            guardian_link_id=dual_guardian_link.id,
            grant_reason="direction_test",
        )
    )
    conversation.created_by_participant_id = parents[0].id
    db.add_all(
        [
            DevicePushRegistration(
                installation_id=uuid4(),
                user_id=user_id,
                platform="android",
                app_package="com.classherohub.app",
                locale="en",
                fcm_token=f"direction-staff-token-{index}-long-enough",
            )
            for index, user_id in enumerate(
                (teacher_user.id, world.admin_user.id),
                start=1,
            )
        ]
    )
    db.commit()
    return SimpleNamespace(
        school=world.school,
        policy=world.policy,
        admin_user=world.admin_user,
        membership=teacher_membership,
        conversation=conversation,
        teacher=teacher,
        alternate_admin=alternate_admin,
        administrator=administrator,
        parents=parents,
        dual_guardian=dual_guardian,
        link=link,
    )


def _set_message_shape(db, message, sender, kind):
    if kind == "text":
        return
    message.body = None
    if kind == "photo":
        db.add(
            MessageMedia(
                client_upload_id=uuid4(),
                school_id=message.school_id,
                conversation_id=message.conversation_id,
                message_id=message.id,
                uploaded_by_participant_id=sender.id,
                state="attached",
                full_storage_key="school-messaging/test/full.jpg",
                thumbnail_storage_key="school-messaging/test/thumb.jpg",
                content_type="image/jpeg",
                full_bytes=100,
                thumbnail_bytes=50,
                width=10,
                height=10,
                thumbnail_width=5,
                thumbnail_height=5,
                source_checksum_sha256="a" * 64,
                checksum_sha256="b" * 64,
                metadata_stripped=True,
                attached_at=message.created_at,
            )
        )
        return
    message.message_type = "voice_note"
    db.add(
        MessageVoiceMedia(
            client_upload_id=uuid4(),
            school_id=message.school_id,
            conversation_id=message.conversation_id,
            message_id=message.id,
            uploaded_by_participant_id=sender.id,
            state="attached",
            storage_key="school-messaging/test/voice.m4a",
            content_type="audio/mp4",
            size_bytes=100,
            duration_ms=1_000,
            codec="aac",
            container="mp4",
            source_checksum_sha256="c" * 64,
            checksum_sha256="d" * 64,
            metadata_stripped=True,
            attached_at=message.created_at,
        )
    )


class RecordingBridgeProvider:
    def __init__(self):
        self.calls = []

    def send(self, **kwargs):
        self.calls.append(kwargs)
        return f"bridge-ref-{len(self.calls)}"


@pytest.mark.parametrize("message_kind", ["text", "photo", "voice"])
def test_fhh_family_message_targets_staff_only_for_every_supported_media_kind(db, message_kind):
    world = _fhh_direction_world(db)
    now = datetime(2026, 7, 20, 8, 0, tzinfo=UTC)
    before_receipts = db.query(MessageReceiptEvent).count()
    before_access = {
        participant.id: (participant.last_delivered_sequence, participant.last_read_sequence)
        for participant in world.parents
    }
    message = _message(db, world, sender=world.parents[0], created_at=now)
    _set_message_shape(db, message, world.parents[0], message_kind)

    rows = enqueue_message_notifications(
        db,
        conversation=world.conversation,
        message=message,
        sender=world.parents[0],
        now=now,
    )
    db.commit()

    assert len(rows) == 2
    assert {row.recipient_kind for row in rows} == {"chh_user"}
    assert {row.recipient_user_id for row in rows} == {
        world.teacher.user_id,
        world.administrator.user_id,
    }
    assert db.query(NotificationOutbox).filter_by(message_id=message.id, recipient_kind="fhh_link").count() == 0
    assert len(world.parents) == 2
    assert all(parent.left_at is None for parent in world.parents)

    claimed = claim_dispatch_rows(
        db,
        worker_id=f"family-{message_kind}-dispatch",
        limit=10,
        now=now + timedelta(seconds=1),
    )
    push_provider = RecordingPushProvider()
    assert dispatch_claimed_rows(
        db,
        row_ids=claimed,
        worker_id=f"family-{message_kind}-dispatch",
        push_provider=push_provider,
        bridge_provider=UnusedBridgeProvider(),
        now=now + timedelta(seconds=1),
    ) == 2
    assert len(push_provider.calls) == 2
    assert {call["message_direction"] for call in push_provider.calls} == {"family_to_staff"}
    assert db.query(MessageReceiptEvent).count() == before_receipts
    assert {
        participant.id: (participant.last_delivered_sequence, participant.last_read_sequence)
        for participant in world.parents
    } == before_access


@pytest.mark.parametrize("staff_sender", ["teacher", "administrator"])
def test_staff_message_targets_one_family_bridge_and_never_staff_or_dual_role_self(db, staff_sender):
    world = _fhh_direction_world(db)
    sender = getattr(world, staff_sender)
    now = datetime(2026, 7, 20, 8, 0, tzinfo=UTC)
    before_receipts = db.query(MessageReceiptEvent).count()
    message = _message(db, world, sender=sender, created_at=now)

    rows = enqueue_message_notifications(
        db,
        conversation=world.conversation,
        message=message,
        sender=sender,
        now=now,
    )
    db.commit()

    assert len(rows) == 1
    assert rows[0].recipient_kind == "fhh_link"
    assert rows[0].recipient_fhh_link_id == world.link.id
    assert db.query(NotificationOutbox).filter_by(message_id=message.id, recipient_kind="chh_user").count() == 0

    claimed = claim_dispatch_rows(
        db,
        worker_id=f"staff-{staff_sender}-dispatch",
        limit=10,
        now=now + timedelta(seconds=1),
    )
    bridge = RecordingBridgeProvider()
    push_provider = RecordingPushProvider()
    assert dispatch_claimed_rows(
        db,
        row_ids=claimed,
        worker_id=f"staff-{staff_sender}-dispatch",
        push_provider=push_provider,
        bridge_provider=bridge,
        now=now + timedelta(seconds=1),
    ) == 1
    assert push_provider.calls == []
    assert len(bridge.calls) == 1
    assert bridge.calls[0]["message_direction"] == "staff_to_family"
    assert db.query(MessageReceiptEvent).count() == before_receipts


def test_preexisting_wrong_direction_family_bridge_rows_are_cancelled_and_not_retried(db):
    world = _fhh_direction_world(db)
    now = datetime(2026, 7, 20, 8, 0, tzinfo=UTC)
    message = _message(db, world, sender=world.parents[0], created_at=now)

    def wrong_row(suffix):
        return NotificationOutbox(
            event_id=uuid4(),
            school_id=world.school.id,
            message_id=message.id,
            recipient_kind="fhh_link",
            recipient_fhh_link_id=world.link.id,
            channel="push",
            template_key="school_message.guardian",
            template_args={"conversation_id": str(world.conversation.public_id)},
            deep_link="school_chat",
            policy_version=world.policy.policy_version,
            state="pending",
            eligible_at=now,
            scheduler_check_at=now,
            next_attempt_at=now,
            dedupe_key=f"wrong-direction-{message.id}-{suffix}",
        )

    dispatch_row = wrong_row("dispatch")
    db.add(dispatch_row)
    db.commit()
    claimed = claim_dispatch_rows(
        db,
        worker_id="wrong-direction-dispatch",
        limit=10,
        now=now,
    )
    assert dispatch_claimed_rows(
        db,
        row_ids=claimed,
        worker_id="wrong-direction-dispatch",
        push_provider=RecordingPushProvider(),
        bridge_provider=UnusedBridgeProvider(),
        now=now,
    ) == 1
    db.refresh(dispatch_row)
    assert dispatch_row.state == "cancelled"
    assert dispatch_row.last_error_code == "invalid_notification_direction"

    scheduler_row = wrong_row("scheduler")
    db.add(scheduler_row)
    db.commit()
    scheduler_claimed = claim_notification_rows(
        db,
        worker_id="wrong-direction-scheduler",
        limit=10,
        now=now,
    )
    reconcile_notification_rows(
        db,
        row_ids=scheduler_claimed,
        worker_id="wrong-direction-scheduler",
        now=now,
    )
    db.refresh(scheduler_row)
    assert scheduler_row.state == "cancelled"
    assert scheduler_row.last_error_code == "invalid_notification_direction"
    assert claim_dispatch_rows(
        db,
        worker_id="wrong-direction-retry",
        limit=10,
        now=now + timedelta(minutes=1),
    ) == []


class RecordingPushProvider:
    def __init__(self):
        self.calls = []

    def send(self, **kwargs):
        self.calls.append(kwargs)
        return f"provider-ref-{len(self.calls)}"


class UnusedBridgeProvider:
    def send(self, **_kwargs):
        raise AssertionError("FHH bridge was not expected")


def test_collapse_keys_are_direction_scoped():
    conversation_id = str(uuid4())
    assert school_message_collapse_key(conversation_id, "family_to_staff") != school_message_collapse_key(
        conversation_id,
        "staff_to_family",
    )
    assert "family-to-staff" in school_message_collapse_key(conversation_id, "family_to_staff")
    with pytest.raises(ProviderError, match="invalid_notification_direction"):
        school_message_collapse_key(conversation_id, "unknown")


def test_chh_device_account_switch_logout_and_opaque_tap_target_are_receipt_neutral(db):
    world = _world(db)
    installation_id = uuid4()
    request = RegisterDeviceRequest(
        installation_id=installation_id,
        platform="android",
        app_package="com.classherohub.app",
        locale="en",
        fcm_token="token-value-long-enough-for-registration-one",
    )
    assert register_device(request, current_user=world.admin_user, db=db) == {
        "status": "registered"
    }

    second_user = User(
        email=f"teacher-{uuid4()}@test",
        name="Second Teacher",
        google_sub=str(uuid4()),
    )
    db.add(second_user)
    db.flush()
    second_membership = Membership(
        school_id=world.school.id,
        user_id=second_user.id,
        role="teacher",
        status="active",
    )
    db.add(second_membership)
    db.commit()
    request.fcm_token = "token-value-long-enough-for-registration-two"
    register_device(request, current_user=second_user, db=db)
    row = db.query(DevicePushRegistration).filter_by(installation_id=installation_id).one()
    assert row.user_id == second_user.id
    assert row.state == "active"

    unregister_device(
        UnregisterDeviceRequest(
            installation_id=installation_id,
            app_package="com.classherohub.app",
            fcm_token="token-value-long-enough-for-registration-two",
        ),
        current_user=second_user,
        db=db,
    )
    db.refresh(row)
    assert row.state == "revoked"
    assert row.disabled_reason == "logout"

    sunday = datetime(2026, 7, 19, 4, 0, tzinfo=UTC)
    message = _message(db, world, sender=world.guardian, created_at=sunday)
    outbox = enqueue_message_notifications(
        db,
        conversation=world.conversation,
        message=message,
        sender=world.guardian,
        now=sunday,
    )[0]
    db.commit()
    before_receipts = db.query(MessageReceiptEvent).count()
    target = notification_target(outbox.event_id, current_user=world.admin_user, db=db)
    assert target == {
        "route_type": "school_chat",
        "conversation_id": str(world.conversation.public_id),
        "membership_id": world.membership.id,
    }
    assert db.query(MessageReceiptEvent).count() == before_receipts


def test_chh_dispatch_bundles_same_conversation_and_records_provider_acceptance(db):
    world = _world(db)
    world.policy.contact_hours_enabled = False
    registration = DevicePushRegistration(
        installation_id=uuid4(),
        user_id=world.membership.user_id,
        platform="android",
        app_package="com.classherohub.app",
        locale="ar",
        fcm_token="staff-device-token-long-enough-for-fcm",
    )
    db.add(registration)
    now = datetime(2026, 7, 19, 4, 0, tzinfo=UTC)
    rows = []
    for offset in (0, 1):
        message = _message(
            db,
            world,
            sender=world.guardian,
            created_at=now + timedelta(seconds=offset),
            urgent=bool(offset),
        )
        rows.extend(
            enqueue_message_notifications(
                db,
                conversation=world.conversation,
                message=message,
                sender=world.guardian,
                now=now + timedelta(seconds=offset),
            )
        )
    db.commit()
    claimed = claim_dispatch_rows(db, worker_id="notification-dispatch-test", limit=10, now=now + timedelta(seconds=2))
    assert set(claimed) == {row.id for row in rows}
    provider = RecordingPushProvider()
    assert dispatch_claimed_rows(
        db,
        row_ids=claimed,
        worker_id="notification-dispatch-test",
        push_provider=provider,
        bridge_provider=UnusedBridgeProvider(),
        now=now + timedelta(seconds=2),
    ) == 2
    assert len(provider.calls) == 1
    assert provider.calls[0]["event_id"] == str(rows[-1].event_id)
    assert provider.calls[0]["locale"] == "ar"
    assert provider.calls[0]["message_direction"] == "family_to_staff"
    assert db.query(NotificationDelivery).filter_by(state="provider_accepted").count() == 2
    assert db.query(NotificationOutbox).filter_by(state="provider_accepted").count() == 2


def test_signed_fhh_bridge_payload_is_minimal_replay_resistant_and_privacy_safe(monkeypatch):
    monkeypatch.setattr(database.settings, "FHH_NOTIFICATION_BRIDGE_URL", "https://dev.familyherohub.com/api/integrations/chh/school-message-notifications")
    monkeypatch.setattr(database.settings, "FHH_NOTIFICATION_SERVICE_TOKEN", "service-" + "t" * 56)
    monkeypatch.setattr(database.settings, "FHH_NOTIFICATION_HMAC_SECRET", "hmac-" + "h" * 59)
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {"status": "accepted"}

    def fake_post(url, *, content, headers, timeout):
        captured.update(url=url, content=content, headers=headers, timeout=timeout)
        return Response()

    from app import messaging_notification_dispatch

    monkeypatch.setattr(messaging_notification_dispatch.httpx, "post", fake_post)
    event_id = uuid4()
    conversation_id = uuid4()
    result = SignedFhhBridgeProvider().send(
        event_id=str(event_id),
        remote_link_id=917,
        conversation_id=str(conversation_id),
        urgent=False,
        occurred_at=datetime(2026, 7, 20, 12, 0, tzinfo=UTC),
        message_direction="staff_to_family",
    )
    assert result == "accepted"
    payload = json.loads(captured["content"])
    assert set(payload) == {
        "event_id",
        "route_type",
        "remote_link_id",
        "conversation_id",
        "message_direction",
        "urgent",
        "occurred_at",
    }
    assert payload["remote_link_id"] == 917
    assert payload["message_direction"] == "staff_to_family"
    rendered = captured["content"].decode()
    for forbidden in ("parent_id", "family_id", "fcm_token", "message_body"):
        assert forbidden not in rendered.lower()
    timestamp = captured["headers"]["X-CHH-Notification-Timestamp"]
    nonce = captured["headers"]["X-CHH-Notification-Nonce"]
    digest = hashlib.sha256(captured["content"]).hexdigest()
    expected = hmac.new(
        database.settings.FHH_NOTIFICATION_HMAC_SECRET.encode(),
        f"{timestamp}\n{nonce}\n{digest}".encode(),
        hashlib.sha256,
    ).hexdigest()
    assert nonce == str(event_id)
    assert hmac.compare_digest(captured["headers"]["X-CHH-Notification-Signature"], expected)


def test_parent_message_is_committed_while_only_staff_notification_is_held(db):
    world = _world(db)
    friday = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)
    message = _message(db, world, sender=world.guardian, created_at=friday)
    rows = enqueue_message_notifications(
        db,
        conversation=world.conversation,
        message=message,
        sender=world.guardian,
        now=friday,
    )
    db.commit()

    assert db.query(Message).filter(Message.id == message.id).one().body == "Committed message"
    assert len(rows) == 1
    assert rows[0].state == "held"
    assert rows[0].eligible_at.replace(tzinfo=UTC) == datetime(2026, 7, 26, 3, 30, tzinfo=UTC)
    assert "Committed message" not in str(rows[0].template_args)
    assert notification_timing_payload(
        db,
        message=message,
        school_timezone=world.school.timezone,
    )["staff_notification_held"] is True


def test_staff_opt_in_only_bypasses_when_school_policy_allows_it(db):
    world = _world(db)
    friday = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)
    preference = StaffMessagingPreference(
        membership_id=world.membership.id,
        school_id=world.school.id,
        out_of_hours_notifications_enabled=True,
    )
    db.add(preference)
    first = _message(db, world, sender=world.guardian, created_at=friday)
    first_row = enqueue_message_notifications(
        db,
        conversation=world.conversation,
        message=first,
        sender=world.guardian,
        now=friday,
    )[0]
    assert first_row.state == "held"

    world.policy.allow_staff_out_of_hours_opt_in = True
    second = _message(db, world, sender=world.guardian, created_at=friday)
    second_row = enqueue_message_notifications(
        db,
        conversation=world.conversation,
        message=second,
        sender=world.guardian,
        now=friday,
    )[0]
    assert second_row.state == "pending"


def test_authorised_urgent_message_bypasses_contact_hour_hold(db):
    world = _world(db)
    friday = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)
    message = _message(
        db,
        world,
        sender=world.guardian,
        created_at=friday,
        urgent=True,
    )

    row = enqueue_message_notifications(
        db,
        conversation=world.conversation,
        message=message,
        sender=world.guardian,
        now=friday,
    )[0]

    assert row.state == "pending"
    assert row.eligible_at == friday
    assert notification_timing_payload(
        db,
        message=message,
        school_timezone=world.school.timezone,
    )["staff_notification_held"] is False


def test_policy_change_releases_held_row_without_recalling_completed_rows(db):
    world = _world(db)
    friday = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)
    message = _message(db, world, sender=world.guardian, created_at=friday)
    row = enqueue_message_notifications(
        db,
        conversation=world.conversation,
        message=message,
        sender=world.guardian,
        now=friday,
    )[0]
    db.commit()
    world.policy.contact_hours_enabled = False
    world.policy.policy_version += 1
    db.commit()

    claimed = claim_notification_rows(
        db,
        worker_id="policy-worker",
        limit=10,
        now=friday + timedelta(minutes=1),
    )
    assert claimed == [row.id]
    assert reconcile_notification_rows(
        db,
        row_ids=claimed,
        worker_id="policy-worker",
        now=friday + timedelta(minutes=1),
    ) == 1
    db.refresh(row)
    assert row.state == "pending"
    assert row.policy_version == world.policy.policy_version

    row.state = "dispatched"
    row.dispatched_at = friday + timedelta(minutes=2)
    world.policy.contact_hours_enabled = True
    world.policy.policy_version += 1
    db.commit()
    assert claim_notification_rows(
        db,
        worker_id="policy-worker-2",
        limit=10,
        now=friday + timedelta(minutes=3),
    ) == []
    db.refresh(row)
    assert row.state == "dispatched"


def test_revoked_recipient_is_cancelled_and_expired_lease_is_recovered(db):
    world = _world(db)
    friday = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)
    message = _message(db, world, sender=world.guardian, created_at=friday)
    row = enqueue_message_notifications(
        db,
        conversation=world.conversation,
        message=message,
        sender=world.guardian,
        now=friday,
    )[0]
    row.scheduler_check_at = friday
    db.commit()

    first_claim = claim_notification_rows(
        db,
        worker_id="notification-scheduler-crashed-worker",
        limit=10,
        now=friday,
    )
    assert first_claim == [row.id]
    assert claim_notification_rows(
        db,
        worker_id="notification-scheduler-second-worker",
        limit=10,
        now=friday + timedelta(seconds=30),
    ) == []
    recovered = claim_notification_rows(
        db,
        worker_id="notification-scheduler-recovery-worker",
        limit=10,
        now=friday + timedelta(seconds=61),
    )
    assert recovered == [row.id]

    world.membership.status = "revoked"
    world.membership.revoked_at = friday + timedelta(seconds=61)
    db.commit()
    reconcile_notification_rows(
        db,
        row_ids=recovered,
        worker_id="notification-scheduler-recovery-worker",
        now=friday + timedelta(seconds=61),
    )
    db.refresh(row)
    assert row.state == "cancelled"
    assert row.last_error_code == "recipient_ineligible"


@pytest.mark.parametrize("blocked_by", ["school_suspension", "messaging_disabled"])
def test_school_suspension_and_messaging_disablement_cancel_undispatched_rows(
    db,
    blocked_by,
):
    world = _world(db)
    friday = datetime(2026, 7, 24, 8, 0, tzinfo=UTC)
    message = _message(db, world, sender=world.guardian, created_at=friday)
    row = enqueue_message_notifications(
        db,
        conversation=world.conversation,
        message=message,
        sender=world.guardian,
        now=friday,
    )[0]
    db.commit()
    if blocked_by == "school_suspension":
        world.school.status = "suspended"
    else:
        world.policy.enabled = False
        world.policy.policy_version += 1
    row.scheduler_check_at = friday
    db.commit()

    claimed = claim_notification_rows(
        db,
        worker_id=f"worker-{blocked_by}",
        limit=10,
        now=friday,
    )
    reconcile_notification_rows(
        db,
        row_ids=claimed,
        worker_id=f"worker-{blocked_by}",
        now=friday,
    )
    db.refresh(row)
    assert row.state == "cancelled"
    assert row.last_error_code == "messaging_disabled"

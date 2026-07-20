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
)
from app.models_school import (
    Conversation,
    ConversationAccessGrant,
    ConversationParticipant,
    DevicePushRegistration,
    GuardianLink,
    Membership,
    Message,
    MessageReceiptEvent,
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


class RecordingPushProvider:
    def __init__(self):
        self.calls = []

    def send(self, **kwargs):
        self.calls.append(kwargs)
        return f"provider-ref-{len(self.calls)}"


class UnusedBridgeProvider:
    def send(self, **_kwargs):
        raise AssertionError("FHH bridge was not expected")


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
    )
    assert result == "accepted"
    payload = json.loads(captured["content"])
    assert set(payload) == {
        "event_id",
        "route_type",
        "remote_link_id",
        "conversation_id",
        "urgent",
        "occurred_at",
    }
    assert payload["remote_link_id"] == 917
    rendered = captured["content"].decode()
    for forbidden in ("parent", "family", "fcm", "token", "message_body"):
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

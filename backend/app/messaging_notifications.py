from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from .database import settings
from .messaging_service import participant_sequence_access_map
from .models_school import (
    Conversation,
    ConversationAccessGrant,
    ConversationParticipant,
    FhhLink,
    Message,
    NotificationOutbox,
    School,
    SchoolContactException,
    SchoolContactWindow,
    SchoolMessagingPolicy,
    StaffMessagingPreference,
    User,
)


UTC = timezone.utc


class ContactHoursConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class ContactHoursConfiguration:
    school: School
    policy: SchoolMessagingPolicy
    windows: dict[int, SchoolContactWindow]
    exceptions: dict[date, SchoolContactException]
    zone: ZoneInfo


@dataclass(frozen=True)
class ContactHoursDecision:
    is_open: bool
    eligible_at: datetime
    school_timezone: str


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def load_contact_hours_configuration(
    db: Session,
    school_id: int,
) -> ContactHoursConfiguration:
    school = db.query(School).filter(School.id == school_id).first()
    if school is None:
        raise ContactHoursConfigurationError("School does not exist")
    policy = (
        db.query(SchoolMessagingPolicy)
        .filter(SchoolMessagingPolicy.school_id == school_id)
        .first()
    )
    if policy is None:
        policy = SchoolMessagingPolicy(school_id=school_id)
        db.add(policy)
        db.flush()
    try:
        zone = ZoneInfo(school.timezone)
    except ZoneInfoNotFoundError as exc:
        raise ContactHoursConfigurationError("School timezone is invalid") from exc
    windows = {
        row.weekday: row
        for row in db.query(SchoolContactWindow)
        .filter(SchoolContactWindow.school_id == school_id)
        .order_by(SchoolContactWindow.weekday)
        .all()
    }
    exceptions = {
        row.local_date: row
        for row in db.query(SchoolContactException)
        .filter(SchoolContactException.school_id == school_id)
        .order_by(SchoolContactException.local_date)
        .all()
    }
    return ContactHoursConfiguration(
        school=school,
        policy=policy,
        windows=windows,
        exceptions=exceptions,
        zone=zone,
    )


def _valid_instants(naive: datetime, zone: ZoneInfo) -> list[datetime]:
    instants: list[datetime] = []
    for fold in (0, 1):
        candidate = naive.replace(tzinfo=zone, fold=fold)
        instant = candidate.astimezone(UTC)
        if instant.astimezone(zone).replace(tzinfo=None) != naive:
            continue
        if instant not in instants:
            instants.append(instant)
    return sorted(instants)


def _resolve_wall_time(
    local_date: date,
    local_time: time,
    zone: ZoneInfo,
    *,
    opening: bool,
) -> datetime:
    naive = datetime.combine(local_date, local_time.replace(tzinfo=None))
    for minute in range(181):
        candidates = _valid_instants(naive + timedelta(minutes=minute), zone)
        if candidates:
            return candidates[0] if opening else candidates[-1]
    raise ContactHoursConfigurationError("Contact window cannot be resolved in the school timezone")


def _window_for_date(
    configuration: ContactHoursConfiguration,
    anchor_date: date,
) -> tuple[time, time] | None:
    exception = configuration.exceptions.get(anchor_date)
    if exception is not None:
        if exception.kind == "closed":
            return None
        if exception.start_local is None or exception.end_local is None:
            raise ContactHoursConfigurationError("Custom contact exception is incomplete")
        return exception.start_local, exception.end_local
    row = configuration.windows.get(anchor_date.isoweekday())
    return (row.start_local, row.end_local) if row is not None else None


def _interval_for_date(
    configuration: ContactHoursConfiguration,
    anchor_date: date,
) -> tuple[datetime, datetime] | None:
    window = _window_for_date(configuration, anchor_date)
    if window is None:
        return None
    start_local, end_local = window
    end_date = anchor_date + timedelta(days=1) if end_local <= start_local else anchor_date
    start = _resolve_wall_time(anchor_date, start_local, configuration.zone, opening=True)
    end = _resolve_wall_time(end_date, end_local, configuration.zone, opening=False)
    if end <= start:
        raise ContactHoursConfigurationError("Contact window resolves to an empty UTC interval")
    return start, end


def contact_hours_decision(
    db: Session,
    school_id: int,
    *,
    at_utc: datetime | None = None,
    configuration: ContactHoursConfiguration | None = None,
) -> ContactHoursDecision:
    at_utc = as_aware(at_utc or utc_now()).astimezone(UTC)
    configuration = configuration or load_contact_hours_configuration(db, school_id)
    timezone_name = configuration.school.timezone
    if not configuration.policy.contact_hours_enabled:
        return ContactHoursDecision(True, at_utc, timezone_name)
    if not configuration.windows:
        raise ContactHoursConfigurationError("Enabled contact hours require an open weekly window")

    local_date = at_utc.astimezone(configuration.zone).date()
    anchors = [local_date]
    # A date-specific exception is authoritative for that local date and blocks a
    # prior weekly/custom window from spilling into it.
    if local_date not in configuration.exceptions:
        anchors.append(local_date - timedelta(days=1))
    for anchor in anchors:
        interval = _interval_for_date(configuration, anchor)
        if interval is not None and interval[0] <= at_utc < interval[1]:
            return ContactHoursDecision(True, at_utc, timezone_name)

    next_opening: datetime | None = None
    for offset in range(0, 378):
        interval = _interval_for_date(configuration, local_date + timedelta(days=offset))
        if interval is None:
            continue
        opening = interval[0]
        if opening < at_utc:
            continue
        if next_opening is None or opening < next_opening:
            next_opening = opening
    if next_opening is None:
        raise ContactHoursConfigurationError("No future contact window is configured")
    return ContactHoursDecision(False, next_opening, timezone_name)


def _scheduler_check_at(now: datetime, eligible_at: datetime) -> datetime:
    next_safety_check = now + timedelta(
        seconds=settings.MESSAGING_NOTIFICATION_RECHECK_SECONDS
    )
    return min(eligible_at, next_safety_check) if eligible_at > now else next_safety_check


def message_notification_direction(
    conversation: Conversation,
    sender: ConversationParticipant,
) -> str | None:
    """Return the only push direction allowed for this committed message."""
    if conversation.kind == "staff_direct" and sender.side == "staff":
        return "staff_to_staff"
    if sender.side == "guardian":
        return "family_to_staff"
    if sender.side == "staff":
        return "staff_to_family"
    return None


def notification_recipient_allowed(
    conversation: Conversation,
    sender: ConversationParticipant,
    recipient: ConversationParticipant,
) -> bool:
    direction = message_notification_direction(conversation, sender)
    if direction is None:
        return False
    # Suppress the same authenticated CHH user even when they appear through a
    # second membership or the opposite guardian/staff participant context.
    if (
        sender.user_id is not None
        and recipient.user_id is not None
        and sender.user_id == recipient.user_id
    ):
        return False
    if direction == "staff_to_staff":
        return recipient.side == "staff"
    if direction == "family_to_staff":
        return recipient.side == "staff"
    return recipient.side == "guardian"


def enqueue_message_notifications(
    db: Session,
    *,
    conversation: Conversation,
    message: Message,
    sender: ConversationParticipant,
    now: datetime | None = None,
) -> list[NotificationOutbox]:
    now = as_aware(now or message.created_at or utc_now()).astimezone(UTC)
    configuration = load_contact_hours_configuration(db, conversation.school_id)
    participants = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.id != sender.id,
            ConversationParticipant.left_at.is_(None),
        )
        .order_by(ConversationParticipant.id)
        .all()
    )
    participants = [
        participant
        for participant in participants
        if notification_recipient_allowed(conversation, sender, participant)
    ]
    preferences = {
        row.membership_id: row
        for row in db.query(StaffMessagingPreference)
        .filter(
            StaffMessagingPreference.membership_id.in_(
                [row.membership_id for row in participants if row.membership_id is not None]
            )
        )
        .all()
    } if any(row.membership_id is not None for row in participants) else {}
    fhh_grants = (
        db.query(ConversationAccessGrant)
        .filter(
            ConversationAccessGrant.conversation_id == conversation.id,
            ConversationAccessGrant.participant_id.in_([row.id for row in participants]),
            ConversationAccessGrant.source_type == "fhh_link",
            ConversationAccessGrant.fhh_link_id.is_not(None),
            ConversationAccessGrant.revoked_at.is_(None),
        )
        .all()
        if participants
        else []
    )
    fhh_links_by_participant: dict[int, set[int]] = {}
    for grant in fhh_grants:
        fhh_links_by_participant.setdefault(grant.participant_id, set()).add(grant.fhh_link_id)

    decision = contact_hours_decision(
        db,
        conversation.school_id,
        at_utc=now,
        configuration=configuration,
    )
    rows: list[NotificationOutbox] = []
    seen_targets: set[tuple[str, int]] = set()
    direction = message_notification_direction(conversation, sender)
    for participant in participants:
        targets: list[tuple[str, int, int | None]] = []
        if (
            direction in {"family_to_staff", "staff_to_staff"}
            and participant.participant_kind == "staff"
            and participant.user_id is not None
        ):
            targets.append(("chh_user", participant.user_id, participant.id))
        elif direction == "staff_to_family" and participant.participant_kind == "fhh_parent":
            targets.extend(
                ("fhh_link", link_id, None)
                for link_id in sorted(fhh_links_by_participant.get(participant.id, set()))
            )
        for recipient_kind, recipient_id, participant_id in targets:
            target_key = (recipient_kind, recipient_id)
            if target_key in seen_targets:
                continue
            seen_targets.add(target_key)
            staff_opted_in = bool(
                participant.side == "staff"
                and participant.membership_id is not None
                and configuration.policy.allow_staff_out_of_hours_opt_in
                and preferences.get(participant.membership_id)
                and preferences[participant.membership_id].out_of_hours_notifications_enabled
            )
            delays_staff_notification = (
                sender.side == "guardian"
                and participant.side == "staff"
                and not message.urgent
                and configuration.policy.contact_hours_enabled
                and not decision.is_open
                and not staff_opted_in
            )
            eligible_at = decision.eligible_at if delays_staff_notification else now
            state = "held" if delays_staff_notification else "pending"
            row = NotificationOutbox(
                event_id=uuid4(),
                school_id=conversation.school_id,
                message_id=message.id,
                recipient_kind=recipient_kind,
                recipient_user_id=recipient_id if recipient_kind == "chh_user" else None,
                recipient_fhh_link_id=recipient_id if recipient_kind == "fhh_link" else None,
                recipient_participant_id=participant_id,
                channel="push",
                template_key=(
                    "school_message.staff"
                    if participant.side == "staff"
                    else "school_message.guardian"
                ),
                template_args={
                    "conversation_id": str(conversation.public_id),
                    "message_id": str(message.public_id),
                    "membership_id": participant.membership_id,
                },
                # This is an allowlisted route type, not a client-controlled URL.
                # Native clients resolve the opaque event_id through an authenticated
                # target endpoint before navigating.
                deep_link="school_chat",
                policy_version=configuration.policy.policy_version,
                state=state,
                eligible_at=eligible_at,
                scheduler_check_at=_scheduler_check_at(now, eligible_at),
                next_attempt_at=eligible_at,
                dedupe_key=f"message:{message.id}:{recipient_kind}:{recipient_id}:push",
            )
            db.add(row)
            rows.append(row)
    db.flush()
    return rows


def notification_timing_payload(
    db: Session,
    *,
    message: Message,
    school_timezone: str,
) -> dict:
    held = (
        db.query(NotificationOutbox)
        .join(
            ConversationParticipant,
            ConversationParticipant.id == NotificationOutbox.recipient_participant_id,
        )
        .filter(
            NotificationOutbox.message_id == message.id,
            NotificationOutbox.state == "held",
            ConversationParticipant.side == "staff",
        )
        .order_by(NotificationOutbox.eligible_at, NotificationOutbox.id)
        .first()
    )
    return {
        "staff_notification_held": held is not None,
        "next_eligible_at": held.eligible_at if held is not None else None,
        "school_timezone": school_timezone,
    }


def claim_notification_rows(
    db: Session,
    *,
    worker_id: str,
    limit: int,
    now: datetime | None = None,
) -> list[int]:
    now = as_aware(now or utc_now()).astimezone(UTC)
    rows = (
        db.query(NotificationOutbox)
        .join(
            SchoolMessagingPolicy,
            SchoolMessagingPolicy.school_id == NotificationOutbox.school_id,
        )
        .filter(
            or_(
                and_(
                    NotificationOutbox.state.in_(("held", "pending", "failed")),
                    or_(
                        NotificationOutbox.scheduler_check_at <= now,
                        NotificationOutbox.policy_version != SchoolMessagingPolicy.policy_version,
                    ),
                ),
                and_(
                    NotificationOutbox.state == "leased",
                    NotificationOutbox.lease_owner.like("notification-scheduler-%"),
                    NotificationOutbox.lease_expires_at < now,
                ),
            )
        )
        .order_by(NotificationOutbox.scheduler_check_at, NotificationOutbox.id)
        .with_for_update(of=NotificationOutbox, skip_locked=True)
        .limit(limit)
        .all()
    )
    lease_expires_at = now + timedelta(
        seconds=settings.MESSAGING_NOTIFICATION_SCHEDULER_LEASE_SECONDS
    )
    for row in rows:
        row.state = "leased"
        row.lease_owner = worker_id
        row.lease_expires_at = lease_expires_at
    row_ids = [row.id for row in rows]
    db.commit()
    return row_ids


def _cancel(row: NotificationOutbox, *, code: str, now: datetime) -> None:
    row.state = "cancelled"
    row.last_error_code = code
    row.completed_at = now
    row.lease_owner = None
    row.lease_expires_at = None


def reconcile_notification_rows(
    db: Session,
    *,
    row_ids: list[int],
    worker_id: str,
    now: datetime | None = None,
) -> int:
    if not row_ids:
        return 0
    now = as_aware(now or utc_now()).astimezone(UTC)
    rows = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.id.in_(row_ids),
            NotificationOutbox.state == "leased",
            NotificationOutbox.lease_owner == worker_id,
        )
        .order_by(NotificationOutbox.id)
        .all()
    )
    message_ids = {row.message_id for row in rows}
    messages = {
        row.id: row
        for row in db.query(Message).filter(Message.id.in_(message_ids)).all()
    }
    conversation_ids = {row.conversation_id for row in messages.values()}
    conversations = {
        row.id: row
        for row in db.query(Conversation).filter(Conversation.id.in_(conversation_ids)).all()
    }
    # Include FHH participants so a per-link target can be cancelled when every
    # individual grant on that link is revoked.
    participants = (
        db.query(ConversationParticipant)
        .filter(ConversationParticipant.conversation_id.in_(conversation_ids))
        .all()
        if conversation_ids
        else []
    )
    participants_by_id = {row.id: row for row in participants}
    access_map = participant_sequence_access_map(
        db,
        conversations=list(conversations.values()),
        participants=participants,
        now=now,
    )
    users = {
        row.id: row
        for row in db.query(User)
        .filter(User.id.in_([row.recipient_user_id for row in rows if row.recipient_user_id is not None]))
        .all()
    }
    fhh_links = {
        row.id: row
        for row in db.query(FhhLink)
        .filter(FhhLink.id.in_([row.recipient_fhh_link_id for row in rows if row.recipient_fhh_link_id is not None]))
        .all()
    }
    fhh_grants = (
        db.query(ConversationAccessGrant)
        .filter(
            ConversationAccessGrant.conversation_id.in_(conversation_ids),
            ConversationAccessGrant.source_type == "fhh_link",
            ConversationAccessGrant.fhh_link_id.in_(list(fhh_links)),
            ConversationAccessGrant.participant_id.is_not(None),
        )
        .all()
        if conversation_ids and fhh_links
        else []
    )
    fhh_participants_by_target: dict[tuple[int, int], set[int]] = {}
    for grant in fhh_grants:
        fhh_participants_by_target.setdefault(
            (grant.conversation_id, grant.fhh_link_id), set()
        ).add(grant.participant_id)

    school_ids = {row.school_id for row in rows}
    configurations = {
        school_id: load_contact_hours_configuration(db, school_id)
        for school_id in school_ids
    }
    preferences = {
        row.membership_id: row
        for row in db.query(StaffMessagingPreference)
        .filter(StaffMessagingPreference.school_id.in_(school_ids))
        .all()
    }

    for row in rows:
        message = messages.get(row.message_id)
        conversation = conversations.get(message.conversation_id) if message else None
        configuration = configurations.get(row.school_id)
        if message is None or conversation is None or configuration is None:
            _cancel(row, code="notification_target_missing", now=now)
            continue
        if (
            not settings.MESSAGING_ENABLED
            or not configuration.policy.enabled
            or configuration.school.status not in {"pending_setup", "active"}
        ):
            _cancel(row, code="messaging_disabled", now=now)
            continue
        if message.state != "active" or conversation.status != "active":
            _cancel(row, code="message_or_conversation_inactive", now=now)
            continue

        recipient: ConversationParticipant | None = None
        recipient_valid = False
        if row.recipient_kind == "chh_user":
            recipient = participants_by_id.get(row.recipient_participant_id)
            access = access_map.get(row.recipient_participant_id)
            user = users.get(row.recipient_user_id)
            recipient_valid = bool(
                recipient is not None
                and recipient.user_id == row.recipient_user_id
                and user is not None
                and user.status == "active"
                and access is not None
                and access.includes(int(message.sequence))
            )
        else:
            link = fhh_links.get(row.recipient_fhh_link_id)
            candidate_ids = fhh_participants_by_target.get(
                (conversation.id, row.recipient_fhh_link_id), set()
            )
            recipient_valid = bool(
                link is not None
                and link.school_id == row.school_id
                and link.status == "active"
                and link.revoked_at is None
                and any(
                    access_map.get(participant_id) is not None
                    and access_map[participant_id].includes(int(message.sequence))
                    for participant_id in candidate_ids
                )
            )
            recipient = next(
                (participants_by_id.get(participant_id) for participant_id in candidate_ids),
                None,
            )
        sender = participants_by_id.get(message.sender_participant_id)
        if sender is None:
            _cancel(row, code="sender_missing", now=now)
            continue
        # Classify an impossible direction before access validity so malformed
        # legacy rows receive the stable, actionable reason and are never retried.
        if recipient is not None and not notification_recipient_allowed(conversation, sender, recipient):
            _cancel(row, code="invalid_notification_direction", now=now)
            continue
        if not recipient_valid or recipient is None:
            _cancel(row, code="recipient_ineligible", now=now)
            continue
        decision = contact_hours_decision(
            db,
            row.school_id,
            at_utc=now,
            configuration=configuration,
        )
        preference = preferences.get(recipient.membership_id)
        staff_opted_in = bool(
            recipient.side == "staff"
            and configuration.policy.allow_staff_out_of_hours_opt_in
            and preference is not None
            and preference.out_of_hours_notifications_enabled
        )
        held = bool(
            sender.side == "guardian"
            and recipient.side == "staff"
            and not message.urgent
            and configuration.policy.contact_hours_enabled
            and not decision.is_open
            and not staff_opted_in
        )
        row.state = "held" if held else "pending"
        row.eligible_at = decision.eligible_at if held else now
        row.next_attempt_at = row.eligible_at
        row.scheduler_check_at = _scheduler_check_at(now, row.eligible_at)
        row.policy_version = configuration.policy.policy_version
        row.last_error_code = None
        row.completed_at = None
        row.lease_owner = None
        row.lease_expires_at = None
    db.commit()
    return len(rows)


def fail_notification_rows(
    db: Session,
    *,
    row_ids: list[int],
    worker_id: str,
    now: datetime | None = None,
) -> None:
    now = as_aware(now or utc_now()).astimezone(UTC)
    rows = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.id.in_(row_ids),
            NotificationOutbox.state == "leased",
            NotificationOutbox.lease_owner == worker_id,
        )
        .all()
    )
    for row in rows:
        row.attempt_count += 1
        row.lease_owner = None
        row.lease_expires_at = None
        row.last_error_code = "scheduler_error"
        if row.attempt_count >= settings.MESSAGING_NOTIFICATION_MAX_ATTEMPTS:
            row.state = "dead"
            row.completed_at = now
        else:
            delay = min(
                settings.MESSAGING_NOTIFICATION_RETRY_MAX_SECONDS,
                settings.MESSAGING_NOTIFICATION_RETRY_BASE_SECONDS
                * (2 ** max(row.attempt_count - 1, 0)),
            )
            row.state = "failed"
            row.scheduler_check_at = now + timedelta(seconds=delay)
            row.next_attempt_at = row.scheduler_check_at
    db.commit()


def process_notification_scheduler_batch(
    session_factory: Callable[[], Session],
    *,
    worker_id: str,
    limit: int | None = None,
    now: datetime | None = None,
) -> int:
    claim_db = session_factory()
    try:
        row_ids = claim_notification_rows(
            claim_db,
            worker_id=worker_id,
            limit=limit or settings.MESSAGING_NOTIFICATION_SCHEDULER_BATCH_SIZE,
            now=now,
        )
    finally:
        claim_db.close()
    if not row_ids:
        return 0
    work_db = session_factory()
    try:
        return reconcile_notification_rows(
            work_db,
            row_ids=row_ids,
            worker_id=worker_id,
            now=now,
        )
    except Exception:
        work_db.rollback()
        failure_db = session_factory()
        try:
            fail_notification_rows(
                failure_db,
                row_ids=row_ids,
                worker_id=worker_id,
                now=now,
            )
        finally:
            failure_db.close()
        raise
    finally:
        work_db.close()

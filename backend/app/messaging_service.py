from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from .models_school import (
    Conversation,
    ConversationAccessGrant,
    ConversationParticipant,
    FhhLink,
    FhhMessagingIdentity,
    FhhMessagingIdentityLink,
    GuardianLink,
    Membership,
    Message,
    MessagingAuditEvent,
    StaffAssignment,
)
from .rosters import resolve_rosters_for_students
from .school_scope import open_interval_expression


class MessagingAccessDenied(Exception):
    pass


class MessagingConflict(Exception):
    pass


class MessagingValidationError(Exception):
    pass


@dataclass(frozen=True)
class SequenceAccess:
    visible_from: int
    visible_through: int | None

    def includes(self, sequence: int) -> bool:
        return sequence >= self.visible_from and (
            self.visible_through is None or sequence <= self.visible_through
        )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _timestamp_grant_is_open(grant: ConversationAccessGrant, now: datetime) -> bool:
    valid_from = _as_aware(grant.valid_from)
    valid_to = _as_aware(grant.valid_to)
    revoked_at = _as_aware(grant.revoked_at)
    return (
        valid_from is not None
        and valid_from <= now
        and (valid_to is None or valid_to > now)
        and (revoked_at is None or revoked_at > now)
    )


def _membership_is_current(
    db: Session,
    *,
    membership_id: int,
    school_id: int,
) -> Membership | None:
    return (
        db.query(Membership)
        .filter(
            Membership.id == membership_id,
            Membership.school_id == school_id,
            Membership.status == "active",
            Membership.revoked_at.is_(None),
        )
        .first()
    )


def _assignment_targets_student(
    db: Session,
    *,
    assignment: StaffAssignment,
    conversation: Conversation,
    today: date,
) -> bool:
    if conversation.student_id is None:
        return False
    resolution = resolve_rosters_for_students(
        db,
        conversation.school_id,
        today,
        student_ids=[conversation.student_id],
    )
    section_ids = {
        row.id
        for row in resolution.class_sections_by_student.get(conversation.student_id, [])
    }
    subject_group_ids = {
        row["id"]
        for row in resolution.subject_groups_by_student.get(conversation.student_id, [])
        if row.get("id") is not None
    }
    return (
        assignment.class_section_id is not None
        and assignment.class_section_id in section_ids
    ) or (
        assignment.subject_group_id is not None
        and assignment.subject_group_id in subject_group_ids
    )


def _source_is_current(
    db: Session,
    *,
    conversation: Conversation,
    participant: ConversationParticipant,
    grant: ConversationAccessGrant,
    now: datetime,
) -> bool:
    today = now.date()
    if grant.source_type == "staff_assignment":
        if participant.participant_kind != "staff" or participant.membership_id is None:
            return False
        membership = _membership_is_current(
            db,
            membership_id=participant.membership_id,
            school_id=conversation.school_id,
        )
        if membership is None or membership.role != "teacher":
            return False
        assignment = (
            db.query(StaffAssignment)
            .filter(
                StaffAssignment.id == grant.staff_assignment_id,
                StaffAssignment.school_id == conversation.school_id,
                StaffAssignment.membership_id == participant.membership_id,
                *open_interval_expression(StaffAssignment, today),
            )
            .first()
        )
        return assignment is not None and _assignment_targets_student(
            db,
            assignment=assignment,
            conversation=conversation,
            today=today,
        )

    if grant.source_type == "school_admin_membership":
        if participant.participant_kind != "staff" or participant.membership_id is None:
            return False
        membership = _membership_is_current(
            db,
            membership_id=participant.membership_id,
            school_id=conversation.school_id,
        )
        if membership is None or membership.id != grant.membership_id:
            return False
        if membership.role == "school_admin":
            return True
        # The approved ledger has a single membership-backed source value.
        # A current teacher membership may use it only for a staff-direct
        # conversation; student access remains assignment-backed.
        return conversation.kind == "staff_direct" and membership.role == "teacher"

    if grant.source_type == "guardian_link":
        if participant.participant_kind != "chh_guardian" or participant.user_id is None:
            return False
        guardian_link = (
            db.query(GuardianLink)
            .filter(
                GuardianLink.id == grant.guardian_link_id,
                GuardianLink.school_id == conversation.school_id,
                GuardianLink.user_id == participant.user_id,
                GuardianLink.status == "active",
                GuardianLink.revoked_at.is_(None),
            )
            .first()
        )
        if guardian_link is None:
            return False
        return (
            conversation.student_id is None
            or guardian_link.student_id == conversation.student_id
        )

    if grant.source_type == "fhh_link":
        if (
            participant.participant_kind != "fhh_parent"
            or participant.external_participant_id is None
        ):
            return False
        fhh_link = (
            db.query(FhhLink)
            .filter(
                FhhLink.id == grant.fhh_link_id,
                FhhLink.school_id == conversation.school_id,
                FhhLink.status == "active",
                FhhLink.revoked_at.is_(None),
            )
            .first()
        )
        if fhh_link is None or (
            conversation.student_id is not None
            and fhh_link.student_id != conversation.student_id
        ):
            return False
        identity = (
            db.query(FhhMessagingIdentity)
            .filter(
                FhhMessagingIdentity.id == participant.external_participant_id,
                FhhMessagingIdentity.school_id == conversation.school_id,
                FhhMessagingIdentity.status == "active",
            )
            .first()
        )
        identity_link = (
            db.query(FhhMessagingIdentityLink)
            .filter(
                FhhMessagingIdentityLink.school_id == conversation.school_id,
                FhhMessagingIdentityLink.fhh_link_id == fhh_link.id,
                FhhMessagingIdentityLink.identity_id == participant.external_participant_id,
                FhhMessagingIdentityLink.status == "active",
            )
            .first()
        )
        return identity is not None and identity_link is not None

    # Manual grants can extend a valid source grant's history but never create
    # ordinary access by themselves.
    return False


def participant_sequence_access(
    db: Session,
    *,
    conversation: Conversation,
    participant: ConversationParticipant,
    now: datetime | None = None,
) -> SequenceAccess:
    now = now or _utc_now()
    if (
        participant.conversation_id != conversation.id
        or participant.left_at is not None
    ):
        raise MessagingAccessDenied("Participant access is no longer active")

    grants = (
        db.query(ConversationAccessGrant)
        .filter(
            ConversationAccessGrant.conversation_id == conversation.id,
            ConversationAccessGrant.participant_id == participant.id,
        )
        .order_by(ConversationAccessGrant.id)
        .all()
    )
    current_source_grants = [
        grant
        for grant in grants
        if grant.source_type != "manual_history_grant"
        and _timestamp_grant_is_open(grant, now)
        and _source_is_current(
            db,
            conversation=conversation,
            participant=participant,
            grant=grant,
            now=now,
        )
    ]
    if not current_source_grants:
        raise MessagingAccessDenied("Current messaging authorization is no longer valid")

    visible_from = min(grant.visible_from_sequence for grant in current_source_grants)
    if any(grant.visible_through_sequence is None for grant in current_source_grants):
        visible_through = None
    else:
        visible_through = max(
            int(grant.visible_through_sequence) for grant in current_source_grants
        )

    manual_grants = [
        grant
        for grant in grants
        if grant.source_type == "manual_history_grant"
        and _timestamp_grant_is_open(grant, now)
    ]
    if manual_grants:
        visible_from = min(
            [visible_from, *(grant.visible_from_sequence for grant in manual_grants)]
        )
        if any(grant.visible_through_sequence is None for grant in manual_grants):
            visible_through = None
        elif visible_through is not None:
            visible_through = max(
                [
                    visible_through,
                    *(int(grant.visible_through_sequence) for grant in manual_grants),
                ]
            )

    return SequenceAccess(
        visible_from=visible_from,
        visible_through=visible_through,
    )


def assert_participant_can_send(
    db: Session,
    *,
    conversation: Conversation,
    participant: ConversationParticipant,
    now: datetime | None = None,
) -> SequenceAccess:
    if conversation.status != "active":
        raise MessagingAccessDenied("Conversation is read-only")
    access = participant_sequence_access(
        db,
        conversation=conversation,
        participant=participant,
        now=now,
    )
    if (
        conversation.kind in {"student_staff", "guardian_direct"}
        and participant.side == "guardian"
    ):
        # The route layer also returns the school policy capability. Keeping
        # guardian reply policy enforcement in the core service prevents a
        # later integration route from bypassing it.
        from .models_school import SchoolMessagingPolicy

        policy = (
            db.query(SchoolMessagingPolicy)
            .filter(SchoolMessagingPolicy.school_id == conversation.school_id)
            .first()
        )
        if policy is None or not policy.guardian_replies_enabled:
            raise MessagingAccessDenied("Guardian replies are disabled")
    return access


def record_messaging_audit(
    db: Session,
    *,
    school_id: int,
    event_type: str,
    participant: ConversationParticipant | None = None,
    conversation_id: int | None = None,
    message_id: int | None = None,
    detail: dict | None = None,
    request_correlation_id: str | None = None,
) -> MessagingAuditEvent:
    actor_kind = "system"
    actor_user_id = None
    actor_membership_id = None
    actor_external_participant_id = None
    participant_id = None
    if participant is not None:
        participant_id = participant.id
        actor_kind = participant.participant_kind
        actor_user_id = participant.user_id
        actor_membership_id = participant.membership_id
        actor_external_participant_id = participant.external_participant_id
    row = MessagingAuditEvent(
        school_id=school_id,
        actor_kind=actor_kind,
        actor_user_id=actor_user_id,
        actor_membership_id=actor_membership_id,
        actor_external_participant_id=actor_external_participant_id,
        event_type=event_type,
        conversation_id=conversation_id,
        message_id=message_id,
        participant_id=participant_id,
        detail=detail or {},
        request_correlation_id=request_correlation_id,
    )
    db.add(row)
    db.flush()
    return row


def normalize_message_body(body: str) -> str:
    normalized = body.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise MessagingValidationError("Message text is required")
    if len(normalized) > 10_000:
        raise MessagingValidationError("Message text is too long")
    return normalized


def send_text_message(
    db: Session,
    *,
    conversation_id: int,
    sender_participant_id: int,
    client_message_id: UUID,
    body: str,
    urgent: bool = False,
    request_correlation_id: str | None = None,
) -> tuple[Message, bool]:
    normalized_body = normalize_message_body(body)
    existing = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.sender_participant_id == sender_participant_id,
            Message.client_message_id == client_message_id,
        )
        .first()
    )
    if existing is not None:
        if existing.body != normalized_body or bool(existing.urgent) != bool(urgent):
            raise MessagingConflict("Client message id was reused with different content")
        return existing, True

    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id)
        .with_for_update()
        .first()
    )
    participant = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.id == sender_participant_id,
            ConversationParticipant.conversation_id == conversation_id,
        )
        .first()
    )
    if conversation is None or participant is None:
        raise MessagingAccessDenied("Conversation is unavailable")
    assert_participant_can_send(
        db,
        conversation=conversation,
        participant=participant,
    )

    # Repeat after the row lock so two retries cannot both insert.
    existing = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.sender_participant_id == sender_participant_id,
            Message.client_message_id == client_message_id,
        )
        .first()
    )
    if existing is not None:
        if existing.body != normalized_body or bool(existing.urgent) != bool(urgent):
            raise MessagingConflict("Client message id was reused with different content")
        return existing, True

    sequence = int(conversation.last_message_sequence or 0) + 1
    message = Message(
        school_id=conversation.school_id,
        conversation_id=conversation.id,
        sequence=sequence,
        sender_participant_id=participant.id,
        sender_display_name_snapshot=participant.display_name_snapshot,
        client_message_id=client_message_id,
        body=normalized_body,
        urgent=urgent,
    )
    db.add(message)
    db.flush()
    conversation.last_message_sequence = sequence
    conversation.last_message_at = message.created_at or _utc_now()
    record_messaging_audit(
        db,
        school_id=conversation.school_id,
        event_type="message.sent",
        participant=participant,
        conversation_id=conversation.id,
        message_id=message.id,
        detail={"sequence": sequence, "urgent": bool(urgent)},
        request_correlation_id=request_correlation_id,
    )
    return message, False

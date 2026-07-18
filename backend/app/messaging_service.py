from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import or_
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
    MessageReceiptEvent,
    MessagingAuditEvent,
    StaffAssignment,
)
from .message_media_service import (
    MessageMediaConflict,
    MessageMediaValidationError,
    attach_staged_media,
    attached_media_map,
)
from .message_voice_service import (
    MessageVoiceConflict,
    attach_staged_voice,
    attached_voice_map,
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
                FhhMessagingIdentityLink.revoked_at.is_(None),
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


def participant_sequence_access_map(
    db: Session,
    *,
    conversations: list[Conversation],
    participants: list[ConversationParticipant],
    now: datetime | None = None,
) -> dict[int, SequenceAccess]:
    """Resolve many participant grants with bounded, set-based source loading."""

    now = now or _utc_now()
    conversations_by_id = {row.id: row for row in conversations}
    active_participants = [
        row
        for row in participants
        if row.left_at is None and row.conversation_id in conversations_by_id
    ]
    if not active_participants:
        return {}

    participant_ids = [row.id for row in active_participants]
    grants = (
        db.query(ConversationAccessGrant)
        .filter(ConversationAccessGrant.participant_id.in_(participant_ids))
        .order_by(ConversationAccessGrant.id)
        .all()
    )
    membership_ids = {
        value
        for row in active_participants
        for value in (row.membership_id,)
        if value is not None
    } | {row.membership_id for row in grants if row.membership_id is not None}
    memberships_by_id = {
        row.id: row
        for row in (
            db.query(Membership).filter(Membership.id.in_(membership_ids)).all()
            if membership_ids
            else []
        )
    }
    assignment_ids = {
        row.staff_assignment_id
        for row in grants
        if row.staff_assignment_id is not None
    }
    assignments_by_id = {
        row.id: row
        for row in (
            db.query(StaffAssignment)
            .filter(StaffAssignment.id.in_(assignment_ids))
            .all()
            if assignment_ids
            else []
        )
    }
    guardian_link_ids = {
        row.guardian_link_id for row in grants if row.guardian_link_id is not None
    }
    guardian_links_by_id = {
        row.id: row
        for row in (
            db.query(GuardianLink).filter(GuardianLink.id.in_(guardian_link_ids)).all()
            if guardian_link_ids
            else []
        )
    }
    fhh_link_ids = {row.fhh_link_id for row in grants if row.fhh_link_id is not None}
    fhh_links_by_id = {
        row.id: row
        for row in (
            db.query(FhhLink).filter(FhhLink.id.in_(fhh_link_ids)).all()
            if fhh_link_ids
            else []
        )
    }
    external_identity_ids = {
        row.external_participant_id
        for row in active_participants
        if row.external_participant_id is not None
    }
    identities_by_id = {
        row.id: row
        for row in (
            db.query(FhhMessagingIdentity)
            .filter(FhhMessagingIdentity.id.in_(external_identity_ids))
            .all()
            if external_identity_ids
            else []
        )
    }
    identity_links = (
        db.query(FhhMessagingIdentityLink)
        .filter(
            FhhMessagingIdentityLink.fhh_link_id.in_(fhh_link_ids),
            FhhMessagingIdentityLink.identity_id.in_(external_identity_ids),
        )
        .all()
        if fhh_link_ids and external_identity_ids
        else []
    )
    active_identity_link_pairs = {
        (row.fhh_link_id, row.identity_id)
        for row in identity_links
        if row.status == "active" and row.revoked_at is None
    }
    student_ids = {
        row.student_id for row in conversations if row.student_id is not None
    }
    resolutions_by_school: dict[int, object] = {}
    for school_id in {row.school_id for row in conversations if row.student_id is not None}:
        school_student_ids = {
            row.student_id
            for row in conversations
            if row.school_id == school_id and row.student_id is not None
        }
        resolutions_by_school[school_id] = resolve_rosters_for_students(
            db, school_id, now.date(), student_ids=school_student_ids
        )

    participant_by_id = {row.id: row for row in active_participants}
    current_by_participant: dict[int, list[ConversationAccessGrant]] = {}
    manual_by_participant: dict[int, list[ConversationAccessGrant]] = {}
    for grant in grants:
        participant = participant_by_id.get(grant.participant_id)
        if participant is None or not _timestamp_grant_is_open(grant, now):
            continue
        conversation = conversations_by_id[participant.conversation_id]
        if grant.source_type == "manual_history_grant":
            manual_by_participant.setdefault(participant.id, []).append(grant)
            continue

        source_is_current = False
        if grant.source_type == "staff_assignment":
            membership = memberships_by_id.get(participant.membership_id)
            assignment = assignments_by_id.get(grant.staff_assignment_id)
            resolution = resolutions_by_school.get(conversation.school_id)
            if (
                participant.participant_kind == "staff"
                and membership is not None
                and membership.school_id == conversation.school_id
                and membership.role == "teacher"
                and membership.status == "active"
                and membership.revoked_at is None
                and assignment is not None
                and assignment.school_id == conversation.school_id
                and assignment.membership_id == participant.membership_id
                and assignment.valid_from <= now.date()
                and (assignment.valid_to is None or assignment.valid_to > now.date())
                and conversation.student_id is not None
                and resolution is not None
            ):
                section_ids = {
                    row.id
                    for row in resolution.class_sections_by_student.get(
                        conversation.student_id, []
                    )
                }
                group_ids = {
                    row["id"]
                    for row in resolution.subject_groups_by_student.get(
                        conversation.student_id, []
                    )
                    if row.get("id") is not None
                }
                source_is_current = (
                    assignment.class_section_id in section_ids
                    if assignment.class_section_id is not None
                    else assignment.subject_group_id in group_ids
                )
        elif grant.source_type == "school_admin_membership":
            membership = memberships_by_id.get(grant.membership_id)
            source_is_current = (
                participant.participant_kind == "staff"
                and membership is not None
                and membership.id == participant.membership_id
                and membership.school_id == conversation.school_id
                and membership.status == "active"
                and membership.revoked_at is None
                and (
                    membership.role == "school_admin"
                    or (
                        conversation.kind == "staff_direct"
                        and membership.role == "teacher"
                    )
                )
            )
        elif grant.source_type == "guardian_link":
            link = guardian_links_by_id.get(grant.guardian_link_id)
            source_is_current = (
                participant.participant_kind == "chh_guardian"
                and link is not None
                and link.school_id == conversation.school_id
                and link.user_id == participant.user_id
                and link.status == "active"
                and link.revoked_at is None
                and (
                    conversation.student_id is None
                    or link.student_id == conversation.student_id
                )
            )
        elif grant.source_type == "fhh_link":
            link = fhh_links_by_id.get(grant.fhh_link_id)
            identity = identities_by_id.get(participant.external_participant_id)
            source_is_current = (
                participant.participant_kind == "fhh_parent"
                and link is not None
                and link.school_id == conversation.school_id
                and link.status == "active"
                and link.revoked_at is None
                and (
                    conversation.student_id is None
                    or link.student_id == conversation.student_id
                )
                and identity is not None
                and identity.school_id == conversation.school_id
                and identity.status == "active"
                and (
                    link.id,
                    participant.external_participant_id,
                )
                in active_identity_link_pairs
            )
        if source_is_current:
            current_by_participant.setdefault(participant.id, []).append(grant)

    access_by_participant: dict[int, SequenceAccess] = {}
    for participant in active_participants:
        current = current_by_participant.get(participant.id, [])
        if not current:
            continue
        visible_from = min(row.visible_from_sequence for row in current)
        visible_through = (
            None
            if any(row.visible_through_sequence is None for row in current)
            else max(int(row.visible_through_sequence) for row in current)
        )
        manual = manual_by_participant.get(participant.id, [])
        if manual:
            visible_from = min(
                [visible_from, *(row.visible_from_sequence for row in manual)]
            )
            if any(row.visible_through_sequence is None for row in manual):
                visible_through = None
            elif visible_through is not None:
                visible_through = max(
                    [
                        visible_through,
                        *(int(row.visible_through_sequence) for row in manual),
                    ]
                )
        access_by_participant[participant.id] = SequenceAccess(
            visible_from=visible_from,
            visible_through=visible_through,
        )
    return access_by_participant


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


def normalize_optional_message_body(body: str | None) -> str | None:
    if body is None:
        return None
    normalized = body.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return None
    if len(normalized) > 10_000:
        raise MessagingValidationError("Message text is too long")
    return normalized


def _existing_message_matches(
    db: Session,
    *,
    existing: Message,
    body: str | None,
    urgent: bool,
    staged_media_ids: list[UUID],
    staged_voice_id: UUID | None,
) -> bool:
    if existing.body != body or bool(existing.urgent) != bool(urgent):
        return False
    if existing.message_type != ("voice_note" if staged_voice_id else "standard"):
        return False
    attached = attached_media_map(db, [existing.id]).get(existing.id, [])
    if [row.public_id for row in attached] != staged_media_ids:
        return False
    voice = attached_voice_map(db, [existing.id]).get(existing.id)
    return (voice.public_id if voice else None) == staged_voice_id


def send_message(
    db: Session,
    *,
    conversation_id: int,
    sender_participant_id: int,
    client_message_id: UUID,
    body: str | None,
    staged_media_ids: list[UUID] | None = None,
    staged_voice_id: UUID | None = None,
    urgent: bool = False,
    request_correlation_id: str | None = None,
) -> tuple[Message, bool]:
    normalized_body = normalize_optional_message_body(body)
    media_ids = list(staged_media_ids or [])
    if len(set(media_ids)) != len(media_ids):
        raise MessagingValidationError("A photo can be attached only once")
    if len(media_ids) > 5:
        raise MessagingValidationError("Maximum 5 photos")
    if staged_voice_id is not None and (normalized_body is not None or media_ids):
        raise MessagingValidationError("A voice note must be sent as its own message")
    if staged_voice_id is not None and urgent:
        raise MessagingValidationError("A voice note cannot be marked urgent")
    if normalized_body is None and not media_ids and staged_voice_id is None:
        raise MessagingValidationError("Message text, a photo, or a voice note is required")
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
        if not _existing_message_matches(
            db,
            existing=existing,
            body=normalized_body,
            urgent=urgent,
            staged_media_ids=media_ids,
            staged_voice_id=staged_voice_id,
        ):
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
        if not _existing_message_matches(
            db,
            existing=existing,
            body=normalized_body,
            urgent=urgent,
            staged_media_ids=media_ids,
            staged_voice_id=staged_voice_id,
        ):
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
        message_type="voice_note" if staged_voice_id else "standard",
        body=normalized_body,
        urgent=urgent,
    )
    db.add(message)
    db.flush()
    try:
        attach_staged_media(
            db,
            conversation=conversation,
            participant=participant,
            message=message,
            staged_media_ids=media_ids,
        )
    except MessageMediaValidationError as exc:
        raise MessagingValidationError(str(exc)) from exc
    except MessageMediaConflict as exc:
        raise MessagingConflict(str(exc)) from exc
    if staged_voice_id is not None:
        try:
            attach_staged_voice(
                db,
                conversation=conversation,
                participant=participant,
                message=message,
                staged_voice_id=staged_voice_id,
            )
        except MessageVoiceConflict as exc:
            raise MessagingConflict(str(exc)) from exc
    conversation.last_message_sequence = sequence
    conversation.last_message_at = message.created_at or _utc_now()
    participant.last_delivered_sequence = max(
        int(participant.last_delivered_sequence or 0), sequence
    )
    participant.last_delivered_at = message.created_at or _utc_now()
    participant.last_read_sequence = max(
        int(participant.last_read_sequence or 0), sequence
    )
    participant.last_read_at = message.created_at or _utc_now()
    record_messaging_audit(
        db,
        school_id=conversation.school_id,
        event_type="message.sent",
        participant=participant,
        conversation_id=conversation.id,
        message_id=message.id,
        detail={
            "sequence": sequence,
            "urgent": bool(urgent),
            "photo_count": len(media_ids),
            "voice_note": staged_voice_id is not None,
        },
        request_correlation_id=request_correlation_id,
    )
    return message, False


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
    """Compatibility wrapper for the Slice 3 text-only service contract."""
    return send_message(
        db,
        conversation_id=conversation_id,
        sender_participant_id=sender_participant_id,
        client_message_id=client_message_id,
        body=normalize_message_body(body),
        staged_media_ids=[],
        staged_voice_id=None,
        urgent=urgent,
        request_correlation_id=request_correlation_id,
    )


def acknowledge_messages(
    db: Session,
    *,
    conversation: Conversation,
    participant: ConversationParticipant,
    event_type: str,
    through_sequence: int,
    client_ack_id: UUID,
    occurred_at: datetime,
    device_session_ref: str | None = None,
) -> tuple[MessageReceiptEvent, bool]:
    if event_type not in {"delivered", "read"}:
        raise MessagingValidationError("Unsupported acknowledgement type")
    if through_sequence < 0 or through_sequence > conversation.last_message_sequence:
        raise MessagingValidationError("Acknowledgement sequence is invalid")
    access = participant_sequence_access(
        db, conversation=conversation, participant=participant
    )
    if through_sequence > 0 and not access.includes(through_sequence):
        raise MessagingAccessDenied("Acknowledgement is outside the visible history")

    existing = (
        db.query(MessageReceiptEvent)
        .filter(
            MessageReceiptEvent.participant_id == participant.id,
            MessageReceiptEvent.event_type == event_type,
            MessageReceiptEvent.client_ack_id == client_ack_id,
        )
        .first()
    )
    if existing is not None:
        if existing.through_sequence != through_sequence:
            raise MessagingConflict(
                "Client acknowledgement id was reused with a different sequence"
            )
        return existing, True

    locked = (
        db.query(ConversationParticipant)
        .filter(ConversationParticipant.id == participant.id)
        .with_for_update()
        .one()
    )
    recorded_at = _utc_now()
    if event_type == "read":
        if through_sequence > int(locked.last_read_sequence or 0):
            locked.last_read_sequence = through_sequence
            locked.last_read_at = recorded_at
        if through_sequence > int(locked.last_delivered_sequence or 0):
            locked.last_delivered_sequence = through_sequence
            locked.last_delivered_at = recorded_at
    elif through_sequence > int(locked.last_delivered_sequence or 0):
        locked.last_delivered_sequence = through_sequence
        locked.last_delivered_at = recorded_at

    event = MessageReceiptEvent(
        conversation_id=conversation.id,
        participant_id=participant.id,
        event_type=event_type,
        through_sequence=through_sequence,
        client_ack_id=client_ack_id,
        device_session_ref=device_session_ref,
        occurred_at=occurred_at,
    )
    db.add(event)
    db.flush()
    return event, False

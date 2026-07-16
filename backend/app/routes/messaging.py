from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import auth
from ..database import get_db, settings
from ..messaging_service import (
    MessagingAccessDenied,
    MessagingConflict,
    MessagingValidationError,
    acknowledge_messages,
    participant_sequence_access,
    participant_sequence_access_map,
    record_messaging_audit,
    send_text_message,
)
from ..models_school import (
    ClassSection,
    Conversation,
    ConversationAccessGrant,
    ConversationParticipant,
    FhhLink,
    FhhMessagingIdentity,
    FhhMessagingIdentityLink,
    GuardianLink,
    Membership,
    Message,
    School,
    SchoolMessagingPolicy,
    StaffAssignment,
    Student,
    SubjectGroup,
    User,
)
from ..rosters import resolve_rosters_for_students
from ..school_scope import open_interval_expression


staff_router = APIRouter()
guardian_router = APIRouter()

CURSOR_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
MAX_INBOX_CANDIDATES = 2000
MAX_RECIPIENT_CANDIDATES = 250


@dataclass(frozen=True)
class StaffActor:
    user: User
    membership: Membership
    school: School
    policy: SchoolMessagingPolicy


@dataclass(frozen=True)
class GuardianActor:
    user: User
    school: School
    policy: SchoolMessagingPolicy


@dataclass(frozen=True)
class ExternalGuardianActor:
    identity: FhhMessagingIdentity
    identity_link: FhhMessagingIdentityLink
    link: FhhLink
    school: School
    policy: SchoolMessagingPolicy


class StaffConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["student_staff", "staff_direct", "guardian_direct"]
    student_id: int | None = None
    other_staff_membership_id: int | None = None
    guardian_user_id: int | None = None


class GuardianConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["student_staff", "guardian_direct"] = "student_staff"
    student_id: int | None = None
    staff_membership_id: int


class MessageSendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_message_id: UUID
    body: str = Field(min_length=1, max_length=10_000)
    urgent: bool = False


class MessageAckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: Literal["delivered", "read"]
    through_sequence: int = Field(ge=0)
    client_ack_id: UUID
    occurred_at: datetime
    device_session_ref: str | None = Field(default=None, max_length=96)


class ConversationCloseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Literal[
        "assignment_ended", "student_archived", "restricted", "administrative"
    ]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"


def _cursor_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.JWT_SECRET, salt="chh-messaging-v1-cursor")


def _encode_cursor(payload: dict[str, Any]) -> str:
    return _cursor_serializer().dumps(payload)


def _decode_cursor(
    value: str | None,
    *,
    cursor_type: str,
    actor_ref: str,
    school_id: int,
    conversation_public_id: UUID | None = None,
) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        payload = _cursor_serializer().loads(
            value, max_age=CURSOR_MAX_AGE_SECONDS
        )
    except (BadSignature, SignatureExpired, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination cursor",
        )
    expected = {
        "type": cursor_type,
        "actor": actor_ref,
        "school_id": school_id,
    }
    if any(payload.get(key) != expected_value for key, expected_value in expected.items()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination cursor",
        )
    if conversation_public_id is not None and payload.get("conversation") != str(
        conversation_public_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination cursor",
        )
    return payload


def _school_id_from_header(request: Request) -> int:
    raw = request.headers.get("X-School-Id")
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="School context required",
        )
    try:
        return int(raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid school context",
        )


def _enabled_policy(db: Session, school_id: int) -> SchoolMessagingPolicy:
    policy = (
        db.query(SchoolMessagingPolicy)
        .filter(SchoolMessagingPolicy.school_id == school_id)
        .first()
    )
    if not settings.MESSAGING_ENABLED or policy is None or not policy.enabled:
        # A disabled pilot must not expose route/resource existence.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Messaging is unavailable",
        )
    return policy


async def require_staff_actor(
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> StaffActor:
    school_id = _school_id_from_header(request)
    school = (
        db.query(School)
        .filter(School.id == school_id, School.status == "active")
        .first()
    )
    if school is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="School access denied"
        )
    policy = _enabled_policy(db, school_id)
    memberships = (
        db.query(Membership)
        .filter(
            Membership.school_id == school_id,
            Membership.user_id == current_user.id,
            Membership.role.in_(("school_admin", "teacher")),
            Membership.status == "active",
            Membership.revoked_at.is_(None),
        )
        .order_by(Membership.id)
        .all()
    )
    requested_membership = request.headers.get("X-Membership-Id")
    if requested_membership:
        try:
            requested_id = int(requested_membership)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid membership context",
            )
        membership = next((row for row in memberships if row.id == requested_id), None)
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="School role required",
            )
    elif len(memberships) == 1:
        membership = memberships[0]
    elif len(memberships) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Explicit membership context required",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="School role required"
        )
    return StaffActor(
        user=current_user, membership=membership, school=school, policy=policy
    )


async def require_guardian_actor(
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> GuardianActor:
    school_id = _school_id_from_header(request)
    school = (
        db.query(School)
        .filter(School.id == school_id, School.status == "active")
        .first()
    )
    if school is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="School access denied"
        )
    policy = _enabled_policy(db, school_id)
    link_exists = (
        db.query(GuardianLink.id)
        .filter(
            GuardianLink.school_id == school_id,
            GuardianLink.user_id == current_user.id,
            GuardianLink.status == "active",
            GuardianLink.revoked_at.is_(None),
        )
        .first()
    )
    if link_exists is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guardian link required",
        )
    return GuardianActor(user=current_user, school=school, policy=policy)


def _student_name(row: Student) -> str:
    return " ".join(
        part for part in (row.preferred_name or row.first_name, row.last_name) if part
    ).strip()


def _staff_can_access_student(
    db: Session,
    *,
    membership: Membership,
    student: Student,
) -> StaffAssignment | None:
    if membership.school_id != student.school_id or student.status != "active":
        return None
    if membership.role == "school_admin":
        return None
    assignments = (
        db.query(StaffAssignment)
        .filter(
            StaffAssignment.school_id == student.school_id,
            StaffAssignment.membership_id == membership.id,
            *open_interval_expression(StaffAssignment),
        )
        .order_by(StaffAssignment.id)
        .all()
    )
    if not assignments:
        raise MessagingAccessDenied("Teacher assignment required")
    resolution = resolve_rosters_for_students(
        db, student.school_id, _utc_now().date(), student_ids=[student.id]
    )
    section_ids = {
        row.id for row in resolution.class_sections_by_student.get(student.id, [])
    }
    group_ids = {
        row["id"]
        for row in resolution.subject_groups_by_student.get(student.id, [])
        if row.get("id") is not None
    }
    assignment = next(
        (
            row
            for row in assignments
            if (
                row.class_section_id is not None
                and row.class_section_id in section_ids
            )
            or (
                row.subject_group_id is not None
                and row.subject_group_id in group_ids
            )
        ),
        None,
    )
    if assignment is None:
        raise MessagingAccessDenied("Teacher assignment required")
    return assignment


def _staff_participant(
    db: Session,
    *,
    conversation: Conversation,
    membership: Membership,
    user: User,
    assignment: StaffAssignment | None,
    visible_from: int = 1,
) -> ConversationParticipant:
    participant = ConversationParticipant(
        conversation_id=conversation.id,
        participant_kind="staff",
        user_id=user.id,
        membership_id=membership.id,
        side="staff",
        display_name_snapshot=user.name or "Staff",
        last_delivered_sequence=max(0, visible_from - 1),
        last_read_sequence=max(0, visible_from - 1),
    )
    db.add(participant)
    db.flush()
    grant = ConversationAccessGrant(
        conversation_id=conversation.id,
        participant_id=participant.id,
        source_type=(
            "staff_assignment"
            if assignment is not None
            else "school_admin_membership"
        ),
        staff_assignment_id=assignment.id if assignment is not None else None,
        membership_id=membership.id if assignment is None else None,
        grant_reason="conversation_created",
        visible_from_sequence=visible_from,
    )
    db.add(grant)
    return participant


def _ensure_current_guardians_for_conversations(
    db: Session,
    *,
    conversations: list[Conversation],
    initial: bool = False,
) -> int:
    eligible = [
        row
        for row in conversations
        if row.student_id is not None and row.kind == "student_staff"
    ]
    if not eligible:
        return 0
    conversation_ids = [row.id for row in eligible]
    student_ids_by_school: dict[int, set[int]] = {}
    for row in eligible:
        student_ids_by_school.setdefault(row.school_id, set()).add(row.student_id)

    chh_by_scope: dict[tuple[int, int], list[tuple[GuardianLink, User]]] = {}
    fhh_by_scope: dict[
        tuple[int, int], list[tuple[FhhLink, FhhMessagingIdentity]]
    ] = {}
    for school_id, student_ids in student_ids_by_school.items():
        chh_rows = (
            db.query(GuardianLink, User)
            .join(User, User.id == GuardianLink.user_id)
            .filter(
                GuardianLink.school_id == school_id,
                GuardianLink.student_id.in_(student_ids),
                GuardianLink.status == "active",
                GuardianLink.revoked_at.is_(None),
                User.status == "active",
            )
            .order_by(GuardianLink.student_id, GuardianLink.id)
            .all()
        )
        for link, user in chh_rows:
            chh_by_scope.setdefault((school_id, link.student_id), []).append(
                (link, user)
            )
        fhh_rows = (
            db.query(FhhLink, FhhMessagingIdentity)
            .join(
                FhhMessagingIdentityLink,
                FhhMessagingIdentityLink.fhh_link_id == FhhLink.id,
            )
            .join(
                FhhMessagingIdentity,
                FhhMessagingIdentity.id == FhhMessagingIdentityLink.identity_id,
            )
            .filter(
                FhhLink.school_id == school_id,
                FhhLink.student_id.in_(student_ids),
                FhhLink.status == "active",
                FhhLink.revoked_at.is_(None),
                FhhMessagingIdentityLink.school_id == school_id,
                FhhMessagingIdentityLink.status == "active",
                FhhMessagingIdentityLink.revoked_at.is_(None),
                FhhMessagingIdentity.school_id == school_id,
                FhhMessagingIdentity.status == "active",
            )
            .order_by(
                FhhLink.student_id,
                FhhMessagingIdentity.id,
                FhhLink.id,
            )
            .all()
        )
        for link, identity in fhh_rows:
            fhh_by_scope.setdefault((school_id, link.student_id), []).append(
                (link, identity)
            )

    existing = (
        db.query(ConversationParticipant)
        .filter(ConversationParticipant.conversation_id.in_(conversation_ids))
        .all()
    )
    existing_chh: dict[int, set[int]] = {}
    existing_fhh: dict[int, set[int]] = {}
    for row in existing:
        if (
            row.participant_kind == "chh_guardian"
            and row.left_at is None
            and row.user_id is not None
        ):
            existing_chh.setdefault(row.conversation_id, set()).add(row.user_id)
        elif (
            row.participant_kind == "fhh_parent"
            and row.left_at is None
            and row.external_participant_id is not None
        ):
            existing_fhh.setdefault(row.conversation_id, set()).add(
                row.external_participant_id
            )

    pending: list[
        tuple[ConversationParticipant, str, int | None, int]
    ] = []
    for conversation in eligible:
        visible_from = (
            1
            if initial
            else int(conversation.last_message_sequence or 0) + 1
        )
        current_chh = existing_chh.setdefault(conversation.id, set())
        for link, user in chh_by_scope.get(
            (conversation.school_id, conversation.student_id), []
        ):
            if user.id in current_chh:
                continue
            participant = ConversationParticipant(
                conversation_id=conversation.id,
                participant_kind="chh_guardian",
                user_id=user.id,
                side="guardian",
                display_name_snapshot=link.display_name
                or user.name
                or "Guardian",
                last_delivered_sequence=max(0, visible_from - 1),
                last_read_sequence=max(0, visible_from - 1),
            )
            db.add(participant)
            pending.append(
                (participant, "guardian_link", link.id, visible_from)
            )
            current_chh.add(user.id)

        current_fhh = existing_fhh.setdefault(conversation.id, set())
        for link, identity in fhh_by_scope.get(
            (conversation.school_id, conversation.student_id), []
        ):
            if identity.id in current_fhh:
                continue
            participant = ConversationParticipant(
                conversation_id=conversation.id,
                participant_kind="fhh_parent",
                external_participant_id=identity.id,
                side="guardian",
                display_name_snapshot=identity.display_name,
                last_delivered_sequence=max(0, visible_from - 1),
                last_read_sequence=max(0, visible_from - 1),
            )
            db.add(participant)
            pending.append((participant, "fhh_link", link.id, visible_from))
            current_fhh.add(identity.id)

    if not pending:
        return 0
    db.flush()
    for participant, source_type, source_id, visible_from in pending:
        db.add(
            ConversationAccessGrant(
                conversation_id=participant.conversation_id,
                participant_id=participant.id,
                source_type=source_type,
                guardian_link_id=(
                    source_id if source_type == "guardian_link" else None
                ),
                fhh_link_id=source_id if source_type == "fhh_link" else None,
                grant_reason=(
                    "conversation_created"
                    if initial
                    else "guardian_authorized_later"
                ),
                visible_from_sequence=visible_from,
            )
        )
    return len(pending)


def _ensure_current_guardians(
    db: Session,
    *,
    conversation: Conversation,
    initial: bool = False,
) -> int:
    return _ensure_current_guardians_for_conversations(
        db,
        conversations=[conversation],
        initial=initial,
    )


def _find_conversation(
    db: Session,
    *,
    school_id: int,
    public_id: UUID,
) -> Conversation | None:
    return (
        db.query(Conversation)
        .filter(
            Conversation.school_id == school_id,
            Conversation.public_id == public_id,
        )
        .first()
    )


def _staff_access(
    db: Session,
    *,
    actor: StaffActor,
    public_id: UUID,
) -> tuple[Conversation, ConversationParticipant]:
    conversation = _find_conversation(
        db, school_id=actor.school.id, public_id=public_id
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    _reconcile_closed_assignments(db, [conversation])
    participant = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.participant_kind == "staff",
            ConversationParticipant.membership_id == actor.membership.id,
            ConversationParticipant.left_at.is_(None),
        )
        .first()
    )
    if participant is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    try:
        participant_sequence_access(
            db, conversation=conversation, participant=participant
        )
    except MessagingAccessDenied:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation, participant


def _guardian_access(
    db: Session,
    *,
    actor: GuardianActor,
    public_id: UUID,
) -> tuple[Conversation, ConversationParticipant]:
    conversation = _find_conversation(
        db, school_id=actor.school.id, public_id=public_id
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    added = _ensure_current_guardians(db, conversation=conversation)
    _reconcile_closed_assignments(db, [conversation])
    participant = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.participant_kind == "chh_guardian",
            ConversationParticipant.user_id == actor.user.id,
            ConversationParticipant.left_at.is_(None),
        )
        .first()
    )
    if participant is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    try:
        participant_sequence_access(
            db, conversation=conversation, participant=participant
        )
    except MessagingAccessDenied:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if added:
        db.commit()
    return conversation, participant


def _external_guardian_access(
    db: Session,
    *,
    actor: ExternalGuardianActor,
    public_id: UUID,
) -> tuple[Conversation, ConversationParticipant]:
    conversation = _find_conversation(
        db, school_id=actor.school.id, public_id=public_id
    )
    if (
        conversation is None
        or conversation.student_id != actor.link.student_id
        or conversation.kind != "student_staff"
    ):
        raise HTTPException(status_code=404, detail="Conversation not found")
    added = _ensure_current_guardians(db, conversation=conversation)
    _reconcile_closed_assignments(db, [conversation])
    participant = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.participant_kind == "fhh_parent",
            ConversationParticipant.external_participant_id == actor.identity.id,
            ConversationParticipant.left_at.is_(None),
        )
        .first()
    )
    if participant is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    try:
        participant_sequence_access(
            db, conversation=conversation, participant=participant
        )
    except MessagingAccessDenied:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if added:
        db.commit()
    return conversation, participant


def _reconcile_closed_assignments(
    db: Session,
    conversations: list[Conversation],
) -> None:
    candidates = [
        row
        for row in conversations
        if row.kind == "student_staff" and row.status == "active"
    ]
    if not candidates:
        return
    participant_rows = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id.in_([row.id for row in candidates]),
            ConversationParticipant.participant_kind == "staff",
            ConversationParticipant.left_at.is_(None),
        )
        .all()
    )
    access = participant_sequence_access_map(
        db, conversations=candidates, participants=participant_rows
    )
    now = _utc_now()
    changed = False
    for participant in participant_rows:
        if participant.id in access:
            continue
        conversation = next(
            row for row in candidates if row.id == participant.conversation_id
        )
        conversation.status = "closed_assignment_ended"
        conversation.closed_at = now
        conversation.closed_reason = "assignment_ended"
        participant.left_at = now
        grants = (
            db.query(ConversationAccessGrant)
            .filter(
                ConversationAccessGrant.participant_id == participant.id,
                ConversationAccessGrant.revoked_at.is_(None),
            )
            .all()
        )
        for grant in grants:
            grant.valid_to = grant.valid_to or now
            grant.visible_through_sequence = int(
                conversation.last_message_sequence or 0
            )
            grant.revoked_at = now
            grant.revoke_reason = "current_source_ended"
        record_messaging_audit(
            db,
            school_id=conversation.school_id,
            event_type="conversation.assignment_closed",
            conversation_id=conversation.id,
            detail={"participant_id": participant.id},
        )
        changed = True
    if changed:
        db.commit()


def _actor_ref(actor: StaffActor | GuardianActor | ExternalGuardianActor) -> str:
    if isinstance(actor, StaffActor):
        return f"staff:{actor.membership.id}"
    if isinstance(actor, ExternalGuardianActor):
        return f"fhh:{actor.identity.id}:link:{actor.link.id}"
    return f"guardian:{actor.user.id}"


def _participant_for_actor(
    conversation: Conversation,
    participants: list[ConversationParticipant],
    actor: StaffActor | GuardianActor | ExternalGuardianActor,
) -> ConversationParticipant | None:
    for row in participants:
        if row.conversation_id != conversation.id or row.left_at is not None:
            continue
        if isinstance(actor, StaffActor) and row.membership_id == actor.membership.id:
            return row
        if (
            isinstance(actor, GuardianActor)
            and row.participant_kind == "chh_guardian"
            and row.user_id == actor.user.id
        ):
            return row
        if (
            isinstance(actor, ExternalGuardianActor)
            and row.participant_kind == "fhh_parent"
            and row.external_participant_id == actor.identity.id
        ):
            return row
    return None


def _conversation_payloads(
    db: Session,
    *,
    rows: list[Conversation],
    actor: StaffActor | GuardianActor | ExternalGuardianActor,
) -> list[dict[str, Any]]:
    if not rows:
        return []
    conversation_ids = [row.id for row in rows]
    participants = (
        db.query(ConversationParticipant)
        .filter(ConversationParticipant.conversation_id.in_(conversation_ids))
        .order_by(ConversationParticipant.id)
        .all()
    )
    students = {
        row.id: row
        for row in db.query(Student)
        .filter(Student.id.in_({row.student_id for row in rows if row.student_id}))
        .all()
    }
    latest_messages = (
        db.query(Message)
        .join(
            Conversation,
            (Conversation.id == Message.conversation_id)
            & (Conversation.last_message_sequence == Message.sequence),
        )
        .filter(Conversation.id.in_(conversation_ids))
        .all()
    )
    latest_by_conversation = {row.conversation_id: row for row in latest_messages}
    payloads = []
    for conversation in rows:
        current = _participant_for_actor(conversation, participants, actor)
        if current is None:
            continue
        student = students.get(conversation.student_id)
        latest = latest_by_conversation.get(conversation.id)
        counterpart_names = [
            row.display_name_snapshot
            for row in participants
            if row.conversation_id == conversation.id
            and row.id != current.id
            and row.left_at is None
        ]
        payloads.append(
            {
                "id": str(conversation.public_id),
                "kind": conversation.kind,
                "status": conversation.status,
                "read_only": conversation.status != "active",
                "student": (
                    {
                        "id": student.id,
                        "display_name": _student_name(student),
                        "name_ar": student.name_ar,
                    }
                    if student
                    else None
                ),
                "context": {
                    "label": conversation.context_label,
                    "label_ar": conversation.context_label_ar,
                },
                "participants": counterpart_names,
                "last_message": (
                    {
                        "id": str(latest.public_id),
                        "sequence": latest.sequence,
                        "sender_display_name": latest.sender_display_name_snapshot,
                        "body": latest.body if latest.state == "active" else None,
                        "state": latest.state,
                        "created_at": latest.created_at,
                    }
                    if latest
                    else None
                ),
                "last_message_at": conversation.last_message_at,
                "unread_count": max(
                    0,
                    int(conversation.last_message_sequence or 0)
                    - int(current.last_read_sequence or 0),
                ),
                "capabilities": {
                    "can_send": conversation.status == "active"
                    and (
                        current.side == "staff"
                        or actor.policy.guardian_replies_enabled
                    ),
                    "can_close": isinstance(actor, StaffActor)
                    and actor.membership.role == "school_admin"
                    and conversation.status == "active",
                    "delivery_receipts_visible": actor.policy.delivery_receipts_visible,
                    "read_receipts_visible": actor.policy.read_receipts_visible,
                },
            }
        )
    return payloads


def _authorized_inbox_pairs(
    db: Session,
    *,
    actor: StaffActor | GuardianActor | ExternalGuardianActor,
) -> list[tuple[Conversation, ConversationParticipant]]:
    school_id = actor.school.id
    if isinstance(actor, (GuardianActor, ExternalGuardianActor)):
        student_ids = (
            [actor.link.student_id]
            if isinstance(actor, ExternalGuardianActor)
            else [
                row[0]
                for row in db.query(GuardianLink.student_id)
                .filter(
                    GuardianLink.school_id == school_id,
                    GuardianLink.user_id == actor.user.id,
                    GuardianLink.status == "active",
                    GuardianLink.revoked_at.is_(None),
                )
                .all()
            ]
        )
        if student_ids:
            guardian_conversations = (
                db.query(Conversation)
                .filter(
                    Conversation.school_id == school_id,
                    Conversation.student_id.in_(student_ids),
                    Conversation.kind == "student_staff",
                )
                .all()
            )
            _ensure_current_guardians_for_conversations(
                db,
                conversations=guardian_conversations,
            )
            db.flush()

    participant_query = db.query(ConversationParticipant).join(
        Conversation, Conversation.id == ConversationParticipant.conversation_id
    )
    if isinstance(actor, StaffActor):
        participant_query = participant_query.filter(
            ConversationParticipant.participant_kind == "staff",
            ConversationParticipant.membership_id == actor.membership.id,
        )
    elif isinstance(actor, GuardianActor):
        participant_query = participant_query.filter(
            ConversationParticipant.participant_kind == "chh_guardian",
            ConversationParticipant.user_id == actor.user.id,
        )
    else:
        participant_query = participant_query.filter(
            Conversation.student_id == actor.link.student_id,
            Conversation.kind == "student_staff",
            ConversationParticipant.participant_kind == "fhh_parent",
            ConversationParticipant.external_participant_id == actor.identity.id,
        )
    participants = (
        participant_query.filter(
            Conversation.school_id == school_id,
            ConversationParticipant.left_at.is_(None),
        )
        .order_by(
            func.coalesce(Conversation.last_message_at, Conversation.created_at).desc(),
            Conversation.id.desc(),
        )
        .limit(MAX_INBOX_CANDIDATES)
        .all()
    )
    conversation_ids = [row.conversation_id for row in participants]
    conversations = (
        db.query(Conversation)
        .filter(Conversation.id.in_(conversation_ids))
        .all()
        if conversation_ids
        else []
    )
    conversations_by_id = {row.id: row for row in conversations}
    ordered_conversations = [
        conversations_by_id[row.conversation_id]
        for row in participants
        if row.conversation_id in conversations_by_id
    ]
    _reconcile_closed_assignments(db, ordered_conversations)
    access = participant_sequence_access_map(
        db, conversations=ordered_conversations, participants=participants
    )
    return [
        (conversation, participant)
        for conversation, participant in zip(ordered_conversations, participants)
        if participant.id in access
    ]


def _inbox(
    db: Session,
    *,
    actor: StaffActor | GuardianActor | ExternalGuardianActor,
    response: Response,
    limit: int,
    cursor: str | None,
    unread_only: bool,
    include_item_cursors: bool = False,
) -> dict[str, Any]:
    _private(response)
    school_id = actor.school.id
    actor_reference = _actor_ref(actor)
    decoded = _decode_cursor(
        cursor,
        cursor_type="inbox",
        actor_ref=actor_reference,
        school_id=school_id,
    )
    authorized_pairs = _authorized_inbox_pairs(db, actor=actor)
    if unread_only:
        authorized_pairs = [
            (conversation, participant)
            for conversation, participant in authorized_pairs
            if int(conversation.last_message_sequence or 0)
            > int(participant.last_read_sequence or 0)
        ]
    if decoded:
        cursor_activity = datetime.fromisoformat(decoded["activity"])
        if cursor_activity.tzinfo is None:
            cursor_activity = cursor_activity.replace(tzinfo=timezone.utc)
        cursor_id = int(decoded["id"])
        filtered_pairs = []
        for conversation, participant in authorized_pairs:
            activity = conversation.last_message_at or conversation.created_at
            if activity.tzinfo is None:
                activity = activity.replace(tzinfo=timezone.utc)
            if activity < cursor_activity or (
                activity == cursor_activity and conversation.id < cursor_id
            ):
                filtered_pairs.append((conversation, participant))
        authorized_pairs = filtered_pairs
    page_pairs = authorized_pairs[: limit + 1]
    has_more = len(page_pairs) > limit
    page_pairs = page_pairs[:limit]
    page_rows = [row[0] for row in page_pairs]
    items = _conversation_payloads(db, rows=page_rows, actor=actor)
    if include_item_cursors:
        item_by_id = {item["id"]: item for item in items}
        for row in page_rows:
            item = item_by_id.get(str(row.public_id))
            if item is None:
                continue
            item["cursor_after"] = _encode_cursor(
                {
                    "type": "inbox",
                    "actor": actor_reference,
                    "school_id": school_id,
                    "activity": (row.last_message_at or row.created_at).isoformat(),
                    "id": row.id,
                }
            )
    next_cursor = None
    if has_more and page_rows:
        last = page_rows[-1]
        next_cursor = _encode_cursor(
            {
                "type": "inbox",
                "actor": actor_reference,
                "school_id": school_id,
                "activity": (
                    last.last_message_at or last.created_at
                ).isoformat(),
                "id": last.id,
            }
        )
    db.commit()
    return {"items": items, "next_cursor": next_cursor}


def _conversation_detail(
    db: Session,
    *,
    conversation: Conversation,
    actor: StaffActor | GuardianActor | ExternalGuardianActor,
    response: Response,
) -> dict[str, Any]:
    _private(response)
    payloads = _conversation_payloads(db, rows=[conversation], actor=actor)
    if not payloads:
        raise HTTPException(status_code=404, detail="Conversation not found")
    participants = (
        db.query(ConversationParticipant)
        .filter(ConversationParticipant.conversation_id == conversation.id)
        .order_by(ConversationParticipant.id)
        .all()
    )
    payload = payloads[0]
    payload["participant_details"] = [
        {
            "kind": row.participant_kind,
            "side": row.side,
            "display_name": row.display_name_snapshot,
            "active": row.left_at is None,
        }
        for row in participants
    ]
    payload["shared_guardian_visibility"] = conversation.kind == "student_staff"
    payload["safeguarding_disclosure"] = True
    return payload


def _message_page(
    db: Session,
    *,
    conversation: Conversation,
    participant: ConversationParticipant,
    actor_ref: str,
    response: Response,
    limit: int,
    cursor: str | None,
) -> dict[str, Any]:
    _private(response)
    decoded = _decode_cursor(
        cursor,
        cursor_type="messages",
        actor_ref=actor_ref,
        school_id=conversation.school_id,
        conversation_public_id=conversation.public_id,
    )
    access = participant_sequence_access(
        db, conversation=conversation, participant=participant
    )
    before_sequence = (
        int(decoded["before"])
        if decoded
        else int(conversation.last_message_sequence or 0) + 1
    )
    query = db.query(Message).filter(
        Message.conversation_id == conversation.id,
        Message.sequence < before_sequence,
        Message.sequence >= access.visible_from,
    )
    if access.visible_through is not None:
        query = query.filter(Message.sequence <= access.visible_through)
    rows = query.order_by(Message.sequence.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = None
    if has_more and rows:
        next_cursor = _encode_cursor(
            {
                "type": "messages",
                "actor": actor_ref,
                "school_id": conversation.school_id,
                "conversation": str(conversation.public_id),
                "before": rows[-1].sequence,
            }
        )
    items = [
        {
            "id": str(row.public_id),
            "sequence": row.sequence,
            "sender_display_name": row.sender_display_name_snapshot,
            "sender_is_self": row.sender_participant_id == participant.id,
            "body": row.body if row.state == "active" else None,
            "state": row.state,
            "urgent": row.urgent,
            "created_at": row.created_at,
        }
        for row in reversed(rows)
    ]
    return {"items": items, "next_cursor": next_cursor}


def _create_student_staff_for_staff(
    db: Session, *, actor: StaffActor, student_id: int
) -> Conversation:
    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.school_id == actor.school.id,
            Student.status == "active",
        )
        .first()
    )
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    try:
        assignment = _staff_can_access_student(
            db, membership=actor.membership, student=student
        )
    except MessagingAccessDenied:
        raise HTTPException(status_code=403, detail="Teacher assignment required")
    existing = (
        db.query(Conversation)
        .filter(
            Conversation.school_id == actor.school.id,
            Conversation.kind == "student_staff",
            Conversation.student_id == student.id,
            Conversation.primary_staff_membership_id == actor.membership.id,
            Conversation.status == "active",
        )
        .first()
    )
    if existing:
        _ensure_current_guardians(db, conversation=existing)
        db.commit()
        return existing
    conversation = Conversation(
        school_id=actor.school.id,
        branch_campus_id=actor.membership.branch_campus_id,
        kind="student_staff",
        student_id=student.id,
        primary_staff_membership_id=actor.membership.id,
    )
    db.add(conversation)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(Conversation)
            .filter(
                Conversation.school_id == actor.school.id,
                Conversation.kind == "student_staff",
                Conversation.student_id == student.id,
                Conversation.primary_staff_membership_id == actor.membership.id,
                Conversation.status == "active",
            )
            .one()
        )
        _ensure_current_guardians(db, conversation=existing)
        db.commit()
        return existing
    staff = _staff_participant(
        db,
        conversation=conversation,
        membership=actor.membership,
        user=actor.user,
        assignment=assignment,
    )
    guardian_count = _ensure_current_guardians(
        db, conversation=conversation, initial=True
    )
    if guardian_count == 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No currently authorized guardian is available",
        )
    conversation.created_by_participant_id = staff.id
    record_messaging_audit(
        db,
        school_id=actor.school.id,
        event_type="conversation.created",
        participant=staff,
        conversation_id=conversation.id,
        detail={"kind": conversation.kind, "student_id": student.id},
    )
    db.commit()
    return conversation


def _target_staff(
    db: Session, *, school_id: int, membership_id: int
) -> tuple[Membership, User]:
    row = (
        db.query(Membership, User)
        .join(User, User.id == Membership.user_id)
        .filter(
            Membership.id == membership_id,
            Membership.school_id == school_id,
            Membership.role.in_(("teacher", "school_admin")),
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            User.status == "active",
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Staff recipient not found")
    return row


def _create_staff_direct(
    db: Session, *, actor: StaffActor, other_membership_id: int
) -> Conversation:
    other_membership, other_user = _target_staff(
        db, school_id=actor.school.id, membership_id=other_membership_id
    )
    if other_membership.id == actor.membership.id:
        raise HTTPException(status_code=400, detail="Choose another staff member")
    if "school_admin" not in {actor.membership.role, other_membership.role}:
        raise HTTPException(
            status_code=403, detail="Direct staff messaging requires an administrator"
        )
    low, high = sorted((actor.membership.id, other_membership.id))
    existing = (
        db.query(Conversation)
        .filter(
            Conversation.school_id == actor.school.id,
            Conversation.kind == "staff_direct",
            Conversation.staff_membership_low_id == low,
            Conversation.staff_membership_high_id == high,
            Conversation.status == "active",
        )
        .first()
    )
    if existing:
        return existing
    conversation = Conversation(
        school_id=actor.school.id,
        kind="staff_direct",
        staff_membership_low_id=low,
        staff_membership_high_id=high,
    )
    db.add(conversation)
    db.flush()
    sender = _staff_participant(
        db,
        conversation=conversation,
        membership=actor.membership,
        user=actor.user,
        assignment=None,
    )
    _staff_participant(
        db,
        conversation=conversation,
        membership=other_membership,
        user=other_user,
        assignment=None,
    )
    conversation.created_by_participant_id = sender.id
    record_messaging_audit(
        db,
        school_id=actor.school.id,
        event_type="conversation.created",
        participant=sender,
        conversation_id=conversation.id,
        detail={"kind": conversation.kind},
    )
    db.commit()
    return conversation


def _create_guardian_direct(
    db: Session,
    *,
    actor: StaffActor,
    guardian_user_id: int,
    student_id: int | None,
) -> Conversation:
    if actor.membership.role != "school_admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    link_query = db.query(GuardianLink, User).join(User, User.id == GuardianLink.user_id)
    link_query = link_query.filter(
        GuardianLink.school_id == actor.school.id,
        GuardianLink.user_id == guardian_user_id,
        GuardianLink.status == "active",
        GuardianLink.revoked_at.is_(None),
        User.status == "active",
    )
    if student_id is not None:
        link_query = link_query.filter(GuardianLink.student_id == student_id)
    link_row = link_query.order_by(GuardianLink.id).first()
    if link_row is None:
        raise HTTPException(status_code=404, detail="Guardian recipient not found")
    link, guardian_user = link_row
    student_id = student_id if student_id is not None else None
    existing_query = db.query(Conversation).filter(
        Conversation.school_id == actor.school.id,
        Conversation.kind == "guardian_direct",
        Conversation.primary_staff_membership_id == actor.membership.id,
        Conversation.internal_guardian_user_id == guardian_user.id,
        Conversation.status == "active",
    )
    existing_query = (
        existing_query.filter(Conversation.student_id == student_id)
        if student_id is not None
        else existing_query.filter(Conversation.student_id.is_(None))
    )
    existing = existing_query.first()
    if existing:
        return existing
    conversation = Conversation(
        school_id=actor.school.id,
        kind="guardian_direct",
        student_id=student_id,
        primary_staff_membership_id=actor.membership.id,
        internal_guardian_user_id=guardian_user.id,
    )
    db.add(conversation)
    db.flush()
    sender = _staff_participant(
        db,
        conversation=conversation,
        membership=actor.membership,
        user=actor.user,
        assignment=None,
    )
    guardian = ConversationParticipant(
        conversation_id=conversation.id,
        participant_kind="chh_guardian",
        user_id=guardian_user.id,
        side="guardian",
        display_name_snapshot=link.display_name
        or guardian_user.name
        or "Guardian",
    )
    db.add(guardian)
    db.flush()
    db.add(
        ConversationAccessGrant(
            conversation_id=conversation.id,
            participant_id=guardian.id,
            source_type="guardian_link",
            guardian_link_id=link.id,
            grant_reason="conversation_created",
        )
    )
    conversation.created_by_participant_id = sender.id
    record_messaging_audit(
        db,
        school_id=actor.school.id,
        event_type="conversation.created",
        participant=sender,
        conversation_id=conversation.id,
        detail={"kind": conversation.kind, "student_id": student_id},
    )
    db.commit()
    return conversation


def _create_for_guardian(
    db: Session, *, actor: GuardianActor, body: GuardianConversationCreate
) -> Conversation:
    target_membership, target_user = _target_staff(
        db,
        school_id=actor.school.id,
        membership_id=body.staff_membership_id,
    )
    if body.kind == "student_staff":
        if body.student_id is None:
            raise HTTPException(status_code=400, detail="Student is required")
        guardian_link = (
            db.query(GuardianLink)
            .filter(
                GuardianLink.school_id == actor.school.id,
                GuardianLink.student_id == body.student_id,
                GuardianLink.user_id == actor.user.id,
                GuardianLink.status == "active",
                GuardianLink.revoked_at.is_(None),
            )
            .first()
        )
        student = (
            db.query(Student)
            .filter(
                Student.id == body.student_id,
                Student.school_id == actor.school.id,
                Student.status == "active",
            )
            .first()
        )
        if guardian_link is None or student is None:
            raise HTTPException(status_code=404, detail="Student not found")
        try:
            assignment = _staff_can_access_student(
                db, membership=target_membership, student=student
            )
        except MessagingAccessDenied:
            raise HTTPException(status_code=404, detail="Staff recipient not found")
        existing = (
            db.query(Conversation)
            .filter(
                Conversation.school_id == actor.school.id,
                Conversation.kind == "student_staff",
                Conversation.student_id == student.id,
                Conversation.primary_staff_membership_id == target_membership.id,
                Conversation.status == "active",
            )
            .first()
        )
        if existing:
            _ensure_current_guardians(db, conversation=existing)
            db.commit()
            return existing
        conversation = Conversation(
            school_id=actor.school.id,
            kind="student_staff",
            student_id=student.id,
            primary_staff_membership_id=target_membership.id,
        )
        db.add(conversation)
        db.flush()
        _staff_participant(
            db,
            conversation=conversation,
            membership=target_membership,
            user=target_user,
            assignment=assignment,
        )
        _ensure_current_guardians(db, conversation=conversation, initial=True)
    else:
        if target_membership.role != "school_admin":
            raise HTTPException(status_code=404, detail="Staff recipient not found")
        if body.student_id is not None:
            link = (
                db.query(GuardianLink)
                .filter(
                    GuardianLink.school_id == actor.school.id,
                    GuardianLink.student_id == body.student_id,
                    GuardianLink.user_id == actor.user.id,
                    GuardianLink.status == "active",
                    GuardianLink.revoked_at.is_(None),
                )
                .first()
            )
            if link is None:
                raise HTTPException(status_code=404, detail="Student not found")
        existing_query = db.query(Conversation).filter(
            Conversation.school_id == actor.school.id,
            Conversation.kind == "guardian_direct",
            Conversation.primary_staff_membership_id == target_membership.id,
            Conversation.internal_guardian_user_id == actor.user.id,
            Conversation.status == "active",
        )
        existing_query = (
            existing_query.filter(Conversation.student_id == body.student_id)
            if body.student_id is not None
            else existing_query.filter(Conversation.student_id.is_(None))
        )
        existing = existing_query.first()
        if existing:
            return existing
        conversation = Conversation(
            school_id=actor.school.id,
            kind="guardian_direct",
            student_id=body.student_id,
            primary_staff_membership_id=target_membership.id,
            internal_guardian_user_id=actor.user.id,
        )
        db.add(conversation)
        db.flush()
        _staff_participant(
            db,
            conversation=conversation,
            membership=target_membership,
            user=target_user,
            assignment=None,
        )
        guardian_link = (
            db.query(GuardianLink)
            .filter(
                GuardianLink.school_id == actor.school.id,
                GuardianLink.user_id == actor.user.id,
                GuardianLink.status == "active",
                GuardianLink.revoked_at.is_(None),
                *(
                    (GuardianLink.student_id == body.student_id,)
                    if body.student_id is not None
                    else ()
                ),
            )
            .order_by(GuardianLink.id)
            .first()
        )
        guardian = ConversationParticipant(
            conversation_id=conversation.id,
            participant_kind="chh_guardian",
            user_id=actor.user.id,
            side="guardian",
            display_name_snapshot=guardian_link.display_name
            or actor.user.name
            or "Guardian",
        )
        db.add(guardian)
        db.flush()
        db.add(
            ConversationAccessGrant(
                conversation_id=conversation.id,
                participant_id=guardian.id,
                source_type="guardian_link",
                guardian_link_id=guardian_link.id,
                grant_reason="conversation_created",
            )
        )
    guardian_participant = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.participant_kind == "chh_guardian",
            ConversationParticipant.user_id == actor.user.id,
        )
        .one()
    )
    conversation.created_by_participant_id = guardian_participant.id
    record_messaging_audit(
        db,
        school_id=actor.school.id,
        event_type="conversation.created",
        participant=guardian_participant,
        conversation_id=conversation.id,
        detail={"kind": conversation.kind, "student_id": conversation.student_id},
    )
    db.commit()
    return conversation


def _create_for_external_guardian(
    db: Session,
    *,
    actor: ExternalGuardianActor,
    staff_membership_id: int,
) -> Conversation:
    student = (
        db.query(Student)
        .filter(
            Student.id == actor.link.student_id,
            Student.school_id == actor.school.id,
            Student.status == "active",
        )
        .first()
    )
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    target_membership, target_user = _target_staff(
        db,
        school_id=actor.school.id,
        membership_id=staff_membership_id,
    )
    try:
        assignment = _staff_can_access_student(
            db, membership=target_membership, student=student
        )
    except MessagingAccessDenied:
        raise HTTPException(status_code=404, detail="Staff recipient not found")
    existing = (
        db.query(Conversation)
        .filter(
            Conversation.school_id == actor.school.id,
            Conversation.kind == "student_staff",
            Conversation.student_id == student.id,
            Conversation.primary_staff_membership_id == target_membership.id,
            Conversation.status == "active",
        )
        .first()
    )
    if existing:
        _ensure_current_guardians(db, conversation=existing)
        db.commit()
        return existing
    conversation = Conversation(
        school_id=actor.school.id,
        kind="student_staff",
        student_id=student.id,
        primary_staff_membership_id=target_membership.id,
    )
    db.add(conversation)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(Conversation)
            .filter(
                Conversation.school_id == actor.school.id,
                Conversation.kind == "student_staff",
                Conversation.student_id == student.id,
                Conversation.primary_staff_membership_id == target_membership.id,
                Conversation.status == "active",
            )
            .one()
        )
        _ensure_current_guardians(db, conversation=existing)
        db.commit()
        return existing
    _staff_participant(
        db,
        conversation=conversation,
        membership=target_membership,
        user=target_user,
        assignment=assignment,
    )
    _ensure_current_guardians(db, conversation=conversation, initial=True)
    external_participant = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation.id,
            ConversationParticipant.participant_kind == "fhh_parent",
            ConversationParticipant.external_participant_id == actor.identity.id,
        )
        .one()
    )
    conversation.created_by_participant_id = external_participant.id
    record_messaging_audit(
        db,
        school_id=actor.school.id,
        event_type="conversation.created",
        participant=external_participant,
        conversation_id=conversation.id,
        detail={"kind": conversation.kind, "student_id": student.id},
    )
    db.commit()
    return conversation


@staff_router.get("/inbox")
def staff_inbox(
    response: Response,
    limit: int = Query(default=30, ge=1, le=50),
    cursor: str | None = None,
    unread_only: bool = False,
    actor: StaffActor = Depends(require_staff_actor),
    db: Session = Depends(get_db),
):
    return _inbox(
        db,
        actor=actor,
        response=response,
        limit=limit,
        cursor=cursor,
        unread_only=unread_only,
    )


@guardian_router.get("/inbox")
def guardian_inbox(
    response: Response,
    limit: int = Query(default=30, ge=1, le=50),
    cursor: str | None = None,
    unread_only: bool = False,
    actor: GuardianActor = Depends(require_guardian_actor),
    db: Session = Depends(get_db),
):
    return _inbox(
        db,
        actor=actor,
        response=response,
        limit=limit,
        cursor=cursor,
        unread_only=unread_only,
    )


def _unread_count(
    db: Session,
    *,
    actor: StaffActor | GuardianActor | ExternalGuardianActor,
    response: Response,
) -> dict[str, int]:
    _private(response)
    pairs = _authorized_inbox_pairs(db, actor=actor)
    unread = [
        max(
            0,
            int(conversation.last_message_sequence or 0)
            - int(participant.last_read_sequence or 0),
        )
        for conversation, participant in pairs
    ]
    result = {
        "total": sum(unread),
        "conversations": sum(1 for count in unread if count > 0),
    }
    db.commit()
    return result


@staff_router.get("/unread-count")
def staff_unread_count(
    response: Response,
    actor: StaffActor = Depends(require_staff_actor),
    db: Session = Depends(get_db),
):
    return _unread_count(db, actor=actor, response=response)


@guardian_router.get("/unread-count")
def guardian_unread_count(
    response: Response,
    actor: GuardianActor = Depends(require_guardian_actor),
    db: Session = Depends(get_db),
):
    return _unread_count(db, actor=actor, response=response)


@staff_router.get("/recipients")
def staff_recipients(
    response: Response,
    q: str = Query(default="", max_length=120),
    actor: StaffActor = Depends(require_staff_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    needle = q.strip().lower()
    if actor.membership.role == "school_admin":
        students = (
            db.query(Student)
            .filter(
                Student.school_id == actor.school.id,
                Student.status == "active",
            )
            .order_by(Student.last_name, Student.first_name, Student.id)
            .limit(MAX_RECIPIENT_CANDIDATES)
            .all()
        )
    else:
        assignments = (
            db.query(StaffAssignment)
            .filter(
                StaffAssignment.school_id == actor.school.id,
                StaffAssignment.membership_id == actor.membership.id,
                *open_interval_expression(StaffAssignment),
            )
            .all()
        )
        resolution = resolve_rosters_for_students(
            db, actor.school.id, _utc_now().date()
        )
        student_ids = {
            student_id
            for student_id, sections in resolution.class_sections_by_student.items()
            if any(
                assignment.class_section_id == section.id
                for assignment in assignments
                for section in sections
            )
        } | {
            student_id
            for student_id, groups in resolution.subject_groups_by_student.items()
            if any(
                assignment.subject_group_id == group.get("id")
                for assignment in assignments
                for group in groups
            )
        }
        students = (
            db.query(Student)
            .filter(Student.id.in_(student_ids), Student.status == "active")
            .order_by(Student.last_name, Student.first_name, Student.id)
            .limit(MAX_RECIPIENT_CANDIDATES)
            .all()
            if student_ids
            else []
        )
    if needle:
        students = [
            row
            for row in students
            if needle in _student_name(row).lower()
            or needle in (row.name_ar or "").lower()
        ]
    guardian_rows = (
        db.query(GuardianLink, User)
        .join(User, User.id == GuardianLink.user_id)
        .filter(
            GuardianLink.school_id == actor.school.id,
            GuardianLink.student_id.in_([row.id for row in students]),
            GuardianLink.status == "active",
            GuardianLink.revoked_at.is_(None),
        )
        .all()
        if students
        else []
    )
    guardian_names: dict[int, list[str]] = {}
    for link, user in guardian_rows:
        guardian_names.setdefault(link.student_id, []).append(
            link.display_name or user.name or "Guardian"
        )
    staff_rows = []
    if actor.membership.role == "school_admin":
        staff_rows = (
            db.query(Membership, User)
            .join(User, User.id == Membership.user_id)
            .filter(
                Membership.school_id == actor.school.id,
                Membership.role.in_(("teacher", "school_admin")),
                Membership.status == "active",
                Membership.revoked_at.is_(None),
                Membership.id != actor.membership.id,
            )
            .order_by(User.name, Membership.id)
            .limit(MAX_RECIPIENT_CANDIDATES)
            .all()
        )
        if needle:
            staff_rows = [
                row for row in staff_rows if needle in (row[1].name or "").lower()
            ]
    return {
        "students": [
            {
                "student_id": row.id,
                "display_name": _student_name(row),
                "name_ar": row.name_ar,
                "guardian_names": guardian_names.get(row.id, []),
            }
            for row in students[:50]
        ],
        "staff": [
            {
                "membership_id": membership.id,
                "display_name": user.name,
                "name_ar": user.name_ar,
                "role": membership.role,
            }
            for membership, user in staff_rows[:50]
        ],
    }


@guardian_router.get("/recipients")
def guardian_recipients(
    response: Response,
    q: str = Query(default="", max_length=120),
    actor: GuardianActor = Depends(require_guardian_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    links = (
        db.query(GuardianLink)
        .filter(
            GuardianLink.school_id == actor.school.id,
            GuardianLink.user_id == actor.user.id,
            GuardianLink.status == "active",
            GuardianLink.revoked_at.is_(None),
        )
        .order_by(GuardianLink.id)
        .all()
    )
    student_ids = {row.student_id for row in links}
    students = {
        row.id: row
        for row in db.query(Student)
        .filter(Student.id.in_(student_ids), Student.status == "active")
        .all()
    }
    resolution = resolve_rosters_for_students(
        db, actor.school.id, _utc_now().date(), student_ids=student_ids
    )
    assignments = (
        db.query(StaffAssignment, Membership, User)
        .join(Membership, Membership.id == StaffAssignment.membership_id)
        .join(User, User.id == Membership.user_id)
        .filter(
            StaffAssignment.school_id == actor.school.id,
            *open_interval_expression(StaffAssignment),
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            User.status == "active",
        )
        .limit(MAX_RECIPIENT_CANDIDATES)
        .all()
    )
    needle = q.strip().lower()
    results = []
    for student_id, student in students.items():
        section_ids = {
            row.id
            for row in resolution.class_sections_by_student.get(student_id, [])
        }
        group_ids = {
            row["id"]
            for row in resolution.subject_groups_by_student.get(student_id, [])
            if row.get("id") is not None
        }
        for assignment, membership, user in assignments:
            if assignment.class_section_id not in section_ids and assignment.subject_group_id not in group_ids:
                continue
            if needle and needle not in (user.name or "").lower() and needle not in _student_name(student).lower():
                continue
            results.append(
                {
                    "student_id": student.id,
                    "student_display_name": _student_name(student),
                    "membership_id": membership.id,
                    "display_name": user.name,
                    "name_ar": user.name_ar,
                    "role": membership.role,
                }
            )
    admins = (
        db.query(Membership, User)
        .join(User, User.id == Membership.user_id)
        .filter(
            Membership.school_id == actor.school.id,
            Membership.role == "school_admin",
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            User.status == "active",
        )
        .order_by(User.name, Membership.id)
        .limit(50)
        .all()
    )
    return {
        "student_staff": results[:100],
        "administrators": [
            {
                "membership_id": membership.id,
                "display_name": user.name,
                "name_ar": user.name_ar,
                "role": membership.role,
            }
            for membership, user in admins
            if not needle or needle in (user.name or "").lower()
        ],
    }


@staff_router.post("/conversations")
def create_staff_conversation(
    body: StaffConversationCreate,
    response: Response,
    actor: StaffActor = Depends(require_staff_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    if body.kind == "student_staff":
        if body.student_id is None or body.other_staff_membership_id or body.guardian_user_id:
            raise HTTPException(status_code=400, detail="Invalid conversation target")
        conversation = _create_student_staff_for_staff(
            db, actor=actor, student_id=body.student_id
        )
    elif body.kind == "staff_direct":
        if body.other_staff_membership_id is None or body.student_id or body.guardian_user_id:
            raise HTTPException(status_code=400, detail="Invalid conversation target")
        conversation = _create_staff_direct(
            db, actor=actor, other_membership_id=body.other_staff_membership_id
        )
    else:
        if body.guardian_user_id is None or body.other_staff_membership_id:
            raise HTTPException(status_code=400, detail="Invalid conversation target")
        conversation = _create_guardian_direct(
            db,
            actor=actor,
            guardian_user_id=body.guardian_user_id,
            student_id=body.student_id,
        )
    return {"conversation_id": str(conversation.public_id), "status": conversation.status}


@guardian_router.post("/conversations")
def create_guardian_conversation(
    body: GuardianConversationCreate,
    response: Response,
    actor: GuardianActor = Depends(require_guardian_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    conversation = _create_for_guardian(db, actor=actor, body=body)
    return {"conversation_id": str(conversation.public_id), "status": conversation.status}


@staff_router.get("/conversations/{conversation_id}")
def staff_conversation_detail(
    conversation_id: UUID,
    response: Response,
    actor: StaffActor = Depends(require_staff_actor),
    db: Session = Depends(get_db),
):
    conversation, _ = _staff_access(db, actor=actor, public_id=conversation_id)
    return _conversation_detail(
        db, conversation=conversation, actor=actor, response=response
    )


@guardian_router.get("/conversations/{conversation_id}")
def guardian_conversation_detail(
    conversation_id: UUID,
    response: Response,
    actor: GuardianActor = Depends(require_guardian_actor),
    db: Session = Depends(get_db),
):
    conversation, _ = _guardian_access(db, actor=actor, public_id=conversation_id)
    return _conversation_detail(
        db, conversation=conversation, actor=actor, response=response
    )


@staff_router.get("/conversations/{conversation_id}/messages")
def staff_messages(
    conversation_id: UUID,
    response: Response,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    actor: StaffActor = Depends(require_staff_actor),
    db: Session = Depends(get_db),
):
    conversation, participant = _staff_access(
        db, actor=actor, public_id=conversation_id
    )
    return _message_page(
        db,
        conversation=conversation,
        participant=participant,
        actor_ref=_actor_ref(actor),
        response=response,
        limit=limit,
        cursor=cursor,
    )


@guardian_router.get("/conversations/{conversation_id}/messages")
def guardian_messages(
    conversation_id: UUID,
    response: Response,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    actor: GuardianActor = Depends(require_guardian_actor),
    db: Session = Depends(get_db),
):
    conversation, participant = _guardian_access(
        db, actor=actor, public_id=conversation_id
    )
    return _message_page(
        db,
        conversation=conversation,
        participant=participant,
        actor_ref=_actor_ref(actor),
        response=response,
        limit=limit,
        cursor=cursor,
    )


def _send(
    db: Session,
    *,
    conversation: Conversation,
    participant: ConversationParticipant,
    body: MessageSendRequest,
    actor: StaffActor | GuardianActor | ExternalGuardianActor,
    response: Response,
) -> dict[str, Any]:
    _private(response)
    if body.urgent:
        allowed = isinstance(actor, StaffActor) and (
            actor.membership.role == "school_admin"
            or actor.policy.teachers_may_mark_urgent
        )
        if not allowed:
            raise HTTPException(status_code=403, detail="Urgent sending is not allowed")
    try:
        message, duplicate = send_text_message(
            db,
            conversation_id=conversation.id,
            sender_participant_id=participant.id,
            client_message_id=body.client_message_id,
            body=body.body,
            urgent=body.urgent,
        )
        db.commit()
    except MessagingAccessDenied as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except MessagingValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except MessagingConflict as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    return {
        "id": str(message.public_id),
        "sequence": message.sequence,
        "sender_display_name": message.sender_display_name_snapshot,
        "body": message.body,
        "state": message.state,
        "urgent": message.urgent,
        "created_at": message.created_at,
        "duplicate": duplicate,
    }


@staff_router.post("/conversations/{conversation_id}/messages")
def staff_send(
    conversation_id: UUID,
    body: MessageSendRequest,
    response: Response,
    actor: StaffActor = Depends(require_staff_actor),
    db: Session = Depends(get_db),
):
    conversation, participant = _staff_access(
        db, actor=actor, public_id=conversation_id
    )
    return _send(
        db,
        conversation=conversation,
        participant=participant,
        body=body,
        actor=actor,
        response=response,
    )


@guardian_router.post("/conversations/{conversation_id}/messages")
def guardian_send(
    conversation_id: UUID,
    body: MessageSendRequest,
    response: Response,
    actor: GuardianActor = Depends(require_guardian_actor),
    db: Session = Depends(get_db),
):
    conversation, participant = _guardian_access(
        db, actor=actor, public_id=conversation_id
    )
    return _send(
        db,
        conversation=conversation,
        participant=participant,
        body=body,
        actor=actor,
        response=response,
    )


def _ack(
    db: Session,
    *,
    conversation: Conversation,
    participant: ConversationParticipant,
    body: MessageAckRequest,
    response: Response,
) -> dict[str, Any]:
    _private(response)
    try:
        event, duplicate = acknowledge_messages(
            db,
            conversation=conversation,
            participant=participant,
            event_type=body.event_type,
            through_sequence=body.through_sequence,
            client_ack_id=body.client_ack_id,
            occurred_at=body.occurred_at,
            device_session_ref=body.device_session_ref,
        )
        db.commit()
    except MessagingAccessDenied as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except MessagingValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except MessagingConflict as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    return {
        "event_type": event.event_type,
        "through_sequence": event.through_sequence,
        "recorded_at": event.recorded_at,
        "duplicate": duplicate,
    }


@staff_router.post("/conversations/{conversation_id}/acknowledgements")
def staff_ack(
    conversation_id: UUID,
    body: MessageAckRequest,
    response: Response,
    actor: StaffActor = Depends(require_staff_actor),
    db: Session = Depends(get_db),
):
    conversation, participant = _staff_access(
        db, actor=actor, public_id=conversation_id
    )
    return _ack(
        db,
        conversation=conversation,
        participant=participant,
        body=body,
        response=response,
    )


@guardian_router.post("/conversations/{conversation_id}/acknowledgements")
def guardian_ack(
    conversation_id: UUID,
    body: MessageAckRequest,
    response: Response,
    actor: GuardianActor = Depends(require_guardian_actor),
    db: Session = Depends(get_db),
):
    conversation, participant = _guardian_access(
        db, actor=actor, public_id=conversation_id
    )
    return _ack(
        db,
        conversation=conversation,
        participant=participant,
        body=body,
        response=response,
    )


@staff_router.post("/conversations/{conversation_id}/close")
def close_conversation(
    conversation_id: UUID,
    body: ConversationCloseRequest,
    response: Response,
    actor: StaffActor = Depends(require_staff_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    if actor.membership.role != "school_admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    conversation, participant = _staff_access(
        db, actor=actor, public_id=conversation_id
    )
    if conversation.status == "active":
        mapping = {
            "assignment_ended": "closed_assignment_ended",
            "student_archived": "closed_student_archived",
            "restricted": "closed_restricted",
            "administrative": "archived",
        }
        conversation.status = mapping[body.reason]
        conversation.closed_at = _utc_now()
        conversation.closed_reason = body.reason
        record_messaging_audit(
            db,
            school_id=actor.school.id,
            event_type="conversation.closed",
            participant=participant,
            conversation_id=conversation.id,
            detail={"reason": body.reason},
        )
        db.commit()
    return {"conversation_id": str(conversation.public_id), "status": conversation.status}

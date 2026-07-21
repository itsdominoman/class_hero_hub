"""Confidential school-scoped messaging legal holds."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from .models_school import (
    Conversation,
    Message,
    MessagingLegalHold,
    MessagingLegalHoldEvent,
    Student,
)
from .safeguarding_service import (
    PERMISSION_LEGAL_HOLD,
    SafeguardingActor,
    SafeguardingConflict,
    SafeguardingNotFound,
    normalized_reason,
    require_permission,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def place_hold(
    db: Session,
    *,
    actor: SafeguardingActor,
    scope_type: str,
    target_ref: str,
    reason: str,
    case_reference: str | None,
    review_at: datetime | None,
) -> MessagingLegalHold:
    require_permission(actor, PERMISSION_LEGAL_HOLD)
    clean_reason = normalized_reason(reason, maximum=4000)
    target: dict[str, int | None] = {
        "conversation_id": None,
        "message_id": None,
        "student_id": None,
    }
    if scope_type == "conversation":
        try:
            public_id = UUID(target_ref)
        except ValueError as exc:
            raise SafeguardingNotFound("Conversation not found") from exc
        row = db.query(Conversation).filter(
            Conversation.school_id == actor.school.id,
            Conversation.public_id == public_id,
        ).first()
        if row is None:
            raise SafeguardingNotFound("Conversation not found")
        target["conversation_id"] = row.id
    elif scope_type == "message":
        try:
            public_id = UUID(target_ref)
        except ValueError as exc:
            raise SafeguardingNotFound("Message not found") from exc
        row = db.query(Message).filter(
            Message.school_id == actor.school.id,
            Message.public_id == public_id,
        ).first()
        if row is None:
            raise SafeguardingNotFound("Message not found")
        target["message_id"] = row.id
    elif scope_type == "student":
        try:
            student_id = int(target_ref)
        except ValueError as exc:
            raise SafeguardingNotFound("Student not found") from exc
        row = db.query(Student).filter(
            Student.school_id == actor.school.id,
            Student.id == student_id,
        ).first()
        if row is None:
            raise SafeguardingNotFound("Student not found")
        target["student_id"] = row.id
    else:
        raise SafeguardingConflict("Invalid legal-hold scope")
    if review_at is not None:
        if review_at.tzinfo is None:
            review_at = review_at.replace(tzinfo=timezone.utc)
        if review_at <= now_utc():
            raise SafeguardingConflict("Legal-hold review date must be in the future")
    duplicate = db.query(MessagingLegalHold.id).filter(
        MessagingLegalHold.school_id == actor.school.id,
        MessagingLegalHold.released_at.is_(None),
        MessagingLegalHold.scope_type == scope_type,
        *[
            getattr(MessagingLegalHold, key) == value
            for key, value in target.items()
            if value is not None
        ],
    ).first()
    if duplicate is not None:
        raise SafeguardingConflict("An active legal hold already covers this target")
    hold = MessagingLegalHold(
        school_id=actor.school.id,
        scope_type=scope_type,
        reason=clean_reason,
        case_reference=(case_reference or "").strip() or None,
        review_at=review_at,
        created_by_membership_id=actor.membership.id,
        **target,
    )
    db.add(hold)
    db.flush()
    db.add(MessagingLegalHoldEvent(
        hold_id=hold.id,
        school_id=actor.school.id,
        action="placed",
        actor_membership_id=actor.membership.id,
        reason=clean_reason,
    ))
    db.commit()
    db.refresh(hold)
    return hold


def release_hold(
    db: Session,
    *,
    actor: SafeguardingActor,
    public_id: UUID,
    reason: str,
) -> MessagingLegalHold:
    require_permission(actor, PERMISSION_LEGAL_HOLD)
    clean_reason = normalized_reason(reason, maximum=4000)
    actor_membership_id = int(actor.membership.id)
    hold = db.query(MessagingLegalHold).filter(
        MessagingLegalHold.school_id == actor.school.id,
        MessagingLegalHold.public_id == public_id,
    ).with_for_update().first()
    if hold is None:
        raise SafeguardingNotFound("Legal hold not found")
    if hold.released_at is not None:
        raise SafeguardingConflict("Legal hold is already released")
    hold.released_at = now_utc()
    hold.released_by_membership_id = actor_membership_id
    hold.release_reason = clean_reason
    db.add(MessagingLegalHoldEvent(
        hold_id=hold.id,
        school_id=actor.school.id,
        action="released",
        actor_membership_id=actor_membership_id,
        reason=clean_reason,
    ))
    db.commit()
    db.refresh(hold)
    return hold


def held_message_filter(school_id: int):
    """SQL expression identifying messages under any active hold."""
    return MessagingLegalHold.school_id == school_id, MessagingLegalHold.released_at.is_(None)


def held_message_ids(db: Session, *, school_id: int, message_ids: list[int]) -> set[int]:
    """Resolve holds in one bounded query for a retention batch."""
    if not message_ids:
        return set()
    messages = db.query(Message.id, Message.conversation_id).join(
        Conversation, Conversation.id == Message.conversation_id
    ).filter(
        Message.school_id == school_id,
        Message.id.in_(message_ids),
    ).all()
    by_id = {int(row.id): int(row.conversation_id) for row in messages}
    conversation_ids = set(by_id.values())
    student_by_conversation = dict(db.query(Conversation.id, Conversation.student_id).filter(
        Conversation.id.in_(conversation_ids)
    ).all())
    holds = db.query(MessagingLegalHold).filter(
        MessagingLegalHold.school_id == school_id,
        MessagingLegalHold.released_at.is_(None),
        or_(
            MessagingLegalHold.message_id.in_(message_ids),
            MessagingLegalHold.conversation_id.in_(conversation_ids),
            MessagingLegalHold.student_id.in_(
                [value for value in student_by_conversation.values() if value is not None]
            ),
        ),
    ).all()
    held: set[int] = set()
    for hold in holds:
        for message_id, conversation_id in by_id.items():
            if (
                hold.message_id == message_id
                or hold.conversation_id == conversation_id
                or (
                    hold.student_id is not None
                    and student_by_conversation.get(conversation_id) == hold.student_id
                )
            ):
                held.add(message_id)
    return held

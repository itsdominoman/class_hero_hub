"""School-scoped safeguarding review, moderation and evidence export services.

This module deliberately never calls participant access, acknowledgement, send, or
notification helpers. Safeguarding review is an audited administrative projection,
not conversation participation.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func
from sqlalchemy.orm import Session

from .message_media_service import protected_media_file
from .message_voice_service import protected_voice_file
from .models_school import (
    Conversation,
    ConversationParticipant,
    Membership,
    Message,
    MessageMedia,
    MessageReceiptEvent,
    MessageVoiceMedia,
    MessagingAuditEvent,
    MessagingEvidenceExport,
    MessagingModerationAction,
    MessagingPermissionGrant,
    SafeguardingFlag,
    SafeguardingInternalNote,
    SafeguardingReviewSession,
    School,
    User,
)


PERMISSION_REVIEW = "messaging.safeguarding_review"
PERMISSION_MODERATE = "messaging.moderate"
PERMISSION_EXPORT = "messaging.export_evidence"
PERMISSION_EXPORT_NOTES = "messaging.export_internal_notes"
PERMISSION_MANAGE = "messaging.manage_safeguarding_permissions"
SAFEGUARDING_PERMISSIONS = frozenset(
    {
        PERMISSION_REVIEW,
        PERMISSION_MODERATE,
        PERMISSION_EXPORT,
        PERMISSION_EXPORT_NOTES,
        PERMISSION_MANAGE,
    }
)
REASON_CATEGORIES = frozenset(
    {
        "reported_concern",
        "safeguarding_investigation",
        "complaint",
        "staff_conduct_review",
        "parent_communication_review",
        "legal_regulatory_request",
        "authorised_technical_support",
        "other",
    }
)
RESTRICTION_TYPES = frozenset(
    {"family_replies", "staff_replies", "both_replies", "read_only"}
)
REVIEW_TTL = timedelta(minutes=30)
MAX_REVIEW_TTL = timedelta(minutes=60)
EXPORT_TTL = timedelta(minutes=30)
MAX_EXPORT_MESSAGES = 5000
MAX_EXPORT_MEDIA = 500
MAX_EXPORT_BYTES = 100 * 1024 * 1024
EXPORT_ROOT = Path(
    os.environ.get("SAFEGUARDING_EXPORT_DIR", "/app/data/safeguarding_exports")
)


class SafeguardingError(Exception):
    pass


class SafeguardingAccessDenied(SafeguardingError):
    pass


class SafeguardingNotFound(SafeguardingError):
    pass


class SafeguardingConflict(SafeguardingError):
    pass


class SafeguardingExpired(SafeguardingError):
    pass


class SafeguardingRateLimited(SafeguardingError):
    pass


class SafeguardingValidationError(SafeguardingError):
    pass


@dataclass(frozen=True)
class SafeguardingActor:
    user: User
    school: School
    membership: Membership
    permissions: frozenset[str]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def normalized_reason(value: str, *, minimum: int = 8, maximum: int = 2000) -> str:
    result = " ".join((value or "").split())
    if len(result) < minimum or len(result) > maximum:
        raise SafeguardingValidationError(
            f"Justification must be between {minimum} and {maximum} characters"
        )
    if len(set(result.casefold())) < 3:
        raise SafeguardingValidationError("A meaningful justification is required")
    return result


def validate_reason_category(value: str) -> str:
    if value not in REASON_CATEGORIES:
        raise SafeguardingValidationError("Invalid safeguarding reason category")
    return value


def active_permission_names(
    db: Session, *, school_id: int, membership_id: int
) -> frozenset[str]:
    return frozenset(
        row.permission
        for row in db.query(MessagingPermissionGrant)
        .filter(
            MessagingPermissionGrant.school_id == school_id,
            MessagingPermissionGrant.membership_id == membership_id,
            MessagingPermissionGrant.revoked_at.is_(None),
        )
        .all()
    )


def resolve_actor(
    db: Session,
    *,
    user: User,
    school_id: int,
    membership_id: int | None,
) -> SafeguardingActor:
    school = (
        db.query(School)
        .filter(
            School.id == school_id,
            School.status.in_(("pending_setup", "active")),
        )
        .first()
    )
    if school is None or user.status != "active":
        raise SafeguardingAccessDenied("Safeguarding access denied")
    query = db.query(Membership).filter(
        Membership.school_id == school_id,
        Membership.user_id == user.id,
        Membership.status == "active",
        Membership.revoked_at.is_(None),
    )
    if membership_id is not None:
        query = query.filter(Membership.id == membership_id)
    memberships = query.order_by(Membership.id).all()
    eligible = [
        (row, active_permission_names(db, school_id=school_id, membership_id=row.id))
        for row in memberships
    ]
    eligible = [(row, permissions) for row, permissions in eligible if permissions]
    if len(eligible) != 1:
        if membership_id is None and len(eligible) > 1:
            raise SafeguardingValidationError("Explicit membership context required")
        raise SafeguardingAccessDenied("Safeguarding access denied")
    membership, permissions = eligible[0]
    return SafeguardingActor(
        user=user,
        school=school,
        membership=membership,
        permissions=permissions,
    )


def require_permission(actor: SafeguardingActor, permission: str) -> None:
    if permission not in actor.permissions:
        raise SafeguardingAccessDenied("Safeguarding permission required")


def audit_event(
    db: Session,
    *,
    actor: SafeguardingActor | None,
    school_id: int,
    event_type: str,
    conversation_id: int | None = None,
    message_id: int | None = None,
    detail: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> MessagingAuditEvent:
    row = MessagingAuditEvent(
        school_id=school_id,
        actor_kind="safeguarding_admin" if actor else "system",
        actor_user_id=actor.user.id if actor else None,
        actor_membership_id=actor.membership.id if actor else None,
        actor_external_participant_id=None,
        event_type=event_type,
        conversation_id=conversation_id,
        message_id=message_id,
        participant_id=None,
        detail=detail or {},
        request_correlation_id=correlation_id,
    )
    db.add(row)
    db.flush()
    return row


def enforce_rate_limit(
    db: Session,
    *,
    actor: SafeguardingActor,
    event_types: Iterable[str],
    window: timedelta,
    maximum: int,
) -> None:
    count = (
        db.query(func.count(MessagingAuditEvent.id))
        .filter(
            MessagingAuditEvent.school_id == actor.school.id,
            MessagingAuditEvent.actor_membership_id == actor.membership.id,
            MessagingAuditEvent.event_type.in_(tuple(event_types)),
            MessagingAuditEvent.occurred_at >= utc_now() - window,
        )
        .scalar()
        or 0
    )
    if int(count) >= maximum:
        raise SafeguardingRateLimited("Safeguarding request rate limit exceeded")


def grant_permission(
    db: Session,
    *,
    actor: SafeguardingActor,
    membership: Membership,
    permission: str,
    reason: str,
) -> MessagingPermissionGrant:
    require_permission(actor, PERMISSION_MANAGE)
    if permission not in SAFEGUARDING_PERMISSIONS:
        raise SafeguardingValidationError("Unknown safeguarding permission")
    if membership.school_id != actor.school.id or membership.status != "active" or membership.revoked_at is not None:
        raise SafeguardingNotFound("Membership not found")
    user = db.query(User).filter(User.id == membership.user_id, User.status == "active").first()
    if user is None:
        raise SafeguardingNotFound("Membership not found")
    existing = (
        db.query(MessagingPermissionGrant)
        .filter(
            MessagingPermissionGrant.school_id == actor.school.id,
            MessagingPermissionGrant.membership_id == membership.id,
            MessagingPermissionGrant.permission == permission,
            MessagingPermissionGrant.revoked_at.is_(None),
        )
        .first()
    )
    if existing:
        return existing
    normalized = normalized_reason(reason, minimum=3, maximum=1000)
    row = MessagingPermissionGrant(
        school_id=actor.school.id,
        membership_id=membership.id,
        permission=permission,
        granted_by_membership_id=actor.membership.id,
        grant_reason=normalized,
    )
    db.add(row)
    db.flush()
    audit_event(
        db,
        actor=actor,
        school_id=actor.school.id,
        event_type="safeguarding.permission_granted",
        detail={"membership_id": membership.id, "permission": permission},
    )
    return row


def revoke_permission(
    db: Session,
    *,
    actor: SafeguardingActor,
    grant: MessagingPermissionGrant,
    reason: str,
) -> None:
    require_permission(actor, PERMISSION_MANAGE)
    if grant.school_id != actor.school.id or grant.revoked_at is not None:
        raise SafeguardingNotFound("Permission grant not found")
    grant.revoked_at = utc_now()
    grant.revoked_by_membership_id = actor.membership.id
    grant.revoke_reason = normalized_reason(reason, minimum=3, maximum=1000)
    audit_event(
        db,
        actor=actor,
        school_id=actor.school.id,
        event_type="safeguarding.permission_revoked",
        detail={"membership_id": grant.membership_id, "permission": grant.permission},
    )


def start_review_session(
    db: Session,
    *,
    actor: SafeguardingActor,
    conversation: Conversation,
    reason_category: str,
    justification: str,
    acknowledgement: bool,
    ttl_minutes: int = 30,
    correlation_id: str | None = None,
) -> SafeguardingReviewSession:
    require_permission(actor, PERMISSION_REVIEW)
    if conversation.school_id != actor.school.id:
        raise SafeguardingNotFound("Conversation not found")
    if not acknowledgement:
        raise SafeguardingValidationError("Audit acknowledgement is required")
    if ttl_minutes < 5 or timedelta(minutes=ttl_minutes) > MAX_REVIEW_TTL:
        raise SafeguardingValidationError("Review duration must be between 5 and 60 minutes")
    enforce_rate_limit(
        db,
        actor=actor,
        event_types=("safeguarding.review_started",),
        window=timedelta(minutes=1),
        maximum=10,
    )
    now = utc_now()
    row = SafeguardingReviewSession(
        school_id=actor.school.id,
        conversation_id=conversation.id,
        reviewer_membership_id=actor.membership.id,
        reason_category=validate_reason_category(reason_category),
        justification=normalized_reason(justification),
        acknowledgement=True,
        started_at=now,
        expires_at=now + timedelta(minutes=ttl_minutes),
    )
    db.add(row)
    db.flush()
    audit_event(
        db,
        actor=actor,
        school_id=actor.school.id,
        event_type="safeguarding.review_started",
        conversation_id=conversation.id,
        detail={
            "review_session": str(row.public_id),
            "reason_category": row.reason_category,
            "expires_at": row.expires_at.isoformat(),
        },
        correlation_id=correlation_id,
    )
    return row


def active_review_session(
    db: Session,
    *,
    actor: SafeguardingActor,
    public_id: UUID,
    conversation_public_id: UUID | None = None,
) -> tuple[SafeguardingReviewSession, Conversation]:
    require_permission(actor, PERMISSION_REVIEW)
    row = (
        db.query(SafeguardingReviewSession)
        .filter(
            SafeguardingReviewSession.public_id == public_id,
            SafeguardingReviewSession.school_id == actor.school.id,
            SafeguardingReviewSession.reviewer_membership_id == actor.membership.id,
        )
        .first()
    )
    if row is None:
        raise SafeguardingNotFound("Review session not found")
    now = utc_now()
    if row.revoked_at is not None or row.ended_at is not None:
        raise SafeguardingExpired("Review session is no longer active")
    if as_aware(row.expires_at) <= now:
        row.ended_at = now
        row.end_reason = "expired"
        audit_event(
            db,
            actor=actor,
            school_id=actor.school.id,
            event_type="safeguarding.review_expired",
            conversation_id=row.conversation_id,
            detail={"review_session": str(row.public_id)},
        )
        db.commit()
        raise SafeguardingExpired("Review session has expired")
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == row.conversation_id,
            Conversation.school_id == actor.school.id,
        )
        .first()
    )
    if conversation is None or (
        conversation_public_id is not None
        and conversation.public_id != conversation_public_id
    ):
        raise SafeguardingNotFound("Conversation not found for this review session")
    return row, conversation


def end_review_session(
    db: Session,
    *,
    actor: SafeguardingActor,
    session: SafeguardingReviewSession,
    reason: str = "ended_by_reviewer",
) -> None:
    if session.reviewer_membership_id != actor.membership.id or session.school_id != actor.school.id:
        raise SafeguardingNotFound("Review session not found")
    if session.ended_at is None:
        session.ended_at = utc_now()
        session.end_reason = reason
        audit_event(
            db,
            actor=actor,
            school_id=actor.school.id,
            event_type="safeguarding.review_ended",
            conversation_id=session.conversation_id,
            detail={"review_session": str(session.public_id), "end_reason": reason},
        )


def revoke_review_session(
    db: Session,
    *,
    actor: SafeguardingActor,
    session: SafeguardingReviewSession,
    reason: str,
) -> None:
    require_permission(actor, PERMISSION_MANAGE)
    if session.school_id != actor.school.id:
        raise SafeguardingNotFound("Review session not found")
    if session.revoked_at is not None or session.ended_at is not None:
        raise SafeguardingConflict("Review session is no longer active")
    session.revoked_at = utc_now()
    session.revoked_by_membership_id = actor.membership.id
    session.end_reason = normalized_reason(reason, minimum=3, maximum=48)
    audit_event(
        db,
        actor=actor,
        school_id=actor.school.id,
        event_type="safeguarding.review_revoked",
        conversation_id=session.conversation_id,
        detail={"review_session": str(session.public_id)},
    )


def state_hash(value: dict[str, Any]) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def conversation_moderation_state(conversation: Conversation) -> dict[str, Any]:
    return {
        "status": conversation.status,
        "restriction_type": conversation.restriction_type,
        "restricted_at": conversation.restricted_at,
        "restricted_by_membership_id": conversation.restricted_by_membership_id,
        "reopening_requires_approval": bool(conversation.reopening_requires_approval),
        "closed_at": conversation.closed_at,
        "closed_reason": conversation.closed_reason,
        "safeguarding_closed_by_membership_id": conversation.safeguarding_closed_by_membership_id,
    }


def message_moderation_state(message: Message) -> dict[str, Any]:
    return {
        "state": message.state,
        "tombstoned_at": message.tombstoned_at,
        "tombstoned_by_membership_id": message.tombstoned_by_membership_id,
        "tombstone_reason": message.tombstone_reason,
    }


def record_moderation_action(
    db: Session,
    *,
    actor: SafeguardingActor,
    session: SafeguardingReviewSession,
    conversation: Conversation,
    action: str,
    reason_category: str,
    confidential_reason: str,
    before: dict[str, Any],
    after: dict[str, Any],
    message: Message | None = None,
    restriction_type: str | None = None,
    participant_safe_reason: str | None = None,
) -> MessagingModerationAction:
    row = MessagingModerationAction(
        school_id=actor.school.id,
        conversation_id=conversation.id,
        message_id=message.id if message else None,
        review_session_id=session.id,
        actor_membership_id=actor.membership.id,
        action=action,
        restriction_type=restriction_type,
        reason_category=validate_reason_category(reason_category),
        confidential_reason=normalized_reason(confidential_reason, maximum=4000),
        participant_safe_reason=(participant_safe_reason or "").strip()[:240] or None,
        prior_state_hash=state_hash(before),
        new_state_hash=state_hash(after),
    )
    db.add(row)
    db.flush()
    audit_event(
        db,
        actor=actor,
        school_id=actor.school.id,
        event_type=f"safeguarding.{action}",
        conversation_id=conversation.id,
        message_id=message.id if message else None,
        detail={
            "moderation_event": str(row.event_id),
            "reason_category": row.reason_category,
            "prior_state_hash": row.prior_state_hash,
            "new_state_hash": row.new_state_hash,
            **({"restriction_type": restriction_type} if restriction_type else {}),
        },
    )
    return row


def apply_restriction(
    db: Session,
    *,
    actor: SafeguardingActor,
    session: SafeguardingReviewSession,
    conversation: Conversation,
    restriction_type: str,
    reason_category: str,
    confidential_reason: str,
    reopening_requires_approval: bool,
    participant_safe_reason: str | None,
) -> MessagingModerationAction:
    require_permission(actor, PERMISSION_MODERATE)
    if restriction_type not in RESTRICTION_TYPES:
        raise SafeguardingValidationError("Invalid restriction type")
    before = conversation_moderation_state(conversation)
    conversation.restriction_type = restriction_type
    conversation.restricted_at = utc_now()
    conversation.restricted_by_membership_id = actor.membership.id
    conversation.reopening_requires_approval = reopening_requires_approval
    after = conversation_moderation_state(conversation)
    return record_moderation_action(
        db,
        actor=actor,
        session=session,
        conversation=conversation,
        action="restrict",
        reason_category=reason_category,
        confidential_reason=confidential_reason,
        before=before,
        after=after,
        restriction_type=restriction_type,
        participant_safe_reason=participant_safe_reason,
    )


def remove_restriction(
    db: Session,
    *,
    actor: SafeguardingActor,
    session: SafeguardingReviewSession,
    conversation: Conversation,
    reason_category: str,
    confidential_reason: str,
) -> MessagingModerationAction:
    require_permission(actor, PERMISSION_MODERATE)
    if conversation.restriction_type is None:
        raise SafeguardingConflict("Conversation is not restricted")
    before = conversation_moderation_state(conversation)
    old_type = conversation.restriction_type
    conversation.restriction_type = None
    conversation.restricted_at = None
    conversation.restricted_by_membership_id = None
    conversation.reopening_requires_approval = False
    after = conversation_moderation_state(conversation)
    return record_moderation_action(
        db,
        actor=actor,
        session=session,
        conversation=conversation,
        action="remove_restriction",
        reason_category=reason_category,
        confidential_reason=confidential_reason,
        before=before,
        after=after,
        restriction_type=old_type,
    )


def close_conversation(
    db: Session,
    *,
    actor: SafeguardingActor,
    session: SafeguardingReviewSession,
    conversation: Conversation,
    reason_category: str,
    confidential_reason: str,
    requires_approval: bool,
    participant_safe_reason: str | None,
) -> MessagingModerationAction:
    require_permission(actor, PERMISSION_MODERATE)
    if conversation.status != "active":
        raise SafeguardingConflict("Conversation is already closed")
    before = conversation_moderation_state(conversation)
    conversation.status = "closed_restricted"
    conversation.closed_at = utc_now()
    conversation.closed_reason = "safeguarding"
    conversation.safeguarding_closed_by_membership_id = actor.membership.id
    conversation.reopening_requires_approval = requires_approval
    after = conversation_moderation_state(conversation)
    return record_moderation_action(
        db,
        actor=actor,
        session=session,
        conversation=conversation,
        action="close",
        reason_category=reason_category,
        confidential_reason=confidential_reason,
        before=before,
        after=after,
        participant_safe_reason=participant_safe_reason,
    )


def reopen_conversation(
    db: Session,
    *,
    actor: SafeguardingActor,
    session: SafeguardingReviewSession,
    conversation: Conversation,
    reason_category: str,
    confidential_reason: str,
    remove_existing_restriction: bool,
) -> MessagingModerationAction:
    require_permission(actor, PERMISSION_MODERATE)
    if conversation.status != "closed_restricted" or conversation.closed_reason != "safeguarding":
        raise SafeguardingConflict("Only a safeguarding-closed conversation can be reopened here")
    before = conversation_moderation_state(conversation)
    conversation.status = "active"
    conversation.closed_at = None
    conversation.closed_reason = None
    conversation.safeguarding_closed_by_membership_id = None
    conversation.reopening_requires_approval = False
    if remove_existing_restriction:
        conversation.restriction_type = None
        conversation.restricted_at = None
        conversation.restricted_by_membership_id = None
    after = conversation_moderation_state(conversation)
    return record_moderation_action(
        db,
        actor=actor,
        session=session,
        conversation=conversation,
        action="reopen",
        reason_category=reason_category,
        confidential_reason=confidential_reason,
        before=before,
        after=after,
    )


def moderate_message(
    db: Session,
    *,
    actor: SafeguardingActor,
    session: SafeguardingReviewSession,
    conversation: Conversation,
    message: Message,
    action: str,
    reason_category: str,
    confidential_reason: str,
    participant_safe_reason: str | None,
) -> MessagingModerationAction:
    require_permission(actor, PERMISSION_MODERATE)
    if message.school_id != actor.school.id or message.conversation_id != conversation.id:
        raise SafeguardingNotFound("Message not found")
    before = message_moderation_state(message)
    if action == "tombstone":
        if message.state == "tombstoned":
            raise SafeguardingConflict("Message is already tombstoned")
        message.state = "tombstoned"
        message.tombstoned_at = utc_now()
        message.tombstoned_by_membership_id = actor.membership.id
        message.tombstone_reason = "removed_by_school"
    elif action == "restore":
        if message.state != "tombstoned":
            raise SafeguardingConflict("Message is not tombstoned")
        message.state = "active"
        message.tombstoned_at = None
        message.tombstoned_by_membership_id = None
        message.tombstone_reason = None
    else:
        raise SafeguardingValidationError("Invalid message moderation action")
    after = message_moderation_state(message)
    return record_moderation_action(
        db,
        actor=actor,
        session=session,
        conversation=conversation,
        message=message,
        action=action,
        reason_category=reason_category,
        confidential_reason=confidential_reason,
        before=before,
        after=after,
        participant_safe_reason=participant_safe_reason,
    )


def add_internal_note(
    db: Session,
    *,
    actor: SafeguardingActor,
    session: SafeguardingReviewSession,
    conversation: Conversation,
    body: str,
    correction_of: SafeguardingInternalNote | None,
) -> SafeguardingInternalNote:
    require_permission(actor, PERMISSION_MODERATE)
    if correction_of and (
        correction_of.school_id != actor.school.id
        or correction_of.conversation_id != conversation.id
    ):
        raise SafeguardingNotFound("Internal note not found")
    note = SafeguardingInternalNote(
        school_id=actor.school.id,
        conversation_id=conversation.id,
        review_session_id=session.id,
        author_membership_id=actor.membership.id,
        body=normalized_reason(body, minimum=3, maximum=10000),
        correction_of_note_id=correction_of.id if correction_of else None,
    )
    db.add(note)
    db.flush()
    audit_event(
        db,
        actor=actor,
        school_id=actor.school.id,
        event_type="safeguarding.internal_note_added",
        conversation_id=conversation.id,
        detail={
            "note": str(note.public_id),
            "correction_of": str(correction_of.public_id) if correction_of else None,
            "content_sha256": hashlib.sha256(note.body.encode()).hexdigest(),
        },
    )
    return note


def create_flag(
    db: Session,
    *,
    actor: SafeguardingActor,
    conversation: Conversation,
    message: Message | None,
    category: str,
    severity: str,
    internal_note: str | None,
    assigned_membership_id: int | None,
) -> SafeguardingFlag:
    require_permission(actor, PERMISSION_MODERATE)
    if message and message.conversation_id != conversation.id:
        raise SafeguardingNotFound("Message not found")
    if severity not in {"low", "medium", "high", "critical"}:
        raise SafeguardingValidationError("Invalid flag severity")
    category_value = "_".join((category or "").strip().lower().split())
    if not 3 <= len(category_value) <= 48:
        raise SafeguardingValidationError("Flag category must be 3 to 48 characters")
    if assigned_membership_id is not None:
        assigned = (
            db.query(Membership)
            .filter(
                Membership.id == assigned_membership_id,
                Membership.school_id == actor.school.id,
                Membership.status == "active",
                Membership.revoked_at.is_(None),
            )
            .first()
        )
        if assigned is None:
            raise SafeguardingNotFound("Assigned reviewer not found")
    flag = SafeguardingFlag(
        school_id=actor.school.id,
        conversation_id=conversation.id,
        message_id=message.id if message else None,
        category=category_value,
        severity=severity,
        status="open",
        internal_note=(normalized_reason(internal_note, minimum=3, maximum=4000) if internal_note else None),
        assigned_membership_id=assigned_membership_id,
        created_by_membership_id=actor.membership.id,
    )
    db.add(flag)
    db.flush()
    audit_event(
        db,
        actor=actor,
        school_id=actor.school.id,
        event_type="safeguarding.flagged",
        conversation_id=conversation.id,
        message_id=message.id if message else None,
        detail={"flag": str(flag.public_id), "category": category_value, "severity": severity},
    )
    return flag


def update_flag_status(
    db: Session,
    *,
    actor: SafeguardingActor,
    flag: SafeguardingFlag,
    status: str,
    resolution_note: str | None,
) -> None:
    require_permission(actor, PERMISSION_MODERATE)
    if flag.school_id != actor.school.id:
        raise SafeguardingNotFound("Flag not found")
    if status not in {"open", "follow_up", "resolved"}:
        raise SafeguardingValidationError("Invalid follow-up status")
    previous = flag.status
    flag.status = status
    if status == "resolved":
        flag.resolved_at = utc_now()
        flag.resolved_by_membership_id = actor.membership.id
        flag.resolution_note = (
            normalized_reason(resolution_note, minimum=3, maximum=4000)
            if resolution_note
            else None
        )
    else:
        flag.resolved_at = None
        flag.resolved_by_membership_id = None
        flag.resolution_note = None
    audit_event(
        db,
        actor=actor,
        school_id=actor.school.id,
        event_type="safeguarding.flag_status_changed",
        conversation_id=flag.conversation_id,
        message_id=flag.message_id,
        detail={"flag": str(flag.public_id), "prior_status": previous, "new_status": status},
    )


def _iso_utc(value: datetime | None) -> str | None:
    return as_aware(value).astimezone(timezone.utc).isoformat() if value else None


def _iso_local(value: datetime | None, school: School) -> str | None:
    if value is None:
        return None
    try:
        zone = ZoneInfo(school.timezone or "UTC")
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("UTC")
    return as_aware(value).astimezone(zone).isoformat()


def _safe_zip_name(value: str) -> str:
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
        raise SafeguardingValidationError("Invalid evidence package path")
    return str(candidate)


def export_path(storage_key: str) -> Path:
    root = EXPORT_ROOT.resolve()
    path = (root / storage_key).resolve()
    if root != path and root not in path.parents:
        raise SafeguardingValidationError("Evidence export is unavailable")
    return path


def _canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _transcript_html(
    *,
    school: School,
    conversation: Conversation,
    participants: list[ConversationParticipant],
    messages: list[Message],
    sender_by_id: dict[int, ConversationParticipant],
    notes: list[SafeguardingInternalNote],
    generated_at: datetime,
) -> bytes:
    participant_rows = "".join(
        f"<li>{html.escape(row.display_name_snapshot)} "
        f"({html.escape(row.participant_kind)}, {html.escape(row.side)})</li>"
        for row in participants
    )
    message_rows = []
    for message in messages:
        sender = sender_by_id.get(message.sender_participant_id)
        body = message.body or "[No text body]"
        if message.state == "tombstoned":
            body = f"[TOMBSTONED - AUTHORISED ORIGINAL FOLLOWS]\n{body}"
        message_rows.append(
            "<article><h3>"
            f"#{message.sequence} - {html.escape(message.sender_display_name_snapshot)}"
            "</h3><p>"
            f"UTC: {html.escape(_iso_utc(message.created_at) or '')}<br>"
            f"School time: {html.escape(_iso_local(message.created_at, school) or '')}<br>"
            f"Role: {html.escape(sender.participant_kind if sender else 'unknown')}<br>"
            f"Type: {html.escape(message.message_type)}; State: {html.escape(message.state)}"
            "</p><pre>"
            f"{html.escape(body)}"
            "</pre></article>"
        )
    note_rows = "".join(
        "<article class=\"internal\"><h3>Internal safeguarding note</h3><p>"
        f"{html.escape(_iso_utc(note.created_at) or '')}</p><pre>{html.escape(note.body)}</pre></article>"
        for note in notes
    )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Safeguarding evidence transcript</title>
<style>body{{font-family:system-ui,sans-serif;max-width:920px;margin:2rem auto;padding:0 1rem;color:#172033}}
article{{border-top:1px solid #ccd3df;padding:1rem 0}}pre{{white-space:pre-wrap;font:inherit}}
.internal{{background:#fff5d6;padding:1rem;border:1px solid #e1b94f}}</style></head><body>
<h1>Safeguarding evidence transcript</h1>
<p><strong>School:</strong> {html.escape(school.name or '')}<br>
<strong>Conversation:</strong> {html.escape(str(conversation.public_id))}<br>
<strong>Generated UTC:</strong> {html.escape(_iso_utc(generated_at) or '')}</p>
<h2>Participants</h2><ul>{participant_rows}</ul>
<h2>Messages</h2>{''.join(message_rows)}
{('<h2>Internal notes</h2>' + note_rows) if notes else ''}
</body></html>"""
    return document.encode("utf-8")


def create_evidence_export(
    db: Session,
    *,
    actor: SafeguardingActor,
    session: SafeguardingReviewSession,
    conversation: Conversation,
    export_mode: str,
    reason_category: str,
    justification: str,
    include_internal_notes: bool,
) -> MessagingEvidenceExport:
    require_permission(actor, PERMISSION_EXPORT)
    # Slice 12 intentionally exposes only the internal evidence package.  The
    # manifest carries an explicit privacy_mode so a separately designed,
    # redacted participant-safe variant can be added without changing format.
    if export_mode != "internal":
        raise SafeguardingValidationError("Only internal evidence export is currently available")
    if include_internal_notes:
        if export_mode != "internal":
            raise SafeguardingValidationError("Participant-safe exports cannot include internal notes")
        require_permission(actor, PERMISSION_EXPORT_NOTES)
    enforce_rate_limit(
        db,
        actor=actor,
        event_types=("safeguarding.export_requested",),
        window=timedelta(hours=1),
        maximum=5,
    )
    now = utc_now()
    row = MessagingEvidenceExport(
        school_id=actor.school.id,
        conversation_id=conversation.id,
        review_session_id=session.id,
        created_by_membership_id=actor.membership.id,
        export_mode=export_mode,
        reason_category=validate_reason_category(reason_category),
        justification=normalized_reason(justification),
        include_internal_notes=include_internal_notes,
        state="requested",
        expires_at=now + EXPORT_TTL,
        counts={},
    )
    db.add(row)
    db.flush()
    audit_event(
        db,
        actor=actor,
        school_id=actor.school.id,
        event_type="safeguarding.export_requested",
        conversation_id=conversation.id,
        detail={
            "export": str(row.public_id),
            "mode": export_mode,
            "reason_category": row.reason_category,
            "include_internal_notes": include_internal_notes,
        },
    )
    db.commit()

    messages = (
        db.query(Message)
        .filter(
            Message.school_id == actor.school.id,
            Message.conversation_id == conversation.id,
        )
        .order_by(Message.sequence)
        .all()
    )
    if len(messages) > MAX_EXPORT_MESSAGES:
        row.state = "failed"
        row.failure_code = "message_limit_exceeded"
        audit_event(
            db,
            actor=actor,
            school_id=actor.school.id,
            event_type="safeguarding.export_failed",
            conversation_id=conversation.id,
            detail={"export": str(row.public_id), "failure_code": row.failure_code},
        )
        db.commit()
        raise SafeguardingValidationError("Conversation exceeds the evidence export message limit")
    message_ids = [message.id for message in messages]
    participants = (
        db.query(ConversationParticipant)
        .filter(ConversationParticipant.conversation_id == conversation.id)
        .order_by(ConversationParticipant.id)
        .all()
    )
    sender_by_id = {participant.id: participant for participant in participants}
    photos = (
        db.query(MessageMedia)
        .filter(
            MessageMedia.school_id == actor.school.id,
            MessageMedia.conversation_id == conversation.id,
            MessageMedia.message_id.in_(message_ids),
            MessageMedia.state == "attached",
        )
        .order_by(MessageMedia.message_id, MessageMedia.sort_order, MessageMedia.id)
        .all()
        if message_ids
        else []
    )
    voices = (
        db.query(MessageVoiceMedia)
        .filter(
            MessageVoiceMedia.school_id == actor.school.id,
            MessageVoiceMedia.conversation_id == conversation.id,
            MessageVoiceMedia.message_id.in_(message_ids),
            MessageVoiceMedia.state == "attached",
        )
        .order_by(MessageVoiceMedia.message_id, MessageVoiceMedia.id)
        .all()
        if message_ids
        else []
    )
    if len(photos) + len(voices) > MAX_EXPORT_MEDIA:
        row.state = "failed"
        row.failure_code = "media_count_limit_exceeded"
        audit_event(
            db,
            actor=actor,
            school_id=actor.school.id,
            event_type="safeguarding.export_failed",
            conversation_id=conversation.id,
            detail={"export": str(row.public_id), "failure_code": row.failure_code},
        )
        db.commit()
        raise SafeguardingValidationError("Conversation exceeds the evidence export media limit")
    notes = (
        db.query(SafeguardingInternalNote)
        .filter(SafeguardingInternalNote.conversation_id == conversation.id)
        .order_by(SafeguardingInternalNote.created_at, SafeguardingInternalNote.id)
        .all()
        if include_internal_notes
        else []
    )
    moderation = (
        db.query(MessagingModerationAction)
        .filter(MessagingModerationAction.conversation_id == conversation.id)
        .order_by(MessagingModerationAction.occurred_at, MessagingModerationAction.id)
        .all()
    )
    receipts = (
        db.query(MessageReceiptEvent)
        .filter(MessageReceiptEvent.conversation_id == conversation.id)
        .order_by(MessageReceiptEvent.recorded_at, MessageReceiptEvent.id)
        .all()
    )
    flags = (
        db.query(SafeguardingFlag)
        .filter(SafeguardingFlag.conversation_id == conversation.id)
        .order_by(SafeguardingFlag.created_at, SafeguardingFlag.id)
        .all()
        if export_mode == "internal"
        else []
    )

    photos_by_message: dict[int, list[MessageMedia]] = {}
    for photo in photos:
        photos_by_message.setdefault(int(photo.message_id), []).append(photo)
    voices_by_message = {int(voice.message_id): voice for voice in voices}
    attachments: list[dict[str, Any]] = []
    total_bytes = 0
    generated_at = utc_now()
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    storage_key = f"{row.public_id}.zip"
    target = export_path(storage_key)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    transcript = _transcript_html(
        school=actor.school,
        conversation=conversation,
        participants=participants,
        messages=messages,
        sender_by_id=sender_by_id,
        notes=notes,
        generated_at=generated_at,
    )
    total_bytes += len(transcript)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=False) as archive:
            transcript_name = _safe_zip_name("transcript.html")
            archive.writestr(transcript_name, transcript)
            transcript_sha = hashlib.sha256(transcript).hexdigest()
            for message in messages:
                for photo in photos_by_message.get(message.id, []):
                    path, content_type = protected_media_file(photo, "full")
                    size = path.stat().st_size
                    checksum = file_sha256(path)
                    if checksum != photo.checksum_sha256:
                        raise SafeguardingConflict("Protected photo integrity check failed")
                    total_bytes += size
                    if total_bytes > MAX_EXPORT_BYTES:
                        raise SafeguardingValidationError("Evidence export exceeds the size limit")
                    suffix = ".webp" if content_type == "image/webp" else ".jpg"
                    name = _safe_zip_name(
                        f"media/{message.sequence:06d}-photo-{photo.sort_order + 1}-{photo.public_id}{suffix}"
                    )
                    archive.write(path, name)
                    attachments.append(
                        {
                            "message_id": str(message.public_id),
                            "kind": "photo",
                            "file": name,
                            "content_type": content_type,
                            "size_bytes": size,
                            "sha256": checksum,
                            "original_filename": photo.original_filename_safe,
                            "tombstoned": message.state == "tombstoned",
                        }
                    )
                voice = voices_by_message.get(message.id)
                if voice:
                    path, content_type = protected_voice_file(voice)
                    size = path.stat().st_size
                    checksum = file_sha256(path)
                    if checksum != voice.checksum_sha256:
                        raise SafeguardingConflict("Protected voice integrity check failed")
                    total_bytes += size
                    if total_bytes > MAX_EXPORT_BYTES:
                        raise SafeguardingValidationError("Evidence export exceeds the size limit")
                    name = _safe_zip_name(
                        f"media/{message.sequence:06d}-voice-{voice.public_id}.m4a"
                    )
                    archive.write(path, name)
                    attachments.append(
                        {
                            "message_id": str(message.public_id),
                            "kind": "voice_note",
                            "file": name,
                            "content_type": content_type,
                            "size_bytes": size,
                            "duration_ms": voice.duration_ms,
                            "sha256": checksum,
                            "original_filename": "voice-note.m4a",
                            "tombstoned": message.state == "tombstoned",
                        }
                    )

            manifest_payload: dict[str, Any] = {
                "schema_version": "chh.messaging.evidence.v1",
                "privacy_mode": export_mode,
                "export": {
                    "id": str(row.public_id),
                    "created_by_user_id": actor.user.id,
                    "created_by_membership_id": actor.membership.id,
                    "reason_category": row.reason_category,
                    "reason": row.justification,
                    "generated_at_utc": _iso_utc(generated_at),
                    "expires_at_utc": _iso_utc(row.expires_at),
                    "includes_internal_notes": include_internal_notes,
                },
                "school": {
                    "id": actor.school.id,
                    "name": actor.school.name,
                    "timezone": actor.school.timezone,
                },
                "conversation": {
                    "id": str(conversation.public_id),
                    "kind": conversation.kind,
                    "status": conversation.status,
                    "restriction_type": conversation.restriction_type if export_mode == "internal" else None,
                    "created_at_utc": _iso_utc(conversation.created_at),
                    "created_at_school_local": _iso_local(conversation.created_at, actor.school),
                    "last_message_sequence": int(conversation.last_message_sequence or 0),
                },
                "participants": [
                    {
                        "reference": f"participant-{participant.id}",
                        "kind": participant.participant_kind,
                        "side": participant.side,
                        "display_name": participant.display_name_snapshot,
                        "joined_at_utc": _iso_utc(participant.joined_at),
                        "left_at_utc": _iso_utc(participant.left_at),
                    }
                    for participant in participants
                ],
                "messages": [
                    {
                        "id": str(message.public_id),
                        "sequence": int(message.sequence),
                        "sender_reference": f"participant-{message.sender_participant_id}",
                        "sender_display_name": message.sender_display_name_snapshot,
                        "sender_role": sender_by_id.get(message.sender_participant_id).participant_kind
                        if sender_by_id.get(message.sender_participant_id)
                        else None,
                        "type": message.message_type,
                        "body": message.body,
                        "state": message.state,
                        "urgent": bool(message.urgent),
                        "created_at_utc": _iso_utc(message.created_at),
                        "created_at_school_local": _iso_local(message.created_at, actor.school),
                    }
                    for message in messages
                ],
                "attachments": attachments,
                "receipt_evidence": [
                    {
                        "participant_reference": f"participant-{receipt.participant_id}",
                        "event_type": receipt.event_type,
                        "through_sequence": int(receipt.through_sequence),
                        "occurred_at_utc": _iso_utc(receipt.occurred_at),
                        "recorded_at_utc": _iso_utc(receipt.recorded_at),
                    }
                    for receipt in receipts
                ],
                "moderation_history": [
                    {
                        "event_id": str(action.event_id),
                        "action": action.action,
                        "message_id": next(
                            (str(message.public_id) for message in messages if message.id == action.message_id),
                            None,
                        ),
                        "restriction_type": action.restriction_type,
                        "reason_category": action.reason_category if export_mode == "internal" else None,
                        "confidential_reason": action.confidential_reason if export_mode == "internal" else None,
                        "participant_safe_reason": action.participant_safe_reason,
                        "prior_state_hash": action.prior_state_hash,
                        "new_state_hash": action.new_state_hash,
                        "occurred_at_utc": _iso_utc(action.occurred_at),
                    }
                    for action in moderation
                ],
                "flags": [
                    {
                        "id": str(flag.public_id),
                        "category": flag.category,
                        "severity": flag.severity,
                        "status": flag.status,
                        "message_id": next(
                            (str(message.public_id) for message in messages if message.id == flag.message_id),
                            None,
                        ),
                    }
                    for flag in flags
                ],
                "internal_notes": [
                    {
                        "id": str(note.public_id),
                        "label": "internal_safeguarding_note",
                        "body": note.body,
                        "created_at_utc": _iso_utc(note.created_at),
                        "correction_of": next(
                            (str(other.public_id) for other in notes if other.id == note.correction_of_note_id),
                            None,
                        ),
                    }
                    for note in notes
                ],
                "files": [
                    {
                        "file": transcript_name,
                        "size_bytes": len(transcript),
                        "sha256": transcript_sha,
                    },
                    *[
                        {
                            "file": attachment["file"],
                            "size_bytes": attachment["size_bytes"],
                            "sha256": attachment["sha256"],
                        }
                        for attachment in attachments
                    ],
                ],
            }
            manifest_hash = hashlib.sha256(_canonical_json(manifest_payload)).hexdigest()
            manifest = {
                **manifest_payload,
                "integrity": {
                    "algorithm": "SHA-256",
                    "canonical_payload_sha256": manifest_hash,
                    "canonicalization": "UTF-8 JSON, sorted keys, compact separators, integrity omitted",
                },
            }
            archive.writestr(_safe_zip_name("manifest.json"), _canonical_json(manifest))
        if temporary.stat().st_size > MAX_EXPORT_BYTES:
            raise SafeguardingValidationError("Evidence export exceeds the size limit")
        os.replace(temporary, target)
        row.state = "ready"
        row.artifact_storage_key = storage_key
        row.artifact_sha256 = file_sha256(target)
        row.manifest_sha256 = manifest_hash
        row.size_bytes = target.stat().st_size
        row.counts = {
            "messages": len(messages),
            "participants": len(participants),
            "attachments": len(attachments),
            "receipts": len(receipts),
            "moderation_actions": len(moderation),
            "internal_notes": len(notes),
        }
        row.generated_at = generated_at
        audit_event(
            db,
            actor=actor,
            school_id=actor.school.id,
            event_type="safeguarding.export_generated",
            conversation_id=conversation.id,
            detail={
                "export": str(row.public_id),
                "artifact_sha256": row.artifact_sha256,
                "manifest_sha256": row.manifest_sha256,
                "size_bytes": row.size_bytes,
                "counts": row.counts,
            },
        )
        db.commit()
        db.refresh(row)
        return row
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        db.rollback()
        failed = db.query(MessagingEvidenceExport).filter(MessagingEvidenceExport.id == row.id).first()
        if failed is not None and failed.state != "ready":
            failed.state = "failed"
            failed.failure_code = (
                "validation_failed" if isinstance(exc, SafeguardingValidationError) else "generation_failed"
            )
            audit_event(
                db,
                actor=actor,
                school_id=actor.school.id,
                event_type="safeguarding.export_failed",
                conversation_id=conversation.id,
                detail={"export": str(failed.public_id), "failure_code": failed.failure_code},
            )
            db.commit()
        raise


def evidence_export_file(
    db: Session,
    *,
    actor: SafeguardingActor,
    public_id: UUID,
) -> tuple[MessagingEvidenceExport, Path]:
    require_permission(actor, PERMISSION_EXPORT)
    row = (
        db.query(MessagingEvidenceExport)
        .filter(
            MessagingEvidenceExport.public_id == public_id,
            MessagingEvidenceExport.school_id == actor.school.id,
        )
        .with_for_update()
        .first()
    )
    if row is None:
        raise SafeguardingNotFound("Evidence export not found")
    if row.state != "ready" or as_aware(row.expires_at) <= utc_now():
        raise SafeguardingExpired("Evidence export has expired")
    if row.download_count >= row.max_downloads:
        raise SafeguardingExpired("Evidence export download limit reached")
    path = export_path(row.artifact_storage_key)
    if not path.is_file() or file_sha256(path) != row.artifact_sha256:
        raise SafeguardingConflict("Evidence export integrity check failed")
    row.download_count += 1
    row.last_downloaded_at = utc_now()
    audit_event(
        db,
        actor=actor,
        school_id=actor.school.id,
        event_type="safeguarding.export_downloaded",
        conversation_id=row.conversation_id,
        detail={
            "export": str(row.public_id),
            "download_number": row.download_count,
            "artifact_sha256": row.artifact_sha256,
        },
    )
    db.commit()
    return row, path


def cleanup_expired_safeguarding_state(db: Session, *, limit: int = 100) -> dict[str, int]:
    now = utc_now()
    expired_sessions = (
        db.query(SafeguardingReviewSession)
        .filter(
            SafeguardingReviewSession.expires_at <= now,
            SafeguardingReviewSession.ended_at.is_(None),
            SafeguardingReviewSession.revoked_at.is_(None),
        )
        .order_by(SafeguardingReviewSession.expires_at, SafeguardingReviewSession.id)
        .limit(limit)
        .all()
    )
    for session in expired_sessions:
        session.ended_at = now
        session.end_reason = "expired"
        audit_event(
            db,
            actor=None,
            school_id=session.school_id,
            event_type="safeguarding.review_expired",
            conversation_id=session.conversation_id,
            detail={"review_session": str(session.public_id)},
        )
    expired_exports = (
        db.query(MessagingEvidenceExport)
        .filter(
            MessagingEvidenceExport.expires_at <= now,
            MessagingEvidenceExport.state.in_(("ready", "failed", "requested")),
        )
        .order_by(MessagingEvidenceExport.expires_at, MessagingEvidenceExport.id)
        .limit(limit)
        .all()
    )
    deleted = 0
    for export in expired_exports:
        if export.artifact_storage_key:
            export_path(export.artifact_storage_key).unlink(missing_ok=True)
            deleted += 1
        export.state = "expired"
        export.deleted_at = now
        audit_event(
            db,
            actor=None,
            school_id=export.school_id,
            event_type="safeguarding.export_expired",
            conversation_id=export.conversation_id,
            detail={"export": str(export.public_id)},
        )
    db.commit()
    return {
        "expired_sessions": len(expired_sessions),
        "expired_exports": len(expired_exports),
        "deleted_files": deleted,
    }

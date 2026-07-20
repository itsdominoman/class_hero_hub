from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import String, and_, cast, exists, func, or_
from sqlalchemy.orm import Session, aliased

from .. import auth
from ..database import get_db
from ..message_media_service import media_payload, protected_media_file
from ..message_voice_service import protected_voice_file, voice_payload
from ..models_school import (
    AuditLog,
    ClassSection,
    Conversation,
    ConversationParticipant,
    Enrolment,
    GradeLevel,
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
    Student,
    User,
)
from ..safeguarding_service import (
    PERMISSION_EXPORT,
    PERMISSION_MANAGE,
    PERMISSION_MODERATE,
    PERMISSION_REVIEW,
    SAFEGUARDING_PERMISSIONS,
    SafeguardingAccessDenied,
    SafeguardingActor,
    SafeguardingConflict,
    SafeguardingError,
    SafeguardingExpired,
    SafeguardingNotFound,
    SafeguardingRateLimited,
    SafeguardingValidationError,
    active_review_session,
    add_internal_note,
    apply_restriction,
    audit_event,
    cleanup_expired_safeguarding_state,
    close_conversation,
    create_evidence_export,
    create_flag,
    end_review_session,
    enforce_rate_limit,
    evidence_export_file,
    grant_permission,
    moderate_message,
    remove_restriction,
    reopen_conversation,
    require_permission,
    resolve_actor,
    revoke_permission,
    revoke_review_session,
    start_review_session,
    update_flag_status,
    utc_now,
)
from ..school_scope import write_audit


router = APIRouter()
MAX_SEARCH_RESULTS = 50
MAX_REVIEW_MESSAGES = 100


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"


def _school_id(request: Request) -> int:
    raw = request.headers.get("X-School-Id")
    try:
        value = int(raw or "")
    except ValueError:
        raise HTTPException(status_code=400, detail="Valid school context required")
    if value <= 0:
        raise HTTPException(status_code=400, detail="Valid school context required")
    return value


def _membership_id(request: Request) -> int | None:
    raw = request.headers.get("X-Membership-Id")
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid membership context")
    if value <= 0:
        raise HTTPException(status_code=400, detail="Invalid membership context")
    return value


def _correlation_id(request: Request) -> str:
    supplied = (request.headers.get("X-Request-Id") or "").strip()
    if supplied and len(supplied) <= 96 and all(character.isalnum() or character in "-_.:" for character in supplied):
        return supplied
    return str(uuid4())


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, SafeguardingNotFound):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, SafeguardingExpired):
        raise HTTPException(status_code=410, detail=str(exc))
    if isinstance(exc, SafeguardingRateLimited):
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "60"})
    if isinstance(exc, SafeguardingValidationError):
        raise HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, SafeguardingConflict):
        raise HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, SafeguardingAccessDenied):
        raise HTTPException(status_code=403, detail=str(exc))
    raise exc


def require_safeguarding_actor(
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> SafeguardingActor:
    school_id = _school_id(request)
    try:
        return resolve_actor(
            db,
            user=current_user,
            school_id=school_id,
            membership_id=_membership_id(request),
        )
    except SafeguardingError as exc:
        # A denied attempt is recorded without target content or guessed resource data.
        if db.query(School.id).filter(School.id == school_id).first() is not None:
            write_audit(
                db,
                current_user,
                "safeguarding.access_denied",
                ("messaging_safeguarding", None),
                {"school_id": school_id, "reason": exc.__class__.__name__},
                school_id=school_id,
            )
            db.commit()
        _raise_http(exc)


def _require(
    db: Session,
    *,
    actor: SafeguardingActor,
    permission: str,
    conversation_id: int | None = None,
) -> None:
    try:
        require_permission(actor, permission)
    except SafeguardingAccessDenied as exc:
        audit_event(
            db,
            actor=actor,
            school_id=actor.school.id,
            event_type="safeguarding.access_denied",
            conversation_id=conversation_id,
            detail={"required_permission": permission},
        )
        db.commit()
        _raise_http(exc)


class PermissionGrantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    membership_id: int = Field(gt=0)
    permission: str = Field(min_length=3, max_length=80)
    reason: str = Field(min_length=3, max_length=1000)


class PermissionRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=1000)


class ReviewRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=48)


class ReviewStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: UUID
    reason_category: str = Field(min_length=3, max_length=48)
    justification: str = Field(min_length=8, max_length=2000)
    acknowledgement: bool
    ttl_minutes: int = Field(default=30, ge=5, le=60)


class ModerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason_category: str = Field(min_length=3, max_length=48)
    confidential_reason: str = Field(min_length=8, max_length=4000)
    participant_safe_reason: str | None = Field(default=None, max_length=240)


class RestrictionRequest(ModerationRequest):
    restriction_type: Literal["family_replies", "staff_replies", "both_replies", "read_only"]
    reopening_requires_approval: bool = False


class CloseRequest(ModerationRequest):
    reopening_requires_approval: bool = True


class ReopenRequest(ModerationRequest):
    remove_existing_restriction: bool = False


class InternalNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=3, max_length=10000)
    correction_of_note_id: UUID | None = None


class FlagRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: UUID | None = None
    category: str = Field(min_length=3, max_length=48)
    severity: Literal["low", "medium", "high", "critical"]
    internal_note: str | None = Field(default=None, max_length=4000)
    assigned_membership_id: int | None = Field(default=None, gt=0)


class FlagStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["open", "follow_up", "resolved"]
    resolution_note: str | None = Field(default=None, max_length=4000)


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    export_mode: Literal["internal"] = "internal"
    reason_category: str = Field(min_length=3, max_length=48)
    justification: str = Field(min_length=8, max_length=2000)
    include_internal_notes: bool = False


@router.get("/availability")
def availability(
    request: Request,
    response: Response,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Return only whether this exact signed-in membership has any active grant.

    The application shell uses this non-sensitive probe to hide navigation without
    generating routine denied-access audit noise for every ordinary staff session.
    Protected endpoints still resolve and audit the full safeguarding actor.
    """
    _private(response)
    school_id = _school_id(request)
    membership_id = _membership_id(request)
    if membership_id is None or current_user.status != "active":
        return {"available": False}
    available = (
        db.query(MessagingPermissionGrant.id)
        .join(Membership, Membership.id == MessagingPermissionGrant.membership_id)
        .join(School, School.id == MessagingPermissionGrant.school_id)
        .filter(
            MessagingPermissionGrant.school_id == school_id,
            MessagingPermissionGrant.membership_id == membership_id,
            MessagingPermissionGrant.revoked_at.is_(None),
            Membership.school_id == school_id,
            Membership.user_id == current_user.id,
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            School.status.in_(("pending_setup", "active")),
        )
        .first()
        is not None
    )
    return {"available": available}


@router.get("/context")
def context(
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
):
    _private(response)
    return {
        "school": {
            "id": actor.school.id,
            "name": actor.school.name,
            "timezone": actor.school.timezone,
        },
        "reviewer": {
            "user_id": actor.user.id,
            "membership_id": actor.membership.id,
            "name": actor.user.name,
            "role": actor.membership.role,
        },
        "permissions": sorted(actor.permissions),
        "review_ttl_minutes": 30,
        "audit_notice": True,
    }


@router.get("/permissions")
def permissions(
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    _require(db, actor=actor, permission=PERMISSION_MANAGE)
    rows = (
        db.query(Membership, User)
        .join(User, User.id == Membership.user_id)
        .filter(
            Membership.school_id == actor.school.id,
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            User.status == "active",
        )
        .order_by(func.lower(User.name), Membership.id)
        .limit(500)
        .all()
    )
    grants = (
        db.query(MessagingPermissionGrant)
        .filter(
            MessagingPermissionGrant.school_id == actor.school.id,
            MessagingPermissionGrant.revoked_at.is_(None),
        )
        .all()
    )
    by_membership: dict[int, list[MessagingPermissionGrant]] = {}
    for grant in grants:
        by_membership.setdefault(grant.membership_id, []).append(grant)
    return {
        "available_permissions": sorted(SAFEGUARDING_PERMISSIONS),
        "memberships": [
            {
                "membership_id": membership.id,
                "name": user.name,
                "role": membership.role,
                "permissions": [
                    {"id": str(grant.public_id), "permission": grant.permission, "granted_at": grant.granted_at}
                    for grant in sorted(by_membership.get(membership.id, []), key=lambda item: item.permission)
                ],
            }
            for membership, user in rows
        ],
    }


@router.post("/permissions")
def create_permission(
    body: PermissionGrantRequest,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    membership = (
        db.query(Membership)
        .filter(
            Membership.id == body.membership_id,
            Membership.school_id == actor.school.id,
        )
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    try:
        row = grant_permission(
            db,
            actor=actor,
            membership=membership,
            permission=body.permission,
            reason=body.reason,
        )
        db.commit()
        db.refresh(row)
        return {"id": str(row.public_id), "permission": row.permission, "membership_id": row.membership_id}
    except SafeguardingError as exc:
        db.rollback()
        _raise_http(exc)


@router.post("/permissions/{grant_id}/revoke")
def remove_permission(
    grant_id: UUID,
    body: PermissionRevokeRequest,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    grant = (
        db.query(MessagingPermissionGrant)
        .filter(
            MessagingPermissionGrant.public_id == grant_id,
            MessagingPermissionGrant.school_id == actor.school.id,
        )
        .first()
    )
    if grant is None:
        raise HTTPException(status_code=404, detail="Permission grant not found")
    try:
        revoke_permission(db, actor=actor, grant=grant, reason=body.reason)
        db.commit()
        return {"id": str(grant.public_id), "revoked": True}
    except SafeguardingError as exc:
        db.rollback()
        _raise_http(exc)


def _safe_like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return "%" + escaped + "%"


@router.get("/conversations")
def search_conversations(
    request: Request,
    response: Response,
    student_id: int | None = Query(default=None, gt=0),
    student: str | None = Query(default=None, min_length=1, max_length=120),
    class_section_id: int | None = Query(default=None, gt=0),
    grade_level_id: int | None = Query(default=None, gt=0),
    participant: str | None = Query(default=None, min_length=1, max_length=120),
    participant_role: Literal["staff", "chh_guardian", "fhh_parent"] | None = None,
    conversation_ref: UUID | None = None,
    reference: str | None = Query(default=None, min_length=4, max_length=64),
    class_grade: str | None = Query(default=None, min_length=1, max_length=120),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    conversation_status: str | None = Query(default=None, max_length=32),
    flagged: bool | None = None,
    restricted: bool | None = None,
    closed: bool | None = None,
    branch_id: int | None = Query(default=None, gt=0),
    message_type: Literal["standard", "voice_note", "photo"] | None = None,
    direction: Literal["staff_to_family", "family_to_staff", "staff_internal"] | None = None,
    limit: int = Query(default=30, ge=1, le=MAX_SEARCH_RESULTS),
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    _require(db, actor=actor, permission=PERMISSION_REVIEW)
    try:
        enforce_rate_limit(
            db,
            actor=actor,
            event_types=("safeguarding.search",),
            window=timedelta(minutes=1),
            maximum=30,
        )
    except SafeguardingError as exc:
        _raise_http(exc)
    query = db.query(Conversation).filter(Conversation.school_id == actor.school.id)
    if conversation_ref:
        query = query.filter(Conversation.public_id == conversation_ref)
    if reference:
        normalized_reference = reference.strip().removeprefix("MSG-").removeprefix("msg-")
        if not normalized_reference or any(character not in "0123456789abcdefABCDEF-" for character in normalized_reference):
            raise HTTPException(status_code=422, detail="Invalid conversation reference")
        query = query.filter(cast(Conversation.public_id, String).ilike(f"{normalized_reference}%"))
    if student_id:
        query = query.filter(Conversation.student_id == student_id)
    if branch_id:
        query = query.filter(Conversation.branch_campus_id == branch_id)
    if conversation_status:
        query = query.filter(Conversation.status == conversation_status)
    activity = func.coalesce(Conversation.last_message_at, Conversation.created_at)
    if date_from:
        query = query.filter(activity >= date_from)
    if date_to:
        query = query.filter(activity <= date_to)
    if restricted is True:
        query = query.filter(Conversation.restriction_type.is_not(None))
    elif restricted is False:
        query = query.filter(Conversation.restriction_type.is_(None))
    if closed is True:
        query = query.filter(Conversation.status != "active")
    elif closed is False:
        query = query.filter(Conversation.status == "active")
    if student:
        pattern = _safe_like(student.strip())
        query = query.filter(
            exists().where(
                and_(
                    Student.id == Conversation.student_id,
                    Student.school_id == actor.school.id,
                    or_(
                        func.coalesce(Student.first_name, "").ilike(pattern, escape="\\"),
                        func.coalesce(Student.last_name, "").ilike(pattern, escape="\\"),
                        func.coalesce(Student.preferred_name, "").ilike(pattern, escape="\\"),
                        func.coalesce(Student.name_ar, "").ilike(pattern, escape="\\"),
                    ),
                )
            )
        )
    if class_section_id or grade_level_id or class_grade:
        class_grade_pattern = _safe_like(class_grade.strip()) if class_grade else None
        enrolment_exists = exists().where(
            and_(
                Enrolment.school_id == actor.school.id,
                Enrolment.student_id == Conversation.student_id,
                Enrolment.valid_to.is_(None),
                *([Enrolment.class_section_id == class_section_id] if class_section_id else []),
                *(
                    [
                        exists().where(
                            and_(
                                ClassSection.id == Enrolment.class_section_id,
                                ClassSection.school_id == actor.school.id,
                                ClassSection.grade_level_id == grade_level_id,
                            )
                        )
                    ]
                    if grade_level_id
                    else []
                ),
                *(
                    [
                        exists().where(
                            and_(
                                ClassSection.id == Enrolment.class_section_id,
                                ClassSection.school_id == actor.school.id,
                                or_(
                                    ClassSection.name.ilike(class_grade_pattern, escape="\\"),
                                    ClassSection.name_ar.ilike(class_grade_pattern, escape="\\"),
                                    exists().where(
                                        and_(
                                            GradeLevel.id == ClassSection.grade_level_id,
                                            GradeLevel.school_id == actor.school.id,
                                            or_(
                                                GradeLevel.name.ilike(class_grade_pattern, escape="\\"),
                                                GradeLevel.name_ar.ilike(class_grade_pattern, escape="\\"),
                                            ),
                                        )
                                    ),
                                ),
                            )
                        )
                    ]
                    if class_grade_pattern
                    else []
                ),
            )
        )
        query = query.filter(enrolment_exists)
    if participant or participant_role:
        participant_filters = [ConversationParticipant.conversation_id == Conversation.id]
        if participant:
            participant_filters.append(
                ConversationParticipant.display_name_snapshot.ilike(_safe_like(participant.strip()), escape="\\")
            )
        if participant_role:
            participant_filters.append(ConversationParticipant.participant_kind == participant_role)
        query = query.filter(exists().where(and_(*participant_filters)))
    if flagged is not None:
        flag_exists = exists().where(SafeguardingFlag.conversation_id == Conversation.id)
        query = query.filter(flag_exists if flagged else ~flag_exists)
    if message_type:
        message_filter = [Message.conversation_id == Conversation.id]
        if message_type == "photo":
            message_filter.append(
                exists().where(
                    and_(
                        MessageMedia.message_id == Message.id,
                        MessageMedia.state == "attached",
                    )
                )
            )
        else:
            message_filter.append(Message.message_type == message_type)
        query = query.filter(exists().where(and_(*message_filter)))
    if direction:
        sender = aliased(ConversationParticipant)
        direction_filter = [Message.conversation_id == Conversation.id, sender.id == Message.sender_participant_id]
        if direction == "staff_to_family":
            direction_filter.extend([sender.side == "staff", Conversation.kind != "staff_direct"])
        elif direction == "family_to_staff":
            direction_filter.append(sender.side == "guardian")
        else:
            direction_filter.extend([sender.side == "staff", Conversation.kind == "staff_direct"])
        query = query.filter(exists().where(and_(*direction_filter)))
    rows = query.order_by(activity.desc(), Conversation.id.desc()).limit(limit).all()
    student_ids = {row.student_id for row in rows if row.student_id is not None}
    students = {
        row.id: row
        for row in db.query(Student).filter(Student.id.in_(student_ids)).all()
    } if student_ids else {}
    participants = (
        db.query(ConversationParticipant)
        .filter(ConversationParticipant.conversation_id.in_([row.id for row in rows]))
        .order_by(ConversationParticipant.id)
        .all()
        if rows else []
    )
    by_conversation: dict[int, list[ConversationParticipant]] = {}
    for row in participants:
        by_conversation.setdefault(row.conversation_id, []).append(row)
    flag_counts = dict(
        db.query(SafeguardingFlag.conversation_id, func.count(SafeguardingFlag.id))
        .filter(SafeguardingFlag.conversation_id.in_([row.id for row in rows]))
        .group_by(SafeguardingFlag.conversation_id)
        .all()
    ) if rows else {}
    audit_event(
        db,
        actor=actor,
        school_id=actor.school.id,
        event_type="safeguarding.search",
        detail={
            "filter_names": sorted(
                name for name, value in {
                    "student_id": student_id,
                    "student": student,
                    "class_section_id": class_section_id,
                    "grade_level_id": grade_level_id,
                    "participant": participant,
                    "participant_role": participant_role,
                    "conversation_ref": conversation_ref,
                    "reference": reference,
                    "class_grade": class_grade,
                    "date_from": date_from,
                    "date_to": date_to,
                    "conversation_status": conversation_status,
                    "flagged": flagged,
                    "restricted": restricted,
                    "closed": closed,
                    "branch_id": branch_id,
                    "message_type": message_type,
                    "direction": direction,
                }.items() if value is not None
            ),
            "result_count": len(rows),
            "limit": limit,
        },
        correlation_id=_correlation_id(request),
    )
    db.commit()
    return {
        "items": [
            {
                "conversation_id": str(row.public_id),
                "reference": f"MSG-{str(row.public_id).split('-')[0].upper()}",
                "kind": row.kind,
                "status": row.status,
                "participant_state": "closed" if row.status != "active" else "read_only" if row.restriction_type else "active",
                "restricted": row.restriction_type is not None,
                "flag_count": int(flag_counts.get(row.id, 0)),
                "student": (
                    {
                        "id": students[row.student_id].id,
                        "display_name": " ".join(
                            part for part in (
                                students[row.student_id].preferred_name or students[row.student_id].first_name,
                                students[row.student_id].last_name,
                            ) if part
                        ),
                        "name_ar": students[row.student_id].name_ar,
                    }
                    if row.student_id in students else None
                ),
                "participants": [
                    {
                        "display_name": item.display_name_snapshot,
                        "kind": item.participant_kind,
                        "side": item.side,
                    }
                    for item in by_conversation.get(row.id, [])
                    if item.left_at is None
                ],
                "branch_id": row.branch_campus_id,
                "last_activity_at": row.last_message_at or row.created_at,
            }
            for row in rows
        ]
    }


@router.post("/reviews")
def create_review(
    body: ReviewStartRequest,
    request: Request,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.public_id == body.conversation_id,
            Conversation.school_id == actor.school.id,
        )
        .first()
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    try:
        session = start_review_session(
            db,
            actor=actor,
            conversation=conversation,
            reason_category=body.reason_category,
            justification=body.justification,
            acknowledgement=body.acknowledgement,
            ttl_minutes=body.ttl_minutes,
            correlation_id=_correlation_id(request),
        )
        db.commit()
        db.refresh(session)
        return {
            "review_session_id": str(session.public_id),
            "conversation_id": str(conversation.public_id),
            "reason_category": session.reason_category,
            "started_at": session.started_at,
            "expires_at": session.expires_at,
        }
    except SafeguardingError as exc:
        db.rollback()
        _raise_http(exc)


def _review(
    db: Session,
    *,
    actor: SafeguardingActor,
    session_id: UUID,
) -> tuple[SafeguardingReviewSession, Conversation]:
    try:
        return active_review_session(db, actor=actor, public_id=session_id)
    except SafeguardingError as exc:
        _raise_http(exc)


def _message_public_map(db: Session, message_ids: set[int]) -> dict[int, str]:
    if not message_ids:
        return {}
    return {
        row.id: str(row.public_id)
        for row in db.query(Message).filter(Message.id.in_(message_ids)).all()
    }


@router.get("/reviews/{session_id}")
def review_detail(
    session_id: UUID,
    request: Request,
    response: Response,
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=MAX_REVIEW_MESSAGES, ge=1, le=MAX_REVIEW_MESSAGES),
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    session, conversation = _review(db, actor=actor, session_id=session_id)
    try:
        enforce_rate_limit(
            db,
            actor=actor,
            event_types=("safeguarding.conversation_opened",),
            window=timedelta(minutes=1),
            maximum=120,
        )
    except SafeguardingError as exc:
        _raise_http(exc)
    participants = (
        db.query(ConversationParticipant)
        .filter(ConversationParticipant.conversation_id == conversation.id)
        .order_by(ConversationParticipant.id)
        .all()
    )
    participants_by_id = {row.id: row for row in participants}
    messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation.id,
            Message.sequence > after_sequence,
        )
        .order_by(Message.sequence)
        .limit(limit + 1)
        .all()
    )
    has_more = len(messages) > limit
    messages = messages[:limit]
    message_ids = [row.id for row in messages]
    photos = (
        db.query(MessageMedia)
        .filter(
            MessageMedia.message_id.in_(message_ids),
            MessageMedia.state == "attached",
        )
        .order_by(MessageMedia.message_id, MessageMedia.sort_order, MessageMedia.id)
        .all()
        if message_ids else []
    )
    voices = (
        db.query(MessageVoiceMedia)
        .filter(
            MessageVoiceMedia.message_id.in_(message_ids),
            MessageVoiceMedia.state == "attached",
        )
        .all()
        if message_ids else []
    )
    photos_by_message: dict[int, list[MessageMedia]] = {}
    for photo in photos:
        photos_by_message.setdefault(photo.message_id, []).append(photo)
    voices_by_message = {voice.message_id: voice for voice in voices}
    flags = (
        db.query(SafeguardingFlag)
        .filter(SafeguardingFlag.conversation_id == conversation.id)
        .order_by(SafeguardingFlag.created_at, SafeguardingFlag.id)
        .all()
    )
    flags_by_message: dict[int | None, list[SafeguardingFlag]] = {}
    for flag in flags:
        flags_by_message.setdefault(flag.message_id, []).append(flag)
    notes = (
        db.query(SafeguardingInternalNote)
        .filter(SafeguardingInternalNote.conversation_id == conversation.id)
        .order_by(SafeguardingInternalNote.created_at, SafeguardingInternalNote.id)
        .all()
    )
    moderation = (
        db.query(MessagingModerationAction)
        .filter(MessagingModerationAction.conversation_id == conversation.id)
        .order_by(MessagingModerationAction.occurred_at, MessagingModerationAction.id)
        .all()
    )
    audit = (
        db.query(MessagingAuditEvent)
        .filter(
            MessagingAuditEvent.conversation_id == conversation.id,
            MessagingAuditEvent.school_id == actor.school.id,
            MessagingAuditEvent.event_type.like("safeguarding.%"),
        )
        .order_by(MessagingAuditEvent.occurred_at.desc(), MessagingAuditEvent.id.desc())
        .limit(250)
        .all()
    )
    receipts = (
        db.query(MessageReceiptEvent)
        .filter(MessageReceiptEvent.conversation_id == conversation.id)
        .order_by(MessageReceiptEvent.recorded_at, MessageReceiptEvent.id)
        .all()
    )
    exports = (
        db.query(MessagingEvidenceExport)
        .filter(MessagingEvidenceExport.conversation_id == conversation.id)
        .order_by(MessagingEvidenceExport.created_at.desc())
        .limit(50)
        .all()
    )
    message_refs = _message_public_map(
        db,
        {
            value
            for value in [
                *(row.message_id for row in moderation),
                *(row.message_id for row in flags),
            ]
            if value is not None
        },
    )
    audit_event(
        db,
        actor=actor,
        school_id=actor.school.id,
        event_type="safeguarding.conversation_opened",
        conversation_id=conversation.id,
        detail={
            "review_session": str(session.public_id),
            "after_sequence": after_sequence,
            "result_count": len(messages),
        },
        correlation_id=_correlation_id(request),
    )
    db.commit()
    return {
        "mode": "safeguarding_review",
        "review": {
            "id": str(session.public_id),
            "reason_category": session.reason_category,
            "justification": session.justification,
            "started_at": session.started_at,
            "expires_at": session.expires_at,
            "audited": True,
        },
        "reviewer": {
            "user_id": actor.user.id,
            "membership_id": actor.membership.id,
            "name": actor.user.name,
            "role": actor.membership.role,
        },
        "school": {"id": actor.school.id, "name": actor.school.name, "timezone": actor.school.timezone},
        "permissions": sorted(actor.permissions),
        "conversation": {
            "id": str(conversation.public_id),
            "reference": f"MSG-{str(conversation.public_id).split('-')[0].upper()}",
            "kind": conversation.kind,
            "status": conversation.status,
            "restriction_type": conversation.restriction_type,
            "reopening_requires_approval": bool(conversation.reopening_requires_approval),
            "created_at": conversation.created_at,
            "last_message_sequence": int(conversation.last_message_sequence or 0),
            "participants": [
                {
                    "reference": f"participant-{participant.id}",
                    "display_name": participant.display_name_snapshot,
                    "kind": participant.participant_kind,
                    "side": participant.side,
                    "joined_at": participant.joined_at,
                    "left_at": participant.left_at,
                    "receipt_cursor": {
                        "delivered_sequence": int(participant.last_delivered_sequence or 0),
                        "read_sequence": int(participant.last_read_sequence or 0),
                    },
                }
                for participant in participants
            ],
        },
        "messages": [
            {
                "id": str(message.public_id),
                "sequence": int(message.sequence),
                "sender_display_name": message.sender_display_name_snapshot,
                "sender_kind": participants_by_id.get(message.sender_participant_id).participant_kind
                if participants_by_id.get(message.sender_participant_id) else None,
                "sender_side": participants_by_id.get(message.sender_participant_id).side
                if participants_by_id.get(message.sender_participant_id) else None,
                "message_type": message.message_type,
                "body": message.body,
                "state": message.state,
                "urgent": bool(message.urgent),
                "created_at": message.created_at,
                "photos": [media_payload(photo) for photo in photos_by_message.get(message.id, [])],
                "voice_note": voice_payload(voices_by_message[message.id]) if message.id in voices_by_message else None,
                "flags": [
                    {
                        "id": str(flag.public_id),
                        "category": flag.category,
                        "severity": flag.severity,
                        "status": flag.status,
                    }
                    for flag in flags_by_message.get(message.id, [])
                ],
            }
            for message in messages
        ],
        "next_after_sequence": int(messages[-1].sequence) if has_more and messages else None,
        "receipt_evidence": [
            {
                "participant_reference": f"participant-{receipt.participant_id}",
                "event_type": receipt.event_type,
                "through_sequence": int(receipt.through_sequence),
                "occurred_at": receipt.occurred_at,
                "recorded_at": receipt.recorded_at,
            }
            for receipt in receipts
        ],
        "conversation_flags": [
            {
                "id": str(flag.public_id),
                "message_id": message_refs.get(flag.message_id),
                "category": flag.category,
                "severity": flag.severity,
                "status": flag.status,
                "internal_note": flag.internal_note,
                "assigned_membership_id": flag.assigned_membership_id,
                "created_at": flag.created_at,
                "resolution_note": flag.resolution_note,
            }
            for flag in flags
        ],
        "internal_notes": [
            {
                "id": str(note.public_id),
                "body": note.body,
                "author_membership_id": note.author_membership_id,
                "correction_of_note_id": next(
                    (str(other.public_id) for other in notes if other.id == note.correction_of_note_id),
                    None,
                ),
                "created_at": note.created_at,
            }
            for note in notes
        ],
        "moderation_history": [
            {
                "event_id": str(action.event_id),
                "action": action.action,
                "message_id": message_refs.get(action.message_id),
                "restriction_type": action.restriction_type,
                "reason_category": action.reason_category,
                "confidential_reason": action.confidential_reason,
                "participant_safe_reason": action.participant_safe_reason,
                "actor_membership_id": action.actor_membership_id,
                "prior_state_hash": action.prior_state_hash,
                "new_state_hash": action.new_state_hash,
                "occurred_at": action.occurred_at,
            }
            for action in moderation
        ],
        "audit_history": [
            {
                "event_id": str(event.event_id),
                "action": event.event_type,
                "actor_membership_id": event.actor_membership_id,
                "reason_category": event.detail.get("reason_category") if isinstance(event.detail, dict) else None,
                "metadata": event.detail,
                "correlation_id": event.request_correlation_id,
                "occurred_at": event.occurred_at,
            }
            for event in audit
        ],
        "exports": [
            {
                "id": str(export.public_id),
                "mode": export.export_mode,
                "state": export.state,
                "size_bytes": export.size_bytes,
                "artifact_sha256": export.artifact_sha256,
                "manifest_sha256": export.manifest_sha256,
                "expires_at": export.expires_at,
                "download_count": export.download_count,
                "max_downloads": export.max_downloads,
            }
            for export in exports
        ],
        "capabilities": {
            "can_moderate": PERMISSION_MODERATE in actor.permissions,
            "can_export": PERMISSION_EXPORT in actor.permissions,
            "has_composer": False,
        },
    }


@router.post("/reviews/{session_id}/end")
def end_review(
    session_id: UUID,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    session, _ = _review(db, actor=actor, session_id=session_id)
    end_review_session(db, actor=actor, session=session)
    db.commit()
    return {"review_session_id": str(session.public_id), "ended": True}


@router.get("/reviews/{session_id}/media/{media_id}/{variant}")
def review_photo(
    session_id: UUID,
    media_id: UUID,
    variant: Literal["thumbnail", "full"],
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    session, conversation = _review(db, actor=actor, session_id=session_id)
    row = (
        db.query(MessageMedia)
        .filter(
            MessageMedia.public_id == media_id,
            MessageMedia.school_id == actor.school.id,
            MessageMedia.conversation_id == conversation.id,
            MessageMedia.message_id.is_not(None),
            MessageMedia.state == "attached",
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    try:
        path, content_type = protected_media_file(row, variant)
    except Exception:
        raise HTTPException(status_code=404, detail="Photo not found")
    audit_event(
        db,
        actor=actor,
        school_id=actor.school.id,
        event_type="safeguarding.media_accessed",
        conversation_id=conversation.id,
        message_id=row.message_id,
        detail={"review_session": str(session.public_id), "media_kind": "photo", "variant": variant, "media": str(row.public_id)},
    )
    db.commit()
    return FileResponse(path, media_type=content_type, headers={"Cache-Control": "private, no-store, max-age=0"})


@router.get("/reviews/{session_id}/voice-media/{media_id}")
def review_voice(
    session_id: UUID,
    media_id: UUID,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    session, conversation = _review(db, actor=actor, session_id=session_id)
    row = (
        db.query(MessageVoiceMedia)
        .filter(
            MessageVoiceMedia.public_id == media_id,
            MessageVoiceMedia.school_id == actor.school.id,
            MessageVoiceMedia.conversation_id == conversation.id,
            MessageVoiceMedia.message_id.is_not(None),
            MessageVoiceMedia.state == "attached",
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Voice note not found")
    try:
        path, content_type = protected_voice_file(row)
    except Exception:
        raise HTTPException(status_code=404, detail="Voice note not found")
    audit_event(
        db,
        actor=actor,
        school_id=actor.school.id,
        event_type="safeguarding.media_accessed",
        conversation_id=conversation.id,
        message_id=row.message_id,
        detail={"review_session": str(session.public_id), "media_kind": "voice_note", "media": str(row.public_id)},
    )
    db.commit()
    return FileResponse(
        path,
        media_type=content_type,
        filename="voice-note.m4a",
        headers={"Cache-Control": "private, no-store, max-age=0"},
    )


@router.post("/reviews/{session_id}/restriction")
def restrict(
    session_id: UUID,
    body: RestrictionRequest,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    session, conversation = _review(db, actor=actor, session_id=session_id)
    try:
        action = apply_restriction(
            db,
            actor=actor,
            session=session,
            conversation=conversation,
            restriction_type=body.restriction_type,
            reason_category=body.reason_category,
            confidential_reason=body.confidential_reason,
            reopening_requires_approval=body.reopening_requires_approval,
            participant_safe_reason=body.participant_safe_reason,
        )
        db.commit()
        return {"event_id": str(action.event_id), "restriction_type": conversation.restriction_type}
    except SafeguardingError as exc:
        db.rollback()
        _raise_http(exc)


@router.post("/reviews/{session_id}/revoke")
def revoke_review(
    session_id: UUID,
    body: ReviewRevokeRequest,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    session = (
        db.query(SafeguardingReviewSession)
        .filter(
            SafeguardingReviewSession.public_id == session_id,
            SafeguardingReviewSession.school_id == actor.school.id,
        )
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Review session not found")
    try:
        revoke_review_session(db, actor=actor, session=session, reason=body.reason)
        db.commit()
        return {"review_session_id": str(session.public_id), "revoked": True}
    except SafeguardingError as exc:
        db.rollback()
        _raise_http(exc)


@router.post("/reviews/{session_id}/restriction/remove")
def unrestrict(
    session_id: UUID,
    body: ModerationRequest,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    session, conversation = _review(db, actor=actor, session_id=session_id)
    try:
        action = remove_restriction(
            db,
            actor=actor,
            session=session,
            conversation=conversation,
            reason_category=body.reason_category,
            confidential_reason=body.confidential_reason,
        )
        db.commit()
        return {"event_id": str(action.event_id), "restriction_type": None}
    except SafeguardingError as exc:
        db.rollback()
        _raise_http(exc)


@router.post("/reviews/{session_id}/close")
def close(
    session_id: UUID,
    body: CloseRequest,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    session, conversation = _review(db, actor=actor, session_id=session_id)
    try:
        action = close_conversation(
            db,
            actor=actor,
            session=session,
            conversation=conversation,
            reason_category=body.reason_category,
            confidential_reason=body.confidential_reason,
            requires_approval=body.reopening_requires_approval,
            participant_safe_reason=body.participant_safe_reason,
        )
        db.commit()
        return {"event_id": str(action.event_id), "status": conversation.status}
    except SafeguardingError as exc:
        db.rollback()
        _raise_http(exc)


@router.post("/reviews/{session_id}/reopen")
def reopen(
    session_id: UUID,
    body: ReopenRequest,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    session, conversation = _review(db, actor=actor, session_id=session_id)
    try:
        action = reopen_conversation(
            db,
            actor=actor,
            session=session,
            conversation=conversation,
            reason_category=body.reason_category,
            confidential_reason=body.confidential_reason,
            remove_existing_restriction=body.remove_existing_restriction,
        )
        db.commit()
        return {"event_id": str(action.event_id), "status": conversation.status, "restriction_type": conversation.restriction_type}
    except SafeguardingError as exc:
        db.rollback()
        _raise_http(exc)


@router.post("/reviews/{session_id}/messages/{message_id}/tombstone")
def tombstone(
    session_id: UUID,
    message_id: UUID,
    body: ModerationRequest,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    return _message_action(session_id, message_id, "tombstone", body, response, actor, db)


@router.post("/reviews/{session_id}/messages/{message_id}/restore")
def restore(
    session_id: UUID,
    message_id: UUID,
    body: ModerationRequest,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    return _message_action(session_id, message_id, "restore", body, response, actor, db)


def _message_action(
    session_id: UUID,
    message_id: UUID,
    action_name: str,
    body: ModerationRequest,
    response: Response,
    actor: SafeguardingActor,
    db: Session,
):
    _private(response)
    session, conversation = _review(db, actor=actor, session_id=session_id)
    message = (
        db.query(Message)
        .filter(
            Message.public_id == message_id,
            Message.school_id == actor.school.id,
            Message.conversation_id == conversation.id,
        )
        .first()
    )
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    try:
        action = moderate_message(
            db,
            actor=actor,
            session=session,
            conversation=conversation,
            message=message,
            action=action_name,
            reason_category=body.reason_category,
            confidential_reason=body.confidential_reason,
            participant_safe_reason=body.participant_safe_reason,
        )
        db.commit()
        return {"event_id": str(action.event_id), "message_id": str(message.public_id), "state": message.state}
    except SafeguardingError as exc:
        db.rollback()
        _raise_http(exc)


@router.post("/reviews/{session_id}/notes")
def add_note(
    session_id: UUID,
    body: InternalNoteRequest,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    session, conversation = _review(db, actor=actor, session_id=session_id)
    correction = None
    if body.correction_of_note_id:
        correction = (
            db.query(SafeguardingInternalNote)
            .filter(SafeguardingInternalNote.public_id == body.correction_of_note_id)
            .first()
        )
    try:
        note = add_internal_note(
            db,
            actor=actor,
            session=session,
            conversation=conversation,
            body=body.body,
            correction_of=correction,
        )
        db.commit()
        return {"id": str(note.public_id), "created_at": note.created_at}
    except SafeguardingError as exc:
        db.rollback()
        _raise_http(exc)


@router.post("/reviews/{session_id}/flags")
def add_flag(
    session_id: UUID,
    body: FlagRequest,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    _, conversation = _review(db, actor=actor, session_id=session_id)
    message = None
    if body.message_id:
        message = (
            db.query(Message)
            .filter(
                Message.public_id == body.message_id,
                Message.school_id == actor.school.id,
                Message.conversation_id == conversation.id,
            )
            .first()
        )
        if message is None:
            raise HTTPException(status_code=404, detail="Message not found")
    try:
        flag = create_flag(
            db,
            actor=actor,
            conversation=conversation,
            message=message,
            category=body.category,
            severity=body.severity,
            internal_note=body.internal_note,
            assigned_membership_id=body.assigned_membership_id,
        )
        db.commit()
        return {"id": str(flag.public_id), "status": flag.status}
    except SafeguardingError as exc:
        db.rollback()
        _raise_http(exc)


@router.post("/reviews/{session_id}/flags/{flag_id}/status")
def change_flag_status(
    session_id: UUID,
    flag_id: UUID,
    body: FlagStatusRequest,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    _, conversation = _review(db, actor=actor, session_id=session_id)
    flag = (
        db.query(SafeguardingFlag)
        .filter(
            SafeguardingFlag.public_id == flag_id,
            SafeguardingFlag.school_id == actor.school.id,
            SafeguardingFlag.conversation_id == conversation.id,
        )
        .first()
    )
    if flag is None:
        raise HTTPException(status_code=404, detail="Flag not found")
    try:
        update_flag_status(
            db,
            actor=actor,
            flag=flag,
            status=body.status,
            resolution_note=body.resolution_note,
        )
        db.commit()
        return {"id": str(flag.public_id), "status": flag.status}
    except SafeguardingError as exc:
        db.rollback()
        _raise_http(exc)


@router.post("/reviews/{session_id}/exports")
def generate_export(
    session_id: UUID,
    body: ExportRequest,
    response: Response,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    _private(response)
    session, conversation = _review(db, actor=actor, session_id=session_id)
    cleanup_expired_safeguarding_state(db, limit=25)
    try:
        export = create_evidence_export(
            db,
            actor=actor,
            session=session,
            conversation=conversation,
            export_mode=body.export_mode,
            reason_category=body.reason_category,
            justification=body.justification,
            include_internal_notes=body.include_internal_notes,
        )
        return {
            "id": str(export.public_id),
            "state": export.state,
            "size_bytes": export.size_bytes,
            "artifact_sha256": export.artifact_sha256,
            "manifest_sha256": export.manifest_sha256,
            "expires_at": export.expires_at,
            "download_count": export.download_count,
            "max_downloads": export.max_downloads,
        }
    except SafeguardingError as exc:
        _raise_http(exc)


@router.get("/exports/{export_id}/download")
def download_export(
    export_id: UUID,
    actor: SafeguardingActor = Depends(require_safeguarding_actor),
    db: Session = Depends(get_db),
):
    try:
        row, path = evidence_export_file(db, actor=actor, public_id=export_id)
        return FileResponse(
            path,
            media_type="application/zip",
            filename=f"chh-message-evidence-{str(row.public_id)[:8]}.zip",
            headers={
                "Cache-Control": "private, no-store, max-age=0",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "sandbox",
            },
        )
    except SafeguardingError as exc:
        _raise_http(exc)

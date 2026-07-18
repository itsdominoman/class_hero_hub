from __future__ import annotations

import base64
import hashlib
import json
from typing import Literal
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db, settings
from ..fhh_messaging_assertions import verify_and_consume_actor_assertion
from ..models_school import (
    FhhLink,
    Membership,
    School,
    StaffAssignment,
    Student,
    Subject,
    SubjectGroup,
    User,
)
from ..school_scope import open_interval_expression
from .integrations_fhh import _link, require_fhh_service
from .messaging import (
    ExternalGuardianActor,
    MessageAckRequest,
    MessageSendRequest,
    _ack,
    _actor_ref,
    _conversation_detail,
    _create_for_external_guardian,
    _enabled_policy,
    _external_guardian_access,
    _inbox,
    _media_for_participant,
    _message_page,
    _private,
    _protected_media_response,
    _protected_voice_response,
    _search_pattern,
    _send,
    _student_context_catalog,
    _upload_media,
    _upload_voice,
    _unread_count,
    _voice_for_participant,
)
from ..message_media_service import MAX_RAW_IMAGE_BYTES
from ..message_voice_service import MAX_RAW_AUDIO_BYTES


router = APIRouter(dependencies=[Depends(require_fhh_service)])
MAX_RECIPIENTS = 100


class ExternalConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["student_staff"] = "student_staff"
    recipient_ref: str = Field(min_length=16, max_length=1000)


def _recipient_cipher() -> Fernet:
    return Fernet(
        base64.urlsafe_b64encode(
            hashlib.sha256(
                f"{settings.JWT_SECRET}:chh-fhh-messaging-recipient-v1".encode()
            ).digest()
        )
    )


def _recipient_ref(
    *, school_id: int, student_id: int, membership_id: int
) -> str:
    payload = {
        "type": "fhh_messaging_recipient",
        "school_id": school_id,
        "student_id": student_id,
        "membership_id": membership_id,
    }
    return _recipient_cipher().encrypt(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    ).decode()


def _recipient_membership_id(
    value: str,
    *,
    school_id: int,
    student_id: int,
) -> int:
    try:
        payload = json.loads(
            _recipient_cipher().decrypt(value.encode(), ttl=24 * 60 * 60)
        )
    except (
        InvalidToken,
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
    ):
        raise HTTPException(status_code=400, detail="Invalid recipient reference")
    if (
        payload.get("type") != "fhh_messaging_recipient"
        or payload.get("school_id") != school_id
        or payload.get("student_id") != student_id
        or not isinstance(payload.get("membership_id"), int)
    ):
        raise HTTPException(status_code=400, detail="Invalid recipient reference")
    return payload["membership_id"]


def _actor(
    *,
    request: Request,
    db: Session,
    link_id: int,
    link_token: str | None,
    assertion: str | None,
    body: dict | None = None,
) -> ExternalGuardianActor:
    link = _link(db, link_id, link_token, lock=False)
    school = (
        db.query(School)
        .filter(
            School.id == link.school_id,
            School.status.in_(("pending_setup", "active")),
        )
        .first()
    )
    if school is None:
        raise HTTPException(status_code=404, detail="Messaging is unavailable")
    policy = _enabled_policy(db, school.id)
    identity, identity_link = verify_and_consume_actor_assertion(
        db,
        request=request,
        link=link,
        assertion=assertion,
        body=body,
    )
    return ExternalGuardianActor(
        identity=identity,
        identity_link=identity_link,
        link=link,
        school=school,
        policy=policy,
    )


@router.get("/links/{link_id}/messaging/inbox")
def inbox(
    link_id: int,
    request: Request,
    response: Response,
    limit: int = Query(default=30, ge=1, le=50),
    cursor: str | None = None,
    unread_only: bool = False,
    x_fhh_link_token: str | None = Header(default=None),
    x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    actor = _actor(
        request=request,
        db=db,
        link_id=link_id,
        link_token=x_fhh_link_token,
        assertion=x_fhh_messaging_actor,
    )
    return _inbox(
        db,
        actor=actor,
        response=response,
        limit=limit,
        cursor=cursor,
        unread_only=unread_only,
        include_item_cursors=True,
    )


@router.get("/links/{link_id}/messaging/unread-count")
def unread_count(
    link_id: int,
    request: Request,
    response: Response,
    x_fhh_link_token: str | None = Header(default=None),
    x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    actor = _actor(
        request=request,
        db=db,
        link_id=link_id,
        link_token=x_fhh_link_token,
        assertion=x_fhh_messaging_actor,
    )
    return _unread_count(db, actor=actor, response=response)


@router.get("/links/{link_id}/messaging/recipients")
def recipients(
    link_id: int,
    request: Request,
    response: Response,
    q: str = Query(default="", max_length=120),
    x_fhh_link_token: str | None = Header(default=None),
    x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    actor = _actor(
        request=request,
        db=db,
        link_id=link_id,
        link_token=x_fhh_link_token,
        assertion=x_fhh_messaging_actor,
    )
    _private(response)
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
        raise HTTPException(status_code=404, detail="Messaging is unavailable")
    student_contexts, resolution, subjects = _student_context_catalog(
        db,
        school_id=actor.school.id,
        student_ids={student.id},
    )
    section_ids = {
        row.id
        for row in resolution.class_sections_by_student.get(student.id, [])
    }
    group_ids = {
        row["id"]
        for row in resolution.subject_groups_by_student.get(student.id, [])
        if row.get("id") is not None
    }
    assignment_scope = []
    if section_ids:
        assignment_scope.append(StaffAssignment.class_section_id.in_(section_ids))
    if group_ids:
        assignment_scope.append(StaffAssignment.subject_group_id.in_(group_ids))
    needle = q.strip().casefold()
    assignment_query = (
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
    )
    if assignment_scope:
        assignment_query = assignment_query.filter(or_(*assignment_scope))
    else:
        assignment_query = assignment_query.filter(False)
    if needle:
        pattern = _search_pattern(needle)
        matching_subject_group_ids = (
            db.query(SubjectGroup.id)
            .join(Subject, Subject.id == SubjectGroup.subject_id)
            .filter(
                SubjectGroup.school_id == actor.school.id,
                or_(
                    func.coalesce(Subject.name, "").ilike(pattern, escape="\\"),
                    func.coalesce(Subject.name_ar, "").ilike(pattern, escape="\\"),
                    func.coalesce(SubjectGroup.name, "").ilike(pattern, escape="\\"),
                    func.coalesce(SubjectGroup.name_ar, "").ilike(pattern, escape="\\"),
                ),
            )
        )
        assignment_query = assignment_query.filter(
            or_(
                func.coalesce(User.name, "").ilike(pattern, escape="\\"),
                func.coalesce(User.name_ar, "").ilike(pattern, escape="\\"),
                func.coalesce(StaffAssignment.role, "").ilike(pattern, escape="\\"),
                StaffAssignment.subject_group_id.in_(matching_subject_group_ids),
            )
        )
    assignment_rows = assignment_query.limit(500).all()
    staff_by_membership: dict[int, tuple[Membership, User]] = {}
    assignments_by_membership: dict[int, list[StaffAssignment]] = {}
    for assignment, membership, user in assignment_rows:
        if (
            assignment.class_section_id in section_ids
            or assignment.subject_group_id in group_ids
        ):
            staff_by_membership[membership.id] = (membership, user)
            assignments_by_membership.setdefault(membership.id, []).append(assignment)
    admin_query = (
        db.query(Membership, User)
        .join(User, User.id == Membership.user_id)
        .filter(
            Membership.school_id == actor.school.id,
            Membership.role == "school_admin",
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            User.status == "active",
        )
    )
    if needle:
        pattern = _search_pattern(needle)
        admin_query = admin_query.filter(
            or_(
                func.coalesce(User.name, "").ilike(pattern, escape="\\"),
                func.coalesce(User.name_ar, "").ilike(pattern, escape="\\"),
                func.coalesce(Membership.role, "").ilike(pattern, escape="\\"),
            )
        )
    for membership, user in admin_query.limit(50).all():
        staff_by_membership[membership.id] = (membership, user)
    rows = list(staff_by_membership.values())
    rows.sort(key=lambda row: ((row[1].name or "").casefold(), row[0].id))
    student_groups = {
        int(group["id"]): group
        for group in resolution.subject_groups_by_student.get(student.id, [])
        if group.get("id") is not None
    }
    student_sections = {
        section.id
        for section in resolution.class_sections_by_student.get(student.id, [])
    }

    def staff_context(membership: Membership) -> dict:
        if membership.role == "school_admin":
            return {"relationship": "school_administration", "subjects": []}
        matching = assignments_by_membership.get(membership.id, [])
        has_homeroom = any(
            assignment.role in {"homeroom", "class_teacher"}
            and assignment.class_section_id in student_sections
            for assignment in matching
        )
        subject_rows: list[Subject] = []
        seen: set[int] = set()
        for assignment in matching:
            group = student_groups.get(assignment.subject_group_id or -1)
            subject_id = int(group["subject_id"]) if group and group.get("subject_id") else None
            subject = subjects.get(subject_id) if subject_id is not None else None
            if subject and subject.id not in seen:
                subject_rows.append(subject)
                seen.add(subject.id)
        return {
            "relationship": (
                "homeroom_teacher"
                if has_homeroom
                else "subject_teacher"
                if subject_rows
                else "school_staff"
            ),
            "subjects": [
                {"name": subject.name, "name_ar": subject.name_ar}
                for subject in subject_rows
            ],
        }

    student_context = student_contexts.get(student.id, {})
    db.commit()
    return {
        "student": {
            "display_name": " ".join(
                part
                for part in (
                    student.preferred_name or student.first_name,
                    student.last_name,
                )
                if part
            ).strip(),
            "name_ar": student.name_ar,
            **student_context,
        },
        "staff": [
            {
                "recipient_ref": _recipient_ref(
                    school_id=actor.school.id,
                    student_id=student.id,
                    membership_id=membership.id,
                ),
                "display_name": user.name,
                "name_ar": user.name_ar,
                "role": membership.role,
                "staff_context": staff_context(membership),
            }
            for membership, user in rows[:MAX_RECIPIENTS]
        ],
    }


@router.post("/links/{link_id}/messaging/conversations")
def create_conversation(
    link_id: int,
    body: ExternalConversationCreate,
    request: Request,
    response: Response,
    x_fhh_link_token: str | None = Header(default=None),
    x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    payload = body.model_dump(mode="json")
    actor = _actor(
        request=request,
        db=db,
        link_id=link_id,
        link_token=x_fhh_link_token,
        assertion=x_fhh_messaging_actor,
        body=payload,
    )
    _private(response)
    conversation = _create_for_external_guardian(
        db,
        actor=actor,
        staff_membership_id=_recipient_membership_id(
            body.recipient_ref,
            school_id=actor.school.id,
            student_id=actor.link.student_id,
        ),
    )
    return {
        "conversation_id": str(conversation.public_id),
        "status": conversation.status,
    }


@router.get("/links/{link_id}/messaging/conversations/{conversation_id}")
def conversation_detail(
    link_id: int,
    conversation_id: UUID,
    request: Request,
    response: Response,
    x_fhh_link_token: str | None = Header(default=None),
    x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    actor = _actor(
        request=request,
        db=db,
        link_id=link_id,
        link_token=x_fhh_link_token,
        assertion=x_fhh_messaging_actor,
    )
    conversation, _ = _external_guardian_access(
        db, actor=actor, public_id=conversation_id
    )
    payload = _conversation_detail(
        db, conversation=conversation, actor=actor, response=response
    )
    db.commit()
    return payload


@router.get("/links/{link_id}/messaging/conversations/{conversation_id}/messages")
def messages(
    link_id: int,
    conversation_id: UUID,
    request: Request,
    response: Response,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    after_sequence: int | None = Query(default=None, ge=0),
    x_fhh_link_token: str | None = Header(default=None),
    x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    actor = _actor(
        request=request,
        db=db,
        link_id=link_id,
        link_token=x_fhh_link_token,
        assertion=x_fhh_messaging_actor,
    )
    conversation, participant = _external_guardian_access(
        db, actor=actor, public_id=conversation_id
    )
    payload = _message_page(
        db,
        conversation=conversation,
        participant=participant,
        actor_ref=_actor_ref(actor),
        response=response,
        limit=limit,
        cursor=cursor,
        after_sequence=after_sequence,
    )
    db.commit()
    return payload


@router.post("/links/{link_id}/messaging/conversations/{conversation_id}/messages")
def send_message(
    link_id: int,
    conversation_id: UUID,
    body: MessageSendRequest,
    request: Request,
    response: Response,
    x_fhh_link_token: str | None = Header(default=None),
    x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    # Hash only keys actually sent so older FHH clients that predate optional
    # voice fields remain valid, while current clients still sign every field.
    payload = body.model_dump(mode="json", exclude_unset=True)
    actor = _actor(
        request=request,
        db=db,
        link_id=link_id,
        link_token=x_fhh_link_token,
        assertion=x_fhh_messaging_actor,
        body=payload,
    )
    conversation, participant = _external_guardian_access(
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


@router.post(
    "/links/{link_id}/messaging/conversations/{conversation_id}/media",
    status_code=status.HTTP_201_CREATED,
)
async def upload_media(
    link_id: int,
    conversation_id: UUID,
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    x_upload_id: UUID = Header(alias="X-Upload-Id"),
    x_fhh_media_sha256: str = Header(alias="X-FHH-Media-SHA256", min_length=64, max_length=64),
    x_fhh_media_size: int = Header(alias="X-FHH-Media-Size", ge=1, le=MAX_RAW_IMAGE_BYTES),
    x_fhh_link_token: str | None = Header(default=None),
    x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    checksum = x_fhh_media_sha256.lower()
    if any(character not in "0123456789abcdef" for character in checksum):
        raise HTTPException(status_code=400, detail="Invalid signed media digest")
    signed_body = {
        "client_upload_id": str(x_upload_id),
        "content_sha256": checksum,
        "size_bytes": x_fhh_media_size,
    }
    actor = _actor(
        request=request,
        db=db,
        link_id=link_id,
        link_token=x_fhh_link_token,
        assertion=x_fhh_messaging_actor,
        body=signed_body,
    )
    conversation, participant = _external_guardian_access(
        db, actor=actor, public_id=conversation_id
    )
    return await _upload_media(
        db,
        conversation=conversation,
        participant=participant,
        file=file,
        client_upload_id=x_upload_id,
        response=response,
        expected_source_checksum=checksum,
        expected_size=x_fhh_media_size,
    )


@router.get(
    "/links/{link_id}/messaging/conversations/{conversation_id}/media/{media_id}/{variant}"
)
def view_media(
    link_id: int,
    conversation_id: UUID,
    media_id: UUID,
    variant: Literal["thumbnail", "full"],
    request: Request,
    x_fhh_link_token: str | None = Header(default=None),
    x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    actor = _actor(
        request=request,
        db=db,
        link_id=link_id,
        link_token=x_fhh_link_token,
        assertion=x_fhh_messaging_actor,
    )
    conversation, participant = _external_guardian_access(
        db, actor=actor, public_id=conversation_id
    )
    return _protected_media_response(
        _media_for_participant(
            db,
            conversation=conversation,
            participant=participant,
            media_public_id=media_id,
        ),
        variant,
    )


@router.post(
    "/links/{link_id}/messaging/conversations/{conversation_id}/voice-media",
    status_code=status.HTTP_201_CREATED,
)
async def upload_voice(
    link_id: int,
    conversation_id: UUID,
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    x_upload_id: UUID = Header(alias="X-Upload-Id"),
    x_fhh_media_sha256: str = Header(alias="X-FHH-Media-SHA256", min_length=64, max_length=64),
    x_fhh_media_size: int = Header(alias="X-FHH-Media-Size", ge=1, le=MAX_RAW_AUDIO_BYTES),
    x_fhh_link_token: str | None = Header(default=None),
    x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    checksum = x_fhh_media_sha256.lower()
    if any(character not in "0123456789abcdef" for character in checksum):
        raise HTTPException(status_code=400, detail="Invalid signed media digest")
    signed_body = {
        "client_upload_id": str(x_upload_id),
        "content_sha256": checksum,
        "size_bytes": x_fhh_media_size,
    }
    actor = _actor(
        request=request,
        db=db,
        link_id=link_id,
        link_token=x_fhh_link_token,
        assertion=x_fhh_messaging_actor,
        body=signed_body,
    )
    conversation, participant = _external_guardian_access(
        db, actor=actor, public_id=conversation_id
    )
    return await _upload_voice(
        db,
        conversation=conversation,
        participant=participant,
        file=file,
        client_upload_id=x_upload_id,
        response=response,
        expected_source_checksum=checksum,
        expected_size=x_fhh_media_size,
    )


@router.get(
    "/links/{link_id}/messaging/conversations/{conversation_id}/voice-media/{media_id}"
)
def view_voice(
    link_id: int,
    conversation_id: UUID,
    media_id: UUID,
    request: Request,
    x_fhh_link_token: str | None = Header(default=None),
    x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    actor = _actor(
        request=request,
        db=db,
        link_id=link_id,
        link_token=x_fhh_link_token,
        assertion=x_fhh_messaging_actor,
    )
    conversation, participant = _external_guardian_access(
        db, actor=actor, public_id=conversation_id
    )
    return _protected_voice_response(
        _voice_for_participant(
            db,
            conversation=conversation,
            participant=participant,
            media_public_id=media_id,
        )
    )


@router.post(
    "/links/{link_id}/messaging/conversations/{conversation_id}/acknowledgements"
)
def acknowledge(
    link_id: int,
    conversation_id: UUID,
    body: MessageAckRequest,
    request: Request,
    response: Response,
    x_fhh_link_token: str | None = Header(default=None),
    x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    payload = body.model_dump(mode="json")
    actor = _actor(
        request=request,
        db=db,
        link_id=link_id,
        link_token=x_fhh_link_token,
        assertion=x_fhh_messaging_actor,
        body=payload,
    )
    conversation, participant = _external_guardian_access(
        db, actor=actor, public_id=conversation_id
    )
    return _ack(
        db,
        conversation=conversation,
        participant=participant,
        body=body,
        response=response,
    )

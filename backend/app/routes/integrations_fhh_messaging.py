from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..database import get_db, settings
from ..fhh_messaging_assertions import verify_and_consume_actor_assertion
from ..models_school import (
    FhhLink,
    Membership,
    School,
    StaffAssignment,
    Student,
    User,
)
from ..rosters import resolve_rosters_for_students
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
    _message_page,
    _private,
    _send,
    _unread_count,
)


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
        .filter(School.id == link.school_id, School.status == "active")
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
        .one()
    )
    resolution = resolve_rosters_for_students(
        db,
        actor.school.id,
        datetime.now(timezone.utc).date(),
        student_ids=[student.id],
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
    assignment_rows = (
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
        .limit(500)
        .all()
    )
    staff_by_membership: dict[int, tuple[Membership, User]] = {}
    for assignment, membership, user in assignment_rows:
        if (
            assignment.class_section_id in section_ids
            or assignment.subject_group_id in group_ids
        ):
            staff_by_membership[membership.id] = (membership, user)
    for membership, user in (
        db.query(Membership, User)
        .join(User, User.id == Membership.user_id)
        .filter(
            Membership.school_id == actor.school.id,
            Membership.role == "school_admin",
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            User.status == "active",
        )
        .limit(50)
        .all()
    ):
        staff_by_membership[membership.id] = (membership, user)
    needle = q.strip().casefold()
    rows = [
        (membership, user)
        for membership, user in staff_by_membership.values()
        if not needle
        or needle in (user.name or "").casefold()
        or needle in (user.name_ar or "").casefold()
    ]
    rows.sort(key=lambda row: ((row[1].name or "").casefold(), row[0].id))
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
    return _send(
        db,
        conversation=conversation,
        participant=participant,
        body=body,
        actor=actor,
        response=response,
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

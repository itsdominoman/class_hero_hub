from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from .. import auth
from ..database import get_db
from ..messaging_service import participant_sequence_access_map
from ..models_school import (
    Conversation,
    ConversationParticipant,
    DevicePushRegistration,
    Membership,
    Message,
    NotificationOutbox,
    User,
)


router = APIRouter()
ANDROID_PACKAGE = "com.classherohub.app"


class RegisterDeviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    installation_id: UUID
    platform: Literal["android"]
    app_package: Literal[ANDROID_PACKAGE]
    locale: Literal["en", "ar"] = "en"
    fcm_token: str = Field(min_length=20, max_length=512)


class UnregisterDeviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    installation_id: UUID
    app_package: Literal[ANDROID_PACKAGE]
    fcm_token: str = Field(min_length=20, max_length=512)


def _active_staff_membership(db: Session, user_id: int) -> bool:
    return (
        db.query(Membership.id)
        .filter(
            Membership.user_id == user_id,
            Membership.role.in_(("teacher", "school_admin")),
            Membership.status == "active",
            Membership.revoked_at.is_(None),
        )
        .first()
        is not None
    )


@router.post("/devices/register")
def register_device(
    body: RegisterDeviceRequest,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not _active_staff_membership(db, current_user.id):
        raise HTTPException(status_code=403, detail="School messaging is unavailable")

    registration = (
        db.query(DevicePushRegistration)
        .filter(
            DevicePushRegistration.app_package == body.app_package,
            DevicePushRegistration.installation_id == body.installation_id,
        )
        .with_for_update()
        .first()
    )
    token_owner = (
        db.query(DevicePushRegistration)
        .filter(DevicePushRegistration.fcm_token == body.fcm_token)
        .with_for_update()
        .first()
    )
    if token_owner is not None and token_owner is not registration:
        if registration is None:
            registration = token_owner
            registration.installation_id = body.installation_id
            registration.app_package = body.app_package
        else:
            token_owner.fcm_token = f"disabled:{token_owner.id}:{body.installation_id}"
            token_owner.state = "invalid"
            token_owner.disabled_reason = "token_reassigned"
            token_owner.revoked_at = datetime.now(timezone.utc)

    if registration is None:
        registration = DevicePushRegistration(
            installation_id=body.installation_id,
            user_id=current_user.id,
            platform=body.platform,
            app_package=body.app_package,
            locale=body.locale,
            fcm_token=body.fcm_token,
        )
        db.add(registration)
    else:
        registration.user_id = current_user.id
        registration.platform = body.platform
        registration.locale = body.locale
        registration.fcm_token = body.fcm_token
        registration.state = "active"
        registration.disabled_reason = None
        registration.revoked_at = None
        registration.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "registered"}


@router.post("/devices/unregister")
def unregister_device(
    body: UnregisterDeviceRequest,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(DevicePushRegistration)
        .filter(
            DevicePushRegistration.app_package == body.app_package,
            DevicePushRegistration.installation_id == body.installation_id,
            DevicePushRegistration.fcm_token == body.fcm_token,
        )
        .with_for_update()
        .first()
    )
    if row is not None:
        row.state = "revoked"
        row.disabled_reason = "logout"
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return {"status": "unregistered"}


@router.get("/devices/status")
def device_status(
    installation_id: UUID = Query(),
    app_package: Literal[ANDROID_PACKAGE] = Query(default=ANDROID_PACKAGE),
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(DevicePushRegistration)
        .filter(
            DevicePushRegistration.user_id == current_user.id,
            DevicePushRegistration.installation_id == installation_id,
            DevicePushRegistration.app_package == app_package,
        )
        .first()
    )
    return {
        "status": row.state if row is not None else "unregistered",
        "registered": bool(row is not None and row.state == "active"),
    }


@router.get("/events/{event_id}/target")
def notification_target(
    event_id: UUID,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.event_id == event_id,
            NotificationOutbox.recipient_kind == "chh_user",
            NotificationOutbox.recipient_user_id == current_user.id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Notification target is unavailable")
    message = db.query(Message).filter(Message.id == row.message_id, Message.state == "active").first()
    participant = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.id == row.recipient_participant_id,
            ConversationParticipant.user_id == current_user.id,
            ConversationParticipant.side == "staff",
            ConversationParticipant.membership_id.is_not(None),
            ConversationParticipant.left_at.is_(None),
        )
        .first()
    )
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == message.conversation_id, Conversation.status == "active")
        .first()
        if message is not None
        else None
    )
    membership = (
        db.query(Membership)
        .filter(
            Membership.id == participant.membership_id,
            Membership.user_id == current_user.id,
            Membership.school_id == row.school_id,
            Membership.role.in_(("teacher", "school_admin")),
            Membership.status == "active",
            Membership.revoked_at.is_(None),
        )
        .first()
        if participant is not None
        else None
    )
    if message is None or conversation is None or participant is None or membership is None:
        raise HTTPException(status_code=404, detail="Notification target is unavailable")
    access = participant_sequence_access_map(
        db,
        conversations=[conversation],
        participants=[participant],
        now=datetime.now(timezone.utc),
    ).get(participant.id)
    if access is None or not access.includes(int(message.sequence)):
        raise HTTPException(status_code=404, detail="Notification target is unavailable")
    return {
        "route_type": "school_chat",
        "conversation_id": str(conversation.public_id),
        "membership_id": membership.id,
    }

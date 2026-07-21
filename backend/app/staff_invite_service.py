from __future__ import annotations

import logging
from datetime import timedelta
from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from . import auth, invite_tokens
from .database import settings
from .mailer import StaffInviteEmail, send_staff_invite as default_send_staff_invite
from .models_school import School, StaffInvite, User


logger = logging.getLogger(__name__)
STAFF_INVITE_TTL = timedelta(days=7)
STAFF_ROLES = {"school_admin", "teacher"}


def issue_staff_invite(
    db: Session,
    *,
    school: School,
    email: str,
    actor: User,
    role: str,
    send: Callable[[StaffInviteEmail], None] | None = None,
) -> tuple[StaffInvite, str, str | None]:
    if role not in STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported staff invite role")
    normalized_email = auth.normalize_email(email)
    current = invite_tokens.now_utc()
    pending_invites = (
        db.query(StaffInvite)
        .filter(
            StaffInvite.school_id == school.id,
            StaffInvite.email == normalized_email,
            StaffInvite.role == role,
            StaffInvite.revoked_at.is_(None),
            StaffInvite.accepted_at.is_(None),
        )
        .all()
    )
    for pending in pending_invites:
        expires_at = invite_tokens.as_utc_aware(pending.expires_at)
        if expires_at is None or expires_at > current:
            pending.revoked_at = current

    raw_token = invite_tokens.generate_token()
    row = StaffInvite(
        school_id=school.id,
        email=normalized_email,
        role=role,
        token_hash=invite_tokens.hash_token(raw_token),
        invited_by_user_id=actor.id,
        expires_at=current + STAFF_INVITE_TTL,
        send_status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    warning = None
    accept_url = f"{settings.PUBLIC_APP_URL.rstrip('/')}/invite/{raw_token}"
    try:
        (send or default_send_staff_invite)(
            StaffInviteEmail(
                to_email=row.email,
                school_name=school.name,
                accept_url=accept_url,
            )
        )
        row.send_status = "sent"
        row.last_send_error = None
    except Exception as exc:  # pragma: no cover - provider behavior
        logger.exception("Failed to send staff invite %s for school %s", row.id, school.id)
        warning = "Invite was created, but the email could not be sent. Use resend after SMTP is available."
        row.send_status = "failed"
        row.last_send_error = type(exc).__name__[:80]
    db.commit()
    db.refresh(row)
    return row, raw_token, warning

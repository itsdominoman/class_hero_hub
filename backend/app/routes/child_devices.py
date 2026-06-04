from datetime import timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db, settings
from .. import models, schemas, auth
from ..child_auth import issue_child_device_invite, now_utc, revoke_child_device_access
from .family_scope import get_family_child_or_404

router = APIRouter()


def _session_is_active(session: models.ChildDeviceSession) -> bool:
    expires_at = session.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    return bool(
        session.revoked_at is None
        and expires_at is not None
        and expires_at > now_utc()
    )


@router.post("/children/{child_id}/device-invites", response_model=schemas.ChildDeviceInviteCreateResponse)
async def create_child_device_invite(
    child_id: int,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    child = get_family_child_or_404(db, child_id, current_parent)
    if not child.active:
        raise HTTPException(status_code=404, detail="Child not found")

    invite, raw_token = issue_child_device_invite(db, child, current_parent.family_id, current_parent.id)
    invite_url = f"{settings.PUBLIC_APP_URL.rstrip('/')}/child-link/{raw_token}"
    return schemas.ChildDeviceInviteCreateResponse(
        id=invite.id,
        child_id=child.id,
        child_name=child.display_name,
        invite_token=raw_token,
        invite_url=invite_url,
        expires_at=invite.expires_at,
    )


@router.post("/children/{child_id}/device-invites/revoke", response_model=schemas.ChildDeviceInviteRevokeResponse)
async def revoke_child_device_invites(
    child_id: int,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    child = get_family_child_or_404(db, child_id, current_parent)
    if not child.active:
        raise HTTPException(status_code=404, detail="Child not found")

    revoked_invites, revoked_sessions = revoke_child_device_access(db, child, current_parent.family_id)
    return schemas.ChildDeviceInviteRevokeResponse(
        revoked_invites=revoked_invites,
        revoked_sessions=revoked_sessions,
    )


@router.get("/children/{child_id}/devices", response_model=List[schemas.ChildDeviceSession])
async def list_child_devices(
    child_id: int,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    child = get_family_child_or_404(db, child_id, current_parent)
    if not child.active:
        raise HTTPException(status_code=404, detail="Child not found")

    sessions = (
        db.query(models.ChildDeviceSession)
        .filter(
            models.ChildDeviceSession.child_id == child.id,
            models.ChildDeviceSession.family_id == current_parent.family_id,
            models.ChildDeviceSession.revoked_at.is_(None),
            models.ChildDeviceSession.expires_at > now_utc(),
        )
        .order_by(models.ChildDeviceSession.last_seen_at.desc().nullslast(), models.ChildDeviceSession.created_at.desc())
        .all()
    )

    return [
        schemas.ChildDeviceSession(
            id=session.id,
            child_id=session.child_id,
            created_at=session.created_at,
            expires_at=session.expires_at,
            revoked_at=session.revoked_at,
            last_seen_at=session.last_seen_at,
            is_active=_session_is_active(session),
        )
        for session in sessions
    ]


@router.delete("/children/{child_id}/devices/{device_id}", response_model=schemas.ChildDeviceUnlinkResponse)
async def unlink_child_device(
    child_id: int,
    device_id: int,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    child = get_family_child_or_404(db, child_id, current_parent)
    if not child.active:
        raise HTTPException(status_code=404, detail="Child not found")

    session = (
        db.query(models.ChildDeviceSession)
        .filter(
            models.ChildDeviceSession.id == device_id,
            models.ChildDeviceSession.child_id == child.id,
            models.ChildDeviceSession.family_id == current_parent.family_id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Device not found")

    if session.revoked_at is None:
        session.revoked_at = now_utc()
        db.commit()
        db.refresh(session)

    return schemas.ChildDeviceUnlinkResponse(
        id=session.id,
        child_id=session.child_id,
        revoked=True,
    )

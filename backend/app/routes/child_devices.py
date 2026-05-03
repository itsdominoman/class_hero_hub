from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db, settings
from .. import models, schemas, auth
from ..child_auth import issue_child_device_invite, revoke_child_device_access
from .family_scope import get_family_child_or_404

router = APIRouter()


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

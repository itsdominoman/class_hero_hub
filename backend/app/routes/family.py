from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from ..database import get_db, settings
from .. import models, schemas, auth, mailer
import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/members", response_model=List[schemas.FamilyMember])
async def get_family_members(
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    return db.query(models.ParentUser).filter(
        models.ParentUser.family_id == current_parent.family_id
    ).all()

@router.get("/invites", response_model=List[schemas.FamilyInvite])
async def get_family_invites(
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    return db.query(models.FamilyInvite).filter(
        models.FamilyInvite.family_id == current_parent.family_id
    ).all()

@router.post("/invites", response_model=schemas.FamilyInvite)
async def create_family_invite(
    invite: schemas.FamilyInviteCreate,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    invite_email = auth.normalize_email(invite.email)
    current_email = auth.normalize_email(current_parent.email)
    if invite_email == current_email:
        raise HTTPException(status_code=400, detail="Cannot invite yourself")

    existing_member = db.query(models.ParentUser).filter(
        models.ParentUser.family_id == current_parent.family_id,
        func.lower(models.ParentUser.email) == invite_email
    ).first()
    if existing_member:
        raise HTTPException(status_code=400, detail="Email is already a family member")

    # Check if already invited or already a member
    existing_invite = db.query(models.FamilyInvite).filter(
        models.FamilyInvite.family_id == current_parent.family_id,
        func.lower(models.FamilyInvite.email) == invite_email,
        models.FamilyInvite.status == "pending"
    ).first()
    if existing_invite:
        # Check if expired
        expires_at = existing_invite.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        if expires_at and expires_at < datetime.now(timezone.utc):
            existing_invite.status = "expired"
            db.commit()
        else:
            raise HTTPException(status_code=400, detail="Invite already pending for this email")

    # Generate secure token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.INVITE_EXPIRY_DAYS)

    db_invite = models.FamilyInvite(
        family_id=current_parent.family_id,
        email=invite_email,
        invited_by_parent_id=current_parent.id,
        token_hash=token_hash,
        expires_at=expires_at,
        status="pending"
    )
    db.add(db_invite)
    db.commit()
    db.refresh(db_invite)

    # Send email. If sending fails, keep the pending invite row for audit/debug,
    # but return a clean error so the UI/user does not think the email was sent.
    invite_url = f"{settings.PUBLIC_APP_URL.rstrip('/')}/family-invite/{raw_token}"
    email_sent = mailer.send_invite_email(
        to_email=invite_email,
        inviter_name=current_parent.name or current_parent.email,
        invite_url=invite_url
    )

    if not email_sent:
        logger.warning("Invite created for %s but email delivery was unavailable", invite_email)

    return db_invite

@router.patch("/invites/{invite_id}/revoke", response_model=schemas.FamilyInvite)
async def revoke_family_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    db_invite = db.query(models.FamilyInvite).filter(
        models.FamilyInvite.id == invite_id,
        models.FamilyInvite.family_id == current_parent.family_id,
        models.FamilyInvite.status == "pending"
    ).first()
    
    if not db_invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    
    db_invite.status = "revoked"
    db_invite.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_invite)

    return db_invite

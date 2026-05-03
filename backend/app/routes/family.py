from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from ..database import get_db
from .. import models, schemas, auth

router = APIRouter()

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
        raise HTTPException(status_code=400, detail="Invite already pending for this email")

    db_invite = models.FamilyInvite(
        family_id=current_parent.family_id,
        email=invite_email,
        invited_by_parent_id=current_parent.id
    )
    db.add(db_invite)
    db.commit()
    db.refresh(db_invite)
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
    db.commit()
    db.refresh(db_invite)
    return db_invite

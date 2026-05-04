from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from .. import models, schemas, auth, mailer
from datetime import datetime, timezone
from typing import List

router = APIRouter()

@router.get("/registration-requests", response_model=List[schemas.RegistrationRequest])
async def list_registration_requests(
    db: Session = Depends(get_db),
    current_admin: models.ParentUser = Depends(auth.get_current_admin)
):
    return db.query(models.RegistrationRequest).order_by(models.RegistrationRequest.created_at.desc()).all()

@router.post("/registration-requests/{request_id}/approve", response_model=schemas.RegistrationRequest)
async def approve_registration_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_admin: models.ParentUser = Depends(auth.get_current_admin)
):
    reg_request = db.query(models.RegistrationRequest).filter(models.RegistrationRequest.id == request_id).first()
    if not reg_request:
        raise HTTPException(status_code=404, detail="Registration request not found")
    
    if reg_request.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {reg_request.status}")

    # Mark request as approved
    reg_request.status = "approved"
    reg_request.approved_at = datetime.now(timezone.utc)
    reg_request.approved_by_parent_id = current_admin.id

    # Add to approved emails
    approved_email = db.query(models.ApprovedParentEmail).filter(
        models.ApprovedParentEmail.normalized_email == reg_request.normalized_email
    ).first()
    
    if approved_email:
        approved_email.status = "active"
        approved_email.approved_at = datetime.now(timezone.utc)
        approved_email.approved_by_parent_id = current_admin.id
        approved_email.source = "registration_request"
    else:
        approved_email = models.ApprovedParentEmail(
            email=reg_request.email,
            normalized_email=reg_request.normalized_email,
            approved_by_parent_id=current_admin.id,
            source="registration_request",
            status="active"
        )
        db.add(approved_email)

    db.commit()
    db.refresh(reg_request)

    # Send approval email
    mailer.send_approval_email(reg_request.email, reg_request.name)

    return reg_request

@router.post("/registration-requests/{request_id}/reject", response_model=schemas.RegistrationRequest)
async def reject_registration_request(
    request_id: int,
    review_data: schemas.RegistrationRequestReview,
    db: Session = Depends(get_db),
    current_admin: models.ParentUser = Depends(auth.get_current_admin)
):
    reg_request = db.query(models.RegistrationRequest).filter(models.RegistrationRequest.id == request_id).first()
    if not reg_request:
        raise HTTPException(status_code=404, detail="Registration request not found")
    
    if reg_request.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {reg_request.status}")

    reg_request.status = "rejected"
    reg_request.rejected_at = datetime.now(timezone.utc)
    reg_request.rejection_reason = review_data.rejection_reason
    
    db.commit()
    db.refresh(reg_request)

    return reg_request

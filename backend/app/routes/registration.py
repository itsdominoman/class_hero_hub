from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from .. import models, schemas, auth, mailer
from datetime import datetime, timezone

router = APIRouter()

@router.post("", response_model=schemas.RegistrationRequest)
async def create_registration_request(
    request_data: schemas.RegistrationRequestCreate,
    db: Session = Depends(get_db)
):
    normalized_email = auth.normalize_email(request_data.email)
    
    # Check if already approved
    existing_approval = db.query(models.ApprovedParentEmail).filter(
        models.ApprovedParentEmail.normalized_email == normalized_email,
        models.ApprovedParentEmail.status == "active"
    ).first()
    if existing_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is already approved. Please log in."
        )

    # Check for existing pending request
    existing_request = db.query(models.RegistrationRequest).filter(
        models.RegistrationRequest.normalized_email == normalized_email,
        models.RegistrationRequest.status == "pending"
    ).first()
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A registration request for this email is already pending."
        )

    # Create request
    new_request = models.RegistrationRequest(
        email=request_data.email,
        normalized_email=normalized_email,
        name=request_data.name,
        family_name=request_data.family_name,
        message=request_data.message
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # Notify support
    mailer.send_registration_notification({
        "name": new_request.name,
        "email": new_request.email,
        "family_name": new_request.family_name,
        "message": new_request.message
    })

    return new_request

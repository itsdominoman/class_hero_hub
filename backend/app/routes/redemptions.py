from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import models, schemas, auth
from ..services import points_service
from datetime import datetime

router = APIRouter()

@router.get("/redemptions", response_model=List[schemas.RedemptionRequest])
async def get_all_redemptions(
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    return db.query(models.RedemptionRequest).order_by(models.RedemptionRequest.status == models.RedemptionStatus.pending, models.RedemptionRequest.created_at.desc()).all()

@router.post("/children/{child_id}/redemptions", response_model=schemas.RedemptionRequest)
async def request_redemption(
    child_id: int,
    req: schemas.RedemptionRequestCreate,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    child = db.query(models.Child).filter(models.Child.id == child_id).first()
    if not child or not child.active:
        raise HTTPException(status_code=404, detail="Child not found or inactive")

    if req.points <= 0:
        raise HTTPException(status_code=400, detail="Points must be positive")
    
    balances = points_service.calculate_balances(db, child_id)
    if balances["spending_balance"] < req.points:
        raise HTTPException(status_code=400, detail="Insufficient spending points")

    # Create redemption request
    db_request = models.RedemptionRequest(
        child_id=child_id,
        points=req.points,
        title=req.title,
        description=req.description,
        status=models.RedemptionStatus.pending
    )
    
    # Hold points immediately in the ledger
    hold_tx = models.LedgerTransaction(
        child_id=child_id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.redemption_hold,
        points=-req.points,
        description=f"Redemption Hold: {req.title}",
        created_by_parent_id=current_parent.id
    )
    
    db.add(db_request)
    db.add(hold_tx)
    db.commit()
    db.refresh(db_request)
    
    return db_request

@router.post("/redemptions/{request_id}/approve", response_model=schemas.RedemptionRequest)
async def approve_redemption(
    request_id: int,
    req: schemas.RedemptionReviewRequest,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    db_request = db.query(models.RedemptionRequest).filter(models.RedemptionRequest.id == request_id).first()
    if not db_request:
        raise HTTPException(status_code=404, detail="Redemption request not found")
    
    if db_request.status != models.RedemptionStatus.pending:
        raise HTTPException(status_code=400, detail="Request already processed")

    db_request.status = models.RedemptionStatus.approved
    db_request.parent_note = req.parent_note
    db_request.reviewed_at = datetime.utcnow()
    db_request.reviewed_by_parent_id = current_parent.id

    # Points were already held during request creation.
    # No need to deduct again. 
    # We can optionally add an "approved" marker transaction with 0 points if needed,
    # but the instructions say "Approved redemption should permanently deduct the held spending points."
    # Since they are already deducted (negative points in ledger), we just leave them.

    db.commit()
    db.refresh(db_request)
    
    return db_request

@router.post("/redemptions/{request_id}/reject", response_model=schemas.RedemptionRequest)
async def reject_redemption(
    request_id: int,
    req: schemas.RedemptionReviewRequest,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    db_request = db.query(models.RedemptionRequest).filter(models.RedemptionRequest.id == request_id).first()
    if not db_request:
        raise HTTPException(status_code=404, detail="Redemption request not found")
    
    if db_request.status != models.RedemptionStatus.pending:
        raise HTTPException(status_code=400, detail="Request already processed")

    db_request.status = models.RedemptionStatus.rejected
    db_request.parent_note = req.parent_note
    db_request.reviewed_at = datetime.utcnow()
    db_request.reviewed_by_parent_id = current_parent.id

    # Release held points back to spending
    release_tx = models.LedgerTransaction(
        child_id=db_request.child_id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.redemption_rejected,
        points=db_request.points,
        description=f"Redemption Rejected: {db_request.title}",
        created_by_parent_id=current_parent.id
    )
    db.add(release_tx)
    db.commit()
    db.refresh(db_request)
    
    return db_request

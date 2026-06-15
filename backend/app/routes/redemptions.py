from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from typing import List
from ..database import get_db
from .. import models, schemas, auth
from ..services import points_service
from .family_scope import get_family_child_or_404
from datetime import datetime

router = APIRouter()


def _get_family_redemption_or_404(
    db: Session,
    request_id: int,
    current_parent: models.ParentUser,
) -> models.RedemptionRequest:
    db_request = (
        db.query(models.RedemptionRequest)
        .options(joinedload(models.RedemptionRequest.child))
        .join(models.Child)
        .filter(
            models.RedemptionRequest.id == request_id,
            models.Child.family_id == current_parent.family_id,
        )
        .first()
    )
    if not db_request:
        raise HTTPException(status_code=404, detail="Redemption request not found")
    return db_request


def _claim_pending_redemption(
    db: Session,
    request_id: int,
    current_parent: models.ParentUser,
    next_status: models.RedemptionStatus,
    parent_note: str | None,
) -> models.RedemptionRequest:
    db_request = _get_family_redemption_or_404(db, request_id, current_parent)

    result = db.execute(
        update(models.RedemptionRequest)
        .where(
            models.RedemptionRequest.id == db_request.id,
            models.RedemptionRequest.status == models.RedemptionStatus.pending,
        )
        .values(
            status=next_status,
            parent_note=parent_note,
            reviewed_at=datetime.utcnow(),
            reviewed_by_parent_id=current_parent.id,
        )
    )
    if result.rowcount != 1:
        db.rollback()
        db_request = _get_family_redemption_or_404(db, request_id, current_parent)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request already {db_request.status.value}",
        )

    db.flush()
    db.refresh(db_request)
    return db_request

@router.get("/redemptions", response_model=List[schemas.RedemptionRequest])
async def get_all_redemptions(
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    return (
        db.query(models.RedemptionRequest)
        .options(joinedload(models.RedemptionRequest.child))
        .join(models.Child)
        .filter(models.Child.family_id == current_parent.family_id)
        .order_by(
            models.RedemptionRequest.status == models.RedemptionStatus.pending,
            models.RedemptionRequest.created_at.desc(),
        )
        .all()
    )

@router.post("/children/{child_id}/redemptions", response_model=schemas.RedemptionRequest)
async def request_redemption(
    child_id: int,
    req: schemas.RedemptionRequestCreate,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    child = get_family_child_or_404(db, child_id, current_parent)
    if not child.active:
        raise HTTPException(status_code=404, detail="Child not found or inactive")

    if req.points <= 0:
        raise HTTPException(status_code=400, detail="Points must be positive")
    
    balances = points_service.calculate_balances(db, child.id)
    if balances["spending_balance"] < req.points:
        raise HTTPException(status_code=400, detail="Insufficient spending points")

    # Create redemption request
    db_request = models.RedemptionRequest(
        child_id=child.id,
        points=req.points,
        title=req.title,
        description=req.description,
        status=models.RedemptionStatus.pending
    )
    
    # Hold points immediately in the ledger
    hold_tx = models.LedgerTransaction(
        child_id=child.id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.redemption_hold,
        points=-req.points,
        description=f"Redemption Hold: {req.title}",
        created_by_parent_id=current_parent.id
    )
    
    try:
        db.add(db_request)
        db.flush()
        hold_tx.redemption_request_id = db_request.id
        db.add(hold_tx)
        db.commit()
        db.refresh(db_request)
        db_request.child = child
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate redemption hold") from exc
    
    return db_request

@router.post("/redemptions/{request_id}/approve", response_model=schemas.RedemptionRequest)
async def approve_redemption(
    request_id: int,
    req: schemas.RedemptionReviewRequest,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    try:
        db_request = _claim_pending_redemption(
            db,
            request_id,
            current_parent,
            models.RedemptionStatus.approved,
            req.parent_note,
        )
        # Approval only updates the redemption request; the original hold
        # transaction remains the single point deduction in the ledger.
        db.commit()
        db.refresh(db_request)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise
    
    return db_request

@router.post("/redemptions/{request_id}/reject", response_model=schemas.RedemptionRequest)
async def reject_redemption(
    request_id: int,
    req: schemas.RedemptionReviewRequest,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent)
):
    try:
        db_request = _claim_pending_redemption(
            db,
            request_id,
            current_parent,
            models.RedemptionStatus.rejected,
            req.parent_note,
        )

        # Release held points back to spending exactly once. The unique
        # redemption_request_id index protects retries and concurrent callers.
        release_tx = models.LedgerTransaction(
            child_id=db_request.child_id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.redemption_rejected,
            points=db_request.points,
            description=f"Redemption Rejected: {db_request.title}",
            redemption_request_id=db_request.id,
            created_by_parent_id=current_parent.id
        )
        db.add(release_tx)
        db.commit()
        db.refresh(db_request)
    except HTTPException:
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Request already processed") from exc
    except Exception:
        db.rollback()
        raise
    
    return db_request

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session
from typing import List, Literal

from ..database import get_db
from .. import models, schemas, auth
from ..child_auth import get_current_child, clear_child_session_cookie
from ..services import allowance_service, points_service
from ..services.rewards_service import get_family_rewards

router = APIRouter()


@router.get("/me", response_model=schemas.ChildSummary)
async def get_my_dashboard(
    db: Session = Depends(get_db),
    current_child: models.Child = Depends(get_current_child),
    request: Request = None,
    response: Response = None,
):
    summary = points_service.get_child_summary(db, current_child.id)
    if not summary:
        raise HTTPException(status_code=404, detail="Child not found")

    if request is not None and response is not None and not request.cookies.get(auth.CSRF_COOKIE_NAME):
        auth.set_csrf_cookie(response, auth.create_csrf_token())

    return summary


@router.get("/rewards", response_model=List[schemas.Reward])
async def get_my_rewards(
    db: Session = Depends(get_db),
    current_child: models.Child = Depends(get_current_child),
):
    return get_family_rewards(db, current_child.family_id)


@router.get("/allowance", response_model=schemas.AllowancePreview)
async def get_my_allowance(
    db: Session = Depends(get_db),
    current_child: models.Child = Depends(get_current_child),
):
    settings = allowance_service.get_settings_response(db, current_child)
    return allowance_service.get_allowance_summary(
        db,
        current_child,
        settings,
        reveal_preview_when_disabled=False,
    )


@router.get("/ledger", response_model=List[schemas.LedgerTransaction])
async def get_my_ledger(
    period: Literal["day", "week", "month"] = Query("month"),
    tx_type: Literal["all", "earned", "spent", "saved", "held", "released", "adjustment"] = Query("all", alias="type"),
    db: Session = Depends(get_db),
    current_child: models.Child = Depends(get_current_child),
):
    return points_service.get_ledger_transactions(db, current_child.id, period=period, tx_type=tx_type)


@router.get("/ledger/summary", response_model=schemas.LedgerSummary)
async def get_my_ledger_summary(
    period: Literal["day", "week", "month"] = Query("month"),
    db: Session = Depends(get_db),
    current_child: models.Child = Depends(get_current_child),
):
    return points_service.get_ledger_summary(db, current_child.id, period=period)


@router.get("/redemptions", response_model=List[schemas.RedemptionRequest])
async def get_my_redemptions(
    db: Session = Depends(get_db),
    current_child: models.Child = Depends(get_current_child),
):
    return (
        db.query(models.RedemptionRequest)
        .filter(models.RedemptionRequest.child_id == current_child.id)
        .order_by(
            models.RedemptionRequest.status == models.RedemptionStatus.pending,
            models.RedemptionRequest.created_at.desc(),
        )
        .all()
    )


@router.post("/redemptions", response_model=schemas.RedemptionRequest)
async def request_my_redemption(
    req: schemas.RedemptionRequestCreate,
    db: Session = Depends(get_db),
    current_child: models.Child = Depends(get_current_child),
):
    if req.points <= 0:
        raise HTTPException(status_code=400, detail="Points must be positive")

    if not current_child.active:
        raise HTTPException(status_code=404, detail="Child not found or inactive")

    balances = points_service.calculate_balances(db, current_child.id)
    if balances["spending_balance"] < req.points:
        raise HTTPException(status_code=400, detail="Insufficient spending points")

    db_request = models.RedemptionRequest(
        child_id=current_child.id,
        points=req.points,
        title=req.title,
        description=req.description,
        status=models.RedemptionStatus.pending,
    )

    hold_tx = models.LedgerTransaction(
        child_id=current_child.id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.redemption_hold,
        points=-req.points,
        description=f"Redemption Hold: {req.title}",
        created_by_parent_id=None,
    )

    db.add(db_request)
    db.add(hold_tx)
    db.commit()
    db.refresh(db_request)

    return db_request


@router.post("/logout")
async def child_logout(response: Response):
    clear_child_session_cookie(response)
    return {"message": "Logged out"}

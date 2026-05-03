from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..child_auth import exchange_child_link, register_exchange_attempt, set_child_session_cookie

router = APIRouter()


@router.post("/exchange", response_model=schemas.ChildLinkExchangeResponse)
async def exchange_link_token(
    payload: schemas.ChildLinkExchangeRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    register_exchange_attempt(request)
    invite, session, session_raw_token = exchange_child_link(db, payload.token)
    child = db.query(models.Child).filter(
        models.Child.id == invite.child_id,
        models.Child.family_id == invite.family_id,
    ).first()
    if not child:
        raise HTTPException(status_code=401, detail="Invalid or expired child link")
    set_child_session_cookie(response, session_raw_token, session.expires_at)
    return schemas.ChildLinkExchangeResponse(
        child=child,
        session_expires_at=session.expires_at,
    )

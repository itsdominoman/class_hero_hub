from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..services import allowance_service
from .family_scope import get_family_child_or_404

router = APIRouter()


@router.get("/children/{child_id}/settings", response_model=schemas.AllowanceSettings)
async def get_child_allowance_settings(
    child_id: int,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    child = get_family_child_or_404(db, child_id, current_parent)
    return allowance_service.get_settings_response(db, child)


@router.put("/children/{child_id}/settings", response_model=schemas.AllowanceSettings)
async def put_child_allowance_settings(
    child_id: int,
    payload: schemas.AllowanceSettingsUpsert,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    child = get_family_child_or_404(db, child_id, current_parent)
    setting = allowance_service.upsert_settings(db, child, current_parent, payload)
    return setting


@router.delete("/children/{child_id}/settings", status_code=status.HTTP_204_NO_CONTENT)
async def delete_child_allowance_settings(
    child_id: int,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    child = get_family_child_or_404(db, child_id, current_parent)
    allowance_service.delete_settings(db, child)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/children/{child_id}/preview", response_model=schemas.AllowancePreview)
async def get_child_allowance_preview(
    child_id: int,
    db: Session = Depends(get_db),
    current_parent: models.ParentUser = Depends(auth.get_current_parent),
):
    child = get_family_child_or_404(db, child_id, current_parent)
    settings = allowance_service.get_settings_response(db, child)
    return allowance_service.preview_allowance(db, child, settings)

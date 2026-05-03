from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models


def get_family_child_or_404(
    db: Session,
    child_id: int,
    current_parent: models.ParentUser,
) -> models.Child:
    child = db.query(models.Child).filter(
        models.Child.id == child_id,
        models.Child.family_id == current_parent.family_id,
    ).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    return child

from sqlalchemy.orm import Session

from .. import models


def get_family_rewards(db: Session, family_id: int):
    return (
        db.query(models.Reward)
        .filter(
            models.Reward.family_id == family_id,
            models.Reward.is_active.is_(True),
            models.Reward.points > 0,
        )
        .order_by(models.Reward.points.asc(), models.Reward.created_at.asc())
        .all()
    )

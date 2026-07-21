from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import auth
from ..behaviour_service import category_payload, create_events, guardian_points_payload, quick_actions_payload, seed_default_categories, visible_categories
from ..database import get_db
from ..models_school import BehaviourCategory, Membership, User
from ..school_scope import require_school_role, write_audit
from ..family_notifications import enqueue_family_notifications

school_router = APIRouter(dependencies=[Depends(require_school_role("school_admin"))])
teacher_router = APIRouter()
guardian_router = APIRouter()


class CategoryRequest(BaseModel):
    type: str
    label: str = Field(min_length=1, max_length=120)
    points_value: int
    sort_order: int = 0
    active: bool = True
    is_quick_action: bool = False
    quick_action_order: int | None = Field(default=None, ge=1)

    @field_validator("type")
    @classmethod
    def type_valid(cls, value):
        if value not in {"positive", "needs_work"}: raise ValueError("type must be positive or needs_work")
        return value

    @field_validator("points_value")
    @classmethod
    def value_valid(cls, value, info):
        category_type = info.data.get("type")
        if value == 0 or (category_type == "positive" and value < 0) or (category_type == "needs_work" and value > 0):
            raise ValueError("points value must match category type")
        return value

    @model_validator(mode="after")
    def quick_action_valid(self):
        if self.active and self.is_quick_action and self.quick_action_order is None:
            raise ValueError("quick_action_order is required for quick actions")
        return self


class CategoryPatch(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    points_value: int | None = None
    sort_order: int | None = None
    active: bool | None = None
    is_quick_action: bool | None = None
    quick_action_order: int | None = Field(default=None, ge=1)


class QuickActionsRequest(BaseModel):
    positive_category_ids: list[int] = Field(default_factory=list, max_length=6)
    needs_work_category_ids: list[int] = Field(default_factory=list, max_length=6)


def apply_quick_action_fields(db: Session, row: BehaviourCategory, values: dict) -> None:
    active = values.get("active", row.active)
    quick = values.get("is_quick_action", row.is_quick_action)
    quick_order = values.get("quick_action_order", row.quick_action_order)
    if not active:
        values["is_quick_action"] = False
        values["quick_action_order"] = None
        return
    if quick and quick_order is None:
        raise HTTPException(422, "quick_action_order is required for quick actions")
    if not quick:
        values["quick_action_order"] = None
        return
    existing_quick_count = db.query(BehaviourCategory).filter(
        BehaviourCategory.school_id == row.school_id,
        BehaviourCategory.type == row.type,
        BehaviourCategory.active.is_(True),
        BehaviourCategory.is_quick_action.is_(True),
        BehaviourCategory.id != row.id,
    ).count()
    if existing_quick_count >= 6:
        raise HTTPException(422, "A school can have at most six quick actions per type")


class EventRequest(BaseModel):
    school_id: int
    student_ids: list[int] = Field(min_length=1, max_length=40)
    category_id: int
    note: str | None = Field(default=None, max_length=500)
    context_type: str = "general"
    class_section_id: int | None = None
    subject_group_id: int | None = None
    duty_context: str | None = None

    @field_validator("context_type")
    @classmethod
    def context_type_valid(cls, value):
        if value not in {"class", "subject", "duty", "general"}:
            raise ValueError("Invalid behaviour context type")
        return value

    @field_validator("duty_context")
    @classmethod
    def duty_context_valid(cls, value):
        if value is not None and value not in {"break", "lunch", "playground", "hallway", "assembly", "bus", "general_duty"}:
            raise ValueError("Invalid duty context")
        return value

    @model_validator(mode="after")
    def context_combination_valid(self):
        valid = (
            (self.context_type == "subject" and self.subject_group_id is not None and self.class_section_id is None and self.duty_context is None)
            or (self.context_type == "class" and self.class_section_id is not None and self.subject_group_id is None and self.duty_context is None)
            or (self.context_type == "duty" and self.duty_context is not None and self.class_section_id is None and self.subject_group_id is None)
            or (self.context_type == "general" and self.class_section_id is None and self.subject_group_id is None and self.duty_context is None)
        )
        if not valid:
            raise ValueError("Behaviour context fields do not match context_type")
        return self


@school_router.get("/behaviour/categories")
def admin_categories(membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    seed_default_categories(db, membership.school_id); db.commit()
    return {"categories": [category_payload(r) for r in visible_categories(db, membership.school_id, active_only=False)]}


@school_router.post("/behaviour/categories/seed-defaults")
def seed_categories(membership: Membership = Depends(require_school_role("school_admin")), user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    rows = seed_default_categories(db, membership.school_id)
    write_audit(db, user, "behaviour.categories.seeded", ("behaviour_categories", None), {"created": len(rows)}, membership.school_id); db.commit()
    return {"created": len(rows), "categories": [category_payload(r) for r in visible_categories(db, membership.school_id, active_only=False)]}


@school_router.post("/behaviour/categories", status_code=201)
def create_category(body: CategoryRequest, membership: Membership = Depends(require_school_role("school_admin")), user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    values = body.model_dump(); values["label"] = body.label.strip()
    row = BehaviourCategory(school_id=membership.school_id, **values)
    apply_quick_action_fields(db, row, values)
    for key, value in values.items(): setattr(row, key, value)
    db.add(row)
    try: db.flush()
    except IntegrityError: db.rollback(); raise HTTPException(409, "Category label already exists")
    write_audit(db, user, "behaviour.category.created", row, category_payload(row), membership.school_id); db.commit(); db.refresh(row)
    return category_payload(row)


@school_router.patch("/behaviour/categories/{category_id}")
def edit_category(category_id: int, body: CategoryPatch, membership: Membership = Depends(require_school_role("school_admin")), user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    row = db.query(BehaviourCategory).filter(BehaviourCategory.id == category_id, BehaviourCategory.school_id == membership.school_id).first()
    if not row: raise HTTPException(404, "Category not found")
    values = body.model_dump(exclude_unset=True)
    if "label" in values: values["label"] = values["label"].strip()
    prospective = values.get("points_value", row.points_value)
    if prospective == 0 or (row.type == "positive" and prospective < 0) or (row.type == "needs_work" and prospective > 0): raise HTTPException(422, "Points value must match category type")
    apply_quick_action_fields(db, row, values)
    for key, value in values.items(): setattr(row, key, value)
    try: db.flush()
    except IntegrityError: db.rollback(); raise HTTPException(409, "Category label already exists")
    write_audit(db, user, "behaviour.category.updated", row, values, membership.school_id); db.commit(); db.refresh(row)
    return category_payload(row)


@school_router.put("/behaviour/quick-actions")
def configure_quick_actions(body: QuickActionsRequest, membership: Membership = Depends(require_school_role("school_admin")), user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    requested = {
        "positive": body.positive_category_ids,
        "needs_work": body.needs_work_category_ids,
    }
    all_ids = [category_id for ids in requested.values() for category_id in ids]
    if len(all_ids) != len(set(all_ids)):
        raise HTTPException(422, "Quick action category IDs must be unique")
    rows = db.query(BehaviourCategory).filter(
        BehaviourCategory.school_id == membership.school_id,
        BehaviourCategory.id.in_(all_ids),
    ).all() if all_ids else []
    by_id = {row.id: row for row in rows}
    if len(by_id) != len(all_ids):
        raise HTTPException(422, "Quick action categories must belong to this school")
    for category_type, ids in requested.items():
        for category_id in ids:
            row = by_id[category_id]
            if not row.active:
                raise HTTPException(422, "Quick action categories must be active")
            if row.type != category_type:
                raise HTTPException(422, "Quick action category type does not match its list")

    categories = db.query(BehaviourCategory).filter(BehaviourCategory.school_id == membership.school_id).all()
    for row in categories:
        row.is_quick_action = False
        row.quick_action_order = None
    for category_type, ids in requested.items():
        for order, category_id in enumerate(ids, 1):
            row = by_id[category_id]
            row.is_quick_action = True
            row.quick_action_order = order
    db.flush()
    write_audit(
        db,
        user,
        "behaviour.quick_actions.updated",
        ("behaviour_categories", None),
        {"positive_category_ids": requested["positive"], "needs_work_category_ids": requested["needs_work"]},
        membership.school_id,
    )
    db.commit()
    return {"categories": [category_payload(row) for row in visible_categories(db, membership.school_id, active_only=False)]}


@teacher_router.get("/behaviour/categories")
def teacher_categories(school_id: int, user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    from ..behaviour_service import active_teacher_membership
    active_teacher_membership(db, user.id, school_id)
    return {"categories": [category_payload(r) for r in visible_categories(db, school_id)]}


@teacher_router.get("/behaviour/quick-actions")
def teacher_quick_actions(school_id: int, user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    from ..behaviour_service import active_teacher_membership
    active_teacher_membership(db, user.id, school_id)
    return quick_actions_payload(db, school_id)


@teacher_router.post("/behaviour/events", status_code=201)
def award_points(body: EventRequest, user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    rows = create_events(
        db,
        school_id=body.school_id,
        student_ids=body.student_ids,
        category_id=body.category_id,
        actor=user,
        note=body.note,
        context_type=body.context_type,
        class_section_id=body.class_section_id,
        subject_group_id=body.subject_group_id,
        duty_context=body.duty_context,
    )
    for row in rows:
        enqueue_family_notifications(db, category="points", source=row, action="awarded")
    write_audit(db, user, "behaviour.events.created", ("behaviour_events", None), {"event_ids": [r.id for r in rows], "student_ids": body.student_ids, "category_id": body.category_id}, body.school_id); db.commit()
    return {"created": len(rows), "events": [{"id": r.id, "student_id": r.student_id, "category_id": r.category_id, "points_delta": r.points_delta} for r in rows]}


@guardian_router.get("/points")
def guardian_points(user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return guardian_points_payload(db, user.id)

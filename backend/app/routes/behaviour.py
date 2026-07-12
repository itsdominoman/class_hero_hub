from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import auth
from ..behaviour_service import category_payload, create_events, guardian_points_payload, seed_default_categories, visible_categories
from ..database import get_db
from ..models_school import BehaviourCategory, Membership, User
from ..school_scope import require_school_role, write_audit

school_router = APIRouter(dependencies=[Depends(require_school_role("school_admin"))])
teacher_router = APIRouter()
guardian_router = APIRouter()


class CategoryRequest(BaseModel):
    type: str
    label: str = Field(min_length=1, max_length=120)
    points_value: int
    sort_order: int = 0
    active: bool = True

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


class CategoryPatch(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    points_value: int | None = None
    sort_order: int | None = None
    active: bool | None = None


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
    row = BehaviourCategory(school_id=membership.school_id, **values); db.add(row)
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
    for key, value in values.items(): setattr(row, key, value)
    try: db.flush()
    except IntegrityError: db.rollback(); raise HTTPException(409, "Category label already exists")
    write_audit(db, user, "behaviour.category.updated", row, values, membership.school_id); db.commit(); db.refresh(row)
    return category_payload(row)


@teacher_router.get("/behaviour/categories")
def teacher_categories(school_id: int, user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    from ..behaviour_service import active_teacher_membership
    active_teacher_membership(db, user.id, school_id)
    return {"categories": [category_payload(r) for r in visible_categories(db, school_id)]}


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
    write_audit(db, user, "behaviour.events.created", ("behaviour_events", None), {"event_ids": [r.id for r in rows], "student_ids": body.student_ids, "category_id": body.category_id}, body.school_id); db.commit()
    return {"created": len(rows), "events": [{"id": r.id, "student_id": r.student_id, "category_id": r.category_id, "points_delta": r.points_delta} for r in rows]}


@guardian_router.get("/points")
def guardian_points(user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return guardian_points_payload(db, user.id)

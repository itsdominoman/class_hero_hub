from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import auth
from ..database import get_db
from ..models_school import (
    BehaviourCategory,
    BranchCampus,
    ClassSection,
    GradeLevel,
    Membership,
    School,
    StudentRecognitionCandidate,
    StudentRecognitionCategory,
    StudentRecognitionConfig,
    StudentRecognitionReview,
    StudentRecognitionSafeguardCategory,
    User,
)
from ..recognition_service import (
    candidate_payload,
    config_payload,
    generate_shortlist,
    positive_categories,
    review_payload,
    scope_record,
    selected_needs_work_categories,
)
from ..school_scope import require_school_role, write_audit


router = APIRouter(dependencies=[Depends(require_school_role("school_admin"))])


class RecognitionConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recognition_type: Literal["star_of_week"] = "star_of_week"
    name: str = Field(min_length=1, max_length=160)
    scope_type: Literal["branch", "grade", "class"]
    scope_ref_id: int = Field(ge=1)
    review_period_days: int = Field(default=7, ge=1, le=366)
    category_ids: list[int] = Field(min_length=1, max_length=100)
    minimum_positive_points: int = Field(default=1, ge=1)
    shortlist_size: int = Field(default=3, ge=1, le=50)
    needs_work_safeguard_enabled: bool = False
    maximum_needs_work_events: int = Field(default=0, ge=0)
    needs_work_category_ids: list[int] = Field(default_factory=list, max_length=100)
    certificate_title: str = Field(min_length=1, max_length=200)
    signatory_text: str = Field(min_length=1, max_length=200)
    active: bool = True
    confirm_similar_active_configuration: bool = False

    @field_validator("name", "certificate_title", "signatory_text")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value may not be blank")
        return value

    @field_validator("category_ids", "needs_work_category_ids")
    @classmethod
    def unique_categories(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Category IDs must be unique")
        return value


class GenerateReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    config_id: int = Field(ge=1)
    period_end: date


class ExcludeCandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Reason must contain at least three characters")
        return value


class OverrideSafeguardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Reason must contain at least three characters")
        return value


class ConfirmReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: int = Field(ge=1)
    citation: str | None = Field(default=None, max_length=500)

    @field_validator("citation")
    @classmethod
    def strip_citation(cls, value: str | None) -> str | None:
        value = value.strip() if value else None
        return value or None


class RevokeReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Reason must contain at least three characters")
        return value


class ArchiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Reason must contain at least three characters")
        return value


def _config(db: Session, school_id: int, config_id: int, *, lock: bool = False) -> StudentRecognitionConfig:
    query = db.query(StudentRecognitionConfig).filter(
        StudentRecognitionConfig.id == config_id,
        StudentRecognitionConfig.school_id == school_id,
    )
    if lock and db.bind and db.bind.dialect.name == "postgresql":
        query = query.with_for_update()
    row = query.first()
    if not row:
        raise HTTPException(404, "Recognition configuration not found")
    return row


def _normalise_recognition_name(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _review(db: Session, school_id: int, review_id: int, *, lock: bool = False) -> StudentRecognitionReview:
    query = db.query(StudentRecognitionReview).filter(
        StudentRecognitionReview.id == review_id,
        StudentRecognitionReview.school_id == school_id,
    )
    if lock and db.bind and db.bind.dialect.name == "postgresql":
        query = query.with_for_update()
    row = query.first()
    if not row:
        raise HTTPException(404, "Recognition review not found")
    return row


def _write_categories(db: Session, config_id: int, categories: list[BehaviourCategory]) -> None:
    db.query(StudentRecognitionCategory).filter(StudentRecognitionCategory.config_id == config_id).delete(synchronize_session=False)
    db.add_all([StudentRecognitionCategory(config_id=config_id, category_id=row.id) for row in categories])
    db.flush()


def _write_safeguard_categories(db: Session, config_id: int, categories: list[BehaviourCategory]) -> None:
    db.query(StudentRecognitionSafeguardCategory).filter(
        StudentRecognitionSafeguardCategory.config_id == config_id
    ).delete(synchronize_session=False)
    db.add_all(
        [StudentRecognitionSafeguardCategory(config_id=config_id, category_id=row.id) for row in categories]
    )
    db.flush()


@router.get("/recognition/options")
def recognition_options(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = membership.school_id
    branches = db.query(BranchCampus).filter(BranchCampus.school_id == school_id, BranchCampus.status == "active").order_by(BranchCampus.sort_order, BranchCampus.name).all()
    grades = db.query(GradeLevel).filter(GradeLevel.school_id == school_id, GradeLevel.status == "active").order_by(GradeLevel.sort_order, GradeLevel.name).all()
    classes = db.query(ClassSection).filter(ClassSection.school_id == school_id, ClassSection.status == "active").order_by(ClassSection.sort_order, ClassSection.name).all()
    categories = db.query(BehaviourCategory).filter(BehaviourCategory.school_id == school_id, BehaviourCategory.type == "positive", BehaviourCategory.active.is_(True)).order_by(BehaviourCategory.sort_order, BehaviourCategory.label).all()
    needs_work_categories = db.query(BehaviourCategory).filter(BehaviourCategory.school_id == school_id, BehaviourCategory.type == "needs_work", BehaviourCategory.active.is_(True)).order_by(BehaviourCategory.sort_order, BehaviourCategory.label).all()
    return {
        "branches": [{"id": row.id, "name": row.name, "name_ar": row.name_ar} for row in branches],
        "grades": [{"id": row.id, "name": row.name, "name_ar": row.name_ar} for row in grades],
        "classes": [{"id": row.id, "name": row.name, "name_ar": row.name_ar, "branch_campus_id": row.branch_campus_id, "grade_level_id": row.grade_level_id} for row in classes],
        "positive_categories": [{"id": row.id, "label": row.label, "points_value": row.points_value} for row in categories],
        "needs_work_categories": [{"id": row.id, "label": row.label} for row in needs_work_categories],
    }


@router.get("/recognition/configs")
def list_configs(
    include_archived: bool = Query(default=False),
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    query = db.query(StudentRecognitionConfig).filter(StudentRecognitionConfig.school_id == membership.school_id)
    if not include_archived:
        query = query.filter(StudentRecognitionConfig.archived_at.is_(None))
    rows = query.order_by(
        StudentRecognitionConfig.archived_at.is_not(None),
        StudentRecognitionConfig.active.desc(),
        StudentRecognitionConfig.name,
        StudentRecognitionConfig.id,
    ).all()
    return {"configs": [config_payload(db, row) for row in rows]}


@router.post("/recognition/configs", status_code=201)
def create_config(
    body: RecognitionConfigRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    scope = scope_record(db, membership.school_id, body.scope_type, body.scope_ref_id)
    categories = positive_categories(db, membership.school_id, body.category_ids)
    safeguard_category_rows = selected_needs_work_categories(
        db, membership.school_id, body.needs_work_category_ids
    )
    active_names = [
        row.name
        for row in db.query(StudentRecognitionConfig.name).filter(
            StudentRecognitionConfig.school_id == membership.school_id,
            StudentRecognitionConfig.active.is_(True),
            StudentRecognitionConfig.archived_at.is_(None),
        ).all()
    ]
    normalised_name = _normalise_recognition_name(body.name)
    if (
        body.active
        and any(_normalise_recognition_name(name) == normalised_name for name in active_names)
        and not body.confirm_similar_active_configuration
    ):
        raise HTTPException(409, "Confirm creation of a similarly named active recognition configuration")
    values = body.model_dump(
        exclude={"category_ids", "needs_work_category_ids", "confirm_similar_active_configuration"}
    )
    row = StudentRecognitionConfig(
        school_id=membership.school_id,
        scope_key=f"{body.scope_type}:{scope.id}",
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
        **values,
    )
    db.add(row)
    try:
        db.flush()
        _write_categories(db, row.id, categories)
        _write_safeguard_categories(db, row.id, safeguard_category_rows)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A Star of the Week configuration already exists for this scope")
    payload = config_payload(db, row)
    write_audit(db, user, "recognition.config.created", row, {"config": payload}, membership.school_id)
    db.commit()
    db.refresh(row)
    return config_payload(db, row)


@router.put("/recognition/configs/{config_id}")
def update_config(
    config_id: int,
    body: RecognitionConfigRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    row = _config(db, membership.school_id, config_id)
    if row.archived_at is not None:
        raise HTTPException(409, "Archived recognition configurations cannot be changed")
    before = config_payload(db, row)
    scope = scope_record(db, membership.school_id, body.scope_type, body.scope_ref_id)
    categories = positive_categories(db, membership.school_id, body.category_ids)
    safeguard_category_rows = selected_needs_work_categories(
        db, membership.school_id, body.needs_work_category_ids
    )
    for key, value in body.model_dump(
        exclude={"category_ids", "needs_work_category_ids", "confirm_similar_active_configuration"}
    ).items():
        setattr(row, key, value)
    row.scope_key = f"{body.scope_type}:{scope.id}"
    row.updated_by_user_id = user.id
    try:
        _write_categories(db, row.id, categories)
        _write_safeguard_categories(db, row.id, safeguard_category_rows)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A Star of the Week configuration already exists for this scope")
    after = config_payload(db, row)
    write_audit(db, user, "recognition.config.updated", row, {"before": before, "after": after}, membership.school_id)
    db.commit()
    db.refresh(row)
    return config_payload(db, row)


@router.post("/recognition/configs/{config_id}/archive")
def archive_config(
    config_id: int,
    body: ArchiveRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    row = _config(db, membership.school_id, config_id, lock=True)
    if row.archived_at is not None:
        return config_payload(db, row)
    before = config_payload(db, row)
    row.active = False
    row.archived_by_user_id = user.id
    row.archived_at = datetime.now(timezone.utc)
    row.archive_reason = body.reason
    row.updated_by_user_id = user.id
    after = config_payload(db, row)
    write_audit(
        db,
        user,
        "recognition.config.archived",
        row,
        {"before": before, "after": after, "reason": body.reason},
        membership.school_id,
    )
    db.commit()
    db.refresh(row)
    return config_payload(db, row)


@router.get("/recognition/reviews")
def list_reviews(
    limit: int = Query(default=25, ge=1, le=100),
    include_archived: bool = Query(default=False),
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    query = db.query(StudentRecognitionReview).filter(
        StudentRecognitionReview.school_id == membership.school_id
    )
    if not include_archived:
        query = query.filter(StudentRecognitionReview.status != "archived")
    rows = query.order_by(
        StudentRecognitionReview.generated_at.desc(), StudentRecognitionReview.id.desc()
    ).limit(limit).all()
    return {"reviews": [review_payload(db, row, include_candidates=False) for row in rows]}


@router.post("/recognition/reviews", status_code=201)
def create_review(
    body: GenerateReviewRequest,
    response: Response,
    membership: Membership = Depends(require_school_role("school_admin")),
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    config = _config(db, membership.school_id, body.config_id, lock=True)
    if config.archived_at is not None:
        raise HTTPException(422, "Recognition configuration is archived")
    if not config.active:
        raise HTTPException(422, "Recognition configuration is inactive")
    period_start = body.period_end - timedelta(days=config.review_period_days - 1)
    existing = db.query(StudentRecognitionReview).filter(
        StudentRecognitionReview.school_id == membership.school_id,
        StudentRecognitionReview.config_id == config.id,
        StudentRecognitionReview.period_start == period_start,
        StudentRecognitionReview.period_end == body.period_end,
        StudentRecognitionReview.status == "draft",
    ).first()
    if existing:
        response.status_code = 200
        payload = review_payload(db, existing)
        payload["was_existing_draft"] = True
        return payload
    school = db.query(School).filter(School.id == membership.school_id).one()
    review = generate_shortlist(db, school=school, config=config, period_end=body.period_end, actor_user_id=user.id)
    candidates = db.query(StudentRecognitionCandidate).filter(StudentRecognitionCandidate.review_id == review.id).order_by(StudentRecognitionCandidate.display_order).all()
    for candidate in candidates:
        if candidate.safeguard_excluded:
            write_audit(
                db,
                user,
                "recognition.candidate.safeguard_excluded",
                candidate,
                {
                    "review_id": review.id,
                    "student_id": candidate.student_id,
                    "counted_total": candidate.safeguard_counted_total,
                    "maximum_allowed": config.maximum_needs_work_events,
                    "category_counts": candidate.safeguard_category_totals,
                },
                membership.school_id,
            )
    write_audit(
        db,
        user,
        "recognition.shortlist.generated",
        review,
        {
            "config_id": config.id,
            "period_start": review.period_start.isoformat(),
            "period_end": review.period_end.isoformat(),
            "criteria": review.criteria_snapshot,
            "shortlist": [{"student_id": row.student_id, "points": row.positive_points_total, "events": row.positive_event_count, "rank": row.rank} for row in candidates],
        },
        membership.school_id,
    )
    db.commit()
    db.refresh(review)
    payload = review_payload(db, review)
    payload["was_existing_draft"] = False
    return payload


@router.get("/recognition/reviews/{review_id}")
def get_review(
    review_id: int,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    review = _review(db, membership.school_id, review_id)
    school = db.query(School).filter(School.id == membership.school_id).one()
    payload = review_payload(db, review)
    payload["school"] = {"name": school.name, "name_ar": school.name_ar, "logo_url": None}
    return payload


@router.post("/recognition/reviews/{review_id}/archive")
def archive_review(
    review_id: int,
    body: ArchiveRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    review = _review(db, membership.school_id, review_id, lock=True)
    if review.status == "archived":
        return review_payload(db, review)
    if review.status != "draft":
        raise HTTPException(409, "Only an unconfirmed draft review can be archived")
    review.status = "archived"
    review.archived_by_user_id = user.id
    review.archived_at = datetime.now(timezone.utc)
    review.archive_reason = body.reason
    write_audit(
        db,
        user,
        "recognition.review.archived",
        review,
        {
            "config_id": review.config_id,
            "period_start": review.period_start.isoformat(),
            "period_end": review.period_end.isoformat(),
            "reason": body.reason,
        },
        membership.school_id,
    )
    db.commit()
    db.refresh(review)
    return review_payload(db, review)


@router.post("/recognition/reviews/{review_id}/candidates/{candidate_id}/exclude")
def exclude_candidate(
    review_id: int,
    candidate_id: int,
    body: ExcludeCandidateRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    review = _review(db, membership.school_id, review_id, lock=True)
    if review.status != "draft":
        raise HTTPException(409, "Only a draft shortlist can be changed")
    candidate = db.query(StudentRecognitionCandidate).filter(
        StudentRecognitionCandidate.id == candidate_id,
        StudentRecognitionCandidate.review_id == review.id,
        StudentRecognitionCandidate.school_id == membership.school_id,
    ).first()
    if not candidate:
        raise HTTPException(404, "Recognition candidate not found")
    if candidate.is_excluded:
        return candidate_payload(candidate)
    candidate.is_excluded = True
    candidate.exclusion_reason = body.reason
    candidate.excluded_by_user_id = user.id
    candidate.excluded_at = datetime.now(timezone.utc)
    write_audit(db, user, "recognition.candidate.excluded", candidate, {"review_id": review.id, "student_id": candidate.student_id, "reason": body.reason}, membership.school_id)
    db.commit()
    db.refresh(candidate)
    return candidate_payload(candidate)


@router.post("/recognition/reviews/{review_id}/candidates/{candidate_id}/override-safeguard")
def override_candidate_safeguard(
    review_id: int,
    candidate_id: int,
    body: OverrideSafeguardRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    review = _review(db, membership.school_id, review_id, lock=True)
    if review.status != "draft":
        raise HTTPException(409, "Only a draft shortlist can be changed")
    candidate = db.query(StudentRecognitionCandidate).filter(
        StudentRecognitionCandidate.id == candidate_id,
        StudentRecognitionCandidate.review_id == review.id,
        StudentRecognitionCandidate.school_id == membership.school_id,
    ).first()
    if not candidate:
        raise HTTPException(404, "Recognition candidate not found")
    if not candidate.safeguard_excluded:
        raise HTTPException(409, "This student was not excluded by the eligibility safeguard")
    if candidate.safeguard_overridden_at is not None:
        return candidate_payload(candidate)
    candidate.safeguard_override_reason = body.reason
    candidate.safeguard_overridden_by_user_id = user.id
    candidate.safeguard_overridden_at = datetime.now(timezone.utc)
    write_audit(
        db,
        user,
        "recognition.candidate.safeguard_overridden",
        candidate,
        {
            "review_id": review.id,
            "student_id": candidate.student_id,
            "counted_total": candidate.safeguard_counted_total,
            "reason": body.reason,
        },
        membership.school_id,
    )
    db.commit()
    db.refresh(candidate)
    return candidate_payload(candidate)


@router.post("/recognition/reviews/{review_id}/confirm")
def confirm_review(
    review_id: int,
    body: ConfirmReviewRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    review = _review(db, membership.school_id, review_id, lock=True)
    if review.status == "confirmed" and review.selected_student_id == body.student_id and review.citation == body.citation:
        return review_payload(db, review)
    if review.status != "draft":
        raise HTTPException(409, "Only a draft shortlist can be confirmed")
    candidate = db.query(StudentRecognitionCandidate).filter(
        StudentRecognitionCandidate.review_id == review.id,
        StudentRecognitionCandidate.school_id == membership.school_id,
        StudentRecognitionCandidate.student_id == body.student_id,
        StudentRecognitionCandidate.is_excluded.is_(False),
    ).first()
    if not candidate:
        raise HTTPException(422, "Select an eligible, non-excluded shortlisted student")
    if candidate.safeguard_excluded and candidate.safeguard_overridden_at is None:
        raise HTTPException(422, "Selected student is not eligible under current criteria")
    duplicate = db.query(StudentRecognitionReview.id).filter(
        StudentRecognitionReview.school_id == membership.school_id,
        StudentRecognitionReview.recognition_type == review.recognition_type,
        StudentRecognitionReview.scope_key == review.scope_key,
        StudentRecognitionReview.period_start == review.period_start,
        StudentRecognitionReview.period_end == review.period_end,
        StudentRecognitionReview.status == "confirmed",
        StudentRecognitionReview.id != review.id,
    ).first()
    if duplicate:
        raise HTTPException(409, "This recognition scope and period already has a confirmed award")
    review.status = "confirmed"
    review.selected_student_id = candidate.student_id
    review.citation = body.citation
    review.confirmed_by_user_id = user.id
    review.confirmed_at = datetime.now(timezone.utc)
    write_audit(db, user, "recognition.review.confirmed", review, {"student_id": candidate.student_id, "candidate_id": candidate.id, "period_start": review.period_start.isoformat(), "period_end": review.period_end.isoformat()}, membership.school_id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This recognition scope and period already has a confirmed award")
    db.refresh(review)
    return review_payload(db, review)


@router.post("/recognition/reviews/{review_id}/revoke")
def revoke_review(
    review_id: int,
    body: RevokeReviewRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    review = _review(db, membership.school_id, review_id, lock=True)
    if review.status == "revoked":
        return review_payload(db, review)
    if review.status != "confirmed":
        raise HTTPException(409, "Only a confirmed award can be revoked")
    review.status = "revoked"
    review.revoked_by_user_id = user.id
    review.revoked_at = datetime.now(timezone.utc)
    review.revocation_reason = body.reason
    write_audit(db, user, "recognition.review.revoked", review, {"student_id": review.selected_student_id, "reason": body.reason}, membership.school_id)
    db.commit()
    db.refresh(review)
    return review_payload(db, review)

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import re
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db, settings
from ..family_notifications import enqueue_family_notifications
from ..fhh_messaging_assertions import verify_and_consume_actor_assertion
from ..models_school import (
    BranchCampus, ClassSection, FhhLink, FhhMessagingIdentity, FhhMessagingIdentityLink,
    GradeLevel, Membership, MessagingPermissionGrant, NotificationOutbox, School, SchoolSystemOwner, Student,
    Survey, SurveyAnswer, SurveyEvent, SurveyOption, SurveyQuestion, SurveyResponse, SurveyTarget,
    User,
)
from ..school_governance import GovernanceConflict, GovernanceForbidden, require_owner
from ..school_scope import require_school_role, write_audit
from ..survey_service import aware_utc, eligible_links, link_is_eligible, refresh_survey_state
from .integrations_fhh import _link, require_fhh_service


router = APIRouter()
integration_router = APIRouter(dependencies=[Depends(require_fhh_service)])
UTC = timezone.utc
SURVEY_PERMISSION = "surveys.manage"
QUESTION_TYPES = {"single_choice", "multiple_choice", "yes_no", "rating", "short_text", "long_text"}
HOUSEHOLD_REF_RE = re.compile(r"^[0-9a-f]{64}$")


class OptionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1, max_length=500)

    @field_validator("label")
    @classmethod
    def clean_label(cls, value: str) -> str:
        return value.strip()


class QuestionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_type: Literal["single_choice", "multiple_choice", "yes_no", "rating", "short_text", "long_text"]
    prompt: str = Field(min_length=1, max_length=1000)
    required: bool = False
    scale_min: int | None = Field(default=None, ge=0, le=10)
    scale_max: int | None = Field(default=None, ge=1, le=10)
    options: list[OptionInput] = Field(default_factory=list, max_length=20)

    @field_validator("prompt")
    @classmethod
    def clean_prompt(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def valid_shape(self):
        if self.question_type in {"single_choice", "multiple_choice"} and len(self.options) < 2:
            raise ValueError("Choice questions require at least two options")
        if self.question_type not in {"single_choice", "multiple_choice"} and self.options:
            raise ValueError("Only choice questions accept options")
        if self.question_type == "rating":
            if self.scale_min is None or self.scale_max is None or self.scale_min >= self.scale_max:
                raise ValueError("Rating scale is invalid")
        elif self.scale_min is not None or self.scale_max is not None:
            raise ValueError("Only rating questions accept a scale")
        return self


class SurveyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    introduction: str = Field(min_length=1, max_length=1000)
    instructions: str | None = Field(default=None, max_length=5000)
    audience_type: Literal["whole_school", "branch", "grade", "class", "selected_families"]
    target_ids: list[int] = Field(default_factory=list, max_length=500)
    anonymous: bool = True
    response_mode: Literal["guardian", "household"] = "guardian"
    opens_at: datetime
    closes_at: datetime
    reminder_at: datetime | None = None
    parent_results_visible: bool = False
    push_enabled: bool = True
    dashboard_card_enabled: bool = True
    notices_feed_enabled: bool = True
    questions: list[QuestionInput] = Field(min_length=1, max_length=100)

    @field_validator("title", "introduction")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("instructions")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        clean = (value or "").strip()
        return clean or None

    @model_validator(mode="after")
    def valid_window_and_targets(self):
        if self.opens_at.tzinfo is None or self.closes_at.tzinfo is None:
            raise ValueError("Survey dates must include a timezone")
        if self.closes_at <= self.opens_at:
            raise ValueError("Closing time must be after opening time")
        if self.reminder_at is not None:
            if self.reminder_at.tzinfo is None or not self.opens_at < self.reminder_at < self.closes_at:
                raise ValueError("Reminder must fall inside the survey window")
        unique = list(dict.fromkeys(self.target_ids))
        self.target_ids = unique
        if self.audience_type == "whole_school" and unique:
            raise ValueError("Whole-school surveys do not accept target IDs")
        if self.audience_type != "whole_school" and not unique:
            raise ValueError("The selected audience requires at least one target")
        return self


class PermissionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    membership_id: int
    enabled: bool
    reason: str = Field(min_length=3, max_length=1000)


class ReopenSurveyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    closes_at: datetime | None = None

    @field_validator("closes_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Survey closing time must include a timezone")
        return value


class HouseholdEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    household_ref: str = Field(pattern=r"^[0-9a-f]{64}$")


class ParentAnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: UUID
    value: Any = None


class ParentSubmission(HouseholdEvidence):
    answers: list[ParentAnswerInput] = Field(min_length=1, max_length=100)


def _has_permission(db: Session, membership: Membership) -> bool:
    return db.query(MessagingPermissionGrant.id).filter(
        MessagingPermissionGrant.school_id == membership.school_id,
        MessagingPermissionGrant.membership_id == membership.id,
        MessagingPermissionGrant.permission == SURVEY_PERMISSION,
        MessagingPermissionGrant.revoked_at.is_(None),
    ).first() is not None


def require_survey_admin(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
) -> Membership:
    if not _has_permission(db, membership):
        raise HTTPException(status_code=403, detail="Survey management permission required")
    return membership


def _survey_or_404(db: Session, membership: Membership, survey_id: UUID, *, lock: bool = False) -> Survey:
    query = db.query(Survey).filter(Survey.public_id == survey_id, Survey.school_id == membership.school_id)
    if lock:
        query = query.with_for_update()
    row = query.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Survey not found")
    refresh_survey_state(row)
    return row


def _question_payload(db: Session, survey_id: int) -> list[dict[str, Any]]:
    questions = db.query(SurveyQuestion).filter(SurveyQuestion.survey_id == survey_id).order_by(SurveyQuestion.sort_order).all()
    option_rows = db.query(SurveyOption).filter(SurveyOption.question_id.in_([row.id for row in questions])).order_by(SurveyOption.question_id, SurveyOption.sort_order).all() if questions else []
    options: dict[int, list[dict[str, Any]]] = {}
    for option in option_rows:
        options.setdefault(option.question_id, []).append({"id": str(option.public_id), "label": option.label, "sort_order": option.sort_order})
    return [
        {
            "id": str(question.public_id), "question_type": question.question_type, "prompt": question.prompt,
            "required": bool(question.required), "sort_order": question.sort_order,
            "scale_min": question.scale_min, "scale_max": question.scale_max,
            "options": options.get(question.id, []),
        }
        for question in questions
    ]


def _target_ids(db: Session, survey_id: int) -> list[int]:
    return [row[0] for row in db.query(SurveyTarget.target_id).filter(SurveyTarget.survey_id == survey_id).order_by(SurveyTarget.target_id).all()]


def _eligible_count(db: Session, survey: Survey) -> int:
    links = eligible_links(db, survey)
    if survey.response_mode == "household":
        known = {link.fhh_household_ref for link in links if link.fhh_household_ref}
        unknown = sum(1 for link in links if not link.fhh_household_ref)
        return len(known) + unknown
    link_ids = [link.id for link in links]
    if not link_ids:
        return 0
    return int(
        db.query(func.count(func.distinct(FhhMessagingIdentity.external_subject_ref)))
        .join(FhhMessagingIdentityLink, FhhMessagingIdentityLink.identity_id == FhhMessagingIdentity.id)
        .filter(
            FhhMessagingIdentityLink.fhh_link_id.in_(link_ids),
            FhhMessagingIdentityLink.status == "active",
            FhhMessagingIdentityLink.revoked_at.is_(None),
            FhhMessagingIdentity.status == "active",
        ).scalar() or 0
    )


def _summary_payload(db: Session, survey: Survey) -> dict[str, Any]:
    response_count = int(db.query(func.count(SurveyResponse.id)).filter(SurveyResponse.survey_id == survey.id).scalar() or 0)
    eligible_count = _eligible_count(db, survey)
    reminder = db.query(SurveyEvent).filter(SurveyEvent.survey_id == survey.id, SurveyEvent.action == "reminder_sent").order_by(SurveyEvent.id.desc()).first()
    reminder_delivery = db.query(NotificationOutbox).filter(NotificationOutbox.school_id == survey.school_id, NotificationOutbox.source_type == "survey", NotificationOutbox.source_id == survey.id, NotificationOutbox.source_action == "reminder").order_by(NotificationOutbox.id.desc()).first()
    return {
        "id": str(survey.public_id), "title": survey.title, "introduction": survey.introduction,
        "status": survey.status, "audience_type": survey.audience_type, "target_ids": _target_ids(db, survey.id),
        "anonymous": bool(survey.anonymous), "response_mode": survey.response_mode,
        "opens_at": survey.opens_at, "closes_at": survey.closes_at, "reminder_at": survey.reminder_at,
        "parent_results_visible": bool(survey.parent_results_visible), "push_enabled": bool(survey.push_enabled),
        "dashboard_card_enabled": bool(survey.dashboard_card_enabled), "notices_feed_enabled": bool(survey.notices_feed_enabled),
        "eligible_count": eligible_count, "response_count": response_count,
        "response_rate": round((response_count / eligible_count * 100), 1) if eligible_count else 0,
        "reminder_status": "sent" if reminder or (reminder_delivery and reminder_delivery.state in {"dispatched", "provider_accepted"}) else ("scheduled" if reminder_delivery or survey.reminder_at else "off"),
        "created_at": survey.created_at, "published_at": survey.published_at,
    }


def _detail_payload(db: Session, survey: Survey) -> dict[str, Any]:
    return {**_summary_payload(db, survey), "instructions": survey.instructions, "questions": _question_payload(db, survey.id)}


def _validate_targets(db: Session, school_id: int, audience_type: str, target_ids: list[int]) -> None:
    if audience_type == "whole_school":
        return
    model = {"branch": BranchCampus, "grade": GradeLevel, "class": ClassSection, "selected_families": Student}[audience_type]
    count = db.query(func.count(model.id)).filter(model.school_id == school_id, model.id.in_(target_ids), model.status == "active").scalar()
    if int(count or 0) != len(target_ids):
        raise HTTPException(status_code=422, detail="One or more audience targets are invalid")


def _replace_questions_and_targets(db: Session, survey: Survey, body: SurveyInput) -> None:
    db.query(SurveyTarget).filter(SurveyTarget.survey_id == survey.id).delete(synchronize_session=False)
    question_ids = [row[0] for row in db.query(SurveyQuestion.id).filter(SurveyQuestion.survey_id == survey.id).all()]
    if question_ids:
        db.query(SurveyOption).filter(SurveyOption.question_id.in_(question_ids)).delete(synchronize_session=False)
        response_ids = [row[0] for row in db.query(SurveyResponse.id).filter(SurveyResponse.survey_id == survey.id).all()]
        if response_ids:
            db.query(SurveyAnswer).filter(SurveyAnswer.response_id.in_(response_ids)).delete(synchronize_session=False)
        db.query(SurveyQuestion).filter(SurveyQuestion.survey_id == survey.id).delete(synchronize_session=False)
    target_type = "student" if body.audience_type == "selected_families" else body.audience_type
    for target_id in body.target_ids:
        db.add(SurveyTarget(survey_id=survey.id, target_type=target_type, target_id=target_id))
    for order, item in enumerate(body.questions):
        question = SurveyQuestion(
            survey_id=survey.id, question_type=item.question_type, prompt=item.prompt,
            required=item.required, sort_order=order, scale_min=item.scale_min, scale_max=item.scale_max,
        )
        db.add(question); db.flush()
        for option_order, option in enumerate(item.options):
            db.add(SurveyOption(question_id=question.id, label=option.label, sort_order=option_order))


def _apply_input(survey: Survey, body: SurveyInput) -> None:
    for field in (
        "title", "introduction", "instructions", "audience_type", "anonymous", "response_mode",
        "opens_at", "closes_at", "reminder_at", "parent_results_visible", "push_enabled",
        "dashboard_card_enabled", "notices_feed_enabled",
    ):
        setattr(survey, field, getattr(body, field))


@router.get("/surveys/availability")
def availability(
    membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db),
):
    return {"available": _has_permission(db, membership)}


@router.get("/surveys/context")
def context(membership: Membership = Depends(require_survey_admin), db: Session = Depends(get_db)):
    school = db.query(School).filter(School.id == membership.school_id).one()
    branches = db.query(BranchCampus).filter(BranchCampus.school_id == school.id, BranchCampus.status == "active").order_by(BranchCampus.sort_order, BranchCampus.name).all()
    grades = db.query(GradeLevel).filter(GradeLevel.school_id == school.id, GradeLevel.status == "active").order_by(GradeLevel.sort_order, GradeLevel.name).all()
    classes = db.query(ClassSection).filter(ClassSection.school_id == school.id, ClassSection.status == "active").order_by(ClassSection.sort_order, ClassSection.name).all()
    linked_students = (
        db.query(Student).join(FhhLink, FhhLink.student_id == Student.id)
        .filter(Student.school_id == school.id, Student.status == "active", FhhLink.status == "active", FhhLink.revoked_at.is_(None))
        .distinct().order_by(Student.first_name, Student.last_name).all()
    )
    return {
        "school": {"id": school.id, "name": school.name, "timezone": school.timezone},
        "branches": [{"id": row.id, "name": row.name, "name_ar": row.name_ar} for row in branches],
        "grades": [{"id": row.id, "name": row.name, "name_ar": row.name_ar} for row in grades],
        "classes": [{"id": row.id, "name": row.name, "name_ar": row.name_ar, "grade_level_id": row.grade_level_id, "branch_campus_id": row.branch_campus_id} for row in classes],
        "linked_families": [{"id": row.id, "label": (row.preferred_name or f"{row.first_name} {row.last_name}").strip(), "label_ar": row.name_ar} for row in linked_students],
    }


@router.get("/surveys/permissions")
def permissions(membership: Membership = Depends(require_survey_admin), db: Session = Depends(get_db)):
    owner = db.query(SchoolSystemOwner).filter(SchoolSystemOwner.school_id == membership.school_id).first()
    rows = db.query(Membership, User).join(User, User.id == Membership.user_id).filter(
        Membership.school_id == membership.school_id, Membership.role == "school_admin",
    ).order_by(User.name, Membership.id).all()
    grants = db.query(MessagingPermissionGrant).filter(
        MessagingPermissionGrant.school_id == membership.school_id,
        MessagingPermissionGrant.permission == SURVEY_PERMISSION,
        MessagingPermissionGrant.revoked_at.is_(None),
    ).all()
    by_membership = {row.membership_id: row for row in grants}
    return {
        "can_manage": bool(owner and owner.membership_id == membership.id),
        "administrators": [
            {"membership_id": row.id, "name": user.name, "status": row.status, "enabled": row.id in by_membership, "grant_id": str(by_membership[row.id].public_id) if row.id in by_membership else None}
            for row, user in rows
        ],
    }


@router.post("/surveys/permissions")
def update_permission(body: PermissionInput, membership: Membership = Depends(require_survey_admin), db: Session = Depends(get_db)):
    try:
        require_owner(db, membership)
    except GovernanceForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except GovernanceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    target = db.query(Membership).filter(
        Membership.id == body.membership_id, Membership.school_id == membership.school_id,
        Membership.role == "school_admin", Membership.status == "active", Membership.revoked_at.is_(None),
    ).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Active administrator not found")
    grant = db.query(MessagingPermissionGrant).filter(
        MessagingPermissionGrant.school_id == membership.school_id,
        MessagingPermissionGrant.membership_id == target.id,
        MessagingPermissionGrant.permission == SURVEY_PERMISSION,
        MessagingPermissionGrant.revoked_at.is_(None),
    ).first()
    if body.enabled and grant is None:
        grant = MessagingPermissionGrant(school_id=membership.school_id, membership_id=target.id, permission=SURVEY_PERMISSION, granted_by_membership_id=membership.id, grant_reason=body.reason.strip())
        db.add(grant)
    elif not body.enabled and grant is not None:
        grant.revoked_at = datetime.now(UTC); grant.revoked_by_membership_id = membership.id; grant.revoke_reason = body.reason.strip()
    write_audit(db, membership.user_id, "school.survey_permission.updated", target, {"enabled": body.enabled, "reason": body.reason.strip()}, school_id=membership.school_id)
    db.commit()
    return {"membership_id": target.id, "enabled": body.enabled}


@router.get("/surveys")
def list_surveys(
    survey_status: str | None = Query(default=None, alias="status"),
    membership: Membership = Depends(require_survey_admin), db: Session = Depends(get_db),
):
    query = db.query(Survey).filter(Survey.school_id == membership.school_id)
    rows = query.order_by(Survey.created_at.desc(), Survey.id.desc()).all()
    changed = False
    for row in rows:
        changed = refresh_survey_state(row) or changed
    if changed:
        db.commit()
    if survey_status:
        rows = [row for row in rows if row.status == survey_status]
    return {"items": [_summary_payload(db, row) for row in rows]}


@router.post("/surveys", status_code=status.HTTP_201_CREATED)
def create_survey(body: SurveyInput, membership: Membership = Depends(require_survey_admin), db: Session = Depends(get_db)):
    _validate_targets(db, membership.school_id, body.audience_type, body.target_ids)
    survey = Survey(school_id=membership.school_id, created_by_membership_id=membership.id)
    _apply_input(survey, body); db.add(survey); db.flush()
    _replace_questions_and_targets(db, survey, body)
    write_audit(db, membership.user_id, "school.survey.draft_created", survey, {"audience_type": survey.audience_type, "question_count": len(body.questions)}, school_id=membership.school_id)
    db.commit(); db.refresh(survey)
    return _detail_payload(db, survey)


@router.put("/surveys/{survey_id}")
def update_survey(survey_id: UUID, body: SurveyInput, membership: Membership = Depends(require_survey_admin), db: Session = Depends(get_db)):
    survey = _survey_or_404(db, membership, survey_id, lock=True)
    if survey.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft surveys can be edited")
    _validate_targets(db, membership.school_id, body.audience_type, body.target_ids)
    _apply_input(survey, body); survey.version += 1
    _replace_questions_and_targets(db, survey, body)
    write_audit(db, membership.user_id, "school.survey.draft_updated", survey, {"version": survey.version}, school_id=membership.school_id)
    db.commit(); db.refresh(survey)
    return _detail_payload(db, survey)


@router.get("/surveys/{survey_id}")
def survey_detail(survey_id: UUID, membership: Membership = Depends(require_survey_admin), db: Session = Depends(get_db)):
    survey = _survey_or_404(db, membership, survey_id)
    db.commit()
    return _detail_payload(db, survey)


def _event(db: Session, survey: Survey, membership: Membership, action: str, detail: dict[str, Any] | None = None) -> SurveyEvent:
    row = SurveyEvent(survey_id=survey.id, school_id=survey.school_id, action=action, actor_membership_id=membership.id, detail=detail or {})
    db.add(row); db.flush()
    return row


@router.post("/surveys/{survey_id}/publish")
def publish(survey_id: UUID, membership: Membership = Depends(require_survey_admin), db: Session = Depends(get_db)):
    survey = _survey_or_404(db, membership, survey_id, lock=True)
    if survey.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft surveys can be published")
    now = datetime.now(UTC)
    if aware_utc(survey.closes_at) <= now:
        raise HTTPException(status_code=409, detail="Survey closing time has passed")
    survey.status = "open" if aware_utc(survey.opens_at) <= now else "scheduled"
    survey.published_at = now
    _event(db, survey, membership, "published", {"status": survey.status})
    if survey.push_enabled:
        enqueue_family_notifications(db, category="survey", source=survey, action="published", eligible_at=max(now, aware_utc(survey.opens_at)))
        if survey.reminder_at:
            enqueue_family_notifications(db, category="survey", source=survey, action="reminder", eligible_at=aware_utc(survey.reminder_at))
    write_audit(db, membership.user_id, "school.survey.published", survey, {"status": survey.status}, school_id=membership.school_id)
    db.commit(); db.refresh(survey)
    return _detail_payload(db, survey)


@router.post("/surveys/{survey_id}/close")
def close_survey(survey_id: UUID, membership: Membership = Depends(require_survey_admin), db: Session = Depends(get_db)):
    survey = _survey_or_404(db, membership, survey_id, lock=True)
    if survey.status not in {"open", "scheduled"}:
        raise HTTPException(status_code=409, detail="Survey is not open or scheduled")
    survey.status = "closed"; survey.closed_at = datetime.now(UTC)
    _event(db, survey, membership, "closed")
    write_audit(db, membership.user_id, "school.survey.closed", survey, {}, school_id=membership.school_id)
    db.commit(); return _detail_payload(db, survey)


@router.post("/surveys/{survey_id}/reopen")
def reopen_survey(
    survey_id: UUID,
    body: ReopenSurveyInput,
    membership: Membership = Depends(require_survey_admin),
    db: Session = Depends(get_db),
):
    survey = _survey_or_404(db, membership, survey_id, lock=True)
    if survey.status != "closed":
        raise HTTPException(status_code=409, detail="Only closed surveys can be reopened")
    previous_closes_at = aware_utc(survey.closes_at)
    next_closes_at = aware_utc(body.closes_at) if body.closes_at is not None else previous_closes_at
    if next_closes_at <= datetime.now(UTC):
        raise HTTPException(status_code=409, detail="Choose a future closing time before reopening")
    survey.closes_at = next_closes_at
    survey.status = "open"; survey.closed_at = None
    detail = {"previous_closes_at": previous_closes_at.isoformat(), "closes_at": next_closes_at.isoformat()}
    _event(db, survey, membership, "reopened", detail)
    write_audit(db, membership.user_id, "school.survey.reopened", survey, detail, school_id=membership.school_id)
    db.commit(); return _detail_payload(db, survey)


@router.post("/surveys/{survey_id}/archive")
def archive_survey(survey_id: UUID, membership: Membership = Depends(require_survey_admin), db: Session = Depends(get_db)):
    survey = _survey_or_404(db, membership, survey_id, lock=True)
    if survey.status != "closed":
        raise HTTPException(status_code=409, detail="Only closed surveys can be archived")
    survey.status = "archived"; survey.archived_at = datetime.now(UTC)
    _event(db, survey, membership, "archived")
    write_audit(db, membership.user_id, "school.survey.archived", survey, {}, school_id=membership.school_id)
    db.commit(); return _detail_payload(db, survey)


@router.post("/surveys/{survey_id}/remind")
def remind(survey_id: UUID, membership: Membership = Depends(require_survey_admin), db: Session = Depends(get_db)):
    survey = _survey_or_404(db, membership, survey_id, lock=True)
    if survey.status != "open":
        raise HTTPException(status_code=409, detail="Only open surveys can send reminders")
    existing = db.query(SurveyEvent).filter(SurveyEvent.survey_id == survey.id, SurveyEvent.action == "reminder_sent").first()
    if existing:
        return {"status": "already_sent", "event_id": str(existing.event_id)}
    scheduled = db.query(NotificationOutbox).filter(
        NotificationOutbox.school_id == survey.school_id, NotificationOutbox.source_type == "survey",
        NotificationOutbox.source_id == survey.id, NotificationOutbox.source_action == "reminder",
        NotificationOutbox.state.in_(("held", "pending", "leased", "dispatched", "provider_accepted", "failed")),
    ).first()
    if scheduled:
        return {"status": "already_scheduled", "notification_event_id": str(scheduled.event_id)}
    event = _event(db, survey, membership, "reminder_sent")
    enqueue_family_notifications(db, category="survey", source=survey, action="reminder", eligible_at=datetime.now(UTC), event_marker=str(event.event_id))
    write_audit(db, membership.user_id, "school.survey.reminder_sent", survey, {}, school_id=membership.school_id)
    db.commit(); return {"status": "sent", "event_id": str(event.event_id)}


def _answer_result(db: Session, question: SurveyQuestion, responses: int) -> dict[str, Any]:
    answers = db.query(SurveyAnswer).filter(SurveyAnswer.question_id == question.id).all()
    base = {"question_id": str(question.public_id), "question_type": question.question_type, "prompt": question.prompt, "answer_count": len(answers)}
    if question.question_type in {"single_choice", "multiple_choice"}:
        options = db.query(SurveyOption).filter(SurveyOption.question_id == question.id).order_by(SurveyOption.sort_order).all()
        counts = {row.id: 0 for row in options}
        for answer in answers:
            for option_id in answer.selected_option_ids or []:
                if option_id in counts: counts[option_id] += 1
        base["distribution"] = [{"option_id": str(row.public_id), "label": row.label, "count": counts[row.id]} for row in options]
    elif question.question_type == "yes_no":
        base["distribution"] = [{"label": "Yes", "count": sum(1 for row in answers if row.answer_boolean is True)}, {"label": "No", "count": sum(1 for row in answers if row.answer_boolean is False)}]
    elif question.question_type == "rating":
        values = [row.answer_number for row in answers if row.answer_number is not None]
        base["average"] = round(sum(values) / len(values), 2) if values else None
        base["distribution"] = [{"label": str(value), "count": values.count(value)} for value in range(question.scale_min, question.scale_max + 1)]
    return base


@router.get("/surveys/{survey_id}/results")
def results(
    survey_id: UUID, q: str = Query(default="", max_length=100), page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=50),
    membership: Membership = Depends(require_survey_admin), db: Session = Depends(get_db),
):
    survey = _survey_or_404(db, membership, survey_id)
    responses = db.query(SurveyResponse).filter(SurveyResponse.survey_id == survey.id).order_by(SurveyResponse.submitted_at.desc(), SurveyResponse.id.desc()).all()
    questions = db.query(SurveyQuestion).filter(SurveyQuestion.survey_id == survey.id).order_by(SurveyQuestion.sort_order).all()
    text_question_ids = [row.id for row in questions if row.question_type in {"short_text", "long_text"}]
    text_query = db.query(SurveyAnswer, SurveyQuestion, SurveyResponse).join(SurveyQuestion, SurveyQuestion.id == SurveyAnswer.question_id).join(SurveyResponse, SurveyResponse.id == SurveyAnswer.response_id).filter(
        SurveyAnswer.question_id.in_(text_question_ids), SurveyAnswer.answer_text.is_not(None), SurveyAnswer.answer_text != "",
    ) if text_question_ids else None
    if text_query is not None and q.strip():
        text_query = text_query.filter(SurveyAnswer.answer_text.ilike(f"%{q.strip()}%"))
    text_total = int(text_query.count()) if text_query is not None else 0
    text_rows = text_query.order_by(SurveyResponse.submitted_at.desc(), SurveyAnswer.id.desc()).offset((page - 1) * page_size).limit(page_size).all() if text_query is not None else []
    eligible_count = _eligible_count(db, survey)
    timeline = db.query(func.date(SurveyResponse.submitted_at), func.count(SurveyResponse.id)).filter(SurveyResponse.survey_id == survey.id).group_by(func.date(SurveyResponse.submitted_at)).order_by(func.date(SurveyResponse.submitted_at)).all()
    return {
        "survey": _detail_payload(db, survey),
        "response_rate": {"completed": len(responses), "outstanding": max(eligible_count - len(responses), 0)},
        "questions": [_answer_result(db, question, len(responses)) for question in questions],
        "responses_over_time": [{"date": str(day), "count": count} for day, count in timeline],
        "free_text": {
            "items": [
                {"question_id": str(question.public_id), "prompt": question.prompt, "text": answer.answer_text, "submitted_at": response.submitted_at, **({"respondent": response.respondent_label} if not survey.anonymous else {})}
                for answer, question, response in text_rows
            ],
            "page": page, "page_size": page_size, "total": text_total,
        },
        "respondents": [] if survey.anonymous else [{"label": row.respondent_label, "submitted_at": row.submitted_at} for row in responses[:500]],
    }


def _csv_rows(db: Session, survey: Survey) -> list[list[Any]]:
    questions = db.query(SurveyQuestion).filter(SurveyQuestion.survey_id == survey.id).order_by(SurveyQuestion.sort_order).all()
    options = db.query(SurveyOption).filter(SurveyOption.question_id.in_([row.id for row in questions])).all() if questions else []
    option_label = {row.id: row.label for row in options}
    responses = db.query(SurveyResponse).filter(SurveyResponse.survey_id == survey.id).order_by(SurveyResponse.submitted_at, SurveyResponse.id).all()
    rows: list[list[Any]] = [["survey_title", survey.title], ["status", survey.status], ["audience", survey.audience_type], ["anonymous", str(bool(survey.anonymous)).lower()], ["response_mode", survey.response_mode], ["opens_at", survey.opens_at.isoformat()], ["closes_at", survey.closes_at.isoformat()], [], ["response_timestamp", *([] if survey.anonymous else ["respondent"]), *[row.prompt for row in questions]]]
    for response in responses:
        answers = {row.question_id: row for row in db.query(SurveyAnswer).filter(SurveyAnswer.response_id == response.id).all()}
        values: list[Any] = []
        for question in questions:
            answer = answers.get(question.id)
            if answer is None: values.append("")
            elif question.question_type in {"single_choice", "multiple_choice"}: values.append(" | ".join(option_label.get(value, "") for value in answer.selected_option_ids or []))
            elif question.question_type == "yes_no": values.append("Yes" if answer.answer_boolean else "No")
            elif question.question_type == "rating": values.append(answer.answer_number)
            else: values.append(answer.answer_text or "")
        rows.append([response.submitted_at.isoformat(), *([] if survey.anonymous else [response.respondent_label or ""]), *values])
    return rows


@router.get("/surveys/{survey_id}/export.csv")
def export_csv(survey_id: UUID, membership: Membership = Depends(require_survey_admin), db: Session = Depends(get_db)):
    survey = _survey_or_404(db, membership, survey_id)
    output = io.StringIO(newline=""); writer = csv.writer(output); writer.writerows(_csv_rows(db, survey))
    _event(db, survey, membership, "exported", {"format": "csv"})
    write_audit(db, membership.user_id, "school.survey.exported", survey, {"format": "csv", "anonymous": bool(survey.anonymous)}, school_id=membership.school_id)
    db.commit()
    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "-", survey.title).strip("-")[:60] or "survey"
    return Response(content="\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{safe_title}-results.csv"', "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


def _response_key(survey: Survey, identity: FhhMessagingIdentity, household_ref: str) -> str:
    unit = str(identity.external_subject_ref) if survey.response_mode == "guardian" else household_ref
    return hmac.new(settings.SESSION_SECRET.encode("utf-8"), f"survey:{survey.public_id}:{unit}".encode("utf-8"), hashlib.sha256).hexdigest()


def _parent_survey(db: Session, public_id: UUID, link: FhhLink) -> Survey:
    survey = db.query(Survey).filter(Survey.public_id == public_id, Survey.school_id == link.school_id).first()
    if survey is None or not link_is_eligible(db, survey, link):
        raise HTTPException(status_code=404, detail="Survey is unavailable")
    refresh_survey_state(survey)
    return survey


def _parent_payload(db: Session, survey: Survey, identity: FhhMessagingIdentity, household_ref: str) -> dict[str, Any]:
    completed = db.query(SurveyResponse.id).filter(SurveyResponse.survey_id == survey.id, SurveyResponse.response_key_hash == _response_key(survey, identity, household_ref)).first() is not None
    school = db.query(School).filter(School.id == survey.school_id).one()
    parent_results = None
    if survey.parent_results_visible and survey.status == "closed":
        response_count = int(db.query(func.count(SurveyResponse.id)).filter(SurveyResponse.survey_id == survey.id).scalar() or 0)
        questions = db.query(SurveyQuestion).filter(SurveyQuestion.survey_id == survey.id).order_by(SurveyQuestion.sort_order).all()
        parent_results = {
            "response_count": response_count,
            "questions": [_answer_result(db, question, response_count) for question in questions],
        }
    return {
        "id": str(survey.public_id), "school": school.name, "school_ar": school.name_ar,
        "title": survey.title, "introduction": survey.introduction, "instructions": survey.instructions,
        "status": survey.status, "opens_at": survey.opens_at, "closes_at": survey.closes_at,
        "anonymous": bool(survey.anonymous), "response_mode": survey.response_mode,
        "parent_results_visible": bool(survey.parent_results_visible), "dashboard_card_enabled": bool(survey.dashboard_card_enabled),
        "notices_feed_enabled": bool(survey.notices_feed_enabled), "completed": completed,
        "questions": _question_payload(db, survey.id), "parent_results": parent_results,
    }


def _bind_household_ref(link: FhhLink, household_ref: str) -> None:
    if link.fhh_household_ref and not hmac.compare_digest(link.fhh_household_ref, household_ref):
        raise HTTPException(status_code=409, detail="Household evidence changed")
    link.fhh_household_ref = household_ref


def _integration_actor(request: Request, db: Session, link_id: int, token: str | None, assertion: str | None, body: dict[str, Any]):
    link = _link(db, link_id, token)
    identity, identity_link = verify_and_consume_actor_assertion(db, request=request, link=link, assertion=assertion, body=body)
    return link, identity, identity_link


@integration_router.post("/links/{link_id}/surveys/query")
def parent_surveys(
    link_id: int, body: HouseholdEvidence, request: Request,
    x_fhh_link_token: str | None = Header(default=None), x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    payload = body.model_dump(mode="json")
    link, identity, _ = _integration_actor(request, db, link_id, x_fhh_link_token, x_fhh_messaging_actor, payload)
    _bind_household_ref(link, body.household_ref)
    surveys = db.query(Survey).filter(Survey.school_id == link.school_id, Survey.status.notin_(("draft", "archived"))).order_by(Survey.closes_at, Survey.id).all()
    result = []
    for survey in surveys:
        refresh_survey_state(survey)
        if link_is_eligible(db, survey, link):
            result.append(_parent_payload(db, survey, identity, body.household_ref))
    db.commit()
    return {"items": result}


@integration_router.post("/links/{link_id}/surveys/{survey_id}/open")
def parent_survey_open(
    link_id: int, survey_id: UUID, body: HouseholdEvidence, request: Request,
    x_fhh_link_token: str | None = Header(default=None), x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    payload = body.model_dump(mode="json")
    link, identity, _ = _integration_actor(request, db, link_id, x_fhh_link_token, x_fhh_messaging_actor, payload)
    _bind_household_ref(link, body.household_ref)
    survey = _parent_survey(db, survey_id, link)
    if survey.status == "scheduled": raise HTTPException(status_code=409, detail="Survey is not open yet")
    db.commit()
    return _parent_payload(db, survey, identity, body.household_ref)


def _answer_row(db: Session, question: SurveyQuestion, answer: ParentAnswerInput) -> SurveyAnswer | None:
    value = answer.value
    if value is None or value == "" or value == []:
        if question.required: raise HTTPException(status_code=422, detail=f"Required question is unanswered: {question.prompt}")
        return None
    row = SurveyAnswer(question_id=question.id)
    if question.question_type in {"single_choice", "multiple_choice"}:
        raw = value if isinstance(value, list) else [value]
        if question.question_type == "single_choice" and len(raw) != 1: raise HTTPException(status_code=422, detail="Single-choice answer is invalid")
        try: public_ids = [UUID(str(item)) for item in raw]
        except ValueError as exc: raise HTTPException(status_code=422, detail="Choice answer is invalid") from exc
        options = db.query(SurveyOption).filter(SurveyOption.question_id == question.id, SurveyOption.public_id.in_(public_ids)).all()
        if len(options) != len(set(public_ids)): raise HTTPException(status_code=422, detail="Choice answer is invalid")
        order = {row.public_id: row.id for row in options}; row.selected_option_ids = [order[item] for item in public_ids]
    elif question.question_type == "yes_no":
        if not isinstance(value, bool): raise HTTPException(status_code=422, detail="Yes/no answer is invalid")
        row.answer_boolean = value
    elif question.question_type == "rating":
        if isinstance(value, bool) or not isinstance(value, int) or not question.scale_min <= value <= question.scale_max: raise HTTPException(status_code=422, detail="Rating answer is invalid")
        row.answer_number = value
    else:
        if not isinstance(value, str): raise HTTPException(status_code=422, detail="Text answer is invalid")
        clean = value.strip(); limit = 500 if question.question_type == "short_text" else 5000
        if not clean and question.required: raise HTTPException(status_code=422, detail=f"Required question is unanswered: {question.prompt}")
        if len(clean) > limit: raise HTTPException(status_code=422, detail="Text answer is too long")
        if not clean: return None
        row.answer_text = clean
    return row


@integration_router.post("/links/{link_id}/surveys/{survey_id}/responses", status_code=status.HTTP_201_CREATED)
def submit_parent_response(
    link_id: int, survey_id: UUID, body: ParentSubmission, request: Request,
    x_fhh_link_token: str | None = Header(default=None), x_fhh_messaging_actor: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    payload = body.model_dump(mode="json")
    link, identity, _ = _integration_actor(request, db, link_id, x_fhh_link_token, x_fhh_messaging_actor, payload)
    _bind_household_ref(link, body.household_ref)
    survey = _parent_survey(db, survey_id, link)
    if survey.status != "open": raise HTTPException(status_code=409, detail="Survey is closed")
    questions = db.query(SurveyQuestion).filter(SurveyQuestion.survey_id == survey.id).order_by(SurveyQuestion.sort_order).all()
    by_public = {row.public_id: row for row in questions}
    submitted = {row.question_id: row for row in body.answers}
    if any(question_id not in by_public for question_id in submitted): raise HTTPException(status_code=422, detail="Response contains an unknown question")
    response = SurveyResponse(
        survey_id=survey.id, response_key_hash=_response_key(survey, identity, body.household_ref),
        respondent_label=None if survey.anonymous else (identity.display_name if survey.response_mode == "guardian" else f"Household via {identity.display_name}"),
    )
    db.add(response)
    try:
        db.flush()
        for question in questions:
            answer_input = submitted.get(question.public_id, ParentAnswerInput(question_id=question.public_id, value=None))
            row = _answer_row(db, question, answer_input)
            if row is not None:
                row.response_id = response.id; db.add(row)
        db.commit(); db.refresh(response)
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(status_code=409, detail="This guardian or household has already responded") from exc
    return {"status": "submitted", "response_id": str(response.public_id), "submitted_at": response.submitted_at, "anonymous": bool(survey.anonymous), "response_mode": survey.response_mode}

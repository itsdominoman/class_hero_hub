from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .models_school import ClassSection, Enrolment, FhhLink, Student, Survey, SurveyTarget
from .school_scope import open_interval_expression


UTC = timezone.utc


def aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def refresh_survey_state(survey: Survey, *, now: datetime | None = None) -> bool:
    now = aware_utc(now or datetime.now(UTC))
    if survey.status in {"draft", "closed", "archived"}:
        return False
    before = survey.status
    if now >= aware_utc(survey.closes_at):
        survey.status = "closed"
        survey.closed_at = survey.closed_at or now
    elif now >= aware_utc(survey.opens_at):
        survey.status = "open"
        survey.closed_at = None
    else:
        survey.status = "scheduled"
    return survey.status != before


def survey_student_ids(db: Session, survey: Survey) -> set[int]:
    active_students = db.query(Student.id).filter(
        Student.school_id == survey.school_id,
        Student.status == "active",
    )
    if survey.audience_type == "whole_school":
        return {int(row[0]) for row in active_students.all()}
    targets = db.query(SurveyTarget).filter(SurveyTarget.survey_id == survey.id).all()
    target_ids = {row.target_id for row in targets}
    if not target_ids:
        return set()
    if survey.audience_type == "selected_families":
        return {int(row[0]) for row in active_students.filter(Student.id.in_(target_ids)).all()}
    today = datetime.now(UTC).date()
    query = (
        db.query(Student.id)
        .join(Enrolment, Enrolment.student_id == Student.id)
        .join(ClassSection, ClassSection.id == Enrolment.class_section_id)
        .filter(
            Student.school_id == survey.school_id,
            Student.status == "active",
            Enrolment.school_id == survey.school_id,
            Enrolment.kind == "member",
            *open_interval_expression(Enrolment, today),
        )
    )
    column = {
        "branch": ClassSection.branch_campus_id,
        "grade": ClassSection.grade_level_id,
        "class": ClassSection.id,
    }[survey.audience_type]
    return {int(row[0]) for row in query.filter(column.in_(target_ids)).distinct().all()}


def eligible_links(db: Session, survey: Survey) -> list[FhhLink]:
    student_ids = survey_student_ids(db, survey)
    if not student_ids:
        return []
    return (
        db.query(FhhLink)
        .join(Student, Student.id == FhhLink.student_id)
        .filter(
            FhhLink.school_id == survey.school_id,
            FhhLink.student_id.in_(student_ids),
            FhhLink.status == "active",
            FhhLink.revoked_at.is_(None),
            Student.status == "active",
        )
        .order_by(FhhLink.id)
        .all()
    )


def link_is_eligible(db: Session, survey: Survey, link: FhhLink) -> bool:
    return (
        link.school_id == survey.school_id
        and link.status == "active"
        and link.revoked_at is None
        and link.student_id in survey_student_ids(db, survey)
    )

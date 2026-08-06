from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, and_, case, cast, exists, func, or_, select
from sqlalchemy.orm import Session, aliased

from ..database import get_db
from ..entitlement_service import REPORTS_INSIGHTS, require_school_entitlement
from ..department_scope import active_department_membership_ids, active_head_department_ids
from ..models_school import (
    BehaviourCategory,
    BehaviourEvent,
    BranchCampus,
    ClassSection,
    Department,
    Enrolment,
    GradeLevel,
    Membership,
    MessageDocument,
    School,
    Student,
    Subject,
    SubjectGroup,
    User,
)
from ..document_rendering import render_behaviour_report_csv, render_behaviour_report_pdf
from ..generated_document_service import (
    GeneratedDocumentValidationError,
    create_generated_document,
    document_payload,
)
from ..school_scope import require_school_role, write_audit
from ..school_roles import HEAD_OF_DEPARTMENT, REPORTING_ROLES, STAFF_ROLES


router = APIRouter(dependencies=[Depends(require_school_role(*REPORTING_ROLES)), Depends(require_school_entitlement(REPORTS_INSIGHTS))])

DUTY_CONTEXTS = {"break", "lunch", "playground", "hallway", "assembly", "bus", "general_duty"}
MATRIX_DIMENSIONS = {"student", "class_section", "grade", "subject", "subject_group", "teacher", "duty_context", "category", "category_type", "date_bucket"}
MATRIX_ORDER_BY = {"total_events", "positive_count", "needs_work_count", "signed_points_total"}
MAX_RANGE_DAYS = 366
MAX_MATRIX_ROWS = 100
MAX_MATRIX_CELLS = 2_500
MAX_EXPORT_EVENTS = 25_000
STAFF_REVIEW_CURRENT_MIN_EVENTS = 20
STAFF_REVIEW_PRIOR_MIN_EVENTS = 10
STAFF_REVIEW_NEEDS_WORK_RATIO_DELTA = 0.20
INCOMPATIBLE_MATRIX_PAIRS = {
    frozenset(("subject", "duty_context")),
    frozenset(("subject_group", "duty_context")),
}


class BehaviourDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["pdf", "csv"] = "pdf"
    language: Literal["en", "ar"] = "en"
    date_from: date | None = None
    date_to: date | None = None
    branch_campus_id: int | None = None
    grade_level_id: int | None = None
    class_section_id: int | None = None
    subject_id: int | None = None
    subject_group_id: int | None = None
    duty_context: str | None = None
    category_id: int | None = None
    actor_user_id: int | None = None
    student_id: int | None = None
    category_type: Literal["positive", "needs_work"] | None = None


@dataclass
class ReportFilters:
    date_from: date
    date_to: date
    start: datetime
    end: datetime
    branch_campus_id: int | None
    grade_level_id: int | None
    class_section_id: int | None
    subject_id: int | None
    subject_group_id: int | None
    duty_context: str | None
    category_id: int | None
    actor_user_id: int | None
    student_id: int | None
    category_type: str | None
    school_timezone: str

    def payload(self) -> dict:
        # IDs are input selectors, not report payload dimensions.
        return {"date_from": self.date_from.isoformat(), "date_to": self.date_to.isoformat(), "category_type": self.category_type, "duty_context": self.duty_context, "timezone": self.school_timezone}


def _school_dates(school: School, date_from: date | None, date_to: date | None) -> tuple[date, date, datetime, datetime]:
    try:
        zone = ZoneInfo(school.timezone or "UTC")
    except Exception:
        zone = timezone.utc
    today = datetime.now(zone).date()
    end_date = date_to or today
    start_date = date_from or (end_date - timedelta(days=29))
    if start_date > end_date:
        raise HTTPException(422, "date_from must be on or before date_to")
    if (end_date - start_date).days + 1 > MAX_RANGE_DAYS:
        raise HTTPException(422, f"Date range may not exceed {MAX_RANGE_DAYS} days")
    # Event timestamps are stored as UTC. SQLite tests tolerate these values too.
    start = datetime.combine(start_date, time.min, tzinfo=zone).astimezone(timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=zone).astimezone(timezone.utc)
    return start_date, end_date, start, end


def _require_school_row(db: Session, model, row_id: int | None, school_id: int, field: str):
    if row_id is None:
        return
    if not db.query(model.id).filter(model.id == row_id, model.school_id == school_id).first():
        raise HTTPException(422, f"Invalid {field} for school")


def _scoped_actor_user_ids(db: Session, membership: Membership) -> frozenset[int] | None:
    """Return None for school-wide management or current department staff for an HOD."""
    if membership.role != HEAD_OF_DEPARTMENT:
        return None
    department_ids = active_head_department_ids(
        db,
        school_id=membership.school_id,
        membership_id=membership.id,
    )
    membership_ids = active_department_membership_ids(
        db,
        school_id=membership.school_id,
        department_ids=department_ids,
    )
    if not membership_ids:
        return frozenset()
    return frozenset(
        row[0]
        for row in db.query(Membership.user_id)
        .filter(
            Membership.school_id == membership.school_id,
            Membership.id.in_(membership_ids),
            Membership.status == "active",
            Membership.revoked_at.is_(None),
        )
        .all()
    )


def _filters(
    db: Session, membership: Membership, *, date_from: date | None = None, date_to: date | None = None,
    branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None,
    subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None,
    category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None,
    category_type: str | None = None,
) -> ReportFilters:
    school = db.query(School).filter(School.id == membership.school_id).one()
    start_date, end_date, start, end = _school_dates(school, date_from, date_to)
    _require_school_row(db, BranchCampus, branch_campus_id, membership.school_id, "branch_campus_id")
    _require_school_row(db, GradeLevel, grade_level_id, membership.school_id, "grade_level_id")
    _require_school_row(db, ClassSection, class_section_id, membership.school_id, "class_section_id")
    _require_school_row(db, Subject, subject_id, membership.school_id, "subject_id")
    _require_school_row(db, SubjectGroup, subject_group_id, membership.school_id, "subject_group_id")
    _require_school_row(db, BehaviourCategory, category_id, membership.school_id, "category_id")
    _require_school_row(db, Student, student_id, membership.school_id, "student_id")
    if actor_user_id is not None:
        scoped_actor_user_ids = _scoped_actor_user_ids(db, membership)
        if scoped_actor_user_ids is not None and actor_user_id not in scoped_actor_user_ids:
            raise HTTPException(422, "Invalid actor_user_id for reporting scope")
        if not db.query(BehaviourEvent.id).filter(BehaviourEvent.school_id == membership.school_id, BehaviourEvent.actor_user_id == actor_user_id).first():
            raise HTTPException(422, "Invalid actor_user_id for school")
    if duty_context is not None and duty_context not in DUTY_CONTEXTS:
        raise HTTPException(422, "Invalid duty_context")
    if category_type is not None and category_type not in {"positive", "needs_work"}:
        raise HTTPException(422, "category_type must be positive or needs_work")
    if subject_group_id is not None:
        group = db.query(SubjectGroup).filter(SubjectGroup.id == subject_group_id).one()
        if subject_id is not None and group.subject_id != subject_id:
            raise HTTPException(422, "subject_group_id does not belong to subject_id")
        if class_section_id is not None and group.class_section_id not in {None, class_section_id}:
            raise HTTPException(422, "subject_group_id does not belong to class_section_id")
    if category_id is not None and category_type is not None:
        category = db.query(BehaviourCategory).filter(BehaviourCategory.id == category_id).one()
        if category.type != category_type:
            raise HTTPException(422, "category_id does not match category_type")
    if duty_context is not None and (subject_id is not None or subject_group_id is not None):
        raise HTTPException(422, "duty_context cannot be combined with subject filters")
    return ReportFilters(start_date, end_date, start, end, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type, school.timezone or "UTC")


def _local_day_expr(db: Session, timezone_name: str, timestamp=BehaviourEvent.created_at):
    """Return the school-local calendar date for PostgreSQL and SQLite tests."""
    if db.bind and db.bind.dialect.name == "postgresql":
        return func.date(func.timezone(timezone_name, timestamp))
    try:
        zone = ZoneInfo(timezone_name)
    except Exception:
        zone = timezone.utc
    offset = datetime.now(zone).utcoffset() or timedelta(0)
    minutes = int(offset.total_seconds() // 60)
    sign = "+" if minutes >= 0 else "-"
    modifier = f"{sign}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d}"
    return func.date(timestamp, modifier)


def _query(db: Session, membership: Membership, filters: ReportFilters):
    """Return one event-time query with only bounded, school-scoped rows."""
    school_id = membership.school_id
    direct_section = aliased(ClassSection)
    group = aliased(SubjectGroup)
    group_section = aliased(ClassSection)
    historic_enrolment = aliased(Enrolment)
    historic_section = aliased(ClassSection)
    grade = aliased(GradeLevel)
    group_grade = aliased(GradeLevel)
    historic_grade = aliased(GradeLevel)
    subject = aliased(Subject)
    actor = aliased(User)

    event_day = _local_day_expr(db, filters.school_timezone)
    # Only attribute duty/general events when exactly one class enrolment spans
    # the event date. Ambiguous history deliberately remains Unattributed.
    historic_enrolment_id = select(func.min(Enrolment.id)).where(
        Enrolment.school_id == BehaviourEvent.school_id,
        Enrolment.student_id == BehaviourEvent.student_id,
        Enrolment.class_section_id.is_not(None),
        Enrolment.kind == "member",
        Enrolment.valid_from <= event_day,
        or_(Enrolment.valid_to.is_(None), Enrolment.valid_to > event_day),
    ).having(func.count(func.distinct(Enrolment.class_section_id)) == 1).correlate(BehaviourEvent).scalar_subquery()
    query = db.query(BehaviourEvent, BehaviourCategory, Student, actor, direct_section, group, subject, grade, group_grade, historic_section, historic_grade).join(
        BehaviourCategory, BehaviourCategory.id == BehaviourEvent.category_id
    ).join(Student, Student.id == BehaviourEvent.student_id).outerjoin(actor, actor.id == BehaviourEvent.actor_user_id).outerjoin(
        direct_section, direct_section.id == BehaviourEvent.class_section_id
    ).outerjoin(group, group.id == BehaviourEvent.subject_group_id).outerjoin(subject, subject.id == group.subject_id).outerjoin(
        group_section, group_section.id == group.class_section_id
    ).outerjoin(grade, grade.id == direct_section.grade_level_id).outerjoin(group_grade, group_grade.id == func.coalesce(group.grade_level_id, group_section.grade_level_id)).outerjoin(
        historic_enrolment,
        and_(
            historic_enrolment.id == historic_enrolment_id,
            BehaviourEvent.context_type.in_(("duty", "general")),
        ),
    ).outerjoin(historic_section, historic_section.id == historic_enrolment.class_section_id).outerjoin(historic_grade, historic_grade.id == historic_section.grade_level_id).filter(
        BehaviourEvent.school_id == school_id,
        BehaviourEvent.reversed_at.is_(None),
        BehaviourEvent.created_at >= filters.start,
        BehaviourEvent.created_at < filters.end,
    )
    scoped_actor_user_ids = _scoped_actor_user_ids(db, membership)
    if scoped_actor_user_ids is not None:
        query = query.filter(BehaviourEvent.actor_user_id.in_(scoped_actor_user_ids))

    class_id = func.coalesce(BehaviourEvent.class_section_id, group.class_section_id, historic_section.id)
    grade_id = func.coalesce(grade.id, group_grade.id, historic_grade.id)
    branch_id = func.coalesce(direct_section.branch_campus_id, group_section.branch_campus_id, historic_section.branch_campus_id)
    if filters.branch_campus_id is not None: query = query.filter(branch_id == filters.branch_campus_id)
    if filters.grade_level_id is not None: query = query.filter(grade_id == filters.grade_level_id)
    if filters.class_section_id is not None: query = query.filter(class_id == filters.class_section_id)
    if filters.subject_id is not None: query = query.filter(subject.id == filters.subject_id)
    if filters.subject_group_id is not None: query = query.filter(BehaviourEvent.subject_group_id == filters.subject_group_id)
    if filters.duty_context is not None: query = query.filter(BehaviourEvent.context_type == "duty", BehaviourEvent.duty_context == filters.duty_context)
    if filters.category_id is not None: query = query.filter(BehaviourEvent.category_id == filters.category_id)
    if filters.actor_user_id is not None: query = query.filter(BehaviourEvent.actor_user_id == filters.actor_user_id)
    if filters.student_id is not None: query = query.filter(BehaviourEvent.student_id == filters.student_id)
    if filters.category_type is not None: query = query.filter(BehaviourCategory.type == filters.category_type)
    query._report_aliases = {
        "actor": actor, "direct_section": direct_section, "group": group,
        "group_section": group_section, "subject": subject, "grade": grade,
        "group_grade": group_grade, "historic_section": historic_section,
        "historic_grade": historic_grade,
    }
    return query


def _measures():
    return (
        func.count(BehaviourEvent.id).label("total_events"),
        func.sum(case((BehaviourCategory.type == "positive", 1), else_=0)).label("positive_count"),
        func.sum(case((BehaviourCategory.type == "needs_work", 1), else_=0)).label("needs_work_count"),
        func.coalesce(func.sum(BehaviourEvent.points_delta), 0).label("signed_points_total"),
        func.count(func.distinct(BehaviourEvent.student_id)).label("active_students"),
    )


def _metric_payload(row, *, include_students: bool = True) -> dict:
    payload = {name: int(getattr(row, name) or 0) for name in ("total_events", "positive_count", "needs_work_count", "signed_points_total")}
    if include_students: payload["active_students"] = int(getattr(row, "active_students") or 0)
    return payload


def _display_student(student: Student) -> str:
    return student.preferred_name or f"{student.first_name} {student.last_name}".strip()


@router.get("/reports/behaviour/context")
def report_context(
    membership: Membership = Depends(require_school_role(*REPORTING_ROLES)),
    db: Session = Depends(get_db),
):
    school_id = membership.school_id
    scoped_user_ids = _scoped_actor_user_ids(db, membership)
    grade_levels = (
        db.query(GradeLevel)
        .filter(GradeLevel.school_id == school_id, GradeLevel.status == "active")
        .order_by(GradeLevel.sort_order, func.lower(GradeLevel.name), GradeLevel.id)
        .all()
    )
    class_sections = (
        db.query(ClassSection)
        .filter(ClassSection.school_id == school_id, ClassSection.status == "active")
        .order_by(ClassSection.grade_level_id, ClassSection.sort_order, func.lower(ClassSection.name), ClassSection.id)
        .all()
    )
    subjects = (
        db.query(Subject)
        .filter(Subject.school_id == school_id, Subject.status == "active")
        .order_by(func.lower(Subject.name), Subject.id)
        .all()
    )
    categories = (
        db.query(BehaviourCategory)
        .filter(BehaviourCategory.school_id == school_id, BehaviourCategory.active.is_(True))
        .order_by(BehaviourCategory.type, BehaviourCategory.sort_order, func.lower(BehaviourCategory.label), BehaviourCategory.id)
        .all()
    )
    staff_query = (
        db.query(Membership, User)
        .join(User, User.id == Membership.user_id)
        .filter(
            Membership.school_id == school_id,
            Membership.role.in_(STAFF_ROLES),
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            User.status == "active",
        )
    )
    if scoped_user_ids is not None:
        staff_query = staff_query.filter(Membership.user_id.in_(scoped_user_ids))
    staff_rows = staff_query.order_by(func.lower(User.name), Membership.id).all()
    department_ids = (
        active_head_department_ids(db, school_id=school_id, membership_id=membership.id)
        if membership.role == HEAD_OF_DEPARTMENT
        else frozenset()
    )
    departments = (
        db.query(Department)
        .filter(Department.school_id == school_id, Department.id.in_(department_ids))
        .order_by(func.lower(Department.name), Department.id)
        .all()
        if department_ids
        else []
    )
    return {
        "scope": {
            "type": "department" if membership.role == HEAD_OF_DEPARTMENT else "school",
            "departments": [
                {"id": row.id, "name": row.name, "name_ar": row.name_ar}
                for row in departments
            ],
        },
        "grade_levels": [
            {"id": row.id, "name": row.name, "name_ar": row.name_ar, "status": row.status, "sort_order": row.sort_order}
            for row in grade_levels
        ],
        "class_sections": [
            {
                "id": row.id,
                "name": row.name,
                "name_ar": row.name_ar,
                "status": row.status,
                "sort_order": row.sort_order,
                "grade_level_id": row.grade_level_id,
                "branch_campus_id": row.branch_campus_id,
            }
            for row in class_sections
        ],
        "subjects": [
            {"id": row.id, "name": row.name, "name_ar": row.name_ar, "status": row.status, "sort_order": row.sort_order}
            for row in subjects
        ],
        "categories": [
            {"id": row.id, "label": row.label, "type": row.type, "points_value": row.points_value}
            for row in categories
        ],
        "staff": [
            {"id": user.id, "name": user.name, "name_ar": user.name_ar, "role": staff_membership.role}
            for staff_membership, user in staff_rows
        ],
    }


@router.get("/reports/behaviour/students/search")
def search_report_students(
    search: str = Query(min_length=1, max_length=120),
    class_section_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=20, ge=1, le=20),
    membership: Membership = Depends(require_school_role(*REPORTING_ROLES)),
    db: Session = Depends(get_db),
):
    term = search.strip()
    if not term:
        return []
    school_id = membership.school_id
    normalized = term.casefold()
    exact_identifier = or_(
        cast(Student.id, String) == term,
        func.lower(func.trim(func.coalesce(Student.external_ref, ""))) == normalized,
    )
    name_match = or_(
        func.coalesce(Student.first_name, "").ilike(f"%{term}%"),
        func.coalesce(Student.last_name, "").ilike(f"%{term}%"),
        func.coalesce(Student.preferred_name, "").ilike(f"%{term}%"),
        func.coalesce(Student.name_ar, "").ilike(f"%{term}%"),
    )
    query = db.query(Student).filter(Student.school_id == school_id, Student.status == "active")
    query = query.filter(exact_identifier if len(term) < 2 else or_(exact_identifier, name_match))
    if class_section_id is not None:
        _require_school_row(db, ClassSection, class_section_id, school_id, "class_section_id")
        query = query.filter(
            exists().where(
                and_(
                    Enrolment.school_id == school_id,
                    Enrolment.student_id == Student.id,
                    Enrolment.class_section_id == class_section_id,
                    Enrolment.kind == "member",
                    Enrolment.valid_from <= date.today(),
                    or_(Enrolment.valid_to.is_(None), Enrolment.valid_to > date.today()),
                )
            )
        )
    scoped_user_ids = _scoped_actor_user_ids(db, membership)
    if scoped_user_ids is not None:
        query = query.filter(
            exists().where(
                and_(
                    BehaviourEvent.school_id == school_id,
                    BehaviourEvent.student_id == Student.id,
                    BehaviourEvent.actor_user_id.in_(scoped_user_ids),
                )
            )
        )
    students = query.order_by(func.lower(Student.last_name), func.lower(Student.first_name), Student.id).limit(limit).all()
    student_ids = {row.id for row in students}
    current_enrolments = (
        db.query(Enrolment, ClassSection)
        .join(ClassSection, ClassSection.id == Enrolment.class_section_id)
        .filter(
            Enrolment.school_id == school_id,
            Enrolment.student_id.in_(student_ids),
            Enrolment.kind == "member",
            Enrolment.valid_from <= date.today(),
            or_(Enrolment.valid_to.is_(None), Enrolment.valid_to > date.today()),
            ClassSection.school_id == school_id,
        )
        .order_by(Enrolment.valid_from.desc(), Enrolment.id.desc())
        .all()
        if student_ids
        else []
    )
    class_by_student: dict[int, ClassSection] = {}
    for enrolment, section in current_enrolments:
        class_by_student.setdefault(enrolment.student_id, section)
    return [
        {
            "id": row.id,
            "external_ref": row.external_ref,
            "display_name": _display_student(row),
            "name_ar": row.name_ar,
            "current_class_section": (
                {
                    "id": class_by_student[row.id].id,
                    "name": class_by_student[row.id].name,
                    "name_ar": class_by_student[row.id].name_ar,
                    "grade_level_id": class_by_student[row.id].grade_level_id,
                }
                if row.id in class_by_student
                else None
            ),
        }
        for row in students
    ]


@router.get("/reports/behaviour/overview")
def overview(date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None, category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None, membership: Membership = Depends(require_school_role(*REPORTING_ROLES)), db: Session = Depends(get_db)):
    filters = _filters(db, membership, **_report_params(date_from, date_to, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type))
    row = _query(db, membership, filters).with_entities(*_measures(), func.count(func.distinct(BehaviourEvent.actor_user_id)).label("active_teachers")).one()
    metrics = _metric_payload(row); metrics["active_teachers"] = int(row.active_teachers or 0)
    metrics["positive_ratio"] = round(metrics["positive_count"] / metrics["total_events"], 4) if metrics["total_events"] else 0
    return {"filters": filters.payload(), "metrics": metrics}


def _report_params(
    date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None,
    class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None,
    category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None,
):
    return locals()


@router.get("/reports/behaviour/trends")
def trends(date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None, category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None, membership: Membership = Depends(require_school_role(*REPORTING_ROLES)), db: Session = Depends(get_db)):
    filters = _filters(db, membership, **_report_params(date_from, date_to, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type))
    local_day = _local_day_expr(db, filters.school_timezone)
    rows = _query(db, membership, filters).with_entities(local_day.label("day"), *_measures()).group_by(local_day).order_by(local_day).all()
    return {"filters": filters.payload(), "interval": "day", "series": [{"date": str(row.day), **_metric_payload(row)} for row in rows]}


def _grouped(query, label_expr, key_expr=None, *, limit: int = 100):
    columns = [label_expr.label("label")]
    if key_expr is not None: columns.append(key_expr.label("dimension_key"))
    rows = query.with_entities(*columns, *_measures()).group_by(*columns).order_by(func.count(BehaviourEvent.id).desc(), label_expr.asc()).limit(limit).all()
    return [{"label": row.label or "Unattributed", **_metric_payload(row)} for row in rows]


@router.get("/reports/behaviour/breakdowns")
def breakdowns(date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None, category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None, membership: Membership = Depends(require_school_role(*REPORTING_ROLES)), db: Session = Depends(get_db)):
    filters = _filters(db, membership, **_report_params(date_from, date_to, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type))
    base = _query(db, membership, filters); dims = base._report_aliases
    class_name = func.coalesce(dims["direct_section"].name, dims["group_section"].name, dims["historic_section"].name)
    grade_name = func.coalesce(dims["grade"].name, dims["group_grade"].name, dims["historic_grade"].name)
    class_key = func.coalesce(BehaviourEvent.class_section_id, dims["group"].class_section_id, dims["historic_section"].id)
    grade_key = func.coalesce(dims["grade"].id, dims["group_grade"].id, dims["historic_grade"].id)
    classes = base.filter(BehaviourEvent.context_type == "class").with_entities(class_key.label("dimension_key"), class_name.label("label"), *_measures()).group_by(class_key, class_name).order_by(func.count(BehaviourEvent.id).desc(), class_name.asc(), class_key.asc()).all()
    grades = base.filter(BehaviourEvent.context_type.in_(("class", "subject"))).with_entities(grade_key.label("dimension_key"), grade_name.label("label"), *_measures()).group_by(grade_key, grade_name).order_by(func.count(BehaviourEvent.id).desc(), grade_name.asc(), grade_key.asc()).all()
    subjects = base.filter(BehaviourEvent.context_type == "subject").with_entities(dims["subject"].id.label("dimension_key"), dims["subject"].name.label("label"), *_measures()).group_by(dims["subject"].id, dims["subject"].name).order_by(func.count(BehaviourEvent.id).desc(), dims["subject"].name.asc(), dims["subject"].id.asc()).all()
    duties = base.filter(BehaviourEvent.context_type == "duty").with_entities(BehaviourEvent.duty_context.label("dimension_key"), BehaviourEvent.duty_context.label("label"), *_measures()).group_by(BehaviourEvent.duty_context).order_by(func.count(BehaviourEvent.id).desc(), BehaviourEvent.duty_context.asc()).all()
    categories = base.with_entities(BehaviourCategory.id.label("dimension_key"), BehaviourCategory.label.label("label"), BehaviourCategory.type.label("category_type"), *_measures()).group_by(BehaviourCategory.id, BehaviourCategory.label, BehaviourCategory.type).order_by(func.count(BehaviourEvent.id).desc(), BehaviourCategory.label.asc(), BehaviourCategory.id.asc()).all()
    pack = lambda rows: [{"label": row.label or "Unattributed", "dimension_key": row.dimension_key, **_metric_payload(row)} for row in rows]
    return {"filters": filters.payload(), "classes": pack(classes), "grades": pack(grades), "subjects": pack(subjects), "duty_contexts": pack(duties), "categories": [{**item, "category_type": row.category_type} for item, row in zip(pack(categories), categories)]}


def _student_rows(query, type_value: str, limit: int = 20):
    type_count = func.sum(case((BehaviourCategory.type == type_value, 1), else_=0))
    rows = query.filter(BehaviourCategory.type == type_value).with_entities(Student.id.label("dimension_key"), Student.first_name, Student.last_name, Student.preferred_name, *_measures()).group_by(Student.id, Student.first_name, Student.last_name, Student.preferred_name).order_by(type_count.desc(), Student.last_name.asc(), Student.first_name.asc(), Student.id.asc()).limit(limit).all()
    return [{"display_name": row.preferred_name or f"{row.first_name} {row.last_name}".strip(), "dimension_key": row.dimension_key, **_metric_payload(row)} for row in rows]


@router.get("/reports/behaviour/students")
def students(date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None, category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None, membership: Membership = Depends(require_school_role(*REPORTING_ROLES)), db: Session = Depends(get_db)):
    filters = _filters(db, membership, **_report_params(date_from, date_to, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type))
    base = _query(db, membership, filters)
    previous_start = filters.date_from - timedelta(days=(filters.date_to - filters.date_from).days + 1)
    previous = replace(filters, date_from=previous_start, date_to=filters.date_from - timedelta(days=1), start=filters.start - timedelta(days=(filters.date_to - filters.date_from).days + 1), end=filters.start)
    current_signed = base.with_entities(BehaviourEvent.student_id.label("student_id"), func.sum(BehaviourEvent.points_delta).label("current_total")).group_by(BehaviourEvent.student_id).subquery()
    prior_signed = _query(db, membership, previous).with_entities(BehaviourEvent.student_id.label("student_id"), func.sum(BehaviourEvent.points_delta).label("prior_total")).group_by(BehaviourEvent.student_id).subquery()
    changes = db.query(Student.id.label("dimension_key"), Student.first_name, Student.last_name, Student.preferred_name, current_signed.c.current_total, func.coalesce(prior_signed.c.prior_total, 0).label("prior_total")).join(current_signed, current_signed.c.student_id == Student.id).outerjoin(prior_signed, prior_signed.c.student_id == Student.id).order_by((current_signed.c.current_total - func.coalesce(prior_signed.c.prior_total, 0)).desc()).limit(20).all()
    improving = [{"display_name": r.preferred_name or f"{r.first_name} {r.last_name}".strip(), "dimension_key": r.dimension_key, "signed_points_change": int(r.current_total - r.prior_total)} for r in changes if r.current_total > r.prior_total]
    worsening = [{"display_name": r.preferred_name or f"{r.first_name} {r.last_name}".strip(), "dimension_key": r.dimension_key, "signed_points_change": int(r.current_total - r.prior_total)} for r in reversed(changes) if r.current_total < r.prior_total]
    return {"filters": filters.payload(), "comparison_period": {"date_from": previous.date_from.isoformat(), "date_to": previous.date_to.isoformat()}, "repeated_needs_work": _student_rows(base, "needs_work"), "top_positive": _student_rows(base, "positive"), "improving": improving[:20], "worsening": worsening[:20]}


@router.get("/reports/behaviour/teachers")
def teachers(date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None, category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None, membership: Membership = Depends(require_school_role(*REPORTING_ROLES)), db: Session = Depends(get_db)):
    filters = _filters(db, membership, **_report_params(date_from, date_to, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type))
    query = _query(db, membership, filters); actor = query._report_aliases["actor"]
    rows = query.with_entities(actor.id.label("dimension_key"), actor.name.label("display_name"), *_measures()).group_by(actor.id, actor.name).order_by(func.count(BehaviourEvent.id).desc(), actor.name.asc(), actor.id.asc()).limit(100).all()
    period_days = (filters.date_to - filters.date_from).days + 1
    previous = replace(
        filters,
        date_from=filters.date_from - timedelta(days=period_days),
        date_to=filters.date_from - timedelta(days=1),
        start=filters.start - timedelta(days=period_days),
        end=filters.start,
    )
    prior_query = _query(db, membership, previous); prior_actor = prior_query._report_aliases["actor"]
    prior_rows = prior_query.with_entities(
        prior_actor.id.label("dimension_key"), *_measures()
    ).group_by(prior_actor.id).all()
    prior_by_actor = {row.dimension_key: _metric_payload(row) for row in prior_rows}
    indicator_available = filters.category_id is None and filters.category_type is None
    teacher_rows = []
    for row in rows:
        current = _metric_payload(row)
        prior = prior_by_actor.get(row.dimension_key, {
            "total_events": 0,
            "positive_count": 0,
            "needs_work_count": 0,
            "signed_points_total": 0,
            "active_students": 0,
        })
        current_total = current["total_events"]
        prior_total = prior["total_events"]
        current_needs_work_ratio = current["needs_work_count"] / current_total if current_total else 0.0
        prior_needs_work_ratio = prior["needs_work_count"] / prior_total if prior_total else 0.0
        sample_sufficient = (
            indicator_available
            and current_total >= STAFF_REVIEW_CURRENT_MIN_EVENTS
            and prior_total >= STAFF_REVIEW_PRIOR_MIN_EVENTS
        )
        teacher_rows.append({
            "display_name": row.display_name or "Staff member",
            "dimension_key": row.dimension_key,
            **current,
            "previous_total_events": prior_total,
            "total_events_change": current_total - prior_total,
            "current_needs_work_ratio": round(current_needs_work_ratio, 4),
            "previous_needs_work_ratio": round(prior_needs_work_ratio, 4),
            "needs_work_ratio_change": round(current_needs_work_ratio - prior_needs_work_ratio, 4),
            "sample_sufficient": sample_sufficient,
            "supportive_review": bool(
                sample_sufficient
                and current_needs_work_ratio - prior_needs_work_ratio >= STAFF_REVIEW_NEEDS_WORK_RATIO_DELTA
            ),
        })
    return {
        "filters": filters.payload(),
        "comparison_period": {"date_from": previous.date_from.isoformat(), "date_to": previous.date_to.isoformat()},
        "indicator": {
            "available": indicator_available,
            "current_min_events": STAFF_REVIEW_CURRENT_MIN_EVENTS,
            "prior_min_events": STAFF_REVIEW_PRIOR_MIN_EVENTS,
            "needs_work_ratio_delta": STAFF_REVIEW_NEEDS_WORK_RATIO_DELTA,
        },
        "teachers": teacher_rows,
    }


def _matrix_dimension(name: str, dims: dict, local_day):
    if name not in MATRIX_DIMENSIONS:
        raise HTTPException(422, "Unknown matrix dimension")
    # Fixed, explicit mappings prevent arbitrary SQL or relationship traversal.
    if name == "student": return Student.id, func.coalesce(Student.preferred_name, Student.first_name)
    if name == "teacher": return BehaviourEvent.actor_user_id, func.coalesce(dims["actor"].name, "Staff member")
    if name == "category": return BehaviourCategory.id, BehaviourCategory.label
    if name == "category_type": return BehaviourCategory.type, BehaviourCategory.type
    if name == "duty_context": return BehaviourEvent.duty_context, func.coalesce(BehaviourEvent.duty_context, "Not duty")
    if name == "date_bucket": return local_day, local_day
    if name == "subject_group": return BehaviourEvent.subject_group_id, func.coalesce(dims["group"].name, "Unattributed")
    if name == "subject": return dims["subject"].id, func.coalesce(dims["subject"].name, "Unattributed")
    if name == "class_section":
        return func.coalesce(BehaviourEvent.class_section_id, dims["group"].class_section_id, dims["historic_section"].id), func.coalesce(dims["direct_section"].name, dims["group_section"].name, dims["historic_section"].name, "Unattributed")
    return func.coalesce(dims["grade"].id, dims["group_grade"].id, dims["historic_grade"].id), func.coalesce(dims["grade"].name, dims["group_grade"].name, dims["historic_grade"].name, "Unattributed")


def _validate_matrix_dimensions(row_dimension: str, column_dimension: str | None) -> None:
    if row_dimension not in MATRIX_DIMENSIONS or (column_dimension is not None and column_dimension not in MATRIX_DIMENSIONS):
        raise HTTPException(400, "Unknown matrix dimension")
    if column_dimension == row_dimension:
        raise HTTPException(400, "Matrix dimensions must differ")
    if column_dimension is not None and frozenset((row_dimension, column_dimension)) in INCOMPATIBLE_MATRIX_PAIRS:
        raise HTTPException(400, f"Incompatible matrix dimensions: {row_dimension} and {column_dimension}")


def _selected_values(expression, values: list):
    non_null = [value for value in values if value is not None]
    clauses = []
    if non_null:
        clauses.append(expression.in_(non_null))
    if len(non_null) != len(values):
        clauses.append(expression.is_(None))
    return or_(*clauses)


@router.get("/reports/behaviour/matrix")
def matrix(row_dimension: str, column_dimension: str | None = None, limit: int = Query(default=25, ge=1, le=MAX_MATRIX_ROWS), order_by: str = "total_events", date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None, category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None, membership: Membership = Depends(require_school_role(*REPORTING_ROLES)), db: Session = Depends(get_db)):
    _validate_matrix_dimensions(row_dimension, column_dimension)
    if order_by not in MATRIX_ORDER_BY: raise HTTPException(400, "Invalid matrix order_by")
    filters = _filters(db, membership, **_report_params(date_from, date_to, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type))
    base = _query(db, membership, filters)
    dims = base._report_aliases
    selected_dimensions = {row_dimension, column_dimension}
    if selected_dimensions & {"subject", "subject_group"}:
        base = base.filter(BehaviourEvent.context_type == "subject")
    if "duty_context" in selected_dimensions:
        base = base.filter(BehaviourEvent.context_type == "duty")
    local_day = _local_day_expr(db, filters.school_timezone)
    row_key, row_label = _matrix_dimension(row_dimension, dims, local_day)
    order_expr = {"total_events": func.count(BehaviourEvent.id), "positive_count": func.sum(case((BehaviourCategory.type == "positive", 1), else_=0)), "needs_work_count": func.sum(case((BehaviourCategory.type == "needs_work", 1), else_=0)), "signed_points_total": func.sum(BehaviourEvent.points_delta)}[order_by]
    if column_dimension is None:
        results = base.with_entities(row_key.label("row_key"), row_label.label("row_label"), *_measures()).group_by(row_key, row_label).order_by(order_expr.desc(), row_label.asc()).limit(limit + 1).all()
        rows_truncated = len(results) > limit
        results = results[:limit]
        return {"filters": filters.payload(), "row_dimension": row_dimension, "column_dimension": None, "measures": sorted(MATRIX_ORDER_BY) + ["active_students"], "rows": [{"label": r.row_label or "Unattributed", "dimension_key": r.row_key, **_metric_payload(r)} for r in results], "truncation": {"row_limit": limit, "rows_truncated": rows_truncated, "columns_truncated": False, "max_cells": MAX_MATRIX_CELLS, "returned_rows": len(results), "returned_cells": 0}}

    col_key, col_label = _matrix_dimension(column_dimension, dims, local_day)
    top_rows = base.with_entities(row_key.label("row_key"), row_label.label("row_label"), *_measures()).group_by(row_key, row_label).order_by(order_expr.desc(), row_label.asc()).limit(limit + 1).all()
    rows_truncated = len(top_rows) > limit
    top_rows = top_rows[:limit]
    row_values = [row.row_key for row in top_rows]
    if not row_values:
        return {"filters": filters.payload(), "row_dimension": row_dimension, "column_dimension": column_dimension, "measures": sorted(MATRIX_ORDER_BY) + ["active_students"], "rows": [], "truncation": {"row_limit": limit, "column_limit": 0, "rows_truncated": False, "columns_truncated": False, "max_cells": MAX_MATRIX_CELLS, "returned_rows": 0, "returned_cells": 0}}

    selected_base = base.filter(_selected_values(row_key, row_values))
    column_limit = max(1, MAX_MATRIX_CELLS // len(top_rows))
    top_columns = selected_base.with_entities(col_key.label("column_key"), col_label.label("column_label"), *_measures()).group_by(col_key, col_label).order_by(order_expr.desc(), col_label.asc()).limit(column_limit + 1).all()
    columns_truncated = len(top_columns) > column_limit
    top_columns = top_columns[:column_limit]
    column_values = [column.column_key for column in top_columns]
    cells = selected_base.filter(_selected_values(col_key, column_values)).with_entities(row_key.label("row_key"), col_key.label("column_key"), *_measures()).group_by(row_key, col_key).all() if column_values else []
    cell_map = {(cell.row_key, cell.column_key): _metric_payload(cell) for cell in cells}
    rows = []
    for row in top_rows:
        row_cells = []
        for column in top_columns:
            metrics = cell_map.get((row.row_key, column.column_key))
            if metrics is not None:
                row_cells.append({"label": column.column_label or "Unattributed", "dimension_key": column.column_key, **metrics})
        rows.append({"label": row.row_label or "Unattributed", "dimension_key": row.row_key, "cells": row_cells})
    return {"filters": filters.payload(), "row_dimension": row_dimension, "column_dimension": column_dimension, "measures": sorted(MATRIX_ORDER_BY) + ["active_students"], "rows": rows, "truncation": {"row_limit": limit, "column_limit": column_limit, "rows_truncated": rows_truncated, "columns_truncated": columns_truncated, "max_cells": MAX_MATRIX_CELLS, "returned_rows": len(rows), "returned_cells": len(cells)}}


@router.get("/reports/behaviour/events")
def events(offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100), date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None, category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None, membership: Membership = Depends(require_school_role(*REPORTING_ROLES)), db: Session = Depends(get_db)):
    filters = _filters(db, membership, **_report_params(date_from, date_to, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type))
    query = _query(db, membership, filters)
    total = query.with_entities(func.count(func.distinct(BehaviourEvent.id))).scalar() or 0
    rows = query.order_by(BehaviourEvent.created_at.desc(), BehaviourEvent.id.desc()).offset(offset).limit(limit).all()
    events_payload = []
    for event, category, student, actor, section, group, subject, *_ in rows:
        events_payload.append({"id": event.id, "created_at": event.created_at, "student_display_name": _display_student(student), "staff_display_name": actor.name if actor else None, "category_label": category.label, "category_type": category.type, "points_delta": event.points_delta, "context_type": event.context_type, "class_section_name": section.name if section else None, "subject_name": subject.name if subject else None, "duty_context": event.duty_context})
    return {"filters": filters.payload(), "pagination": {"limit": limit, "offset": offset, "total": int(total)}, "events": events_payload}


def _export_query(
    date_from: date | None = None,
    date_to: date | None = None,
    branch_campus_id: int | None = None,
    grade_level_id: int | None = None,
    class_section_id: int | None = None,
    subject_id: int | None = None,
    subject_group_id: int | None = None,
    duty_context: str | None = None,
    category_id: int | None = None,
    actor_user_id: int | None = None,
    student_id: int | None = None,
    category_type: Literal["positive", "needs_work"] | None = None,
) -> dict:
    return _report_params(
        date_from,
        date_to,
        branch_campus_id,
        grade_level_id,
        class_section_id,
        subject_id,
        subject_group_id,
        duty_context,
        category_id,
        actor_user_id,
        student_id,
        category_type,
    )


def _localized(value, language: str, *, primary: str = "name", arabic: str = "name_ar") -> str:
    if value is None:
        return ""
    return getattr(value, arabic, None) if language == "ar" and getattr(value, arabic, None) else getattr(value, primary, "")


def _export_filter_labels(db: Session, membership: Membership, params: dict, language: str) -> list[str]:
    school_id = membership.school_id
    lookups = (
        ("branch_campus_id", BranchCampus, "Branch", "الفرع"),
        ("grade_level_id", GradeLevel, "Grade", "الصف"),
        ("class_section_id", ClassSection, "Class", "الفصل"),
        ("subject_id", Subject, "Subject", "المادة"),
        ("subject_group_id", SubjectGroup, "Subject group", "مجموعة المادة"),
        ("category_id", BehaviourCategory, "Category", "الفئة"),
        ("student_id", Student, "Student", "الطالب"),
    )
    labels = []
    for key, model, english_label, arabic_label in lookups:
        value = params.get(key)
        if value is None:
            continue
        row = db.query(model).filter(model.id == value, model.school_id == school_id).first()
        if row is None:
            continue
        if model is Student:
            display = row.name_ar if language == "ar" and row.name_ar else _display_student(row)
        elif model is BehaviourCategory:
            display = row.label
        else:
            display = _localized(row, language)
        labels.append(f"{arabic_label if language == 'ar' else english_label}: {display}")
    if params.get("actor_user_id") is not None:
        user = db.query(User).filter(User.id == params["actor_user_id"]).first()
        if user:
            name = user.name_ar if language == "ar" and user.name_ar else user.name
            labels.append(f"{'الموظف' if language == 'ar' else 'Staff'}: {name}")
    if params.get("duty_context"):
        labels.append(f"{'سياق المناوبة' if language == 'ar' else 'Duty context'}: {params['duty_context']}")
    if params.get("category_type"):
        type_label = (
            "إيجابي" if params["category_type"] == "positive" else "يحتاج إلى تحسين"
        ) if language == "ar" else params["category_type"].replace("_", " ").title()
        labels.append(f"{'نوع الفئة' if language == 'ar' else 'Category type'}: {type_label}")
    return labels


def _export_bundle(
    db: Session,
    membership: Membership,
    *,
    params: dict,
    language: Literal["en", "ar"],
) -> dict:
    validated_filters = _filters(db, membership, **params)
    base = _query(db, membership, validated_filters)
    total = int(base.with_entities(func.count(func.distinct(BehaviourEvent.id))).scalar() or 0)
    if total > MAX_EXPORT_EVENTS:
        raise HTTPException(422, f"Export contains more than {MAX_EXPORT_EVENTS} matching events; narrow the filters")
    overview_payload = overview(**params, membership=membership, db=db)
    trends_payload = trends(**params, membership=membership, db=db)
    breakdown_payload = breakdowns(**params, membership=membership, db=db)
    event_payload = events(offset=0, limit=MAX_EXPORT_EVENTS, **params, membership=membership, db=db)
    school = db.query(School).filter(School.id == membership.school_id).one()
    context = report_context(membership=membership, db=db)
    if context["scope"]["type"] == "department":
        department_names = [
            row.get("name_ar") if language == "ar" and row.get("name_ar") else row["name"]
            for row in context["scope"]["departments"]
        ]
        scope_label = f"{'القسم' if language == 'ar' else 'Department'}: {', '.join(department_names)}"
    else:
        scope_label = "المدرسة" if language == "ar" else "School"
    return {
        "school_name": school.name,
        "school_name_ar": school.name_ar,
        "scope_label": scope_label,
        "filters": overview_payload["filters"],
        "filter_labels": _export_filter_labels(db, membership, params, language),
        "metrics": overview_payload["metrics"],
        "trends": trends_payload["series"],
        "breakdowns": breakdown_payload,
        "events": event_payload["events"],
        "event_total": total,
    }


def _render_export(bundle: dict, *, format: Literal["pdf", "csv"], language: Literal["en", "ar"]) -> tuple[bytes, str, str]:
    suffix = f"{bundle['filters']['date_from']}-to-{bundle['filters']['date_to']}"
    if format == "pdf":
        pdf_bundle = {**bundle, "events": bundle["events"][:200]}
        return render_behaviour_report_pdf(pdf_bundle, language), "application/pdf", f"behaviour-overview-{suffix}.pdf"
    return render_behaviour_report_csv(bundle, language), "text/csv", f"behaviour-events-{suffix}.csv"


def _audit_export(db: Session, membership: Membership, *, format: str, bundle: dict, action: str, entity) -> None:
    write_audit(
        db,
        membership.user_id,
        action,
        entity,
        {
            "format": format,
            "filters": bundle["filters"],
            "event_count": bundle["event_total"],
            "scope": "department" if membership.role == HEAD_OF_DEPARTMENT else "school",
        },
        school_id=membership.school_id,
    )


@router.get("/reports/behaviour/export.{format}")
def export_behaviour_report(
    format: Literal["pdf", "csv"],
    language: Literal["en", "ar"] = "en",
    params: dict = Depends(_export_query),
    membership: Membership = Depends(require_school_role(*REPORTING_ROLES)),
    db: Session = Depends(get_db),
):
    bundle = _export_bundle(db, membership, params=params, language=language)
    content, content_type, filename = _render_export(bundle, format=format, language=language)
    _audit_export(
        db,
        membership,
        format=format,
        bundle=bundle,
        action="reports.behaviour.exported",
        entity=("behaviour_reports", None),
    )
    db.commit()
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/reports/behaviour/generated-document", status_code=201)
def generate_behaviour_document(
    body: BehaviourDocumentRequest,
    membership: Membership = Depends(require_school_role(*REPORTING_ROLES)),
    db: Session = Depends(get_db),
):
    values = body.model_dump()
    format = values.pop("format")
    language = values.pop("language")
    bundle = _export_bundle(db, membership, params=values, language=language)
    content, content_type, filename = _render_export(bundle, format=format, language=language)
    try:
        row = create_generated_document(
            db,
            school_id=membership.school_id,
            membership_id=membership.id,
            document_type="behaviour_report",
            source_ref=f"behaviour:{bundle['filters']['date_from']}:{bundle['filters']['date_to']}",
            filename=filename,
            content_type=content_type,
            content=content,
        )
    except GeneratedDocumentValidationError as exc:
        db.rollback()
        raise HTTPException(422, str(exc))
    _audit_export(
        db,
        membership,
        format=format,
        bundle=bundle,
        action="reports.behaviour.generated_document.created",
        entity=row,
    )
    db.commit()
    db.refresh(row)
    return document_payload(row)

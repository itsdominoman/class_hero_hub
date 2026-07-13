from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from ..database import get_db
from ..models_school import (
    BehaviourCategory,
    BehaviourEvent,
    BranchCampus,
    ClassSection,
    Enrolment,
    GradeLevel,
    Membership,
    School,
    Student,
    Subject,
    SubjectGroup,
    User,
)
from ..school_scope import require_school_role


router = APIRouter(dependencies=[Depends(require_school_role("school_admin"))])

DUTY_CONTEXTS = {"break", "lunch", "playground", "hallway", "assembly", "bus", "general_duty"}
MATRIX_DIMENSIONS = {"student", "class_section", "grade", "subject", "subject_group", "teacher", "duty_context", "category", "category_type", "date_bucket"}
MATRIX_ORDER_BY = {"total_events", "positive_count", "needs_work_count", "signed_points_total"}
MAX_RANGE_DAYS = 366
MAX_MATRIX_ROWS = 100
MAX_MATRIX_CELLS = 2_500
INCOMPATIBLE_MATRIX_PAIRS = {
    frozenset(("subject", "duty_context")),
    frozenset(("subject_group", "duty_context")),
}


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
    if actor_user_id is not None and not db.query(BehaviourEvent.id).filter(BehaviourEvent.school_id == membership.school_id, BehaviourEvent.actor_user_id == actor_user_id).first():
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


def _query(db: Session, school_id: int, filters: ReportFilters):
    """Return one event-time query with only bounded, school-scoped rows."""
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


@router.get("/reports/behaviour/overview")
def overview(date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None, category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    filters = _filters(db, membership, **_report_params(date_from, date_to, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type))
    row = _query(db, membership.school_id, filters).with_entities(*_measures(), func.count(func.distinct(BehaviourEvent.actor_user_id)).label("active_teachers")).one()
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
def trends(date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None, category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    filters = _filters(db, membership, **_report_params(date_from, date_to, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type))
    local_day = _local_day_expr(db, filters.school_timezone)
    rows = _query(db, membership.school_id, filters).with_entities(local_day.label("day"), *_measures()).group_by(local_day).order_by(local_day).all()
    return {"filters": filters.payload(), "interval": "day", "series": [{"date": str(row.day), **_metric_payload(row)} for row in rows]}


def _grouped(query, label_expr, key_expr=None, *, limit: int = 100):
    columns = [label_expr.label("label")]
    if key_expr is not None: columns.append(key_expr.label("dimension_key"))
    rows = query.with_entities(*columns, *_measures()).group_by(*columns).order_by(func.count(BehaviourEvent.id).desc(), label_expr.asc()).limit(limit).all()
    return [{"label": row.label or "Unattributed", **_metric_payload(row)} for row in rows]


@router.get("/reports/behaviour/breakdowns")
def breakdowns(date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None, category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    filters = _filters(db, membership, **_report_params(date_from, date_to, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type))
    base = _query(db, membership.school_id, filters); dims = base._report_aliases
    class_name = func.coalesce(dims["direct_section"].name, dims["group_section"].name, dims["historic_section"].name)
    grade_name = func.coalesce(dims["grade"].name, dims["group_grade"].name, dims["historic_grade"].name)
    classes = base.filter(BehaviourEvent.context_type == "class").with_entities(class_name.label("label"), *_measures()).group_by(class_name).order_by(func.count(BehaviourEvent.id).desc()).all()
    grades = base.filter(BehaviourEvent.context_type.in_(("class", "subject"))).with_entities(grade_name.label("label"), *_measures()).group_by(grade_name).all()
    subjects = base.filter(BehaviourEvent.context_type == "subject").with_entities(dims["subject"].name.label("label"), *_measures()).group_by(dims["subject"].name).all()
    duties = base.filter(BehaviourEvent.context_type == "duty").with_entities(BehaviourEvent.duty_context.label("label"), *_measures()).group_by(BehaviourEvent.duty_context).all()
    categories = base.with_entities(BehaviourCategory.label.label("label"), *_measures()).group_by(BehaviourCategory.label).all()
    pack = lambda rows: [{"label": row.label or "Unattributed", **_metric_payload(row)} for row in rows]
    return {"filters": filters.payload(), "classes": pack(classes), "grades": pack(grades), "subjects": pack(subjects), "duty_contexts": pack(duties), "categories": pack(categories)}


def _student_rows(query, type_value: str, limit: int = 20):
    rows = query.filter(BehaviourCategory.type == type_value).with_entities(Student.first_name, Student.last_name, Student.preferred_name, *_measures()).group_by(Student.id, Student.first_name, Student.last_name, Student.preferred_name).order_by(func.count(BehaviourEvent.id).desc()).limit(limit).all()
    return [{"display_name": row.preferred_name or f"{row.first_name} {row.last_name}".strip(), **_metric_payload(row)} for row in rows]


@router.get("/reports/behaviour/students")
def students(date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None, category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    filters = _filters(db, membership, **_report_params(date_from, date_to, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type))
    base = _query(db, membership.school_id, filters)
    previous_start = filters.date_from - timedelta(days=(filters.date_to - filters.date_from).days + 1)
    previous = replace(filters, date_from=previous_start, date_to=filters.date_from - timedelta(days=1), start=filters.start - timedelta(days=(filters.date_to - filters.date_from).days + 1), end=filters.start)
    current_signed = base.with_entities(BehaviourEvent.student_id.label("student_id"), func.sum(BehaviourEvent.points_delta).label("current_total")).group_by(BehaviourEvent.student_id).subquery()
    prior_signed = _query(db, membership.school_id, previous).with_entities(BehaviourEvent.student_id.label("student_id"), func.sum(BehaviourEvent.points_delta).label("prior_total")).group_by(BehaviourEvent.student_id).subquery()
    changes = db.query(Student.first_name, Student.last_name, Student.preferred_name, current_signed.c.current_total, func.coalesce(prior_signed.c.prior_total, 0).label("prior_total")).join(current_signed, current_signed.c.student_id == Student.id).outerjoin(prior_signed, prior_signed.c.student_id == Student.id).order_by((current_signed.c.current_total - func.coalesce(prior_signed.c.prior_total, 0)).desc()).limit(20).all()
    improving = [{"display_name": r.preferred_name or f"{r.first_name} {r.last_name}".strip(), "signed_points_change": int(r.current_total - r.prior_total)} for r in changes if r.current_total > r.prior_total]
    worsening = [{"display_name": r.preferred_name or f"{r.first_name} {r.last_name}".strip(), "signed_points_change": int(r.current_total - r.prior_total)} for r in reversed(changes) if r.current_total < r.prior_total]
    return {"filters": filters.payload(), "comparison_period": {"date_from": previous.date_from.isoformat(), "date_to": previous.date_to.isoformat()}, "repeated_needs_work": _student_rows(base, "needs_work"), "top_positive": _student_rows(base, "positive"), "improving": improving[:20], "worsening": worsening[:20]}


@router.get("/reports/behaviour/teachers")
def teachers(date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None, category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    filters = _filters(db, membership, **_report_params(date_from, date_to, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type))
    query = _query(db, membership.school_id, filters); actor = query._report_aliases["actor"]
    rows = query.with_entities(actor.name.label("display_name"), *_measures()).group_by(actor.id, actor.name).order_by(func.count(BehaviourEvent.id).desc()).limit(100).all()
    return {"filters": filters.payload(), "teachers": [{"display_name": row.display_name or "Staff member", **_metric_payload(row)} for row in rows]}


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
def matrix(row_dimension: str, column_dimension: str | None = None, limit: int = Query(default=25, ge=1, le=MAX_MATRIX_ROWS), order_by: str = "total_events", date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None, category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    _validate_matrix_dimensions(row_dimension, column_dimension)
    if order_by not in MATRIX_ORDER_BY: raise HTTPException(400, "Invalid matrix order_by")
    filters = _filters(db, membership, **_report_params(date_from, date_to, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type))
    base = _query(db, membership.school_id, filters)
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
        return {"filters": filters.payload(), "row_dimension": row_dimension, "column_dimension": None, "measures": sorted(MATRIX_ORDER_BY) + ["active_students"], "rows": [{"label": r.row_label or "Unattributed", **_metric_payload(r)} for r in results], "truncation": {"row_limit": limit, "rows_truncated": rows_truncated, "columns_truncated": False, "max_cells": MAX_MATRIX_CELLS, "returned_rows": len(results), "returned_cells": 0}}

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
                row_cells.append({"label": column.column_label or "Unattributed", **metrics})
        rows.append({"label": row.row_label or "Unattributed", "cells": row_cells})
    return {"filters": filters.payload(), "row_dimension": row_dimension, "column_dimension": column_dimension, "measures": sorted(MATRIX_ORDER_BY) + ["active_students"], "rows": rows, "truncation": {"row_limit": limit, "column_limit": column_limit, "rows_truncated": rows_truncated, "columns_truncated": columns_truncated, "max_cells": MAX_MATRIX_CELLS, "returned_rows": len(rows), "returned_cells": len(cells)}}


@router.get("/reports/behaviour/events")
def events(offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100), date_from: date | None = None, date_to: date | None = None, branch_campus_id: int | None = None, grade_level_id: int | None = None, class_section_id: int | None = None, subject_id: int | None = None, subject_group_id: int | None = None, duty_context: str | None = None, category_id: int | None = None, actor_user_id: int | None = None, student_id: int | None = None, category_type: str | None = None, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    filters = _filters(db, membership, **_report_params(date_from, date_to, branch_campus_id, grade_level_id, class_section_id, subject_id, subject_group_id, duty_context, category_id, actor_user_id, student_id, category_type))
    query = _query(db, membership.school_id, filters)
    total = query.with_entities(func.count(func.distinct(BehaviourEvent.id))).scalar() or 0
    rows = query.order_by(BehaviourEvent.created_at.desc(), BehaviourEvent.id.desc()).offset(offset).limit(limit).all()
    events_payload = []
    for event, category, student, actor, section, group, subject, *_ in rows:
        events_payload.append({"id": event.id, "created_at": event.created_at, "student_display_name": _display_student(student), "staff_display_name": actor.name if actor else None, "category_label": category.label, "category_type": category.type, "points_delta": event.points_delta, "context_type": event.context_type, "class_section_name": section.name if section else None, "subject_name": subject.name if subject else None, "duty_context": event.duty_context})
    return {"filters": filters.payload(), "pagination": {"limit": limit, "offset": offset, "total": int(total)}, "events": events_payload}

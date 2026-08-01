from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .models_school import (
    BehaviourCategory,
    BehaviourEvent,
    BranchCampus,
    ClassSection,
    Enrolment,
    GradeLevel,
    School,
    Student,
    StudentRecognitionCandidate,
    StudentRecognitionCategory,
    StudentRecognitionConfig,
    StudentRecognitionReview,
    StudentRecognitionSafeguardCategory,
)


def school_period_bounds(school: School, period_start: date, period_end: date) -> tuple[datetime, datetime]:
    try:
        zone = ZoneInfo(school.timezone or "UTC")
    except Exception:
        zone = timezone.utc
    start = datetime.combine(period_start, time.min, tzinfo=zone).astimezone(timezone.utc)
    end = datetime.combine(period_end + timedelta(days=1), time.min, tzinfo=zone).astimezone(timezone.utc)
    return start, end


def scope_record(db: Session, school_id: int, scope_type: str, scope_ref_id: int):
    models = {"branch": BranchCampus, "grade": GradeLevel, "class": ClassSection}
    model = models.get(scope_type)
    if model is None:
        raise HTTPException(422, "Recognition scope must be branch, grade or class")
    row = db.query(model).filter(model.id == scope_ref_id, model.school_id == school_id).first()
    if not row or (row.status or "active") != "active":
        raise HTTPException(422, "Recognition scope must be an active structure in this school")
    return row


def positive_categories(db: Session, school_id: int, category_ids: list[int]) -> list[BehaviourCategory]:
    unique_ids = list(dict.fromkeys(category_ids))
    if not unique_ids:
        raise HTTPException(422, "Select at least one positive behaviour category")
    rows = (
        db.query(BehaviourCategory)
        .filter(BehaviourCategory.school_id == school_id, BehaviourCategory.id.in_(unique_ids))
        .all()
    )
    by_id = {row.id: row for row in rows}
    if len(by_id) != len(unique_ids) or any(row.type != "positive" or not row.active for row in rows):
        raise HTTPException(422, "Recognition categories must be active positive categories in this school")
    return [by_id[row_id] for row_id in unique_ids]


def selected_needs_work_categories(
    db: Session,
    school_id: int,
    category_ids: list[int],
) -> list[BehaviourCategory]:
    unique_ids = list(dict.fromkeys(category_ids))
    if not unique_ids:
        return []
    rows = (
        db.query(BehaviourCategory)
        .filter(BehaviourCategory.school_id == school_id, BehaviourCategory.id.in_(unique_ids))
        .all()
    )
    by_id = {row.id: row for row in rows}
    if len(by_id) != len(unique_ids) or any(row.type != "needs_work" or not row.active for row in rows):
        raise HTTPException(422, "Safeguard categories must be active needs-work categories in this school")
    return [by_id[row_id] for row_id in unique_ids]


def config_categories(db: Session, config_id: int) -> list[BehaviourCategory]:
    return (
        db.query(BehaviourCategory)
        .join(StudentRecognitionCategory, StudentRecognitionCategory.category_id == BehaviourCategory.id)
        .filter(StudentRecognitionCategory.config_id == config_id)
        .order_by(BehaviourCategory.sort_order, BehaviourCategory.id)
        .all()
    )


def safeguard_categories(db: Session, config_id: int) -> list[BehaviourCategory]:
    return (
        db.query(BehaviourCategory)
        .join(
            StudentRecognitionSafeguardCategory,
            StudentRecognitionSafeguardCategory.category_id == BehaviourCategory.id,
        )
        .filter(StudentRecognitionSafeguardCategory.config_id == config_id)
        .order_by(BehaviourCategory.sort_order, BehaviourCategory.id)
        .all()
    )


def scope_payload(db: Session, config: StudentRecognitionConfig) -> dict:
    model = {"branch": BranchCampus, "grade": GradeLevel, "class": ClassSection}[config.scope_type]
    row = db.query(model).filter(model.id == config.scope_ref_id, model.school_id == config.school_id).first()
    if not row:
        raise HTTPException(409, "Configured recognition scope no longer exists")
    return {
        "type": config.scope_type,
        "id": row.id,
        "name": row.name,
        "name_ar": row.name_ar,
    }


def config_payload(db: Session, config: StudentRecognitionConfig) -> dict:
    categories = config_categories(db, config.id)
    needs_work_categories = safeguard_categories(db, config.id)
    return {
        "id": config.id,
        "recognition_type": config.recognition_type,
        "name": config.name,
        "scope": scope_payload(db, config),
        "review_period_days": config.review_period_days,
        "category_ids": [row.id for row in categories],
        "categories": [{"id": row.id, "label": row.label, "points_value": row.points_value} for row in categories],
        "minimum_positive_points": config.minimum_positive_points,
        "shortlist_size": config.shortlist_size,
        "needs_work_safeguard_enabled": config.needs_work_safeguard_enabled,
        "maximum_needs_work_events": config.maximum_needs_work_events,
        "needs_work_category_ids": [row.id for row in needs_work_categories],
        "needs_work_categories": [{"id": row.id, "label": row.label} for row in needs_work_categories],
        "certificate_title": config.certificate_title,
        "signatory_text": config.signatory_text,
        "active": config.active,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


def candidate_payload(candidate: StudentRecognitionCandidate) -> dict:
    safeguard_overridden = candidate.safeguard_overridden_at is not None
    return {
        "id": candidate.id,
        "student_id": candidate.student_id,
        "student_name": candidate.student_name,
        "student_name_ar": candidate.student_name_ar,
        "branch_name": candidate.branch_name,
        "grade_name": candidate.grade_name,
        "class_name": candidate.class_name,
        "positive_points_total": candidate.positive_points_total,
        "positive_event_count": candidate.positive_event_count,
        "category_totals": candidate.category_totals,
        "rank": candidate.rank,
        "display_order": candidate.display_order,
        "is_excluded": candidate.is_excluded,
        "exclusion_reason": candidate.exclusion_reason,
        "excluded_at": candidate.excluded_at,
        "safeguard_excluded": candidate.safeguard_excluded,
        "safeguard_counted_total": candidate.safeguard_counted_total,
        "safeguard_category_totals": candidate.safeguard_category_totals,
        "safeguard_overridden": safeguard_overridden,
        "safeguard_override_reason": candidate.safeguard_override_reason,
        "safeguard_overridden_at": candidate.safeguard_overridden_at,
        "is_eligible": not candidate.is_excluded and (not candidate.safeguard_excluded or safeguard_overridden),
    }


def review_payload(db: Session, review: StudentRecognitionReview, *, include_candidates: bool = True) -> dict:
    payload = {
        "id": review.id,
        "config_id": review.config_id,
        "recognition_type": review.recognition_type,
        "scope_key": review.scope_key,
        "period_start": review.period_start,
        "period_end": review.period_end,
        "criteria": review.criteria_snapshot,
        "status": review.status,
        "selected_student_id": review.selected_student_id,
        "citation": review.citation,
        "generated_at": review.generated_at,
        "confirmed_at": review.confirmed_at,
        "revoked_at": review.revoked_at,
        "revocation_reason": review.revocation_reason,
    }
    if include_candidates:
        candidates = (
            db.query(StudentRecognitionCandidate)
            .filter(
                StudentRecognitionCandidate.school_id == review.school_id,
                StudentRecognitionCandidate.review_id == review.id,
            )
            .order_by(StudentRecognitionCandidate.display_order)
            .all()
        )
        payload["candidates"] = [candidate_payload(row) for row in candidates]
        selected = next((row for row in candidates if row.student_id == review.selected_student_id), None)
        payload["selected_candidate"] = candidate_payload(selected) if selected else None
    return payload


def _eligible_placements(db: Session, config: StudentRecognitionConfig, period_end: date) -> dict[int, tuple]:
    query = (
        db.query(Student, Enrolment, ClassSection, GradeLevel, BranchCampus)
        .join(Enrolment, Enrolment.student_id == Student.id)
        .join(ClassSection, ClassSection.id == Enrolment.class_section_id)
        .join(GradeLevel, GradeLevel.id == ClassSection.grade_level_id)
        .join(BranchCampus, BranchCampus.id == ClassSection.branch_campus_id)
        .filter(
            Student.school_id == config.school_id,
            Student.status == "active",
            Enrolment.school_id == config.school_id,
            Enrolment.kind == "member",
            Enrolment.valid_from <= period_end,
            or_(Enrolment.valid_to.is_(None), Enrolment.valid_to > period_end),
            ClassSection.school_id == config.school_id,
        )
    )
    if config.scope_type == "branch":
        query = query.filter(ClassSection.branch_campus_id == config.scope_ref_id)
    elif config.scope_type == "grade":
        query = query.filter(ClassSection.grade_level_id == config.scope_ref_id)
    else:
        query = query.filter(ClassSection.id == config.scope_ref_id)
    rows = query.order_by(Student.id, Enrolment.valid_from.desc(), Enrolment.id.desc()).all()
    placements: dict[int, tuple] = {}
    for student, enrolment, section, grade, branch in rows:
        placements.setdefault(student.id, (student, section, grade, branch))
    return placements


def generate_shortlist(
    db: Session,
    *,
    school: School,
    config: StudentRecognitionConfig,
    period_end: date,
    actor_user_id: int,
) -> StudentRecognitionReview:
    period_start = period_end - timedelta(days=config.review_period_days - 1)
    categories = config_categories(db, config.id)
    if not categories or any(row.type != "positive" for row in categories):
        raise HTTPException(422, "Recognition configuration has no valid positive categories")
    scope = scope_payload(db, config)
    category_ids = [row.id for row in categories]
    needs_work_categories = safeguard_categories(db, config.id)
    criteria = {
        "recognition_name": config.name,
        "scope": scope,
        "review_period_days": config.review_period_days,
        "minimum_positive_points": config.minimum_positive_points,
        "shortlist_size": config.shortlist_size,
        "categories": [{"id": row.id, "label": row.label} for row in categories],
        "ordering": "positive_points_desc_then_positive_events_desc",
        "tie_rule": "shared_rank_and_include_cutoff_ties",
        "needs_work_safeguard": {
            "enabled": config.needs_work_safeguard_enabled,
            "maximum_allowed_events": config.maximum_needs_work_events,
            "category_filter": "selected" if needs_work_categories else "all_needs_work",
            "categories": [{"id": row.id, "label": row.label} for row in needs_work_categories],
            "rule": "not_eligible_when_count_exceeds_maximum",
        },
        "certificate_title": config.certificate_title,
        "signatory_text": config.signatory_text,
    }
    review = StudentRecognitionReview(
        school_id=config.school_id,
        config_id=config.id,
        recognition_type=config.recognition_type,
        scope_key=config.scope_key,
        period_start=period_start,
        period_end=period_end,
        criteria_snapshot=criteria,
        generated_by_user_id=actor_user_id,
    )
    db.add(review)
    db.flush()

    placements = _eligible_placements(db, config, period_end)
    if not placements:
        return review
    start_at, end_at = school_period_bounds(school, period_start, period_end)
    rows = (
        db.query(
            BehaviourEvent.student_id,
            BehaviourCategory.id.label("category_id"),
            BehaviourCategory.label.label("category_label"),
            func.sum(BehaviourEvent.points_delta).label("points_total"),
            func.count(BehaviourEvent.id).label("event_count"),
        )
        .join(BehaviourCategory, BehaviourCategory.id == BehaviourEvent.category_id)
        .filter(
            BehaviourEvent.school_id == config.school_id,
            BehaviourEvent.student_id.in_(list(placements)),
            BehaviourEvent.category_id.in_(category_ids),
            BehaviourEvent.reversed_at.is_(None),
            BehaviourEvent.points_delta > 0,
            BehaviourEvent.created_at >= start_at,
            BehaviourEvent.created_at < end_at,
            BehaviourCategory.school_id == config.school_id,
            BehaviourCategory.type == "positive",
        )
        .group_by(BehaviourEvent.student_id, BehaviourCategory.id, BehaviourCategory.label)
        .all()
    )
    totals: dict[int, dict] = {}
    for row in rows:
        entry = totals.setdefault(row.student_id, {"points": 0, "events": 0, "categories": []})
        points = int(row.points_total or 0)
        events = int(row.event_count or 0)
        entry["points"] += points
        entry["events"] += events
        entry["categories"].append({"id": row.category_id, "label": row.category_label, "points": points, "events": events})
    ordered = [
        (student_id, values)
        for student_id, values in totals.items()
        if values["points"] >= config.minimum_positive_points and values["events"] > 0
    ]
    ordered.sort(key=lambda item: (-item[1]["points"], -item[1]["events"], item[0]))
    if len(ordered) > config.shortlist_size:
        cutoff = ordered[config.shortlist_size - 1][1]
        cutoff_key = (cutoff["points"], cutoff["events"])
        ordered = [item for item in ordered if (item[1]["points"], item[1]["events"]) >= cutoff_key]

    safeguard_totals: dict[int, dict] = {}
    if config.needs_work_safeguard_enabled and ordered:
        safeguarded_student_ids = [student_id for student_id, _ in ordered]
        safeguard_query = (
            db.query(
                BehaviourEvent.student_id,
                BehaviourCategory.id.label("category_id"),
                BehaviourCategory.label.label("category_label"),
                func.count(BehaviourEvent.id).label("event_count"),
            )
            .join(BehaviourCategory, BehaviourCategory.id == BehaviourEvent.category_id)
            .filter(
                BehaviourEvent.school_id == config.school_id,
                BehaviourEvent.student_id.in_(safeguarded_student_ids),
                BehaviourEvent.reversed_at.is_(None),
                BehaviourEvent.created_at >= start_at,
                BehaviourEvent.created_at < end_at,
                BehaviourCategory.school_id == config.school_id,
                BehaviourCategory.type == "needs_work",
            )
        )
        if needs_work_categories:
            safeguard_query = safeguard_query.filter(
                BehaviourEvent.category_id.in_([row.id for row in needs_work_categories])
            )
        safeguard_rows = safeguard_query.group_by(
            BehaviourEvent.student_id,
            BehaviourCategory.id,
            BehaviourCategory.label,
        ).all()
        for row in safeguard_rows:
            entry = safeguard_totals.setdefault(row.student_id, {"events": 0, "categories": []})
            events = int(row.event_count or 0)
            entry["events"] += events
            entry["categories"].append(
                {"id": row.category_id, "label": row.category_label, "events": events}
            )

    previous_score = None
    current_rank = 0
    for display_order, (student_id, values) in enumerate(ordered, 1):
        score = (values["points"], values["events"])
        if score != previous_score:
            current_rank = display_order
            previous_score = score
        student, section, grade, branch = placements[student_id]
        values["categories"].sort(key=lambda item: (-item["points"], -item["events"], item["label"], item["id"]))
        safeguard = safeguard_totals.get(student_id, {"events": 0, "categories": []})
        safeguard["categories"].sort(key=lambda item: (-item["events"], item["label"], item["id"]))
        db.add(
            StudentRecognitionCandidate(
                school_id=config.school_id,
                review_id=review.id,
                student_id=student.id,
                student_name=student.preferred_name or f"{student.first_name} {student.last_name}".strip(),
                student_name_ar=student.name_ar,
                branch_name=branch.name,
                grade_name=grade.name,
                class_name=section.name,
                positive_points_total=values["points"],
                positive_event_count=values["events"],
                category_totals=values["categories"],
                rank=current_rank,
                display_order=display_order,
                safeguard_excluded=(
                    config.needs_work_safeguard_enabled
                    and safeguard["events"] > config.maximum_needs_work_events
                ),
                safeguard_counted_total=safeguard["events"],
                safeguard_category_totals=safeguard["categories"],
            )
        )
    db.flush()
    return review

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .. import auth, invite_tokens
from ..database import get_db
from ..models_school import AcademicYear, BehaviourEvent, BranchCampus, ClassSection, Enrolment, GradeLevel, Membership, School, StaffAssignment, Student, Subject, SubjectGroup, User
from ..rosters import roster_payload
from ..school_scope import open_interval_expression, require_teacher_of
from ..student_avatars import avatar_urls, ensure_student_avatars

router = APIRouter()


def _row_ref(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "code": getattr(row, "code", None),
        "name": getattr(row, "name", None),
        "name_ar": getattr(row, "name_ar", None),
        "status": getattr(row, "status", None),
    }


def _assignment_cards(db: Session, assignments_with_school: list[tuple[StaffAssignment, School]]) -> list[dict[str, Any]]:
    """Build dashboard cards for many assignments using a fixed number of queries.

    Looks up every referenced class_section/subject_group/branch/year/grade_level/subject
    once via WHERE id IN (...), instead of querying per assignment.
    """
    section_ids = {a.class_section_id for a, _ in assignments_with_school if a.class_section_id is not None}
    group_ids = {a.subject_group_id for a, _ in assignments_with_school if a.subject_group_id is not None}

    groups_by_id = {g.id: g for g in (db.query(SubjectGroup).filter(SubjectGroup.id.in_(group_ids)).all() if group_ids else [])}
    section_ids |= {g.class_section_id for g in groups_by_id.values() if g.class_section_id is not None}
    sections_by_id = {s.id: s for s in (db.query(ClassSection).filter(ClassSection.id.in_(section_ids)).all() if section_ids else [])}

    branch_ids = {s.branch_campus_id for s in sections_by_id.values() if s.branch_campus_id is not None}
    year_ids = {s.academic_year_id for s in sections_by_id.values()} | {g.academic_year_id for g in groups_by_id.values()}
    level_ids = {s.grade_level_id for s in sections_by_id.values()} | {g.grade_level_id for g in groups_by_id.values() if g.grade_level_id is not None}
    subject_ids = {g.subject_id for g in groups_by_id.values()}

    branches_by_id = {b.id: b for b in (db.query(BranchCampus).filter(BranchCampus.id.in_(branch_ids)).all() if branch_ids else [])}
    years_by_id = {y.id: y for y in (db.query(AcademicYear).filter(AcademicYear.id.in_(year_ids)).all() if year_ids else [])}
    levels_by_id = {l.id: l for l in (db.query(GradeLevel).filter(GradeLevel.id.in_(level_ids)).all() if level_ids else [])}
    subjects_by_id = {s.id: s for s in (db.query(Subject).filter(Subject.id.in_(subject_ids)).all() if subject_ids else [])}

    cards = []
    for assignment, school in assignments_with_school:
        section = sections_by_id.get(assignment.class_section_id)
        group = groups_by_id.get(assignment.subject_group_id)
        branch = year = level = subject = None

        if section is not None:
            branch = branches_by_id.get(section.branch_campus_id)
            year = years_by_id.get(section.academic_year_id)
            level = levels_by_id.get(section.grade_level_id)

        if group is not None:
            subject = subjects_by_id.get(group.subject_id)
            year = years_by_id.get(group.academic_year_id)
            if group.class_section_id is not None:
                section = sections_by_id.get(group.class_section_id)
                if section is not None:
                    branch = branches_by_id.get(section.branch_campus_id)
                    level = levels_by_id.get(section.grade_level_id)
            elif group.grade_level_id is not None:
                level = levels_by_id.get(group.grade_level_id)

        cards.append(
            {
                "id": assignment.id,
                "role": assignment.role,
                "target_type": "subject_group" if assignment.subject_group_id is not None else "class_section",
                "valid_from": assignment.valid_from,
                "valid_to": assignment.valid_to,
                "school": {"id": school.id, "name": school.name, "name_ar": school.name_ar},
                "class_section": _row_ref(section),
                "subject_group": _row_ref(group),
                "branch": _row_ref(branch),
                "academic_year": _row_ref(year),
                "grade_level": _row_ref(level),
                "subject": _row_ref(subject),
            }
        )
    return cards


def _roster_payload(db: Session, school_id: int, *, class_section_id: int | None = None, subject_group_id: int | None = None) -> dict[str, Any]:
    if class_section_id is not None:
        section = db.query(ClassSection).filter(ClassSection.id == class_section_id, ClassSection.school_id == school_id).first()
        if not section:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roster target not found")
    else:
        group = db.query(SubjectGroup).filter(SubjectGroup.id == subject_group_id, SubjectGroup.school_id == school_id).first()
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roster target not found")
    return roster_payload(db, school_id, class_section_id=class_section_id, subject_group_id=subject_group_id, today=invite_tokens.now_utc().date())


@router.get("/dashboard")
def teacher_dashboard(
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    teacher_memberships = (
        db.query(Membership, School)
        .join(School, Membership.school_id == School.id)
        .filter(
            Membership.user_id == current_user.id,
            Membership.role == "teacher",
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            School.status != "suspended",
        )
        .all()
    )
    if not teacher_memberships:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher access required")

    today = invite_tokens.now_utc().date()
    assignments_with_school: list[tuple[StaffAssignment, School]] = []
    for membership, school in teacher_memberships:
        assignments = (
            db.query(StaffAssignment)
            .filter(
                StaffAssignment.school_id == school.id,
                StaffAssignment.membership_id == membership.id,
                *open_interval_expression(StaffAssignment, today),
            )
            .order_by(StaffAssignment.role.asc(), StaffAssignment.id.asc())
            .all()
        )
        assignments_with_school.extend((assignment, school) for assignment in assignments)

    return {
        "assignments": _assignment_cards(db, assignments_with_school),
        "schools": [{"id": school.id, "name": school.name, "name_ar": school.name_ar} for _membership, school in teacher_memberships],
    }


@router.get("/students/search")
def search_students(
    school_id: int,
    q: str = "",
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Search an active teacher's school without exposing the admin student record."""
    from ..behaviour_service import active_teacher_membership

    active_teacher_membership(db, current_user.id, school_id)
    term = q.strip()
    if len(term) < 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter at least 2 characters")

    pattern = f"%{term}%"
    students = (
        db.query(Student)
        .filter(
            Student.school_id == school_id,
            Student.status == "active",
            or_(
                Student.first_name.ilike(pattern),
                Student.last_name.ilike(pattern),
                Student.preferred_name.ilike(pattern),
                Student.external_ref.ilike(pattern),
            ),
        )
        .order_by(func.lower(Student.last_name).asc(), func.lower(Student.first_name).asc(), Student.id.asc())
        .limit(30)
        .all()
    )
    student_ids = [student.id for student in students]
    totals = (
        dict(
            db.query(BehaviourEvent.student_id, func.coalesce(func.sum(BehaviourEvent.points_delta), 0))
            .filter(
                BehaviourEvent.school_id == school_id,
                BehaviourEvent.student_id.in_(student_ids),
                BehaviourEvent.reversed_at.is_(None),
            )
            .group_by(BehaviourEvent.student_id)
            .all()
        )
        if student_ids else {}
    )
    enrolment_rows = (
        db.query(Enrolment.student_id, ClassSection, GradeLevel)
        .join(ClassSection, ClassSection.id == Enrolment.class_section_id)
        .join(GradeLevel, GradeLevel.id == ClassSection.grade_level_id)
        .filter(
            Enrolment.school_id == school_id,
            Enrolment.student_id.in_(student_ids),
            Enrolment.kind == "member",
            Enrolment.valid_from <= invite_tokens.now_utc().date(),
            or_(Enrolment.valid_to.is_(None), Enrolment.valid_to >= invite_tokens.now_utc().date()),
            ClassSection.status == "active",
        )
        .order_by(Enrolment.student_id.asc(), Enrolment.id.asc())
        .all()
        if student_ids else []
    )
    context_by_student = {}
    for student_id, section, grade in enrolment_rows:
        context_by_student.setdefault(student_id, {"class_section": section.name or section.code, "grade_level": grade.name})

    return {
        "students": [
            {
                "id": student.id,
                "display_name": student.preferred_name or f"{student.first_name} {student.last_name}".strip(),
                "first_name": student.first_name,
                "last_name": student.last_name,
                "preferred_name": student.preferred_name,
                "name_ar": student.name_ar,
                "points_total": int(totals.get(student.id, 0)),
                **avatar_urls(student.avatar_id),
                **context_by_student.get(student.id, {"class_section": None, "grade_level": None}),
            }
            for student in students
        ],
        "limit": 30,
    }


def _classroom_student_payload(row: dict[str, Any], avatar_id: int | None, points_total: int = 0) -> dict[str, Any]:
    return {
        "id": row["id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "preferred_name": row["preferred_name"],
        "display_name": row["display_name"],
        "name_ar": row["name_ar"],
        "points_total": points_total,
        **avatar_urls(avatar_id),
    }


@router.get("/assignments/{assignment_id}")
def teacher_class_detail(
    assignment_id: int,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    today = invite_tokens.now_utc().date()
    assignment_access = (
        db.query(StaffAssignment, Membership, School)
        .join(Membership, Membership.id == StaffAssignment.membership_id)
        .join(School, School.id == StaffAssignment.school_id)
        .filter(
            StaffAssignment.id == assignment_id,
            Membership.user_id == current_user.id,
            Membership.role == "teacher",
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            Membership.school_id == StaffAssignment.school_id,
            School.status != "suspended",
            *open_interval_expression(StaffAssignment, today),
        )
        .first()
    )
    if not assignment_access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Active teacher assignment required")

    assignment, _membership, school = assignment_access
    cards = _assignment_cards(db, [(assignment, school)])
    card = cards[0]
    roster = _roster_payload(
        db,
        school.id,
        class_section_id=assignment.class_section_id,
        subject_group_id=assignment.subject_group_id,
    )
    student_ids = [row["id"] for row in roster["students"]]
    avatar_ids = ensure_student_avatars(db, student_ids)
    point_totals = (
        dict(
            db.query(BehaviourEvent.student_id, func.coalesce(func.sum(BehaviourEvent.points_delta), 0))
            .filter(
                BehaviourEvent.school_id == school.id,
                BehaviourEvent.student_id.in_(student_ids),
                BehaviourEvent.reversed_at.is_(None),
            )
            .group_by(BehaviourEvent.student_id)
            .all()
        )
        if student_ids
        else {}
    )

    # The response is deliberately allow-listed for the classroom screen:
    # no guardian, contact, enrolment, import, invite, code, or token fields.
    return {
        "assignment": {
            "id": card["id"],
            "role": card["role"],
            "target_type": card["target_type"],
            "school": {"id": school.id, "name": school.name, "name_ar": school.name_ar},
            "class_section": ({"id": card["class_section"]["id"], "name": card["class_section"]["name"], "name_ar": card["class_section"]["name_ar"]} if card["class_section"] else None),
            "subject_group": ({"id": card["subject_group"]["id"], "name": card["subject_group"]["name"], "name_ar": card["subject_group"]["name_ar"]} if card["subject_group"] else None),
            "subject": ({"id": card["subject"]["id"], "name": card["subject"]["name"], "name_ar": card["subject"]["name_ar"]} if card["subject"] else None),
            "branch": ({"id": card["branch"]["id"], "name": card["branch"]["name"], "name_ar": card["branch"]["name_ar"]} if card["branch"] else None),
            "academic_year": ({"id": card["academic_year"]["id"], "name": card["academic_year"]["name"], "name_ar": card["academic_year"]["name_ar"]} if card["academic_year"] else None),
            "grade_level": ({"id": card["grade_level"]["id"], "name": card["grade_level"]["name"], "name_ar": card["grade_level"]["name_ar"]} if card["grade_level"] else None),
        },
        "student_count": len(roster["students"]),
        "students": [_classroom_student_payload(row, avatar_ids.get(row["id"]), int(point_totals.get(row["id"], 0))) for row in roster["students"]],
    }


@router.get(
    "/schools/{school_id}/sections/{class_section_id}/roster",
    dependencies=[Depends(require_teacher_of(class_section_param="class_section_id"))],
)
def section_roster(school_id: int, class_section_id: int, db: Session = Depends(get_db)):
    return _roster_payload(db, school_id, class_section_id=class_section_id)


@router.get(
    "/schools/{school_id}/subject-groups/{subject_group_id}/roster",
    dependencies=[Depends(require_teacher_of(subject_group_param="subject_group_id"))],
)
def subject_group_roster(school_id: int, subject_group_id: int, db: Session = Depends(get_db)):
    return _roster_payload(db, school_id, subject_group_id=subject_group_id)

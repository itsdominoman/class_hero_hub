from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import auth
from ..behaviour_service import guardian_points_payload
from ..database import get_db
from ..models_school import ClassSection, Enrolment, GradeLevel, GuardianLink, School, Student, User
from ..school_scope import open_interval_expression
from ..student_avatars import avatar_urls, ensure_student_avatars

router = APIRouter()


def _current_class_section_id_by_student(db: Session, student_ids: set[int]) -> dict[int, int]:
    if not student_ids:
        return {}
    rows = (
        db.query(Enrolment)
        .filter(
            Enrolment.student_id.in_(student_ids),
            Enrolment.class_section_id.is_not(None),
            *open_interval_expression(Enrolment),
        )
        .order_by(Enrolment.id.desc())
        .all()
    )
    section_by_student_id: dict[int, int] = {}
    for row in rows:
        section_by_student_id.setdefault(row.student_id, row.class_section_id)
    return section_by_student_id


def initials_from_name(first_name: str | None, last_name: str | None) -> str:
    parts = [part[0] for part in (first_name, last_name) if part]
    initials = "".join(parts).upper()
    return initials[:2] or "?"


@router.get("/dashboard")
def guardian_dashboard(
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    links = (
        db.query(GuardianLink)
        .filter(
            GuardianLink.user_id == current_user.id,
            GuardianLink.status == "active",
            GuardianLink.revoked_at.is_(None),
        )
        .all()
    )

    student_ids = {link.student_id for link in links}
    avatar_ids_by_student = ensure_student_avatars(db, student_ids)
    students_by_id = (
        {student.id: student for student in db.query(Student).filter(Student.id.in_(student_ids)).all()}
        if student_ids
        else {}
    )

    school_ids = {student.school_id for student in students_by_id.values()}
    schools_by_id = (
        {school.id: school for school in db.query(School).filter(School.id.in_(school_ids)).all()}
        if school_ids
        else {}
    )

    section_by_student_id = _current_class_section_id_by_student(db, student_ids)

    class_section_ids = {section_id for section_id in section_by_student_id.values() if section_id is not None}
    class_sections_by_id = (
        {row.id: row for row in db.query(ClassSection).filter(ClassSection.id.in_(class_section_ids)).all()}
        if class_section_ids
        else {}
    )

    grade_level_ids = {row.grade_level_id for row in class_sections_by_id.values() if row.grade_level_id}
    grade_levels_by_id = (
        {row.id: row for row in db.query(GradeLevel).filter(GradeLevel.id.in_(grade_level_ids)).all()}
        if grade_level_ids
        else {}
    )
    points_by_student_id = {
        row["student_id"]: row for row in guardian_points_payload(db, current_user.id)["children"]
    }

    children: list[dict[str, Any]] = []
    for link in sorted(links, key=lambda row: row.id):
        student = students_by_id.get(link.student_id)
        if not student:
            continue
        school = schools_by_id.get(student.school_id)
        class_section = class_sections_by_id.get(section_by_student_id.get(student.id))
        grade_level = grade_levels_by_id.get(class_section.grade_level_id) if class_section else None
        display_name = student.preferred_name or f"{student.first_name} {student.last_name}".strip()
        points = points_by_student_id.get(student.id, {"total": 0, "recent_events": []})
        children.append(
            {
                "student_id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "display_name": display_name,
                "initials": initials_from_name(student.first_name, student.last_name),
                **avatar_urls(avatar_ids_by_student.get(student.id)),
                "school_id": student.school_id,
                "school_name": school.name if school else None,
                "class_section_name": class_section.name if class_section else None,
                "grade_level_name": grade_level.name if grade_level else None,
                "relationship": link.relationship,
                "link_status": link.status,
                "email_matched_contact": link.email_matched_contact,
                "points_total": points["total"],
                "recent_point_events": points["recent_events"],
            }
        )

    return {"children": children}

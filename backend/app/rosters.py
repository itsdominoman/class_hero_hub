from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from .models_school import ClassSection, Enrolment, Student, SubjectGroup
from .school_scope import open_interval_expression


def row_ref(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = {
        "id": row.id,
        "code": getattr(row, "code", None),
        "name": getattr(row, "name", None),
        "name_ar": getattr(row, "name_ar", None),
        "status": getattr(row, "status", None),
        "created_at": getattr(row, "created_at", None),
    }
    for field in ("school_id", "sort_order", "branch_campus_id", "academic_year_id", "grade_level_id", "class_section_id", "subject_id", "enrolment_policy"):
        if hasattr(row, field):
            data[field] = getattr(row, field)
    return data


def student_payload(row: Student) -> dict[str, Any]:
    display_name = " ".join(part for part in [row.preferred_name or row.first_name, row.last_name] if part).strip()
    return {
        "id": row.id,
        "school_id": row.school_id,
        "external_ref": row.external_ref,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "preferred_name": row.preferred_name,
        "display_name": display_name,
        "name_ar": row.name_ar,
        "date_of_birth": row.date_of_birth,
        "gender": row.gender,
        "status": row.status,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _section_roster_rows(db: Session, school_id: int, class_section_id: int, today: date):
    return (
        db.query(Student, Enrolment)
        .join(Enrolment, Enrolment.student_id == Student.id)
        .filter(
            Enrolment.school_id == school_id,
            Enrolment.class_section_id == class_section_id,
            Enrolment.kind == "member",
            *open_interval_expression(Enrolment, today),
            Student.status == "active",
        )
        .order_by(Student.last_name.asc(), Student.first_name.asc(), Student.id.asc())
        .all()
    )


def _explicit_group_rows(db: Session, school_id: int, subject_group_id: int, today: date, *, kind: str = "member"):
    return (
        db.query(Student, Enrolment)
        .join(Enrolment, Enrolment.student_id == Student.id)
        .filter(
            Enrolment.school_id == school_id,
            Enrolment.subject_group_id == subject_group_id,
            Enrolment.kind == kind,
            *open_interval_expression(Enrolment, today),
            Student.status == "active",
        )
        .all()
    )


def _default_group_rows(db: Session, school_id: int, group: SubjectGroup, today: date):
    query = (
        db.query(Student, Enrolment)
        .join(Enrolment, Enrolment.student_id == Student.id)
        .filter(
            Enrolment.school_id == school_id,
            Enrolment.class_section_id.is_not(None),
            Enrolment.kind == "member",
            *open_interval_expression(Enrolment, today),
            Student.status == "active",
        )
    )
    if group.enrolment_policy == "default_for_section":
        return query.filter(Enrolment.class_section_id == group.class_section_id).all()
    if group.enrolment_policy == "default_for_grade":
        return (
            query.join(ClassSection, ClassSection.id == Enrolment.class_section_id)
            .filter(
                ClassSection.school_id == school_id,
                ClassSection.status == "active",
                ClassSection.grade_level_id == group.grade_level_id,
                ClassSection.academic_year_id == group.academic_year_id,
            )
            .all()
        )
    return []


def subject_group_members(db: Session, school_id: int, group: SubjectGroup, today: date) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    excluded = {
        student.id: (student, enrolment)
        for student, enrolment in _explicit_group_rows(db, school_id, group.id, today, kind="excluded")
    }
    members: dict[int, dict[str, Any]] = {}
    if group.enrolment_policy in {"default_for_section", "default_for_grade"}:
        for student, enrolment in _default_group_rows(db, school_id, group, today):
            if student.id not in excluded:
                members[student.id] = student_payload(student) | {
                    "enrolment_id": None,
                    "enrolled_from": enrolment.valid_from,
                    "source": "default",
                }
    for student, enrolment in _explicit_group_rows(db, school_id, group.id, today):
        if student.id not in excluded:
            members[student.id] = student_payload(student) | {
                "enrolment_id": enrolment.id,
                "enrolled_from": enrolment.valid_from,
                "source": "explicit",
            }
    students = sorted(members.values(), key=lambda row: ((row["last_name"] or ""), (row["first_name"] or ""), row["id"]))
    excluded_students = sorted(
        [
            student_payload(student) | {"enrolment_id": enrolment.id, "enrolled_from": enrolment.valid_from, "source": "excluded"}
            for student, enrolment in excluded.values()
        ],
        key=lambda row: ((row["last_name"] or ""), (row["first_name"] or ""), row["id"]),
    )
    return students, excluded_students


def roster_payload(
    db: Session,
    school_id: int,
    *,
    class_section_id: int | None = None,
    subject_group_id: int | None = None,
    today: date,
) -> dict[str, Any]:
    if class_section_id is not None:
        section = db.query(ClassSection).filter(ClassSection.id == class_section_id, ClassSection.school_id == school_id).first()
        students = [
            student_payload(student) | {"enrolment_id": enrolment.id, "enrolled_from": enrolment.valid_from}
            for student, enrolment in _section_roster_rows(db, school_id, class_section_id, today)
        ]
        return {"class_section": row_ref(section), "subject_group": None, "students": students}

    group = db.query(SubjectGroup).filter(SubjectGroup.id == subject_group_id, SubjectGroup.school_id == school_id).first()
    section = db.query(ClassSection).filter(ClassSection.id == group.class_section_id).first() if group and group.class_section_id else None
    students, excluded_students = subject_group_members(db, school_id, group, today) if group else ([], [])
    return {
        "class_section": row_ref(section),
        "subject_group": row_ref(group),
        "enrolment_policy": group.enrolment_policy if group else None,
        "students": students,
        "excluded_students": excluded_students,
    }


def current_subject_groups_for_student(db: Session, school_id: int, student_id: int, today: date) -> list[dict[str, Any]]:
    groups = (
        db.query(SubjectGroup)
        .filter(SubjectGroup.school_id == school_id, SubjectGroup.status != "archived")
        .order_by(SubjectGroup.sort_order.asc(), SubjectGroup.id.asc())
        .all()
    )
    current = []
    for group in groups:
        for student in subject_group_members(db, school_id, group, today)[0]:
            if student["id"] == student_id:
                current.append(row_ref(group) | {key: student[key] for key in ("source", "enrolment_id", "enrolled_from")})
                break
    return current

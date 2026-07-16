from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable

from sqlalchemy import and_, or_
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
        "avatar_id": row.avatar_id,
        "status": row.status,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _section_roster_rows(db: Session, school_id: int, class_section_id: int, today: date):
    return (
        db.query(Student, Enrolment)
        .join(Enrolment, Enrolment.student_id == Student.id)
        .filter(
            Student.school_id == school_id,
            Enrolment.school_id == school_id,
            Enrolment.class_section_id == class_section_id,
            Enrolment.kind == "member",
            *open_interval_expression(Enrolment, today),
            Student.status == "active",
        )
        .order_by(Student.last_name.asc(), Student.first_name.asc(), Student.id.asc())
        .all()
    )


@dataclass
class RosterResolution:
    """Set-based current roster context for a school and optional student scope."""

    class_sections_by_student: dict[int, list[ClassSection]]
    subject_groups_by_student: dict[int, list[dict[str, Any]]]
    students_by_subject_group: dict[int, list[dict[str, Any]]]
    excluded_students_by_subject_group: dict[int, list[dict[str, Any]]]


def _normalise_ids(values: Iterable[int] | None) -> set[int] | None:
    if values is None:
        return None
    return {int(value) for value in values}


def resolve_rosters_for_students(
    db: Session,
    school_id: int,
    today: date,
    *,
    student_ids: Iterable[int] | None = None,
    groups: Iterable[SubjectGroup] | None = None,
) -> RosterResolution:
    """Resolve current class and subject-group membership with bounded queries.

    When ``student_ids`` is supplied, every query is restricted to those students.
    Passing ``groups`` avoids reloading a caller-owned single-group target; otherwise
    all non-archived groups in the school are loaded once.
    """

    scoped_student_ids = _normalise_ids(student_ids)
    if scoped_student_ids == set():
        return RosterResolution({}, {}, {}, {})

    all_groups_scope = groups is None
    if all_groups_scope:
        group_rows = (
            db.query(SubjectGroup)
            .filter(SubjectGroup.school_id == school_id, SubjectGroup.status != "archived")
            .order_by(SubjectGroup.sort_order.asc(), SubjectGroup.id.asc())
            .all()
        )
    else:
        group_rows = sorted(
            (
                group
                for group in groups
                if group.school_id == school_id and group.status != "archived"
            ),
            key=lambda group: (group.sort_order or 0, group.id),
        )

    default_section_ids = {
        group.class_section_id
        for group in group_rows
        if group.enrolment_policy == "default_for_section" and group.class_section_id is not None
    }
    default_grade_years = {
        (group.grade_level_id, group.academic_year_id)
        for group in group_rows
        if group.enrolment_policy == "default_for_grade" and group.grade_level_id is not None
    }
    class_scope_filters = []
    if default_section_ids:
        class_scope_filters.append(ClassSection.id.in_(default_section_ids))
    class_scope_filters.extend(
        and_(
            ClassSection.grade_level_id == grade_level_id,
            ClassSection.academic_year_id == academic_year_id,
        )
        for grade_level_id, academic_year_id in default_grade_years
    )

    class_rows: list[tuple[Student, Enrolment, ClassSection]] = []
    if all_groups_scope or class_scope_filters:
        class_query = (
            db.query(Student, Enrolment, ClassSection)
            .join(Enrolment, Enrolment.student_id == Student.id)
            .join(ClassSection, ClassSection.id == Enrolment.class_section_id)
            .filter(
                Student.school_id == school_id,
                Student.status == "active",
                Enrolment.school_id == school_id,
                Enrolment.class_section_id.is_not(None),
                Enrolment.kind == "member",
                *open_interval_expression(Enrolment, today),
                ClassSection.school_id == school_id,
                ClassSection.status == "active",
            )
            .order_by(Enrolment.id.asc())
        )
        if not all_groups_scope:
            class_query = class_query.filter(or_(*class_scope_filters))
        if scoped_student_ids is not None:
            class_query = class_query.filter(Student.id.in_(scoped_student_ids))
        class_rows = class_query.all()

    group_ids = [group.id for group in group_rows]
    explicit_rows: list[tuple[Student, Enrolment]] = []
    if group_ids:
        explicit_query = (
            db.query(Student, Enrolment)
            .join(Enrolment, Enrolment.student_id == Student.id)
            .filter(
                Student.school_id == school_id,
                Student.status == "active",
                Enrolment.school_id == school_id,
                Enrolment.subject_group_id.in_(group_ids),
                Enrolment.kind.in_(("member", "excluded")),
                *open_interval_expression(Enrolment, today),
            )
            .order_by(Enrolment.id.asc())
        )
        if scoped_student_ids is not None:
            explicit_query = explicit_query.filter(Student.id.in_(scoped_student_ids))
        explicit_rows = explicit_query.all()

    class_sections_by_student: dict[int, list[ClassSection]] = {}
    class_rows_by_section: dict[int, list[tuple[Student, Enrolment, ClassSection]]] = {}
    class_rows_by_grade_year: dict[tuple[int, int], list[tuple[Student, Enrolment, ClassSection]]] = {}
    for student, enrolment, section in class_rows:
        student_sections = class_sections_by_student.setdefault(student.id, [])
        if section.id not in {row.id for row in student_sections}:
            student_sections.append(section)
        class_rows_by_section.setdefault(section.id, []).append((student, enrolment, section))
        class_rows_by_grade_year.setdefault((section.grade_level_id, section.academic_year_id), []).append((student, enrolment, section))

    explicit_members_by_group: dict[int, list[tuple[Student, Enrolment]]] = {}
    exclusions_by_group: dict[int, list[tuple[Student, Enrolment]]] = {}
    for student, enrolment in explicit_rows:
        target = explicit_members_by_group if enrolment.kind == "member" else exclusions_by_group
        target.setdefault(enrolment.subject_group_id, []).append((student, enrolment))

    students_by_subject_group: dict[int, list[dict[str, Any]]] = {}
    excluded_students_by_subject_group: dict[int, list[dict[str, Any]]] = {}
    subject_groups_by_student: dict[int, list[dict[str, Any]]] = {}
    for group in group_rows:
        excluded = {
            student.id: (student, enrolment)
            for student, enrolment in exclusions_by_group.get(group.id, [])
        }
        members: dict[int, dict[str, Any]] = {}
        if group.enrolment_policy == "default_for_section" and group.class_section_id is not None:
            default_rows = class_rows_by_section.get(group.class_section_id, [])
            # The exact-section match also enforces the group's academic-year
            # context if legacy/inconsistent rows exist.
            default_rows = [row for row in default_rows if row[2].academic_year_id == group.academic_year_id]
        elif group.enrolment_policy == "default_for_grade" and group.grade_level_id is not None:
            default_rows = class_rows_by_grade_year.get((group.grade_level_id, group.academic_year_id), [])
        else:
            default_rows = []

        for student, enrolment, _section in default_rows:
            members[student.id] = student_payload(student) | {
                "enrolment_id": None,
                "enrolled_from": enrolment.valid_from,
                "source": "default",
            }
        for student, enrolment in explicit_members_by_group.get(group.id, []):
            members[student.id] = student_payload(student) | {
                "enrolment_id": enrolment.id,
                "enrolled_from": enrolment.valid_from,
                "source": "explicit",
            }
        for student_id in excluded:
            members.pop(student_id, None)

        sorted_members = sorted(
            members.values(),
            key=lambda row: ((row["last_name"] or ""), (row["first_name"] or ""), row["id"]),
        )
        sorted_excluded = sorted(
            [
                student_payload(student) | {
                    "enrolment_id": enrolment.id,
                    "enrolled_from": enrolment.valid_from,
                    "source": "excluded",
                }
                for student, enrolment in excluded.values()
            ],
            key=lambda row: ((row["last_name"] or ""), (row["first_name"] or ""), row["id"]),
        )
        students_by_subject_group[group.id] = sorted_members
        excluded_students_by_subject_group[group.id] = sorted_excluded

        group_ref = row_ref(group)
        for student in sorted_members:
            subject_groups_by_student.setdefault(student["id"], []).append(
                group_ref | {
                    key: student[key]
                    for key in ("source", "enrolment_id", "enrolled_from")
                }
            )

    return RosterResolution(
        class_sections_by_student=class_sections_by_student,
        subject_groups_by_student=subject_groups_by_student,
        students_by_subject_group=students_by_subject_group,
        excluded_students_by_subject_group=excluded_students_by_subject_group,
    )


def subject_group_members(db: Session, school_id: int, group: SubjectGroup, today: date) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    resolution = resolve_rosters_for_students(db, school_id, today, groups=[group])
    return (
        resolution.students_by_subject_group.get(group.id, []),
        resolution.excluded_students_by_subject_group.get(group.id, []),
    )


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


def bulk_subject_groups_for_students(
    db: Session,
    school_id: int,
    today: date,
    *,
    student_ids: Iterable[int] | None = None,
) -> dict[int, list[dict[str, Any]]]:
    """Return current subject groups using three bounded set-based queries."""

    return resolve_rosters_for_students(
        db,
        school_id,
        today,
        student_ids=student_ids,
    ).subject_groups_by_student


def current_subject_groups_for_student(db: Session, school_id: int, student_id: int, today: date) -> list[dict[str, Any]]:
    return bulk_subject_groups_for_students(
        db,
        school_id,
        today,
        student_ids=[student_id],
    ).get(student_id, [])

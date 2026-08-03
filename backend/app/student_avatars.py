from __future__ import annotations

import secrets
from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy.orm import Session

from .models_school import ClassSection, Enrolment, Student
from .school_scope import open_interval_expression


RETIRED_AVATAR_IDS = frozenset({56, 59, 67, 75, 77, 89, 90})
DISPLAYABLE_BOY_AVATAR_IDS = tuple(range(31, 61))
DISPLAYABLE_GIRL_AVATAR_IDS = tuple((*range(61, 74), *range(75, 91)))
DISPLAYABLE_AVATAR_IDS = DISPLAYABLE_BOY_AVATAR_IDS + DISPLAYABLE_GIRL_AVATAR_IDS
BOY_AVATAR_IDS = tuple(avatar_id for avatar_id in DISPLAYABLE_BOY_AVATAR_IDS if avatar_id not in RETIRED_AVATAR_IDS)
GIRL_AVATAR_IDS = tuple(avatar_id for avatar_id in DISPLAYABLE_GIRL_AVATAR_IDS if avatar_id not in RETIRED_AVATAR_IDS)
ASSIGNABLE_AVATAR_IDS = BOY_AVATAR_IDS + GIRL_AVATAR_IDS


def avatar_urls(avatar_id: int | None) -> dict[str, str | int | None]:
    # Retired artwork remains displayable for safe rollback and stale clients,
    # but is excluded from every assignment pool below.
    if avatar_id not in DISPLAYABLE_AVATAR_IDS:
        return {"avatar_id": None, "avatar_url_128": None, "avatar_url_256": None}
    return {
        "avatar_id": avatar_id,
        "avatar_url_128": f"/avatars/128/{avatar_id}-128.webp",
        "avatar_url_256": f"/avatars/256/{avatar_id}-256.webp",
    }


def _pool_for_gender(gender: str | None) -> tuple[int, ...]:
    normalized = (gender or "").strip().lower()
    if normalized == "male":
        return BOY_AVATAR_IDS
    if normalized == "female":
        return GIRL_AVATAR_IDS
    return ()


def _current_class_ids_by_student(db: Session, student_ids: set[int]) -> dict[int, set[int]]:
    if not student_ids:
        return {}
    rows = (
        db.query(Enrolment.student_id, Enrolment.class_section_id)
        .join(Student, Student.id == Enrolment.student_id)
        .join(ClassSection, ClassSection.id == Enrolment.class_section_id)
        .filter(
            Enrolment.student_id.in_(student_ids),
            Enrolment.class_section_id.is_not(None),
            Enrolment.school_id == Student.school_id,
            Enrolment.kind == "member",
            ClassSection.school_id == Student.school_id,
            ClassSection.status == "active",
            *open_interval_expression(Enrolment),
        )
        .distinct()
        .all()
    )
    result: dict[int, set[int]] = defaultdict(set)
    for student_id, class_section_id in rows:
        result[student_id].add(class_section_id)
    return dict(result)


def _used_avatars_by_class(
    db: Session,
    class_section_ids: set[int],
    reassigned_student_ids: set[int],
) -> dict[int, set[int]]:
    if not class_section_ids:
        return {}
    rows = (
        db.query(Student.id, Student.avatar_id, Enrolment.class_section_id)
        .join(Enrolment, Enrolment.student_id == Student.id)
        .join(ClassSection, ClassSection.id == Enrolment.class_section_id)
        .filter(
            Student.status == "active",
            Enrolment.class_section_id.in_(class_section_ids),
            Enrolment.school_id == Student.school_id,
            Enrolment.kind == "member",
            ClassSection.school_id == Student.school_id,
            ClassSection.status == "active",
            *open_interval_expression(Enrolment),
        )
        .distinct()
        .all()
    )
    result: dict[int, set[int]] = defaultdict(set)
    for student_id, avatar_id, class_section_id in rows:
        if student_id not in reassigned_student_ids and avatar_id in ASSIGNABLE_AVATAR_IDS:
            result[class_section_id].add(avatar_id)
    return dict(result)


def ensure_student_avatars(
    db: Session,
    student_ids: Iterable[int],
    *,
    commit: bool = True,
) -> dict[int, int]:
    """Assign safe, stable avatars while avoiding current class collisions.

    Male and female students use separate assignable pools. Missing or unknown
    gender is never guessed. Retired or wrong-pool assignments are replaced.
    Current classmates are considered even when the caller requests only one
    student, and repeats are used only when every suitable avatar is already
    present in at least one of the student's current classes.
    """
    ids = set(student_ids)
    if not ids:
        return {}

    students = (
        db.query(Student)
        .filter(Student.id.in_(ids))
        .order_by(Student.id.asc())
        .all()
    )
    without_recorded_gender = [
        student
        for student in students
        if not _pool_for_gender(student.gender) and student.avatar_id is not None
    ]
    for student in without_recorded_gender:
        student.avatar_id = None

    candidates = [
        student
        for student in students
        if (pool := _pool_for_gender(student.gender)) and student.avatar_id not in pool
    ]
    candidate_ids = {student.id for student in candidates}
    class_ids_by_student = _current_class_ids_by_student(db, candidate_ids)
    class_section_ids = {
        class_section_id
        for class_ids in class_ids_by_student.values()
        for class_section_id in class_ids
    }
    used_by_class = _used_avatars_by_class(db, class_section_ids, candidate_ids)
    changed = bool(without_recorded_gender)
    rng = secrets.SystemRandom()

    for student in sorted(candidates, key=lambda row: (-len(class_ids_by_student.get(row.id, set())), row.id)):
        pool = _pool_for_gender(student.gender)
        class_ids = class_ids_by_student.get(student.id, set())
        used = {
            avatar_id
            for class_section_id in class_ids
            for avatar_id in used_by_class.get(class_section_id, set())
        }
        available = [avatar_id for avatar_id in pool if avatar_id not in used]
        if available:
            choices = available
        else:
            conflict_counts = {
                avatar_id: sum(
                    avatar_id in used_by_class.get(class_section_id, set())
                    for class_section_id in class_ids
                )
                for avatar_id in pool
            }
            fewest_conflicts = min(conflict_counts.values(), default=0)
            choices = [
                avatar_id
                for avatar_id, conflict_count in conflict_counts.items()
                if conflict_count == fewest_conflicts
            ]
        student.avatar_id = rng.choice(choices)
        for class_section_id in class_ids:
            used_by_class.setdefault(class_section_id, set()).add(student.avatar_id)
        changed = True

    result = {
        student.id: student.avatar_id
        for student in students
        if student.avatar_id in DISPLAYABLE_AVATAR_IDS
    }
    if changed and commit:
        db.commit()
    return result

"""Audit or apply gender-safe student avatar assignments.

Dry-run is the default. Pass ``--apply`` to persist replacements for retired,
missing, or wrong-pool assignments. Output is aggregate-only and contains no
student, class, or school identifiers.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import text

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.database import SessionLocal
from app.models_school import Student
from app.student_avatars import (
    BOY_AVATAR_IDS,
    GIRL_AVATAR_IDS,
    RETIRED_AVATAR_IDS,
    ensure_student_avatars,
)


def _normalise_gender(value: str | None) -> str:
    return (value or "").strip().lower()


def _pool_for_gender(value: str | None) -> tuple[int, ...]:
    gender = _normalise_gender(value)
    if gender == "male":
        return BOY_AVATAR_IDS
    if gender == "female":
        return GIRL_AVATAR_IDS
    return ()


def _class_duplicate_groups(db) -> int:
    row = db.execute(
        text(
            """
            WITH current_members AS (
              SELECT DISTINCT e.class_section_id, s.id AS student_id, s.avatar_id
              FROM enrolments e
              JOIN students s ON s.id = e.student_id
              JOIN class_sections c ON c.id = e.class_section_id
              WHERE s.status = 'active'
                AND c.status = 'active'
                AND e.class_section_id IS NOT NULL
                AND e.kind = 'member'
                AND e.valid_from <= CURRENT_DATE
                AND (e.valid_to IS NULL OR e.valid_to > CURRENT_DATE)
                AND s.avatar_id IS NOT NULL
            ), duplicate_groups AS (
              SELECT class_section_id, avatar_id
              FROM current_members
              GROUP BY class_section_id, avatar_id
              HAVING count(*) > 1
            )
            SELECT count(*) AS duplicate_groups FROM duplicate_groups
            """
        )
    ).one()
    return int(row.duplicate_groups)


def run(*, apply: bool) -> dict[str, object]:
    db = SessionLocal()
    try:
        students = (
            db.query(Student)
            .filter(Student.status == "active")
            .order_by(Student.id.asc())
            .all()
        )
        before = {student.id: student.avatar_id for student in students}
        targets = [
            student
            for student in students
            if (pool := _pool_for_gender(student.gender)) and student.avatar_id not in pool
        ]
        duplicate_groups_before = _class_duplicate_groups(db)

        ensure_student_avatars(db, (student.id for student in targets), commit=False)
        db.flush()

        changed = [student for student in targets if student.avatar_id != before[student.id]]
        changed_by_gender = Counter(_normalise_gender(student.gender) for student in changed)
        remaining_retired = sum(student.avatar_id in RETIRED_AVATAR_IDS for student in students)
        wrong_pool = sum(
            bool(pool := _pool_for_gender(student.gender)) and student.avatar_id not in pool
            for student in students
        )
        missing_without_gender = sum(
            student.avatar_id is None and not _pool_for_gender(student.gender)
            for student in students
        )
        duplicate_groups_after = _class_duplicate_groups(db)

        report: dict[str, object] = {
            "mode": "apply" if apply else "dry-run",
            "active_students": len(students),
            "targeted_students": len(targets),
            "changed_students": len(changed),
            "missing_assigned": sum(before[student.id] is None for student in changed),
            "retired_reassigned": sum(before[student.id] in RETIRED_AVATAR_IDS for student in changed),
            "wrong_pool_reassigned": sum(
                before[student.id] is not None
                and before[student.id] not in RETIRED_AVATAR_IDS
                and before[student.id] not in _pool_for_gender(student.gender)
                for student in changed
            ),
            "changed_by_gender": dict(sorted(changed_by_gender.items())),
            "missing_without_male_or_female_gender": missing_without_gender,
            "remaining_retired_assignments": remaining_retired,
            "remaining_wrong_gender_pool_assignments": wrong_pool,
            "class_duplicate_avatar_groups_before": duplicate_groups_before,
            "class_duplicate_avatar_groups_after": duplicate_groups_after,
        }

        if remaining_retired or wrong_pool or duplicate_groups_after > duplicate_groups_before:
            db.rollback()
            raise RuntimeError(f"avatar assignment validation failed: {json.dumps(report, sort_keys=True)}")

        if apply:
            db.commit()
        else:
            db.rollback()
        return report
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist assignments. Without this flag the command is read-only.",
    )
    args = parser.parse_args()
    print(json.dumps(run(apply=args.apply), sort_keys=True))


if __name__ == "__main__":
    main()

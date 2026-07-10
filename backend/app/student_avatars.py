from __future__ import annotations

import secrets
from collections.abc import Iterable

from sqlalchemy.orm import Session

from .models_school import Student


BOY_AVATAR_IDS = tuple(range(31, 61))
GIRL_AVATAR_IDS = tuple((*range(61, 74), *range(75, 91)))
VALID_AVATAR_IDS = BOY_AVATAR_IDS + GIRL_AVATAR_IDS


def avatar_urls(avatar_id: int | None) -> dict[str, str | int | None]:
    if avatar_id not in VALID_AVATAR_IDS:
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
    return VALID_AVATAR_IDS


def ensure_student_avatars(db: Session, student_ids: Iterable[int]) -> dict[int, int]:
    """Assign missing avatars in one query and one transaction commit.

    Existing values always win, making the student identity stable across
    class moves and page loads. Missing values prefer an unused valid avatar
    within this returned roster; repeats begin only after that gender's pool
    has been exhausted. Unknown/other/unspecified genders use the combined
    valid pool. Avatar 74 is absent from every pool.
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
    used = {student.avatar_id for student in students if student.avatar_id in VALID_AVATAR_IDS}
    changed = False
    rng = secrets.SystemRandom()

    for student in students:
        if student.avatar_id in VALID_AVATAR_IDS:
            continue
        pool = _pool_for_gender(student.gender)
        available = [avatar_id for avatar_id in pool if avatar_id not in used]
        student.avatar_id = rng.choice(available or pool)
        used.add(student.avatar_id)
        changed = True

    result = {student.id: student.avatar_id for student in students if student.avatar_id in VALID_AVATAR_IDS}
    if changed:
        db.commit()
    return result

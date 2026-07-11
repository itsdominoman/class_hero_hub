from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .models_school import BehaviourCategory, BehaviourEvent, GuardianLink, Membership, School, Student, User

DEFAULT_CATEGORIES = {
    "positive": ["Listening well", "Good work", "Teamwork", "Helping others", "Kindness", "Great effort", "Respectful behaviour", "Leadership", "Improvement", "Participation"],
    "needs_work": ["Late for class", "Homework incomplete", "Not listening", "Disrupting others", "Unkind behaviour", "Fighting / rough play", "Disrespect", "Off-task", "Forgot equipment", "Unsafe behaviour"],
}


def category_payload(row: BehaviourCategory) -> dict:
    return {"id": row.id, "type": row.type, "label": row.label, "points_value": row.points_value, "sort_order": row.sort_order, "active": row.active}


def seed_default_categories(db: Session, school_id: int) -> list[BehaviourCategory]:
    existing = {(r.type, r.label) for r in db.query(BehaviourCategory).filter(BehaviourCategory.school_id == school_id).all()}
    created = []
    for category_type, labels in DEFAULT_CATEGORIES.items():
        for index, label in enumerate(labels, 1):
            if (category_type, label) in existing:
                continue
            row = BehaviourCategory(school_id=school_id, type=category_type, label=label, points_value=1 if category_type == "positive" else -1, sort_order=index * 10, active=True)
            db.add(row)
            created.append(row)
    db.flush()
    return created


def visible_categories(db: Session, school_id: int, *, active_only: bool = True) -> list[BehaviourCategory]:
    query = db.query(BehaviourCategory).filter(BehaviourCategory.school_id == school_id)
    if active_only:
        query = query.filter(BehaviourCategory.active.is_(True))
    return query.order_by(BehaviourCategory.type.asc(), BehaviourCategory.sort_order.asc(), BehaviourCategory.label.asc()).all()


def active_teacher_membership(db: Session, user_id: int, school_id: int) -> Membership:
    row = (db.query(Membership).join(School, School.id == Membership.school_id).filter(
        Membership.user_id == user_id, Membership.school_id == school_id, Membership.role == "teacher",
        Membership.status == "active", Membership.revoked_at.is_(None), School.status != "suspended",
    ).first())
    if not row:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Active teacher access required")
    return row


def create_events(db: Session, *, school_id: int, student_ids: Iterable[int], category_id: int, actor: User, note: str | None) -> list[BehaviourEvent]:
    active_teacher_membership(db, actor.id, school_id)
    ids = list(dict.fromkeys(student_ids))
    if not ids or len(ids) > 40:
        raise HTTPException(status_code=422, detail="Select between 1 and 40 students")
    category = db.query(BehaviourCategory).filter(BehaviourCategory.id == category_id, BehaviourCategory.school_id == school_id, BehaviourCategory.active.is_(True)).first()
    if not category:
        raise HTTPException(status_code=400, detail="Active behaviour category not found")
    students = db.query(Student).filter(Student.id.in_(ids), Student.school_id == school_id, Student.status == "active").all()
    if len(students) != len(ids):
        raise HTTPException(status_code=400, detail="Every student must be active and belong to this school")
    safe_note = note.strip() if note and note.strip() else None
    rows = [BehaviourEvent(school_id=school_id, student_id=student.id, category_id=category.id, actor_user_id=actor.id, points_delta=category.points_value, note=safe_note, source="teacher") for student in students]
    db.add_all(rows)
    db.flush()
    return rows


def guardian_points_payload(db: Session, user_id: int, *, recent_limit: int = 5) -> dict:
    links = db.query(GuardianLink).filter(GuardianLink.user_id == user_id, GuardianLink.status == "active", GuardianLink.revoked_at.is_(None)).all()
    student_ids = {link.student_id for link in links}
    if not student_ids:
        return {"children": []}
    students = {s.id: s for s in db.query(Student).filter(Student.id.in_(student_ids)).all()}
    totals = dict(db.query(BehaviourEvent.student_id, func.coalesce(func.sum(BehaviourEvent.points_delta), 0)).filter(BehaviourEvent.student_id.in_(student_ids), BehaviourEvent.reversed_at.is_(None)).group_by(BehaviourEvent.student_id).all())
    rows = (db.query(BehaviourEvent, BehaviourCategory, User).join(BehaviourCategory, BehaviourCategory.id == BehaviourEvent.category_id).join(User, User.id == BehaviourEvent.actor_user_id).filter(BehaviourEvent.student_id.in_(student_ids), BehaviourEvent.reversed_at.is_(None)).order_by(BehaviourEvent.created_at.desc(), BehaviourEvent.id.desc()).all())
    events_by_student = defaultdict(list)
    for event, category, actor in rows:
        bucket = events_by_student[event.student_id]
        if len(bucket) < recent_limit:
            bucket.append({"id": event.id, "category_id": category.id, "category_label": category.label, "type": category.type, "points_delta": event.points_delta, "note": event.note, "teacher_name": actor.name, "created_at": event.created_at})
    return {"children": [{"student_id": sid, "display_name": students[sid].preferred_name or f"{students[sid].first_name} {students[sid].last_name}".strip(), "total": int(totals.get(sid, 0)), "recent_events": events_by_student[sid]} for sid in sorted(student_ids) if sid in students]}

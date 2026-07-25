from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models_school import BehaviourAwardRequest, BehaviourCategory, BehaviourEvent, ClassSection, GuardianLink, Membership, School, StaffAssignment, Student, Subject, SubjectGroup, User
from .rosters import roster_payload
from .school_scope import open_interval_expression

DEFAULT_CATEGORIES = {
    "positive": ["Listening well", "Good work", "Teamwork", "Helping others", "Kindness", "Great effort", "Respectful behaviour", "Leadership", "Improvement", "Participation", "Good sportsmanship", "Safe play", "Helping at break", "Lining up well", "Responsible behaviour"],
    "needs_work": ["Late for class", "Homework incomplete", "Not listening", "Disrupting others", "Unkind behaviour", "Fighting / rough play", "Disrespect", "Off-task", "Forgot equipment", "Unsafe behaviour", "Out of bounds", "Wandering halls", "Unsafe play", "Running indoors", "Leaving area without permission", "Not following instructions"],
}
DEFAULT_QUICK_ACTIONS = {
    "positive": ["Listening well", "Good work", "Teamwork", "Helping others", "Kindness", "Great effort"],
    "needs_work": ["Not listening", "Disrupting others", "Unkind behaviour", "Unsafe behaviour", "Off-task", "Not following instructions"],
}
CONTEXT_TYPES = {"class", "subject", "duty", "general"}
DUTY_CONTEXTS = {"break", "lunch", "playground", "hallway", "assembly", "bus", "general_duty"}


def category_payload(row: BehaviourCategory) -> dict:
    return {
        "id": row.id,
        "type": row.type,
        "label": row.label,
        "points_value": row.points_value,
        "sort_order": row.sort_order,
        "active": row.active,
        "is_quick_action": row.is_quick_action,
        "quick_action_order": row.quick_action_order,
    }


def seed_default_categories(db: Session, school_id: int) -> list[BehaviourCategory]:
    existing = {(r.type, r.label) for r in db.query(BehaviourCategory).filter(BehaviourCategory.school_id == school_id).all()}
    created = []
    for category_type, labels in DEFAULT_CATEGORIES.items():
        for index, label in enumerate(labels, 1):
            if (category_type, label) in existing:
                continue
            quick_order = (DEFAULT_QUICK_ACTIONS[category_type].index(label) + 1) if label in DEFAULT_QUICK_ACTIONS[category_type] else None
            row = BehaviourCategory(
                school_id=school_id,
                type=category_type,
                label=label,
                points_value=1 if category_type == "positive" else -1,
                sort_order=index * 10,
                active=True,
                is_quick_action=quick_order is not None,
                quick_action_order=quick_order,
            )
            db.add(row)
            created.append(row)
    db.flush()
    return created


def visible_categories(db: Session, school_id: int, *, active_only: bool = True) -> list[BehaviourCategory]:
    query = db.query(BehaviourCategory).filter(BehaviourCategory.school_id == school_id)
    if active_only:
        query = query.filter(BehaviourCategory.active.is_(True))
    return query.order_by(BehaviourCategory.type.asc(), BehaviourCategory.sort_order.asc(), BehaviourCategory.label.asc()).all()


def quick_actions_payload(db: Session, school_id: int) -> dict:
    rows = db.query(BehaviourCategory).filter(
        BehaviourCategory.school_id == school_id,
        BehaviourCategory.active.is_(True),
    ).order_by(
        BehaviourCategory.type.asc(),
        BehaviourCategory.is_quick_action.desc(),
        BehaviourCategory.quick_action_order.asc().nullslast(),
        BehaviourCategory.sort_order.asc(),
        BehaviourCategory.label.asc(),
    ).all()
    result = {
        "quick_actions": {"positive": [], "needs_work": []},
        "other_actions": {"positive": [], "needs_work": []},
    }
    for row in rows:
        payload = {"id": row.id, "label": row.label, "points_value": row.points_value}
        bucket = "quick_actions" if row.is_quick_action else "other_actions"
        result[bucket][row.type].append(payload)
    return result


def active_teacher_membership(db: Session, user_id: int, school_id: int) -> Membership:
    row = (db.query(Membership).join(School, School.id == Membership.school_id).filter(
        Membership.user_id == user_id, Membership.school_id == school_id, Membership.role == "teacher",
        Membership.status == "active", Membership.revoked_at.is_(None), School.status != "suspended",
    ).first())
    if not row:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Active teacher access required")
    return row


def active_behaviour_staff_membership(db: Session, user_id: int, school_id: int) -> Membership:
    rows = (db.query(Membership).join(School, School.id == Membership.school_id).filter(
        Membership.user_id == user_id,
        Membership.school_id == school_id,
        Membership.role.in_(("teacher", "school_admin")),
        Membership.status == "active",
        Membership.revoked_at.is_(None),
        School.status != "suspended",
    ).all())
    if not rows:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Active staff access required")
    return next((row for row in rows if row.role == "school_admin"), rows[0])


def _award_request_hash(
    *,
    school_id: int,
    student_ids: list[int],
    category_id: int,
    note: str | None,
    context_type: str,
    class_section_id: int | None,
    subject_group_id: int | None,
    duty_context: str | None,
) -> str:
    payload = {
        "school_id": school_id,
        "student_ids": sorted(student_ids),
        "category_id": category_id,
        "note": note,
        "context_type": context_type,
        "class_section_id": class_section_id,
        "subject_group_id": subject_group_id,
        "duty_context": duty_context,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _existing_award(
    db: Session,
    *,
    school_id: int,
    actor_user_id: int,
    idempotency_key: UUID,
    request_hash: str,
) -> list[BehaviourEvent] | None:
    request = db.query(BehaviourAwardRequest).filter(
        BehaviourAwardRequest.school_id == school_id,
        BehaviourAwardRequest.actor_user_id == actor_user_id,
        BehaviourAwardRequest.idempotency_key == idempotency_key,
    ).first()
    if request is None:
        return None
    if request.request_hash != request_hash:
        raise HTTPException(status_code=409, detail="Idempotency key was already used for a different award batch")
    rows = db.query(BehaviourEvent).filter(
        BehaviourEvent.award_request_id == request.id,
    ).order_by(BehaviourEvent.id).all()
    if not rows:
        raise HTTPException(status_code=409, detail="The original award batch is not available")
    return rows


def create_events(
    db: Session,
    *,
    school_id: int,
    student_ids: Iterable[int],
    category_id: int,
    actor: User,
    idempotency_key: UUID,
    note: str | None,
    context_type: str = "general",
    class_section_id: int | None = None,
    subject_group_id: int | None = None,
    duty_context: str | None = None,
) -> tuple[list[BehaviourEvent], bool]:
    membership = active_teacher_membership(db, actor.id, school_id)
    valid_context = (
        context_type in CONTEXT_TYPES
        and (
            (context_type == "subject" and subject_group_id is not None and class_section_id is None and duty_context is None)
            or (context_type == "class" and class_section_id is not None and subject_group_id is None and duty_context is None)
            or (context_type == "duty" and duty_context in DUTY_CONTEXTS and class_section_id is None and subject_group_id is None)
            or (context_type == "general" and class_section_id is None and subject_group_id is None and duty_context is None)
        )
    )
    if not valid_context:
        raise HTTPException(status_code=422, detail="Invalid behaviour context")
    ids = list(dict.fromkeys(student_ids))
    if not ids or len(ids) > 40:
        raise HTTPException(status_code=422, detail="Select between 1 and 40 students")
    safe_note = note.strip() if note and note.strip() else None
    request_hash = _award_request_hash(
        school_id=school_id,
        student_ids=ids,
        category_id=category_id,
        note=safe_note,
        context_type=context_type,
        class_section_id=class_section_id,
        subject_group_id=subject_group_id,
        duty_context=duty_context,
    )
    actor_user_id = actor.id
    existing = _existing_award(
        db,
        school_id=school_id,
        actor_user_id=actor_user_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    if existing is not None:
        return existing, True
    category = db.query(BehaviourCategory).filter(BehaviourCategory.id == category_id, BehaviourCategory.school_id == school_id, BehaviourCategory.active.is_(True)).first()
    if not category:
        raise HTTPException(status_code=400, detail="Active behaviour category not found")
    students = db.query(Student).filter(Student.id.in_(ids), Student.school_id == school_id, Student.status == "active").all()
    if len(students) != len(ids):
        raise HTTPException(status_code=400, detail="Every student must be active and belong to this school")
    if context_type in {"class", "subject"}:
        target_filter = StaffAssignment.class_section_id == class_section_id if context_type == "class" else StaffAssignment.subject_group_id == subject_group_id
        target_model = ClassSection if context_type == "class" else SubjectGroup
        target_id = class_section_id if context_type == "class" else subject_group_id
        target = db.query(target_model).filter(target_model.id == target_id, target_model.school_id == school_id, target_model.status == "active").first()
        if not target:
            raise HTTPException(status_code=400, detail="Active behaviour target not found")
        assignment = db.query(StaffAssignment).filter(
            StaffAssignment.school_id == school_id,
            StaffAssignment.membership_id == membership.id,
            target_filter,
            *open_interval_expression(StaffAssignment),
        ).first()
        if not assignment:
            raise HTTPException(status_code=403, detail="Teacher assignment required")
        roster = roster_payload(
            db,
            school_id,
            class_section_id=class_section_id,
            subject_group_id=subject_group_id,
            today=datetime.now(timezone.utc).date(),
        )
        roster_ids = {row["id"] for row in roster["students"]}
        if not set(ids).issubset(roster_ids):
            raise HTTPException(status_code=400, detail="Every student must belong to the selected behaviour target")
    award_request = BehaviourAwardRequest(
        school_id=school_id,
        actor_user_id=actor_user_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    db.add(award_request)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = _existing_award(
            db,
            school_id=school_id,
            actor_user_id=actor_user_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if existing is None:
            raise
        return existing, True
    rows = [BehaviourEvent(
        school_id=school_id,
        student_id=student.id,
        category_id=category.id,
        actor_user_id=actor_user_id,
        award_request_id=award_request.id,
        class_section_id=class_section_id,
        subject_group_id=subject_group_id,
        points_delta=category.points_value,
        note=safe_note,
        source="teacher",
        context_type=context_type,
        duty_context=duty_context,
    ) for student in students]
    db.add_all(rows)
    db.flush()
    return sorted(rows, key=lambda row: row.id), False


def reverse_event(
    db: Session,
    *,
    school_id: int,
    event_id: int,
    actor: User,
    reason: str,
) -> tuple[BehaviourEvent, bool]:
    membership = active_behaviour_staff_membership(db, actor.id, school_id)
    event = db.query(BehaviourEvent).filter(
        BehaviourEvent.id == event_id,
        BehaviourEvent.school_id == school_id,
    ).with_for_update().first()
    if event is None:
        raise HTTPException(status_code=404, detail="Behaviour event not found")
    if membership.role != "school_admin" and event.actor_user_id != actor.id:
        raise HTTPException(status_code=403, detail="Only the awarding teacher or a school administrator can reverse this event")
    if event.reversed_at is not None:
        return event, True
    safe_reason = reason.strip()
    if not safe_reason:
        raise HTTPException(status_code=422, detail="A reversal reason is required")
    event.reversed_at = datetime.now(timezone.utc)
    event.reversed_by_user_id = actor.id
    event.reversal_reason = safe_reason
    db.flush()
    return event, False


def event_context_payloads(db: Session, events: Iterable[BehaviourEvent]) -> dict[int, dict]:
    rows = list(events)
    group_ids = {row.subject_group_id for row in rows if row.subject_group_id is not None}
    section_ids = {row.class_section_id for row in rows if row.class_section_id is not None}
    groups = {}
    if group_ids:
        groups = {
            group.id: (group, subject)
            for group, subject in db.query(SubjectGroup, Subject).join(Subject, Subject.id == SubjectGroup.subject_id).filter(SubjectGroup.id.in_(group_ids)).all()
        }
        section_ids.update(group.class_section_id for group, _subject in groups.values() if group.class_section_id is not None)
    sections = {row.id: row for row in db.query(ClassSection).filter(ClassSection.id.in_(section_ids)).all()} if section_ids else {}
    result = {}
    for event in rows:
        group, subject = groups.get(event.subject_group_id, (None, None))
        section_id = event.class_section_id if event.class_section_id is not None else (group.class_section_id if group else None)
        result[event.id] = {
            "class_section_name": sections[section_id].name if section_id in sections else None,
            "subject_name": subject.name if subject else None,
            "subject_code": subject.code if subject else None,
            "duty_context": event.duty_context,
            "context_type": event.context_type,
        }
    return result


def guardian_points_payload(db: Session, user_id: int, *, recent_limit: int = 5) -> dict:
    links = db.query(GuardianLink).filter(GuardianLink.user_id == user_id, GuardianLink.status == "active", GuardianLink.revoked_at.is_(None)).all()
    student_ids = {link.student_id for link in links}
    if not student_ids:
        return {"children": []}
    students = {s.id: s for s in db.query(Student).filter(Student.id.in_(student_ids)).all()}
    totals = dict(db.query(BehaviourEvent.student_id, func.coalesce(func.sum(BehaviourEvent.points_delta), 0)).filter(BehaviourEvent.student_id.in_(student_ids), BehaviourEvent.reversed_at.is_(None)).group_by(BehaviourEvent.student_id).all())
    rows = (db.query(BehaviourEvent, BehaviourCategory, User).join(BehaviourCategory, BehaviourCategory.id == BehaviourEvent.category_id).join(User, User.id == BehaviourEvent.actor_user_id).filter(BehaviourEvent.student_id.in_(student_ids), BehaviourEvent.reversed_at.is_(None)).order_by(BehaviourEvent.created_at.desc(), BehaviourEvent.id.desc()).all())
    contexts = event_context_payloads(db, [event for event, _category, _actor in rows])
    events_by_student = defaultdict(list)
    for event, category, actor in rows:
        bucket = events_by_student[event.student_id]
        if len(bucket) < recent_limit:
            bucket.append({"id": event.id, "category_id": category.id, "category_label": category.label, "type": category.type, "points_delta": event.points_delta, "note": event.note, "teacher_name": actor.name, "staff_display_name": actor.name, "created_at": event.created_at, **contexts[event.id]})
    return {"children": [{"student_id": sid, "display_name": students[sid].preferred_name or f"{students[sid].first_name} {students[sid].last_name}".strip(), "total": int(totals.get(sid, 0)), "recent_events": events_by_student[sid]} for sid in sorted(student_ids) if sid in students]}

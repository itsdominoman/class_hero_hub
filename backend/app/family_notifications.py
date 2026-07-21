from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models_school import (
    Announcement,
    BehaviourCategory,
    BehaviourEvent,
    CalendarEvent,
    FhhLink,
    HomeworkItem,
    NotificationOutbox,
    PointNotificationSummary,
    School,
    SchoolPointsNotificationPolicy,
    Student,
    UpdatePost,
)
from .rosters import roster_payload


UTC = timezone.utc
CATEGORIES = {"homework", "notice", "points", "calendar", "update"}
ELIGIBLE_SCHOOL_STATUSES = {"pending_setup", "active"}
SOURCE_MODELS = {
    "homework": HomeworkItem,
    "notice": Announcement,
    "points": BehaviourEvent,
    "calendar": CalendarEvent,
    "update": UpdatePost,
}
SOURCE_TYPES = {
    "homework": "homework_item",
    "notice": "announcement",
    "points": "behaviour_event",
    "calendar": "calendar_event",
    "update": "update_post",
}
ROUTE_TYPES = dict.fromkeys(CATEGORIES)


def material_snapshot(category: str, source: Any) -> tuple:
    """Only parent-facing fields belong in material-change detection."""
    if category == "homework":
        resources = tuple(
            sorted((str(row.get("url", "")), str(row.get("label", ""))) for row in (source.resource_links or []))
        )
        return (source.item_type, source.title, source.body, source.due_at, resources)
    if category == "notice":
        return (source.title, source.body, bool(source.urgent))
    if category == "calendar":
        return (source.title, source.body, source.event_type, source.starts_at, source.ends_at, bool(source.all_day))
    if category == "update":
        return (source.body,)
    if category == "points":
        return (source.points_delta, source.reversed_at)
    raise ValueError("Unsupported family notification category")


def _student_ids_for_source(db: Session, category: str, source: Any) -> set[int]:
    if category == "points":
        return {int(source.student_id)}
    if source.audience_type == "school":
        return {
            row[0]
            for row in db.query(Student.id).filter(
                Student.school_id == source.school_id,
                Student.status == "active",
            ).all()
        }
    roster = roster_payload(
        db,
        source.school_id,
        class_section_id=source.class_section_id if source.audience_type == "class_section" else None,
        subject_group_id=source.subject_group_id if source.audience_type == "subject_group" else None,
        today=datetime.now(UTC).date(),
    )
    return {int(row["id"]) for row in roster.get("students", [])}


def _source_visible(category: str, source: Any, action: str) -> bool:
    if category == "points":
        return action == "awarded" and source.reversed_at is None
    expected = "published" if category == "notice" else "active"
    if action in {"published", "updated"}:
        return source.status == expected
    if action == "cancelled":
        return source.status == "archived"
    return False


def _next_version(db: Session, *, school_id: int, source_type: str, source_id: int) -> int:
    current = db.query(func.max(NotificationOutbox.source_version)).filter(
        NotificationOutbox.school_id == school_id,
        NotificationOutbox.source_type == source_type,
        NotificationOutbox.source_id == source_id,
    ).scalar()
    return int(current or 0) + 1


def enqueue_family_notifications(
    db: Session,
    *,
    category: str,
    source: Any,
    action: str,
    version: int | None = None,
) -> list[NotificationOutbox]:
    """Append CHH→FHH rows to the existing durable outbox.

    CHH stores only its opaque link target. Parent, family and installation
    resolution remains entirely inside FHH.
    """
    if category not in CATEGORIES or not _source_visible(category, source, action):
        return []
    points_policy = None
    if category == "points":
        points_policy = db.query(SchoolPointsNotificationPolicy).filter(
            SchoolPointsNotificationPolicy.school_id == source.school_id
        ).first()
        if points_policy is None:
            points_policy = SchoolPointsNotificationPolicy(school_id=source.school_id)
            db.add(points_policy)
            db.flush()
        if points_policy.mode != "immediate":
            return []
    if category == "homework" and source.item_type != "homework":
        return []
    school_active = db.query(School.id).filter(
        School.id == source.school_id,
        School.status.in_(ELIGIBLE_SCHOOL_STATUSES),
    ).first()
    if school_active is None:
        return []
    if category == "homework" and action == "cancelled" and source.due_at is not None:
        due_at = source.due_at if source.due_at.tzinfo else source.due_at.replace(tzinfo=UTC)
        if due_at < datetime.now(UTC):
            return []

    student_ids = _student_ids_for_source(db, category, source)
    if not student_ids:
        return []
    links = (
        db.query(FhhLink)
        .join(Student, Student.id == FhhLink.student_id)
        .filter(
            FhhLink.school_id == source.school_id,
            FhhLink.student_id.in_(student_ids),
            FhhLink.status == "active",
            FhhLink.revoked_at.is_(None),
            Student.status == "active",
        )
        .order_by(FhhLink.id)
        .all()
    )
    source_type = SOURCE_TYPES[category]
    source_version = version or _next_version(
        db, school_id=source.school_id, source_type=source_type, source_id=source.id
    )
    now = datetime.now(UTC)
    variant = None
    if category == "points":
        row = db.query(BehaviourCategory.type).filter(BehaviourCategory.id == source.category_id).first()
        variant = "positive" if row and row[0] == "positive" else "behaviour"
    urgent = bool(category == "notice" and getattr(source, "urgent", False))
    created: list[NotificationOutbox] = []
    for link in links:
        dedupe_key = (
            f"family:{category}:{source_type}:{source.id}:{action}:v{source_version}:link:{link.id}"
        )
        if db.query(NotificationOutbox.id).filter(NotificationOutbox.dedupe_key == dedupe_key).first():
            continue
        row = NotificationOutbox(
            school_id=source.school_id,
            message_id=None,
            event_category=category,
            source_type=source_type,
            source_id=source.id,
            source_action=action,
            source_version=source_version,
            route_type=category,
            route_ref=str(source.id),
            urgent=urgent,
            recipient_kind="fhh_link",
            recipient_fhh_link_id=link.id,
            channel="push",
            template_key=f"family.{category}.{action}",
            template_args={"variant": variant} if variant else {},
            deep_link=f"fhh:{category}",
            policy_version=points_policy.policy_version if points_policy is not None else 1,
            state="pending",
            eligible_at=now,
            scheduler_check_at=now,
            next_attempt_at=now,
            dedupe_key=dedupe_key,
        )
        db.add(row)
        created.append(row)
    if created:
        db.flush()
    return created


def revalidate_family_notification(db: Session, row: NotificationOutbox) -> bool:
    if row.event_category not in CATEGORIES or row.recipient_kind != "fhh_link":
        return False
    school = db.query(School).filter(
        School.id == row.school_id,
        School.status.in_(ELIGIBLE_SCHOOL_STATUSES),
    ).first()
    link = db.query(FhhLink).filter(
        FhhLink.id == row.recipient_fhh_link_id,
        FhhLink.school_id == row.school_id,
        FhhLink.status == "active",
        FhhLink.revoked_at.is_(None),
    ).first()
    if school is None or link is None:
        return False
    if row.event_category == "points":
        policy = db.query(SchoolPointsNotificationPolicy).filter(
            SchoolPointsNotificationPolicy.school_id == row.school_id
        ).first()
        if policy is None or row.policy_version != policy.policy_version:
            return False
        if row.source_type == "point_summary":
            summary = db.query(PointNotificationSummary).filter(
                PointNotificationSummary.id == row.source_id,
                PointNotificationSummary.school_id == row.school_id,
            ).first()
            enabled = bool(summary and getattr(policy, f"{summary.summary_type}_enabled", False))
            return bool(
                policy.mode == "summaries"
                and enabled
                and summary.policy_version == policy.policy_version
                and summary.student_id == link.student_id
                and db.query(Student.id).filter(
                    Student.id == link.student_id, Student.status == "active"
                ).first() is not None
            )
        if policy.mode != "immediate" or row.source_type != "behaviour_event":
            return False
    model = SOURCE_MODELS[row.event_category]
    source = db.query(model).filter(model.id == row.source_id, model.school_id == row.school_id).first()
    if source is None:
        return False
    if not _source_visible(row.event_category, source, row.source_action):
        return False
    if link.student_id not in _student_ids_for_source(db, row.event_category, source):
        return False
    student = db.query(Student.id).filter(Student.id == link.student_id, Student.status == "active").first()
    return student is not None


def cancel_undispatched_immediate_points(
    db: Session,
    *,
    school_id: int,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(UTC)
    return db.query(NotificationOutbox).filter(
        NotificationOutbox.school_id == school_id,
        NotificationOutbox.event_category == "points",
        NotificationOutbox.source_type == "behaviour_event",
        NotificationOutbox.state.in_(("held", "pending", "leased", "failed")),
    ).update({
        NotificationOutbox.state: "cancelled",
        NotificationOutbox.last_error_code: "points_policy_changed",
        NotificationOutbox.completed_at: now,
        NotificationOutbox.lease_owner: None,
        NotificationOutbox.lease_expires_at: None,
    }, synchronize_session=False)

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import auth
from ..database import get_db
from ..models_school import CalendarEvent, ClassSection, HomeworkItem, Membership, StaffAssignment, SubjectGroup, User
from ..school_scope import open_interval_expression, write_audit
from ..family_notifications import enqueue_family_notifications, material_snapshot
from .announcements import (
    _guardian_audience,
    _school_id_from_header,
    _staff_membership,
    _teacher_has_target,
    _teacher_membership,
    _validate_staff_audience,
)
from .homework import _guardian_query as _guardian_homework_query

staff_router = APIRouter()
teacher_router = APIRouter()
guardian_router = APIRouter()

EVENT_TYPES = {"event", "test", "reminder", "trip", "civvies", "charity"}
TEACHER_EVENT_TYPES = {"event", "test", "reminder"}


class CalendarEventCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str | None = Field(default=None, max_length=10000)
    # Kept for backward compatibility and future categorisation. Manual calendar
    # events intentionally use the neutral default rather than exposing taxonomy.
    event_type: str = "event"
    audience_type: str
    class_section_id: int | None = None
    subject_group_id: int | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    all_day: bool = False

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required")
        return value

    @field_validator("body")
    @classmethod
    def clean_body(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("event_type")
    @classmethod
    def valid_event_type(cls, value: str) -> str:
        if value not in EVENT_TYPES:
            raise ValueError("event_type must be one of: " + ", ".join(sorted(EVENT_TYPES)))
        return value

    @field_validator("audience_type")
    @classmethod
    def valid_audience(cls, value: str) -> str:
        if value not in {"school", "class_section", "subject_group"}:
            raise ValueError("audience_type must be school, class_section, or subject_group")
        return value

    @model_validator(mode="after")
    def valid_range(self):
        if self.ends_at is not None and self.starts_at is not None and self.ends_at < self.starts_at:
            raise ValueError("ends_at must not be before starts_at")
        return self


class CalendarEventUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str | None = Field(default=None, max_length=10000)
    event_type: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    all_day: bool = False

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required")
        return value

    @field_validator("body")
    @classmethod
    def clean_body(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("event_type")
    @classmethod
    def valid_event_type(cls, value: str | None) -> str | None:
        if value is not None and value not in EVENT_TYPES:
            raise ValueError("event_type must be one of: " + ", ".join(sorted(EVENT_TYPES)))
        return value

    @model_validator(mode="after")
    def valid_range(self):
        if self.ends_at is not None and self.starts_at is not None and self.ends_at < self.starts_at:
            raise ValueError("ends_at must not be before starts_at")
        return self


def _can_manage_event(db: Session, membership: Membership, event: CalendarEvent) -> bool:
    if event.school_id != membership.school_id:
        return False
    if membership.role == "school_admin":
        return True
    if event.audience_type == "school":
        return False
    if event.author_user_id == membership.user_id:
        return True
    if event.audience_type == "class_section":
        return _teacher_has_target(db, membership, class_section_id=event.class_section_id)
    return _teacher_has_target(db, membership, subject_group_id=event.subject_group_id)


def _assigned_targets(db: Session, membership: Membership) -> tuple[set[int], set[int]]:
    today = datetime.now(timezone.utc).date()
    assignments = db.query(StaffAssignment).filter(
        StaffAssignment.school_id == membership.school_id,
        StaffAssignment.membership_id == membership.id,
        *open_interval_expression(StaffAssignment, today),
    ).all()
    section_ids = {row.class_section_id for row in assignments if row.class_section_id}
    group_ids = {row.subject_group_id for row in assignments if row.subject_group_id}
    return section_ids, group_ids


def _target_context(db: Session, section_ids: set[int], group_ids: set[int]) -> tuple[dict[int, ClassSection], dict[int, SubjectGroup]]:
    sections = {row.id: row for row in db.query(ClassSection).filter(ClassSection.id.in_(section_ids)).all()} if section_ids else {}
    groups = {row.id: row for row in db.query(SubjectGroup).filter(SubjectGroup.id.in_(group_ids)).all()} if group_ids else {}
    return sections, groups


def _event_payload(row: CalendarEvent, sections: dict[int, ClassSection], groups: dict[int, SubjectGroup], *, can_manage: bool | None = None) -> dict[str, Any]:
    payload = {
        "id": f"event-{row.id}",
        "kind": "event",
        "event_id": row.id,
        "school_id": row.school_id,
        "title": row.title,
        "body": row.body,
        "event_type": row.event_type,
        "audience_type": row.audience_type,
        "class_section_id": row.class_section_id,
        "class_section_name": sections.get(row.class_section_id).name if row.class_section_id in sections else None,
        "subject_group_id": row.subject_group_id,
        "subject_group_name": groups.get(row.subject_group_id).name if row.subject_group_id in groups else None,
        "starts_at": row.starts_at,
        "ends_at": row.ends_at,
        "all_day": row.all_day,
        "status": row.status,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
    if can_manage is not None:
        payload["can_manage"] = can_manage
    return payload


def _homework_payload(row: HomeworkItem, sections: dict[int, ClassSection], groups: dict[int, SubjectGroup]) -> dict[str, Any]:
    return {
        "id": f"homework-{row.id}",
        "kind": "homework_due",
        "homework_item_id": row.id,
        "school_id": row.school_id,
        "title": row.title,
        "body": None,
        "event_type": "homework_due",
        "item_type": row.item_type,
        "audience_type": row.audience_type,
        "class_section_id": row.class_section_id,
        "class_section_name": sections.get(row.class_section_id).name if row.class_section_id in sections else None,
        "subject_group_id": row.subject_group_id,
        "subject_group_name": groups.get(row.subject_group_id).name if row.subject_group_id in groups else None,
        "starts_at": row.due_at,
        "ends_at": None,
        "all_day": False,
        "status": row.status,
        "created_at": row.created_at,
    }


def _parse_range(start: str | None, end: str | None) -> tuple[datetime, datetime | None]:
    try:
        start_at = datetime.combine(date.fromisoformat(start), datetime.min.time(), tzinfo=timezone.utc) if start else datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        end_at = datetime.combine(date.fromisoformat(end), datetime.max.time(), tzinfo=timezone.utc) if end else None
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start and end must be YYYY-MM-DD dates")
    if end_at is not None and end_at < start_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end must not be before start")
    # Calendar surfaces are deliberately future-facing.  Keep the API bounded when
    # callers do not supply a range; explicit query parameters still take priority.
    if end_at is None:
        end_at = start_at + timedelta(days=30) - timedelta(microseconds=1)
    return start_at, end_at


def _range_filter(query, column, start_at: datetime, end_at: datetime | None):
    query = query.filter(column >= start_at)
    if end_at is not None:
        query = query.filter(column <= end_at)
    return query


def _sorted_items(items: list[dict[str, Any]], limit: int = 100) -> list[dict[str, Any]]:
    items.sort(key=lambda item: (item["starts_at"], item["id"]))
    return items[:limit]


@staff_router.post("/calendar", status_code=status.HTTP_201_CREATED)
def create_calendar_event(
    payload: CalendarEventCreateRequest,
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    school_id = _school_id_from_header(request.headers)
    membership = _staff_membership(db, current_user, school_id)
    if membership.role != "school_admin" and payload.event_type not in TEACHER_EVENT_TYPES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teachers can only create event, test, or reminder calendar events")
    class_section_id, subject_group_id = _validate_staff_audience(db, school_id, membership, payload)
    event = CalendarEvent(
        school_id=school_id,
        author_user_id=current_user.id,
        title=payload.title,
        body=payload.body,
        event_type=payload.event_type,
        audience_type=payload.audience_type,
        class_section_id=class_section_id,
        subject_group_id=subject_group_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        all_day=payload.all_day,
    )
    db.add(event)
    db.flush()
    enqueue_family_notifications(db, category="calendar", source=event, action="published")
    write_audit(db, current_user.id, "school.calendar_event.created", event, {"event_type": event.event_type, "audience_type": event.audience_type}, school_id=school_id)
    db.commit()
    db.refresh(event)
    sections, groups = _target_context(
        db,
        {event.class_section_id} if event.class_section_id else set(),
        {event.subject_group_id} if event.subject_group_id else set(),
    )
    return _event_payload(event, sections, groups, can_manage=True)


@staff_router.patch("/calendar/{event_id}")
def update_calendar_event(
    event_id: int,
    payload: CalendarEventUpdateRequest,
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    school_id = _school_id_from_header(request.headers)
    membership = _staff_membership(db, current_user, school_id)
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id, CalendarEvent.school_id == school_id).first()
    if not event or not _can_manage_event(db, membership, event):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar event not found")
    if event.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived events cannot be edited")
    if membership.role != "school_admin" and payload.event_type is not None and payload.event_type not in TEACHER_EVENT_TYPES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teachers can only create event, test, or reminder calendar events")
    before = material_snapshot("calendar", event)
    event.title = payload.title
    event.body = payload.body
    if payload.event_type is not None:
        event.event_type = payload.event_type
    event.starts_at = payload.starts_at
    event.ends_at = payload.ends_at
    event.all_day = payload.all_day
    if material_snapshot("calendar", event) != before:
        enqueue_family_notifications(db, category="calendar", source=event, action="updated")
    write_audit(db, current_user.id, "school.calendar_event.updated", event, {"event_type": event.event_type}, school_id=school_id)
    db.commit()
    db.refresh(event)
    sections, groups = _target_context(
        db,
        {event.class_section_id} if event.class_section_id else set(),
        {event.subject_group_id} if event.subject_group_id else set(),
    )
    return _event_payload(event, sections, groups, can_manage=True)


@staff_router.get("/calendar")
def list_staff_calendar(
    request: Request,
    start: str | None = None,
    end: str | None = None,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """School-admin management list; intentionally includes only real events."""
    school_id = _school_id_from_header(request.headers)
    membership = _staff_membership(db, current_user, school_id)
    start_at, end_at = _parse_range(start, end)
    events = _range_filter(
        db.query(CalendarEvent).filter(
            CalendarEvent.school_id == school_id,
            CalendarEvent.status == "active",
        ),
        CalendarEvent.starts_at,
        start_at,
        end_at,
    ).all()
    section_ids = {row.class_section_id for row in events if row.class_section_id}
    group_ids = {row.subject_group_id for row in events if row.subject_group_id}
    sections, groups = _target_context(db, section_ids, group_ids)
    return {"items": _sorted_items([_event_payload(row, sections, groups, can_manage=_can_manage_event(db, membership, row)) for row in events])}


@staff_router.delete("/calendar/{event_id}")
def archive_calendar_event(
    event_id: int,
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    school_id = _school_id_from_header(request.headers)
    membership = _staff_membership(db, current_user, school_id)
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id, CalendarEvent.school_id == school_id).first()
    if not event or not _can_manage_event(db, membership, event):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar event not found")
    event.status = "archived"
    event.archived_at = datetime.now(timezone.utc)
    enqueue_family_notifications(db, category="calendar", source=event, action="cancelled")
    write_audit(db, current_user.id, "school.calendar_event.archived", event, {}, school_id=school_id)
    db.commit()
    return {"status": "archived"}


@teacher_router.get("/calendar")
def list_teacher_calendar(
    request: Request,
    start: str | None = None,
    end: str | None = None,
    class_section_id: int | None = None,
    subject_group_id: int | None = None,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    school_id = _school_id_from_header(request.headers)
    membership = _teacher_membership(db, current_user, school_id)
    start_at, end_at = _parse_range(start, end)
    if class_section_id is not None and subject_group_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose one calendar target")
    section_ids, group_ids = _assigned_targets(db, membership)

    if class_section_id is not None:
        if not _teacher_has_target(db, membership, class_section_id=class_section_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher assignment required")
        section_ids, group_ids = {class_section_id}, set()
    if subject_group_id is not None:
        if not _teacher_has_target(db, membership, subject_group_id=subject_group_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher assignment required")
        section_ids, group_ids = set(), {subject_group_id}

    target_filtered = class_section_id is not None or subject_group_id is not None
    clauses = []
    if not target_filtered:
        clauses.append(CalendarEvent.audience_type == "school")
        clauses.append(CalendarEvent.author_user_id == current_user.id)
    if section_ids:
        clauses.append((CalendarEvent.audience_type == "class_section") & CalendarEvent.class_section_id.in_(section_ids))
    if group_ids:
        clauses.append((CalendarEvent.audience_type == "subject_group") & CalendarEvent.subject_group_id.in_(group_ids))
    event_query = db.query(CalendarEvent).filter(
        CalendarEvent.school_id == school_id,
        CalendarEvent.status == "active",
        or_(*clauses),
    )
    events = _range_filter(event_query, CalendarEvent.starts_at, start_at, end_at).all() if clauses else []

    homework_clauses = []
    if section_ids:
        homework_clauses.append((HomeworkItem.audience_type == "class_section") & HomeworkItem.class_section_id.in_(section_ids))
    if group_ids:
        homework_clauses.append((HomeworkItem.audience_type == "subject_group") & HomeworkItem.subject_group_id.in_(group_ids))
    homework_items = []
    if homework_clauses:
        homework_query = db.query(HomeworkItem).filter(
            HomeworkItem.school_id == school_id,
            HomeworkItem.status == "active",
            HomeworkItem.due_at.is_not(None),
            or_(*homework_clauses),
        )
        homework_items = _range_filter(homework_query, HomeworkItem.due_at, start_at, end_at).all()

    all_section_ids = {row.class_section_id for row in events + homework_items if row.class_section_id}
    all_group_ids = {row.subject_group_id for row in events + homework_items if row.subject_group_id}
    sections, groups = _target_context(db, all_section_ids, all_group_ids)

    def event_can_manage(event: CalendarEvent) -> bool:
        if event.audience_type == "school":
            return False
        if event.author_user_id == current_user.id:
            return True
        if event.audience_type == "class_section":
            return event.class_section_id in section_ids
        return event.subject_group_id in group_ids

    items = [_event_payload(row, sections, groups, can_manage=event_can_manage(row)) for row in events]
    items += [_homework_payload(row, sections, groups) for row in homework_items]
    return {"items": _sorted_items(items)}


@guardian_router.get("/calendar")
def list_guardian_calendar(
    start: str | None = None,
    end: str | None = None,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    start_at, end_at = _parse_range(start, end)
    school_ids, section_ids, group_ids = _guardian_audience(db, current_user)
    if not school_ids:
        return {"items": []}

    clauses = [CalendarEvent.audience_type == "school"]
    if section_ids:
        clauses.append((CalendarEvent.audience_type == "class_section") & CalendarEvent.class_section_id.in_(section_ids))
    if group_ids:
        clauses.append((CalendarEvent.audience_type == "subject_group") & CalendarEvent.subject_group_id.in_(group_ids))
    event_query = db.query(CalendarEvent).filter(
        CalendarEvent.school_id.in_(school_ids),
        CalendarEvent.status == "active",
        or_(*clauses),
    )
    events = _range_filter(event_query, CalendarEvent.starts_at, start_at, end_at).all()

    homework_query = _guardian_homework_query(db, current_user, include_completed=True)
    homework_items = (
        _range_filter(homework_query.filter(HomeworkItem.due_at.is_not(None)), HomeworkItem.due_at, start_at, end_at).all()
        if homework_query is not None
        else []
    )

    all_section_ids = {row.class_section_id for row in events + homework_items if row.class_section_id}
    all_group_ids = {row.subject_group_id for row in events + homework_items if row.subject_group_id}
    sections, groups = _target_context(db, all_section_ids, all_group_ids)

    items = [_event_payload(row, sections, groups) for row in events]
    items += [_homework_payload(row, sections, groups) for row in homework_items]
    return {"items": _sorted_items(items)}

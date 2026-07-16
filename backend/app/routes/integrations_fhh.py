from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import invite_tokens
from ..database import get_db, settings
from ..models_school import (
    Announcement, AnnouncementAttachment, BehaviourCategory, BehaviourEvent, CalendarEvent,
    ClassSection, Enrolment, FhhLink, FhhLinkInvite, GradeLevel, HomeworkAttachment,
    HomeworkItem, School, Student, UpdatePhoto, UpdatePost, User,
)
from ..behaviour_service import event_context_payloads
from ..rosters import resolve_rosters_for_students
from ..school_scope import open_interval_expression, write_audit
from ..security import BoundedInMemoryRateLimiter, get_client_ip_from_scope, is_ip_trusted, parse_ip_networks
from .announcements import _attachment_path
from .homework import _file_response
from .updates import _photo_response
from fastapi.responses import FileResponse
from .guardian import initials_from_name

router = APIRouter()
AUTH_LIMITER = BoundedInMemoryRateLimiter(60, 120)
LINK_LIMITER = BoundedInMemoryRateLimiter(60, 30)
GENERIC_LINK_ERROR = "Link code is unavailable"
GENERIC_ACCESS_ERROR = "Integration access denied"


class CodeRequest(BaseModel):
    code: str = Field(min_length=8, max_length=200)


class ConsumeRequest(CodeRequest):
    fhh_child_ref: str = Field(min_length=1, max_length=200)

    @field_validator("fhh_child_ref")
    @classmethod
    def clean_ref(cls, value: str) -> str:
        return value.strip()


def require_fhh_service(request: Request) -> None:
    if not settings.FHH_INTEGRATION_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")
    client_ip = get_client_ip_from_scope(request.scope)
    if not AUTH_LIMITER.allow(client_ip or "unknown"):
        raise HTTPException(status_code=429, detail=GENERIC_ACCESS_ERROR)
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    expected = settings.FHH_INTEGRATION_SERVICE_TOKEN
    if scheme.lower() != "bearer" or not token or not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail=GENERIC_ACCESS_ERROR, headers={"WWW-Authenticate": "Bearer"})
    networks = parse_ip_networks(settings.FHH_INTEGRATION_ALLOWED_IPS)
    if networks and not is_ip_trusted(client_ip, networks):
        raise HTTPException(status_code=403, detail=GENERIC_ACCESS_ERROR)


def _rate_link(request: Request) -> None:
    if not LINK_LIMITER.allow(get_client_ip_from_scope(request.scope) or "unknown"):
        raise HTTPException(status_code=429, detail=GENERIC_LINK_ERROR)


def _invite(db: Session, code: str, *, lock: bool = False) -> FhhLinkInvite:
    normalized = invite_tokens.normalize_short_code(code)
    query = db.query(FhhLinkInvite).filter(FhhLinkInvite.token_hash == invite_tokens.hash_token(normalized))
    if lock:
        query = query.with_for_update()
    row = query.first()
    now = invite_tokens.now_utc()
    expires_at = row.expires_at.replace(tzinfo=timezone.utc) if row and row.expires_at.tzinfo is None else (row.expires_at if row else None)
    if not row or row.revoked_at is not None or row.consumed_at is not None or expires_at <= now:
        raise HTTPException(status_code=404, detail=GENERIC_LINK_ERROR)
    student = db.query(Student).filter(Student.id == row.student_id, Student.school_id == row.school_id, Student.status == "active").first()
    school = db.query(School).filter(School.id == row.school_id, School.status != "suspended").first()
    if not student or not school:
        raise HTTPException(status_code=404, detail=GENERIC_LINK_ERROR)
    return row


def _snapshot(db: Session, school_id: int, student_id: int) -> dict[str, Any]:
    school = db.query(School).filter(School.id == school_id).one()
    student = db.query(Student).filter(Student.id == student_id).one()
    enrolment = db.query(Enrolment).filter(
        Enrolment.student_id == student_id, Enrolment.class_section_id.is_not(None), Enrolment.kind == "member",
        *open_interval_expression(Enrolment),
    ).order_by(Enrolment.id.desc()).first()
    section = db.query(ClassSection).filter(ClassSection.id == enrolment.class_section_id).first() if enrolment else None
    grade = db.query(GradeLevel).filter(GradeLevel.id == section.grade_level_id).first() if section else None
    display_name = student.preferred_name or f"{student.first_name} {student.last_name}".strip()
    return {
        "school": {"name": school.name, "name_ar": school.name_ar},
        "student": {"display_name": display_name, "first_name": student.first_name, "initials": initials_from_name(student.first_name, student.last_name), "class_section_name": section.name if section else None, "grade_level_name": grade.name if grade else None, "avatar_id": student.avatar_id if isinstance(student.avatar_id, int) and not isinstance(student.avatar_id, bool) else None},
    }


def _link(db: Session, link_id: int, token: str | None) -> FhhLink:
    row = db.query(FhhLink).filter(FhhLink.id == link_id, FhhLink.status == "active", FhhLink.revoked_at.is_(None)).first()
    if not row or not token or not hmac.compare_digest(invite_tokens.hash_token(token), row.link_token_hash):
        raise HTTPException(status_code=404, detail=GENERIC_ACCESS_ERROR)
    return row


@router.post("/link/verify", dependencies=[Depends(require_fhh_service)])
def verify(body: CodeRequest, request: Request, db: Session = Depends(get_db)):
    _rate_link(request); row = _invite(db, body.code)
    return {**_snapshot(db, row.school_id, row.student_id), "expires_at": row.expires_at}


@router.post("/link/consume", dependencies=[Depends(require_fhh_service)])
def consume(body: ConsumeRequest, request: Request, db: Session = Depends(get_db)):
    _rate_link(request)
    try:
        row = _invite(db, body.code, lock=True)
        raw_token = secrets.token_urlsafe(32)
        link = FhhLink(school_id=row.school_id, student_id=row.student_id, source_invite_id=row.id, link_token_hash=invite_tokens.hash_token(raw_token), fhh_child_ref=body.fhh_child_ref)
        db.add(link); db.flush()
        row.consumed_at = invite_tokens.now_utc(); row.consumed_by = body.fhh_child_ref
        write_audit(db, None, "integration.fhh_link.created", link, {"student_id": row.student_id, "source_invite_id": row.id}, school_id=row.school_id)
        db.commit(); db.refresh(link)
    except IntegrityError:
        db.rollback(); raise HTTPException(status_code=404, detail=GENERIC_LINK_ERROR)
    return {"link_id": link.id, "link_token": raw_token, **_snapshot(db, link.school_id, link.student_id), "created_at": link.created_at}


def _scope(db: Session, link: FhhLink):
    today = datetime.now(timezone.utc).date()
    resolution = resolve_rosters_for_students(
        db,
        link.school_id,
        today,
        student_ids=[link.student_id],
    )
    sections = {
        section.id
        for section in resolution.class_sections_by_student.get(link.student_id, [])
    }
    groups = {
        group["id"]
        for group in resolution.subject_groups_by_student.get(link.student_id, [])
        if group.get("id") is not None
    }
    return sections, groups


def _audience(model, school_id: int, sections: set[int], groups: set[int], *, school_wide: bool):
    clauses = [model.audience_type == "school"] if school_wide else []
    if sections: clauses.append((model.audience_type == "class_section") & model.class_section_id.in_(sections))
    if groups: clauses.append((model.audience_type == "subject_group") & model.subject_group_id.in_(groups))
    return [model.school_id == school_id, or_(*clauses)] if clauses else [model.id == -1]


def _linked_announcement(db: Session, link: FhhLink, announcement_id: int) -> Announcement | None:
    sections, groups = _scope(db, link)
    return db.query(Announcement).filter(
        Announcement.id == announcement_id,
        Announcement.status == "published",
        *_audience(Announcement, link.school_id, sections, groups, school_wide=True),
    ).first()


def _linked_homework(db: Session, link: FhhLink, homework_id: int) -> HomeworkItem | None:
    sections, groups = _scope(db, link)
    return db.query(HomeworkItem).filter(
        HomeworkItem.id == homework_id,
        HomeworkItem.status == "active",
        *_audience(HomeworkItem, link.school_id, sections, groups, school_wide=False),
    ).first()


def _linked_update(db: Session, link: FhhLink, update_id: int) -> UpdatePost | None:
    sections, groups = _scope(db, link)
    return db.query(UpdatePost).filter(
        UpdatePost.id == update_id,
        UpdatePost.status == "active",
        *_audience(UpdatePost, link.school_id, sections, groups, school_wide=False),
    ).first()


@router.delete("/links/{link_id}", dependencies=[Depends(require_fhh_service)])
def revoke_link(link_id: int, x_fhh_link_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    link = _link(db, link_id, x_fhh_link_token)
    link.status = "revoked"; link.revoked_at = invite_tokens.now_utc()
    write_audit(db, None, "integration.fhh_link.revoked", link, {"student_id": link.student_id}, school_id=link.school_id)
    db.commit()
    return {"link_id": link.id, "status": "revoked"}


@router.get("/links/{link_id}/dashboard", dependencies=[Depends(require_fhh_service)])
def dashboard(link_id: int, x_fhh_link_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    link = _link(db, link_id, x_fhh_link_token); sections, groups = _scope(db, link)
    snap = _snapshot(db, link.school_id, link.student_id)
    total = db.query(func.coalesce(func.sum(BehaviourEvent.points_delta), 0)).filter(BehaviourEvent.student_id == link.student_id, BehaviourEvent.reversed_at.is_(None)).scalar()
    events = db.query(BehaviourEvent, BehaviourCategory, User).join(BehaviourCategory, BehaviourCategory.id == BehaviourEvent.category_id).outerjoin(User, User.id == BehaviourEvent.actor_user_id).filter(BehaviourEvent.student_id == link.student_id, BehaviourEvent.reversed_at.is_(None)).order_by(BehaviourEvent.created_at.desc(), BehaviourEvent.id.desc()).limit(10).all()
    point_contexts = event_context_payloads(db, [event for event, _category, _actor in events])
    homework = db.query(HomeworkItem).filter(*_audience(HomeworkItem, link.school_id, sections, groups, school_wide=False), HomeworkItem.status == "active").order_by(HomeworkItem.created_at.desc()).limit(100).all()
    hids = [x.id for x in homework]; hats = db.query(HomeworkAttachment).filter(HomeworkAttachment.homework_item_id.in_(hids)).all() if hids else []
    hats_by = {i: [a for a in hats if a.homework_item_id == i] for i in hids}
    announcements = db.query(Announcement).filter(*_audience(Announcement, link.school_id, sections, groups, school_wide=True), Announcement.status == "published").order_by(Announcement.created_at.desc()).limit(20).all()
    aids = [x.id for x in announcements]; aatts = db.query(AnnouncementAttachment).filter(AnnouncementAttachment.post_id.in_(aids)).all() if aids else []
    updates = db.query(UpdatePost).filter(*_audience(UpdatePost, link.school_id, sections, groups, school_wide=False), UpdatePost.status == "active").order_by(UpdatePost.created_at.desc()).limit(50).all()
    uids = [x.id for x in updates]; photos = db.query(UpdatePhoto).filter(UpdatePhoto.post_id.in_(uids)).all() if uids else []
    now = datetime.now(timezone.utc); end = now + timedelta(days=30)
    calendar = db.query(CalendarEvent).filter(*_audience(CalendarEvent, link.school_id, sections, groups, school_wide=True), CalendarEvent.status == "active", CalendarEvent.starts_at >= now, CalendarEvent.starts_at <= end).order_by(CalendarEvent.starts_at).limit(100).all()
    meta = lambda a: {"id": a.id, "original_filename": a.original_filename, "content_type": a.content_type, "size_bytes": a.size_bytes}
    return {
        **snap,
        # Event-time context is purpose-built and display-safe. Never replace
        # it with current enrolment or expose actor/target identifiers.
        "points": {"total": int(total or 0), "recent_events": [{"id": e.id, "category_label": c.label, "category_type": c.type, "points_delta": e.points_delta, "note": e.note, "created_at": e.created_at, "staff_display_name": actor.name if actor else None, **point_contexts[e.id]} for e,c,actor in events]},
        "homework": {"active": [{"id": x.id, "item_type": x.item_type, "title": x.title, "body": x.body, "due_at": x.due_at, "resource_links": x.resource_links, "attachments": [meta(a) for a in hats_by[x.id]], "done": False} for x in homework], "completed": []},
        "announcements": [{"id": x.id, "title": x.title, "body": x.body, "audience_type": x.audience_type, "created_at": x.created_at, "attachments": [meta(a) for a in aatts if a.post_id == x.id]} for x in announcements],
        "updates": [{"id": x.id, "body": x.body, "created_at": x.created_at, "photos": [{"id": p.id, "content_type": p.content_type, "size_bytes": p.size_bytes} for p in photos if p.post_id == x.id]} for x in updates],
        "calendar_upcoming": [{"id": x.id, "kind": "event", "title": x.title, "event_type": x.event_type, "starts_at": x.starts_at, "ends_at": x.ends_at, "all_day": x.all_day} for x in calendar],
        "permissions": {"can_mark_homework_done": False}, "link": {"link_id": link.id, "status": link.status}, "server_time": now,
    }


@router.get("/links/{link_id}/announcements/{announcement_id}/attachments/{attachment_id}/download", dependencies=[Depends(require_fhh_service)])
def download_announcement_attachment(link_id: int, announcement_id: int, attachment_id: int, x_fhh_link_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    link = _link(db, link_id, x_fhh_link_token)
    announcement = _linked_announcement(db, link, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Not found")
    attachment = db.query(AnnouncementAttachment).filter(
        AnnouncementAttachment.id == attachment_id,
        AnnouncementAttachment.post_id == announcement.id,
        AnnouncementAttachment.school_id == link.school_id,
    ).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Not found")
    path = _attachment_path(attachment.storage_key)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_filename)


@router.get("/links/{link_id}/homework/{homework_id}/attachments/{attachment_id}/download", dependencies=[Depends(require_fhh_service)])
def download_homework_attachment(link_id: int, homework_id: int, attachment_id: int, x_fhh_link_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    link = _link(db, link_id, x_fhh_link_token)
    homework = _linked_homework(db, link, homework_id)
    if not homework:
        raise HTTPException(status_code=404, detail="Not found")
    attachment = db.query(HomeworkAttachment).filter(
        HomeworkAttachment.id == attachment_id,
        HomeworkAttachment.homework_item_id == homework.id,
        HomeworkAttachment.school_id == link.school_id,
    ).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Not found")
    return _file_response(attachment)


@router.get("/links/{link_id}/updates/{update_id}/photos/{photo_id}/view", dependencies=[Depends(require_fhh_service)])
def view_update_photo(link_id: int, update_id: int, photo_id: int, x_fhh_link_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    link = _link(db, link_id, x_fhh_link_token)
    update = _linked_update(db, link, update_id)
    if not update:
        raise HTTPException(status_code=404, detail="Not found")
    photo = db.query(UpdatePhoto).filter(
        UpdatePhoto.id == photo_id,
        UpdatePhoto.post_id == update.id,
        UpdatePhoto.school_id == link.school_id,
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Not found")
    return _photo_response(photo)

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import auth
from ..database import get_db
from ..models_school import (
    Announcement,
    AnnouncementAttachment,
    AnnouncementRead,
    ClassSection,
    Enrolment,
    GuardianLink,
    Membership,
    School,
    StaffAssignment,
    SubjectGroup,
    User,
)
from ..rosters import bulk_subject_groups_for_students
from ..school_scope import open_interval_expression, write_audit

staff_router = APIRouter()
teacher_router = APIRouter()
guardian_router = APIRouter()

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENTS_PER_POST = 5
UPLOAD_ROOT = Path(os.environ.get("ANNOUNCEMENT_UPLOAD_DIR", "/app/data/announcement_uploads"))
ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".txt": "text/plain",
    ".csv": "text/csv",
}


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=10000)
    audience_type: str = Field(max_length=40)
    class_section_id: int | None = None
    subject_group_id: int | None = None

    @field_validator("title", "body")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field is required")
        return cleaned

    @field_validator("audience_type")
    @classmethod
    def validate_audience_type(cls, value: str) -> str:
        if value not in {"school", "class_section", "subject_group"}:
            raise ValueError("audience_type must be school, class_section, or subject_group")
        return value


def _school_id_from_header(headers: Any) -> int:
    raw_school_id = headers.get("X-School-Id")
    if raw_school_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School context required")
    try:
        return int(raw_school_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid school context")


def _active_school(db: Session, school_id: int) -> School:
    school = db.query(School).filter(School.id == school_id).first()
    if not school or (school.status or "").lower() == "suspended":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="School access denied")
    return school


def _staff_membership(db: Session, current_user: User, school_id: int) -> Membership:
    _active_school(db, school_id)
    memberships = (
        db.query(Membership)
        .filter(
            Membership.school_id == school_id,
            Membership.user_id == current_user.id,
            Membership.role.in_(["school_admin", "teacher"]),
            Membership.status == "active",
            Membership.revoked_at.is_(None),
        )
        .all()
    )
    if not memberships:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="School staff access required")
    return next((membership for membership in memberships if membership.role == "school_admin"), memberships[0])


def _teacher_membership(db: Session, current_user: User, school_id: int) -> Membership:
    _active_school(db, school_id)
    membership = (
        db.query(Membership)
        .filter(
            Membership.school_id == school_id,
            Membership.user_id == current_user.id,
            Membership.role == "teacher",
            Membership.status == "active",
            Membership.revoked_at.is_(None),
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher access required")
    return membership


def _teacher_has_target(db: Session, membership: Membership, *, class_section_id: int | None = None, subject_group_id: int | None = None) -> bool:
    today = datetime.now(timezone.utc).date()
    query = db.query(StaffAssignment).filter(
        StaffAssignment.school_id == membership.school_id,
        StaffAssignment.membership_id == membership.id,
        *open_interval_expression(StaffAssignment, today),
    )
    if class_section_id is not None:
        query = query.filter(StaffAssignment.class_section_id == class_section_id)
    if subject_group_id is not None:
        query = query.filter(StaffAssignment.subject_group_id == subject_group_id)
    return query.first() is not None


def _validate_staff_audience(db: Session, school_id: int, membership: Membership, payload: AnnouncementCreateRequest) -> tuple[int | None, int | None]:
    class_section_id = payload.class_section_id if payload.audience_type == "class_section" else None
    subject_group_id = payload.subject_group_id if payload.audience_type == "subject_group" else None

    if payload.audience_type == "school":
        if payload.class_section_id is not None or payload.subject_group_id is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="School announcements cannot include a class or subject target")
        if membership.role != "school_admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher assignment required")
        return None, None

    if payload.audience_type == "class_section":
        if class_section_id is None or payload.subject_group_id is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Class section target required")
        target = db.query(ClassSection).filter(ClassSection.id == class_section_id, ClassSection.school_id == school_id).first()
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement target not found")
        if membership.role != "school_admin" and not _teacher_has_target(db, membership, class_section_id=class_section_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher assignment required")
        return class_section_id, None

    if subject_group_id is None or payload.class_section_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject group target required")
    target = db.query(SubjectGroup).filter(SubjectGroup.id == subject_group_id, SubjectGroup.school_id == school_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement target not found")
    if membership.role != "school_admin" and not _teacher_has_target(db, membership, subject_group_id=subject_group_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher assignment required")
    return None, subject_group_id


def _can_manage_announcement(db: Session, membership: Membership, announcement: Announcement) -> bool:
    if announcement.school_id != membership.school_id:
        return False
    if membership.role == "school_admin":
        return True
    if announcement.author_user_id == membership.user_id:
        return True
    if announcement.audience_type == "class_section":
        return _teacher_has_target(db, membership, class_section_id=announcement.class_section_id)
    if announcement.audience_type == "subject_group":
        return _teacher_has_target(db, membership, subject_group_id=announcement.subject_group_id)
    return False


def _teacher_can_manage_announcement(db: Session, membership: Membership, announcement: Announcement) -> bool:
    if announcement.audience_type == "school":
        return False
    return _can_manage_announcement(db, membership, announcement)


def _teacher_manage_query(db: Session, membership: Membership):
    today = datetime.now(timezone.utc).date()
    assignments = db.query(StaffAssignment).filter(
        StaffAssignment.school_id == membership.school_id,
        StaffAssignment.membership_id == membership.id,
        *open_interval_expression(StaffAssignment, today),
    )
    class_section_ids = {
        row[0]
        for row in assignments.with_entities(StaffAssignment.class_section_id).filter(StaffAssignment.class_section_id.is_not(None)).all()
    }
    subject_group_ids = {
        row[0]
        for row in assignments.with_entities(StaffAssignment.subject_group_id).filter(StaffAssignment.subject_group_id.is_not(None)).all()
    }
    clauses = [Announcement.author_user_id == membership.user_id]
    if class_section_ids:
        clauses.append((Announcement.audience_type == "class_section") & Announcement.class_section_id.in_(class_section_ids))
    if subject_group_ids:
        clauses.append((Announcement.audience_type == "subject_group") & Announcement.subject_group_id.in_(subject_group_ids))
    return (
        db.query(Announcement)
        .filter(
            Announcement.school_id == membership.school_id,
            Announcement.audience_type.in_(["class_section", "subject_group"]),
            or_(*clauses),
        )
        .order_by(Announcement.created_at.desc(), Announcement.id.desc())
    )


def _attachment_payload(row: AnnouncementAttachment) -> dict[str, Any]:
    return {
        "id": row.id,
        "original_filename": row.original_filename,
        "content_type": row.content_type,
        "size_bytes": row.size_bytes,
        "created_at": row.created_at,
    }


def _announcement_payload(
    row: Announcement,
    *,
    attachments: list[AnnouncementAttachment] | None = None,
    author: User | None = None,
    section: ClassSection | None = None,
    group: SubjectGroup | None = None,
    school: School | None = None,
    include_body: bool = True,
    is_read: bool | None = None,
) -> dict[str, Any]:
    items = attachments or []
    payload = {
        "id": row.id,
        "school_id": row.school_id,
        "school_name": school.name if school else None,
        "author_name": author.name if author else None,
        "title": row.title,
        "audience_type": row.audience_type,
        "class_section_id": row.class_section_id,
        "class_section_name": section.name if section else None,
        "subject_group_id": row.subject_group_id,
        "subject_group_name": group.name if group else None,
        "status": row.status,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "attachment_count": len(items),
        "attachments": [_attachment_payload(item) for item in items],
    }
    if include_body:
        payload["body"] = row.body
    else:
        payload["preview"] = row.body[:180]
    if is_read is not None:
        payload["is_read"] = is_read
    return payload


def _load_context(db: Session, announcements: list[Announcement]) -> tuple[dict[int, User], dict[int, ClassSection], dict[int, SubjectGroup], dict[int, School]]:
    author_ids = {row.author_user_id for row in announcements}
    section_ids = {row.class_section_id for row in announcements if row.class_section_id is not None}
    group_ids = {row.subject_group_id for row in announcements if row.subject_group_id is not None}
    school_ids = {row.school_id for row in announcements}
    authors = {row.id: row for row in db.query(User).filter(User.id.in_(author_ids)).all()} if author_ids else {}
    sections = {row.id: row for row in db.query(ClassSection).filter(ClassSection.id.in_(section_ids)).all()} if section_ids else {}
    groups = {row.id: row for row in db.query(SubjectGroup).filter(SubjectGroup.id.in_(group_ids)).all()} if group_ids else {}
    schools = {row.id: row for row in db.query(School).filter(School.id.in_(school_ids)).all()} if school_ids else {}
    return authors, sections, groups, schools


def _attachments_by_post(db: Session, post_ids: set[int]) -> dict[int, list[AnnouncementAttachment]]:
    if not post_ids:
        return {}
    rows = (
        db.query(AnnouncementAttachment)
        .filter(AnnouncementAttachment.post_id.in_(post_ids))
        .order_by(AnnouncementAttachment.id.asc())
        .all()
    )
    grouped: dict[int, list[AnnouncementAttachment]] = {}
    for row in rows:
        grouped.setdefault(row.post_id, []).append(row)
    return grouped


def _safe_filename(filename: str | None) -> str:
    base = Path(filename or "attachment").name.strip() or "attachment"
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", base).strip(" .")
    return cleaned[:160] or "attachment"


def _validate_upload_filename(filename: str | None) -> tuple[str, str, str]:
    original = _safe_filename(filename)
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        if ext in {".heic", ".heif"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="iPhone photo format is not supported yet. Please upload JPG, PNG, or WEBP.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attachment type is not allowed")
    return original, ext, ALLOWED_EXTENSIONS[ext]


def _attachment_path(storage_key: str) -> Path:
    root = UPLOAD_ROOT.resolve()
    path = (root / storage_key).resolve()
    if root != path and root not in path.parents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return path


async def _store_upload(db: Session, announcement: Announcement, current_user: User, file: UploadFile) -> AnnouncementAttachment:
    existing_count = db.query(AnnouncementAttachment).filter(AnnouncementAttachment.post_id == announcement.id).count()
    if existing_count >= MAX_ATTACHMENTS_PER_POST:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Too many attachments")

    original, ext, content_type = _validate_upload_filename(file.filename)
    content = await file.read(MAX_ATTACHMENT_BYTES + 1)
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attachment is too large")
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attachment is empty")

    storage_key = f"school-{announcement.school_id}/announcement-{announcement.id}/{uuid.uuid4().hex}{ext}"
    path = _attachment_path(storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

    attachment = AnnouncementAttachment(
        post_id=announcement.id,
        school_id=announcement.school_id,
        uploaded_by_user_id=current_user.id,
        original_filename=original,
        storage_key=storage_key,
        content_type=content_type,
        size_bytes=len(content),
    )
    db.add(attachment)
    db.flush()
    write_audit(
        db,
        current_user.id,
        "school.announcement.attachment_uploaded",
        attachment,
        {"post_id": announcement.id, "filename": original, "size_bytes": len(content)},
        school_id=announcement.school_id,
    )
    return attachment


def _guardian_audience(db: Session, current_user: User) -> tuple[set[int], set[int], set[int]]:
    links = (
        db.query(GuardianLink)
        .filter(
            GuardianLink.user_id == current_user.id,
            GuardianLink.status == "active",
            GuardianLink.revoked_at.is_(None),
        )
        .all()
    )
    student_ids = {link.student_id for link in links}
    school_ids = {link.school_id for link in links}
    if not student_ids:
        return set(), set(), set()

    today = datetime.now(timezone.utc).date()
    enrolments = (
        db.query(Enrolment)
        .filter(
            Enrolment.student_id.in_(student_ids),
            Enrolment.kind == "member",
            *open_interval_expression(Enrolment, today),
        )
        .all()
    )
    class_section_ids = {row.class_section_id for row in enrolments if row.class_section_id is not None}
    subject_group_ids = {row.subject_group_id for row in enrolments if row.subject_group_id is not None}

    for school_id in school_ids:
        grouped = bulk_subject_groups_for_students(db, school_id, today)
        for student_id in student_ids:
            for group in grouped.get(student_id, []):
                if group.get("id") is not None:
                    subject_group_ids.add(group["id"])

    return school_ids, class_section_ids, subject_group_ids


def _guardian_query(db: Session, current_user: User):
    school_ids, class_section_ids, subject_group_ids = _guardian_audience(db, current_user)
    if not school_ids:
        return None
    clauses = [Announcement.audience_type == "school"]
    if class_section_ids:
        clauses.append((Announcement.audience_type == "class_section") & Announcement.class_section_id.in_(class_section_ids))
    if subject_group_ids:
        clauses.append((Announcement.audience_type == "subject_group") & Announcement.subject_group_id.in_(subject_group_ids))
    return (
        db.query(Announcement)
        .filter(
            Announcement.school_id.in_(school_ids),
            Announcement.status == "published",
            or_(*clauses),
        )
        .order_by(Announcement.created_at.desc(), Announcement.id.desc())
    )


def _guardian_announcement_or_404(db: Session, current_user: User, announcement_id: int) -> Announcement:
    query = _guardian_query(db, current_user)
    announcement = query.filter(Announcement.id == announcement_id).first() if query is not None else None
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    return announcement


def _read_announcement_ids(db: Session, current_user: User, announcement_ids: set[int]) -> set[int]:
    if not announcement_ids:
        return set()
    rows = (
        db.query(AnnouncementRead.announcement_id)
        .filter(AnnouncementRead.user_id == current_user.id, AnnouncementRead.announcement_id.in_(announcement_ids))
        .all()
    )
    return {row[0] for row in rows}


def _mark_announcement_read(db: Session, current_user: User, announcement: Announcement) -> None:
    existing = (
        db.query(AnnouncementRead)
        .filter(AnnouncementRead.announcement_id == announcement.id, AnnouncementRead.user_id == current_user.id)
        .first()
    )
    if existing:
        return
    db.add(
        AnnouncementRead(
            announcement_id=announcement.id,
            user_id=current_user.id,
            school_id=announcement.school_id,
        )
    )
    db.commit()


@staff_router.get("/announcements")
def list_staff_announcements(
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    school_id = _school_id_from_header(request.headers)
    membership = _staff_membership(db, current_user, school_id)
    query = db.query(Announcement).filter(Announcement.school_id == school_id).order_by(Announcement.created_at.desc(), Announcement.id.desc())
    if membership.role != "school_admin":
        query = query.filter(Announcement.author_user_id == current_user.id)
    announcements = query.limit(100).all()
    attachments = _attachments_by_post(db, {row.id for row in announcements})
    authors, sections, groups, schools = _load_context(db, announcements)
    return {
        "announcements": [
            _announcement_payload(
                row,
                attachments=attachments.get(row.id, []),
                author=authors.get(row.author_user_id),
                section=sections.get(row.class_section_id),
                group=groups.get(row.subject_group_id),
                school=schools.get(row.school_id),
            )
            for row in announcements
        ]
    }


@teacher_router.get("/announcements")
def list_teacher_announcements(
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    school_id = _school_id_from_header(request.headers)
    membership = _teacher_membership(db, current_user, school_id)
    announcements = _teacher_manage_query(db, membership).limit(100).all()
    attachments = _attachments_by_post(db, {row.id for row in announcements})
    authors, sections, groups, schools = _load_context(db, announcements)
    return {
        "announcements": [
            _announcement_payload(
                row,
                attachments=attachments.get(row.id, []),
                author=authors.get(row.author_user_id),
                section=sections.get(row.class_section_id),
                group=groups.get(row.subject_group_id),
                school=schools.get(row.school_id),
            )
            for row in announcements
        ]
    }


@staff_router.post("/announcements", status_code=status.HTTP_201_CREATED)
def create_staff_announcement(
    payload: AnnouncementCreateRequest,
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    school_id = _school_id_from_header(request.headers)
    membership = _staff_membership(db, current_user, school_id)
    class_section_id, subject_group_id = _validate_staff_audience(db, school_id, membership, payload)
    announcement = Announcement(
        school_id=school_id,
        author_user_id=current_user.id,
        title=payload.title,
        body=payload.body,
        audience_type=payload.audience_type,
        class_section_id=class_section_id,
        subject_group_id=subject_group_id,
        status="published",
    )
    db.add(announcement)
    db.flush()
    write_audit(
        db,
        current_user.id,
        "school.announcement.created",
        announcement,
        {"audience_type": payload.audience_type, "class_section_id": class_section_id, "subject_group_id": subject_group_id},
        school_id=school_id,
    )
    db.commit()
    db.refresh(announcement)
    authors, sections, groups, schools = _load_context(db, [announcement])
    return _announcement_payload(
        announcement,
        attachments=[],
        author=authors.get(announcement.author_user_id),
        section=sections.get(announcement.class_section_id),
        group=groups.get(announcement.subject_group_id),
        school=schools.get(announcement.school_id),
    )


@staff_router.post("/announcements/{announcement_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_staff_attachment(
    announcement_id: int,
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    school_id = _school_id_from_header(request.headers)
    membership = _staff_membership(db, current_user, school_id)
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id, Announcement.school_id == school_id).first()
    if not announcement or not _can_manage_announcement(db, membership, announcement):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    attachment = await _store_upload(db, announcement, current_user, file)
    db.commit()
    db.refresh(attachment)
    return _attachment_payload(attachment)


@teacher_router.post("/announcements/{announcement_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_teacher_attachment(
    announcement_id: int,
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    school_id = _school_id_from_header(request.headers)
    membership = _teacher_membership(db, current_user, school_id)
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id, Announcement.school_id == school_id).first()
    if not announcement or not _teacher_can_manage_announcement(db, membership, announcement):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    attachment = await _store_upload(db, announcement, current_user, file)
    db.commit()
    db.refresh(attachment)
    return _attachment_payload(attachment)


@staff_router.delete("/announcements/{announcement_id}")
def archive_staff_announcement(
    announcement_id: int,
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    school_id = _school_id_from_header(request.headers)
    membership = _staff_membership(db, current_user, school_id)
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id, Announcement.school_id == school_id).first()
    if not announcement or not _can_manage_announcement(db, membership, announcement):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    announcement.status = "archived"
    write_audit(db, current_user.id, "school.announcement.archived", announcement, {}, school_id=school_id)
    db.commit()
    return {"status": "archived"}


@teacher_router.delete("/announcements/{announcement_id}")
def archive_teacher_announcement(
    announcement_id: int,
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    school_id = _school_id_from_header(request.headers)
    membership = _teacher_membership(db, current_user, school_id)
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id, Announcement.school_id == school_id).first()
    if not announcement or not _teacher_can_manage_announcement(db, membership, announcement):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    announcement.status = "archived"
    write_audit(db, current_user.id, "school.announcement.archived", announcement, {}, school_id=school_id)
    db.commit()
    return {"status": "archived"}


@staff_router.get("/announcements/{announcement_id}/attachments/{attachment_id}/download")
def download_staff_attachment(
    announcement_id: int,
    attachment_id: int,
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    school_id = _school_id_from_header(request.headers)
    membership = _staff_membership(db, current_user, school_id)
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id, Announcement.school_id == school_id).first()
    if not announcement or not _can_manage_announcement(db, membership, announcement):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    attachment = (
        db.query(AnnouncementAttachment)
        .filter(AnnouncementAttachment.id == attachment_id, AnnouncementAttachment.post_id == announcement_id, AnnouncementAttachment.school_id == school_id)
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    path = _attachment_path(attachment.storage_key)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_filename)


@teacher_router.get("/announcements/{announcement_id}/attachments/{attachment_id}/download")
def download_teacher_attachment(
    announcement_id: int,
    attachment_id: int,
    request: Request,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    school_id = _school_id_from_header(request.headers)
    membership = _teacher_membership(db, current_user, school_id)
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id, Announcement.school_id == school_id).first()
    if not announcement or not _teacher_can_manage_announcement(db, membership, announcement):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    attachment = (
        db.query(AnnouncementAttachment)
        .filter(AnnouncementAttachment.id == attachment_id, AnnouncementAttachment.post_id == announcement_id, AnnouncementAttachment.school_id == school_id)
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    path = _attachment_path(attachment.storage_key)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_filename)


@guardian_router.get("/announcements")
def list_guardian_announcements(
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    query = _guardian_query(db, current_user)
    all_ids = {row.id for row in query.with_entities(Announcement.id).all()} if query is not None else set()
    read_ids = _read_announcement_ids(db, current_user, all_ids)
    unread_count = len(all_ids) - len(read_ids)

    announcements = query.limit(100).all() if query is not None else []
    attachments = _attachments_by_post(db, {row.id for row in announcements})
    authors, sections, groups, schools = _load_context(db, announcements)
    return {
        "unread_count": unread_count,
        "announcements": [
            _announcement_payload(
                row,
                attachments=attachments.get(row.id, []),
                author=authors.get(row.author_user_id),
                section=sections.get(row.class_section_id),
                group=groups.get(row.subject_group_id),
                school=schools.get(row.school_id),
                include_body=False,
                is_read=row.id in read_ids,
            )
            for row in announcements
        ],
    }


@guardian_router.get("/announcements/{announcement_id}")
def get_guardian_announcement(
    announcement_id: int,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    announcement = _guardian_announcement_or_404(db, current_user, announcement_id)
    _mark_announcement_read(db, current_user, announcement)
    attachments = _attachments_by_post(db, {announcement.id})
    authors, sections, groups, schools = _load_context(db, [announcement])
    return _announcement_payload(
        announcement,
        attachments=attachments.get(announcement.id, []),
        author=authors.get(announcement.author_user_id),
        section=sections.get(announcement.class_section_id),
        group=groups.get(announcement.subject_group_id),
        school=schools.get(announcement.school_id),
        is_read=True,
    )


@guardian_router.get("/announcements/{announcement_id}/attachments/{attachment_id}/download")
def download_guardian_attachment(
    announcement_id: int,
    attachment_id: int,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    announcement = _guardian_announcement_or_404(db, current_user, announcement_id)
    attachment = (
        db.query(AnnouncementAttachment)
        .filter(
            AnnouncementAttachment.id == attachment_id,
            AnnouncementAttachment.post_id == announcement_id,
            AnnouncementAttachment.school_id == announcement.school_id,
        )
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    path = _attachment_path(attachment.storage_key)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_filename)

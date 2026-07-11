from __future__ import annotations

import ipaddress
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import auth
from ..database import get_db
from ..models_school import ClassSection, HomeworkAttachment, HomeworkItem, HomeworkItemCompletion, StaffAssignment, SubjectGroup, User
from ..school_scope import open_interval_expression, write_audit
from .announcements import (
    MAX_ATTACHMENTS_PER_POST,
    MAX_ATTACHMENT_BYTES,
    _guardian_audience,
    _school_id_from_header,
    _teacher_has_target,
    _teacher_membership,
    _validate_upload_filename,
)

teacher_router = APIRouter()
guardian_router = APIRouter()
UPLOAD_ROOT = Path(os.environ.get("HOMEWORK_UPLOAD_DIR", "/app/data/homework_uploads"))


class HomeworkCreateRequest(BaseModel):
    item_type: str
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=10000)
    audience_type: str
    class_section_id: int | None = None
    subject_group_id: int | None = None
    due_at: datetime | None = None
    resource_links: list["ResourceLink"] = Field(default_factory=list, max_length=5)

    @field_validator("title", "body")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required")
        return value

    @field_validator("item_type")
    @classmethod
    def valid_item_type(cls, value: str) -> str:
        if value not in {"homework", "diary"}:
            raise ValueError("item_type must be homework or diary")
        return value

    @field_validator("audience_type")
    @classmethod
    def valid_audience(cls, value: str) -> str:
        if value not in {"class_section", "subject_group"}:
            raise ValueError("audience_type must be class_section or subject_group")
        return value


class HomeworkUpdateRequest(BaseModel):
    item_type: str
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=10000)
    due_at: datetime | None = None
    resource_links: list["ResourceLink"] = Field(default_factory=list, max_length=5)

    @field_validator("title", "body")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required")
        return value

    @field_validator("item_type")
    @classmethod
    def valid_item_type(cls, value: str) -> str:
        if value not in {"homework", "diary"}:
            raise ValueError("item_type must be homework or diary")
        return value


class ResourceLink(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    label: str | None = Field(default=None, max_length=160)

    @field_validator("url")
    @classmethod
    def valid_safe_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Resource link must be a public HTTPS URL")
        hostname = parsed.hostname.lower().rstrip(".")
        if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
            raise ValueError("Resource link must be a public HTTPS URL")
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            address = None
        if address and not address.is_global:
            raise ValueError("Resource link must be a public HTTPS URL")
        return value

    @field_validator("label")
    @classmethod
    def clean_label(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


HomeworkCreateRequest.model_rebuild()
HomeworkUpdateRequest.model_rebuild()


def _validate_target(db: Session, school_id: int, membership, payload: HomeworkCreateRequest):
    if payload.audience_type == "class_section":
        if payload.class_section_id is None or payload.subject_group_id is not None:
            raise HTTPException(status_code=400, detail="Class section target required")
        target = db.query(ClassSection).filter(ClassSection.id == payload.class_section_id, ClassSection.school_id == school_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Homework target not found")
        if not _teacher_has_target(db, membership, class_section_id=target.id):
            raise HTTPException(status_code=403, detail="Teacher assignment required")
        return target.id, None
    if payload.subject_group_id is None or payload.class_section_id is not None:
        raise HTTPException(status_code=400, detail="Subject group target required")
    target = db.query(SubjectGroup).filter(SubjectGroup.id == payload.subject_group_id, SubjectGroup.school_id == school_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Homework target not found")
    if not _teacher_has_target(db, membership, subject_group_id=target.id):
        raise HTTPException(status_code=403, detail="Teacher assignment required")
    return None, target.id


def _can_manage(db: Session, membership, item: HomeworkItem) -> bool:
    if item.school_id != membership.school_id:
        return False
    if item.author_user_id == membership.user_id:
        return True
    if item.audience_type == "class_section":
        return _teacher_has_target(db, membership, class_section_id=item.class_section_id)
    return _teacher_has_target(db, membership, subject_group_id=item.subject_group_id)


def _teacher_query(db: Session, membership):
    assignments = db.query(StaffAssignment).filter(
        StaffAssignment.school_id == membership.school_id,
        StaffAssignment.membership_id == membership.id,
        *open_interval_expression(StaffAssignment, datetime.now(timezone.utc).date()),
    ).all()
    section_ids = {row.class_section_id for row in assignments if row.class_section_id}
    group_ids = {row.subject_group_id for row in assignments if row.subject_group_id}
    clauses = [HomeworkItem.author_user_id == membership.user_id]
    if section_ids:
        clauses.append((HomeworkItem.audience_type == "class_section") & HomeworkItem.class_section_id.in_(section_ids))
    if group_ids:
        clauses.append((HomeworkItem.audience_type == "subject_group") & HomeworkItem.subject_group_id.in_(group_ids))
    return db.query(HomeworkItem).filter(HomeworkItem.school_id == membership.school_id, or_(*clauses))


def _attachment_payload(row: HomeworkAttachment) -> dict[str, Any]:
    return {"id": row.id, "original_filename": row.original_filename, "content_type": row.content_type, "size_bytes": row.size_bytes, "created_at": row.created_at}


def _context(db: Session, items: list[HomeworkItem]):
    section_ids = {row.class_section_id for row in items if row.class_section_id}
    group_ids = {row.subject_group_id for row in items if row.subject_group_id}
    sections = {row.id: row for row in db.query(ClassSection).filter(ClassSection.id.in_(section_ids)).all()} if section_ids else {}
    groups = {row.id: row for row in db.query(SubjectGroup).filter(SubjectGroup.id.in_(group_ids)).all()} if group_ids else {}
    item_ids = {row.id for row in items}
    attachments: dict[int, list[HomeworkAttachment]] = {}
    if item_ids:
        for row in db.query(HomeworkAttachment).filter(HomeworkAttachment.homework_item_id.in_(item_ids)).order_by(HomeworkAttachment.id).all():
            attachments.setdefault(row.homework_item_id, []).append(row)
    return sections, groups, attachments


def _payload(row: HomeworkItem, sections, groups, attachments, *, include_body=True):
    files = attachments.get(row.id, [])
    result = {
        "id": row.id, "school_id": row.school_id, "item_type": row.item_type, "title": row.title,
        "audience_type": row.audience_type, "class_section_id": row.class_section_id,
        "class_section_name": sections.get(row.class_section_id).name if row.class_section_id in sections else None,
        "subject_group_id": row.subject_group_id,
        "subject_group_name": groups.get(row.subject_group_id).name if row.subject_group_id in groups else None,
        "due_at": row.due_at, "status": row.status, "created_at": row.created_at, "updated_at": row.updated_at,
        "attachment_count": len(files), "attachments": [_attachment_payload(file) for file in files],
        "resource_links": row.resource_links or [],
    }
    result["body" if include_body else "preview"] = row.body if include_body else row.body[:180]
    return result


def _path(storage_key: str) -> Path:
    root = UPLOAD_ROOT.resolve()
    path = (root / storage_key).resolve()
    if root != path and root not in path.parents:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return path


def _file_response(attachment: HomeworkAttachment):
    path = _path(attachment.storage_key)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_filename)


def _guardian_query(db: Session, current_user: User, *, include_completed: bool = False, only_completed: bool = False):
    school_ids, section_ids, group_ids = _guardian_audience(db, current_user)
    clauses = []
    if section_ids:
        clauses.append((HomeworkItem.audience_type == "class_section") & HomeworkItem.class_section_id.in_(section_ids))
    if group_ids:
        clauses.append((HomeworkItem.audience_type == "subject_group") & HomeworkItem.subject_group_id.in_(group_ids))
    if not school_ids or not clauses:
        return None
    query = db.query(HomeworkItem).filter(HomeworkItem.school_id.in_(school_ids), HomeworkItem.status == "active", or_(*clauses))
    completed_ids = db.query(HomeworkItemCompletion.homework_item_id).filter(HomeworkItemCompletion.guardian_user_id == current_user.id)
    if only_completed:
        query = query.filter(HomeworkItem.id.in_(completed_ids))
    elif not include_completed:
        query = query.filter(~HomeworkItem.id.in_(completed_ids))
    return query


def _guardian_item(db: Session, current_user: User, item_id: int, *, include_completed: bool = False):
    query = _guardian_query(db, current_user, include_completed=include_completed)
    item = query.filter(HomeworkItem.id == item_id).first() if query is not None else None
    if not item:
        raise HTTPException(status_code=404, detail="Homework item not found")
    return item


@teacher_router.get("/homework")
def list_teacher_homework(request: Request, class_section_id: int | None = None, subject_group_id: int | None = None, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers)
    membership = _teacher_membership(db, current_user, school_id)
    query = _teacher_query(db, membership)
    if class_section_id is not None and subject_group_id is not None:
        raise HTTPException(status_code=400, detail="Choose one homework audience")
    if class_section_id is not None:
        if not _teacher_has_target(db, membership, class_section_id=class_section_id): raise HTTPException(status_code=403, detail="Teacher assignment required")
        query = query.filter(HomeworkItem.class_section_id == class_section_id)
    if subject_group_id is not None:
        if not _teacher_has_target(db, membership, subject_group_id=subject_group_id): raise HTTPException(status_code=403, detail="Teacher assignment required")
        query = query.filter(HomeworkItem.subject_group_id == subject_group_id)
    items = query.order_by(HomeworkItem.created_at.desc(), HomeworkItem.id.desc()).limit(100).all()
    sections, groups, attachments = _context(db, items)
    return {"items": [_payload(row, sections, groups, attachments) for row in items]}


@teacher_router.post("/homework", status_code=status.HTTP_201_CREATED)
def create_homework(payload: HomeworkCreateRequest, request: Request, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers)
    membership = _teacher_membership(db, current_user, school_id)
    section_id, group_id = _validate_target(db, school_id, membership, payload)
    item = HomeworkItem(school_id=school_id, author_user_id=current_user.id, item_type=payload.item_type, title=payload.title, body=payload.body, audience_type=payload.audience_type, class_section_id=section_id, subject_group_id=group_id, due_at=payload.due_at, resource_links=[link.model_dump() for link in payload.resource_links])
    db.add(item); db.flush()
    write_audit(db, current_user.id, "school.homework.created", item, {"item_type": item.item_type, "audience_type": item.audience_type}, school_id=school_id)
    db.commit(); db.refresh(item)
    sections, groups, attachments = _context(db, [item])
    return _payload(item, sections, groups, attachments)


@teacher_router.post("/homework/{item_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(item_id: int, request: Request, file: UploadFile = File(...), current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers)
    membership = _teacher_membership(db, current_user, school_id)
    item = db.query(HomeworkItem).filter(HomeworkItem.id == item_id, HomeworkItem.school_id == school_id).first()
    if not item or not _can_manage(db, membership, item):
        raise HTTPException(status_code=404, detail="Homework item not found")
    if db.query(HomeworkAttachment).filter(HomeworkAttachment.homework_item_id == item.id).count() >= MAX_ATTACHMENTS_PER_POST:
        raise HTTPException(status_code=400, detail="Too many attachments")
    original, ext, content_type = _validate_upload_filename(file.filename)
    content = await file.read(MAX_ATTACHMENT_BYTES + 1)
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=400, detail="Attachment is too large")
    if not content:
        raise HTTPException(status_code=400, detail="Attachment is empty")
    storage_key = f"school-{school_id}/homework-{item.id}/{uuid.uuid4().hex}{ext}"
    path = _path(storage_key); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(content)
    attachment = HomeworkAttachment(homework_item_id=item.id, school_id=school_id, uploaded_by_user_id=current_user.id, original_filename=original, storage_key=storage_key, content_type=content_type, size_bytes=len(content))
    db.add(attachment); db.flush()
    write_audit(db, current_user.id, "school.homework.attachment_uploaded", attachment, {"homework_item_id": item.id, "filename": original, "size_bytes": len(content)}, school_id=school_id)
    db.commit(); db.refresh(attachment)
    return _attachment_payload(attachment)


@teacher_router.delete("/homework/{item_id}")
def archive_homework(item_id: int, request: Request, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers)
    membership = _teacher_membership(db, current_user, school_id)
    item = db.query(HomeworkItem).filter(HomeworkItem.id == item_id, HomeworkItem.school_id == school_id).first()
    if not item or not _can_manage(db, membership, item):
        raise HTTPException(status_code=404, detail="Homework item not found")
    item.status = "archived"; item.archived_at = datetime.now(timezone.utc)
    write_audit(db, current_user.id, "school.homework.archived", item, {}, school_id=school_id); db.commit()
    return {"status": "archived"}


@teacher_router.patch("/homework/{item_id}")
def update_homework(item_id: int, payload: HomeworkUpdateRequest, request: Request, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers)
    membership = _teacher_membership(db, current_user, school_id)
    item = db.query(HomeworkItem).filter(HomeworkItem.id == item_id, HomeworkItem.school_id == school_id).first()
    if not item or not _can_manage(db, membership, item):
        raise HTTPException(status_code=404, detail="Homework item not found")
    if item.status != "active":
        raise HTTPException(status_code=409, detail="Archived items cannot be edited")
    item.item_type = payload.item_type; item.title = payload.title; item.body = payload.body
    item.due_at = payload.due_at; item.resource_links = [link.model_dump() for link in payload.resource_links]
    write_audit(db, current_user.id, "school.homework.updated", item, {"item_type": item.item_type}, school_id=school_id)
    db.commit(); db.refresh(item)
    sections, groups, attachments = _context(db, [item])
    return _payload(item, sections, groups, attachments)


@teacher_router.get("/homework/{item_id}")
def teacher_detail(item_id: int, request: Request, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers); membership = _teacher_membership(db, current_user, school_id)
    item = db.query(HomeworkItem).filter(HomeworkItem.id == item_id, HomeworkItem.school_id == school_id).first()
    if not item or not _can_manage(db, membership, item): raise HTTPException(status_code=404, detail="Homework item not found")
    sections, groups, attachments = _context(db, [item]); return _payload(item, sections, groups, attachments)


@teacher_router.get("/homework/{item_id}/attachments/{attachment_id}/download")
def teacher_download(item_id: int, attachment_id: int, request: Request, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers); membership = _teacher_membership(db, current_user, school_id)
    item = db.query(HomeworkItem).filter(HomeworkItem.id == item_id, HomeworkItem.school_id == school_id).first()
    if not item or not _can_manage(db, membership, item): raise HTTPException(status_code=404, detail="Attachment not found")
    attachment = db.query(HomeworkAttachment).filter(HomeworkAttachment.id == attachment_id, HomeworkAttachment.homework_item_id == item.id, HomeworkAttachment.school_id == school_id).first()
    if not attachment: raise HTTPException(status_code=404, detail="Attachment not found")
    return _file_response(attachment)


@guardian_router.get("/homework")
def guardian_list(status: str | None = None, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if status not in (None, "active", "completed"):
        raise HTTPException(status_code=400, detail="status must be active or completed")
    query = _guardian_query(db, current_user, only_completed=status == "completed")
    items = query.order_by(HomeworkItem.created_at.desc(), HomeworkItem.id.desc()).limit(100).all() if query is not None else []
    sections, groups, attachments = _context(db, items)
    return {"items": [_payload(row, sections, groups, attachments, include_body=False) for row in items], "count": len(items)}


@guardian_router.get("/homework/{item_id}")
def guardian_detail(item_id: int, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    item = _guardian_item(db, current_user, item_id, include_completed=True); sections, groups, attachments = _context(db, [item])
    return _payload(item, sections, groups, attachments)


@guardian_router.get("/homework/{item_id}/attachments/{attachment_id}/download")
def guardian_download(item_id: int, attachment_id: int, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    item = _guardian_item(db, current_user, item_id, include_completed=True)
    attachment = db.query(HomeworkAttachment).filter(HomeworkAttachment.id == attachment_id, HomeworkAttachment.homework_item_id == item.id, HomeworkAttachment.school_id == item.school_id).first()
    if not attachment: raise HTTPException(status_code=404, detail="Attachment not found")
    return _file_response(attachment)


@guardian_router.post("/homework/{item_id}/done", status_code=status.HTTP_201_CREATED)
def guardian_done(item_id: int, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    item = _guardian_item(db, current_user, item_id, include_completed=True)
    completion = db.query(HomeworkItemCompletion).filter(HomeworkItemCompletion.homework_item_id == item.id, HomeworkItemCompletion.guardian_user_id == current_user.id).first()
    if completion is None:
        completion = HomeworkItemCompletion(homework_item_id=item.id, school_id=item.school_id, guardian_user_id=current_user.id)
        db.add(completion); db.commit()
    return {"status": "done"}


@guardian_router.delete("/homework/{item_id}/done")
def guardian_not_done(item_id: int, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    item = _guardian_item(db, current_user, item_id, include_completed=True)
    completion = db.query(HomeworkItemCompletion).filter(HomeworkItemCompletion.homework_item_id == item.id, HomeworkItemCompletion.guardian_user_id == current_user.id).first()
    if completion is not None:
        db.delete(completion); db.commit()
    return {"status": "not_done"}

from __future__ import annotations

import os
import uuid
import logging
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
from ..models_school import ClassSection, StaffAssignment, SubjectGroup, UpdatePhoto, UpdatePost, User
from ..school_scope import open_interval_expression, write_audit
from ..family_notifications import enqueue_family_notifications
from .announcements import (
    _guardian_audience,
    _safe_filename,
    _school_id_from_header,
    _teacher_has_target,
    _teacher_membership,
)
from ..update_image_service import (
    MAX_RAW_IMAGE_BYTES,
    create_update_thumbnail,
    optimise_update_photo,
)

teacher_router = APIRouter()
guardian_router = APIRouter()
logger = logging.getLogger(__name__)
UPLOAD_ROOT = Path(os.environ.get("UPDATE_UPLOAD_DIR", "/app/data/update_uploads"))
MAX_PHOTOS_PER_POST = 5


class UpdateCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    audience_type: str
    class_section_id: int | None = None
    subject_group_id: int | None = None

    @field_validator("body")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required")
        return value

    @field_validator("audience_type")
    @classmethod
    def valid_audience(cls, value: str) -> str:
        if value not in {"class_section", "subject_group"}:
            raise ValueError("audience_type must be class_section or subject_group")
        return value


class UpdateEditRequest(BaseModel):
    body: str = Field(min_length=1, max_length=10000)

    @field_validator("body")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required")
        return value


def _validate_target(db: Session, school_id: int, membership, payload: UpdateCreateRequest):
    if payload.audience_type == "class_section":
        if payload.class_section_id is None or payload.subject_group_id is not None:
            raise HTTPException(status_code=400, detail="Class section target required")
        target = db.query(ClassSection).filter(ClassSection.id == payload.class_section_id, ClassSection.school_id == school_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Update target not found")
        if not _teacher_has_target(db, membership, class_section_id=target.id):
            raise HTTPException(status_code=403, detail="Teacher assignment required")
        return target.id, None
    if payload.subject_group_id is None or payload.class_section_id is not None:
        raise HTTPException(status_code=400, detail="Subject group target required")
    target = db.query(SubjectGroup).filter(SubjectGroup.id == payload.subject_group_id, SubjectGroup.school_id == school_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Update target not found")
    if not _teacher_has_target(db, membership, subject_group_id=target.id):
        raise HTTPException(status_code=403, detail="Teacher assignment required")
    return None, target.id


def _can_manage(db: Session, membership, post: UpdatePost) -> bool:
    if post.school_id != membership.school_id:
        return False
    if post.author_user_id == membership.user_id:
        return True
    if post.audience_type == "class_section":
        return _teacher_has_target(db, membership, class_section_id=post.class_section_id)
    return _teacher_has_target(db, membership, subject_group_id=post.subject_group_id)


def _teacher_query(db: Session, membership):
    assignments = db.query(StaffAssignment).filter(
        StaffAssignment.school_id == membership.school_id,
        StaffAssignment.membership_id == membership.id,
        *open_interval_expression(StaffAssignment, datetime.now(timezone.utc).date()),
    ).all()
    section_ids = {row.class_section_id for row in assignments if row.class_section_id}
    group_ids = {row.subject_group_id for row in assignments if row.subject_group_id}
    clauses = [UpdatePost.author_user_id == membership.user_id]
    if section_ids:
        clauses.append((UpdatePost.audience_type == "class_section") & UpdatePost.class_section_id.in_(section_ids))
    if group_ids:
        clauses.append((UpdatePost.audience_type == "subject_group") & UpdatePost.subject_group_id.in_(group_ids))
    return db.query(UpdatePost).filter(UpdatePost.school_id == membership.school_id, or_(*clauses))


def _photo_payload(row: UpdatePhoto) -> dict[str, Any]:
    return {"id": row.id, "original_filename": row.original_filename, "content_type": row.content_type, "size_bytes": row.size_bytes, "created_at": row.created_at}


def _context(db: Session, posts: list[UpdatePost]):
    section_ids = {row.class_section_id for row in posts if row.class_section_id}
    group_ids = {row.subject_group_id for row in posts if row.subject_group_id}
    author_ids = {row.author_user_id for row in posts}
    sections = {row.id: row for row in db.query(ClassSection).filter(ClassSection.id.in_(section_ids)).all()} if section_ids else {}
    groups = {row.id: row for row in db.query(SubjectGroup).filter(SubjectGroup.id.in_(group_ids)).all()} if group_ids else {}
    authors = {row.id: row for row in db.query(User).filter(User.id.in_(author_ids)).all()} if author_ids else {}
    post_ids = {row.id for row in posts}
    photos: dict[int, list[UpdatePhoto]] = {}
    if post_ids:
        for row in db.query(UpdatePhoto).filter(UpdatePhoto.post_id.in_(post_ids)).order_by(UpdatePhoto.id).all():
            photos.setdefault(row.post_id, []).append(row)
    return sections, groups, authors, photos


def _payload(row: UpdatePost, sections, groups, authors, photos, *, include_body=True):
    files = photos.get(row.id, [])
    author = authors.get(row.author_user_id)
    result = {
        "id": row.id, "school_id": row.school_id,
        "author_name": author.name if author else None,
        "audience_type": row.audience_type, "class_section_id": row.class_section_id,
        "class_section_name": sections.get(row.class_section_id).name if row.class_section_id in sections else None,
        "subject_group_id": row.subject_group_id,
        "subject_group_name": groups.get(row.subject_group_id).name if row.subject_group_id in groups else None,
        "status": row.status, "created_at": row.created_at, "updated_at": row.updated_at,
        "photo_count": len(files), "photos": [_photo_payload(file) for file in files],
    }
    result["body" if include_body else "preview"] = row.body if include_body else row.body[:180]
    return result


def _safe_photo_filename(filename: str | None) -> str:
    original = _safe_filename(filename)
    return original or "photo"


def _path(storage_key: str) -> Path:
    root = UPLOAD_ROOT.resolve()
    path = (root / storage_key).resolve()
    if root != path and root not in path.parents:
        raise HTTPException(status_code=404, detail="Photo not found")
    return path


def thumbnail_storage_key(storage_key: str, extension: str) -> str:
    if extension not in {".jpg", ".webp"}:
        raise ValueError("Unsupported thumbnail extension")
    full = Path(storage_key)
    return str(full.with_name(f"{full.stem}.thumbnail{extension}"))


def thumbnail_storage_keys(storage_key: str) -> tuple[str, str]:
    return (
        thumbnail_storage_key(storage_key, ".jpg"),
        thumbnail_storage_key(storage_key, ".webp"),
    )


def _thumbnail_path(photo: UpdatePhoto) -> tuple[Path, str]:
    for storage_key, content_type in zip(
        thumbnail_storage_keys(photo.storage_key),
        ("image/jpeg", "image/webp"),
        strict=True,
    ):
        path = _path(storage_key)
        if path.exists():
            return path, content_type
    raise HTTPException(status_code=404, detail="Photo thumbnail not found")


def _photo_response(photo: UpdatePhoto, *, thumbnail: bool = False):
    if thumbnail:
        path, content_type = _thumbnail_path(photo)
    else:
        path, content_type = _path(photo.storage_key), photo.content_type
    if not path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")
    # No filename → inline display in <img>/lightbox instead of a download.
    return FileResponse(
        path,
        media_type=content_type,
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Cross-Origin-Resource-Policy": "same-origin",
        },
    )


def _guardian_query(db: Session, current_user: User):
    school_ids, section_ids, group_ids = _guardian_audience(db, current_user)
    clauses = []
    if section_ids:
        clauses.append((UpdatePost.audience_type == "class_section") & UpdatePost.class_section_id.in_(section_ids))
    if group_ids:
        clauses.append((UpdatePost.audience_type == "subject_group") & UpdatePost.subject_group_id.in_(group_ids))
    if not school_ids or not clauses:
        return None
    return db.query(UpdatePost).filter(UpdatePost.school_id.in_(school_ids), UpdatePost.status == "active", or_(*clauses))


def _guardian_post(db: Session, current_user: User, post_id: int) -> UpdatePost:
    query = _guardian_query(db, current_user)
    post = query.filter(UpdatePost.id == post_id).first() if query is not None else None
    if not post:
        raise HTTPException(status_code=404, detail="Update not found")
    return post


def _teacher_post(db: Session, current_user: User, school_id: int, post_id: int) -> UpdatePost:
    membership = _teacher_membership(db, current_user, school_id)
    post = db.query(UpdatePost).filter(UpdatePost.id == post_id, UpdatePost.school_id == school_id).first()
    if not post or not _can_manage(db, membership, post):
        raise HTTPException(status_code=404, detail="Update not found")
    return post


@teacher_router.get("/updates")
def list_teacher_updates(request: Request, class_section_id: int | None = None, subject_group_id: int | None = None, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers)
    membership = _teacher_membership(db, current_user, school_id)
    query = _teacher_query(db, membership)
    if class_section_id is not None and subject_group_id is not None:
        raise HTTPException(status_code=400, detail="Choose one update audience")
    if class_section_id is not None:
        if not _teacher_has_target(db, membership, class_section_id=class_section_id): raise HTTPException(status_code=403, detail="Teacher assignment required")
        query = query.filter(UpdatePost.class_section_id == class_section_id)
    if subject_group_id is not None:
        if not _teacher_has_target(db, membership, subject_group_id=subject_group_id): raise HTTPException(status_code=403, detail="Teacher assignment required")
        query = query.filter(UpdatePost.subject_group_id == subject_group_id)
    posts = query.order_by(UpdatePost.created_at.desc(), UpdatePost.id.desc()).limit(100).all()
    sections, groups, authors, photos = _context(db, posts)
    return {"items": [_payload(row, sections, groups, authors, photos) for row in posts]}


@teacher_router.post("/updates", status_code=status.HTTP_201_CREATED)
def create_update(payload: UpdateCreateRequest, request: Request, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers)
    membership = _teacher_membership(db, current_user, school_id)
    section_id, group_id = _validate_target(db, school_id, membership, payload)
    post = UpdatePost(school_id=school_id, author_user_id=current_user.id, body=payload.body, audience_type=payload.audience_type, class_section_id=section_id, subject_group_id=group_id)
    db.add(post); db.flush()
    enqueue_family_notifications(db, category="update", source=post, action="published")
    write_audit(db, current_user.id, "school.update.created", post, {"audience_type": post.audience_type}, school_id=school_id)
    db.commit(); db.refresh(post)
    sections, groups, authors, photos = _context(db, [post])
    return _payload(post, sections, groups, authors, photos)


@teacher_router.post("/updates/{post_id}/photos", status_code=status.HTTP_201_CREATED)
async def upload_photo(post_id: int, request: Request, file: UploadFile = File(...), current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers)
    post = _teacher_post(db, current_user, school_id, post_id)
    if post.status != "active":
        raise HTTPException(status_code=409, detail="Archived updates cannot be changed")
    if db.query(UpdatePhoto).filter(UpdatePhoto.post_id == post.id).count() >= MAX_PHOTOS_PER_POST:
        raise HTTPException(status_code=400, detail="Maximum 5 photos")
    original = _safe_photo_filename(file.filename)
    raw = await file.read(MAX_RAW_IMAGE_BYTES + 1)
    try:
        optimized = optimise_update_photo(raw)
        thumbnail = create_update_thumbnail(optimized.content)
        # The only persistent artifacts are the generated display image and its
        # protected feed derivative. `raw` never has a storage key.
        storage_key = f"school-{school_id}/update-{post.id}/{uuid.uuid4().hex}{optimized.extension}"
        path = _path(storage_key)
        thumbnail_key = thumbnail_storage_key(storage_key, thumbnail.extension)
        thumbnail_path = _path(thumbnail_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(optimized.content)
        thumbnail_path.write_bytes(thumbnail.content)
        photo = UpdatePhoto(post_id=post.id, school_id=school_id, uploaded_by_user_id=current_user.id, original_filename=original, storage_key=storage_key, content_type=optimized.content_type, size_bytes=len(optimized.content))
        db.add(photo); db.flush()
        write_audit(db, current_user.id, "school.update.photo_uploaded", photo, {"post_id": post.id, "filename": original, "size_bytes": len(optimized.content)}, school_id=school_id)
        db.commit(); db.refresh(photo)
        logger.info(
            "event=update_image_optimised input_size_bytes=%d input_format=%s input_width=%d input_height=%d "
            "output_size_bytes=%d output_format=%s output_width=%d output_height=%d quality_used=%d "
            "thumbnail_size_bytes=%d thumbnail_format=%s thumbnail_width=%d thumbnail_height=%d "
            "thumbnail_quality_used=%d raw_original_retained=false processing_ms=%d thumbnail_processing_ms=%d "
            "school_id=%d update_id=%d photo_id=%d",
            len(raw), optimized.input_format, optimized.input_width, optimized.input_height,
            len(optimized.content), optimized.content_type, optimized.output_width, optimized.output_height,
            optimized.quality_used, len(thumbnail.content), thumbnail.content_type,
            thumbnail.output_width, thumbnail.output_height, thumbnail.quality_used,
            optimized.processing_ms, thumbnail.processing_ms, school_id, post.id, photo.id,
        )
        return _photo_payload(photo)
    except Exception:
        if 'path' in locals() and path.exists():
            path.unlink()
        if 'thumbnail_path' in locals() and thumbnail_path.exists():
            thumbnail_path.unlink()
        db.rollback()
        raise
    finally:
        await file.close()
        del raw


@teacher_router.patch("/updates/{post_id}")
def edit_update(post_id: int, payload: UpdateEditRequest, request: Request, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers)
    post = _teacher_post(db, current_user, school_id, post_id)
    if post.status != "active":
        raise HTTPException(status_code=409, detail="Archived updates cannot be edited")
    post.body = payload.body
    write_audit(db, current_user.id, "school.update.updated", post, {}, school_id=school_id)
    db.commit(); db.refresh(post)
    sections, groups, authors, photos = _context(db, [post])
    return _payload(post, sections, groups, authors, photos)


@teacher_router.delete("/updates/{post_id}")
def archive_update(post_id: int, request: Request, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers)
    post = _teacher_post(db, current_user, school_id, post_id)
    post.status = "archived"; post.archived_at = datetime.now(timezone.utc)
    write_audit(db, current_user.id, "school.update.archived", post, {}, school_id=school_id); db.commit()
    return {"status": "archived"}


@teacher_router.get("/updates/{post_id}")
def teacher_detail(post_id: int, request: Request, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers)
    post = _teacher_post(db, current_user, school_id, post_id)
    sections, groups, authors, photos = _context(db, [post])
    return _payload(post, sections, groups, authors, photos)


@teacher_router.get("/updates/{post_id}/photos/{photo_id}/view")
def teacher_view_photo(post_id: int, photo_id: int, request: Request, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers)
    post = _teacher_post(db, current_user, school_id, post_id)
    photo = db.query(UpdatePhoto).filter(UpdatePhoto.id == photo_id, UpdatePhoto.post_id == post.id, UpdatePhoto.school_id == school_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return _photo_response(photo)


@teacher_router.get("/updates/{post_id}/photos/{photo_id}/thumbnail")
def teacher_view_photo_thumbnail(post_id: int, photo_id: int, request: Request, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    school_id = _school_id_from_header(request.headers)
    post = _teacher_post(db, current_user, school_id, post_id)
    photo = db.query(UpdatePhoto).filter(UpdatePhoto.id == photo_id, UpdatePhoto.post_id == post.id, UpdatePhoto.school_id == school_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return _photo_response(photo, thumbnail=True)


@guardian_router.get("/updates")
def guardian_list(current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    query = _guardian_query(db, current_user)
    posts = query.order_by(UpdatePost.created_at.desc(), UpdatePost.id.desc()).limit(50).all() if query is not None else []
    sections, groups, authors, photos = _context(db, posts)
    return {"items": [_payload(row, sections, groups, authors, photos, include_body=False) for row in posts], "count": len(posts)}


@guardian_router.get("/updates/{post_id}")
def guardian_detail(post_id: int, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    post = _guardian_post(db, current_user, post_id)
    sections, groups, authors, photos = _context(db, [post])
    return _payload(post, sections, groups, authors, photos)


@guardian_router.get("/updates/{post_id}/photos/{photo_id}/view")
def guardian_view_photo(post_id: int, photo_id: int, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    post = _guardian_post(db, current_user, post_id)
    photo = db.query(UpdatePhoto).filter(UpdatePhoto.id == photo_id, UpdatePhoto.post_id == post.id, UpdatePhoto.school_id == post.school_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return _photo_response(photo)


@guardian_router.get("/updates/{post_id}/photos/{photo_id}/thumbnail")
def guardian_view_photo_thumbnail(post_id: int, photo_id: int, current_user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    post = _guardian_post(db, current_user, post_id)
    photo = db.query(UpdatePhoto).filter(UpdatePhoto.id == photo_id, UpdatePhoto.post_id == post.id, UpdatePhoto.school_id == post.school_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return _photo_response(photo, thumbnail=True)

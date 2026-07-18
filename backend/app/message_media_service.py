"""CHH-authoritative staged and protected Messaging v1 photo media."""
from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models_school import Conversation, ConversationParticipant, Message, MessageMedia
from .update_image_service import (
    MAX_RAW_IMAGE_BYTES,
    create_protected_thumbnail,
    optimise_protected_photo,
)


logger = logging.getLogger(__name__)
MESSAGE_MEDIA_ROOT = Path(os.environ.get("MESSAGE_MEDIA_DIR", "/app/data/message_media"))
MAX_MESSAGE_PHOTOS = 5
STAGED_MEDIA_TTL = timedelta(hours=24)


class MessageMediaValidationError(Exception):
    pass


class MessageMediaConflict(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def safe_photo_filename(filename: str | None) -> str:
    value = Path(filename or "photo").name
    value = "".join(character for character in value if character.isprintable()).strip()
    return (value[:160] or "photo")


def media_path(storage_key: str) -> Path:
    root = MESSAGE_MEDIA_ROOT.resolve()
    path = (root / storage_key).resolve()
    if root != path and root not in path.parents:
        raise MessageMediaValidationError("Photo is unavailable")
    return path


def _random_storage_key(extension: str) -> str:
    token = uuid.uuid4().hex
    return f"{token[:2]}/{token}{extension}"


def _write_derived(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _unlink_key(storage_key: str | None) -> None:
    if not storage_key:
        return
    try:
        path = media_path(storage_key)
        if path.exists():
            path.unlink()
    except (OSError, MessageMediaValidationError):
        logger.warning("event=message_media_cleanup_failed", exc_info=True)


def media_payload(row: MessageMedia, *, duplicate: bool = False) -> dict:
    return {
        "id": str(row.public_id),
        "sort_order": int(row.sort_order or 0),
        "state": row.state,
        "content_type": row.content_type,
        "full_bytes": row.full_bytes,
        "thumbnail_bytes": row.thumbnail_bytes,
        "width": row.width,
        "height": row.height,
        "thumbnail_width": row.thumbnail_width,
        "thumbnail_height": row.thumbnail_height,
        "thumbnail_available": row.state == "attached",
        "full_available": row.state == "attached",
        "duplicate": duplicate,
    }


def _load_existing_upload(
    db: Session,
    *,
    conversation_id: int,
    participant_id: int,
    client_upload_id: UUID,
) -> MessageMedia | None:
    return (
        db.query(MessageMedia)
        .filter(
            MessageMedia.conversation_id == conversation_id,
            MessageMedia.uploaded_by_participant_id == participant_id,
            MessageMedia.client_upload_id == client_upload_id,
        )
        .first()
    )


def stage_message_photo(
    db: Session,
    *,
    conversation: Conversation,
    participant: ConversationParticipant,
    client_upload_id: UUID,
    raw: bytes,
    filename: str | None,
) -> tuple[MessageMedia, bool]:
    if not raw:
        raise MessageMediaValidationError("Photo is empty")
    if len(raw) > MAX_RAW_IMAGE_BYTES:
        raise MessageMediaValidationError("Photo is too large. Maximum raw upload size is 50 MB.")
    source_checksum = hashlib.sha256(raw).hexdigest()
    existing = _load_existing_upload(
        db,
        conversation_id=conversation.id,
        participant_id=participant.id,
        client_upload_id=client_upload_id,
    )
    now = _utc_now()
    if existing is not None:
        if existing.source_checksum_sha256 != source_checksum:
            raise MessageMediaConflict("Upload id was reused with a different photo")
        if existing.state in {"ready", "attached"}:
            return existing, True
        if existing.state == "processing":
            raise MessageMediaConflict("Photo upload is already processing")
        _unlink_key(existing.full_storage_key)
        _unlink_key(existing.thumbnail_storage_key)
        existing.state = "processing"
        existing.message_id = None
        existing.attached_at = None
        existing.deleted_at = None
        existing.full_storage_key = None
        existing.thumbnail_storage_key = None
        existing.content_type = None
        existing.full_bytes = None
        existing.thumbnail_bytes = None
        existing.width = None
        existing.height = None
        existing.thumbnail_width = None
        existing.thumbnail_height = None
        existing.checksum_sha256 = None
        existing.metadata_stripped = False
        existing.expires_at = now + STAGED_MEDIA_TTL
        row = existing
    else:
        row = MessageMedia(
            school_id=conversation.school_id,
            conversation_id=conversation.id,
            uploaded_by_participant_id=participant.id,
            client_upload_id=client_upload_id,
            source_checksum_sha256=source_checksum,
            original_filename_safe=safe_photo_filename(filename),
            state="processing",
            expires_at=now + STAGED_MEDIA_TTL,
        )
        db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raced = _load_existing_upload(
            db,
            conversation_id=conversation.id,
            participant_id=participant.id,
            client_upload_id=client_upload_id,
        )
        if raced is not None and raced.source_checksum_sha256 == source_checksum and raced.state in {"ready", "attached"}:
            return raced, True
        raise MessageMediaConflict("Photo upload is already processing")

    full_path: Path | None = None
    thumbnail_path: Path | None = None
    try:
        optimized = optimise_protected_photo(raw)
        thumbnail = create_protected_thumbnail(optimized.content)
        full_key = _random_storage_key(optimized.extension)
        thumbnail_key = _random_storage_key(thumbnail.extension)
        full_path = media_path(full_key)
        thumbnail_path = media_path(thumbnail_key)
        _write_derived(full_path, optimized.content)
        _write_derived(thumbnail_path, thumbnail.content)

        row.full_storage_key = full_key
        row.thumbnail_storage_key = thumbnail_key
        row.content_type = optimized.content_type
        row.full_bytes = len(optimized.content)
        row.thumbnail_bytes = len(thumbnail.content)
        row.width = optimized.output_width
        row.height = optimized.output_height
        row.thumbnail_width = thumbnail.output_width
        row.thumbnail_height = thumbnail.output_height
        row.checksum_sha256 = hashlib.sha256(optimized.content).hexdigest()
        row.metadata_stripped = True
        row.state = "ready"
        db.commit()
        db.refresh(row)
        logger.info(
            "event=message_photo_optimised input_size_bytes=%d input_format=%s input_width=%d input_height=%d "
            "output_size_bytes=%d output_format=%s output_width=%d output_height=%d "
            "thumbnail_size_bytes=%d thumbnail_width=%d thumbnail_height=%d raw_original_retained=false "
            "processing_ms=%d thumbnail_processing_ms=%d school_id=%d conversation_id=%d media_id=%d",
            len(raw),
            optimized.input_format,
            optimized.input_width,
            optimized.input_height,
            len(optimized.content),
            optimized.content_type,
            optimized.output_width,
            optimized.output_height,
            len(thumbnail.content),
            thumbnail.output_width,
            thumbnail.output_height,
            optimized.processing_ms,
            thumbnail.processing_ms,
            conversation.school_id,
            conversation.id,
            row.id,
        )
        return row, False
    except Exception:
        db.rollback()
        if full_path is not None and full_path.exists():
            full_path.unlink()
        if thumbnail_path is not None and thumbnail_path.exists():
            thumbnail_path.unlink()
        failed = db.query(MessageMedia).filter(MessageMedia.id == row.id).first()
        if failed is not None and failed.state != "attached":
            failed.state = "failed"
            failed.full_storage_key = None
            failed.thumbnail_storage_key = None
            failed.content_type = None
            failed.full_bytes = None
            failed.thumbnail_bytes = None
            failed.width = None
            failed.height = None
            failed.thumbnail_width = None
            failed.thumbnail_height = None
            failed.checksum_sha256 = None
            failed.metadata_stripped = False
            db.commit()
        raise


def attach_staged_media(
    db: Session,
    *,
    conversation: Conversation,
    participant: ConversationParticipant,
    message: Message,
    staged_media_ids: list[UUID],
) -> list[MessageMedia]:
    if len(staged_media_ids) > MAX_MESSAGE_PHOTOS:
        raise MessageMediaValidationError("Maximum 5 photos")
    if len(set(staged_media_ids)) != len(staged_media_ids):
        raise MessageMediaValidationError("A photo can be attached only once")
    if not staged_media_ids:
        return []
    rows = (
        db.query(MessageMedia)
        .filter(MessageMedia.public_id.in_(staged_media_ids))
        .with_for_update()
        .all()
    )
    by_public_id = {row.public_id: row for row in rows}
    if set(by_public_id) != set(staged_media_ids):
        raise MessageMediaConflict("One or more staged photos are unavailable")
    now = _utc_now()
    ordered = [by_public_id[media_id] for media_id in staged_media_ids]
    for order, row in enumerate(ordered):
        if (
            row.school_id != conversation.school_id
            or row.conversation_id != conversation.id
            or row.uploaded_by_participant_id != participant.id
            or row.message_id is not None
            or row.state != "ready"
            or _as_aware(row.expires_at) <= now
        ):
            raise MessageMediaConflict("One or more staged photos are unavailable")
        row.message_id = message.id
        row.sort_order = order
        row.state = "attached"
        row.attached_at = now
    db.flush()
    return ordered


def attached_media_map(db: Session, message_ids: Iterable[int]) -> dict[int, list[MessageMedia]]:
    ids = set(message_ids)
    if not ids:
        return {}
    rows = (
        db.query(MessageMedia)
        .filter(MessageMedia.message_id.in_(ids), MessageMedia.state == "attached")
        .order_by(MessageMedia.message_id, MessageMedia.sort_order)
        .all()
    )
    result: dict[int, list[MessageMedia]] = {}
    for row in rows:
        result.setdefault(row.message_id, []).append(row)
    return result


def protected_media_file(row: MessageMedia, variant: str) -> tuple[Path, str]:
    if row.state != "attached" or row.message_id is None:
        raise MessageMediaValidationError("Photo is unavailable")
    storage_key = row.thumbnail_storage_key if variant == "thumbnail" else row.full_storage_key
    if not storage_key:
        raise MessageMediaValidationError("Photo is unavailable")
    path = media_path(storage_key)
    if not path.is_file():
        raise MessageMediaValidationError("Photo is unavailable")
    return path, row.content_type or "image/jpeg"


def cleanup_expired_staged_media(
    db: Session,
    *,
    now: datetime | None = None,
    limit: int = 100,
) -> int:
    cutoff = now or _utc_now()
    rows = (
        db.query(MessageMedia)
        .filter(
            MessageMedia.message_id.is_(None),
            MessageMedia.state.in_(("processing", "ready", "failed")),
            MessageMedia.expires_at <= cutoff,
        )
        .order_by(MessageMedia.expires_at, MessageMedia.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
        .all()
    )
    for row in rows:
        _unlink_key(row.full_storage_key)
        _unlink_key(row.thumbnail_storage_key)
        row.state = "expired"
        row.deleted_at = cutoff
        row.full_storage_key = None
        row.thumbnail_storage_key = None
        row.content_type = None
        row.full_bytes = None
        row.thumbnail_bytes = None
        row.width = None
        row.height = None
        row.thumbnail_width = None
        row.thumbnail_height = None
        row.checksum_sha256 = None
        row.metadata_stripped = False
    if rows:
        db.commit()
    return len(rows)

"""Immutable, private generated documents for reports, certificates and messages."""
from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.orm import Session

from .models_school import (
    Conversation,
    ConversationParticipant,
    Membership,
    Message,
    MessageDocument,
)


logger = logging.getLogger(__name__)
GENERATED_DOCUMENT_ROOT = Path(
    os.environ.get("GENERATED_DOCUMENT_DIR", "/app/data/generated_documents")
)
STAGED_DOCUMENT_TTL = timedelta(hours=24)
MAX_GENERATED_DOCUMENT_BYTES = 10 * 1024 * 1024
CONTENT_EXTENSIONS = {"application/pdf": ".pdf", "text/csv": ".csv"}
DOCUMENT_TYPES = {"behaviour_report", "recognition_certificate"}
_DELETE_AFTER_COMMIT = "generated_document_delete_after_commit"
_DELETE_AFTER_ROLLBACK = "generated_document_delete_after_rollback"


class GeneratedDocumentValidationError(Exception):
    pass


class GeneratedDocumentConflict(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def safe_filename(value: str, content_type: str) -> str:
    extension = CONTENT_EXTENSIONS.get(content_type)
    if extension is None:
        raise GeneratedDocumentValidationError("Unsupported generated document type")
    name = Path(value or f"document{extension}").name
    name = "".join(character for character in name if character.isprintable()).strip()
    if not name.lower().endswith(extension):
        name = f"{Path(name).stem}{extension}"
    return (name[:180] or f"document{extension}")


def document_path(storage_key: str) -> Path:
    root = GENERATED_DOCUMENT_ROOT.resolve()
    path = (root / storage_key).resolve()
    if root != path and root not in path.parents:
        raise GeneratedDocumentValidationError("Generated document is unavailable")
    return path


def _unlink(storage_key: str | None) -> None:
    if not storage_key:
        return
    try:
        document_path(storage_key).unlink(missing_ok=True)
    except (OSError, GeneratedDocumentValidationError):
        logger.warning("event=generated_document_cleanup_failed", exc_info=True)


@event.listens_for(Session, "after_commit")
def _generated_document_after_commit(session: Session) -> None:
    for storage_key in session.info.pop(_DELETE_AFTER_COMMIT, set()):
        _unlink(storage_key)
    session.info.pop(_DELETE_AFTER_ROLLBACK, None)


@event.listens_for(Session, "after_rollback")
def _generated_document_after_rollback(session: Session) -> None:
    for storage_key in session.info.pop(_DELETE_AFTER_ROLLBACK, set()):
        _unlink(storage_key)
    session.info.pop(_DELETE_AFTER_COMMIT, None)


def _unlink_after_commit(db: Session, storage_key: str | None) -> None:
    if storage_key:
        db.info.setdefault(_DELETE_AFTER_COMMIT, set()).add(storage_key)


def _unlink_after_rollback(db: Session, storage_key: str) -> None:
    db.info.setdefault(_DELETE_AFTER_ROLLBACK, set()).add(storage_key)


def _write(storage_key: str, content: bytes) -> None:
    path = document_path(storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def cleanup_expired_staged_documents(db: Session, *, limit: int = 25) -> int:
    now = utc_now()
    rows = (
        db.query(MessageDocument)
        .filter(
            MessageDocument.state == "ready",
            MessageDocument.message_id.is_(None),
            MessageDocument.expires_at <= now,
        )
        .order_by(MessageDocument.expires_at, MessageDocument.id)
        .limit(limit)
        .all()
    )
    for row in rows:
        _unlink_after_commit(db, row.storage_key)
        row.storage_key = None
        row.state = "expired"
        row.disposed_at = now
    if rows:
        db.flush()
    return len(rows)


def create_generated_document(
    db: Session,
    *,
    school_id: int,
    membership_id: int,
    document_type: str,
    source_ref: str,
    filename: str,
    content_type: str,
    content: bytes,
) -> MessageDocument:
    if document_type not in DOCUMENT_TYPES:
        raise GeneratedDocumentValidationError("Unsupported generated document type")
    if not source_ref or len(source_ref) > 120:
        raise GeneratedDocumentValidationError("Invalid generated document source")
    if not content or len(content) > MAX_GENERATED_DOCUMENT_BYTES:
        raise GeneratedDocumentValidationError("Generated document size is invalid")
    membership = (
        db.query(Membership)
        .filter(
            Membership.id == membership_id,
            Membership.school_id == school_id,
            Membership.status == "active",
            Membership.revoked_at.is_(None),
        )
        .first()
    )
    if membership is None:
        raise GeneratedDocumentValidationError("Active school membership required")
    cleanup_expired_staged_documents(db)
    extension = CONTENT_EXTENSIONS.get(content_type)
    if extension is None:
        raise GeneratedDocumentValidationError("Unsupported generated document type")
    token = uuid.uuid4().hex
    storage_key = f"school-{school_id}/{token[:2]}/{token}{extension}"
    digest = hashlib.sha256(content).hexdigest()
    _write(storage_key, content)
    _unlink_after_rollback(db, storage_key)
    row = MessageDocument(
        school_id=school_id,
        generated_by_membership_id=membership_id,
        document_type=document_type,
        source_ref=source_ref,
        original_filename_safe=safe_filename(filename, content_type),
        content_type=content_type,
        storage_key=storage_key,
        size_bytes=len(content),
        checksum_sha256=digest,
        state="ready",
        expires_at=utc_now() + STAGED_DOCUMENT_TTL,
    )
    db.add(row)
    try:
        db.flush()
    except Exception:
        _unlink(storage_key)
        raise
    return row


def document_payload(row: MessageDocument) -> dict:
    return {
        "id": str(row.public_id),
        "document_type": row.document_type,
        "filename": row.original_filename_safe,
        "content_type": row.content_type,
        "size_bytes": int(row.size_bytes),
        "available": row.state in {"ready", "attached"} and row.storage_key is not None,
    }


def staged_document_for_membership(
    db: Session,
    *,
    school_id: int,
    membership_id: int,
    public_id: UUID,
    lock: bool = False,
) -> MessageDocument:
    query = db.query(MessageDocument).filter(
        MessageDocument.public_id == public_id,
        MessageDocument.school_id == school_id,
        MessageDocument.generated_by_membership_id == membership_id,
        MessageDocument.message_id.is_(None),
        MessageDocument.state == "ready",
    )
    if lock and db.bind and db.bind.dialect.name == "postgresql":
        query = query.with_for_update()
    row = query.first()
    if row is None or aware(row.expires_at) <= utc_now() or not row.storage_key:
        raise GeneratedDocumentValidationError("Generated document is unavailable")
    return row


def attach_staged_document(
    db: Session,
    *,
    conversation: Conversation,
    participant: ConversationParticipant,
    message: Message,
    staged_document_id: UUID | None,
) -> MessageDocument | None:
    if staged_document_id is None:
        return None
    if participant.membership_id is None or participant.participant_kind != "staff":
        raise GeneratedDocumentValidationError("Only the generating staff member may attach this document")
    row = staged_document_for_membership(
        db,
        school_id=conversation.school_id,
        membership_id=participant.membership_id,
        public_id=staged_document_id,
        lock=True,
    )
    row.message_id = message.id
    row.state = "attached"
    row.attached_at = utc_now()
    db.flush()
    return row


def attached_document_map(db: Session, message_ids: list[int]) -> dict[int, MessageDocument]:
    if not message_ids:
        return {}
    rows = (
        db.query(MessageDocument)
        .filter(
            MessageDocument.message_id.in_(message_ids),
            MessageDocument.state.in_(("attached", "retention_deleted")),
        )
        .all()
    )
    return {int(row.message_id): row for row in rows}


def protected_document_file(row: MessageDocument) -> tuple[Path, str, str]:
    if row.state != "attached" or not row.storage_key:
        raise GeneratedDocumentValidationError("Generated document is unavailable")
    path = document_path(row.storage_key)
    if not path.is_file() or path.stat().st_size != row.size_bytes:
        raise GeneratedDocumentValidationError("Generated document is unavailable")
    if hashlib.sha256(path.read_bytes()).hexdigest() != row.checksum_sha256:
        raise GeneratedDocumentValidationError("Generated document is unavailable")
    return path, row.content_type, row.original_filename_safe


def mark_attached_documents_disposed(db: Session, *, message_ids: list[int], now: datetime) -> list[str]:
    rows = (
        db.query(MessageDocument)
        .filter(
            MessageDocument.message_id.in_(message_ids),
            MessageDocument.state == "attached",
        )
        .all()
        if message_ids
        else []
    )
    storage_keys = [row.storage_key for row in rows if row.storage_key]
    for row in rows:
        row.storage_key = None
        row.state = "retention_deleted"
        row.disposed_at = now
    if rows:
        db.flush()
    return storage_keys


def unlink_disposed_document_keys(storage_keys: list[str]) -> None:
    for storage_key in storage_keys:
        _unlink(storage_key)

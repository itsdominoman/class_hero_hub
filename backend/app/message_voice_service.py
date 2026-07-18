"""CHH-authoritative staged, normalized and protected voice-note media."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .message_media_service import (
    MESSAGE_MEDIA_ROOT,
    MessageMediaValidationError,
    media_path,
)
from .models_school import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageVoiceMedia,
)


logger = logging.getLogger(__name__)
MAX_RAW_AUDIO_BYTES = 8 * 1024 * 1024
MAX_NORMALIZED_AUDIO_BYTES = 3 * 1024 * 1024
MIN_VOICE_DURATION_MS = 600
MAX_VOICE_DURATION_MS = 180_000
STAGED_VOICE_TTL = timedelta(hours=24)


class MessageVoiceValidationError(Exception):
    pass


class MessageVoiceConflict(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _random_storage_key() -> str:
    token = uuid.uuid4().hex
    return f"voice/{token[:2]}/{token}.m4a"


def _write_derived(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _unlink_key(storage_key: str | None) -> None:
    if not storage_key:
        return
    try:
        media_path(storage_key).unlink(missing_ok=True)
    except (OSError, MessageMediaValidationError):
        logger.warning("event=message_voice_cleanup_failed", exc_info=True)


def _run(command: list[str], *, timeout: int = 35) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Protected audio processor is unavailable") from exc
    except subprocess.TimeoutExpired as exc:
        raise MessageVoiceValidationError("Voice note could not be processed") from exc


def _probe(path: Path) -> dict:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=format_name,duration:stream=index,codec_type,codec_name,duration",
            "-of",
            "json",
            str(path),
        ]
    )
    if result.returncode != 0:
        raise MessageVoiceValidationError("Unsupported or malformed voice note")
    try:
        value = json.loads(result.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MessageVoiceValidationError("Unsupported or malformed voice note") from exc
    if not isinstance(value, dict):
        raise MessageVoiceValidationError("Unsupported or malformed voice note")
    return value


def _duration_ms(probe: dict) -> int:
    candidates = [
        stream.get("duration")
        for stream in probe.get("streams", [])
        if isinstance(stream, dict) and stream.get("codec_type") == "audio"
    ]
    if isinstance(probe.get("format"), dict):
        candidates.append(probe["format"].get("duration"))
    for candidate in candidates:
        try:
            duration = float(candidate)
        except (TypeError, ValueError):
            continue
        if duration > 0:
            return int(round(duration * 1000))
    raise MessageVoiceValidationError("Voice note duration could not be determined")


def normalize_voice_note(raw: bytes) -> tuple[bytes, int]:
    """Sniff/decode input and return metadata-free mono AAC-LC in an M4A container."""
    if not raw:
        raise MessageVoiceValidationError("Voice note is empty")
    if len(raw) > MAX_RAW_AUDIO_BYTES:
        raise MessageVoiceValidationError("Voice note is too large")
    processing_root = MESSAGE_MEDIA_ROOT / ".processing"
    processing_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="voice-", dir=processing_root) as directory:
        source = Path(directory) / "source.bin"
        output = Path(directory) / "normalized.m4a"
        source.write_bytes(raw)
        source_probe = _probe(source)
        streams = [row for row in source_probe.get("streams", []) if isinstance(row, dict)]
        audio_streams = [row for row in streams if row.get("codec_type") == "audio"]
        if not audio_streams or any(row.get("codec_type") == "video" for row in streams):
            raise MessageVoiceValidationError("The upload must contain audio only")
        source_duration = _duration_ms(source_probe)
        if source_duration < MIN_VOICE_DURATION_MS:
            raise MessageVoiceValidationError("Voice note is too short")
        if source_duration > MAX_VOICE_DURATION_MS + 500:
            raise MessageVoiceValidationError("Voice note exceeds the 3 minute limit")

        result = _run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-i",
                str(source),
                "-map",
                "0:a:0",
                "-vn",
                "-map_metadata",
                "-1",
                "-map_chapters",
                "-1",
                "-ac",
                "1",
                "-ar",
                "48000",
                "-c:a",
                "aac",
                "-profile:a",
                "aac_low",
                "-b:a",
                "64k",
                "-movflags",
                "+faststart",
                "-t",
                "180.0",
                str(output),
            ]
        )
        if result.returncode != 0 or not output.is_file():
            raise MessageVoiceValidationError("Voice note could not be processed")
        normalized = output.read_bytes()
        if not normalized or len(normalized) > MAX_NORMALIZED_AUDIO_BYTES:
            raise MessageVoiceValidationError("Normalized voice note is too large")
        output_probe = _probe(output)
        output_streams = [
            row for row in output_probe.get("streams", []) if isinstance(row, dict)
        ]
        if (
            len([row for row in output_streams if row.get("codec_type") == "audio"]) != 1
            or any(row.get("codec_type") == "video" for row in output_streams)
            or next(row for row in output_streams if row.get("codec_type") == "audio").get("codec_name") != "aac"
            or "mp4" not in str(output_probe.get("format", {}).get("format_name", ""))
        ):
            raise MessageVoiceValidationError("Normalized voice note is invalid")
        duration_ms = _duration_ms(output_probe)
        if not MIN_VOICE_DURATION_MS <= duration_ms <= MAX_VOICE_DURATION_MS:
            raise MessageVoiceValidationError("Voice note duration is outside the allowed range")
        return normalized, duration_ms


def voice_payload(row: MessageVoiceMedia, *, duplicate: bool = False) -> dict:
    return {
        "id": str(row.public_id),
        "state": row.state,
        "content_type": row.content_type,
        "size_bytes": row.size_bytes,
        "duration_ms": row.duration_ms,
        "codec": row.codec,
        "container": row.container,
        "available": row.state == "attached",
        "transcription": {"available": False, "state": row.transcription_state},
        "duplicate": duplicate,
    }


def _load_existing_upload(
    db: Session,
    *,
    conversation_id: int,
    participant_id: int,
    client_upload_id: UUID,
) -> MessageVoiceMedia | None:
    return (
        db.query(MessageVoiceMedia)
        .filter(
            MessageVoiceMedia.conversation_id == conversation_id,
            MessageVoiceMedia.uploaded_by_participant_id == participant_id,
            MessageVoiceMedia.client_upload_id == client_upload_id,
        )
        .first()
    )


def stage_message_voice(
    db: Session,
    *,
    conversation: Conversation,
    participant: ConversationParticipant,
    client_upload_id: UUID,
    raw: bytes,
) -> tuple[MessageVoiceMedia, bool]:
    if not raw:
        raise MessageVoiceValidationError("Voice note is empty")
    if len(raw) > MAX_RAW_AUDIO_BYTES:
        raise MessageVoiceValidationError("Voice note is too large")
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
            raise MessageVoiceConflict("Upload id was reused with different audio")
        if existing.state in {"ready", "attached"}:
            return existing, True
        if existing.state == "processing":
            raise MessageVoiceConflict("Voice upload is already processing")
        _unlink_key(existing.storage_key)
        existing.state = "processing"
        existing.message_id = None
        existing.attached_at = None
        existing.deleted_at = None
        existing.storage_key = None
        existing.content_type = None
        existing.size_bytes = None
        existing.duration_ms = None
        existing.codec = None
        existing.container = None
        existing.checksum_sha256 = None
        existing.metadata_stripped = False
        existing.expires_at = now + STAGED_VOICE_TTL
        row = existing
    else:
        row = MessageVoiceMedia(
            school_id=conversation.school_id,
            conversation_id=conversation.id,
            uploaded_by_participant_id=participant.id,
            client_upload_id=client_upload_id,
            source_checksum_sha256=source_checksum,
            state="processing",
            expires_at=now + STAGED_VOICE_TTL,
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
        raise MessageVoiceConflict("Voice upload is already processing")

    storage_path: Path | None = None
    try:
        normalized, duration_ms = normalize_voice_note(raw)
        storage_key = _random_storage_key()
        storage_path = media_path(storage_key)
        _write_derived(storage_path, normalized)
        row.storage_key = storage_key
        row.content_type = "audio/mp4"
        row.size_bytes = len(normalized)
        row.duration_ms = duration_ms
        row.codec = "aac"
        row.container = "mp4"
        row.checksum_sha256 = hashlib.sha256(normalized).hexdigest()
        row.metadata_stripped = True
        row.state = "ready"
        db.commit()
        db.refresh(row)
        logger.info(
            "event=message_voice_normalised input_size_bytes=%d output_size_bytes=%d "
            "duration_ms=%d codec=aac container=mp4 metadata_stripped=true "
            "raw_original_retained=false school_id=%d conversation_id=%d media_id=%d",
            len(raw),
            len(normalized),
            duration_ms,
            conversation.school_id,
            conversation.id,
            row.id,
        )
        return row, False
    except Exception:
        db.rollback()
        if storage_path is not None:
            storage_path.unlink(missing_ok=True)
        failed = db.query(MessageVoiceMedia).filter(MessageVoiceMedia.id == row.id).first()
        if failed is not None and failed.state != "attached":
            failed.state = "failed"
            failed.storage_key = None
            failed.content_type = None
            failed.size_bytes = None
            failed.duration_ms = None
            failed.codec = None
            failed.container = None
            failed.checksum_sha256 = None
            failed.metadata_stripped = False
            db.commit()
        raise


def attach_staged_voice(
    db: Session,
    *,
    conversation: Conversation,
    participant: ConversationParticipant,
    message: Message,
    staged_voice_id: UUID,
) -> MessageVoiceMedia:
    row = (
        db.query(MessageVoiceMedia)
        .filter(MessageVoiceMedia.public_id == staged_voice_id)
        .with_for_update()
        .first()
    )
    now = _utc_now()
    if (
        row is None
        or row.school_id != conversation.school_id
        or row.conversation_id != conversation.id
        or row.uploaded_by_participant_id != participant.id
        or row.message_id is not None
        or row.state != "ready"
        or _as_aware(row.expires_at) <= now
    ):
        raise MessageVoiceConflict("Staged voice note is unavailable")
    row.message_id = message.id
    row.state = "attached"
    row.attached_at = now
    db.flush()
    return row


def attached_voice_map(db: Session, message_ids: Iterable[int]) -> dict[int, MessageVoiceMedia]:
    ids = set(message_ids)
    if not ids:
        return {}
    rows = (
        db.query(MessageVoiceMedia)
        .filter(
            MessageVoiceMedia.message_id.in_(ids),
            MessageVoiceMedia.state == "attached",
        )
        .all()
    )
    return {row.message_id: row for row in rows}


def protected_voice_file(row: MessageVoiceMedia) -> tuple[Path, str]:
    if row.state != "attached" or row.message_id is None or not row.storage_key:
        raise MessageVoiceValidationError("Voice note is unavailable")
    path = media_path(row.storage_key)
    if not path.is_file():
        raise MessageVoiceValidationError("Voice note is unavailable")
    return path, "audio/mp4"


def cleanup_expired_staged_voice(
    db: Session,
    *,
    now: datetime | None = None,
    limit: int = 100,
) -> int:
    cutoff = now or _utc_now()
    rows = (
        db.query(MessageVoiceMedia)
        .filter(
            MessageVoiceMedia.message_id.is_(None),
            MessageVoiceMedia.state.in_(("processing", "ready", "failed")),
            MessageVoiceMedia.expires_at <= cutoff,
        )
        .order_by(MessageVoiceMedia.expires_at, MessageVoiceMedia.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
        .all()
    )
    for row in rows:
        _unlink_key(row.storage_key)
        row.state = "expired"
        row.deleted_at = cutoff
        row.storage_key = None
        row.content_type = None
        row.size_bytes = None
        row.duration_ms = None
        row.codec = None
        row.container = None
        row.checksum_sha256 = None
        row.metadata_stripped = False
    if rows:
        db.commit()
    return len(rows)

from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Type

from sqlalchemy.orm import Session

from .models_school import (
    Announcement,
    AnnouncementAttachment,
    AnnouncementRead,
    AuditLog,
    CalendarEvent,
    Conversation,
    DemoSeedRecord,
    HomeworkAttachment,
    HomeworkItem,
    HomeworkItemCompletion,
    Message,
    School,
    Survey,
    UpdatePhoto,
    UpdatePost,
)


@dataclass(frozen=True)
class EntitySpec:
    model_name: str
    model: Type[Any]


ENTITY_SPECS: dict[str, EntitySpec] = {
    "announcement": EntitySpec("announcements", Announcement),
    "calendar_event": EntitySpec("calendar_events", CalendarEvent),
    "homework_item": EntitySpec("homework_items", HomeworkItem),
    "update_post": EntitySpec("update_posts", UpdatePost),
    "update_photo": EntitySpec("update_photos", UpdatePhoto),
}
DEFAULT_ENTITY_TYPES = tuple(ENTITY_SPECS)
CLEANUP_VERSION = "manifest-content-cleanup-v1"


@dataclass(frozen=True)
class StorageRoots:
    announcements: Path
    homework: Path
    updates: Path

    @classmethod
    def from_environment(cls) -> "StorageRoots":
        return cls(
            announcements=Path(os.environ.get("ANNOUNCEMENT_UPLOAD_DIR", "/app/data/announcement_uploads")),
            homework=Path(os.environ.get("HOMEWORK_UPLOAD_DIR", "/app/data/homework_uploads")),
            updates=Path(os.environ.get("UPDATE_UPLOAD_DIR", "/app/data/update_uploads")),
        )


@dataclass
class CleanupSummary:
    mode: str
    school_id: int
    school_slug: str
    manifest_counts: Counter = field(default_factory=Counter)
    delete_counts: Counter = field(default_factory=Counter)
    dependent_counts: Counter = field(default_factory=Counter)
    preserved_counts: Counter = field(default_factory=Counter)
    ambiguous_counts: Counter = field(default_factory=Counter)
    unproven_counts: Counter = field(default_factory=Counter)
    already_removed_counts: Counter = field(default_factory=Counter)
    namespace_counts: Counter = field(default_factory=Counter)
    deleted_files: int = 0
    missing_files: int = 0
    unsafe_files: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "school_id": self.school_id,
            "school_slug": self.school_slug,
            "cleanup_version": CLEANUP_VERSION,
            "manifest_counts": dict(sorted(self.manifest_counts.items())),
            "delete_counts": dict(sorted(self.delete_counts.items())),
            "dependent_counts": dict(sorted(self.dependent_counts.items())),
            "preserved_counts": dict(sorted(self.preserved_counts.items())),
            "ambiguous_counts": dict(sorted(self.ambiguous_counts.items())),
            "unproven_counts": dict(sorted(self.unproven_counts.items())),
            "already_removed_counts": dict(sorted(self.already_removed_counts.items())),
            "namespace_counts": dict(sorted(self.namespace_counts.items())),
            "deleted_files": self.deleted_files,
            "missing_files": self.missing_files,
            "unsafe_files": self.unsafe_files,
        }


@dataclass
class CleanupPlan:
    summary: CleanupSummary
    manifests: list[DemoSeedRecord]
    delete_ids: dict[str, set[int]]
    storage_entries: list[tuple[Path, str]]


class CleanupError(RuntimeError):
    pass


def _cleanup_marker(row: DemoSeedRecord) -> dict[str, Any] | None:
    metadata = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    cleanup = metadata.get("cleanup")
    return cleanup if isinstance(cleanup, dict) else None


def _target_school(db: Session, school_slug: str) -> School:
    schools = db.query(School).filter(School.slug == school_slug).all()
    if len(schools) != 1:
        raise CleanupError(f"Expected one school with slug {school_slug!r}; found {len(schools)}")
    return schools[0]


def _ids(rows: list[Any]) -> set[int]:
    return {int(row.id) for row in rows}


def _thumbnail_keys(storage_key: str) -> tuple[str, str]:
    path = Path(storage_key)
    return (
        str(path.with_name(f"{path.stem}.thumbnail.jpg")),
        str(path.with_name(f"{path.stem}.thumbnail.webp")),
    )


def build_cleanup_plan(
    db: Session,
    *,
    school_slug: str,
    entity_types: tuple[str, ...] = DEFAULT_ENTITY_TYPES,
    storage_roots: StorageRoots | None = None,
) -> CleanupPlan:
    unknown = sorted(set(entity_types) - set(ENTITY_SPECS))
    if unknown:
        raise CleanupError(f"Unsupported seeded entity types: {', '.join(unknown)}")
    school = _target_school(db, school_slug)
    roots = storage_roots or StorageRoots.from_environment()
    summary = CleanupSummary(mode="dry-run", school_id=school.id, school_slug=school.slug)
    manifests: list[DemoSeedRecord] = []
    delete_ids = {entity_type: set() for entity_type in entity_types}

    manifest_rows = (
        db.query(DemoSeedRecord)
        .filter(DemoSeedRecord.entity_type.in_(entity_types))
        .order_by(DemoSeedRecord.seed_namespace, DemoSeedRecord.entity_type, DemoSeedRecord.id)
        .all()
    )
    for manifest in manifest_rows:
        spec = ENTITY_SPECS[manifest.entity_type]
        marker = _cleanup_marker(manifest)
        if marker and marker.get("state") == "removed" and marker.get("school_slug") == school.slug:
            summary.already_removed_counts[manifest.entity_type] += 1
            continue
        if manifest.model_name != spec.model_name:
            summary.ambiguous_counts[f"{manifest.entity_type}:model_mismatch"] += 1
            continue
        if manifest.model_id is None:
            summary.ambiguous_counts[f"{manifest.entity_type}:missing_model_id"] += 1
            continue
        target = db.get(spec.model, manifest.model_id)
        if target is None:
            summary.ambiguous_counts[f"{manifest.entity_type}:target_missing"] += 1
            continue
        if getattr(target, "school_id", None) != school.id:
            summary.preserved_counts[f"{manifest.entity_type}:other_school"] += 1
            continue
        manifests.append(manifest)
        delete_ids[manifest.entity_type].add(int(manifest.model_id))
        summary.manifest_counts[manifest.entity_type] += 1
        summary.namespace_counts[manifest.seed_namespace] += 1

    announcement_ids = delete_ids.get("announcement", set())
    homework_ids = delete_ids.get("homework_item", set())
    update_post_ids = delete_ids.get("update_post", set())

    announcement_attachments = (
        db.query(AnnouncementAttachment).filter(AnnouncementAttachment.post_id.in_(announcement_ids)).all()
        if announcement_ids
        else []
    )
    announcement_reads = (
        db.query(AnnouncementRead).filter(AnnouncementRead.announcement_id.in_(announcement_ids)).all()
        if announcement_ids
        else []
    )
    homework_attachments = (
        db.query(HomeworkAttachment).filter(HomeworkAttachment.homework_item_id.in_(homework_ids)).all()
        if homework_ids
        else []
    )
    homework_completions = (
        db.query(HomeworkItemCompletion).filter(HomeworkItemCompletion.homework_item_id.in_(homework_ids)).all()
        if homework_ids
        else []
    )
    child_update_photos = (
        db.query(UpdatePhoto).filter(UpdatePhoto.post_id.in_(update_post_ids)).all()
        if update_post_ids
        else []
    )
    delete_ids.setdefault("update_photo", set()).update(_ids(child_update_photos))

    summary.dependent_counts.update(
        {
            "announcement_attachments": len(announcement_attachments),
            "announcement_reads": len(announcement_reads),
            "homework_attachments": len(homework_attachments),
            "homework_completions": len(homework_completions),
            "update_photos": len(child_update_photos),
        }
    )
    for entity_type, ids in delete_ids.items():
        summary.delete_counts[entity_type] = len(ids)

    for entity_type in entity_types:
        spec = ENTITY_SPECS[entity_type]
        total = db.query(spec.model).filter(spec.model.school_id == school.id).count()
        summary.preserved_counts[f"{entity_type}:not_selected"] = max(total - len(delete_ids[entity_type]), 0)

    summary.unproven_counts.update(
        {
            "surveys": db.query(Survey).filter(Survey.school_id == school.id).count(),
            "conversations": db.query(Conversation).filter(Conversation.school_id == school.id).count(),
            "messages": db.query(Message).filter(Message.school_id == school.id).count(),
        }
    )

    storage_entries = [
        *((roots.announcements, row.storage_key) for row in announcement_attachments),
        *((roots.homework, row.storage_key) for row in homework_attachments),
    ]
    update_photos = (
        db.query(UpdatePhoto).filter(UpdatePhoto.id.in_(delete_ids["update_photo"])).all()
        if delete_ids["update_photo"]
        else []
    )
    for photo in update_photos:
        storage_entries.append((roots.updates, photo.storage_key))
        storage_entries.extend((roots.updates, key) for key in _thumbnail_keys(photo.storage_key))

    return CleanupPlan(
        summary=summary,
        manifests=manifests,
        delete_ids=delete_ids,
        storage_entries=storage_entries,
    )


def _safe_unlink(root: Path, storage_key: str, summary: CleanupSummary) -> None:
    resolved_root = root.resolve()
    resolved_path = (resolved_root / storage_key).resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        summary.unsafe_files += 1
        return
    if not resolved_path.exists():
        summary.missing_files += 1
        return
    resolved_path.unlink()
    summary.deleted_files += 1


def apply_cleanup_plan(db: Session, plan: CleanupPlan) -> CleanupSummary:
    summary = plan.summary
    now = datetime.now(timezone.utc)
    announcement_ids = plan.delete_ids.get("announcement", set())
    homework_ids = plan.delete_ids.get("homework_item", set())
    update_photo_ids = plan.delete_ids.get("update_photo", set())

    try:
        if announcement_ids:
            db.query(AnnouncementRead).filter(AnnouncementRead.announcement_id.in_(announcement_ids)).delete(synchronize_session=False)
            db.query(AnnouncementAttachment).filter(AnnouncementAttachment.post_id.in_(announcement_ids)).delete(synchronize_session=False)
        if homework_ids:
            db.query(HomeworkItemCompletion).filter(HomeworkItemCompletion.homework_item_id.in_(homework_ids)).delete(synchronize_session=False)
            db.query(HomeworkAttachment).filter(HomeworkAttachment.homework_item_id.in_(homework_ids)).delete(synchronize_session=False)
        if update_photo_ids:
            db.query(UpdatePhoto).filter(UpdatePhoto.id.in_(update_photo_ids)).delete(synchronize_session=False)

        for entity_type in ("announcement", "homework_item", "update_post", "calendar_event"):
            ids = plan.delete_ids.get(entity_type, set())
            if ids:
                model = ENTITY_SPECS[entity_type].model
                db.query(model).filter(model.id.in_(ids)).delete(synchronize_session=False)

        for manifest in plan.manifests:
            metadata = dict(manifest.metadata_json) if isinstance(manifest.metadata_json, dict) else {}
            metadata["cleanup"] = {
                "state": "removed",
                "school_slug": summary.school_slug,
                "removed_at": now.isoformat(),
                "version": CLEANUP_VERSION,
            }
            manifest.metadata_json = metadata

        db.add(
            AuditLog(
                school_id=summary.school_id,
                actor_user_id=None,
                action="demo_seed.content_cleanup",
                entity_type="school",
                entity_id=summary.school_id,
                detail={
                    "version": CLEANUP_VERSION,
                    "manifest_counts": dict(summary.manifest_counts),
                    "delete_counts": dict(summary.delete_counts),
                    "namespace_counts": dict(summary.namespace_counts),
                },
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    summary.mode = "apply"
    for root, storage_key in plan.storage_entries:
        _safe_unlink(root, storage_key, summary)
    return summary


def cleanup_seeded_content(
    db: Session,
    *,
    school_slug: str,
    apply: bool = False,
    entity_types: tuple[str, ...] = DEFAULT_ENTITY_TYPES,
    storage_roots: StorageRoots | None = None,
) -> CleanupSummary:
    plan = build_cleanup_plan(
        db,
        school_slug=school_slug,
        entity_types=entity_types,
        storage_roots=storage_roots,
    )
    return apply_cleanup_plan(db, plan) if apply else plan.summary

"""Idempotent update-photo thumbnail audit and backfill support."""
from __future__ import annotations

import os
import uuid
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from .models_school import UpdatePhoto
from .routes import updates
from .update_image_service import create_update_thumbnail


@dataclass
class ThumbnailBackfillReport:
    mode: str
    total_photos: int = 0
    existing_thumbnails: int = 0
    missing_thumbnails: int = 0
    generated_thumbnails: int = 0
    source_bytes: int = 0
    thumbnail_bytes: int = 0
    failures: int = 0
    failure_categories: Counter[str] = field(default_factory=Counter)
    samples: list[dict[str, int | str]] = field(default_factory=list)
    four_photo_full_bytes: int = 0
    four_photo_thumbnail_bytes: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "total_photos": self.total_photos,
            "existing_thumbnails": self.existing_thumbnails,
            "missing_thumbnails": self.missing_thumbnails,
            "generated_thumbnails": self.generated_thumbnails,
            "source_bytes": self.source_bytes,
            "thumbnail_bytes": self.thumbnail_bytes,
            "failures": self.failures,
            "failure_categories": dict(sorted(self.failure_categories.items())),
            "samples": self.samples,
            "four_photo_full_bytes": self.four_photo_full_bytes,
            "four_photo_thumbnail_bytes": self.four_photo_thumbnail_bytes,
        }


def _existing_thumbnail_path(photo: UpdatePhoto) -> Path | None:
    for storage_key in updates.thumbnail_storage_keys(photo.storage_key):
        path = updates._path(storage_key)
        if path.exists():
            return path
    return None


def _write_new_file_atomically(path: Path, content: bytes) -> bool:
    """Publish a complete new file without ever replacing an existing variant."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, path)
            return True
        except FileExistsError:
            return False
    finally:
        temporary.unlink(missing_ok=True)


def backfill_update_photo_thumbnails(
    db: Session,
    *,
    apply: bool = False,
) -> ThumbnailBackfillReport:
    report = ThumbnailBackfillReport(mode="apply" if apply else "dry-run")
    photos = db.query(UpdatePhoto).order_by(UpdatePhoto.id).all()
    report.total_photos = len(photos)
    generated_metrics: list[dict[str, int]] = []

    for photo in photos:
        if _existing_thumbnail_path(photo) is not None:
            report.existing_thumbnails += 1
            continue

        report.missing_thumbnails += 1
        try:
            full_path = updates._path(photo.storage_key)
            if not full_path.exists():
                raise FileNotFoundError
            full_bytes = full_path.read_bytes()
            report.source_bytes += len(full_bytes)
            thumbnail = create_update_thumbnail(full_bytes)
            report.thumbnail_bytes += len(thumbnail.content)
            generated_metrics.append(
                {
                    "full_bytes": len(full_bytes),
                    "thumbnail_bytes": len(thumbnail.content),
                    "thumbnail_width": thumbnail.output_width,
                    "thumbnail_height": thumbnail.output_height,
                }
            )
            if apply:
                thumbnail_key = updates.thumbnail_storage_key(
                    photo.storage_key,
                    thumbnail.extension,
                )
                thumbnail_path = updates._path(thumbnail_key)
                if _write_new_file_atomically(thumbnail_path, thumbnail.content):
                    report.generated_thumbnails += 1
                else:
                    report.existing_thumbnails += 1
        except FileNotFoundError:
            report.failures += 1
            report.failure_categories["missing_full_image"] += 1
        except Exception:
            report.failures += 1
            report.failure_categories["generation_or_write_failed"] += 1

    if generated_metrics:
        ordered = sorted(generated_metrics, key=lambda metric: metric["full_bytes"])
        sample_positions = [
            ("small", 0),
            ("median", len(ordered) // 2),
            ("large", len(ordered) - 1),
        ]
        report.samples = [
            {"sample": label, **ordered[position]}
            for label, position in sample_positions
        ]
        start = max(0, min(len(ordered) - 4, len(ordered) // 2 - 2))
        four = ordered[start:start + 4]
        report.four_photo_full_bytes = sum(metric["full_bytes"] for metric in four)
        report.four_photo_thumbnail_bytes = sum(
            metric["thumbnail_bytes"] for metric in four
        )

    return report

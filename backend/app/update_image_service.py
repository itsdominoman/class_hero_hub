"""Safe, one-way optimisation for Updates & Photos uploads.

Raw uploads are deliberately kept in memory only while this function runs.  The
caller writes only the returned display image to persistent update storage.
"""
from __future__ import annotations

import io
import warnings
from dataclasses import dataclass, replace
from time import perf_counter

from fastapi import HTTPException
from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

try:
    from pillow_heif import register_heif_opener
except ImportError:  # pragma: no cover - deployment dependency is mandatory
    register_heif_opener = None


MAX_RAW_IMAGE_BYTES = 50 * 1024 * 1024
MAX_OUTPUT_IMAGE_BYTES = int(1.5 * 1024 * 1024)
TARGET_OUTPUT_IMAGE_BYTES = 1 * 1024 * 1024
MAX_IMAGE_DIMENSION = 1600
STARTING_QUALITY = 85
PREFERRED_MINIMUM_QUALITY = 78
THUMBNAIL_MAX_DIMENSION = 400
TARGET_THUMBNAIL_IMAGE_BYTES = 100 * 1024
MAX_THUMBNAIL_IMAGE_BYTES = 160 * 1024
THUMBNAIL_STARTING_QUALITY = 82
# Large enough for modern phone photographs, while preventing decompression
# bombs from allocating unbounded memory.
Image.MAX_IMAGE_PIXELS = 64_000_000

_SOURCE_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF", "HEIC"}

if register_heif_opener is not None:
    register_heif_opener()


@dataclass(frozen=True)
class OptimizedImage:
    content: bytes
    content_type: str
    extension: str
    input_format: str = ""
    input_width: int = 0
    input_height: int = 0
    output_width: int = 0
    output_height: int = 0
    quality_used: int = 0
    processing_ms: int = 0


def _invalid(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


def _normalise_rgb(image: Image.Image) -> tuple[Image.Image, bool]:
    """Apply colour/orientation transforms and return pixels with no metadata."""
    image = ImageOps.exif_transpose(image)
    image.load()
    has_alpha = "A" in image.getbands() or "transparency" in image.info
    # Convert embedded profiles before discarding them. Invalid profiles do not
    # make a valid photo unusable; Pillow's RGB conversion is a safe fallback.
    if image.info.get("icc_profile"):
        try:
            source = ImageCms.ImageCmsProfile(io.BytesIO(image.info["icc_profile"]))
            target = ImageCms.createProfile("sRGB")
            image = ImageCms.profileToProfile(image, source, target, outputMode="RGBA" if has_alpha else "RGB")
        except Exception:
            image = image.convert("RGBA" if has_alpha else "RGB")
    else:
        image = image.convert("RGBA" if has_alpha else "RGB")
    return image, has_alpha


def _resize(image: Image.Image, max_dimension: int) -> Image.Image:
    if max(image.size) <= max_dimension:
        return image
    result = image.copy()
    result.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    return result


def _encode(image: Image.Image, has_alpha: bool, quality: int) -> OptimizedImage:
    output = io.BytesIO()
    if has_alpha:
        image.save(output, format="WEBP", quality=quality, method=6)
        return OptimizedImage(output.getvalue(), "image/webp", ".webp")
    image.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
    return OptimizedImage(output.getvalue(), "image/jpeg", ".jpg")


def _completed(candidate: OptimizedImage, *, input_format: str, input_size: tuple[int, int], output_size: tuple[int, int], quality: int, started_at: float) -> OptimizedImage:
    return replace(
        candidate,
        input_format=input_format,
        input_width=input_size[0],
        input_height=input_size[1],
        output_width=output_size[0],
        output_height=output_size[1],
        quality_used=quality,
        processing_ms=round((perf_counter() - started_at) * 1000),
    )


def optimise_update_photo(raw: bytes) -> OptimizedImage:
    """Decode a permitted real image and return a metadata-free display image."""
    started_at = perf_counter()
    if not raw:
        raise _invalid("Photo is empty")
    if len(raw) > MAX_RAW_IMAGE_BYTES:
        raise _invalid("Photo is too large. Maximum raw upload size is 50 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in _SOURCE_FORMATS:
                    raise _invalid("Photo type not allowed")
                input_format = source.format
                input_size = source.size
                image, has_alpha = _normalise_rgb(source)
    except HTTPException:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise _invalid("Photo dimensions are too large to process safely")
    except (UnidentifiedImageError, OSError, ValueError):
        raise _invalid("Photo is not a supported image")

    # Quality comes before byte minimisation.  At each display size, start at
    # 85 and only lower quality when it is needed to meet the normal 1 MB
    # budget.  A detailed image may deliberately remain between 1 MB and the
    # 1.5 MB hard cap at quality 78 rather than being visibly over-compressed.
    # Below 78 is used only when necessary to honour the hard storage limit.
    dimension = MAX_IMAGE_DIMENSION
    while dimension >= 640:
        resized = _resize(image, dimension)
        preferred_hard_limit_candidate: OptimizedImage | None = None
        for quality in (STARTING_QUALITY, 82, PREFERRED_MINIMUM_QUALITY):
            candidate = _encode(resized, has_alpha, quality)
            if len(candidate.content) <= TARGET_OUTPUT_IMAGE_BYTES:
                return _completed(candidate, input_format=input_format, input_size=input_size, output_size=resized.size, quality=quality, started_at=started_at)
            if len(candidate.content) <= MAX_OUTPUT_IMAGE_BYTES:
                preferred_hard_limit_candidate = _completed(candidate, input_format=input_format, input_size=input_size, output_size=resized.size, quality=quality, started_at=started_at)

        # The last acceptable preferred candidate is quality 78. Do not
        # reduce further merely to save bytes below the target.
        if preferred_hard_limit_candidate is not None:
            return preferred_hard_limit_candidate

        for quality in (75, 72, 68, 64, 60, 56, 52, 48, 44, 40, 35):
            candidate = _encode(resized, has_alpha, quality)
            if len(candidate.content) <= MAX_OUTPUT_IMAGE_BYTES:
                return _completed(candidate, input_format=input_format, input_size=input_size, output_size=resized.size, quality=quality, started_at=started_at)
        dimension = int(dimension * 0.8)
    raise _invalid("Photo could not be compressed below the 1.5 MB storage limit")


def create_update_thumbnail(display_image: bytes) -> OptimizedImage:
    """Create a metadata-free feed derivative without ever upscaling.

    The input may be a newly generated display image or an older stored update
    photo. Re-running the same orientation and colour normalisation makes the
    legacy backfill safe for files that still contain EXIF orientation data.
    """
    started_at = perf_counter()
    if not display_image:
        raise _invalid("Photo is empty")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(display_image)) as source:
                if source.format not in _SOURCE_FORMATS:
                    raise _invalid("Photo type not allowed")
                input_format = source.format
                input_size = source.size
                image, has_alpha = _normalise_rgb(source)
    except HTTPException:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise _invalid("Photo dimensions are too large to process safely")
    except (UnidentifiedImageError, OSError, ValueError):
        raise _invalid("Photo is not a supported image")

    # Keep the derivative close to 400px. Detailed images may step down modestly
    # only when quality reduction alone cannot meet the practical 100KB target.
    dimensions = (THUMBNAIL_MAX_DIMENSION, 360, 320, 288)
    smallest_candidate: OptimizedImage | None = None
    smallest_size: tuple[int, int] | None = None
    smallest_quality = 0
    for dimension in dimensions:
        resized = _resize(image, dimension)
        for quality in (THUMBNAIL_STARTING_QUALITY, 78, 74, 70, 66, 62, 58, 54, 50, 45):
            candidate = _encode(resized, has_alpha, quality)
            if smallest_candidate is None or len(candidate.content) < len(smallest_candidate.content):
                smallest_candidate = candidate
                smallest_size = resized.size
                smallest_quality = quality
            if len(candidate.content) <= TARGET_THUMBNAIL_IMAGE_BYTES:
                return _completed(
                    candidate,
                    input_format=input_format,
                    input_size=input_size,
                    output_size=resized.size,
                    quality=quality,
                    started_at=started_at,
                )
        if max(image.size) <= dimension:
            break

    if smallest_candidate is not None and len(smallest_candidate.content) <= MAX_THUMBNAIL_IMAGE_BYTES:
        return _completed(
            smallest_candidate,
            input_format=input_format,
            input_size=input_size,
            output_size=smallest_size or image.size,
            quality=smallest_quality,
            started_at=started_at,
        )
    raise _invalid("Photo thumbnail could not be compressed safely")

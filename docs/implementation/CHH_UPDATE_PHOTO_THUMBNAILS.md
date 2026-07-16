# CHH protected update-photo thumbnails

Implemented 2026-07-16.

New update-photo uploads keep the existing metadata-free, orientation-corrected
display image with a 1600px maximum edge and also create a separate protected feed
thumbnail. The thumbnail:

- has a maximum edge of 400px and is never upscaled;
- is JPEG, or WebP when transparency must be preserved;
- targets 100KB and has a 160KB hard generation limit;
- is re-encoded without EXIF, ICC, GPS, or other source metadata;
- is stored beside the display image as `<uuid>.thumbnail.jpg|webp`;
- is written before the `UpdatePhoto` row is committed, so a thumbnail failure
  removes any partial derived/full files and leaves no photo record.

The raw upload remains memory-only and is discarded. Existing full-image storage
keys and database rows are unchanged.

Protected thumbnail routes:

- `GET /api/teach/updates/{update_id}/photos/{photo_id}/thumbnail`
- `GET /api/guardian/updates/{update_id}/photos/{photo_id}/thumbnail`
- `GET /api/integrations/fhh/links/{link_id}/updates/{update_id}/photos/{photo_id}/thumbnail`

They reuse the same teacher/guardian audience checks or FHH service-token,
per-link-token, student, school, update, and photo checks as the full image. Media
responses are inline, `private, no-store`, `nosniff`, and same-origin. No public
storage URL, token-bearing URL, or school ID query parameter exists.

## Legacy audit and backfill

The command is dry-run by default:

```bash
docker compose run --rm --no-deps \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$PWD/backend:/app:ro" -w /app backend \
  python scripts/backfill_update_photo_thumbnails.py
```

Apply requires the explicit flag:

```bash
docker compose run --rm --no-deps \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$PWD/backend:/app:ro" -w /app backend \
  python scripts/backfill_update_photo_thumbnails.py --apply
```

It generates missing thumbnails only, publishes each file atomically without
replacement, never changes a database row or full image, and reports aggregate
counts/bytes/failures without identifiers. It is safe to rerun.

Development rollback is filesystem-only: restore `data/update_uploads` from the
pre-apply archive, or remove only files matching `*.thumbnail.jpg` and
`*.thumbnail.webp`. No PostgreSQL rollback is required.

### Development run, 2026-07-16

The initial dry-run found 29 photos, all missing thumbnails, with 23,276,834
source bytes and 600,968 projected thumbnail bytes; generation failures were zero.
Before apply, `data/update_uploads` was archived to:

`tmp/chh-update-uploads-before-thumbnail-backfill-2026-07-16.tar.gz`

SHA-256:

`8b31ae4d7fe5c76d14ec8c29c616ef38664e256f9f6270d30ee7bb6059bad940`

Apply generated 29 thumbnails (600,968 bytes) with zero failures. The aggregate
digest of every full image was identical before and after apply:

`f278262ede29dbf518705e6de3370fba73832fb0cf467520d910eaac2179572c`

A second dry-run reported 29 existing thumbnails, zero missing, zero generated,
and zero failures.

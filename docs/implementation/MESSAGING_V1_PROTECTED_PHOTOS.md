# Messaging v1 Slice 8: CHH-authoritative protected photos

**Status:** implemented and validated for the CHH/FHH development pilot on
2026-07-18. Slices 9–13 remain pending. Production is unchanged.

This is the Slice 8 implementation record. The architecture in
`docs/planning/2026-07-messaging-v1-architecture-plan.md` remains authoritative.

## Ownership and flow

CHH is the sole record owner. FHH authenticates a parent and proxies bytes, but it
does not store message history, media rows, raw uploads, derived photos, storage keys,
or CHH credentials in a client.

1. The current CHH participant is authorized for the conversation and for sending.
2. Each raw image is read into bounded memory, decoded by actual format, normalized,
   and replaced by a protected full image plus thumbnail.
3. CHH commits an opaque staged media row scoped to school, conversation, uploader,
   and a stable client upload UUID.
4. A message send contains text and/or at most five ordered staged IDs.
5. Under the conversation/message transaction CHH locks and verifies every media row,
   then attaches it to the committed message.
6. History returns only allowlisted media metadata. Thumbnail/full bytes require a
   separate protected request and current access is checked again.

Uploads and sends are idempotent. Reusing an upload or message UUID with different
content is a conflict. A staged ID cannot cross school, conversation, participant, or
expiry boundaries.

## Schema and storage

Alembic revision `f5a6b7c8d9e0` adds `message_media`. Important constraints include:

- opaque public and client-upload UUIDs;
- foreign keys to school, conversation, optional message, and uploader participant;
- unique `(conversation_id, uploaded_by_participant_id, client_upload_id)`;
- unique `(message_id, sort_order)` with order limited to 0–4;
- explicit processing/ready/attached/failed/expired/deleted states and shape checks;
- indexed school, conversation, message, uploader, state/expiry, and ordered message
  lookup paths.

Only randomized server-owned derivative keys are stored below `/app/data/message_media`.
Temporary writes are atomically renamed. The raw source is never written. API payloads
contain no key, filesystem path, source checksum, original filename, or public URL.

Staged rows expire after 24 hours. Upload traffic performs small opportunistic cleanup
batches. Operators can inspect or apply bounded cleanup without adding a Slice 13
retention worker:

```bash
docker compose exec -T backend python scripts/cleanup_staged_message_media.py
docker compose exec -T backend python scripts/cleanup_staged_message_media.py --apply
```

The command is dry-run by default and reports aggregate counts only.

## Processing contract

Messaging uses the generalized, already-proven update-photo processor in
`app/update_image_service.py`:

- raw cap: 50 MiB; pixel/decompression cap: 64 million pixels;
- accepted decoded inputs: JPEG, PNG, WEBP, HEIC and HEIF;
- MIME type and extension are not trusted;
- EXIF orientation is applied; pixels are converted to RGB/RGBA and an embedded ICC
  profile is normalized when usable;
- metadata, including GPS, EXIF and ICC, is absent from both outputs;
- no upscaling;
- full output: longest edge at most 1600 px, JPEG or WEBP, hard cap 1.5 MiB;
- thumbnail: normally 400 px longest edge, JPEG or WEBP, hard cap 160 KiB.

A representative synthetic 4032×3024, 11,921,902-byte high-detail JPEG measured on
the development backend image produced a 1600×1200, 775,055-byte full image in
1001.8 ms and a 400×300, 17,380-byte thumbnail in 90.4 ms (1092.2 ms total). This is
a reproducible implementation observation, not a production SLO.

## Protected APIs

CHH staff/admin and supported CHH guardians use:

- `POST /api[/guardian]/messaging/conversations/{conversation}/media`
- `GET /api[/guardian]/messaging/conversations/{conversation}/media/{media}/{thumbnail|full}`
- existing message send with optional `body` and `staged_media_ids`.

FHH's server-only integration uses the matching link-scoped endpoints under
`/api/integrations/fhh/links/{link}/messaging/...`. Upload assertions bind the stable
upload UUID, SHA-256 and byte length. Every upload and byte request checks the live
service credential, exact link credential, short-lived actor assertion, school/link/
student identity scope, conversation access, and message sequence visibility.

Media responses use `private, no-store, max-age=0`, `Pragma: no-cache`, `nosniff`,
same-origin resource policy, and inline disposition. Access paths are redacted from
request logs. A missing media item is an item failure, not link revocation.

## CHH client behavior

The accepted compact header, sticky/safe-area composer, polling, draft ownership,
scroll intent, optimistic retry, and ordered native Back chain remain intact. Slice 8
adds gallery and Android camera inputs, up to five selected previews, per-photo
upload/retry/remove state, text/photo and photo-only sends, protected thumbnail grids,
and a dark full-screen viewer with pinch, pan, swipe, desktop arrows/Escape and native
Back. Each protected fetch owns a short-lived `blob:` URL and revokes it on replacement,
route/access reset, or destruction. One failed tile is independently retryable.

## Performance and validation evidence

Message history fetches media metadata once for the entire page; it never queries per
message or per photo and it never fetches full bytes for the timeline. The existing
100-conversation/100-message fixture measured 24 inbox SELECTs, 17 unread SELECTs and
26 history SELECTs for a 50-message page. The one Slice 8 history query is set-based,
so the count is independent of photo population. Timelines request thumbnails only;
full bytes are requested after the viewer opens.

Focused pre-deployment evidence:

- CHH messaging backend: 15 passed;
- CHH messaging presentation/photo contracts: 9 passed;
- Android-sized focused Playwright: 7 passed;
- protected update-photo regression: 6 passed;
- Svelte check: 0 errors and 0 warnings;
- EN/AR parity: 1,165 keys in each locale;
- production frontend build: passed;
- app-scoped Android unit, lint, app APK and instrumentation APK assembly: passed.

The deployment/APK evidence is recorded in `docs/operations/CHH_CURRENT_DEPLOYMENT.md`.

## Explicit exclusions

Slice 8 adds no final delivery/read receipt presentation, contact-hours worker,
notification or push bridge, safeguarding administration tools, automated retention
worker, Redis/WebSockets/SSE/Celery, video, voice notes, PDFs, office documents, or
other attachment types. Those remain Slices 9–13 or explicit non-goals.

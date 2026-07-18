# Messaging v1 protected voice notes

**Implemented:** 2026-07-18  
**Release:** S25q development pilot  
**Authority:** CHH owns authorization, normalization, metadata and protected bytes;
FHH is a child/family-scoped streaming proxy and never stores a message or audio copy.

## User contract

Voice notes are a separate message type. A message is either text/photos or one voice
note; voice cannot be mixed with text, photos, urgency or a second recording. The
composer supports hold-to-record, horizontal slide-to-cancel (mirrored in RTL),
swipe-up lock, pause/resume while locked, delete, preview, re-record and explicit
send. Recordings shorter than 600 ms are cancelled and recording stops at 180
seconds. Backgrounding pauses and locks a live recording. Android Back first cancels
the active recorder/preview; it does not unexpectedly leave the conversation.

The protected player fetches bytes only when Play is selected. It provides play,
pause, seek, elapsed/total time and 1x/1.5x/2x speed. Starting a player stops the
previous player. It never autoplays and exposes loading, failed, unavailable and
retry states in English and Arabic.

## Media contract and storage

- Browser input may be `audio/mp4` or a MediaRecorder-supported Opus/WebM variant.
- CHH treats declared MIME and filename as untrusted, probes the bytes with
  `ffprobe`, rejects malformed/no-audio/video/over-limit input, and normalizes using
  bounded `ffmpeg` work directories.
- Canonical output is metadata-free AAC-LC, mono, 48 kHz, 64 kbps in an ISO BMFF
  `.m4a` container with MIME `audio/mp4` and fast-start layout.
- Raw input is capped at 8 MiB and is never retained. Canonical output is capped at
  3 MiB. Duration is 600 ms through 180,000 ms inclusive.
- At 64 kbps, audio payload is about 8 KB/s, 480 KB/minute or 1.44 MB for three
  minutes before small container overhead. One thousand one-minute notes are about
  458 MiB. Capacity planning must also allow database rows, filesystem allocation,
  backup copies and headroom.
- Protected files use randomized non-public storage keys. Clients receive opaque
  UUIDs, server-derived duration/codec/container/size and availability only. They
  never receive paths, storage keys, source names, raw probe output or checksums.
- Staged media expires after 24 hours. The bounded cleanup script removes expired
  unattached voice stages and legacy photo stages. Attached-message retention and
  deletion policy remains a separately approved safeguarding/retention operation;
  this release does not silently purge message records.
- Transcription is deliberately absent (`not_requested`). Future transcription,
  waveform persistence and audio export require separate privacy, accessibility,
  retention and threat review.

## Data and API

Alembic revision `b7c8d9e0f1a2` adds `messages.message_type`,
`message_voice_media`, `school_feature_controls` and append-only
`school_feature_control_audit_events`. A voice stage records its owner participant,
school and conversation, idempotent upload UUID, opaque public UUID, random storage
key, normalized media facts, SHA-256, lifecycle timestamps and expiry. Attachment is
transactional with message creation and accepts only the same active participant,
school and conversation. Stable upload and message UUIDs make retries idempotent;
reusing an upload UUID with different bytes fails with conflict.

CHH staff/guardian routes add:

- `POST .../conversations/{conversation_id}/voice-media` with `X-Upload-Id`;
- `GET .../conversations/{conversation_id}/voice-media/{media_id}`;
- `staged_voice_id` on message send;
- `capabilities.voice_notes`, `message_type` and a strict `voice_note` metadata
  object on inbox/history responses.

FHH integration adds signed server-only upload and playback routes under
`/links/{link_id}/messaging/...`. The upload assertion binds the opaque upload UUID,
actual SHA-256 and actual byte count. CHH repeats current link, identity, participant
and conversation authorization before normalization or playback. Protected playback
uses `audio/mp4`, `private, no-store`, `nosniff`, same-origin resource policy and no
stable/public URL. Playback remains available to currently authorized participants
after the feature switch is disabled; disabling blocks only new recording/upload/send.

## Security and failure behavior

Access is fail-closed at global messaging policy, school feature control, actor,
participant, conversation and media scope. Cross-school, cross-conversation and
cross-participant access is denied. Source MIME spoofing is harmless because the
actual streams are probed. Work files are deleted on success and failure. Protected
audio paths are redacted from access logs. A corrupt or unavailable note is isolated
to that item and cannot revoke the durable FHH school connection.

## Focused validation

- CHH backend: 44 focused messaging/integration/voice tests passed, including real
  ffmpeg normalization, malformed/empty/short/video/oversize/over-duration rejection,
  default-off control, immutable acknowledgement audit, idempotency, orphan cleanup,
  cross-participant/conversation/school isolation and retained playback after disable.
- CHH frontend: 12 focused messaging contracts passed; production build passed;
  English/Arabic key parity passed at 1,215 keys each.
- FHH backend: 28 focused proxy/client/lifecycle tests passed, including the 8 MiB
  read bound, child/family/link scope, assertion checksum/size and strict allowlists.
- FHH frontend: 14 focused state/UI-parity tests passed; production build passed;
  English/Arabic key parity passed at 1,451 keys each.

The Android app-scoped unit/lint/assembly evidence and deployed pilot evidence are
recorded in the smoke and current-deployment documents. Real microphone, interruption,
OEM WebView and speaker/Bluetooth behavior remain device gates.

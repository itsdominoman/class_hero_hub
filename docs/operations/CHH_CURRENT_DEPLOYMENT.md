# CHH current development deployment

**Status date:** 2026-07-18
**Environment:** CHH development, `https://class.familyherohub.com`
**Source checkpoint:** `main`, S25q protected voice-note release tag
`chh-s25q-messaging-voice-notes-2026-07-18`
**Messaging status:** development pilot enabled only for United International School;
production remains disabled and unchanged.

## S25q deployed scope

S25q adds CHH-authoritative protected voice notes for staff and the FHH parent
integration. CHH validates a bounded memory-only raw upload, probes and normalizes it
with ffmpeg to mono AAC-LC in M4A/ISO BMFF, and stores only the randomized protected
result. Raw uploads are limited to 8 MiB; normalized notes are limited to 3 MiB and
600 ms through 180 seconds. Staged rows expire after 24 hours, attachment is
idempotent and conversation scoped, and playback repeats current authorization. FHH
remains a bounded, no-persistence proxy.

The CHH backend and frontend images/services were rebuilt and recreated at deployed
application commit `8c56408`. PostgreSQL was migrated in place but was not restarted
or recreated. No production service, database, configuration, DNS, or artifact was
changed.

- Pre-migration pgBackRest full backup: `20260718-180149F`.
- Alembic: `b7c8d9e0f1a2` is current head. A disposable PostgreSQL database passed a
  clean full upgrade, downgrade to `f5a6b7c8d9e0`, and re-upgrade before the deliberate
  development migration.
- Default-off school control: exactly one enabled row, United International School
  (`school_id=1`), control version `2`; zero other schools enabled. The acknowledgement
  produced one immutable feature-control audit event.
- Public API health, frontend root and `/messages`: HTTP 200. Protected staff voice
  playback and school feature-control endpoints return HTTP 401 without credentials.
- A real FHH-to-CHH development upload produced `audio/mp4`, AAC/MP4, duration 1,000 ms
  and 9,350 normalized bytes through the safe proxy allowlist. No staged smoke row is
  left in the database.
- Affected services are running and their latest 20-minute backend/frontend logs have
  no traceback, uncaught exception or error. PostgreSQL remains healthy.
- Focused CHH validation: 44 backend voice/messaging tests, 12 frontend voice/messaging
  tests, production web build, and EN/AR parity at 1,215 keys passed.

## Previous S25n deployed scope

S25n implements Messaging v1 Slice 8 only: CHH-authoritative protected photo
messages for staff and the FHH parent integration. Messages may contain text, one to
five photos, or both. CHH owns staged/attached media rows and randomized protected
derivatives; raw uploads are bounded in memory and are never persisted. FHH remains a
credential-hiding, no-persistence proxy.

The CHH backend and frontend images/services were rebuilt and recreated. PostgreSQL
was not restarted or recreated. No production service, database, configuration, DNS,
or artifact was changed.

- Pre-deploy pgBackRest full backup: `20260718-111653F`.
- Alembic: upgraded `e4f5a6b7c8d9` to `f5a6b7c8d9e0` (`message_media`); current
  revision is head.
- CHH flag: `MESSAGING_ENABLED=true`.
- Enabled school policy: United International School only (`pending_setup`).
- Loopback frontend root and `/messages`: HTTP 200.
- Direct API health: HTTP 200 with `{"status":"ok"}`; affected services have clean
  startup logs.
- Authenticated compatibility smoke: messaging inbox HTTP 200 (1 item), existing text
  history HTTP 200 (10-item page), protected update thumbnail HTTP 200 (`image/jpeg`,
  25,216 bytes).
- New-image backend suite: 15 passed; protected update-photo regression: 6 passed.
- Frontend: Svelte check 0 errors/0 warnings, production build passed, focused contracts
  9 passed, Android-sized Playwright 7 passed, EN/AR parity 1,165 keys each.
- Query fixture: 24 inbox, 17 unread and 26 50-message-history SELECTs; the single
  Slice 8 media query is page-batched rather than per message/photo.

## Development voice-note APK

- Server: `/opt/apps/class_hero_hub/tmp/class-hero-hub-voice-notes-dev.apk`
- Google Drive: `G:\My Drive\CHH\Remote\class-hero-hub-voice-notes-dev.apk`
- Package: `com.classherohub.app`
- Version: code `1`, name `1.0`; compile SDK 35.
- Native API: `https://class.familyherohub.com/api`
- Size: 95,893,704 bytes.
- SHA-256: `b2fd998690250ac3167a6265b3bd4c0f6a2356d997d336ce6669294b545e324c`.
- Signing: Android debug certificate; signer certificate SHA-256
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
- Server and Google Drive copies have identical byte size and SHA-256. Package and
  packaged-asset inspection confirm the application ID and fixed CHH native API above.
- Fresh, app-scoped `testDebugUnitTest`, `lintDebug`, and `assembleDebug` passed after
  the S25q web assets were synchronized into Capacitor.

## Operational boundaries

The source/test default remains disabled; development enablement is an explicit
school acknowledgement and is not production authorization. Staged voice and photo
media expire after 24 hours. Opportunistic bounded cleanup and the dry-run-first
operator cleanup command are not a final retention worker.

Transcription, waveform generation, final retention/deletion automation, compliance
export, receipt presentation, contact-hours scheduling, school-message push,
safeguarding administration and video/office attachments remain later work or
explicit non-goals.

Physical-device verification remains required for microphone grant/denial recovery,
hold/lock/cancel gestures, calls/alarms, backgrounding, speaker/Bluetooth/headset audio
routes, network retry, gesture and three-button navigation, native Back and EN/AR RTL.
Use the S25q rows in `docs/testing/CHH_ANDROID_APK_SMOKE_TEST.md` before widening the
pilot.

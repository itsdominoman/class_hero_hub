# CHH current development deployment

**Status date:** 2026-07-18
**Environment:** CHH development, `https://class.familyherohub.com`
**Source checkpoint:** `main`, S25n / Messaging v1 Slice 8 release tag
`chh-s25n-messaging-photos-2026-07-18`
**Messaging status:** development pilot enabled only for United International School;
production remains disabled and unchanged.

## S25n deployed scope

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

## Development APK

- Server: `/opt/apps/class_hero_hub/tmp/class-hero-hub-messaging-photos-dev.apk`
- Google Drive: `G:\My Drive\CHH\Remote\class-hero-hub-messaging-photos-dev.apk`
- Package: `com.classherohub.app`
- Version: code `1`, name `1.0`; compile SDK 35.
- Native API: `https://class.familyherohub.com/api`
- Public native-debug flag: `true`.
- Size: 95,821,581 bytes.
- SHA-256: `6879bf2955abbdab046ed4eb1ae9182974666251694649be83ef00f8b5cbffd6`.
- Signing: Android debug certificate; APK Signature Schemes v1 and v2 verified.
- Server, downloaded verification copy and Google Drive copy have the same byte size
  and SHA-256.
- Fresh native validation passed app-scoped `testDebugUnitTest`, `lintDebug`,
  `assembleDebug`, and `assembleDebugAndroidTest` after the S25n web assets were
  synchronized into Capacitor.

## Operational boundaries

The source/test default remains disabled; development enablement is an explicit
runtime/policy decision and is not production authorization. Staged media expires
after 24 hours. Opportunistic bounded cleanup runs on upload traffic, and the operator
cleanup command remains dry-run by default. This is not the later retention worker.

S25n adds no final receipt UI, contact-hours worker, notification/push bridge,
safeguarding administration UI, retention worker, Redis/WebSockets/SSE/Celery, video,
voice, PDF, office-document, or other attachment support. Those remain later slices or
explicit non-goals.

Physical-device verification remains required for camera/gallery permissions and
chooser behavior, gesture and three-button navigation, real IME behavior, native Back,
pinch/pan/swipe, session restoration and native Google authentication. Use the S25n
rows in `docs/testing/CHH_ANDROID_APK_SMOKE_TEST.md` before widening the pilot.

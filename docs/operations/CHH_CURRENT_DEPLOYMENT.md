# CHH current development deployment

**Status date:** 2026-07-17
**Environment:** CHH development, `https://class.familyherohub.com`
**Messaging status:** development pilot enabled only for United International School;
production remains disabled.

## S25i deployed scope

S25i hardens only the CHH Android messaging composer, keyboard resize and hardware
Back behavior. The CHH frontend image/service was rebuilt and restarted. The backend,
PostgreSQL service, database schema and FHH services were not rebuilt or restarted.

- Pre-deploy pgBackRest full backup: `20260717-073438F`.
- Alembic head: `e4f5a6b7c8d9`; no migration ran.
- CHH flag: `MESSAGING_ENABLED=true`.
- Enabled school policy: United International School only (`pending_setup`).
- Messaging rows at verification: 3 conversations, 17 messages, 12 participants,
  9 receipt events and 230 assertion-use rows.
- Loopback/public frontend root and `/messages`: HTTP 200.
- Direct/public API health: HTTP 200 with `{"status":"ok"}`.
- Anonymous `/api/me`, messaging inbox and protected update media: HTTP 401.

## Development APK

- Server: `/opt/apps/class_hero_hub/tmp/class-hero-hub-s25i-dev.apk`
- Google Drive: `G:\My Drive\CHH\Remote\class-hero-hub-s25i-dev.apk`
- Package: `com.classherohub.app`
- Native API: `https://class.familyherohub.com/api`
- Size: 95,845,408 bytes
- SHA-256: `55c777e0e344f7777fb308e6cc7d9233f672c01f93ad5b12f6554cef82077834`
- Signing: Android debug certificate; APK Signature Scheme v1/v2 verified.

## Operational boundaries

The default remains disabled in source/test configuration; development enablement is
an explicit runtime/policy decision and is not production authorization. S25i adds no
messaging photos, final receipt UI, contact-hours worker, notification delivery/push,
safeguarding administration UI, retention worker, or CHH guardian UI.

Physical-device verification remains required for gesture and three-button system
navigation, real IME behavior, hardware Back, session restoration, native Google
authentication, protected media and camera/gallery flows. Use the Android smoke
matrix before widening or signing off the pilot.

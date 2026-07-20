# CHH current development deployment

## S26l school-message Android push - final physical acceptance

Messaging v1 Slice 11 is complete on CHH development at runtime commit `0c5c643`.
Dom physically confirmed on 2026-07-20 that CHH receives real push while closed,
that FHH-to-CHH notifications reach staff only, and that a notification tap opens
the correct School Chat. The final notification-direction correction was server-side;
no replacement APK was required for acceptance.

- Post-acceptance database correlation for messages `71` and `73` (FHH parent
  authored) shows exactly one `chh_user` staff target each, no sender/self target,
  and no FHH bridge event at either message timestamp.
- Messages `70` and `72` (staff authored) show exactly one `fhh_link` target each.
  Their matching FHH events reached `provider_accepted`; authorised family devices
  received the notification normally.
- The direction correction therefore prevents family-authored messages from
  notifying any FHH household member while preserving staff-reply delivery.
- CHH and FHH loopback/public `/api/health` returned HTTP 200. CHH backend,
  frontend, scheduler and PostgreSQL services are healthy; the notification evidence
  is retained in the durable outbox/delivery tables.
- Final source tag: `chh-s26l-android-push-notifications-2026-07-20`.

**Status date:** 2026-07-20

**Environment:** CHH development, `https://class.familyherohub.com`

**Source checkpoint:** `main`, `0c5c643` plus this completion record. Production was
not touched.

## S26k named-administrator receipt mop-up

Messaging v1 Slice 9 administrator receipts are corrected on CHH development. The
old aggregate query treated every `school_admin_membership` access grant as though it
were safeguarding review. That grant is also the ordinary authorization source for
both named sides of a staff-direct thread and for a named primary administrator in a
student/guardian thread. Aggregation now accepts staff evidence only for memberships
structurally named by the conversation; a nonparticipant safeguarding reviewer still
owns no participant cursor and cannot affect visible receipts.

- Admin-to-teacher, teacher-to-admin, admin-to-FHH-parent and FHH-parent-to-admin
  Sent/Delivered/Read progression passes through the normal participant routes. Live
  read-only inspection confirms the existing named admin/teacher and named
  admin/FHH rows aggregate as Read without exposing message bodies or family data.
- Dual-role teacher/administrator accounts persist the selected membership in the
  message URL. Each request and acknowledgement remains bound to that exact
  membership/participant; switching roles clears the selected thread, and tests prove
  cursors, aggregates and participant rows do not cross-contaminate or duplicate.
- Safeguarding-only review remains outside the normal inbox/thread/acknowledgement
  routes. The focused gate proves denial for a nonparticipant admin, no participant or
  receipt creation, no cursor movement, immutable audit-only evidence, and defensive
  aggregate exclusion. This release does not add a safeguarding review UI/session.
- The focused current-image backend gate passed 50 tests. Current-source browser
  receipt-only polling and dual-role switching passed 2/2; focused receipt, actor,
  tick and policy source tests passed; Svelte checking passed with 0 errors/warnings;
  EN/AR parity remains 1,274/1,274; the production frontend build passed. Real
  attached photo and voice-note tests advance through Delivered and Read, and the
  signed FHH integration is covered in both directions.
- Only CHH backend and frontend were rebuilt/recreated. Public `/`, `/api/health` and
  `/messages` returned HTTP 200 and affected-service logs were clean. PostgreSQL and
  the Slice 10 `notification_scheduler` were not recreated: their container IDs stayed
  `c4bec565ceae` and `e578f39ef6c2`. No schema, migration or production action was
  required.
- Slice 10 is unchanged after deployment: messaging and scheduler remain enabled;
  poll/batch/lease/recheck are 15/50/60/300 seconds; retry is 30-3,600 seconds with 10
  attempts; the school remains `Asia/Muscat`, policy version 4, receipts/contact hours
  enabled, `delay_notifications_only`, staff opt-in/teacher urgent disabled, Sunday-
  Thursday 07:30-15:00, Friday/Saturday closed; the outbox remains empty.

### Development administrator-receipt APK

- Server: `/opt/apps/class_hero_hub/tmp/class-hero-hub-admin-receipts-dev.apk`
- Google Drive: `G:\My Drive\CHH\Remote\class-hero-hub-admin-receipts-dev.apk`
- Package `com.classherohub.app`; version code/name `1`/`1.0`; min SDK 23,
  compile/target SDK 35; API `https://class.familyherohub.com/api`.
- Size: 95,986,665 bytes; SHA-256:
  `f4ab4cf8f58f4a3e28aca49a80c57d06571f24435abe5d424803f57596310902`.
- Android debug signer certificate SHA-256:
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
- Server/build/Drive copies are byte-identical. ZIP, endpoint, package, v1/v2
  signature, `testDebugUnitTest`, `lintDebug` and `assembleDebug` checks passed after
  the final web assets were synchronized.

**Status date:** 2026-07-20

**Environment:** CHH development, `https://class.familyherohub.com`

**Source checkpoint:** `main`, tag
`chh-s26k-admin-receipt-mopup-2026-07-20`

## S26j Messaging v1 contact-hours/outbox checkpoint

Messaging v1 Slice 10 is deployed on CHH development. Parent messages still commit
and appear to staff immediately; only the new per-recipient notification foundation
is held outside configured school contact hours. No push, email, or other provider
delivery is implemented in this slice.

- United International School uses `Asia/Muscat`, Sunday-Thursday 07:30-15:00,
  Friday/Saturday closed, and policy version `4`. Contact hours are enabled in the
  fixed `delay_notifications_only` mode. Teacher urgent marking and personal staff
  out-of-hours opt-in are disabled. The initialization is append-only audited.
- Alembic head is `c8d9e0f1a2b3`. Pre-migration pgBackRest full backup
  `20260720-062615F` completed successfully. The repository's existing pgBackRest
  stanza requires the explicit `--pg1-user=classhero` override for backup commands.
- The separate `notification_scheduler` service is enabled and running. It performs
  policy re-evaluation and crash-safe leasing only; Slice 11 will own provider
  dispatch. The outbox contained zero rows immediately after rollout, as expected
  before a new post-deployment message.
- CHH backend, frontend, and notification scheduler were built/recreated without
  restarting or recreating PostgreSQL. Public `/api/health`, `/messages`, and `/`
  returned HTTP 200; startup and scheduler logs contained no application error.
- Validation passed 429 backend tests with 2 skips, a fresh PostgreSQL upgrade,
  downgrade/re-upgrade, JSONB and concurrent `SKIP LOCKED` checks, a production web
  build, Svelte checking with 0 errors/0 warnings, and EN/AR parity at 1,274 keys.
  Focused source/UI assertions for Slice 10 pass; three documented legacy regex or
  safe-bottom assertions remain stale and unrelated to this slice.

### Development contact-hours APK

- Server: `/opt/apps/class_hero_hub/tmp/class-hero-hub-contact-hours-dev.apk`
- Google Drive: `G:\My Drive\CHH\Remote\class-hero-hub-contact-hours-dev.apk`
- Package: `com.classherohub.app`; version code `1`, version name `1.0`; min SDK 23,
  compile/target SDK 35; native API `https://class.familyherohub.com/api`.
- Size: 95,954,195 bytes; SHA-256:
  `6dee024626863e0bef33e761f6c7a378a97d6bccfaa22c588bdc0085ba6f01ba`.
- Android debug signer certificate SHA-256:
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
- Server and Drive copies are byte-identical. Endpoint, package, v1/v2 signature,
  `testDebugUnitTest`, `lintDebug`, and `assembleDebug` checks passed after the final
  web assets were synchronized. Physical-device execution of the Slice 10 smoke
  matrix remains required.

**Status date:** 2026-07-20

**Environment:** CHH development, `https://class.familyherohub.com`

**Source checkpoint:** `main`, tag
`chh-s26j-messaging-contact-hours-2026-07-20`

## S26i Messaging v1 delivery/read receipts checkpoint

Messaging v1 Slice 9 is deployed to the CHH development stack. Outgoing message
bubbles now show one gray tick for sent, two gray ticks after at least one eligible
ordinary participant's client renders and acknowledges the message, and two blue
ticks after at least one eligible ordinary participant views it. No recipient
identities, counts, all-read state, or safeguarding-admin activity are exposed.

- CHH remains the authoritative message, access-history, policy, receipt-event, and
  aggregate source. FHH remains a credential-hiding proxy; no receipt persistence was
  added there.
- Delivery and read visibility are independent, versioned school controls. United
  International School is enabled for both in development at policy version `3`;
  the existing immutable policy audit records the change. Defaults remain delivery
  on and read off for other/new policy rows.
- Receipt aggregation uses one bounded set query for the page/delta candidate set.
  A representative 50-message history increases from 27 to 28 SELECTs, independent
  of message and participant count. Historical eligibility is evaluated at receipt
  event time, so valid evidence survives later revocation and late joiners do not
  inherit earlier messages.
- Only the CHH backend/frontend and FHH backend/frontend services were rebuilt and
  recreated. The CHH and FHH PostgreSQL containers were not restarted or recreated.
  No migration or database backup was needed because existing receipt events,
  access grants, policy rows, and polling cursors are reused.
- Loopback and public API health checks returned HTTP 200 with `status=ok`; CHH
  `/messages` and FHH `/school-messages` returned HTTP 200 after deployment.
- Focused validation covers sent/delivered/read transitions, all four policy states,
  event-time eligibility and revocation, late joiners, safeguarding-admin exclusion,
  sender exclusion, closed-world FHH proxy sanitization, text/photo/voice parity,
  receipt-only polling without row remounts, state monotonicity, narrow layout, and
  EN/AR accessible ticks. Receipt-specific Playwright flows passed in both apps.

### Development receipt APK

- Server: `/opt/apps/class_hero_hub/tmp/class-hero-hub-message-receipts-dev.apk`
- Google Drive: `G:\My Drive\CHH\Remote\class-hero-hub-message-receipts-dev.apk`
- Package: `com.classherohub.app`; version code `1`, version name `1.0`; min SDK 23,
  compile/target SDK 35.
- Native API: `https://class.familyherohub.com/api`.
- Size: 95,807,045 bytes.
- SHA-256: `5dc8fbcab2cff03e0941543d08664afaae2177c6f8381b7f57f37d6b11021124`.
- Android debug signer certificate SHA-256:
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
- Server and Drive copies are byte-for-byte identical. APK package, endpoint, and
  signature checks passed. App-scoped `testDebugUnitTest`, `lintDebug`, and
  `assembleDebug` passed after the final web assets were synchronized into Capacitor.

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

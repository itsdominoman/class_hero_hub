# FHH Messaging Integration Operations

## Generated report/certificate document boundary (2026-08-06)

CHH now supports one immutable school-generated behaviour report or confirmed
recognition certificate on a message. Only the active staff membership that
generated the 24-hour stage may attach it; FHH parent sends cannot supply a staged
document identifier. Attachment is mutually exclusive with photos and voice notes,
and the normal stable client-message UUID preserves idempotent retry.

Downloads require current conversation participation and exact message-sequence
access on every request. CHH validates the stored size and SHA-256 before returning
PDF/CSV bytes with private/no-store/nosniff/same-origin headers. The FHH projection
contains only opaque ID, approved type, safe filename, content type, size and
availability; it never contains a storage key, checksum, generator identity, source
reference or direct URL. Abandoned stages expire after 24 hours. Once attached, the
document follows message retention and legal-hold candidate selection; bytes are
unlinked only after the disposal transaction commits.

## Production assertion boundary and protected-destination gate (2026-07-27)

Production School Chats and surveys are enabled. CHH must select the assertion
secret from the active link's stored `integration_environment`; production links
never fall back to the development `FHH_MESSAGING_ASSERTION_SECRET`. Production
requires both `FHH_PRODUCTION_MESSAGING_ENABLED=true` and a non-empty
`FHH_PRODUCTION_MESSAGING_ASSERTION_SECRET`. Startup validation also rejects a
production assertion value that matches the development assertion secret or either
integration service bearer.

FHH production's reciprocal `CHH_MESSAGING_ASSERTION_SECRET` is stored only in its
backend-scoped, mode-600 bridge environment file. Compare presence and a
non-reversible fingerprint only. Never print or copy the value between
environments.

Before emitting `school_chat` or `survey`, the CHH scheduler evaluates whether the
destination can authenticate the protected route for that row's environment. An
unavailable chat destination is cancelled with
`school_chat_destination_unavailable`; unavailable survey assertion configuration
is cancelled with `survey_destination_unavailable`. This guard does not suppress
points, homework, notice, calendar or update notifications. The provider repeats
the same check defensively so a direct invocation cannot emit an unusable protected
deep link.

## Environment-bound bridge selection (2026-07-27)

Every CHH `fhh_links` row records `development` or `production` from the service
credential that redeemed its invite. Notification dispatch must select the bridge
configuration from that stored environment; it must never infer the target from a
student, household, link age or current global overlay. The development bridge uses
the generic `FHH_NOTIFICATION_*` settings. Production is separately enabled with
`FHH_PRODUCTION_NOTIFICATION_ENABLED` and uses only
`FHH_PRODUCTION_NOTIFICATION_*`. URLs and all four bearer/HMAC secrets are distinct.

The normal family notification outbox remains one durable row per active opaque CHH
link. A student linked in both environments therefore produces two rows, but each
row is signed and sent only to its matching private FHH server. FHH independently
requires the corresponding connection and resolves eligible household adults and
production-package installations locally.

## Production school-link and notification boundary (2026-07-27)

Production FHH school linking and protected linked-school access are enabled with a
dedicated production service bearer. CHH retains the separate development bearer
bound to `10.250.50.1/32` and accepts the production bearer only from
`10.250.50.2/32`; a bearer from one environment is not valid from the other
environment's source. FHH retains the HTTPS base URL
`https://class.familyherohub.com`, while Compose maps that hostname to
`10.250.50.5` inside only the backend and lifecycle worker. This preserves private
mesh routing, normal TLS hostname/certificate validation, bounded client pooling and
timeouts. Browser and APK clients continue to call only FHH and receive no CHH
credential or direct CHH URL.

The reciprocal notification path is the literal private endpoint on
`10.250.50.2:8000`. The CHH scheduler permits that plain-HTTP target only because
the complete URL and exact ingestion path are also present in its approved private
endpoint allowlist. FHH accepts only source `10.250.50.5/32`; bearer/HMAC secrets
are dedicated production values, distinct from school-link and development
credentials. Timestamp skew, UUID nonce/replay protection, exact-byte hashing,
five-second timeout and redirect rejection remain mandatory.

FHH production School Chats and surveys are enabled only with the dedicated
production assertion relationship described above. Enabling school links or the
notification worker alone does not enable either protected destination. The
installed production package remains `com.familyherohub.app`.

Before the first real link, create a CHH **FHH invite** through
`POST /api/school/students/{student}/fhh-invites`; a guardian invite is a separate
flow and is not accepted by `/api/integrations/fhh/link/verify`. After linking,
confirm one active CHH `fhh_links` row and one active FHH `school_connections` row,
then use only a fresh controlled notification. Never reset or retry old dead outbox
rows for this acceptance.

CHH service-bearer failures return 401 and are transport/authentication failures, not
proof that an individual family link was revoked. FHH must retain the active local
connection for that response. Only CHH's explicit missing/gone link responses (404
or 410) mark the local connection remotely revoked. This distinction prevents a
server credential deployment error from destroying a valid family-to-school link.

Rollback restores the timestamped mode-600 environment copies recorded in
`CHH_CURRENT_DEPLOYMENT.md`, reverts the associated Compose change, and recreates
only CHH `backend` and `notification_scheduler` plus FHH `backend`,
`lifecycle_worker` and `notification_worker`. No database downgrade or APK rebuild
is involved.

## Slice 12 restricted/closed projection

CHH remains the safeguarding authority. FHH accepts only the closed-world
`participant_state` values `active`, `read_only` and `closed`; it recomputes
`read_only` and forces `can_send=false` outside active state. Its allowlist drops
restriction types, confidential and safe reasons, reviewer/session identity, internal
notes/flags, moderation and audit history. No safeguarding review call traverses FHH,
and review creates no FHH notification event or participant receipt.

The parent UI preserves authorised history and shows only “This conversation is
currently read-only.” or “This conversation has been closed by the school.” It
disables all text/photo/voice reply paths from the safe state. There is no restriction
or closure push in Slice 12.

## S25q protected voice boundary

Voice upload follows the same CHH-authoritative principle as photos with stricter
media rules. FHH reads at most 8 MiB into memory, binds actual size/SHA-256 and the
opaque upload UUID into its one-use actor assertion, and forwards bytes only
server-to-server. CHH reauthorizes and normalizes to AAC-LC/M4A; FHH persists no
audio. Playback is requested only on Play and returns transient `audio/mp4` with
private/no-store/nosniff headers. The safe metadata allowlist is id, duration, size,
AAC/MP4/content type, availability and `not_requested` transcription state.

The `capabilities.voice_notes` value is authoritative from CHH. Disabled means no new
upload/send; existing protected notes remain playable to currently authorized
participants. See `../implementation/MESSAGING_V1_VOICE_NOTES.md`.

## Slice 8 protected media boundary

FHH uploads bytes server-to-server only after parent/family/child/active-connection
validation. Its short-lived actor assertion binds the opaque upload UUID, SHA-256 and
size; CHH then independently verifies link, identity, participant and conversation
scope before processing. Thumbnail/full requests repeat current access validation.

FHH must expose only the media allowlist (`id`, order/state/type/dimensions/sizes and
availability). Never forward CHH storage keys, paths, source checksums, filenames,
credentials, raw upstream errors or direct URLs. Rebuild private/no-store/nosniff
headers at the FHH boundary. A media 404/409 is item-scoped and must not revoke the
durable school connection. FHH does not persist media or message history.

For abandoned CHH stages, run the dry-run cleanup command documented in
`../implementation/MESSAGING_V1_PROTECTED_PHOTOS.md`; there is deliberately no Slice
13 retention worker yet. Slices 9–13 remain pending.

**Status:** Slices 5–7 plus S25h live-refresh/context and S25i CHH Android
safe-area/Back hardening enabled for United International School development testing,
2026-07-17. Production remains disabled.
**Architecture authority:** [`../planning/2026-07-messaging-v1-architecture-plan.md`](../planning/2026-07-messaging-v1-architecture-plan.md)
**Hardening evidence:** [`../implementation/MESSAGING_V1_TEXT_HARDENING.md`](../implementation/MESSAGING_V1_TEXT_HARDENING.md)

## Runtime boundary

CHH is authoritative for messaging. FHH clients call only FHH. FHH calls the
`/api/integrations/fhh/links/{link_id}/messaging/*` family with:

1. the existing FHH service bearer;
2. the exact link credential in `X-FHH-Link-Token`;
3. a per-request actor assertion in `X-FHH-Messaging-Actor`.

The assertion uses a dedicated secret, fixed issuer/audience, five-minute maximum
lifetime, random one-time `jti`, opaque school-scoped parent subject, link ID, trusted
display name/locale, HTTP method, URL path, and canonical body hash. It is never put in
a URL or retained by CHH. CHH stores only one-time replay evidence in
`fhh_messaging_assertion_uses`.

Required configuration:

- CHH development: `FHH_MESSAGING_ASSERTION_SECRET`
- CHH production: `FHH_PRODUCTION_MESSAGING_ENABLED=true` and
  `FHH_PRODUCTION_MESSAGING_ASSERTION_SECRET`
- FHH: `CHH_MESSAGING_ASSERTION_SECRET`

Each environment's reciprocal pair must match, while development and production
must differ. Neither may match a service bearer or link credential. Issuer defaults
to `fhh-school-messaging`; audience defaults to `chh-school-messaging`. Never print
either secret during comparison or recovery.

## Endpoint families

- `GET .../inbox` and `GET .../unread-count`
- `GET .../recipients`
- `POST .../conversations`
- `GET .../conversations/{conversation_uuid}`
- `GET .../conversations/{conversation_uuid}/messages`
- `POST .../conversations/{conversation_uuid}/messages`
- `POST .../conversations/{conversation_uuid}/acknowledgements`

Every route resolves the active CHH link first and confines access to that link's
school and student. Conversation and message IDs are opaque UUIDs. Recipient
references are encrypted, expire after 24 hours, and are school/student bound.
Responses use closed DTOs plus `Cache-Control: private, no-store`.

Message-history GET accepts the existing signed historical `cursor` or an
`after_sequence` delta boundary, never both. A visible CHH or FHH thread uses the
delta form every 12 seconds, merges rows append-only, and refreshes immediately on
focus/visibility/app resume. Polling stops while hidden/offline and all scope and
revocation checks are repeated for every delta request. `latest_sequence` is a
server-owned boundary, not a client authorization claim.

Student class/grade, exact guardian relationship and current staff role/subjects are
derived from CHH's dated enrolment/assignment/participant state and returned only in
closed DTO fields. FHH and native/browser clients must never supply or override this
context.

## Failure and recovery

| Result | Meaning | Operator action |
| --- | --- | --- |
| `401` | Missing/invalid/expired assertion or request binding | Check matched assertion secret, issuer/audience, clock, and FHH backend version; do not retry the same assertion |
| `404` | Feature/policy disabled, link revoked, or scoped resource absent | Confirm flags/policy and durable link state; never swap to another child's link |
| `409` identity sync required | FHH lifecycle state has not reached CHH or profile snapshot differs | Inspect/retry the FHH lifecycle outbox; do not bypass synchronization |
| `409` assertion already used | Duplicate assertion replay | Create a new assertion; retain the same message client UUID for send reconciliation |
| `400` recipient/cursor invalid | Expired, tampered, or wrong student/school reference | Refresh recipient/inbox data |
| FHH `502` | CHH transport/transient service failure | Retry safely; sends retain their stable client UUID |

Lifecycle reconciliation remains owned by the FHH database outbox. Message commits do
not depend on FHH persistence, notification delivery, or any worker.

Expired assertion-use rows are indexed for a later bounded cleanup/retention slice.
No cleanup worker is part of Slice 5.

## Development pilot and verification

The named development pilot is intentionally configured as follows:

- CHH `MESSAGING_ENABLED=true`
- FHH `SCHOOL_MESSAGING_ENABLED=true`
- only the United International School CHH policy is enabled

This configuration is development-only and must not be copied into production.
Confirm the global flags and exact school policy before every test session and after
rollback. Protected photos, protected voice notes and Slice 9 receipt display are
implemented. Contact-hours, notification bridge, push/deep links, safeguarding
administration UI, and retention worker remain unimplemented.

## Slice 9 safe receipt projection

CHH adds `receipt` only to outgoing message rows and supplies bounded
`receipt_updates` during delta polls. The projection contains only visibility flags,
aggregate delivered/read booleans, `sent|delivered|read`, and a policy version. FHH
must apply a closed-world sanitizer and never forward unknown fields, identities,
counts, family/account IDs or tokens. Signed delivery/read acknowledgements retain the
existing canonical body and actor assertion flow. An FHH proxy fetch never counts as
delivery; the actual FHH client acknowledges only after rendering the active thread.

One eligible family adult is sufficient for Delivered or Read. Individual evidence
remains in CHH, late joiners and safeguarding-only administrators do not count, and a
later revocation cannot regress valid historical Read evidence.

A CHH administrator who is the conversation's named primary staff participant is not
a safeguarding-only viewer and counts like any other recipient. Parent-to-admin
Delivered/Read therefore advances when that administrator opens the normal CHH
thread. Conversely, the FHH grown-up's signed participant acknowledgements continue
to advance admin-to-parent messages. FHH never sends a staff role or membership
context; dual-role selection and safeguarding review remain CHH-only concerns.

S25i changed no messaging API, schema, credentials, assertion binding or FHH proxy.
Its deployment used CHH backup `20260717-073438F`, left Alembic at
`e4f5a6b7c8d9`, and rebuilt/restarted only the CHH frontend. Post-deploy verification
confirmed CHH `MESSAGING_ENABLED=true`, only United International School enabled,
and 3 conversations/17 messages/12 participants/9 receipt events/230 assertion-use
rows. The CHH frontend and public `/messages` returned 200, direct/public API health
passed, and anonymous messaging and protected-media requests remained denied.

The S25i APK is
`/opt/apps/class_hero_hub/tmp/class-hero-hub-s25i-dev.apk`, 95,845,408 bytes,
SHA-256 `55c777e0e344f7777fb308e6cc7d9233f672c01f93ad5b12f6554cef82077834`.
Real-device gesture/three-button, IME and ordered Back checks remain required.

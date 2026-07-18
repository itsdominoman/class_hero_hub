# FHH Messaging Integration Operations

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

- CHH: `FHH_MESSAGING_ASSERTION_SECRET`
- FHH: `CHH_MESSAGING_ASSERTION_SECRET`

The values must match one another and must not match the service bearer or a link
credential. Issuer defaults to `fhh-school-messaging`; audience defaults to
`chh-school-messaging`. Never print either secret during comparison or recovery.

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
rollback. Photos, final receipt display, contact-hours worker, notification bridge,
push/deep links, safeguarding administration UI, and retention worker remain
unimplemented.

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

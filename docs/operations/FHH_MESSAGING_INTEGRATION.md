# FHH Messaging Integration Operations

**Status:** Slices 5–7 proxy, parent UI, and text hardening deployed dark on development, 2026-07-17.
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

## Dark rollout and verification

Keep both global flags false until a named pilot:

- CHH `MESSAGING_ENABLED=false`
- FHH `SCHOOL_MESSAGING_ENABLED=false`

Slice 7 E2E and security gates are complete. Keep the feature dark until a named pilot
also completes the plan's policy, disclosure, support, and operational approval gates;
Slice 7 completion is not automatic pilot authorization. FHH contains a feature-gated
parent text UI, but photos, final receipt display, contact-hours worker, notification
bridge, push/deep links, safeguarding administration UI, and retention worker remain
unimplemented.

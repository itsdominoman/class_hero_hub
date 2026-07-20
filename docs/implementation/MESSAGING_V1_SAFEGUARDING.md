# Messaging v1 safeguarding review and evidence architecture

**Slice:** 12 / S26m
**Environment implemented:** CHH and FHH development only
**Date:** 2026-07-20
**Production:** unchanged and disabled

## Non-participation invariant

Safeguarding review is an administrative evidence projection, not conversation
participation. Starting or opening a review creates only a
`safeguarding_review_sessions` row and immutable messaging audit events. It does not
create a `conversation_participants` row or access grant, invoke participant delivery
or read acknowledgements, change a participant cursor, clear unread state, enqueue a
notification, or reveal the reviewer to ordinary participants.

A school administrator who is already named as a real participant continues to use
the ordinary Messages route with ordinary participant receipt semantics. A dual-role
user must supply the explicit school membership header and enter
`/school/safeguarding/message-reviews`; the safeguarding route never infers access
from the teacher or administrator role.

## Explicit permission model

`messaging_permission_grants` stores active and revoked school-scoped grants:

- `messaging.safeguarding_review` — metadata search, reason-gated review and protected
  review media;
- `messaging.moderate` — restrictions, close/reopen, flags, append-only notes and
  tombstone/restore;
- `messaging.export_evidence` — internal evidence package generation and bounded
  download;
- `messaging.export_internal_notes` — additional authority to include internal notes
  in an internal export;
- `messaging.manage_safeguarding_permissions` — grant/revoke and review-session
  revocation administration.

Role alone grants nothing. Actor resolution requires the authenticated user, active
user status, active non-revoked membership, active/pending-setup school and exact
school/membership match. Unknown, inactive, ungranted and cross-school contexts fail
closed. Grant and revocation history is retained; a partial unique index prevents two
simultaneous active copies of one grant.

## Metadata discovery and review sessions

`GET /api/safeguarding/conversations` is bounded to 50 results and 30 searches per
reviewer/minute. It filters by opaque/full conversation reference, student, active
class/grade enrolment, participant name/kind, date, status, flag/restriction/closure,
branch, message type and direction. It does not accept full-body search and never
returns message body previews.

Starting a review requires one conversation, an allowlisted reason category, a
meaningful 8–2,000 character justification, explicit audit acknowledgement and a
5–60 minute lifetime (30 minutes by default). The public session UUID is bound to one
school, conversation and reviewer membership. End, expiry or manager revocation makes
it unusable. Expiry is recorded lazily on access and by the cleanup command.

`GET /api/safeguarding/reviews/{session}` is a separate projection. It provides the
authorised timeline, participant/receipt evidence, protected photo/voice descriptors,
internal flags/notes, moderation history, export history and bounded immutable audit
history. It advertises `has_composer: false`. Review media routes repeat the current
actor, permission, session, school, conversation, message and media checks and return
private/no-store responses. Routine access logs redact safeguarding media and export
paths.

## Moderation and participant effects

Conversation restriction is explicit: `family_replies`, `staff_replies`,
`both_replies`, or `read_only`. Ordinary send authorization checks the current
participant side in the backend; the frontend is only a secondary control. Closure
retains the history and protected media but blocks both sides. Reopen and restriction
removal require `messaging.moderate` and a live review session. A neutral optional
participant-facing explanation is stored with the moderation evidence; confidential
reasons remain internal.

Internal notes are separate append-only records and corrections point to the prior
note. They are not messages, do not increment sequences, and do not reach FHH,
receipts, unread counts or notifications. Flags can target the conversation or one
message and carry category, severity, follow-up state and optional internal
assignment/note.

Tombstoning changes the ordinary projection to an unavailable item, removes body and
media descriptors, and denies ordinary photo/voice routes. It does not delete or
rewrite the original message/media. An authorised review and evidence export retain
the original content and protected files. Restore is a new audited moderation action.
PostgreSQL triggers and ORM listeners reject UPDATE/DELETE of internal-note and
moderation-action evidence rows.

FHH receives only `participant_state: active|read_only|closed`, a coherent `read_only`
boolean and `can_send: false` outside active state through its existing child-scoped
allowlist proxy. It receives no restriction type, confidential reason, review reason,
reviewer, internal note, flag or audit field. Its family UI uses only the neutral
wording “This conversation is currently read-only.” or “This conversation has been
closed by the school.”

## Internal evidence package

Slice 12 implements only the explicitly authorised `internal` privacy mode. The ZIP
is generated server-side in random protected storage and contains:

- `transcript.html`, with chronological human-readable messages and clearly labelled
  internal notes when separately authorised;
- `manifest.json`, schema `chh.messaging.evidence.v1`;
- protected photo and voice copies under safe generated `media/` names.

The manifest contains conversation/participant metadata, UTC and school-local
timestamps, sender identity/role, message/tombstone state, receipt evidence,
moderation hashes/history, an attachment inventory, export creator/reason/time/expiry
and optional separately labelled internal notes. Every included file has size and
SHA-256. `integrity.canonical_payload_sha256` hashes the UTF-8, sorted-key, compact
manifest payload before the `integrity` member is added. The database also stores the
whole-ZIP SHA-256 and manifest hash.

Limits are 5,000 messages, 500 media files and 100 MiB. A reviewer may request five
exports/hour. An artifact expires after 30 minutes and permits at most three
authenticated downloads; every request, generation, download, failure and expiration
is audited. No public URL, private path, token, credential, automatic email or
arbitrary URL fetch is present. Participant-safe export is intentionally not exposed;
the manifest privacy-mode field reserves a compatible future variant without risking
an inadequately redacted package now.

## Audit and retention boundary

Stable UUID audit events record search, review start/open/end/expiry/revocation, media
access, permission changes and denials, notes/flags, all moderation transitions, and
the export lifecycle. Events include school, actor user/membership context, target
references, safe correlation metadata and prior/new state hashes where relevant.
Generic audit metadata excludes message bodies, note bodies, credentials, tokens and
storage paths; protected authoritative rows hold the detailed evidence.

`backend/scripts/cleanup_safeguarding_state.py` expires review sessions, removes
expired export files by validated storage key, marks artifacts expired and writes
system audit events. This is the complete Slice 12 cleanup boundary. Slice 13 still
owns message/media retention schedules, legal hold, archival, disposition approvals,
long-term evidence custody, participant-safe disclosure policy and organisation-wide
retention automation.

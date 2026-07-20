# Messaging contact hours and notification outbox

## Scope

Messaging v1 Slice 10 separates message acceptance from notification scheduling.
The message transaction commits the message, media attachment/audit work, and one
durable outbox row per recipient/channel together. Contact hours never delay the
message itself: authorized staff can see a committed parent message immediately by
opening CHH. Slice 10 does not call FCM, email, or FHH notification delivery.

The only supported mode is `delay_notifications_only`. Hiding messages until opening
and blocking parent sends are not implemented controls.

## Policy precedence

1. Global messaging disablement, school suspension, school policy disablement,
   inactive message/conversation, and recipient/link revocation cancel an
   undispatched row.
2. An authorized urgent message or an effective school-permitted personal staff
   opt-in is immediately eligible.
3. A guardian-originated staff notification outside contact hours is held until the
   next opening. Staff-to-guardian notifications are never held by this policy.
4. Dispatched/completed rows are terminal and are never recalled by policy changes.

Weekly windows are ISO weekdays (`1` Monday through `7` Sunday), expressed as local
wall-clock times in `schools.timezone`. A date exception overrides that date's weekly
window. End time less than start time crosses midnight. Ambiguous DST openings use
the earliest valid instant, ambiguous closings the latest, and nonexistent wall
times advance to the next valid minute. The resulting `eligible_at` is stored in UTC.

## Durable states

- `held`: valid, but contact policy has not opened.
- `pending`: policy-eligible foundation for Slice 11 dispatch; no provider call has
  occurred in Slice 10.
- `leased`: temporarily owned by one scheduler process.
- `failed` / `dead`: scheduler processing failed and exhausted bounded backoff.
- `cancelled`: recipient, message, conversation, school, or messaging eligibility
  ended before dispatch.
- `dispatched` / `provider_accepted`: reserved terminal delivery states for Slice 11.

Claims use PostgreSQL `FOR UPDATE SKIP LOCKED`, commit the lease before work, and
recover an expired lease after a worker crash. The scheduler rechecks active rows at
a bounded interval and immediately detects a `policy_version` mismatch. It stores no
message body in `template_args`; only opaque conversation/message identifiers and an
internal deep link are persisted.

## Configuration and rollout

The scheduler is a separate Compose service:

```text
notification_scheduler -> python -m app.messaging_notification_worker
```

Set `MESSAGING_NOTIFICATION_SCHEDULER_ENABLED=true` only after migration and backend
deployment. The poll, batch, lease, recheck, retry, and maximum-attempt settings are
documented in `.env.example`. Stopping this service is the operational rollback:
message sending and in-app visibility continue and outbox rows remain durable.

The initial United International School development policy is applied explicitly and
idempotently after migration:

```bash
docker compose run -T --rm backend python -m scripts.configure_messaging_contact_hours \
  --school-slug united-international-school \
  --confirm united-international-school
```

The command preserves the existing IANA timezone, does not enable messaging, changes
no other school, sets Sunday-Thursday 07:30-15:00, closes Friday/Saturday, disables
teacher urgent and personal opt-in, increments the policy version, and writes an
append-only school audit record. Repeating the exact configuration is a no-op.

## Safe diagnostics

School administrators can read aggregate state only through
`GET /api/school/messaging-notification-outbox`. It returns counts, oldest held row,
and next eligible time; it exposes no message body or recipient identity.

Operator queries should group by `school_id` and `state`, and examine
`eligible_at`, `scheduler_check_at`, lease age, attempts, and sanitized error code.
Never log or export message bodies, FHH/link credentials, user/device identifiers, or
notification provider credentials. A growing `dead` count, an expired lease older
than two lease periods, or an eligible row still held after the recheck interval is
an incident. Do not manually mark a row dispatched; Slice 11 owns delivery and replay
semantics.

## Validation and rollback

Before rollout, validate a fresh PostgreSQL upgrade, one-revision downgrade and
re-upgrade, JSONB shape, outbox checks, real concurrent disjoint claims, lease expiry,
policy release/re-hold, DST/overnight/exception calculation, recipient cancellation,
and immediate in-app message visibility. Take a pgBackRest full backup before the
development migration.

Rollback order is: stop `notification_scheduler`, disable contact hours if necessary,
and forward-fix application code while retaining rows. The additive migration may be
downgraded only before real outbox/contact configuration is relied upon; do not drop
durable rows as a routine application rollback.

## Slice 11 Android provider dispatch

Slice 11 extends the same scheduler service; it does not add a second CHH queue.
Eligible CHH-device rows are fanned out to durable per-installation deliveries and
sent with Firebase Admin. FHH-link rows are posted as signed, timestamped, nonce-bound
events to the private FHH bridge. CHH stores neither parent/family identifiers nor
FHH tokens. Delivery leases, retry limits, invalid-token revocation, terminal provider
errors and crash recovery are persisted independently from the source outbox row.

Notifications use generic English/Arabic copy and opaque allowlisted route targets.
They contain no message body, media details, private URL or safeguarding context.
Normal held messages are bundled per conversation and installation when contact hours
reopen; an authorized urgent exception may bypass that bundle. Provider acceptance,
display and tap never write Delivered or Read receipts.

The sender service reads Firebase and bridge settings only from the ignored
`.env.push` file. Keep it mode `0600`. Backend and frontend services must not receive
those settings. Safe rollout is: back up PostgreSQL, validate upgrade/downgrade/
re-upgrade on a restored copy, apply the additive migration, recreate backend and
`notification_scheduler`, then inspect aggregate outbox and delivery states. Stop the
scheduler to pause provider calls without interrupting message commitment or in-app
visibility.

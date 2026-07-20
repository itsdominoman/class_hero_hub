# Messaging safeguarding operations

This runbook applies to CHH development Slice 12. It does not authorise production
enablement.

## Access administration

Use **School → Safeguarding → Message reviews**. The navigation item is returned only
after `GET /api/safeguarding/context` proves an active explicit grant. A permission
manager can grant or revoke one school-scoped permission at a time with a meaningful
reason. Never grant all school administrators by role or copy grants between schools.

For a suspected compromise, suspend the user or membership, revoke its grants, and
revoke any active review session. Any of those actions makes subsequent review calls
fail closed. Preserve the audit/event UUIDs and do not edit protected evidence rows.

## Review and moderation procedure

1. Search metadata only and identify the exact opaque conversation reference.
2. Select **Start review**, choose the real reason category, write a case-specific
   justification and acknowledge auditing.
3. Confirm the banner shows the intended reviewer, school, conversation and expiry.
4. Review evidence without opening the ordinary participant inbox.
5. For moderation, enter a confidential reason. Add participant-safe wording only if
   a neutral explanation is intended; it must not disclose safeguarding details.
6. End the session when finished. Do not share the review URL or downloaded package.

Restrictions and closure do not send a push notification in Slice 12. Check both CHH
and FHH participant projections after a change. Internal notes and flags must never be
copied into a normal message.

## Evidence export and verification

Only generate the internal package for an authorised purpose. Including internal
notes requires the separate `messaging.export_internal_notes` grant. Downloads are
private, expire after 30 minutes and stop after three successful accesses.

To verify an extracted package offline, calculate SHA-256 for every file listed in
`manifest.json`, then remove the top-level `integrity` object and hash the remaining
JSON using UTF-8, sorted keys and compact separators. It must equal
`integrity.canonical_payload_sha256` and the database `manifest_sha256`. Verify the
original ZIP against `artifact_sha256`. Never upload an evidence package to a public
hashing website.

## Cleanup

Run the bounded application cleanup from the backend image/service account:

```sh
python /app/scripts/cleanup_safeguarding_state.py --limit 100
```

The command marks expired sessions, deletes only validated random export storage keys,
marks expired rows and audits the result. A missing file is safe and idempotent. Do
not manually delete database evidence or message media. Monitor protected export
storage size and `safeguarding.export_failed` events.

## Backup and migration gate

Before a safeguarding schema change, take a restorable custom-format database dump
and a pgBackRest full backup. Run pgBackRest as the PostgreSQL OS account with the CHH
database role explicitly supplied. Record backup label/path, byte size and SHA-256,
then prove `pg_restore --list` can read the dump. Validate upgrade, practical downgrade
and re-upgrade on a disposable restored PostgreSQL database before touching dev.

The Slice 12 revision is `e0f1a2b3c4d5` (parent `d9e0f1a2b3c4`). Confirm both
append-only triggers after upgrade. Do not restart PostgreSQL for this migration.

## Incident checks

- A review altered unread or receipts: stop deployment, snapshot the conversation's
  participant/receipt rows and audit events, and preserve notification outbox rows.
- FHH exposes an internal field: disable the affected frontend/backend service and
  inspect the FHH allowlist projection; never patch by sending a replacement reason.
- Export hash mismatch: deny download, preserve the artifact and audit UUID, and treat
  it as an integrity incident.
- Storage growth: run the bounded cleanup and investigate unexpired/failed jobs; do
  not widen paths or use recursive deletion.

Complete retention, legal-hold and archival operations remain Slice 13.

# Messaging v1 operations and incident-response runbook

## Health thresholds

Page on: production-worker heartbeat older than 120 seconds; any dead operations/notification row; oldest eligible notification older than 300 seconds; any export generation or retention/archive verification failure; backup marker missing/older than 26 hours; archive disk at 80%; database pool saturation at 80%; send latency over 400 ms sustained; migration revision mismatch; FHH bridge failures above 5% over 15 minutes. External alert delivery is not configured by this slice: scrape the protected platform operations endpoint or translate these fields into the approved monitoring provider.

## First response

1. Declare the incident, record UTC start, environment, school scope, symptoms and correlation IDs—never bodies, tokens, legal-hold reasons or note content.
2. Check public/loopback health, container state, migration revision, worker heartbeats, oldest queues, dead counts, disk, database connections and backup marker.
3. Determine whether messages are committed. Notifications are secondary; do not resend a user message to repair push.
4. Pause destructive retention/archive execution if evidence custody, storage, database, backup, or legal-hold state is uncertain. Pending jobs can be cancelled; leased jobs accept a cancellation request.
5. For a dead row, inspect safe metadata, correct the dependency/permission, select at most 50 exact IDs, state a reason, and use the bounded retry. Never paste an arbitrary payload.
6. Revalidation on replay must pass current school/user/link/device/policy permissions. Confirm no duplicate visible message and no receipt regression.
7. For hash mismatch or missing media/export, preserve the files and logs, stop source deletion, restore only into a disposable target, and escalate to the safeguarding/privacy leads.

## Failure-specific actions

- **Worker lease/crash:** restart the affected worker; expired leases return to pending and increment recovery metrics.
- **Database restart:** wait for health/pool recovery, then confirm claims and idempotency. Do not reset job tables manually.
- **Media unavailable:** stop archival deletion, verify mounts/capacity/permissions and hashes; ordinary routes fail closed while safeguarding archive reads remain audited.
- **Export failed:** correct the dependency; retry the existing unexpired request. Do not create repeated downloads to bypass limits.
- **Bridge/FCM:** correct connectivity/credentials in the worker-only environment, revoke invalid device tokens, retry exact eligible rows.
- **School/user suspended mid-dispatch:** expected outcome is cancellation after revalidation.
- **Migration mismatch:** stop deployment, compare code/tag/revision, and use guarded forward migration. Downgrade a protected target only under the exact emergency override procedure.

Close with impact, affected counts, custody/hold confirmation, recovery evidence, remaining dead rows, timeline, root cause and preventive actions.

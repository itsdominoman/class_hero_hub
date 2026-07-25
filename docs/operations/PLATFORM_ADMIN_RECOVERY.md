# Platform administrator bootstrap and break-glass recovery

This runbook applies to development and pilot CHH environments. It must not be
used in production without explicit authorisation.

## First-run bootstrap

`PLATFORM_ADMIN_EMAILS` identifies the permitted first platform administrator,
but it grants nothing by itself. Bootstrap is allowed only when all of these
conditions are true:

1. `PLATFORM_ADMIN_BOOTSTRAP_ENABLED=true` is set explicitly;
2. the authenticated email is listed in `PLATFORM_ADMIN_EMAILS`; and
3. `platform_admins` contains no row, including revoked rows.

After the first administrator has authenticated and the
`platform_admin.bootstrap` audit row has been verified, set
`PLATFORM_ADMIN_BOOTSTRAP_ENABLED=false` and recreate only the backend service.
Normal authentication never reactivates a revoked platform administrator.

## Audited break-glass recovery

Use this only when no active platform administrator remains. Two authorised
operators must record the incident/change reference, intended recovery email,
reason, and approval before connecting over the restricted break-glass SSH
path. Do not enable first-run bootstrap against an existing
`platform_admins` table.

In a single PostgreSQL transaction:

```sql
BEGIN;

SELECT id, email, status
FROM users
WHERE lower(email) = lower(:recovery_email)
FOR UPDATE;

SELECT id, user_id, granted_at, revoked_at
FROM platform_admins
WHERE user_id = :recovery_user_id
FOR UPDATE;

UPDATE platform_admins
SET revoked_at = NULL
WHERE user_id = :recovery_user_id
  AND revoked_at IS NOT NULL;

INSERT INTO audit_logs (
  school_id,
  actor_user_id,
  action,
  entity_type,
  entity_id,
  detail
)
VALUES (
  NULL,
  :recovery_user_id,
  'platform_admin.break_glass_recovery',
  'platform_admins',
  :platform_admin_id,
  jsonb_build_object(
    'source', 'break_glass',
    'incident_reference', :incident_reference,
    'reason', :recovery_reason,
    'approved_by', :approver_reference
  )
);

COMMIT;
```

Abort rather than commit if the user is absent or inactive, the platform-admin
row is absent, any placeholder is unresolved, or more than one row would be
updated. Recovery reactivates an existing identity only; it does not create a
new platform administrator.

Afterwards, verify one row is active for the intended user and one matching
append-only audit row exists. Have the recovered administrator authenticate and
confirm platform access, then close the incident with the SQL transcript
metadata (never credentials, tokens, or private data). If the transaction fails,
run `ROLLBACK;`; no partial recovery or audit record should remain.

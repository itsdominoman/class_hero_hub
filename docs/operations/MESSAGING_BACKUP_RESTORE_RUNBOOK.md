# Messaging v1 backup and restore runbook

## Backup set

Back up PostgreSQL plus protected message media, local archive adapter, and temporary evidence-export directory with encrypted storage and restricted operators. Preserve audit, holds and durable worker state in PostgreSQL. Back up configuration templates, not live Firebase/bridge/session/database secrets; restore those through the approved secret manager/process. Record UTC, source revision/migration, pgBackRest label, dump/media paths, sizes, SHA-256, encryption state and retention.

The current development pgBackRest repository is not encrypted (`cipher: none`); this is acceptable only as a documented development limitation. Production requires an encrypted, access-controlled off-host repository and tested key recovery.

## Disposable rehearsal

1. Resolve and print an explicit target whose database name starts with `chh_validation_`; refuse all protected names/hosts.
2. Restore the database backup to that isolated target and copy media/archive/export snapshots to isolated paths.
3. Supply only disposable configuration/secrets. Run `backend/scripts/validate_migrations.py` for upgrade/downgrade/re-upgrade compatibility.
4. Start backend and workers against the restored target, with external push/bridge sending disabled.
5. Verify counts and samples for conversation timeline/order; photo/voice hash and protected access; receipt monotonicity; outbox/job states; safeguarding audit/moderation/notes; active and released holds; export metadata and package verifier.
6. Confirm application health, migration revision, query plans, worker claim/recovery, and no connections to development/production.
7. Record measured restore time (RTO observation) and the newest recovered transaction/media time (RPO observation). These are observations, not guarantees.
8. Stop containers, validate the exact disposable database/path, and delete only those isolated targets. Retain the signed rehearsal record.

## Recovery order

Secrets/configuration → PostgreSQL → hot media → archive media → protected exports → backend read-only checks → workers with external sending disabled → application smoke → controlled external delivery. Never run retention until backup, holds and restored evidence are verified.

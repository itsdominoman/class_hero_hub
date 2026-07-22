# Database backup and recovery (OPS-001)

## Architecture

Class Hero Hub uses pgBackRest with continuous WAL archiving and two independent,
client-side AES-256-CBC encrypted repositories. Repository 1 is the local Docker
volume `class_hero_hub_pgbackrest_repo_encrypted`. Repository 2 is an SFTP
repository on the separate Family Hero Hub development host. SFTP host keys are
checked strictly against a pinned `known_hosts` file; unknown or changed keys fail
the job.

The prior `class_hero_hub_pgbackrest_repo` volume is an inactive, unencrypted
historical repository. It is not part of the recovery architecture and must not be
reported as a current backup.

Database recovery is distinct from source/config and application media recovery.
The PostgreSQL repositories do not contain the bind-mounted `data/` tree, including
protected media or uploads. That tree requires a separately encrypted, tested
off-host file backup before complete host-loss recovery can be claimed.

## Schedule and retention

The `administrator` crontab is the single CHH scheduler:

- 02:15 Asia/Muscat daily: differential backup to both repositories; Sunday is full.
- 06:15 daily: cipher, integrity, freshness (30 hours), and `/api/health` check.
- 07:15 on day 1 monthly: isolated restore from off-host repository 2.

Both repositories retain four full backups and seven differential backups. WAL
needed by retained backups is kept by pgBackRest. `archive_timeout=300s` bounds WAL
archive delay during low activity. Jobs use `flock` and exit non-zero on overlap,
backup, SFTP, encryption, integrity, freshness, restore, or health failures.

Target pilot RPO is five minutes while both hosts and the SFTP path are healthy.
Target RTO is two hours for database recovery and application verification. Media
recovery is outside this RTO until the separate media gap above is closed.

## Credentials and trust (no values in Git)

- `.env.backup` in the repository root: pgBackRest repository passphrases, mode 0600.
- `/home/administrator/.config/class-hero-hub/backup-ssh/`: SFTP private/public key
  copy and pinned `known_hosts`, readable only by the PostgreSQL container user.
- `/home/administrator/.ssh/id_ed25519_restore_to_dev`: source SSH credential used
  to provision the restricted container-readable copy.

## Operator commands

Run from `/opt/apps/class_hero_hub`:

```bash
scripts/backup/pgbackrest-backup.sh status
scripts/backup/pgbackrest-health.sh
RESTORE_REPOSITORY=2 scripts/backup/pgbackrest-restore-rehearsal.sh
scripts/backup/install-user-cron.sh status
```

Machine-readable status is under `tmp/backup-status/`; cron output is in the system
journal under tags `chh-backup`, `chh-backup-health`, and
`chh-restore-rehearsal`. On failure, inspect those records and the status JSON,
correct storage/network/host-key/key/passphrase issues, then run a fresh backup and
health check. Do not suppress a changed host key. External paging is not configured
on this pilot host, so operators must monitor the stale/failed status file.

The restore rehearsal creates a unique Docker volume and network-isolated
PostgreSQL container, restores an off-host backup with pgBackRest checksum
verification, opens the database, records only the Alembic revision and aggregate
schema metadata, and removes the container and volume on exit. It never attaches
the restored volume to the live service.

> Historical note: This document was inherited from Family Hero Hub and is preserved as historical context for the Class Hero Hub fork. It may describe old domains, paths, product assumptions, or infrastructure that are not current.

# Restore PostgreSQL

## 1. Purpose
Restore production PostgreSQL data using the pgBackRest tarball.

## 2. Scope
PostgreSQL data directory and WAL archives.

## 3. When to use this restore path
Database corruption, accidental data loss, or full US server rebuild.

## 4. What this restores
PostgreSQL data content inside the Docker volume.

## 5. What this does NOT restore
App configuration or Docker Compose files.

## 6. Required access
Root/SSH on US Server (`10.250.50.2`).

## 7. Required offline secrets/keys
None for the DB restore itself, provided the `.env` with DB credentials is already restored.

## 8. Required backup source options
1. UK `/opt/apps/backups/from-us/us-pgbackrest-repo-*.tar.gz`
2. Google Drive

## 9. Required approval gates before destructive actions
Dom must explicitly approve restoring over a live production database. Ideally, restore to a non-production test target first.

## 10. Exact backup source paths
`us-pgbackrest-repo-*.tar.gz` (This contains the full pgBackRest repo structure, not just a subfolder).

## 11. Exact restore target paths
Docker volume: `/var/lib/docker/volumes/family-hero-hub_pgbackrest_repo/_data`

## 12. Exact commands

**PostgreSQL Restore Order:**

1. **Verify Environment:**
   - Compose service name: `postgres`
   - Container name: `family-hero-hub-postgres`
   - Data volume: `family-hero-hub_postgres_data`
   - pgBackRest volume: `family-hero-hub_pgbackrest_repo`
   - Config path: `/etc/pgbackrest/pgbackrest.conf` inside container.

2. **Stop Application (Crucial!):**
   Stop the backend/frontend from writing, and stop the existing postgres instance.
   ```bash
   cd /opt/apps/family-hero-hub
   sudo docker compose stop backend frontend postgres
   ```

3. **Identify correct tarball and verify SHA-256 checksum:**
   ```bash
   cd /tmp/recovery
   LATEST_PGBACKREST=$(ls -1t us-pgbackrest-repo-*.tar.gz | head -1)
   # Extract the matching manifest for the timestamp
   TIMESTAMP=$(echo "$LATEST_PGBACKREST" | grep -oP '\d{8}-\d{6}')
   sha256sum -c "manifest-${TIMESTAMP}.txt" --ignore-missing
   ```

4. **Clean Existing Volumes:**
   Wipe the corrupted or empty data volumes before extracting the backup.
   ```bash
   sudo rm -rf /var/lib/docker/volumes/family-hero-hub_pgbackrest_repo/_data/*
   sudo rm -rf /var/lib/docker/volumes/family-hero-hub_postgres_data/_data/*
   ```

5. **Extract pgBackRest Repository:**
   ```bash
   sudo tar -xzf "$LATEST_PGBACKREST" -C /var/lib/docker/volumes/family-hero-hub_pgbackrest_repo/
   # Verify extraction:
   sudo ls -la /var/lib/docker/volumes/family-hero-hub_pgbackrest_repo/_data/
   ```

6. **Run pgBackRest Restore using an Ephemeral Container:**
   `pgbackrest restore` MUST be run while the PostgreSQL server process is STOPPED and the data directory is empty. We use an ephemeral container attached to the volumes and the entrypoint overridden to run `pgbackrest` as the `postgres` user.
   ```bash
   cd /opt/apps/family-hero-hub
   sudo docker compose run --rm --user postgres --entrypoint "pgbackrest --stanza=fhh restore" postgres
   ```
   - Rehearse this exact container invocation on a non-production clone before first production use if the compose image, service name, or entrypoint changes.

7. **Start Postgres to apply restored data:**
   ```bash
   sudo docker compose start postgres
   ```

8. **Validate DB:**
   Check if the tables exist without exposing data:
   ```bash
   sudo docker exec -u postgres family-hero-hub-postgres psql -d family_hero_hub -c '\dt'
   ```

9. **Start App:**
   ```bash
   sudo docker compose start backend frontend
   ```

## 13. Expected outputs
pgBackRest will log `restore command begin` and `restore command end: completed successfully` in the ephemeral container stdout.

## 14. Validation checks
Expect to see the application tables in the `\dt` output.

## 15. Failure handling
If WAL/archive restore fails, check `/var/lib/docker/volumes/family-hero-hub_pgbackrest_repo/_data/log/fhh-restore.log` on the host.

## 16. Rollback notes
If the restore fails, wipe the `postgres_data` volume again, double-check the pgBackRest repo permissions, and retry.

## 17. What not to do
Do not start `postgres` before running the ephemeral `pgbackrest restore` command. Do not use placeholder commands like `psql -U ...` if you don't know the user (User is `familyhero`, DB is `family_hero_hub` as per `.env`). Do not print secrets.

## 18. Last verified date
2026-05-19

## 19. Restore rehearsal status
Partially rehearsed: backup extraction/listing only. The US pgBackRest restore path still needs a non-production rehearsal on a fresh clone before it is treated as production-ready.

## 20. Fresh-server dependency checks

Before PostgreSQL restore on rebuilt US:

```bash
tar -tzf /tmp/recovery/us-pgbackrest-repo-*.tar.gz | head
tar -tzf /tmp/recovery/us-sys-configs-*.tar.gz | grep -E 'docker-volumes|docker-compose-files|docker-mounts|docker-ps'
cd /opt/apps/family-hero-hub
sudo docker compose config
```

Expected: pgBackRest repo archive contains `_data/`; compose config resolves after `.env` is restored.

Do not expose PostgreSQL publicly:

```bash
sudo ss -ltnup | grep -E ':5432|postgres' || true
sudo docker ps --format 'table {{.Names}}\t{{.Ports}}'
```

The volume wipe steps are destructive. Use them only on a fresh or explicitly approved target.

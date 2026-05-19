# Recovery Checklist & Decision Tree

## 1. Purpose
Provides a decision tree to determine which restore runbook to use based on the failure scenario.

## 2. Scope
Full system and component-level disaster recovery routing.

## 3. When to use this restore path
When any component or server fails and you need to determine the correct recovery order and runbooks.

## 4. What this restores
This document restores nothing directly; it routes to the correct runbook.

## 5. What this does NOT restore
Mailcow is explicitly out of scope and requires a separate backup/restore project.

## 6. Required access
Access to this repository documentation.

## 7. Required offline secrets/keys
None for routing.

## 8. Required backup source options
None for routing.

## 9. Required approval gates before destructive actions
None.

## 10. Exact backup source paths
N/A

## 11. Exact restore target paths
N/A

## 12. Exact commands
N/A

## 13. Expected outputs
N/A

## 14. Validation checks
N/A

## 15. Failure handling
N/A

## 16. Rollback notes
N/A

## 17. What not to do
Do not guess the recovery order. Follow the tree.

## Decision Tree

**Scenario A: US production down**
1. Determine if PostgreSQL-only or full US server loss.
2. If PostgreSQL-only, use `RESTORE_POSTGRES.md`.
3. If full server, use `RESTORE_US_SERVER.md`.
4. Restore the US app archive, secrets archive, and `us-sys-configs-*.tar.gz` from the same source set.
5. Prefer UK `/opt/apps/backups/from-us/` as the backup source.
6. If UK unavailable, use Google Drive via `GOOGLE_DRIVE_BACKUP.md`.

**Scenario B: Europe/Hermes down**
1. Determine if Hermes-only or full Europe server loss.
2. If Hermes-only, use `RESTORE_HERMES.md`.
3. If full server, use `RESTORE_EUROPE_SERVER.md`.
4. Restore `europe-app-internal-tools-*.tar.gz` as well if you need Hermes workspace or the private viewers.
5. Prefer UK `/opt/apps/backups/from-europe/` if available.
6. If UK unavailable, use US `/opt/apps/backups/from-europe/`.
7. If both unavailable, use Google Drive via `GOOGLE_DRIVE_BACKUP.md`.

**Scenario C: UK backup hub down**
1. Use `RESTORE_UK_SERVER.md`.
2. Rebuild UK using `RESTORE_WIREGUARD.md` and `RESTORE_SECRETS.md`.
3. Pull `uk-sys-configs` from Google Drive via `GOOGLE_DRIVE_BACKUP.md`.

**Scenario D: All servers down (Google Drive only survives)**
1. Restore UK server first (VPN hub + rclone access) using `RESTORE_UK_SERVER.md` and `GOOGLE_DRIVE_BACKUP.md`.
2. Restore Europe server (Hermes, DevOps routing) using `RESTORE_EUROPE_SERVER.md`.
3. Restore US server (Production App) using `RESTORE_US_SERVER.md`.

**Scenario E: WireGuard-only issue**
1. Use `RESTORE_WIREGUARD.md` on the affected server.

**Scenario F: Secrets-only issue (.env lost)**
1. Use `RESTORE_SECRETS.md` on the affected server.

**Scenario G: Caddy-only issue**
1. On Europe: Extract `*-sys-configs-*.tar.gz` and restore `/etc/caddy/Caddyfile`.
2. On US: Extract `us-sys-configs-*.tar.gz` and restore `/etc/caddy/Caddyfile`, US backup timers, and deploy helper.

**Scenario H: Docker/Docker Compose-only issue**
1. Extract `*-app-family-hero-hub-*.tar.gz` and restore `docker-compose.yml`.

**Scenario I: Backup automation-only issue**
1. On Europe/UK: Extract `*-sys-configs-*.tar.gz` and restore `/etc/systemd/system/fhh-*.{timer,service}`, `/etc/systemd/system/wg-*.service`, `/usr/local/sbin/*.sh`, and `/opt/apps/backups/scripts/`.
2. On US: Extract `us-sys-configs-*.tar.gz` and restore `/etc/systemd/system/fhh-us-backup.{service,timer}`, `/etc/systemd/system/wg-personal-to-site-nat.service`, `/etc/systemd/system/cloudflared-update.{service,timer}`, `/usr/local/sbin/wg-personal-to-site-nat.sh`, `/opt/apps/backups/scripts/`, and `/usr/local/bin/family-hero-deploy`.


### 🔑 Offline Key Reference
The age private identity key is stored offline by Dom at:
**Google Drive > keys > VPS Backups Key > fhh-age-identity.txt**

- This location is a human/offline reference only.
- The key contents must never be pasted into chat, committed to git, or stored inside the project repo.
- This key is required to decrypt *-secrets-*.tar.gz.age archives.
- If this key is lost, encrypted secrets archives cannot be recovered.

## 18. Last verified date
2026-05-19

## 19. Restore rehearsal status
Not rehearsed yet.

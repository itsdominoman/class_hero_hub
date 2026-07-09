> Historical note: This document was inherited from Family Hero Hub and is preserved as historical context for the Class Hero Hub fork. It may describe old domains, paths, product assumptions, or infrastructure that are not current.

# Backup Inventory

## 1. Purpose
List of known backup stores and expected files.

## 2. Scope
Applies to all backup directories on US, Europe, and UK.

## 3. When to use this restore path
N/A (This is inventory documentation).

## 4. What this restores
N/A

## 5. What this does NOT restore
N/A

## 6. Required access
N/A

## 7. Required offline secrets/keys
N/A

## 8. Required backup source options
N/A

## 9. Required approval gates before destructive actions
N/A

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
N/A

## Active Backups (`/opt/apps/backups/`)
- `local/`: Server's own backups.
- `from-us/`: Mirrored from US. Expected on Europe and UK, not on US as a self-mirror.
- `from-europe/`: Mirrored from Europe. Expected on US and UK, not on Europe as a self-mirror.

Role-specific local expectations:

- Europe: `/opt/apps/backups/local/` contains `europe-*`; `/opt/apps/backups/from-us/` may contain pulled `us-*`; `/opt/apps/backups/from-europe/` is not expected locally on Europe.
- US: `/opt/apps/backups/local/` contains `us-*`; `/opt/apps/backups/from-europe/` may contain mirrored `europe-*`.
- UK: `/opt/apps/backups/local/` contains `uk-*`; `/opt/apps/backups/from-us/` and `/opt/apps/backups/from-europe/` contain mirrored source-server archives.

Restore drill preference:
- When restoring Europe, the surviving UK or US source server should push the latest complete `europe-*` set to the restore VPS.
- Treat restore-side pulls as a fallback only.

## Google Drive (`gdrive-crypt:` remote)
Encrypted logical layout:
- `gdrive-crypt:us/`
- `gdrive-crypt:europe/`
- `gdrive-crypt:uk/`

## Expected Archives

**US Backup Set:**
- `us-app-family-hero-hub-*.tar.gz` (Includes app files and `docker-compose.yml`)
- `us-sys-configs-*.tar.gz` (Includes `Caddyfile`, `wg-easy/docker-compose.yml`, `fhh-us-backup.service`, `fhh-us-backup.timer`, `wg-personal-to-site-nat.service`, `cloudflared-update.service`, `cloudflared-update.timer`, `/usr/local/bin/family-hero-deploy`, `/usr/local/sbin/wg-personal-to-site-nat.sh`, `/opt/apps/backups/scripts/*.sh`, and `system-info.txt`)
- `us-pgbackrest-repo-*.tar.gz`
- `us-secrets-*.tar.gz.age` (Encrypted; includes `/opt/apps/family-hero-hub/.env`, `/opt/apps/wg-easy/.env`, `/opt/apps/wg-easy/etc_wireguard`, `/etc/wireguard`, and the secret-bearing `cloudflared.service` unit)

**Europe Backup Set:**
- `europe-app-family-hero-hub-*.tar.gz` (Includes app files and `/opt/apps/family-hero-hub/data/family_hero_hub.sqlite` as the Europe dev data source when no Europe pgBackRest exists)
- `europe-app-hermes-*.tar.gz`
- `europe-app-internal-tools-*.tar.gz` (Includes `/opt/apps/hermes-workspace`, `/opt/apps/fhh-ops-dashboard`, and the private viewer apps under `family-hero-hub/tmp/{competitor-review,docs-viewer,qa-reports-viewer}`)
- `europe-home-hermes-*.tar.gz` (Plaintext Hermes home state with `auth`, `env`, `key`, `secret`, and `token` filename patterns excluded; carries Hermes session history, memory markdown, profile state, `state.db`, `kanban.db`, `response_store.db`, `gateway_state.json`, `channel_directory.json`, and `processes.json`)
- `europe-secrets-*.tar.gz.age` (Encrypted; includes `/opt/apps/family-hero-hub/.env`, `/opt/apps/hermes-workspace/.env`, `/opt/apps/wg-easy/.env`, `/opt/apps/wg-easy/etc_wireguard`, `/home/administrator/.hermes/*.env`, `/home/administrator/.hermes/auth*`, Hermes profile env/auth/secrets, Hermes state-snapshot auth/env files, `/etc/wireguard`, `/home/administrator/.ssh/europe-to-us-backups`, `/home/administrator/.ssh/europe-to-uk-backups`, and `/home/administrator/.ssh/known_hosts`)
- `europe-sys-configs-*.tar.gz` (Includes Caddy, `/opt/apps/wg-easy/docker-compose.yml`, custom systemd units, restore helper scripts under `/usr/local/sbin`, backup scripts, and `/etc/sudoers.d`; WireGuard private material moved to the encrypted secrets archive)

**Hermes persistence split:**
- Hermes agent/session history and memory markdown live in `europe-home-hermes-*.tar.gz` under `~/.hermes/`, including the named profile tree under `~/.hermes/profiles/<name>/`.
- Workspace session cache and UI-side portable history live in `europe-app-internal-tools-*.tar.gz` under `hermes-workspace/.runtime/local-sessions.json`.
- Auth, OAuth, tokens, and `.env` material stay in `europe-secrets-*.tar.gz.age`.

**UK Backup Set:**
- `uk-sys-configs-*.tar.gz` (Includes `wg-easy/docker-compose.yml`, `fhh-uk-backup.*`, `hermes-gateway.service`, `wg-personal-to-site-nat.service`, and `/usr/local/sbin/wg-personal-to-site-nat.sh`)
- `fhh-uk-to-restore-sync.{service,timer}` and `/usr/local/sbin/fhh-uk-to-restore-sync.sh` stage the filtered UK replica set to `/srv/fhh-restore-inbox/uk/backups`
- `fhh-uk-backup-retention.{service,timer}` and `/usr/local/sbin/fhh-uk-backup-retention.sh` cap Hermes app backups to the latest 2 and Hermes home backups to the latest 3
- Historical audit archive only: `/opt/apps/backups/local/removed-uk-n8n-openclaw-services-20260519-101652.tar.gz`
- `uk-secrets-*.tar.gz.age` (Encrypted; includes `/etc/wireguard`, `/opt/apps/wg-easy/.env`, `/opt/apps/wg-easy/etc_wireguard`, and `rclone.conf`)

**Common:**
- `manifest-*.txt` (SHA-256 checksums)

## Security
- **Encrypted**: All `*.age` files. Everything in Google Drive.
- **Safe to list**: Tarballs and manifests.
- **Must not be opened/printed**: Unencrypted `.env` files, WireGuard private keys (`.conf`, `.private`), `rclone.conf`.

## Historical Backups
- `/opt/backups/` on US and Europe: **Untouched, inventory only.** Do not migrate or delete.

## 18. Last verified date
2026-06-03

## 19. Restore rehearsal status
N/A

## 20. Required sys-config report inventory

Every current `*-sys-configs-*.tar.gz` archive must include these report families:

- OS/host: `system-info.txt`, `hostnamectl.txt`, `os-release.txt`, `uname.txt`, `timedatectl.txt`, `disk-layout.txt`, `memory.txt`, `ip-addresses.txt`, `ip-routes.txt`, `dns-resolver.txt`, `hosts-file.txt`, `hostname-file.txt`.
- Users/SSH/sudo: `users-summary.txt`, `administrator-groups.txt`, `sudoers-d-files-list.txt`, `sshd-config.txt`, `ssh-authorized-keys-summary.txt`, `ssh-key-fingerprints.txt`, `ssh-backup-trust-map.txt`.
- Firewall/ports: `firewall-status.txt`, `ufw-status-verbose.txt`, `ufw-status-numbered.txt`, `ufw-app-list.txt`, `iptables-save.txt`, `nft-ruleset.txt`, `ss-listening-ports.txt`, `docker-ports.txt`, `provider-firewall-notes.txt`, `trusted-source-ips.txt`, `temporary-dr-firewall-rules.md`.
- Docker: `docker-version.txt`, `docker-compose-version.txt`, `docker-ps.txt`, `docker-images.txt`, `docker-networks.txt`, `docker-volumes.txt`, `docker-compose-files.txt`, `docker-mounts.txt`, `docker-restart-policies.txt`.
- Systemd/cron: `systemd-enabled-services.txt`, `systemd-enabled-timers.txt`, `systemd-project-units.txt`, `systemd-all-custom-units.txt`, `crontab-root.txt`, `crontab-administrator.txt`, `cron-d-listing.txt`.
- Caddy: `caddy-configs/`, `caddy-config-paths.txt`, `caddy-validate.txt`, `caddy-routes-summary.txt`, `caddy-reverse-proxy-targets.txt`, `caddy-allowlists.txt`.
- Backup/WireGuard: `backup-scripts/`, `backup-systemd-units/`, `wireguard-summary.txt`, `wg-show.txt`, `wg-service-status.txt`, `wg-easy-summary.txt`, `wireguard-endpoint-restore-notes.txt`.
- Actual restore files: `helper-scripts/hermes-dashboard-vpn-allow.sh`, `helper-scripts/wg-personal-to-site-nat.sh`, `helper-scripts/wg-site-mesh-forward.sh`, `app-configs/wg-easy/docker-compose.yml`, `caddy-configs/caddy/Caddyfile`, and relevant `systemd-units/*.service`.
- UK only: `rclone-version.txt`, `rclone-remotes.txt`, `rclone-crypt-list-test.txt`, `google-drive-sync-status.txt`.

Verification:

```bash
LATEST_SYS="$(ls -1t /opt/apps/backups/local/*-sys-configs-*.tar.gz | head -1)"
tar -tzf "$LATEST_SYS" | sort
```

High-signal historical plaintext filename findings from the 2026-05-20 audit:

- Older US app archives on US/UK/Europe mirrors contain `family-hero-hub/.env`.
- Older Europe app archives on Europe/UK mirrors contain `family-hero-hub/.env`.
- Older UK sys-config archives contain `wg0.conf` and `wg-site.private` filenames.
- `europe-home-hermes-20260520-145520.tar.gz` contains Hermes auth/env filenames and must be treated as secret-bearing until remediated.

Exact affected archive paths confirmed by filename-only inspection on Europe:

```text
/opt/apps/backups/local/europe-app-family-hero-hub-20260519-070912.tar.gz
/opt/apps/backups/local/europe-app-family-hero-hub-20260519-071313.tar.gz
/opt/apps/backups/local/europe-app-family-hero-hub-20260519-072445.tar.gz
/opt/apps/backups/local/europe-app-family-hero-hub-20260519-074218.tar.gz
/opt/apps/backups/local/europe-home-hermes-20260520-145520.tar.gz
/opt/apps/backups/from-us/us-app-family-hero-hub-20260519-053833.tar.gz
/opt/apps/backups/from-us/us-app-family-hero-hub-20260519-053855.tar.gz
/opt/apps/backups/from-us/us-app-family-hero-hub-20260519-053920.tar.gz
/opt/apps/backups/from-us/us-app-family-hero-hub-20260519-092717.tar.gz
```

No local UK `uk-sys-configs-*.tar.gz` archive was present in the inspected Europe backup folders, so older UK plaintext sys-config archive paths still need to be inventoried on UK or Google Drive by filename only before any deletion decision.

Do not delete these archives without Dom approval. Recommended remediation is to verify encrypted replacements exist, quarantine or delete obsolete plaintext archives, and rotate affected secrets if exposure risk is considered high.

Remediation task list for historical plaintext archives:

1. Inventory affected archive filenames only; do not extract or print secret-bearing contents.
2. For each affected timestamp, verify a newer encrypted replacement exists for the same role and data class.
3. Quarantine affected plaintext archives to restricted storage or delete them only after Dom approval.
4. Rotate any `.env`, Hermes auth, WireGuard, wg-easy, rclone, OAuth, API, or SSH backup credentials that may have been exposed through plaintext archive storage.
5. Europe Hermes plaintext remediation proof is complete for timestamp `20260520-160643`: `/opt/apps/backups/local/europe-home-hermes-20260520-160643.tar.gz` has no obvious Hermes secret filenames matching `auth.json`, `.env`, `token`, `secret`, or `key`; `/opt/apps/backups/local/europe-secrets-20260520-160643.tar.gz.age` exists.
6. Record the final disposition and rotation status in this document before the next full DR drill.

## 21. Europe Restore-Test Source Map

Use this map during Europe restore:

| Backup type | Expected source | Expected path or pattern |
|---|---|---|
| Europe app archive | UK `/opt/apps/backups/from-europe/`, US `/opt/apps/backups/from-europe/`, or Europe local if available | `europe-app-family-hero-hub-*.tar.gz` |
| Europe Hermes app | same | `europe-app-hermes-*.tar.gz` |
| Europe internal tools | same | `europe-app-internal-tools-*.tar.gz` |
| Europe Hermes home | same | `europe-home-hermes-*.tar.gz` |
| Europe sys configs | same | `europe-sys-configs-*.tar.gz` |
| Europe secrets | same | `europe-secrets-*.tar.gz.age` |
| Manifest | same folder | `manifest-*.txt` |
| Europe dev DB | app archive after restore | `/opt/apps/family-hero-hub/data/family_hero_hub.sqlite` |
| US production Postgres | US source only | `us-pgbackrest-repo-*.tar.gz` |

Warning: do not use `us-pgbackrest-repo-*` for Europe dev unless intentionally seeding dev from production with Dom approval.

Expected Europe dev SQLite row counts from the May 2026 restore test:

```text
parent_users: 7
families: 4
children: 7
ledger_transactions: 97
rewards: 10
approved_parent_emails: 8
redemption_requests: 8
calendar_entries: 19
school_items: 47
```

## 22. Final verification status

Completed on 2026-05-20:

- US backup service completed successfully and the latest pulled US sys-config mirror inspected from Europe is `/opt/apps/backups/from-us/us-sys-configs-20260520-131221.tar.gz`.
- Europe backup service completed successfully and the latest remediated Europe sys-config archive inspected from Europe is `/opt/apps/backups/local/europe-sys-configs-20260520-160643.tar.gz`.
- UK backup proof is verified on UK and in Google Drive, not by local files on Europe.
- Required UK proof set: `uk-sys-configs-20260520-131436.tar.gz`, `uk-secrets-20260520-131436.tar.gz.age`, and `manifest-20260520-131436.txt`.
- UK `gdrive-crypt` listing shows `manifest-20260520-131436.txt`, `uk-secrets-20260520-131436.tar.gz.age`, and `uk-sys-configs-20260520-131436.tar.gz`.

Verified archive contents include:

- US: `helper-scripts/wg-personal-to-site-nat.sh`, `local-bin/family-hero-deploy`, `app-configs/wg-easy/docker-compose.yml`.
- Europe: remediated set `20260520-160643` includes `app-configs/wg-easy/docker-compose.yml`, `helper-scripts/wg-personal-to-site-nat.sh`, `helper-scripts/wg-site-mesh-forward.sh`, and `helper-scripts/hermes-dashboard-vpn-allow.sh`.
- UK: `ssh-backup-trust-map.txt`, `backup-systemd-units/fhh-uk-backup.timer`, `backup-systemd-units/fhh-uk-backup.service`, `iptables-save.txt`, `systemd-units/fhh-uk-backup.timer`, `systemd-units/fhh-uk-backup.service`, `nft-ruleset.txt`, `wireguard-summary.txt`, `rclone-remotes.txt`, `google-drive-sync-status.txt`, `firewall-status.txt`, `backup-scripts/uk-local-backup-and-sync.sh`.

## 23. 2026-05-20 Backup-Side Proof Update

The archive proof chain is now complete for all three server roles.

US:

- `us-sys-configs-20260520-131221.tar.gz` contains `./helper-scripts/wg-personal-to-site-nat.sh`, `./local-bin/family-hero-deploy`, and `./app-configs/wg-easy/docker-compose.yml`.

Europe:

- Remediated Europe backup was run.
- `/opt/apps/backups/local/europe-home-hermes-20260520-160643.tar.gz` has no obvious Hermes secret filenames matching `auth.json`, `.env`, `token`, `secret`, or `key`.
- `/opt/apps/backups/local/europe-secrets-20260520-160643.tar.gz.age` exists.
- `/opt/apps/backups/local/europe-sys-configs-20260520-160643.tar.gz` contains `./app-configs/wg-easy/docker-compose.yml`, `./helper-scripts/wg-personal-to-site-nat.sh`, `./helper-scripts/wg-site-mesh-forward.sh`, and `./helper-scripts/hermes-dashboard-vpn-allow.sh`.

UK:

- Fresh UK backup was run.
- On UK, `/opt/apps/backups/local/uk-sys-configs-20260520-131436.tar.gz` contains `ssh-backup-trust-map.txt`, `backup-systemd-units/fhh-uk-backup.timer`, `backup-systemd-units/fhh-uk-backup.service`, `iptables-save.txt`, `systemd-units/fhh-uk-backup.timer`, `systemd-units/fhh-uk-backup.service`, `nft-ruleset.txt`, `wireguard-summary.txt`, `rclone-remotes.txt`, `google-drive-sync-status.txt`, `firewall-status.txt`, and `backup-scripts/uk-local-backup-and-sync.sh`.
- On UK, `/opt/apps/backups/local/uk-secrets-20260520-131436.tar.gz.age` exists alongside it.
- Google Drive `gdrive-crypt:uk/` shows `manifest-20260520-131436.txt`, `uk-secrets-20260520-131436.tar.gz.age`, and `uk-sys-configs-20260520-131436.tar.gz`.

Legitimate remaining caveats:

- Historical plaintext archive quarantine/delete/rotation decisions still remain pending for affected old archives; the Europe Hermes plaintext backup path is remediated as of `20260520-160643`.
- Mailcow remains out of scope.
- Full restore drills still need to be repeated and proven end-to-end.

## 24. 2026-06-03 DR Backup Update

- UK restore replica inbox verified at `/srv/fhh-restore-inbox/uk/backups`.
- Current verified inbox size is about `3.6G` after cleanup.
- Restore sync uses `rsync` over SSH to `ukbackup@95.111.243.235` with both `--delete` and `--delete-excluded`, and keeps only the recent filtered backup set.
- UK and Europe retention scripts now cap Hermes app backups to the latest 2 and Hermes home backups to the latest 3.
- Europe Hermes app backup tarballs now exclude `.venv`, `*/.venv`, `test_venv`, `*/test_venv`, `.cache`, `*/.cache`, and `*.pyc`, reducing the archive from about `4.0G` to about `684M`.

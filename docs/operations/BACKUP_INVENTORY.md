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
- `from-us/`: Mirrored from US.
- `from-europe/`: Mirrored from Europe.

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
- `europe-app-family-hero-hub-*.tar.gz`
- `europe-app-hermes-*.tar.gz`
- `europe-app-internal-tools-*.tar.gz` (Includes `/opt/apps/hermes-workspace`, `/opt/apps/fhh-ops-dashboard`, and the private viewer apps under `family-hero-hub/tmp/{competitor-review,docs-viewer,qa-reports-viewer}`)
- `europe-home-hermes-*.tar.gz`
- `europe-secrets-*.tar.gz.age` (Encrypted; includes `/opt/apps/family-hero-hub/.env`, `/opt/apps/hermes-workspace/.env`, `/opt/apps/wg-easy/.env`, `/opt/apps/wg-easy/etc_wireguard`, `/home/administrator/.hermes/fhh-qa.env`, Hermes profile secrets, and `/etc/wireguard`)
- `europe-sys-configs-*.tar.gz` (Includes Caddy, `/opt/apps/wg-easy/docker-compose.yml`, custom systemd units, `/usr/local/sbin/*.sh`, and `/etc/sudoers.d`; WireGuard moved to the encrypted secrets archive)

**UK Backup Set:**
- `uk-sys-configs-*.tar.gz` (Includes `wg-easy/docker-compose.yml`, `fhh-uk-backup.*`, `hermes-gateway.service`, `wg-personal-to-site-nat.service`, and `/usr/local/sbin/wg-personal-to-site-nat.sh`)
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
2026-05-19

## 19. Restore rehearsal status
N/A

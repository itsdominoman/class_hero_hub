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
- `us-pgbackrest-repo-*.tar.gz`
- `us-secrets-*.tar.gz.age`
- `us-sys-configs-*.tar.gz` (Includes `Caddyfile`, `fhh-us-backup.service`, `fhh-us-backup.timer`, `/usr/local/bin/family-hero-deploy`, `/opt/apps/backups/scripts/*.sh`, and `system-info.txt` with `lsb_release`, Docker, Caddy, firewall, and optional `iptables-save` output)

**Europe Backup Set:**
- `europe-app-family-hero-hub-*.tar.gz`
- `europe-app-hermes-*.tar.gz`
- `europe-home-hermes-*.tar.gz`
- `europe-secrets-*.tar.gz.age`
- `europe-sys-configs-*.tar.gz` (Includes Caddy, systemd, WireGuard configs)

**UK Backup Set:**
- `uk-sys-configs-*.tar.gz`
- `uk-secrets-*.tar.gz.age` (Includes `rclone.conf`, `.env`, WireGuard private keys)

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

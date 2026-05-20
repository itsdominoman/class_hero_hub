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

## 20. Required sys-config report inventory

Every current `*-sys-configs-*.tar.gz` archive must include these report families:

- OS/host: `system-info.txt`, `hostnamectl.txt`, `os-release.txt`, `uname.txt`, `timedatectl.txt`, `disk-layout.txt`, `memory.txt`, `ip-addresses.txt`, `ip-routes.txt`, `dns-resolver.txt`, `hosts-file.txt`, `hostname-file.txt`.
- Users/SSH/sudo: `users-summary.txt`, `administrator-groups.txt`, `sudoers-d-files-list.txt`, `sshd-config.txt`, `ssh-authorized-keys-summary.txt`, `ssh-key-fingerprints.txt`, `ssh-backup-trust-map.txt`.
- Firewall/ports: `firewall-status.txt`, `ufw-status-verbose.txt`, `ufw-status-numbered.txt`, `ufw-app-list.txt`, `iptables-save.txt`, `nft-ruleset.txt`, `ss-listening-ports.txt`, `docker-ports.txt`, `provider-firewall-notes.txt`, `trusted-source-ips.txt`, `temporary-dr-firewall-rules.md`.
- Docker: `docker-version.txt`, `docker-compose-version.txt`, `docker-ps.txt`, `docker-images.txt`, `docker-networks.txt`, `docker-volumes.txt`, `docker-compose-files.txt`, `docker-mounts.txt`, `docker-restart-policies.txt`.
- Systemd/cron: `systemd-enabled-services.txt`, `systemd-enabled-timers.txt`, `systemd-project-units.txt`, `systemd-all-custom-units.txt`, `crontab-root.txt`, `crontab-administrator.txt`, `cron-d-listing.txt`.
- Caddy: `caddy-configs/`, `caddy-config-paths.txt`, `caddy-validate.txt`, `caddy-routes-summary.txt`, `caddy-reverse-proxy-targets.txt`, `caddy-allowlists.txt`.
- Backup/WireGuard: `backup-scripts/`, `backup-systemd-units/`, `wireguard-summary.txt`, `wg-show.txt`, `wg-service-status.txt`, `wg-easy-summary.txt`, `wireguard-endpoint-restore-notes.txt`.
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

Do not delete these archives without Dom approval. Recommended remediation is to verify encrypted replacements exist, quarantine or delete obsolete plaintext archives, and rotate affected secrets if exposure risk is considered high.

## 21. Final verification status

Verified on 2026-05-20 after Dom manually ran the root backup services:

- US: `fhh-us-backup.service` completed successfully and produced `/opt/apps/backups/local/us-sys-configs-20260520-034722.tar.gz`.
- Europe: `fhh-europe-backup.service` completed successfully and produced `/opt/apps/backups/local/europe-sys-configs-20260520-054833.tar.gz`.
- UK: `fhh-uk-backup.service` completed successfully and produced `/opt/apps/backups/local/uk-sys-configs-20260520-035446.tar.gz`.

Verified archive contents include:

- US: `wireguard-summary.txt`, `ssh-backup-trust-map.txt`, `systemd-enabled-services.txt`, `temporary-dr-firewall-rules.md`, `nft-ruleset.txt`, `docker-networks.txt`, `firewall-status.txt`, `iptables-save.txt`.
- Europe: `ssh-backup-trust-map.txt`, `firewall-status.txt`, `temporary-dr-firewall-rules.md`, `iptables-save.txt`, `wireguard-summary.txt`, `docker-networks.txt`, `systemd-enabled-services.txt`, `nft-ruleset.txt`.
- UK: `ssh-backup-trust-map.txt`, `docker-networks.txt`, `iptables-save.txt`, `nft-ruleset.txt`, `wireguard-summary.txt`, `rclone-remotes.txt`, `systemd-enabled-services.txt`, `google-drive-sync-status.txt`, `firewall-status.txt`, `temporary-dr-firewall-rules.md`.

Mirror and cloud verification:

- UK has the latest US sys-config mirror at `/opt/apps/backups/from-us/us-sys-configs-20260520-034722.tar.gz`.
- UK has the latest Europe sys-config mirror at `/opt/apps/backups/from-europe/europe-sys-configs-20260520-054833.tar.gz`.
- Europe successfully pulled the latest US sys-config mirror.
- UK `gdrive-crypt` listing shows the latest UK, US, and Europe sys-config archive names, confirming encrypted Google Drive upload and listing.

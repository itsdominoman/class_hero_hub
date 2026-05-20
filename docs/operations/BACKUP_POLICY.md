# Backup Policy

## 1. Purpose
Official backup schedule and retention policy.

## 2. Scope
Automated backup jobs across US, Europe, and UK.

## 3. When to use this restore path
N/A (This is policy documentation).

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

## Schedule & Timers
Systemd timers trigger localized shell scripts running as `root`.
- **Europe (`fhh-europe-backup.timer` @ 01:00)**: Backs up Europe dev app, Hermes, Europe internal tools, and configs including `wg-easy/docker-compose.yml`; encrypted secrets also include `wg-easy/.env` and `wg-easy/etc_wireguard`. Mirrors to US and UK.
- **US (`fhh-us-backup.timer` @ 02:00)**: Backs up US prod app, pgBackRest tarball, `us-sys-configs` including `wg-easy/docker-compose.yml`, and encrypted secrets, including the secret-bearing `cloudflared.service`, `wg-easy/.env`, and `wg-easy/etc_wireguard`. Mirrors to UK.
- **Europe (`fhh-europe-pull-us.timer` @ 03:00)**: Pulls the US backup mirror down to Europe.
- **UK (`fhh-uk-backup.timer` @ 04:00)**: Backs up UK configs, encrypted WireGuard/wg-easy state, and syncs `local`, `from-us`, and `from-europe` to Google Drive.

## Retention
- **Implemented Retention**: 30 days of archives are kept in `/opt/apps/backups/local/` on each server.
- **Proposed/Future**: 12 weekly, 6 monthly (Not yet implemented in shell scripts).
- **pgBackRest**: Handles its own internal retention (Diff=7, Full=3). Our policy applies to the exported atomic tarballs of the pgBackRest repo.

## Exclusions
- `node_modules`
- `.git`
- `.svelte-kit`
- `build`
- `.env`
- `__pycache__`
- `.pytest_cache`
- `test_venv`
- `tmp` (oversized data intentionally excluded).
- Plaintext WireGuard material is excluded from sys-config tarballs and stored only in the encrypted secrets archives.

## Encryption Design
- **Local secrets**: Asymmetrically encrypted using `age` recipient mode (`age -R /opt/apps/backups/scripts/fhh_backup.pub`). 
  - **Key Material on Server**: ONLY the public key (`fhh_backup.pub`). The server cannot decrypt its own backups.
  - **Offline Key Material**: Dom holds the `age` identity file (`key.txt`).
- **Google Drive**: Entire sync is encrypted using `rclone crypt` (filename and directory name encryption enabled).

## Failure Reporting / Log Locations
- Logs are appended to `/opt/apps/backups/logs/` (e.g., `us-local-backup.log`).
- Check systemd journal: `journalctl -u fhh-us-backup.service`.

## Operations
- **How to manually run each backup script**:
  `sudo /opt/apps/backups/scripts/us-local-backup.sh`
- **How to check latest backup status**:
  `systemctl list-timers | grep fhh`
  `ls -la /opt/apps/backups/local/`


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
N/A

## 20. Fresh-server restore coverage rule

As of 2026-05-20, backup coverage must be proven in this order: live server state, backup script coverage, archive contents, then restore documentation.

Verified on 2026-05-20 after Dom manually ran the root backup services on US, Europe, and UK:

- `fhh-us-backup.service` completed successfully with `status=0/SUCCESS`.
- `fhh-europe-backup.service` completed successfully with `status=0/SUCCESS`.
- `fhh-uk-backup.service` completed successfully with `status=0/SUCCESS`.

Backup services are oneshot/static services. They are expected to be inactive after successful completion. Timers are the persistent mechanism across reboot and should remain enabled/active.

Verified latest sys-config archives:

- US: `/opt/apps/backups/local/us-sys-configs-20260520-034722.tar.gz`
- Europe: `/opt/apps/backups/local/europe-sys-configs-20260520-054833.tar.gz`
- UK: `/opt/apps/backups/local/uk-sys-configs-20260520-035446.tar.gz`

Verified report files inside those archives include the restore-critical set for firewall, SSH trust, systemd/timers, Docker, WireGuard, and Google Drive on UK.

Do not start a Europe restore drill until the latest `*-sys-configs-*.tar.gz` archive for US, Europe, and UK contains the restore report set listed in `BACKUP_INVENTORY.md`.

Manual validation:

```bash
LATEST_SYS="$(ls -1t /opt/apps/backups/local/*-sys-configs-*.tar.gz | head -1)"
tar -tzf "$LATEST_SYS" | sort
tar -tzf "$LATEST_SYS" | grep -E 'firewall-status|systemd-enabled|docker-ps|caddy-validate|wireguard-summary|ssh-backup-trust-map|users-summary'
```

Backup scripts now use `/opt/apps/backups/scripts/fhh-collect-sys-config.sh` to generate restore reports. Private keys, `.env`, `rclone.conf`, WireGuard private configs, OAuth tokens, and API credentials must remain in `*-secrets-*.tar.gz.age`.

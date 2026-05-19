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
- **Europe (`fhh-europe-backup.timer` @ 01:00)**: Backs up Europe dev app, Hermes, and configs. Mirrors to US and UK.
- **US (`fhh-us-backup.timer` @ 02:00)**: Backs up US prod app, pgBackRest tarball, `us-sys-configs`, and encrypted secrets. Mirrors to UK.
- **Europe (`fhh-europe-pull-us.timer` @ 03:00)**: Pulls the US backup mirror down to Europe.
- **UK (`fhh-uk-backup.timer` @ 04:00)**: Backs up UK configs, and syncs `local`, `from-us`, and `from-europe` to Google Drive.

## Retention
- **Implemented Retention**: 30 days of archives are kept in `/opt/apps/backups/local/` on each server.
- **Proposed/Future**: 12 weekly, 6 monthly (Not yet implemented in shell scripts).
- **pgBackRest**: Handles its own internal retention (Diff=7, Full=3). Our policy applies to the exported atomic tarballs of the pgBackRest repo.

## Exclusions
- `node_modules`
- `.git`
- `.svelte-kit`
- `build`
- `__pycache__`
- `.pytest_cache`
- `test_venv`
- `tmp` (oversized data intentionally excluded).

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

# Family Hero Hub Backup Architecture (Implemented)

## 1. Purpose
This document reflects the approved and implemented Phase 2 architecture for the backup system.

## 2. Scope
The full backup strategy design.

## 3. When to use this restore path
N/A

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

## Backup Topology (Push/Pull Mirroring)
- **US** pushes local backups to **UK**.
- **Europe** pulls US local backups from **US**.
- **Europe** pushes local backups to **US** and **UK**.
- **UK** acts as the hub and syncs to **Google Drive**.

## US Local Backup Set
The implemented US backup job writes:
- `us-app-family-hero-hub-*.tar.gz`
- `us-pgbackrest-repo-*.tar.gz`
- `us-sys-configs-*.tar.gz`
- `us-secrets-*.tar.gz.age`

The US sys-config archive captures non-secret host state such as the Caddyfile, US backup service/timer units, deploy helper, backup scripts, and a text system snapshot.

## pgBackRest Mirror Method
Tarred snapshots of the pgBackRest repository immediately after a successful backup. Avoids rsync corruption.

## Google Drive Integration & Encryption
`rclone crypt` on the UK server. Filename encryption is ENABLED (Standard). Drive UI shows unreadable garbage names.

## Secrets Layering
Secrets are doubly encrypted: first with `age` locally, then by `rclone crypt` when uploaded.

## Retention Exclusions
`node_modules`, `.git`, `.svelte-kit`, `build`, `__pycache__`, `.pytest_cache`, `test_venv`, `tmp` are excluded.

## Mailcow
Explicitly out of scope and untouched.

## 18. Last verified date
2026-05-19

## 19. Restore rehearsal status
N/A

# Restore Overview

## 1. Purpose
Main "read this first" restore guide. Provides the high-level strategy for disaster recovery.

## 2. Scope
Applies to all restore operations within the Family Hero Hub infrastructure.

## 3. When to use this restore path
Start here for any major recovery.

## 4. What this restores
N/A - Directs workflow.

## 5. What this does NOT restore
N/A

## 6. Required access
N/A

## 7. Required offline secrets/keys
N/A

## 8. Required backup source options
N/A

## 9. Required approval gates before destructive actions
Never restore over live production without explicit approval.

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
Do not skip steps. Do not guess commands.

## High-Level Restore Strategy

1. **Choose Scenario**: Use `RECOVERY_CHECKLIST.md` to identify the correct runbook.
2. **Choose Backup Source**: Identify the safest backup source (UK Local > US/Europe Local > Google Drive).
3. **Gather Offline Secrets**: Secure the `age` private key and `rclone.conf` from your password manager.
4. **Stage Files First**: Copy `*.tar.gz` and `*.age` files to a `/tmp/recovery/` directory.
5. **Verify Checksums**: Run `sha256sum -c manifest-*.txt` to ensure backup integrity.
6. **Restore Non-Secrets**: Extract standard app and config tarballs, including server-specific `*-sys-configs-*.tar.gz` archives.
7. **Decrypt/Restore Secrets**: Use `RESTORE_SECRETS.md` to decrypt `*.age` files and carefully restore `.env` and WireGuard keys.
8. **Restart Services**: Reload systemd and start containers/services.
9. **Validate**: Perform the specific validation checks listed in the targeted runbook.
10. **Clean Up**: Only after validation, remove the `/tmp/recovery/` staging directory.


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

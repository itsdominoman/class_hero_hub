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
7. **Restore Internal Tools**: On Europe, also extract `europe-app-internal-tools-*.tar.gz` if Hermes workspace or the private viewers are needed.
8. **Decrypt/Restore Secrets**: Use `RESTORE_SECRETS.md` to decrypt `*.age` files and carefully restore `.env` and WireGuard keys.
9. **Restart Services**: Reload systemd and start containers/services.
10. **Validate**: Perform the specific validation checks listed in the targeted runbook.
11. **Clean Up**: Only after validation, remove the `/tmp/recovery/` staging directory.


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

## 20. Fresh-server restore proof chain

For a destroyed server, prove archive coverage before restore:

```bash
tar -tzf <role>-sys-configs-<timestamp>.tar.gz | grep -E 'firewall-status|provider-firewall-notes|ssh-backup-trust-map|wireguard-summary|docker-ps|caddy-validate|systemd-enabled|users-summary'
```

Decrypt secrets only into a private staging directory:

```bash
mkdir -p /tmp/secrets_recovery
chmod 700 /tmp/secrets_recovery
age -d -i /path/to/fhh-age-identity.txt -o /tmp/secrets.tar.gz <role>-secrets-<timestamp>.tar.gz.age
tar -xzf /tmp/secrets.tar.gz -C /tmp/secrets_recovery
rm -f /tmp/secrets.tar.gz
```

Never print `.env`, private keys, `rclone.conf`, OAuth tokens, API tokens, or WireGuard private keys.

Restore activation order: identity isolation, base packages, users/sudo/SSH, firewall preflight, secrets, WireGuard, Docker/app data, Caddy, systemd/cron, backup timers, validation.

## 21. Final verification status

Verified on 2026-05-20:

- Root backup services were manually started by Dom on US, Europe, and UK and completed successfully.
- The verified restore-readiness sys-config archive set now exists for all three roles.
- Backup services remain oneshot/static and are expected to be inactive after successful completion.
- Timers remain enabled/active and are the persistence mechanism across reboot.
- Europe restore drill is safer to begin than before, but it remains a controlled rehearsal that still requires explicit approval gates.

Remaining separate work:

- Historical plaintext archive remediation.
- Mailcow remains out of scope except inventory.

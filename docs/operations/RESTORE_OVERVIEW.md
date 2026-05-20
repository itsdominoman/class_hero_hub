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
2. **Confirm Role and Live Identity**: Before restoring WireGuard, backup timers, or DNS-facing services, confirm whether the original server is offline, isolated, or still active.
3. **Bootstrap First**: On a fresh server, install required tools before restore work. Europe requires Node 22, Caddy, Docker Compose, WireGuard tools, `age`, `rsync`, `jq`, `unzip`, and `sqlite3`.
4. **Stage Files First**: Use `/opt/apps/restore-materials/{docs,backups,keys}` and `/opt/apps/restore-test`; do not decrypt directly into live paths.
5. **Verify Secrets Key and Checksums**: Verify the age identity exists, decrypt into staging only, and run `sha256sum -c manifest-*.txt` before extraction.
6. **Prove SSH Trust Early**: Restore backup SSH keys and validate `ssh -o BatchMode=yes` to US/UK before copying backups or repairing remote peer endpoints. A password prompt means stop.
7. **Restore Dependencies Before Services**: Network identity, Caddy config, systemd units, helper scripts, WireGuard mesh, wg-easy, Hermes, app containers, DB schema, data, OAuth, UI, internal tools, firewall, backup timers, sudo cleanup.
8. **Validate Every Gate**: Service `active` is not sufficient. Validate WireGuard handshakes/ping/SSH, wg-easy real client access, DB schema/data, OAuth, UI data, dashboards, and firewall.
9. **Clean Up Last**: Remove temporary passwordless sudo and decrypted staging only after final validation and approval.


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

Restore activation order for Europe is defined by `RESTORE_EUROPE_SERVER.md` and must not be reordered. Backup timers are last, after all validation passes.

## Europe Restore Gate Summary

The Europe restore path is dependency-based:

```text
role confirmation -> bootstrap -> administrator/sudo -> tools -> temporary restore sudo -> standard paths -> age key -> staged secrets -> SSH trust -> copy backups -> checksum manifests -> extract archives -> path remap -> Caddy -> systemd units -> helper scripts -> site mesh -> peer endpoints -> mesh validation -> wg-easy -> real VPN client -> Hermes -> app containers -> Postgres schema -> Europe SQLite data import -> OAuth -> UI data -> internal tools -> UFW -> backup timers -> remove temporary sudo -> cleanup
```

Use `docs/operations/RESTORE_EUROPE_LESSONS_LEARNED.md` for the full restore-test findings. It is copied into the repo because the source file under `/opt/apps/backups/...` is outside git.

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

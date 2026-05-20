# Restore Hermes Agent

## 1. Purpose
Restore Hermes orchestration agent, its profiles, and services.

## 2. Scope
`/opt/apps/hermes-agent`, `/opt/apps/hermes-workspace`, `/home/administrator/.hermes`, `/opt/apps/family-hero-hub/HERMES_RULES.md` (if backed up), `/home/administrator/.hermes/fhh-qa.env`, systemd services.

## 3. When to use this restore path
Hermes agent is corrupted, deleted, or Europe VPS was rebuilt.

## 4. What this restores
Hermes code, configuration, agent profiles, Zeus gateway, and private dashboard.

## 5. What this does NOT restore
Europe app dev environment or WireGuard mesh.

## 6. Required access
SSH/admin access to Europe server (`10.250.50.1`).

## 7. Required offline secrets/keys
`age` private key (`key.txt`) for decrypting `europe-secrets-*.tar.gz.age`.

## 8. Required backup source options
1. UK `/opt/apps/backups/from-europe/`
2. US `/opt/apps/backups/from-europe/`
3. Europe `/opt/apps/backups/local/` (if still available)
4. Google Drive via `rclone crypt`

## 9. Required approval gates before destructive actions
Dom must explicitly approve overwriting existing Hermes directories.

## 10. Exact backup source paths
- `europe-app-hermes-*.tar.gz`
- `europe-app-internal-tools-*.tar.gz`
- `europe-home-hermes-*.tar.gz` for non-secret Hermes home state
- `europe-secrets-*.tar.gz.age` for Hermes auth/env/profile secret state
- `europe-sys-configs-*.tar.gz`

## 11. Exact restore target paths
- `/opt/apps/hermes-agent`
- `/opt/apps/hermes-workspace`
- `/home/administrator/.hermes`
- `/etc/systemd/system/hermes-*.service`
- `/etc/systemd/system/hermes-workspace.service`

## 12. Exact commands

**Hermes Restore Order:**

```bash
# Assume backups are downloaded to /tmp/recovery
cd /tmp/recovery

# 1. Restore App
sudo tar -xzf europe-app-hermes-*.tar.gz -C /

# 2. Restore Home (non-secret state; auth/env/profile secrets come from europe-secrets)
sudo tar -xzf europe-home-hermes-*.tar.gz -C /

# 3. Restore Systemd Services
sudo tar -xzf europe-sys-configs-*.tar.gz -C / etc/systemd/system/hermes-gateway.service etc/systemd/system/hermes-dashboard.service etc/systemd/system/hermes-dashboard-vpn-allow.service etc/systemd/system/hermes-workspace.service

# 3b. Restore Hermes workspace and private viewers if needed
sudo tar -xzf europe-app-internal-tools-*.tar.gz -C /

# 4. Decrypt Secrets (requires Dom to provide key.txt)
mkdir -p /tmp/secrets_recovery
age -d -i key.txt europe-secrets-*.tar.gz.age | tar -xzf - -C /tmp/secrets_recovery/
sudo cp /tmp/secrets_recovery/home/administrator/.hermes/fhh-qa.env /home/administrator/.hermes/ 2>/dev/null || true
sudo cp /tmp/secrets_recovery/opt/apps/hermes-workspace/.env /opt/apps/hermes-workspace/.env 2>/dev/null || true
sudo cp -r /tmp/secrets_recovery/home/administrator/.hermes/profiles/* /home/administrator/.hermes/profiles/ 2>/dev/null || true

# 5. Set Permissions
sudo chown -R administrator:administrator /opt/apps/hermes-agent
sudo chown -R administrator:administrator /home/administrator/.hermes

# 6. Verify Services
# The service files must have:
# User=administrator
# WorkingDirectory=/opt/apps/hermes-agent
# ExecStart pointing to .venv/bin/python
cat /etc/systemd/system/hermes-gateway.service | grep ExecStart

# 7. Enable Services (Only after secrets are restored!)
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-gateway hermes-dashboard hermes-dashboard-vpn-allow hermes-workspace
```

## 13. Expected outputs
Systemctl should return no errors. Tar will extract files silently.

## 14. Validation checks
- `systemctl status hermes-gateway --no-pager`
- `systemctl status hermes-dashboard --no-pager`
- `systemctl status hermes-workspace --no-pager`
- `curl -I http://10.250.50.1:9119` (from VPN)
- `curl -I http://10.250.50.1:3000` (from VPN or localhost)
- Validate Telegram/agent integrations (check `journalctl -u hermes-gateway` for startup success, no secret exposure).

## 15. Failure handling
If `journalctl` shows missing dependencies, ensure the `.venv` inside `/opt/apps/hermes-agent/` extracted correctly.

## 16. Rollback notes
Stop services, remove `/opt/apps/hermes-agent` and `/home/administrator/.hermes`, and start over.

## 17. What not to do
Do not print decrypted secrets to the console. Do not start Hermes before secrets/configs are restored.

## 18. Last verified date
2026-05-19

## 19. Restore rehearsal status
Partially rehearsed: backup extraction/listing only.

## 20. Fresh-server Hermes validation

Verify these archives before starting Hermes:

```bash
tar -tzf /tmp/recovery/europe-app-hermes-*.tar.gz | head
tar -tzf /tmp/recovery/europe-app-internal-tools-*.tar.gz | head
tar -tzf /tmp/recovery/europe-home-hermes-*.tar.gz | head
tar -tzf /tmp/recovery/europe-sys-configs-*.tar.gz | grep -E 'hermes|systemd-project-units|caddy'
```

Restore secrets first, then validate:

```bash
sudo systemctl daemon-reload
systemctl status hermes-gateway hermes-dashboard hermes-dashboard-vpn-allow hermes-workspace --no-pager
sudo ss -ltnup | grep -E '8642|9119|8765|8766|8767' || true
```

Do not start Hermes before `/home/administrator/.hermes` and secret-bearing Hermes auth/env/profile files are restored from `europe-secrets-*.tar.gz.age`. The plaintext `europe-home-hermes-*.tar.gz` archive must not be treated as the source for auth, token, env, or profile-secret material.

Remediated Europe backup proof from 2026-05-20:

- `/opt/apps/backups/local/europe-home-hermes-20260520-160643.tar.gz` has no obvious Hermes secret filenames matching `auth.json`, `.env`, `token`, `secret`, or `key`.
- `/opt/apps/backups/local/europe-secrets-20260520-160643.tar.gz.age` exists and remains the source for Hermes secret-bearing files.

## 21. Europe Restore Lessons Incorporated

Hermes is not an early restore dependency. In a full Europe rebuild, start Hermes only after the `RESTORE_EUROPE_SERVER.md` gates for SSH trust, backup verification, archive path mapping, Caddy, systemd units, helper scripts, site-to-site WireGuard, wg-easy, and real VPN client access have passed.

Required Hermes restore checks:

```bash
node --version
cd /opt/apps/hermes-workspace
rm -rf node_modules
npm install
sudo systemctl restart hermes-workspace
sudo ss -ltnup | grep -E '9119|3000'
systemctl status hermes-gateway hermes-dashboard hermes-dashboard-vpn-allow hermes-workspace --no-pager
curl -I http://10.250.50.1:9119
curl -I http://10.250.50.1:3000
```

Expected output:

- Node is `v22.x`.
- Hermes dashboard listens privately on `10.250.50.1:9119`.
- Hermes workspace listens on `10.250.50.1:3000`, not `0.0.0.0:3000`.
- `hermes-dashboard-vpn-allow.service` does not fail with `203/EXEC`; `/usr/local/sbin/hermes-dashboard-vpn-allow.sh` exists and is executable.

Stop conditions:

- Node is v18.
- Hermes workspace binds publicly.
- Any Hermes env/token file would need to be printed to debug.
- Telegram/Hermes messaging cannot be validated without exposing tokens.

Telegram validation without printing tokens:

```bash
systemctl status hermes-gateway --no-pager
journalctl -u hermes-gateway -n 100 --no-pager
```

Expected: config and allowlists are present, a real Telegram command is received and processed, and no token values appear in output.

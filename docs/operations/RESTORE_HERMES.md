# Restore Hermes Agent

## 1. Purpose
Restore Hermes orchestration agent, its profiles, and services.

## 2. Scope
`/opt/apps/hermes-agent`, `/home/administrator/.hermes`, `/opt/apps/family-hero-hub/HERMES_RULES.md` (if backed up), `/home/administrator/.hermes/fhh-qa.env`, systemd services.

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
- `europe-home-hermes-*.tar.gz`
- `europe-secrets-*.tar.gz.age`
- `europe-sys-configs-*.tar.gz`

## 11. Exact restore target paths
- `/opt/apps/hermes-agent`
- `/home/administrator/.hermes`
- `/etc/systemd/system/hermes-*.service`

## 12. Exact commands

**Hermes Restore Order:**

```bash
# Assume backups are downloaded to /tmp/recovery
cd /tmp/recovery

# 1. Restore App
sudo tar -xzf europe-app-hermes-*.tar.gz -C /

# 2. Restore Home (profiles)
sudo tar -xzf europe-home-hermes-*.tar.gz -C /

# 3. Restore Systemd Services
sudo tar -xzf europe-sys-configs-*.tar.gz -C / etc/systemd/system/hermes-gateway.service etc/systemd/system/hermes-dashboard.service etc/systemd/system/hermes-dashboard-vpn-allow.service

# 4. Decrypt Secrets (requires Dom to provide key.txt)
mkdir -p /tmp/secrets_recovery
age -d -i key.txt europe-secrets-*.tar.gz.age | tar -xzf - -C /tmp/secrets_recovery/
sudo cp /tmp/secrets_recovery/home/administrator/.hermes/fhh-qa.env /home/administrator/.hermes/ 2>/dev/null || true
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
sudo systemctl enable --now hermes-gateway hermes-dashboard hermes-dashboard-vpn-allow
```

## 13. Expected outputs
Systemctl should return no errors. Tar will extract files silently.

## 14. Validation checks
- `systemctl status hermes-gateway --no-pager`
- `systemctl status hermes-dashboard --no-pager`
- `curl -I http://10.250.50.1:9119` (from VPN)
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

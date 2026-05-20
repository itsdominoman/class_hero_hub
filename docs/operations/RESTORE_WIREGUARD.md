# Restore WireGuard

## 1. Purpose
Restore WireGuard mesh keys and configuration.

## 2. Scope
`/etc/wireguard/wg-site.conf`, `/etc/wireguard/wg-site.private`, `/etc/wireguard/wg-site.public`, and the `wg-easy` WireGuard state under `/opt/apps/wg-easy/etc_wireguard/` plus the matching `/opt/apps/wg-easy/docker-compose.yml` on servers that run the container.

## 3. When to use this restore path
Server rebuild or corrupted VPN config.

## 4. What this restores
WireGuard connectivity.

## 5. What this does NOT restore
App configurations.

## 6. Required access
Root on the target server.

## 7. Required offline secrets/keys
`age` identity file (`key.txt`).

## 8. Required backup source options
`*-secrets-*.tar.gz.age`

## 9. Required approval gates before destructive actions
Do not overwrite working WireGuard config without backup.

## 10. Exact backup source paths
Within the secrets archive.

## 11. Exact restore target paths
`/etc/wireguard/`

## 12. Exact commands
```bash
# Server identities:
# Europe: 10.250.50.1
# US: 10.250.50.2
# UK: 10.250.50.3
# Expected service name: wg-quick@wg-site

# 1. Identify the latest secrets archive
LATEST_SECRETS=$(ls -1t /tmp/recovery/*-secrets-*.tar.gz.age | head -1)

# 2. Decrypt to a staging directory first
mkdir -p /tmp/secrets_recovery
age -d -i key.txt "$LATEST_SECRETS" | tar -xzf - -C /tmp/secrets_recovery/

# 3. Restore config from staging (After Approval)
sudo cp -r /tmp/secrets_recovery/etc/wireguard/* /etc/wireguard/

# 3b. Restore wg-easy WireGuard state on UK (if present)
sudo cp -r /tmp/secrets_recovery/opt/apps/wg-easy/etc_wireguard/* /opt/apps/wg-easy/etc_wireguard/

# 4. Permissions
sudo chmod 600 /etc/wireguard/*.conf
sudo chmod 600 /etc/wireguard/*.private
sudo chown root:root /etc/wireguard/*.conf
sudo chown root:root /etc/wireguard/*.private

# 5. Enabling/restarting service
sudo systemctl enable --now wg-quick@wg-site
```

## 13. Expected outputs
Service starts successfully.

## 14. Validation checks
- `sudo wg show`
- `ip addr show wg-site`
- Ping tests across mesh (`ping 10.250.50.1`).

## 15. Failure handling
Check `journalctl -u wg-quick@wg-site`.

## 16. Rollback notes
Restore original config if overwritten.

## 17. What not to do
- Do not generate replacement keys unless intentionally rotating/rebuilding mesh.
- Do not overwrite working WireGuard config without backup.
- Do not print private keys.

## 18. Last verified date
2026-05-19

## 19. Restore rehearsal status
Not rehearsed yet.

## 20. Endpoint failover procedure

Restore a dead server's mesh identity only after the original server is offline or isolated.

On the replacement:

```bash
sudo cp -a /tmp/secrets_recovery/etc/wireguard/. /etc/wireguard/
sudo chmod 600 /etc/wireguard/*.conf /etc/wireguard/*.private 2>/dev/null || true
sudo chown root:root /etc/wireguard/*
sudo systemctl enable --now wg-quick@wg-site
sudo wg show
ip addr | grep 10.250.50
```

If replacement public IP changed, inspect remaining peers:

```bash
sudo wg show all endpoints
sudo grep -RIn 'Endpoint' /etc/wireguard /opt/apps/wg-easy 2>/dev/null
```

If endpoints are IP-based, update the peer endpoint on remaining servers and keep the previous value for rollback. If endpoints are hostname-based, change DNS only with Dom approval.

Europe restore drill rule: only one server may own `10.250.50.1`. Validate from US and UK:

```bash
ping -c 3 10.250.50.1
sudo wg show
```

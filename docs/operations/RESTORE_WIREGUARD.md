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

## 21. Europe Site Mesh And wg-easy Gates

Canonical live topology: see [INFRASTRUCTURE_MAP.md](./INFRASTRUCTURE_MAP.md).

Current live ranges:

```text
Site-to-site mesh: 10.250.50.0/24
Europe: 10.250.50.1
US: 10.250.50.2
UK: 10.250.50.3
Singapore: 10.250.50.4
Restore node: 10.250.50.5
UDP port: 51830

Europe wg-easy clients: 10.60.0.0/24
Home peer: 10.60.0.7
Home VPN clients behind home: 10.11.0.0/24
US wg-easy clients: 10.8.0.0/24
UK wg-easy clients: 10.70.0.0/24
Singapore wg-easy clients: 10.10.0.0/24
wg-easy UDP: 51820
wg-easy admin: http://10.250.50.1:51821
```

`10.80.0.0/24` is not active and must not be treated as a live trusted range.

Required SSH aliases before backup copy or endpoint repair:

```text
us-mesh
uk-mesh
us-public
uk-public
```

Validation:

```bash
ssh -o BatchMode=yes us-mesh 'hostname; echo US_MESH_OK'
ssh -o BatchMode=yes uk-mesh 'hostname; echo UK_MESH_OK'
ssh -o BatchMode=yes us-public 'hostname; echo US_PUBLIC_OK'
ssh -o BatchMode=yes uk-public 'hostname; echo UK_PUBLIC_OK'
```

Expected output: all aliases print the expected marker. Password prompt means stop.

Site mesh validation must include all of:

```bash
sudo wg show wg-site
ping -c 3 10.250.50.2
ping -c 3 10.250.50.3
ssh -o BatchMode=yes us-mesh 'hostname; echo US_MESH_OK'
ssh -o BatchMode=yes uk-mesh 'hostname; echo UK_MESH_OK'
```

Expected output: recent handshakes, `0% packet loss`, and SSH markers.

Drill cleanup note:

- After a drill, restore the US endpoint back to real Europe `213.199.61.244:51830`.
- Stop and remove the drill `wg-easy` container on the restore VPS.
- If the restore VPS is being rebuilt, let the rebuild remove any leftover local `wg-site` identity instead of trying to preserve drill state.

Endpoint drift:

- Historical May 2026 restore endpoint and original Europe endpoint values must not be reused as defaults.
- Use `<current-restore-public-ip>:51830` for a restore drill endpoint and `<current-original-europe-public-ip>:51830` when returning peers to the original Europe server.
- If Europe restores to a new public IP, US/UK peer endpoint config must be updated only with Dom approval.
- Never run original Europe and restore Europe simultaneously with the same WireGuard identity unless intentionally testing endpoint failover.
- Real restore or cutover rule: `dev.familyherohub.com` must point to the restored server.
- Drill rule: if DNS is intentionally left unchanged, update the WireGuard client endpoint IP manually to the restore server IP before relying on the VPN client path.
- Latest drill confirmed VPN, Caddy, firewall, and routing worked once the restore identity was in place.

wg-easy restore requirements:

- Restore `/opt/apps/wg-easy/docker-compose.yml`.
- Restore encrypted `/opt/apps/wg-easy/.env`.
- Restore encrypted `/opt/apps/wg-easy/etc_wireguard/wg0.conf` and `wg0.json`.
- If the latest encrypted archive is incomplete, inspect older encrypted Europe secrets archives by filename only.
- Compose must bind `./etc_wireguard:/etc/wireguard`, not a named volume.
- `.env` must include `WG_DEFAULT_ADDRESS=10.60.0.x`.
- NAT must show `10.60.0.0/24`, not `10.8.0.0/24`.

Validation:

```bash
cd /opt/apps/wg-easy
docker compose config
docker compose ps
sudo ss -ltnup | grep -E '51820|51821'
sudo docker exec wg-easy-europe sh -lc 'iptables -t nat -S | grep -E "10.8|10.60|MASQUERADE"'
```

Real client validation is mandatory before enabling UFW:

```text
Address = 10.60.0.x/24
Endpoint = dev.familyherohub.com:51820
AllowedIPs = 10.250.50.0/24
ping 10.250.50.1
open http://10.250.50.1:51821
open http://10.250.50.1:9119
open http://10.250.50.1:3000
ssh administrator@10.250.50.1
```

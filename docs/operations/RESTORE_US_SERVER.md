# Restore US Server

## 1. Purpose
Full rebuild of the US production server.

## 2. Scope
App folder, Docker Compose, `.env` files, WireGuard, backup scripts/timers, cloudflared tunnel metadata, and US system-config snapshots.

## 3. When to use this restore path
US VPS hardware failure or OS wipe.

## 4. What this restores
Production App (Family Hero Hub) and WireGuard mesh node.

## 5. What this does NOT restore
**Mailcow is explicitly out of scope.**
This runbook does not restore Mailcow or any other out-of-scope service.

## 6. Required access
Root/SSH on new US VPS (`familyherohub.com`, `10.250.50.2`).

## 7. Required offline secrets/keys
`age` identity file (`key.txt`) for `.env` and WireGuard keys.

## 8. Required backup source options
1. UK `/opt/apps/backups/from-us/`
2. Google Drive via `GOOGLE_DRIVE_BACKUP.md`

## 9. Required approval gates before destructive actions
Dom must approve the OS rebuild and app startup.

## 10. Exact backup source paths
- `us-app-family-hero-hub-*.tar.gz`
- `us-secrets-*.tar.gz.age`
- `us-pgbackrest-repo-*.tar.gz` (for `RESTORE_POSTGRES.md`)
- `us-sys-configs-*.tar.gz`
- `us-secrets-*.tar.gz.age` also carries the secret-bearing `cloudflared.service` unit if the legacy tunnel still needs to be restored.

## 11. Exact restore target paths
`/` (root)

## 12. Exact commands

**Fresh Server Bootstrap Order:**

1. **Confirm Server Identity:**
   - Role: US Production
   - WireGuard IP: `10.250.50.2`
   - Hostname: Verify with `hostname`
   - OS: Ubuntu 24.04 LTS
   - User: `administrator` exists with sudo.

2. **Base OS Update:**
   ```bash
   sudo apt-get update
   sudo apt-get upgrade -y
   ```

3. **Install Recovery Tools:**
   ```bash
   sudo apt-get install -y curl ca-certificates gnupg lsb-release tar gzip rsync openssh-client openssh-server age wireguard
   ```

4. **Transfer Backups:**
   ```bash
   mkdir -p /tmp/recovery
   # e.g., scp administrator@10.250.50.3:/opt/apps/backups/from-us/* /tmp/recovery/
   ```

5. **Decrypt Secrets & Restore Network Identity:**
   ```bash
   LATEST_SECRETS=$(ls -1t /tmp/recovery/us-secrets-*.tar.gz.age | head -1)
   mkdir -p /tmp/secrets_recovery
   age -d -i key.txt "$LATEST_SECRETS" | tar -xzf - -C /tmp/secrets_recovery/
   
   # Restore WireGuard (After Approval)
   sudo cp -r /tmp/secrets_recovery/etc/wireguard/* /etc/wireguard/
   sudo chmod 600 /etc/wireguard/*.conf
   sudo chown root:root /etc/wireguard/*.conf
   sudo systemctl enable --now wg-quick@wg-site
   ```
   - *Validate Mesh*: `sudo wg show`, `ip addr`, `ping 10.250.50.1`, `ping 10.250.50.3`.

6. **Install Docker & Caddy:**
   US uses `docker.io` and `docker-compose-v2` from Ubuntu repos (verified).
   ```bash
   sudo apt-get install -y docker.io docker-compose-v2
   
   # Install Caddy
   sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
   sudo apt-get update
   sudo apt-get install caddy
   ```

7. **Extract App & Configs:**
   ```bash
   LATEST_APP=$(ls -1t /tmp/recovery/us-app-family-hero-hub-*.tar.gz | head -1)
   sudo tar -xzf "$LATEST_APP" -C /
   
   # Restore .env
   sudo cp /tmp/secrets_recovery/opt/apps/family-hero-hub/.env /opt/apps/family-hero-hub/.env
   sudo chown administrator:administrator /opt/apps/family-hero-hub/.env
   ```

8. **Verify Docker Compose Config (Do not start yet!):**
   ```bash
   cd /opt/apps/family-hero-hub
   sudo docker compose config
   ```

9. **PostgreSQL Restore (MANDATORY BEFORE APP START):**
   - STOP: Execute steps in `RESTORE_POSTGRES.md` exactly as written to restore the DB data via an ephemeral pgBackRest container. Do NOT `docker compose up -d` before this is complete.

10. **Restore wg-easy and start application services:**
   - Restore `/opt/apps/wg-easy/docker-compose.yml` from `us-sys-configs-*.tar.gz`.
   - Restore `/opt/apps/wg-easy/.env` and `/opt/apps/wg-easy/etc_wireguard/` from `us-secrets-*.tar.gz.age`.
   - Start it only after the secret archive is restored: `cd /opt/apps/wg-easy && sudo docker compose up -d`.

11. **Start Application & Caddy:**
    ```bash
    # Only after Postgres is fully restored and validated
    cd /opt/apps/family-hero-hub
    sudo tar -xzf /tmp/recovery/us-sys-configs-*.tar.gz -C /
    sudo docker compose up -d backend frontend
    sudo caddy validate --config /etc/caddy/Caddyfile
    sudo systemctl enable --now caddy
    sudo systemctl enable --now wg-personal-to-site-nat 2>/dev/null || true
    ```

11. **Restore Backup Timers:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable --now fhh-us-backup.timer
    ```

## 13. Expected outputs
Service startups should report OK.

## 14. Validation checks
- No public PostgreSQL exposure (`ss -ltnup | grep 5432` should be empty on host).
- Docker containers healthy (`docker ps`).
- `curl -sS https://familyherohub.com/api/health | grep ok`

## 15. Failure handling
If Caddy fails, verify DNS records for familyherohub.com.

## 16. Rollback notes
Re-image the VPS and start over.

## 17. What not to do
Do NOT start `docker compose up -d` before fully restoring PostgreSQL via pgBackRest. Doing so creates an empty DB schema. Do not print secrets.

## 18. Last verified date
2026-05-19

## 19. Restore rehearsal status
Not rehearsed yet.

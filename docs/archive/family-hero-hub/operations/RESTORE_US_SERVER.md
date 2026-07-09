> Historical note: This document was inherited from Family Hero Hub and is preserved as historical context for the Class Hero Hub fork. It may describe old domains, paths, product assumptions, or infrastructure that are not current.

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
   - This US pgBackRest path still needs a non-production rehearsal on a fresh clone before a real production failover.

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

## 20. Fresh-server deterministic restore addendum

Purpose: rebuild the US production role from backups and docs only. Role: Family Hero Hub production, PostgreSQL/pgBackRest, Caddy, WireGuard mesh `10.250.50.2`, backup push to UK, and Mailcow inventory only.

Required archives:

- `us-app-family-hero-hub-*.tar.gz`
- `us-pgbackrest-repo-*.tar.gz`
- `us-sys-configs-*.tar.gz`
- `us-secrets-*.tar.gz.age`

Before restore, inspect the sys-config archive:

```bash
LATEST_SYS="$(ls -1t /tmp/recovery/us-sys-configs-*.tar.gz | head -1)"
tar -tzf "$LATEST_SYS" | grep -E 'firewall-status|ssh-backup-trust-map|wireguard-summary|docker-ps|caddy-validate|systemd-enabled|users-summary'
```

Base packages:

```bash
sudo apt-get update
sudo apt-get install -y curl ca-certificates gnupg lsb-release tar gzip rsync openssh-server openssh-client age wireguard ufw nftables iptables docker.io docker-compose-v2 caddy
```

Restore order:

1. Create `administrator`, restore sudo membership, and compare `users-summary.txt`, `administrator-groups.txt`, and `sudoers-d-files-list.txt`.
2. Restore SSH daemon settings from `sshd-config.txt`; rebuild `authorized_keys` using `ssh-authorized-keys-summary.txt` and Dom-approved public keys.
3. Restore backup automation trust: encrypted secrets archive must provide `/home/administrator/.ssh/us-to-uk-backups`; UK `authorized_keys` must contain the matching public key fingerprint from `ssh-key-fingerprints.txt`.
4. Restore WireGuard from encrypted secrets, start `wg-quick@wg-site`, and validate `ping 10.250.50.1` and `ping 10.250.50.3`.
5. Restore Docker compose/app files, run `docker compose config`, then restore PostgreSQL through `RESTORE_POSTGRES.md` before starting app services.
6. Restore Caddy configs, run `sudo caddy fmt --overwrite /etc/caddy/Caddyfile` and `sudo caddy validate --config /etc/caddy/Caddyfile`, then start/reload Caddy.
7. Restore systemd units, run `sudo systemctl daemon-reload`, and enable timers only after the restored server is the active US identity.

Firewall restore:

```bash
sudo ufw status verbose
sudo ufw status numbered
sudo ss -ltnup
sudo ufw allow from <operator_ip> to any port 22 proto tcp comment 'temporary DR SSH'
sudo ufw allow 51820/udp comment 'WireGuard mesh'
sudo ufw --force enable
sudo ufw status verbose
```

Remove temporary rules after validation:

```bash
sudo ufw status numbered
sudo ufw delete <rule_number>
```

Provider firewall rules are outside the server. Dom must verify provider-side SSH, HTTP/HTTPS, and WireGuard before enabling UFW. Confirm PostgreSQL, backup stores, wg-easy admin, and internal ports are not public:

```bash
sudo ss -ltnup
sudo docker ps --format 'table {{.Names}}\t{{.Ports}}'
```

What not to do: do not restore over live production without approval, do not start app containers before PostgreSQL restore is complete, do not restore Mailcow from this runbook, do not change DNS, and do not print decrypted secrets.

## 21. Final verification status

Verified on 2026-05-20:

- `sudo systemctl start fhh-us-backup.service`
- `sudo systemctl status fhh-us-backup.service --no-pager`
- Result: completed successfully with `status=0/SUCCESS`.
- Latest verified sys-config archive: `/opt/apps/backups/from-us/us-sys-configs-20260520-131221.tar.gz`.
- Verified archive members: `./helper-scripts/wg-personal-to-site-nat.sh`, `./local-bin/family-hero-deploy`, `./app-configs/wg-easy/docker-compose.yml`.
- Backup service is oneshot/static and is expected to be inactive after success; `fhh-us-backup.timer` is the persistent reboot mechanism.

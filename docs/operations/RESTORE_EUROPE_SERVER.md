# Restore Europe Server

## 1. Purpose
Full rebuild of the Europe dev server.

## 2. Scope
App dev folder, Hermes, WireGuard, Caddy, `.env` files, firewall rules.

## 3. When to use this restore path
Europe VPS hardware failure or OS wipe.

## 4. What this restores
Dev app, Hermes orchestration, dev database (from files), backup timers.

## 5. What this does NOT restore
US production. Mailcow.

## 6. Required access
Root/SSH on new Europe VPS (`dev.familyherohub.com`, `10.250.50.1`).

## 7. Required offline secrets/keys
`age` identity file for `.env` and WireGuard keys.

## 8. Required backup source options
1. UK `/opt/apps/backups/from-europe/`
2. US `/opt/apps/backups/from-europe/`
3. Google Drive via `GOOGLE_DRIVE_BACKUP.md`.

## 9. Required approval gates before destructive actions
Dom must approve the OS rebuild and overwriting of any existing configuration.

## 10. Exact backup source paths
- `europe-app-family-hero-hub-*.tar.gz`
- `europe-app-hermes-*.tar.gz`
- `europe-home-hermes-*.tar.gz`
- `europe-sys-configs-*.tar.gz`
- `europe-secrets-*.tar.gz.age`

## 11. Exact restore target paths
`/` (root)

## 12. Exact commands

**Fresh Server Bootstrap Order:**

1. **Confirm Server Identity:**
   - Role: Dev/Test & Hermes
   - WireGuard IP: `10.250.50.1`
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
   # e.g., scp administrator@10.250.50.3:/opt/apps/backups/from-europe/* /tmp/recovery/
   ```

5. **Decrypt Secrets & Restore Network Identity:**
   ```bash
   LATEST_SECRETS=$(ls -1t /tmp/recovery/europe-secrets-*.tar.gz.age | head -1)
   mkdir -p /tmp/secrets_recovery
   age -d -i key.txt "$LATEST_SECRETS" | tar -xzf - -C /tmp/secrets_recovery/
   
   # Restore WireGuard (After Approval)
   sudo cp -r /tmp/secrets_recovery/etc/wireguard/* /etc/wireguard/
   sudo chmod 600 /etc/wireguard/*.conf
   sudo chown root:root /etc/wireguard/*.conf
   sudo systemctl enable --now wg-quick@wg-site
   ```
   - *Validate Mesh*: `sudo wg show`, `ip addr`, `ping 10.250.50.2`, `ping 10.250.50.3`.

6. **Install Docker & Caddy:**
   Europe uses Docker CE from the official repo (verified via `docker-ce` package).
   ```bash
   # Install Docker CE
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   
   # Install Caddy
   sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
   sudo apt-get update
   sudo apt-get install caddy
   ```

7. **Extract Apps & Configs:**
   ```bash
   LATEST_HUB=$(ls -1t /tmp/recovery/europe-app-family-hero-hub-*.tar.gz | head -1)
   LATEST_HERMES_APP=$(ls -1t /tmp/recovery/europe-app-hermes-*.tar.gz | head -1)
   LATEST_HERMES_HOME=$(ls -1t /tmp/recovery/europe-home-hermes-*.tar.gz | head -1)
   LATEST_SYS=$(ls -1t /tmp/recovery/europe-sys-configs-*.tar.gz | head -1)
   
   sudo tar -xzf "$LATEST_HUB" -C /
   sudo tar -xzf "$LATEST_HERMES_APP" -C /
   sudo tar -xzf "$LATEST_HERMES_HOME" -C /
   sudo tar -xzf "$LATEST_SYS" -C /
   
   # Restore remaining secrets
   sudo cp /tmp/secrets_recovery/opt/apps/family-hero-hub/.env /opt/apps/family-hero-hub/.env
   sudo cp /tmp/secrets_recovery/home/administrator/.hermes/fhh-qa.env /home/administrator/.hermes/
   sudo cp -r /tmp/secrets_recovery/home/administrator/.hermes/profiles/* /home/administrator/.hermes/profiles/ 2>/dev/null || true
   
   sudo chown -R administrator:administrator /opt/apps/family-hero-hub /opt/apps/hermes-agent /home/administrator/.hermes
   ```

8. **Verify and Start App:**
   ```bash
   cd /opt/apps/family-hero-hub
   sudo docker compose config
   sudo docker compose up -d
   ```

9. **Start Caddy:**
   *Note: Do not change DNS unless Dom explicitly approves. If cert issuance fails, check DNS/firewall before editing configs.*
   ```bash
   sudo caddy validate --config /etc/caddy/Caddyfile
   sudo systemctl enable --now caddy
   ```

10. **Verify Hermes Dependencies:**
    Hermes requires Python (venv at `.venv/bin/python`) and Node.js (`node_modules/.bin`). The backup includes the environment.
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable --now hermes-gateway hermes-dashboard hermes-dashboard-vpn-allow
    ```

11. **Restore Backup Timers:**
    ```bash
    sudo systemctl enable --now fhh-europe-backup.timer fhh-europe-pull-us.timer
    ```

## 13. Expected outputs
Service startups should report OK.

## 14. Validation checks
- WireGuard mesh ping (`ping 10.250.50.2`, `ping 10.250.50.3`).
- `curl -I https://dev.familyherohub.com`
- `docker ps` shows backend/frontend/postgres.
- `systemctl list-timers | grep fhh`
- `systemctl status hermes-gateway --no-pager`

## 15. Failure handling
If Caddy fails to start, verify DNS points to the new Europe VPS IP before editing configs.

## 16. Rollback notes
Re-image the VPS and start over.

## 17. What not to do
Do not generate new WireGuard keys. Use the restored ones. Do not print secrets.

## 18. Last verified date
2026-05-19

## 19. Restore rehearsal status
Not rehearsed yet.

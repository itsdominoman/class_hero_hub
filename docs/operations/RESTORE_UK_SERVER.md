# Restore UK Server

## 1. Purpose
Restore UK infrastructure and backup hub.

## 2. Scope
WireGuard, `wg-easy`, `rclone` config, `/opt/apps/backups` directories, backup scripts/timers.

## 3. When to use this restore path
UK VPS hardware failure or OS wipe.

## 4. What this restores
UK role: backup hub + Google Drive uploader.

## 5. What this does NOT restore
US/Europe local backups directly (must be pushed from them later or pulled from Drive).

## 6. Required access
Root on new UK VPS (`10.250.50.3`).

## 7. Required offline secrets/keys
`age` identity file, offline `rclone.conf`.

## 8. Required backup source options
Google Drive via `GOOGLE_DRIVE_BACKUP.md`.

## 9. Required approval gates before destructive actions
Approval to rebuild UK. Note: UK does not need outbound SSH to US/Europe for normal backup operation.

## 10. Exact backup source paths
Google Drive: `gdrive-crypt:uk/uk-sys-configs-*.tar.gz`, `uk-secrets-*.tar.gz.age`.

## 11. Exact restore target paths
`/` (root)

## 12. Exact commands

**Fresh Server Bootstrap Order:**

1. **Confirm Server Identity:**
   - Role: Backup Hub
   - WireGuard IP: `10.250.50.3`
   - Hostname: Verify with `hostname`
   - OS: Ubuntu 24.04 LTS
   - User: `administrator` exists with sudo.

2. **Base OS Update:**
   ```bash
   sudo apt-get update
   sudo apt-get upgrade -y
   ```

3. **Install Recovery Tools:**
   UK requires `docker.io` and `docker-compose-v2` (verified).
   ```bash
   sudo apt-get install -y curl ca-certificates gnupg lsb-release tar gzip rsync openssh-client openssh-server age wireguard rclone docker.io docker-compose-v2
   ```

4. **Restore rclone config:**
   ```bash
   mkdir -p ~/.config/rclone
   # Manually recreate ~/.config/rclone/rclone.conf securely from password manager.
   chmod 600 ~/.config/rclone/rclone.conf
   ```

5. **Pull UK Backups from Google Drive:**
   ```bash
   mkdir -p /tmp/recovery
   rclone copy gdrive-crypt:uk/ /tmp/recovery/
   ```

6. **Decrypt Secrets & Restore Network Identity:**
   ```bash
   LATEST_SECRETS=$(ls -1t /tmp/recovery/uk-secrets-*.tar.gz.age | head -1)
   mkdir -p /tmp/secrets_recovery
   age -d -i key.txt "$LATEST_SECRETS" | tar -xzf - -C /tmp/secrets_recovery/
   
   # Restore WireGuard (After Approval)
   sudo cp -r /tmp/secrets_recovery/etc/wireguard/* /etc/wireguard/
   sudo chmod 600 /etc/wireguard/*.conf
   sudo chown root:root /etc/wireguard/*.conf
   sudo systemctl enable --now wg-quick@wg-site
   ```

7. **Extract sys configs:**
   ```bash
   LATEST_SYS=$(ls -1t /tmp/recovery/uk-sys-configs-*.tar.gz | head -1)
   sudo tar -xzf "$LATEST_SYS" -C /
   ```

8. **Restore /opt/apps/backups structure:**
   ```bash
   sudo mkdir -p /opt/apps/backups/{local,from-us,from-europe,google-drive-staging,logs,scripts,manifests,checksums}
   sudo chown -R administrator:administrator /opt/apps/backups
   ```

9. **Start wg-easy (if used):**
   ```bash
   cd /opt/apps/wg-easy && sudo docker compose up -d || true
   ```

10. **Restore backup timers:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable --now fhh-uk-backup.timer
    ```

## 13. Expected outputs
Silent extraction, successful service starts.

## 14. Validation checks
- Check WireGuard connectivity from US/Europe (`ping 10.250.50.3`).
- Validate receiving folder permissions (`ls -ld /opt/apps/backups/from-us`).
- Validate UK local backup (`sudo /opt/apps/backups/scripts/uk-local-backup-and-sync.sh`).
- Validate Google Drive encrypted upload/listing (`rclone ls gdrive-crypt:uk/`).
- Validate no public backup store exposure.

## 15. Failure handling
If `rclone.conf` is missing, recreate it using offline salt/password per `GOOGLE_DRIVE_BACKUP.md`.

## 16. Rollback notes
N/A

## 17. What not to do
Do not generate new SSH keys for US/Europe. US and Europe will push to UK using their existing keys.

## 18. Last verified date
2026-05-19

## 19. Restore rehearsal status
Not rehearsed yet.

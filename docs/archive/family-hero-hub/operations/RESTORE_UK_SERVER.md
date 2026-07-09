> Historical note: This document was inherited from Family Hero Hub and is preserved as historical context for the Class Hero Hub fork. It may describe old domains, paths, product assumptions, or infrastructure that are not current.

# Restore UK Server

## 1. Purpose
Restore UK infrastructure and backup hub.

## 2. Scope
WireGuard, `wg-easy`, `rclone` config, `/opt/apps/backups` directories, backup scripts/timers, and the installed UK helper services required for backup/DR/VPN (`fhh-uk-backup`, `hermes-gateway`, `wg-personal-to-site-nat`, `fhh-uk-to-restore-sync`, and `fhh-uk-backup-retention`).

## 3. When to use this restore path
UK VPS hardware failure or OS wipe.

## 4. What this restores
UK role: backup hub + Google Drive uploader, plus the helper services that support VPN, backup orchestration, retention, and restore staging.

## 5. What this does NOT restore
US/Europe local backups directly (must be pushed from them later or pulled from Drive).

## 6. Required access
Root on new UK VPS (`10.250.50.3`).

## 7. Required offline secrets/keys
`age` identity file, offline `rclone.conf`.

## 8. Required backup source options
Google Drive via `GOOGLE_DRIVE_BACKUP.md`, unless the required UK archives have already been manually staged on the restore VPS.

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

5. **Pull UK Backups from Google Drive unless manually staged:**
   ```bash
   mkdir -p /tmp/recovery
   rclone copy gdrive-crypt:uk/ /tmp/recovery/
   ```
   If Dom manually staged the UK archive set, verify the staged folder contains `uk-sys-configs-*.tar.gz`, `uk-secrets-*.tar.gz.age`, and the matching `manifest-*.txt` before continuing.

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
   - This restores `fhh-uk-backup.*`, `hermes-gateway.service`, and `wg-personal-to-site-nat.service` when present.

8. **Restore /opt/apps/backups structure:**
   ```bash
   sudo mkdir -p /opt/apps/backups/{local,from-us,from-europe,google-drive-staging,logs,scripts,manifests,checksums}
   sudo chown -R administrator:administrator /opt/apps/backups
   ```
   - Restore staging and retention helpers if present:
     - `/usr/local/sbin/fhh-uk-to-restore-sync.sh`
     - `/usr/local/sbin/fhh-uk-backup-retention.sh`
     - `/etc/systemd/system/fhh-uk-to-restore-sync.{service,timer}`
     - `/etc/systemd/system/fhh-uk-backup-retention.timer`

9. **Start wg-easy (if used):**
   ```bash
   cd /opt/apps/wg-easy && sudo docker compose up -d || true
   ```

10. **Restore backup timers:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable --now fhh-uk-backup.timer
    sudo systemctl enable --now fhh-uk-to-restore-sync.timer fhh-uk-backup-retention.timer
    sudo systemctl enable --now hermes-gateway wg-personal-to-site-nat 2>/dev/null || true
    ```

## 13. Expected outputs
Silent extraction, successful service starts.

## 14. Validation checks
- Check WireGuard connectivity from US/Europe (`ping 10.250.50.3`).
- Confirm password authentication is disabled and SSH is key-only; public SSH should only be reachable from trusted public IPs and VPN ranges.
- Validate receiving folder permissions (`ls -ld /opt/apps/backups/from-us`).
- Validate restore inbox staging (`ls -ld /srv/fhh-restore-inbox/uk/backups`).
- Validate UK local backup (`sudo /opt/apps/backups/scripts/uk-local-backup-and-sync.sh`).
- Validate restore sync and retention helpers (`systemctl status fhh-uk-to-restore-sync.timer fhh-uk-backup-retention.timer --no-pager`).
- Validate Google Drive encrypted upload/listing (`rclone ls gdrive-crypt:uk/`).
- Validate no public backup store exposure.
- Validate any restored helper services with `systemctl status fhh-uk-backup.timer hermes-gateway wg-personal-to-site-nat --no-pager`.

## 15. Failure handling
If `rclone.conf` is missing, recreate it using offline salt/password per `GOOGLE_DRIVE_BACKUP.md`.

## 16. Rollback notes
N/A

## 17. What not to do
Do not generate new SSH keys for US/Europe. US and Europe will push to UK using their existing keys.

## 18. Last verified date
2026-06-03

## 19. Restore rehearsal status
Not rehearsed yet.

## 20. Fresh-server deterministic restore addendum

Purpose: rebuild UK backup hub/DR role from backups and docs only. Role: backup receiver, Google Drive uploader through rclone crypt, WireGuard mesh `10.250.50.3`, and wg-easy. UK should not run unrelated services; n8n/OpenClaw remain removed from active restore.

Required archives:

- `uk-sys-configs-*.tar.gz`
- `uk-secrets-*.tar.gz.age`
- Optional mirrored sets: `from-us/*`, `from-europe/*`, or Google Drive encrypted copy.
- Restore replica inbox: `/srv/fhh-restore-inbox/uk/backups`

Source requirement: a fresh UK restore depends on Google Drive/rclone recovery unless Dom manually stages the UK archive set on the restore VPS first. UK local archives are not expected to be available after a UK server loss. The restore node is now a DR receiving node, so the filtered UK replica can also be staged there at `/srv/fhh-restore-inbox/uk/backups`.

Required current UK proof set:

```text
uk-sys-configs-20260520-131436.tar.gz
uk-secrets-20260520-131436.tar.gz.age
manifest-20260520-131436.txt
```

Proof location note: this set is verified on UK local storage and through Google Drive `gdrive-crypt:uk/`. It is not expected to be present on Europe under `/opt/apps/backups/local/`; for a fresh UK rebuild, retrieve it from Google Drive through rclone or manually stage it from an offline copy.

Inspect the sys-config archive:

```bash
LATEST_SYS="$(ls -1t /tmp/recovery/uk-sys-configs-*.tar.gz | head -1)"
tar -tzf "$LATEST_SYS" | grep -E 'firewall-status|ssh-backup-trust-map|wireguard-summary|docker-ps|systemd-enabled|users-summary|rclone'
```

Base packages:

```bash
sudo apt-get update
sudo apt-get install -y curl ca-certificates gnupg lsb-release tar gzip rsync openssh-server openssh-client age wireguard ufw nftables iptables docker.io docker-compose-v2 rclone
```

Restore order:

1. Create `administrator`, restore sudo membership, and compare user/sudo reports.
2. Restore SSH daemon settings; rebuild receiver-side `authorized_keys` for US and Europe backup senders using approved public keys and fingerprints in `ssh-key-fingerprints.txt`.
3. Restore WireGuard and wg-easy secrets from `uk-secrets-*.tar.gz.age`.
4. Restore rclone config from encrypted secrets or offline `rclone.conf`; never print the file.
5. Restore `/opt/apps/backups/{local,from-us,from-europe,logs,scripts}` and systemd units.
6. Restore the DR sync and retention helpers if present.
7. Start WireGuard and validate US/Europe mesh reachability.
8. Validate Google Drive through crypt remote: `rclone lsd gdrive-crypt:`.
9. Enable `fhh-uk-backup.timer` only after local and mirrored backup folders are correct.

Firewall restore:

```bash
sudo ufw status verbose
sudo ufw allow from <trusted_operator_ip> to any port 22 proto tcp comment 'temporary DR SSH'
sudo ufw allow 51820/udp comment 'WireGuard mesh'
sudo ufw --force enable
sudo ufw status verbose
```

Validation:

```bash
sudo ss -ltnup
sudo docker ps --format 'table {{.Names}}\t{{.Ports}}'
rclone lsd gdrive-crypt:
systemctl status fhh-uk-backup.timer --no-pager
```

What not to do: do not expose backup stores publicly, do not restore n8n/OpenClaw active services, do not print `rclone.conf`, and do not enable Google Drive sync until paths and crypt remote are verified.

## 21. Final verification status

Verified on 2026-05-20:

- `sudo systemctl start fhh-uk-backup.service`
- `sudo systemctl status fhh-uk-backup.service --no-pager`
- Result: completed successfully with `status=0/SUCCESS`.
- Latest verified sys-config archive on UK: `/opt/apps/backups/local/uk-sys-configs-20260520-131436.tar.gz`.
- Latest verified secrets archive on UK: `/opt/apps/backups/local/uk-secrets-20260520-131436.tar.gz.age`.
- Google Drive `gdrive-crypt:uk/` also lists `manifest-20260520-131436.txt`, `uk-sys-configs-20260520-131436.tar.gz`, and `uk-secrets-20260520-131436.tar.gz.age`.
- Verified archive members: `ssh-backup-trust-map.txt`, `backup-systemd-units/fhh-uk-backup.timer`, `backup-systemd-units/fhh-uk-backup.service`, `iptables-save.txt`, `systemd-units/fhh-uk-backup.timer`, `systemd-units/fhh-uk-backup.service`, `nft-ruleset.txt`, `wireguard-summary.txt`, `rclone-remotes.txt`, `google-drive-sync-status.txt`, `firewall-status.txt`, `backup-scripts/uk-local-backup-and-sync.sh`.
- UK archive proof shows no active n8n/OpenClaw service or timer files in the sys-config archive.
- Backup service is oneshot/static and is expected to be inactive after success; `fhh-uk-backup.timer` is the persistent reboot mechanism.
- The restore inbox now receives the filtered UK replica set at `/srv/fhh-restore-inbox/uk/backups` and is not a full historical archive.

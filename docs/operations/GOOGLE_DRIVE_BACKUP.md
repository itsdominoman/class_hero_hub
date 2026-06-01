# Google Drive Backup & Recovery

## 1. Purpose
Pull encrypted backups from Google Drive if all servers are lost.

## 2. Scope
Recovery of `us/`, `europe/`, and `uk/` backup sets from the cloud.

## 3. When to use this restore path
Complete catastrophic failure where US, Europe, and UK local backup stores are all destroyed.

## 4. What this restores
Encrypted `.tar.gz` and `.age` archives, including the mirrored US/Europe/UK backup sets and any secret-bearing units moved into the encrypted archives.

## 5. What this does NOT restore
It does not automatically extract or decrypt the files.

## 6. Required access
Any working Linux machine with internet access.

## 7. Required offline secrets/keys
Dom must provide:
1. Google login for `dom.dcubed@gmail.com` (or future replacement account).
2. Offline `rclone.conf` (PREFERRED).
If rclone.conf is lost: rclone crypt password and password2 (salt) (documented offline recovery values).
4. `age` identity file (`key.txt`) for decrypting secret archives locally after download.

## 8. Required backup source options
Google Drive (`gdrive-crypt:` remote).

## 9. Required approval gates before destructive actions
None to download.

## 10. Exact backup source paths
Google Drive logical layout: `gdrive-crypt:us/`, `gdrive-crypt:europe/`, `gdrive-crypt:uk/`.

## 11. Exact restore target paths
Local recovery folder: `/tmp/recovery/`

## 12. Exact commands
```bash
# 1. Install rclone
sudo apt-get update && sudo apt-get install -y rclone

# 2. Restore rclone.conf safely
mkdir -p ~/.config/rclone
# Create ~/.config/rclone/rclone.conf using the offline backup content securely
chmod 600 ~/.config/rclone/rclone.conf

# 3. List backup sets
rclone lsd gdrive-crypt:
rclone ls gdrive-crypt:us/

# 4. Copy down backup sets to a local staging folder
mkdir -p /tmp/recovery/us
rclone copy gdrive-crypt:us/ /tmp/recovery/us/ -P

# 5. Verify checksums after download
cd /tmp/recovery/us
sha256sum -c manifest-*.txt --ignore-missing
```

## 13. Expected outputs
`rclone ls` will show readable filenames (e.g. `us-app-family-hero-hub-*.tar.gz`). 

## 14. Validation checks
Checksum verification must pass.

## 15. Failure handling
If rclone auth/token has expired, run `rclone config reconnect gdrive:` locally on a desktop to generate a new token, then update `rclone.conf`.
If `rclone.conf` is missing, you must manually run `rclone config` to recreate BOTH the `gdrive` remote and `gdrive-crypt` remote (Crypt, pointing to `gdrive:family-hero-hub-backups` with `filename_encryption = standard` and `directory_name_encryption = true`, entering the offline `password` and `password2` (salt)).

## 16. Rollback notes
N/A

## 17. What not to do
- **Do not browse encrypted Drive UI expecting readable names.** Google Drive visible folder/file names are encrypted/gibberish because rclone crypt filename encryption is enabled. Logical layout is ONLY readable through the configured rclone crypt remote.
- **Do not upload/decrypt secrets into public/shared folders.**
- **Do not paste rclone config into chat.**


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
Partially rehearsed: backup listing and sync tested.

## 20. Fresh-server Google Drive restore notes

Google Drive visible names may be encrypted/gibberish. Readable backup names are expected only through the configured rclone crypt remote.

Preferred recovery uses offline `rclone.conf`. If unavailable, recreate both the Google Drive remote and crypt remote using the offline crypt password/password2 and Google login.

Validation:

```bash
rclone listremotes
rclone lsd gdrive-crypt:
rclone lsf gdrive-crypt:us/ | head
rclone lsf gdrive-crypt:europe/ | head
rclone lsf gdrive-crypt:uk/ | head
```

Download without exposing secrets:

```bash
mkdir -p /tmp/recovery/{us,europe,uk}
rclone copy gdrive-crypt:us/ /tmp/recovery/us/ -P
rclone copy gdrive-crypt:europe/ /tmp/recovery/europe/ -P
rclone copy gdrive-crypt:uk/ /tmp/recovery/uk/ -P
find /tmp/recovery -maxdepth 2 -type f -print | sort
```

Do not paste `rclone.conf`, OAuth tokens, crypt passwords, or downloaded decrypted secret contents into chat.

For a fresh UK backup hub rebuild, this Google Drive/rclone path is required unless Dom manually stages the UK archive set on the restore VPS. Required UK files are `uk-sys-configs-*.tar.gz`, `uk-secrets-*.tar.gz.age`, and the matching `manifest-*.txt`.

The manual break-glass SSH/WireGuard recovery bundle is documented separately in [BREAKGLASS_RECOVERY_BUNDLE.md](./BREAKGLASS_RECOVERY_BUNDLE.md). Keep the AGE private identity offline and separate from the Google Drive upload location.

## 21. Europe Restore From Google Drive

If Google Drive is the source for Europe restore, copy the Europe set into the standard restore path:

```bash
sudo mkdir -p /opt/apps/restore-materials/backups
sudo chown -R administrator:administrator /opt/apps/restore-materials
rclone copy gdrive-crypt:europe/ /opt/apps/restore-materials/backups/ -P
cd /opt/apps/restore-materials/backups
ls -1 europe-app-family-hero-hub-*.tar.gz
ls -1 europe-app-hermes-*.tar.gz
ls -1 europe-app-internal-tools-*.tar.gz
ls -1 europe-home-hermes-*.tar.gz
ls -1 europe-sys-configs-*.tar.gz
ls -1 europe-secrets-*.tar.gz.age
ls -1 manifest-*.txt
sha256sum -c manifest-*.txt --ignore-missing
```

Expected output: all selected Europe archives are present and checksum verification returns `OK`.

Stop conditions:

- `rclone.conf` is missing and cannot be securely recreated from offline credentials.
- `rclone` lists encrypted/gibberish Drive UI names instead of readable `gdrive-crypt:` names.
- Any command would print `rclone.conf`, OAuth tokens, crypt passwords, age private key, or decrypted secret contents.
- Manifest verification fails.

After download, continue with `RESTORE_EUROPE_SERVER.md`; do not extract or decrypt directly from the Google Drive staging command.

## 22. Final verification status

Verified on 2026-05-20:

- UK `gdrive-crypt` listing shows `uk-sys-configs-20260520-131436.tar.gz`, `uk-secrets-20260520-131436.tar.gz.age`, and `manifest-20260520-131436.txt`.
- The same recovery path is expected to expose readable mirrored US and Europe archive names through `gdrive-crypt:` rather than through the encrypted Google Drive UI.
- This confirms encrypted Google Drive upload and listing worked after the verified backup runs.
- `rclone-remotes.txt` and `google-drive-sync-status.txt` are now part of the UK restore-readiness archive proof set.

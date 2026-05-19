# Google Drive Backup & Recovery

## 1. Purpose
Pull encrypted backups from Google Drive if all servers are lost.

## 2. Scope
Recovery of `us/`, `europe/`, and `uk/` backup sets from the cloud.

## 3. When to use this restore path
Complete catastrophic failure where US, Europe, and UK local backup stores are all destroyed.

## 4. What this restores
Encrypted `.tar.gz` and `.age` archives.

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

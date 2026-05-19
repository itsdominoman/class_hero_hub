# Restore Secrets

## 1. Purpose
Recover `.env` files, WireGuard keys, `rclone.conf` and other sensitive credentials.

## 2. Scope
`us-secrets-*.age`, `europe-secrets-*.age`, `uk-secrets-*.age`.

## 3. When to use this restore path
Server rebuild, accidental deletion of `.env`, or WireGuard key loss.

## 4. What this restores
- `.env` files (App config, DB passwords, OAuth keys).
- WireGuard private configs (`/etc/wireguard/`).
- `rclone.conf` (on UK).
- QA env (`/home/administrator/.hermes/fhh-qa.env`).
- Hermes profiles/secrets.

## 5. What this does NOT restore
App code or system binaries.

## 6. Required access
Root/SSH on the target server.

## 7. Required offline secrets/keys
The offline `age` identity file (`key.txt`). 
**If the age private key / identity file is lost, encrypted secret archives cannot be decrypted. There is no magic recovery. That is the point of asymmetric public-key encryption.**

## 8. Required backup source options
Any local, mirrored, or Google Drive `*-secrets-*.tar.gz.age` file.

## 9. Required approval gates before destructive actions
Dom must provide the `age` key securely.

## 10. Exact backup source paths
`/opt/apps/backups/local/*-secrets-*.tar.gz.age` (or mirrors).

## 11. Exact restore target paths
Stage to `/tmp/secrets_recovery/` first.

## 12. Exact commands
```bash
# 1. Identify latest secrets archive
LATEST_SECRETS=$(ls -1t /tmp/recovery/*-secrets-*.tar.gz.age | head -1)

# 2. Decrypt using age to a staging folder first without printing contents
mkdir -p /tmp/secrets_recovery
age -d -i key.txt "$LATEST_SECRETS" | tar -xzf - -C /tmp/secrets_recovery/

# 3. Inspect filenames only, not values
find /tmp/secrets_recovery -type f

# 4. Restore .env files
sudo cp /tmp/secrets_recovery/opt/apps/family-hero-hub/.env /opt/apps/family-hero-hub/.env

# 5. Restore WireGuard configs
sudo cp -r /tmp/secrets_recovery/etc/wireguard/* /etc/wireguard/

# 6. Restore rclone config (if UK)
sudo cp /tmp/secrets_recovery/home/administrator/.config/rclone/rclone.conf ~/.config/rclone/

# 7. Set ownership and permissions
sudo chown administrator:administrator /opt/apps/family-hero-hub/.env
sudo chmod 600 /etc/wireguard/*.conf
sudo chown root:root /etc/wireguard/*.conf

# 8. Clean up staging
rm -rf /tmp/secrets_recovery
```

## 13. Expected outputs
Silent extraction.

## 14. Validation checks
Validate secrets exist without printing them:
`ls -la /opt/apps/family-hero-hub/.env`
`sudo ls -la /etc/wireguard/`

## 15. Failure handling
If `age` fails, verify `key.txt` is the correct private key corresponding to `age19pnauxyr2hcuyuf4l6q7c6rxcdxnulkjj5wq3urnt2ga5vkcdeps7dgm3w`.

## 16. Rollback notes
N/A

## 17. What not to do
Do NOT print the output or the `key.txt` into logs. Do NOT `cat .env`. Do NOT extract directly to `/` unless fully rebuilding the server.


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
Not rehearsed yet.

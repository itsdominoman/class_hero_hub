# Restore Secrets

## 1. Purpose
Recover `.env` files, WireGuard keys, `rclone.conf` and other sensitive credentials.

## 2. Scope
`us-secrets-*.age`, `europe-secrets-*.age`, `uk-secrets-*.age`.

## 3. When to use this restore path
Server rebuild, accidental deletion of `.env`, or WireGuard key loss.

## 4. What this restores
- `.env` files (App config, DB passwords, OAuth keys).
- `hermes-workspace/.env`.
- WireGuard private configs (`/etc/wireguard/`).
- `wg-easy/etc_wireguard/` on UK.
- `rclone.conf` (on UK).
- QA env (`/home/administrator/.hermes/fhh-qa.env`).
- Hermes auth/env state, profile env/auth files, state-snapshot auth/env files, and Hermes profiles/secrets.

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

## 20. Secret handling during fresh restore

Offline key location: Google Drive > keys > VPS Backups Key > `fhh-age-identity.txt`. If this key is lost, encrypted secrets archives cannot be decrypted.

Safe decrypt pattern:

```bash
mkdir -p /tmp/secrets_recovery
chmod 700 /tmp/secrets_recovery
age -d -i /path/to/fhh-age-identity.txt -o /tmp/secrets.tar.gz /tmp/recovery/<role>-secrets-<timestamp>.tar.gz.age
tar -xzf /tmp/secrets.tar.gz -C /tmp/secrets_recovery
rm -f /tmp/secrets.tar.gz
```

Place files without printing them:

```bash
sudo install -m 600 -o administrator -g administrator /tmp/secrets_recovery/opt/apps/family-hero-hub/.env /opt/apps/family-hero-hub/.env
sudo cp -a /tmp/secrets_recovery/etc/wireguard/. /etc/wireguard/
sudo chown root:root /etc/wireguard/*
sudo chmod 600 /etc/wireguard/*.conf /etc/wireguard/*.private 2>/dev/null || true
```

Role-specific encrypted secrets must include `.env` files, WireGuard private state, wg-easy `.env`, backup automation SSH private keys needed by that role, UK `rclone.conf`, cloudflared credentials if present, and Hermes/QA/API/OAuth tokens if present.

## 21. Europe Restore Secret Coverage

For Europe, the encrypted secrets archive must include these restore-critical files:

```text
/opt/apps/family-hero-hub/.env
/opt/apps/hermes-workspace/.env
/opt/apps/wg-easy/.env
/opt/apps/wg-easy/etc_wireguard/
/home/administrator/.hermes/.env
/home/administrator/.hermes/*.env
/home/administrator/.hermes/auth.json
/home/administrator/.hermes/auth.lock
/home/administrator/.hermes/auth/
/home/administrator/.hermes/fhh-qa.env
/home/administrator/.hermes/profiles/*/.env
/home/administrator/.hermes/profiles/*/*.env
/home/administrator/.hermes/profiles/*/auth.json
/home/administrator/.hermes/profiles/*/auth.lock
/home/administrator/.hermes/profiles/*/secrets.env
/home/administrator/.hermes/state-snapshots/*/.env
/home/administrator/.hermes/state-snapshots/*/auth.json
/etc/wireguard/
/home/administrator/.ssh/europe-to-us-backups
/home/administrator/.ssh/europe-to-uk-backups
/home/administrator/.ssh/known_hosts
```

Validate by filename only:

```bash
find /opt/apps/restore-materials/secrets-staging -type f -printf '%p\n' | sort
```

Expected output: filenames appear; no secret contents are printed.

Stop conditions:

- The age identity key is missing or fails to decrypt.
- Backup SSH keys are missing; US/UK backup copy cannot proceed.
- Latest archive lacks wg-easy state; inspect older encrypted Europe secrets archives without printing contents.
- Any command would print `.env`, private keys, WireGuard private keys, age key material, tokens, or `rclone.conf`.

Do not restore secrets directly to `/`. Decrypt to staging, validate filenames, then copy exact files into exact restore targets after approval.

Europe remediated backup proof from 2026-05-20:

- `/opt/apps/backups/local/europe-secrets-20260520-160643.tar.gz.age` exists.
- `/opt/apps/backups/local/europe-home-hermes-20260520-160643.tar.gz` has no obvious Hermes secret filenames matching `auth.json`, `.env`, `token`, `secret`, or `key`, so Hermes secret-bearing files should be restored from the encrypted Europe secrets archive.

The manual break-glass SSH/WireGuard recovery bundle is documented separately in [BREAKGLASS_RECOVERY_BUNDLE.md](./BREAKGLASS_RECOVERY_BUNDLE.md). Use that page for the offsite bundle naming and storage rules; keep the AGE private identity outside the upload folder.

# Break-Glass Recovery Bundle

## 1. Purpose
Document the manual offsite recovery bundle for SSH and WireGuard recovery material.

## 2. Scope
The human-prepared bundle created on the home machine under `/home/aibotadmin/documents/fhh-breakglass-YYYYMMDD/` and intended for manual upload to Google Drive.

## 3. What this bundle is for
- Offsite encrypted recovery material for SSH and WireGuard recovery.
- A readable outer wrapper so a human can identify the bundle without decrypting filename noise.
- A manual fallback alongside the normal encrypted Drive backups.

## 4. What this does not do
- It does not replace the normal mirrored backup flow.
- It does not store any private identity files inside the same Drive folder as the encrypted archive.

## 5. Bundle design
The outer folder uses readable filenames, while sensitive contents remain encrypted inside the `.age` archive.

Expected files:

- `fhh-breakglass-ssh-wireguard-YYYYMMDD.tar.gz.age`
- `SHA256SUMS-YYYYMMDD.txt`
- `FHH_BREAKGLASS_README_YYYYMMDD.txt`
- `FHH_BREAKGLASS_AGE_RECIPIENT_PUBLIC.txt`

Expected host folders inside the archive may include:

- `fhh-europe-breakglass`
- `fhh-us-breakglass`
- `fhh-uk-breakglass`
- `fhh-singapore-breakglass`
- `fhh-restore-breakglass`
- `fhh-home-brain-breakglass`

Typical contents inside each host folder may include:

- `HOSTINFO.txt`
- SSH folder snapshots
- `/etc/wireguard` snapshots where available

## 6. Security rules
- The AGE private identity file must not be uploaded into the same Google Drive folder as the encrypted archive.
- Store the AGE private identity separately and offline, such as in a password manager secure note or on removable media kept offline.
- Do not document or print AGE private identity contents.

## 7. Verification
Last verified on `2026-06-01`:

- The manual bundle naming exists as a readable outer wrapper for offsite recovery.
- The archive contents are meant to remain encrypted inside the `.age` file.
- The AGE private identity remains separate from the upload location.

## 8. Pending / Next Pass
- Update this bundle again after the server hardening documentation pass is complete.

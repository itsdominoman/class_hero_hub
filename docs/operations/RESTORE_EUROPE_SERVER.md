# Restore Europe Server

Use this as the strict Europe/dev/Hermes disaster recovery runbook. Do not use it as a loose checklist. Each phase is a gate: if the expected output does not match, stop and fix that layer before continuing.

Lessons learned source copied into this repo: `docs/operations/RESTORE_EUROPE_LESSONS_LEARNED.md`.

## Global Rules

- Do not print `.env`, private keys, WireGuard private keys, `rclone.conf`, OAuth tokens, API tokens, or age private keys.
- Do not change DNS without Dom approval.
- Do not deploy app changes during restore.
- Do not stop production services unless Dom approves the failover or teardown step.
- Do not delete backups or staging folders until final validation and archive review pass.
- Do not expose new public ports.
- Do not touch Mailcow beyond inventory.
- Do not commit or push runbook changes until Dom approves.
- Do not enable backup timers until all restore validation passes and duplicate backup streams are ruled out.

## Standard Restore Paths

```bash
sudo mkdir -p /opt/apps/restore-materials/docs
sudo mkdir -p /opt/apps/restore-materials/backups
sudo mkdir -p /opt/apps/restore-materials/keys
sudo mkdir -p /opt/apps/restore-test
sudo chown -R administrator:administrator /opt/apps/restore-materials /opt/apps/restore-test
```

Expected output: the four directories exist under `/opt/apps`.

Stop conditions: any path cannot be created, ownership is wrong, or the target is not the intended restore VPS.

Do not touch: `/opt/apps/backups` on surviving source servers, DNS, production app services, Mailcow.

Rollback/backup step: no rollback needed for new empty directories.

Approval gate: Dom approval required before overwriting any existing `/opt/apps/*` service directory.

## Backup Source Map

| Backup type | Expected source | Expected path or pattern |
|---|---|---|
| Europe app archive | UK backup hub, US mirror, Google Drive, or Europe local if original Europe is available | UK/US mirror: `/opt/apps/backups/from-europe/europe-app-family-hero-hub-*.tar.gz`; Europe local: `/opt/apps/backups/local/europe-app-family-hero-hub-*.tar.gz`; restore VPS staging: `/opt/apps/restore-materials/backups/europe-app-family-hero-hub-*.tar.gz` |
| Europe Hermes app | same | `europe-app-hermes-*.tar.gz` in the selected source folder |
| Europe internal tools | same | `europe-app-internal-tools-*.tar.gz` in the selected source folder |
| Europe Hermes home | same | `europe-home-hermes-*.tar.gz` in the selected source folder |
| Europe sys configs | same | `europe-sys-configs-*.tar.gz` in the selected source folder |
| Europe secrets | same | `europe-secrets-*.tar.gz.age` in the selected source folder |
| Manifest | same folder as selected backup set | `manifest-*.txt` |
| Europe SQLite DB source | restored app archive | `/opt/apps/family-hero-hub/data/family_hero_hub.sqlite` |
| US production Postgres | US pgBackRest repo only | `us-pgbackrest-repo-*.tar.gz` |
| wg-easy older state | older Europe encrypted secrets archive if latest is incomplete | `europe-secrets-20260520-010000.tar.gz.age` or older matching set |

Historical test-proven set from the May 2026 drill, retained only as a reference. Do not use this timestamp as a default:

```text
europe-app-family-hero-hub-20260520-054833.tar.gz
europe-app-hermes-20260520-054833.tar.gz
europe-app-internal-tools-20260520-054833.tar.gz
europe-home-hermes-20260520-054833.tar.gz
europe-sys-configs-20260520-054833.tar.gz
europe-secrets-20260520-054833.tar.gz.age
manifest-20260520-054833.txt
```

Do not restore `us-pgbackrest-repo-*` into Europe dev unless Dom explicitly approves seeding Europe dev from US production. Before any pgBackRest restore, prove origin, environment, database name, stanza, timestamp, and intended target.

Before extracting anything, Codex must identify the intended Europe archive set and use that selected set consistently. Do not mix timestamps.

Use an explicit Dom-approved timestamp:

```bash
RESTORE_TS=<approved-europe-backup-timestamp>
APP_ARCHIVE="/opt/apps/restore-materials/backups/europe-app-family-hero-hub-${RESTORE_TS}.tar.gz"
HERMES_ARCHIVE="/opt/apps/restore-materials/backups/europe-app-hermes-${RESTORE_TS}.tar.gz"
INTERNAL_ARCHIVE="/opt/apps/restore-materials/backups/europe-app-internal-tools-${RESTORE_TS}.tar.gz"
HERMES_HOME_ARCHIVE="/opt/apps/restore-materials/backups/europe-home-hermes-${RESTORE_TS}.tar.gz"
SYS_ARCHIVE="/opt/apps/restore-materials/backups/europe-sys-configs-${RESTORE_TS}.tar.gz"
SECRETS_ARCHIVE="/opt/apps/restore-materials/backups/europe-secrets-${RESTORE_TS}.tar.gz.age"
MANIFEST="/opt/apps/restore-materials/backups/manifest-${RESTORE_TS}.txt"
```

Or discover the latest complete set and then record the chosen timestamp:

```bash
cd /opt/apps/restore-materials/backups
RESTORE_TS="$(
  for ts in $(ls -1t europe-sys-configs-*.tar.gz | sed -E 's/^europe-sys-configs-([0-9-]+)\.tar\.gz$/\1/'); do
    test -s "europe-app-family-hero-hub-${ts}.tar.gz" &&
    test -s "europe-app-hermes-${ts}.tar.gz" &&
    test -s "europe-app-internal-tools-${ts}.tar.gz" &&
    test -s "europe-home-hermes-${ts}.tar.gz" &&
    test -s "europe-sys-configs-${ts}.tar.gz" &&
    test -s "europe-secrets-${ts}.tar.gz.age" &&
    test -s "manifest-${ts}.txt" &&
    { printf '%s\n' "$ts"; break; }
  done
)"
test -n "$RESTORE_TS"
APP_ARCHIVE="/opt/apps/restore-materials/backups/europe-app-family-hero-hub-${RESTORE_TS}.tar.gz"
HERMES_ARCHIVE="/opt/apps/restore-materials/backups/europe-app-hermes-${RESTORE_TS}.tar.gz"
INTERNAL_ARCHIVE="/opt/apps/restore-materials/backups/europe-app-internal-tools-${RESTORE_TS}.tar.gz"
HERMES_HOME_ARCHIVE="/opt/apps/restore-materials/backups/europe-home-hermes-${RESTORE_TS}.tar.gz"
SYS_ARCHIVE="/opt/apps/restore-materials/backups/europe-sys-configs-${RESTORE_TS}.tar.gz"
SECRETS_ARCHIVE="/opt/apps/restore-materials/backups/europe-secrets-${RESTORE_TS}.tar.gz.age"
MANIFEST="/opt/apps/restore-materials/backups/manifest-${RESTORE_TS}.txt"
ls -lah "$APP_ARCHIVE" "$HERMES_ARCHIVE" "$INTERNAL_ARCHIVE" "$HERMES_HOME_ARCHIVE" "$SYS_ARCHIVE" "$SECRETS_ARCHIVE" "$MANIFEST"
```

Expected output: every file in the selected set exists. Stop if any selected archive is missing.

Europe local note: `/opt/apps/backups/from-europe/` is not expected on the Europe server itself. Europe stores its own backups under `/opt/apps/backups/local/`; `from-europe/` is expected on US and UK mirrors, and on a restored UK hub after it resumes receiving Europe mirrors.

## Phase 1: Confirm Restore Role And Original Europe State

Purpose: prevent duplicate Europe identities and accidental production impact.

Commands:

```bash
hostname
hostnamectl
ip -br addr
curl -4 ifconfig.me
```

Expected output: this is the fresh restore VPS. Historical May 2026 drill endpoints must not be reused as defaults; use the current restore VPS IP and current Europe public IP supplied by Dom.

Stop conditions: host is not the restore VPS, original Europe is active and not intentionally isolated, or Dom has not approved using the restored Europe WireGuard identity.

Do not touch: DNS, US/UK production services, Mailcow, original Europe services.

Rollback/backup step: record current hostname and IP output in `/opt/apps/restore-test/phase-01-identity.txt`.

Approval gate: Dom must confirm whether this is a real outage or a restore drill and whether original Europe is offline or still active.

## Phase 2: Bootstrap Fresh VPS

Purpose: install a safe base for restore tooling.

Commands:

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release tar gzip rsync unzip jq age wireguard wireguard-tools sqlite3 openssh-client openssh-server ufw nftables iptables python3 python3-venv
```

Expected output: packages install without errors; `sqlite3 --version`, `age --version`, and `wg --version` work.

Stop conditions: apt fails, SSH server is not reachable, or package install prompts cannot be resolved safely.

Do not touch: app directories, backups, DNS, production services.

Rollback/backup step: none for base packages; save apt errors to `/opt/apps/restore-test/phase-02-apt-errors.txt`.

Approval gate: none unless replacing an existing non-fresh host.

## Phase 3: Create Administrator User And Sudo Access

Purpose: standardize the restore operator account.

Commands:

```bash
id administrator || sudo adduser administrator
sudo usermod -aG sudo administrator
sudo install -d -m 700 -o administrator -g administrator /home/administrator/.ssh
id administrator
```

Expected output: `administrator` exists and is a member of `sudo`.

Stop conditions: cannot create the user, home directory is missing, or sudo membership does not apply after a new login.

Do not touch: root SSH keys unless Dom explicitly approves.

Rollback/backup step: if modifying an existing user, save `id administrator` output first.

Approval gate: Dom approval required before removing or replacing existing users.

## Phase 4: Install Required Tools Including Node 22 And Caddy

Purpose: avoid Ubuntu default Node 18 and make Caddy validation possible before service start.

Commands:

```bash
sudo apt-get remove -y nodejs npm || true
sudo apt-get autoremove -y || true
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
sudo chmod 644 /etc/apt/keyrings/nodesource.gpg
NODE_MAJOR=22
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" | sudo tee /etc/apt/sources.list.d/nodesource.list
sudo apt-get update
sudo apt-get install -y nodejs docker.io docker-compose-v2 debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update
sudo apt-get install -y caddy
node --version
npm --version
caddy version
docker --version
docker compose version
```

Expected output: Node is `v22.x`; `caddy version`, `docker --version`, and `docker compose version` succeed.

Stop conditions: Node is v18, Caddy is missing, Docker Compose is missing, or apt configuration prompts would overwrite existing configs without review.

Do not touch: `/etc/caddy/Caddyfile` until the restored Caddyfile is staged.

Rollback/backup step: if `/etc/apt/sources.list.d/nodesource.list` already exists, copy it before editing.

Approval gate: Dom approval required before replacing an existing package source on a non-fresh host.

## Phase 5: Enable Temporary Passwordless Sudo For Codex Only

Purpose: allow non-interactive root-required restore steps.

Commands:

```bash
sudo tee /etc/sudoers.d/99-fhh-restore-administrator >/dev/null <<'EOSUDO'
administrator ALL=(ALL) NOPASSWD:ALL
EOSUDO
sudo chmod 440 /etc/sudoers.d/99-fhh-restore-administrator
sudo visudo -cf /etc/sudoers.d/99-fhh-restore-administrator
sudo -u administrator sudo -n whoami
```

Expected output:

```text
/etc/sudoers.d/99-fhh-restore-administrator: parsed OK
root
```

Stop conditions: `visudo` fails or `sudo -u administrator sudo -n whoami` does not print `root`.

Do not touch: any other sudoers file.

Rollback/backup step: remove only this temporary file if validation fails.

Approval gate: Dom must approve this restore-only sudo relaxation and it must be removed in Phase 31.

## Phase 6: Place Docs, Backups, And Keys In Standard Paths

Purpose: make all restore materials predictable.

Commands:

```bash
find /opt/apps/restore-materials -maxdepth 2 -type d -print
ls -lah /opt/apps/restore-materials/docs
ls -lah /opt/apps/restore-materials/backups
ls -lah /opt/apps/restore-materials/keys
```

Expected output: runbooks are in `docs`, selected backup set is in `backups`, age identity is in `keys`.

Stop conditions: backup set is incomplete, age identity is missing, or key file permissions are broader than owner-only.

Do not touch: decrypted secrets, live app paths, production sources.

Rollback/backup step: do not delete source copies from US/UK/Google Drive.

Approval gate: Dom must provide the age identity through a secure channel; never paste it into chat.

## Phase 7: Verify Age Identity Key

Purpose: confirm the offline key can decrypt secrets before any destructive restore.

Commands:

```bash
chmod 600 /opt/apps/restore-materials/keys/fhh-age-identity.txt
AGE_KEY=/opt/apps/restore-materials/keys/fhh-age-identity.txt
LATEST_SECRETS="${SECRETS_ARCHIVE:?set SECRETS_ARCHIVE from the selected Europe archive set first}"
test -s "$AGE_KEY"
test -s "$LATEST_SECRETS"
```

Expected output: no output and exit code `0`.

Stop conditions: key file missing, archive missing, or permissions cannot be restricted.

Do not touch: decrypted secret contents.

Rollback/backup step: none.

Approval gate: Dom must confirm this is the correct Europe secrets archive.

## Phase 8: Decrypt Secrets Into Staging Only

Purpose: inspect secret archive structure without writing to live paths.

Commands:

```bash
sudo rm -rf /opt/apps/restore-materials/secrets-staging
sudo install -d -m 700 -o administrator -g administrator /opt/apps/restore-materials/secrets-staging
age -d -i "$AGE_KEY" -o /opt/apps/restore-materials/secrets.tar.gz "$LATEST_SECRETS"
tar -xzf /opt/apps/restore-materials/secrets.tar.gz -C /opt/apps/restore-materials/secrets-staging
rm -f /opt/apps/restore-materials/secrets.tar.gz
find /opt/apps/restore-materials/secrets-staging -type f -printf '%p\n' | sort
```

Expected output: filenames only, including `/etc/wireguard`, Family Hero Hub `.env`, Hermes secrets, backup SSH keys, and wg-easy files if present.

Stop conditions: decryption fails, latest archive lacks required files, or any command would print file contents.

Do not touch: `/etc/wireguard`, `/opt/apps/*/.env`, or `/home/administrator/.ssh` yet.

Rollback/backup step: delete only the failed staging directory, not source archives.

Approval gate: Dom approval required before copying staged secrets into live paths.

## Phase 9: Restore SSH Keys And Validate Key-Based SSH To US/UK

Purpose: establish backup-source trust before copying or repairing anything remote.

Commands:

```bash
sudo install -d -m 700 -o administrator -g administrator /home/administrator/.ssh
sudo install -m 600 -o administrator -g administrator /opt/apps/restore-materials/secrets-staging/home/administrator/.ssh/europe-to-us-backups /home/administrator/.ssh/europe-to-us-backups
sudo install -m 600 -o administrator -g administrator /opt/apps/restore-materials/secrets-staging/home/administrator/.ssh/europe-to-uk-backups /home/administrator/.ssh/europe-to-uk-backups
sudo install -m 600 -o administrator -g administrator /opt/apps/restore-materials/secrets-staging/home/administrator/.ssh/known_hosts /home/administrator/.ssh/known_hosts 2>/dev/null || true
ssh-keygen -y -f /home/administrator/.ssh/europe-to-us-backups >/tmp/europe-to-us-backups.pub.check && echo "US key readable"
ssh-keygen -y -f /home/administrator/.ssh/europe-to-uk-backups >/tmp/europe-to-uk-backups.pub.check && echo "UK key readable"
cat > /home/administrator/.ssh/config <<'EOSSH'
Host us-mesh
    HostName 10.250.50.2
    User administrator
    IdentityFile /home/administrator/.ssh/europe-to-us-backups
    IdentitiesOnly yes

Host uk-mesh
    HostName 10.250.50.3
    User administrator
    IdentityFile /home/administrator/.ssh/europe-to-uk-backups
    IdentitiesOnly yes

Host us-public
    HostName <current-us-public-ip>
    User administrator
    IdentityFile /home/administrator/.ssh/europe-to-us-backups
    IdentitiesOnly yes

Host uk-public
    HostName <current-uk-public-ip>
    User administrator
    IdentityFile /home/administrator/.ssh/europe-to-uk-backups
    IdentitiesOnly yes
EOSSH
chmod 600 /home/administrator/.ssh/config
chown administrator:administrator /home/administrator/.ssh/config
ssh -o BatchMode=yes us-public 'hostname; echo US_PUBLIC_ALIAS_OK'
ssh -o BatchMode=yes uk-public 'hostname; echo UK_PUBLIC_ALIAS_OK'
```

Expected output: `US key readable`, `UK key readable`, `US_PUBLIC_ALIAS_OK`, `UK_PUBLIC_ALIAS_OK`.

Stop conditions: any password prompt appears, `BatchMode` fails, or keys are unreadable.

Do not touch: US/UK WireGuard configs or backup directories.

Rollback/backup step: if replacing existing SSH files, copy them to `/opt/apps/restore-materials/ssh-before-restore/` first.

Approval gate: Dom approval required before replacing existing SSH config on a non-fresh host.

## Phase 10: Use SSH Trust To Copy Backups From US/UK

Purpose: pull the selected Europe backup set from surviving sources.

Commands:

```bash
rsync -av --progress uk-public:/opt/apps/backups/from-europe/ /opt/apps/restore-materials/backups/
# If UK is unavailable:
rsync -av --progress us-public:/opt/apps/backups/from-europe/ /opt/apps/restore-materials/backups/
ls -lah /opt/apps/restore-materials/backups
```

Expected output: Europe app, Hermes, internal tools, home, sys-configs, secrets, and manifest files are present.

Stop conditions: SSH prompts for a password, backup set is incomplete, or timestamps do not match the intended restore set.

Do not touch: remote backups other than read-only copy.

Rollback/backup step: keep all copied archives until final cleanup.

Approval gate: none for read-only copy.

## Phase 11: Verify Backup Manifests And Checksums

Purpose: prove archive integrity before extraction.

Commands:

```bash
cd /opt/apps/restore-materials/backups
sha256sum -c "$MANIFEST"
```

Expected output: every selected archive reports `OK`.

Stop conditions: checksum mismatch, missing manifest, or selected archive not present in manifest.

Do not touch: live restore targets.

Rollback/backup step: fetch a different matching set from US/UK/Google Drive.

Approval gate: none.

## Phase 12: Extract Archives

Purpose: stage archive contents without assuming paths are correct.

Commands:

```bash
cd /opt/apps/restore-materials/backups
sudo tar -xzf "$APP_ARCHIVE" -C /
sudo tar -xzf "$HERMES_ARCHIVE" -C /
sudo tar -xzf "$INTERNAL_ARCHIVE" -C /
sudo tar -xzf "$HERMES_HOME_ARCHIVE" -C /
sudo tar -xzf "$SYS_ARCHIVE" -C /
ls -ld /family-hero-hub /hermes-agent /hermes-workspace /fhh-ops-dashboard /caddy-configs /systemd-units
```

Expected output: top-level extracted directories exist.

Stop conditions: tar fails, expected directory missing, or extraction would overwrite a live directory without approval.

Do not touch: `/opt/apps/*` yet.

Rollback/backup step: if existing top-level extracted directories exist, rename them with a timestamp before extraction.

Approval gate: Dom approval required before extracting over any existing non-empty target.

## Phase 13: Fix Archive Path Mapping Into `/opt/apps`

Purpose: map archive roots to actual service paths.

Commands:

```bash
sudo mkdir -p /opt/apps/family-hero-hub /opt/apps/hermes-agent /opt/apps/hermes-workspace /opt/apps/fhh-ops-dashboard
sudo rsync -aHAX --delete /family-hero-hub/ /opt/apps/family-hero-hub/
sudo rsync -aHAX --delete /hermes-agent/ /opt/apps/hermes-agent/
sudo rsync -aHAX --delete /hermes-workspace/ /opt/apps/hermes-workspace/
sudo rsync -aHAX --delete /fhh-ops-dashboard/ /opt/apps/fhh-ops-dashboard/
sudo chown -R administrator:administrator /opt/apps/family-hero-hub /opt/apps/hermes-agent /opt/apps/hermes-workspace /opt/apps/fhh-ops-dashboard
```

Expected output: commands are silent and target directories contain restored files.

Stop conditions: source top-level directories are missing or target contains unrelated live data.

Do not touch: do not delete `/family-hero-hub`, `/hermes-agent`, `/hermes-workspace`, or `/fhh-ops-dashboard` until final validation.

Rollback/backup step: copy existing `/opt/apps/*` target directories to `/opt/apps/restore-materials/pre-rsync-backups/` before `--delete` if the host is not fresh.

Approval gate: Dom approval required before any `rsync --delete` against a non-fresh target.

## Phase 14: Restore Caddy Config And Install Caddy

Purpose: put the restored Caddyfile where Caddy expects it and validate before reload.

Commands:

```bash
sudo mkdir -p /etc/caddy
sudo cp -a /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak-restore-$(date +%Y%m%d-%H%M%S) 2>/dev/null || true
sudo install -o root -g root -m 644 /caddy-configs/caddy/Caddyfile /etc/caddy/Caddyfile
caddy version
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl enable caddy
```

Expected output: `caddy version` succeeds and validation reports a valid config.

Stop conditions: `/caddy-configs/caddy/Caddyfile` missing, Caddy not installed, validation fails, or allowlist would expose private tools.

Do not touch: DNS, public Caddy records, Mailcow.

Rollback/backup step: restore the timestamped `/etc/caddy/Caddyfile.bak-*`.

Approval gate: Dom approval required before reloading Caddy if DNS points at the restore host.

## Phase 15: Restore Systemd Unit Files

Purpose: install units into the active systemd path.

Commands:

```bash
sudo install -o root -g root -m 644 /systemd-units/hermes-gateway.service /etc/systemd/system/hermes-gateway.service
sudo install -o root -g root -m 644 /systemd-units/hermes-dashboard.service /etc/systemd/system/hermes-dashboard.service
sudo install -o root -g root -m 644 /systemd-units/hermes-dashboard-vpn-allow.service /etc/systemd/system/hermes-dashboard-vpn-allow.service
sudo install -o root -g root -m 644 /systemd-units/hermes-workspace.service /etc/systemd/system/hermes-workspace.service
sudo install -o root -g root -m 644 /systemd-units/wg-personal-to-site-nat.service /etc/systemd/system/wg-personal-to-site-nat.service
sudo install -o root -g root -m 644 /systemd-units/wg-site-mesh-forward.service /etc/systemd/system/wg-site-mesh-forward.service
sudo systemctl daemon-reload
sudo systemctl cat hermes-gateway hermes-dashboard hermes-dashboard-vpn-allow hermes-workspace wg-personal-to-site-nat wg-site-mesh-forward
```

Expected output: `systemctl cat` prints the restored unit definitions.

Stop conditions: any unit file missing or references missing paths.

Do not touch: do not start services yet.

Rollback/backup step: copy existing `/etc/systemd/system/*.service` to `/opt/apps/restore-materials/systemd-before-restore/` before overwrite.

Approval gate: Dom approval required before overwriting existing units on a non-fresh host.

## Phase 16: Restore Helper Scripts Under `/usr/local/sbin`

Purpose: satisfy systemd unit `ExecStart` dependencies.

Commands:

```bash
sudo install -o root -g root -m 755 /helper-scripts/hermes-dashboard-vpn-allow.sh /usr/local/sbin/hermes-dashboard-vpn-allow.sh
sudo install -o root -g root -m 755 /helper-scripts/wg-personal-to-site-nat.sh /usr/local/sbin/wg-personal-to-site-nat.sh
sudo install -o root -g root -m 755 /helper-scripts/wg-site-mesh-forward.sh /usr/local/sbin/wg-site-mesh-forward.sh
ls -lah /usr/local/sbin/hermes-dashboard-vpn-allow.sh /usr/local/sbin/wg-personal-to-site-nat.sh /usr/local/sbin/wg-site-mesh-forward.sh
```

Expected output: all three scripts exist and are executable.

Stop conditions: helper scripts are missing from sys-config archive. Recreate only with Dom approval and document the exact content.

Do not touch: iptables rules until WireGuard phases.

Rollback/backup step: timestamp-copy existing helper scripts before replacing them.

Approval gate: Dom approval required before replacing helper scripts.

## Phase 17: Restore Site-To-Site WireGuard

Purpose: restore Europe mesh identity.

Commands:

```bash
sudo install -d -m 700 -o root -g root /etc/wireguard
sudo cp -a /etc/wireguard /opt/apps/restore-materials/etc-wireguard-before-restore-$(date +%Y%m%d-%H%M%S) 2>/dev/null || true
sudo cp -a /opt/apps/restore-materials/secrets-staging/etc/wireguard/. /etc/wireguard/
sudo chown root:root /etc/wireguard/*
sudo chmod 600 /etc/wireguard/*.conf /etc/wireguard/*.private 2>/dev/null || true
sudo systemctl enable --now wg-quick@wg-site
sudo systemctl enable --now wg-site-mesh-forward wg-personal-to-site-nat
sudo wg show wg-site
```

Expected output: `wg-site` exists with Europe address `10.250.50.1/24` and no private keys printed.

Stop conditions: original Europe is still active with the same identity and this is not an approved failover test; service fails; config missing.

Do not touch: US/UK peer configs until Phase 18.

Rollback/backup step: restore `/opt/apps/restore-materials/etc-wireguard-before-restore-*`.

Approval gate: Dom must approve starting restored Europe WireGuard identity.

## Phase 18: Update US/UK Peer Endpoints If Restore IP Changed

Purpose: point surviving peers at the restored Europe endpoint when required.

Commands on US and UK, only after approval:

```bash
RESTORE_PUBLIC_IP=<new-vps-ip>
ORIGINAL_EUROPE_PUBLIC_IP=<current-original-europe-public-ip>
sudo cp /etc/wireguard/wg-site.conf /etc/wireguard/wg-site.conf.bak-restore-europe-endpoint-$(date +%Y%m%d-%H%M%S)
sudo sed -i "s#Endpoint = ${ORIGINAL_EUROPE_PUBLIC_IP}:51830#Endpoint = ${RESTORE_PUBLIC_IP}:51830#g" /etc/wireguard/wg-site.conf
sudo systemctl restart wg-quick@wg-site
sudo wg show
```

Expected output: US/UK show recent handshakes with the restore endpoint.

Stop conditions: this is only a drill and original Europe is still active without intentional endpoint failover testing.

Do not touch: DNS unless Dom explicitly approves.

Rollback/backup step: restore the timestamped `wg-site.conf.bak-*`.

Approval gate: Dom approval required on each surviving peer before endpoint edits.

## Phase 19: Validate Mesh Handshakes, Ping, And SSH

Purpose: prove the mesh works, not just the local service.

Commands:

```bash
sudo wg show wg-site
ping -c 3 10.250.50.2
ping -c 3 10.250.50.3
ssh -o BatchMode=yes us-mesh 'hostname; echo US_MESH_OK'
ssh -o BatchMode=yes uk-mesh 'hostname; echo UK_MESH_OK'
```

Expected output: recent handshakes, `0% packet loss`, `US_MESH_OK`, and `UK_MESH_OK`.

Stop conditions: stale/no handshakes, packet loss, SSH password prompt, or `BatchMode` failure.

Do not touch: app services before this gate passes.

Rollback/backup step: revert US/UK endpoint changes if the restore endpoint fails.

Approval gate: none for validation.

## Phase 20: Restore wg-easy User VPN State And Config

Purpose: restore mobile/user VPN separately from site mesh.

Commands:

```bash
sudo mkdir -p /opt/apps/wg-easy/etc_wireguard
sudo install -o administrator -g administrator -m 600 /opt/apps/restore-materials/secrets-staging/opt/apps/wg-easy/.env /opt/apps/wg-easy/.env
sudo rsync -a /opt/apps/restore-materials/secrets-staging/opt/apps/wg-easy/etc_wireguard/ /opt/apps/wg-easy/etc_wireguard/
sudo install -o administrator -g administrator -m 644 /app-configs/wg-easy/docker-compose.yml /opt/apps/wg-easy/docker-compose.yml
cd /opt/apps/wg-easy
docker compose config
docker compose up -d
sudo ss -ltnup | grep -E '51820|51821'
sudo docker exec wg-easy-europe sh -lc 'iptables -t nat -S | grep -E "10.8|10.60|MASQUERADE"'
```

Expected output: UDP `51820`, admin bind `10.250.50.1:51821`, bind mount `./etc_wireguard:/etc/wireguard`, `WG_DEFAULT_ADDRESS=10.60.0.x` in `.env`, and NAT for `10.60.0.0/24` rather than `10.8.0.0/24`.

Stop conditions: latest archive lacks `wg0.conf` or `wg0.json`; inspect older encrypted Europe secrets archives without printing contents. Stop if compose uses a named volume for `/etc/wireguard`.

Do not touch: real client configs unless Dom approves rotating or regenerating profiles.

Rollback/backup step: timestamp-copy `/opt/apps/wg-easy` before replacing files.

Approval gate: Dom approval required before changing wg-easy admin password or client profiles.

## Phase 21: Validate Real VPN Client Access

Purpose: prove user VPN routing works from an actual laptop or phone.

Commands from the real client:

```text
Profile must show:
Address = 10.60.0.x/24
Endpoint = dev.familyherohub.com:51820
AllowedIPs = 10.250.50.0/24

ping 10.250.50.1
open http://10.250.50.1:51821
open http://10.250.50.1:9119
open http://10.250.50.1:3000
ssh administrator@10.250.50.1
```

Expected output: client reaches mesh IP, wg-easy admin, Hermes dashboard, Hermes workspace, and SSH.

Stop conditions: handshake works but client cannot reach `10.250.50.1`; check NAT for `10.60.0.0/24`.

Do not touch: firewall enabling before this gate passes.

Rollback/backup step: revert wg-easy compose/env/state from backup.

Approval gate: Dom must confirm real-client validation.

## Phase 22: Start Hermes Services

Purpose: start Hermes only after VPN, secrets, units, helper scripts, and Node 22 are ready.

Commands:

```bash
sudo install -o administrator -g administrator -m 600 /opt/apps/restore-materials/secrets-staging/home/administrator/.hermes/fhh-qa.env /home/administrator/.hermes/fhh-qa.env 2>/dev/null || true
sudo install -o administrator -g administrator -m 600 /opt/apps/restore-materials/secrets-staging/opt/apps/hermes-workspace/.env /opt/apps/hermes-workspace/.env 2>/dev/null || true
cd /opt/apps/hermes-workspace
node --version
rm -rf node_modules
npm install
sudo cp /etc/systemd/system/hermes-workspace.service /etc/systemd/system/hermes-workspace.service.bak-bind-$(date +%Y%m%d-%H%M%S)
sudo perl -0pi -e 's|ExecStart=/usr/bin/npm run dev$|ExecStart=/usr/bin/npm run dev -- --host 10.250.50.1|' /etc/systemd/system/hermes-workspace.service
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-gateway hermes-dashboard hermes-dashboard-vpn-allow hermes-workspace
sudo ss -ltnup | grep -E '9119|3000'
```

Expected output: Node `v22.x`; Hermes dashboard binds private IP; Hermes workspace binds `10.250.50.1:3000`, not `0.0.0.0:3000`.

Stop conditions: Node is too old, workspace binds publicly, missing secrets, or services fail with `203/EXEC`.

Do not touch: Telegram tokens or print Hermes secret files.

Rollback/backup step: restore the timestamped Hermes workspace unit.

Approval gate: Dom approval required before sending real Telegram commands.

## Phase 23: Start Family Hero Hub Containers

Purpose: start app stack after infrastructure dependencies pass.

Commands:

```bash
sudo install -o administrator -g administrator -m 600 /opt/apps/restore-materials/secrets-staging/opt/apps/family-hero-hub/.env /opt/apps/family-hero-hub/.env
cd /opt/apps/family-hero-hub
docker compose config
docker compose up -d postgres
docker compose up -d backend frontend
docker compose ps
curl -I http://127.0.0.1:8000/docs
curl -I http://127.0.0.1:5173
```

Expected output: compose config is valid; postgres, backend, and frontend are running; local HTTP checks return success or redirects.

Stop conditions: compose invalid, containers crash, or `.env` missing.

Do not touch: database data import until schema gate passes.

Rollback/backup step: save `docker compose ps` and logs before changes.

Approval gate: Dom approval required before clearing or importing database data.

## Phase 24: Validate Postgres Schema

Purpose: prove DB readiness before OAuth.

Commands:

```bash
cd /opt/apps/family-hero-hub
docker compose exec -T postgres psql -U familyhero -d family_hero_hub_dev -c '\dt'
docker compose exec -T postgres psql -U familyhero -d family_hero_hub_dev -c 'select * from alembic_version;'
docker compose exec -T backend alembic upgrade head
```

Expected output: `alembic_version` exists and critical tables include `approved_parent_emails`, `parent_users`, `families`, `children`, `ledger_transactions`, `redemption_requests`, `rewards`, `calendar_entries`, and `school_items`.

Stop conditions: Postgres is healthy but tables are missing, Alembic fails, or backend cannot connect.

Do not touch: OAuth validation before schema exists.

Rollback/backup step: dump DB before migrations if any data exists.

Approval gate: Dom approval required before destructive schema repair.

## Phase 25: Restore Europe Dev Data From Correct Europe Source

Purpose: import Europe dev data from SQLite when no Europe pgBackRest repo exists.

Commands:

```bash
cd /opt/apps/family-hero-hub
test -s /opt/apps/family-hero-hub/data/family_hero_hub.sqlite
mkdir -p /opt/apps/restore-materials/db-before-sqlite-import
docker compose exec -T postgres pg_dump -U familyhero -d family_hero_hub_dev > /opt/apps/restore-materials/db-before-sqlite-import/family_hero_hub_dev_before_sqlite_import_$(date +%Y%m%d_%H%M%S).sql
docker compose exec -T backend python backend/scripts/migrate_sqlite_to_postgres.py --dry-run --source-path /opt/apps/family-hero-hub/data/family_hero_hub.sqlite
docker compose stop backend frontend
docker compose run --rm backend python backend/scripts/migrate_sqlite_to_postgres.py --import --yes-i-understand-this-writes-postgres --clear-target --source-path /opt/apps/family-hero-hub/data/family_hero_hub.sqlite
docker compose up -d backend frontend
docker compose exec -T postgres psql -U familyhero -d family_hero_hub_dev -c "
select 'parent_users' table_name, count(*) from parent_users
union all select 'families', count(*) from families
union all select 'children', count(*) from children
union all select 'ledger_transactions', count(*) from ledger_transactions
union all select 'rewards', count(*) from rewards
union all select 'approved_parent_emails', count(*) from approved_parent_emails
union all select 'redemption_requests', count(*) from redemption_requests
union all select 'calendar_entries', count(*) from calendar_entries
union all select 'school_items', count(*) from school_items;
"
```

Expected Europe dev counts from the restore test:

```text
parent_users: 7
families: 4
children: 7
ledger_transactions: 97
rewards: 10
approved_parent_emails: 8
redemption_requests: 8
calendar_entries: 19
school_items: 47
```

Stop conditions: SQLite file missing, dry run fails, dump fails, or row counts do not match expected Europe dev data.

Do not touch: US pgBackRest repo unless intentionally seeding from production.

Rollback/backup step: restore the pre-import `pg_dump`.

Approval gate: Dom approval required before `--clear-target`.

## Phase 26: Validate OAuth

Purpose: verify the full OAuth chain after DB schema and data gates.

Commands and checks:

```text
1. DNS points to the intended restore server. DNS changes require Dom approval.
2. Caddy allowlist includes the current admin/browser public IP exactly.
3. Google Cloud Console callback URI exists:
   https://dev.familyherohub.com/api/auth/google/callback
4. Backend route is reachable:
   https://dev.familyherohub.com/api/auth/google/login
5. DB schema exists.
6. approved_parent_emails contains restored rows.
7. UI shows restored family data after login.
```

Expected output: Google login completes and the parent dashboard loads with restored data.

Stop conditions: DNS wrong, Caddy 403, callback URI missing, backend exception, `approved_parent_emails` missing/empty, or UI shows empty bootstrap data.

Do not touch: DNS or Google Cloud Console without Dom approval.

Rollback/backup step: restore previous Caddyfile if allowlist edit breaks access.

Approval gate: Dom approval required for DNS/provider/Google Console edits.

## Phase 27: Validate UI Data

Purpose: prove login is not merely successful but data is restored.

Commands:

```bash
cd /opt/apps/family-hero-hub
docker compose ps
docker compose logs --tail=100 backend
```

Expected output: no DB missing-table errors; parent dashboard shows parents, families, children, ledger, rewards, calendar, and school data.

Stop conditions: empty family data after OAuth, backend errors, or row counts changed unexpectedly.

Do not touch: production data.

Rollback/backup step: use the pre-import dump from Phase 25.

Approval gate: Dom confirms UI data is correct.

## Phase 28: Validate Dashboards And Internal Tools

Purpose: verify Hermes/internal tools are private and functional.

Commands:

```bash
sudo ss -ltnup | grep -E '8765|8766|8767|8768|9119|3000' || true
systemctl list-units --all | grep -Ei 'fhh|ops|viewer|docs|competitor' || true
find /opt/apps/fhh-ops-dashboard -maxdepth 3 -type f | head -50
curl -I http://10.250.50.1:9119
curl -I http://10.250.50.1:3000
curl -I http://10.250.50.1:8765
curl -I http://10.250.50.1:8766
curl -I http://10.250.50.1:8767
```

Expected output: tools bind to VPN/private IPs only, not public internet; HTTP checks work from VPN/mesh.

Stop conditions: any internal tool binds `0.0.0.0` or public interfaces unexpectedly.

Do not touch: Caddy public exposure without approval.

Rollback/backup step: stop the offending internal tool and restore previous unit/config.

Approval gate: Dom approval required before exposing any internal tool publicly, even temporarily.

## Phase 29: Configure Firewall/UFW

Purpose: harden only after all access paths are proven.

Commands:

```bash
sudo ufw status verbose
sudo ss -ltnup
sudo ufw allow from <admin_public_ip> to any port 22 proto tcp comment 'temporary DR SSH'
sudo ufw allow 80/tcp comment 'Caddy HTTP'
sudo ufw allow 443/tcp comment 'Caddy HTTPS'
sudo ufw allow 51820/udp comment 'wg-easy user VPN'
sudo ufw allow 51830/udp comment 'site-to-site WireGuard'
sudo ufw --force enable
sudo ufw status verbose
```

Expected output: SSH remains reachable; public listeners are limited to intended ports; private listeners remain private.

Stop conditions: SSH key trust, mesh, user VPN, admin IP allowlist, Caddy, or wg-easy validation has not passed.

Do not touch: provider firewall unless Dom approves.

Rollback/backup step: save `sudo ufw status numbered` before changes and delete bad rules by number.

Approval gate: Dom must approve enabling UFW.

## Phase 30: Re-enable Backup Timers Only After Validation Passes

Purpose: avoid duplicate or corrupt backup streams during drills.

Commands:

```bash
systemctl list-timers --all | grep -Ei 'backup|pgbackrest|fhh|hermes' || true
systemctl list-unit-files | grep -Ei 'backup|pgbackrest|fhh|hermes' || true
sudo systemctl enable --now fhh-europe-backup.timer fhh-europe-pull-us.timer
```

Expected output: timers are enabled only after this server is the active Europe role.

Stop conditions: original Europe still runs backups, validation incomplete, or Dom has not approved activation.

Do not touch: backup archive deletion or retention changes.

Rollback/backup step: `sudo systemctl disable --now fhh-europe-backup.timer fhh-europe-pull-us.timer`.

Approval gate: Dom approval required.

## Phase 31: Remove Temporary Passwordless Sudo

Purpose: restore normal sudo security.

Commands:

```bash
sudo rm -f /etc/sudoers.d/99-fhh-restore-administrator
sudo visudo -c
sudo -u administrator sudo -n whoami || echo "Passwordless sudo removed"
```

Expected output: `visudo` passes and `Passwordless sudo removed` prints.

Stop conditions: `visudo` fails.

Do not touch: other sudoers files.

Rollback/backup step: if sudo breaks, use provider console/root recovery.

Approval gate: none; this cleanup is mandatory.

## Phase 32: Archive And Clean Staging Folders

Purpose: preserve forensic context, then remove risky staging files.

Commands:

```bash
sudo tar -czf /opt/apps/restore-test/europe-restore-staging-review-$(date +%Y%m%d-%H%M%S).tar.gz \
  /opt/apps/restore-materials \
  /family-hero-hub /hermes-agent /hermes-workspace /fhh-ops-dashboard /caddy-configs /systemd-units /helper-scripts /app-configs 2>/dev/null
sudo rm -rf /opt/apps/restore-materials/secrets-staging
```

Expected output: review archive exists; decrypted secrets staging is removed.

Stop conditions: final validation incomplete or Dom has not approved deleting staging.

Do not touch: source backups or encrypted archives.

Rollback/backup step: review archive is the rollback reference for staging metadata.

Approval gate: Dom approval required before deleting non-secret extracted directories.

## Restore Drill Teardown

Use only for a test where original Europe remains the real active server.

Commands on restore VPS:

```bash
sudo systemctl stop wg-quick@wg-site
sudo systemctl disable wg-quick@wg-site
cd /opt/apps/wg-easy
docker compose down || true
```

Commands on US/UK:

```bash
RESTORE_PUBLIC_IP=<restore-vps-ip-used-for-this-drill>
ORIGINAL_EUROPE_PUBLIC_IP=<current-original-europe-public-ip>
sudo cp /etc/wireguard/wg-site.conf /etc/wireguard/wg-site.conf.bak-return-to-real-europe-$(date +%Y%m%d-%H%M%S)
sudo sed -i -E "s#Endpoint = [0-9.]+:51830#Endpoint = ${ORIGINAL_EUROPE_PUBLIC_IP}:51830#g" /etc/wireguard/wg-site.conf
sudo systemctl restart wg-quick@wg-site
sudo wg show
```

Expected output: no peer still shows `${RESTORE_PUBLIC_IP}:51830`; US/UK point back to `${ORIGINAL_EUROPE_PUBLIC_IP}:51830`.

Stop conditions: original Europe is not healthy or endpoint ownership is unclear.

Do not touch: DNS without Dom approval.

Rollback/backup step: restore the timestamped US/UK WireGuard config backups.

Approval gate: Dom approval required before teardown endpoint changes.

Warning: never run original Europe and restore Europe simultaneously with the same WireGuard identity unless intentionally testing endpoint failover. US/UK peers may roam to whichever endpoint last sent traffic.

## Final Validation Checklist

```bash
hostname
hostnamectl
ip -br addr
curl -4 ifconfig.me
ssh -o BatchMode=yes us-mesh 'hostname'
ssh -o BatchMode=yes uk-mesh 'hostname'
ssh -o BatchMode=yes administrator@10.250.50.2 'hostname'
ssh -o BatchMode=yes administrator@10.250.50.3 'hostname'
sudo wg show wg-site
ping -c 3 10.250.50.2
ping -c 3 10.250.50.3
cd /opt/apps/wg-easy && docker compose ps
sudo ss -ltnup | grep -E '51820|51821'
sudo docker exec wg-easy-europe sh -lc 'wg show; iptables -t nat -S | grep -E "10.60|MASQUERADE"'
systemctl status hermes-gateway hermes-dashboard hermes-workspace --no-pager
curl -I http://10.250.50.1:9119
curl -I http://10.250.50.1:3000
cd /opt/apps/family-hero-hub && docker compose ps
curl -I http://127.0.0.1:8000/docs
curl -I http://127.0.0.1:5173
curl -I https://dev.familyherohub.com
docker compose exec -T postgres psql -U familyhero -d family_hero_hub_dev -c 'select * from alembic_version;'
sudo ufw status verbose
systemctl list-timers --all | grep -Ei 'backup|pgbackrest|fhh|hermes'
```

Real VPN client must also pass:

```text
Address = 10.60.0.x/24
Endpoint = dev.familyherohub.com:51820
AllowedIPs = 10.250.50.0/24
ping 10.250.50.1
http://10.250.50.1:51821
http://10.250.50.1:9119
http://10.250.50.1:3000
ssh administrator@10.250.50.1
```

OAuth must pass:

```text
Google callback URI:
https://dev.familyherohub.com/api/auth/google/callback

Browser test:
https://dev.familyherohub.com/api/auth/google/login

Success:
Login works, parent dashboard loads, restored children/family data appears.
```

Telegram/Hermes messaging validation:

```bash
systemctl status hermes-gateway --no-pager
journalctl -u hermes-gateway -n 100 --no-pager
```

Expected output: config and allowlists are present, a real Telegram command is received and processed, and no tokens are printed.

Last verified date: 2026-05-20 restore test lessons incorporated.

## Backup Proof Update

Completed Europe remediated backup-side proof from 2026-05-20:

- Latest remediated Europe Hermes home archive: `/opt/apps/backups/local/europe-home-hermes-20260520-160643.tar.gz`
- Latest remediated Europe secrets archive: `/opt/apps/backups/local/europe-secrets-20260520-160643.tar.gz.age`
- Latest remediated Europe sys-config archive: `/opt/apps/backups/local/europe-sys-configs-20260520-160643.tar.gz`
- `europe-home-hermes-20260520-160643.tar.gz` has no obvious Hermes secret filenames matching `auth.json`, `.env`, `token`, `secret`, or `key`.
- `europe-secrets-20260520-160643.tar.gz.age` exists.
- Verified sys-config archive members: `./app-configs/wg-easy/docker-compose.yml`, `./helper-scripts/wg-personal-to-site-nat.sh`, `./helper-scripts/wg-site-mesh-forward.sh`, `./helper-scripts/hermes-dashboard-vpn-allow.sh`

> Historical note: This document was inherited from Family Hero Hub and is preserved as historical context for the Class Hero Hub fork. It may describe old domains, paths, product assumptions, or infrastructure that are not current.

# Family Hero Hub Europe Restore Test — Full Documentation Issues, Restore Failures, and Lessons Learned

## Context

This document is a historical May 2026 restore-test record. Public IP addresses shown here are evidence from that drill only; do not use them as defaults in a future restore.

We ran a full restore test for the Europe/dev/Hermes server onto a fresh restore VPS.

Historical restore VPS used in this test only:

```text
95.111.243.235
```

Historical original Europe server at the time of this test only:

```text
213.199.61.244
```

The original Europe server was still alive because this was a restore test, not a true outage. However, the restore was intentionally treated like a real disaster recovery scenario.

The goal was to prove that the existing backup and restore documentation was sufficient to rebuild the Europe dev/Hermes server role from:

```text
docs/operations/
backup archives
encrypted secrets archive
age identity key
US/UK backup mirrors
WireGuard mesh
Hermes services
Family Hero Hub app stack
database backup/source
wg-easy user VPN
```

The result: **the system was recoverable, but the documentation and backup coverage were not good enough.**

The restore took over **5 hours** and required repeated manual diagnosis because the runbooks were not dependency-based, not gate-based, and did not clearly state where several critical restore materials lived.

This must be fixed before the restore process can be considered production-grade.

---

## Executive Summary

The restore did eventually prove that the Europe role can be rebuilt, but not cleanly.

The biggest issue was not that one thing failed. The issue was that the restore docs allowed the process to continue without proving the previous layers were actually working.

Examples:

```text
Docker running was treated as progress before SSH trust was validated.
wg-site active was treated as progress before mesh handshakes worked.
Backend /docs returning 200 was treated as progress before DB schema/data was verified.
OAuth login working was almost treated as success even though the app data was missing.
wg-easy container running was almost treated as success before client routing worked.
```

That is not disaster recovery. That is “poke things until they look alive.”

The documentation needs to be rewritten into a strict phased runbook with validation gates.

Each phase must include:

```text
Purpose
Commands
Expected output
Stop conditions
What must not be touched
Rollback/backup step
Approval gate before destructive action
```

---

# Correct Restore Order That Documentation Must Enforce

The restore must happen in this order. The current docs did not enforce this order clearly enough.

## Correct high-level sequence

```text
1. Confirm restore role and whether original server is offline or still active.
2. Bootstrap fresh VPS.
3. Create administrator user and sudo access.
4. Install required tools.
5. Enable temporary passwordless sudo for Codex only.
6. Place docs, backups, and keys in standard restore paths.
7. Verify age identity key.
8. Decrypt secrets into staging only.
9. Restore SSH keys and validate key-based SSH to US/UK.
10. Use SSH trust to copy backups from US/UK.
11. Verify backup manifests/checksums.
12. Extract archives.
13. Fix archive path mapping into /opt/apps.
14. Restore Caddy config and install Caddy.
15. Restore systemd unit files into /etc/systemd/system.
16. Restore helper scripts under /usr/local/sbin.
17. Restore site-to-site WireGuard.
18. Update US/UK peer endpoints if restore IP changed.
19. Validate mesh handshakes, ping, and SSH.
20. Restore wg-easy user VPN state/config.
21. Validate real VPN client access.
22. Start Hermes services.
23. Start Family Hero Hub containers.
24. Validate Postgres schema.
25. Restore Postgres data from the correct Europe data source.
26. Validate OAuth.
27. Validate UI data.
28. Validate dashboards/internal tools.
29. Configure firewall/UFW.
30. Re-enable backup timers only after all restore validation passes.
31. Remove temporary passwordless sudo.
32. Archive/clean staging folders.
```

Any doc update must follow this order. Randomly restoring services before SSH/VPN/DB gates are proven is how this became a five-hour clown show.

---

# 1. Fresh VPS Bootstrap Was Incomplete

## What happened

The fresh VPS started clean, but the runbook did not fully cover everything needed to prepare it.

Missing/unclear items included:

```text
/opt/apps directory creation
restore-materials folder creation
administrator user setup
Docker install/verification
Codex install prerequisites
Node version requirements
Caddy install
WireGuard tools install
sqlite3 install
age/rclone/unzip/rsync/jq install
```

## Required standard restore paths

Docs must define and create:

```bash
sudo mkdir -p /opt/apps/restore-materials/docs
sudo mkdir -p /opt/apps/restore-materials/backups
sudo mkdir -p /opt/apps/restore-materials/keys
sudo mkdir -p /opt/apps/restore-test
```

Expected:

```text
/opt/apps/restore-materials/docs/
/opt/apps/restore-materials/backups/
/opt/apps/restore-materials/keys/
/opt/apps/restore-test/
```

## Codex install issue

Fresh Ubuntu did not have `node` or `npm`.

Codex required:

```bash
sudo apt-get update
sudo apt-get install -y nodejs npm
sudo npm i -g @openai/codex
codex --version
```

But for the restored server, Node 18 from Ubuntu was later too old for Hermes workspace, so the docs should standardize on **Node 22** during bootstrap.

## Node 22 requirement

Hermes workspace failed on Node 18 with Vite errors:

```text
Vite requires Node.js version 20.19+ or 22.12+
ReferenceError: File is not defined
```

Docs must install Node 22, not Ubuntu’s default Node 18:

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
sudo apt-get install -y nodejs

node --version
npm --version
```

## Temporary passwordless sudo issue

Codex could not continue root-required restore steps because it could not handle interactive sudo reliably.

Docs must add a temporary restore-only sudo step:

```bash
sudo tee /etc/sudoers.d/99-fhh-restore-administrator >/dev/null <<'EOSUDO'
administrator ALL=(ALL) NOPASSWD:ALL
EOSUDO

sudo chmod 440 /etc/sudoers.d/99-fhh-restore-administrator
sudo visudo -cf /etc/sudoers.d/99-fhh-restore-administrator
sudo -n whoami
```

Expected:

```text
/etc/sudoers.d/99-fhh-restore-administrator: parsed OK
root
```

Docs must also include the cleanup step:

```bash
sudo rm -f /etc/sudoers.d/99-fhh-restore-administrator
sudo visudo -c
sudo -n whoami || echo "Passwordless sudo removed"
```

This must be clearly labelled:

```text
Temporary for restore only.
Must be removed after validation.
```

---

# 2. SSH Key Trust Was Not Treated as an Early Gate

This was one of the biggest process failures.

## What happened

The restore needed to pull/inspect backups from US and UK. But SSH key trust was not validated early.

Codex hit authentication failures and continued other checks instead of fixing the key path.

That is wrong.

If US/UK are backup sources, key-based SSH must be validated before:

```text
copying backups
checking remote backup inventories
checking old secrets archives
repairing WireGuard endpoints
inspecting US/UK configs
```

## Required early SSH trust gate

After secrets are staged/restored, docs must restore and validate:

```text
/home/administrator/.ssh/europe-to-us-backups
/home/administrator/.ssh/europe-to-uk-backups
/home/administrator/.ssh/known_hosts
```

Fix permissions:

```bash
chmod 700 /home/administrator/.ssh
chmod 600 /home/administrator/.ssh/europe-to-us-backups
chmod 600 /home/administrator/.ssh/europe-to-uk-backups
chmod 600 /home/administrator/.ssh/known_hosts 2>/dev/null || true
chown -R administrator:administrator /home/administrator/.ssh
```

Verify private keys are readable without printing them:

```bash
ssh-keygen -y -f /home/administrator/.ssh/europe-to-us-backups >/tmp/europe-to-us-backups.pub.check && echo "US key readable"
ssh-keygen -y -f /home/administrator/.ssh/europe-to-uk-backups >/tmp/europe-to-uk-backups.pub.check && echo "UK key readable"
```

## SSH config must be created

The keys worked only when explicitly specified. Plain SSH still asked for a password until we created SSH config entries.

Docs must create:

```bash
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

Host 10.250.50.2
    User administrator
    IdentityFile /home/administrator/.ssh/europe-to-us-backups
    IdentitiesOnly yes

Host 10.250.50.3
    User administrator
    IdentityFile /home/administrator/.ssh/europe-to-uk-backups
    IdentitiesOnly yes

Host <current-us-public-ip>
    User administrator
    IdentityFile /home/administrator/.ssh/europe-to-us-backups
    IdentitiesOnly yes

Host <current-uk-public-ip>
    User administrator
    IdentityFile /home/administrator/.ssh/europe-to-uk-backups
    IdentitiesOnly yes
EOSSH

chmod 600 /home/administrator/.ssh/config
chown administrator:administrator /home/administrator/.ssh/config
```

Validate:

```bash
ssh -o BatchMode=yes us-mesh 'hostname; echo US_MESH_ALIAS_OK'
ssh -o BatchMode=yes uk-mesh 'hostname; echo UK_MESH_ALIAS_OK'
ssh -o BatchMode=yes administrator@10.250.50.2 'hostname; echo US_RAW_MESH_KEY_OK'
ssh -o BatchMode=yes administrator@10.250.50.3 'hostname; echo UK_RAW_MESH_KEY_OK'
```

Docs must state:

```text
Password prompt = key trust not complete.
Do not proceed with backup restore until key SSH works.
Do not rely on default SSH identity discovery.
```

---

# 3. Backup Source Locations Were Not Clear Enough

The docs did not clearly map backup types to locations.

This wasted a lot of time.

## Required backup source map

Docs must have a table like this:

| Backup type | Expected source | Expected path/pattern |
|---|---|---|
| Europe app archive | US mirror / UK backup hub | `/opt/apps/backups/from-europe/europe-app-family-hero-hub-*.tar.gz` |
| Europe Hermes app | US mirror / UK backup hub | `/opt/apps/backups/from-europe/europe-app-hermes-*.tar.gz` |
| Europe internal tools | US mirror / UK backup hub | `/opt/apps/backups/from-europe/europe-app-internal-tools-*.tar.gz` |
| Europe Hermes home | US mirror / UK backup hub | `/opt/apps/backups/from-europe/europe-home-hermes-*.tar.gz` |
| Europe sys configs | US mirror / UK backup hub | `/opt/apps/backups/from-europe/europe-sys-configs-*.tar.gz` |
| Europe secrets | US mirror / UK backup hub | `/opt/apps/backups/from-europe/europe-secrets-*.tar.gz.age` |
| Manifest | same backup folder | `manifest-*.txt` |
| Europe SQLite DB source | restored app archive | `/opt/apps/family-hero-hub/data/family_hero_hub.sqlite` |
| US production Postgres | US pgBackRest repo | `us-pgbackrest-repo-*.tar.gz` |
| wg-easy older state | older Europe secrets archive | `europe-secrets-20260520-010000.tar.gz.age` |

## Required backup verification

For the Europe archive set used in this test:

```text
20260520-054833
```

Required files:

```text
europe-app-family-hero-hub-20260520-054833.tar.gz
europe-app-hermes-20260520-054833.tar.gz
europe-app-internal-tools-20260520-054833.tar.gz
europe-home-hermes-20260520-054833.tar.gz
europe-sys-configs-20260520-054833.tar.gz
europe-secrets-20260520-054833.tar.gz.age
manifest-20260520-054833.txt
```

Verify:

```bash
cd /opt/apps/restore-materials/backups
sha256sum -c manifest-20260520-054833.txt
```

Docs must say:

```text
Do not extract or restore until manifest verification passes.
```

---

# 4. App Archives Extracted to the Wrong Paths

## What happened

Archives extracted into top-level paths:

```text
/family-hero-hub
/hermes-agent
/hermes-workspace
/fhh-ops-dashboard
```

But the docs and services expected:

```text
/opt/apps/family-hero-hub
/opt/apps/hermes-agent
/opt/apps/hermes-workspace
/opt/apps/fhh-ops-dashboard
```

This broke secrets restore because the target paths did not exist.

## Required fix

Either fix archive generation to include `/opt/apps/...`, or document the remap:

```bash
sudo mkdir -p /opt/apps/family-hero-hub /opt/apps/hermes-agent /opt/apps/hermes-workspace /opt/apps/fhh-ops-dashboard

sudo rsync -aHAX --delete /family-hero-hub/ /opt/apps/family-hero-hub/
sudo rsync -aHAX --delete /hermes-agent/ /opt/apps/hermes-agent/
sudo rsync -aHAX --delete /hermes-workspace/ /opt/apps/hermes-workspace/
sudo rsync -aHAX --delete /fhh-ops-dashboard/ /opt/apps/fhh-ops-dashboard/
```

Docs must state:

```text
Do not delete the top-level extracted directories until final validation is complete.
```

---

# 5. Caddy Restore Was Incomplete

## Issue 1: Caddyfile restored to the wrong place

Caddyfile was found at:

```text
/caddy-configs/caddy/Caddyfile
```

Expected:

```text
/etc/caddy/Caddyfile
```

Required:

```bash
sudo mkdir -p /etc/caddy
sudo install -o root -g root -m 644 /caddy-configs/caddy/Caddyfile /etc/caddy/Caddyfile
```

## Issue 2: Caddy was not installed

Fresh VPS did not have the `caddy` command.

Required:

```bash
sudo apt-get update
sudo apt-get install -y caddy
```

If apt hits config prompt:

```bash
sudo DEBIAN_FRONTEND=noninteractive apt-get \
  -o Dpkg::Options::='--force-confold' \
  -o Dpkg::Options::='--force-confdef' \
  -y -f install
```

Validate:

```bash
caddy version
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

---

# 6. Systemd Units Were Restored to the Wrong Place

## What happened

Systemd files were restored under:

```text
/systemd-units/
```

But systemd needs them in:

```text
/etc/systemd/system/
```

## Required restore step

Docs must install:

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

Docs must not assume extracted unit files are already active.

---

# 7. Required Helper Scripts Were Missing From Backups

This is a serious backup coverage failure.

## Missing helper: `hermes-dashboard-vpn-allow.sh`

Service expected:

```text
/usr/local/sbin/hermes-dashboard-vpn-allow.sh
```

But it was not in:

```text
restored filesystem
sys-config archive
secrets archive
```

Result:

```text
hermes-dashboard-vpn-allow failed with status=203/EXEC
```

Docs/backups must either:

```text
1. Back up /usr/local/sbin/hermes-dashboard-vpn-allow.sh
2. Remove this service from the required restore path
3. Document how to recreate it safely
```

During the test, it was safe to defer because Hermes dashboard was bound only to:

```text
10.250.50.1:9119
```

and Caddy did not expose it publicly.

But that must be explicit in docs.

## Missing helper: `wg-personal-to-site-nat.sh`

Service expected:

```text
/usr/local/sbin/wg-personal-to-site-nat.sh
```

It was missing.

Working Europe version reconstructed from US/UK pattern:

```sh
#!/bin/sh
iptables -t nat -C POSTROUTING -s 10.60.0.0/24 -o wg-site -j MASQUERADE 2>/dev/null || \
iptables -t nat -A POSTROUTING -s 10.60.0.0/24 -o wg-site -j MASQUERADE
```

## Missing helper: `wg-site-mesh-forward.sh`

Service expected:

```text
/usr/local/sbin/wg-site-mesh-forward.sh
```

No US/UK reference existed.

Conservative Europe script used:

```sh
#!/bin/sh
sysctl -w net.ipv4.ip_forward=1 >/dev/null
iptables -C FORWARD -i wg-site -j ACCEPT 2>/dev/null || iptables -A FORWARD -i wg-site -j ACCEPT
iptables -C FORWARD -o wg-site -j ACCEPT 2>/dev/null || iptables -A FORWARD -o wg-site -j ACCEPT
```

## Backup script fix required

Backups must include:

```text
/usr/local/sbin/hermes-dashboard-vpn-allow.sh
/usr/local/sbin/wg-personal-to-site-nat.sh
/usr/local/sbin/wg-site-mesh-forward.sh
```

---

# 8. Site-to-Site WireGuard Validation Was Wrong

## What happened

`wg-quick@wg-site` was active on the restore VPS, but the mesh was not working.

Initial state:

```text
wg-site active locally
10.250.50.1/24 present
route 10.250.50.0/24 present
US ping failed
UK ping failed
US/UK SSH over mesh failed
```

Docs/Codex initially treated “active service” as progress. That is not enough.

## Required validation gate

Docs must require:

```bash
sudo wg show wg-site
ping -c 3 10.250.50.2
ping -c 3 10.250.50.3
ssh -o BatchMode=yes us-mesh 'hostname; echo US_MESH_OK'
ssh -o BatchMode=yes uk-mesh 'hostname; echo UK_MESH_OK'
```

Expected:

```text
recent handshakes
0% packet loss
US_MESH_OK
UK_MESH_OK
```

## Endpoint drift issue

US/UK still pointed to the old Europe endpoint during restore.

During this historical test, US/UK needed to point to the then-current restore VPS:

```text
95.111.243.235:51830
```

At the end of this historical test, they had to be reverted to the then-current original Europe server:

```text
213.199.61.244:51830
```

Docs must include:

```text
When Europe is restored to a new public IP, surviving US/UK peers must update their Europe peer endpoint.
```

## Very important test cleanup lesson

Because the original Europe server and restore server had the same restored WireGuard identity, US/UK peers could “roam” to whichever endpoint last sent traffic.

Docs must include this warning:

```text
Never run the original Europe server and restore Europe server on the same WireGuard identity at the same time unless intentionally testing endpoint failover.

If both are online with the same wg-site private key, US/UK peers may roam between endpoints and show the wrong live endpoint even if the config file is correct.
```

End-of-test cleanup must include:

```text
1. Stop wg-site on restore VPS.
2. Stop wg-easy on restore VPS.
3. Repoint US/UK Europe peer endpoint back to original Europe public IP.
4. Restart wg-site on US/UK.
5. Confirm no US/UK peer shows restore VPS endpoint.
```

Commands on restore VPS:

```bash
sudo systemctl stop wg-quick@wg-site
sudo systemctl disable wg-quick@wg-site

cd /opt/apps/wg-easy
docker compose down || true
```

Commands on US/UK to revert:

```bash
sudo cp /etc/wireguard/wg-site.conf /etc/wireguard/wg-site.conf.bak-return-to-real-europe-$(date +%Y%m%d-%H%M%S)
RESTORE_PUBLIC_IP=<restore-vps-ip-used-for-this-drill>
ORIGINAL_EUROPE_PUBLIC_IP=<current-original-europe-public-ip>
sudo sed -i -E "s#Endpoint = ${RESTORE_PUBLIC_IP}:51830#Endpoint = ${ORIGINAL_EUROPE_PUBLIC_IP}:51830#g" /etc/wireguard/wg-site.conf
sudo wg-quick strip wg-site >/dev/null
sudo systemctl restart wg-quick@wg-site
sudo wg show
```

---

# 9. wg-easy/User VPN Restore Was Incomplete

This was a huge restore gap.

## Expected architecture

Docs must clearly define two separate VPN layers:

```text
Site-to-site mesh:
10.250.50.0/24
Europe: 10.250.50.1
US: 10.250.50.2
UK: 10.250.50.3
UDP port: 51830

Personal/mobile VPN:
10.60.0.0/24
wg-easy UDP: 51820
wg-easy admin: http://10.250.50.1:51821
```

## Missing from latest backup

Latest Europe secrets did not contain full wg-easy restore material.

Missing:

```text
/opt/apps/wg-easy/.env
/opt/apps/wg-easy/docker-compose.yml
```

Latest restore had empty:

```text
/opt/apps/wg-easy/etc_wireguard/
```

## Older archive contained partial wg-easy state

Older encrypted secrets archive:

```text
europe-secrets-20260520-010000.tar.gz.age
```

contained:

```text
/opt/apps/wg-easy/etc_wireguard/wg0.conf
/opt/apps/wg-easy/etc_wireguard/wg0.json
```

Docs must state:

```text
If latest secrets archive lacks wg-easy state, inspect older encrypted Europe secrets archives.
```

## Correct wg-easy compose

Must use bind mount:

```yaml
services:
  wg-easy:
    image: ghcr.io/wg-easy/wg-easy:14
    container_name: wg-easy-europe
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    env_file:
      - .env
    volumes:
      - ./etc_wireguard:/etc/wireguard
      - /lib/modules:/lib/modules:ro
    ports:
      - "51820:51820/udp"
      - "10.250.50.1:51821:51821/tcp"
    sysctls:
      net.ipv4.ip_forward: "1"
      net.ipv4.conf.all.src_valid_mark: "1"
```

Must not use named volume:

```yaml
volumes:
  - etc_wireguard:/etc/wireguard
```

because it ignores recovered:

```text
/opt/apps/wg-easy/etc_wireguard/wg0.conf
/opt/apps/wg-easy/etc_wireguard/wg0.json
```

## Correct `.env`

Final working pattern:

```env
WG_HOST=dev.familyherohub.com
WG_PORT=51820
PORT=51821
WG_DEFAULT_DNS=1.1.1.1
WG_ALLOWED_IPS=10.250.50.0/24
WG_DEFAULT_ADDRESS=10.60.0.x
LANG=en
PASSWORD_HASH=<generated-hash>
```

## Critical issue: WG_DEFAULT_ADDRESS

Without:

```env
WG_DEFAULT_ADDRESS=10.60.0.x
```

wg-easy v14 defaulted runtime NAT to:

```text
10.8.0.0/24
```

even though restored clients were:

```text
10.60.0.x
```

This caused:

```text
client handshake works
client profile looks right
but client cannot reach 10.250.50.1
```

Docs must explicitly check:

```bash
sudo docker exec wg-easy-europe sh -lc 'iptables -t nat -S | grep -E "10.8|10.60|MASQUERADE"'
```

Expected:

```text
10.60.0.0/24
```

Not:

```text
10.8.0.0/24
```

## Password hash generation

`wgpw` did not prompt when run without argument.

Working safe method:

```bash
cd /opt/apps/wg-easy

read -rsp "Enter new wg-easy admin password: " WGPW
echo
docker run --rm ghcr.io/wg-easy/wg-easy:14 wgpw "$WGPW"
unset WGPW
```

Docs must say not to print or paste the plain password.

## Client validation

Real client profile must show:

```text
Address = 10.60.0.x/24
Endpoint = dev.familyherohub.com:51820
AllowedIPs = 10.250.50.0/24
```

Then from actual laptop/phone:

```text
ping 10.250.50.1
open http://10.250.50.1:51821
open http://10.250.50.1:9119
open http://10.250.50.1:3000
ssh administrator@10.250.50.1
```

The restore is not complete until an actual VPN client can reach private services.

---

# 10. Hermes Workspace Restore Issues

## Node version issue

Hermes workspace failed because Node 18 was too old.

Required:

```text
Node 22
```

Docs must run:

```bash
cd /opt/apps/hermes-workspace
rm -rf node_modules
npm install
sudo systemctl restart hermes-workspace
```

after Node 22 is installed.

## Public exposure issue

Hermes workspace initially listened on:

```text
0.0.0.0:3000
```

That is wrong.

Expected:

```text
10.250.50.1:3000
```

Patch service:

```bash
sudo cp /etc/systemd/system/hermes-workspace.service /etc/systemd/system/hermes-workspace.service.bak

sudo perl -0pi -e 's|ExecStart=/usr/bin/npm run dev|ExecStart=/usr/bin/npm run dev -- --host 10.250.50.1|' /etc/systemd/system/hermes-workspace.service

sudo systemctl daemon-reload
sudo systemctl restart hermes-workspace
sudo ss -ltnup | grep 3000
```

Expected:

```text
10.250.50.1:3000
```

Not:

```text
0.0.0.0:3000
```

Docs must explicitly include exposure validation.

---

# 11. Database Schema Was Not Checked

This was a critical restore failure.

## What happened

Postgres container was running and healthy, but the database had no tables.

OAuth crashed with:

```text
psycopg.errors.UndefinedTable: relation "approved_parent_emails" does not exist
```

The database had:

```text
no alembic_version
no approved_parent_emails
no app tables
```

## Required schema gate

Immediately after containers start:

```bash
cd /opt/apps/family-hero-hub

docker compose exec -T postgres psql -U familyhero -d family_hero_hub_dev -c '\dt'
docker compose exec -T postgres psql -U familyhero -d family_hero_hub_dev -c 'select * from alembic_version;'
```

If missing:

```bash
docker compose exec -T backend alembic upgrade head
```

In this test, Codex had to run Alembic from a one-off container with the repo root mounted. The exact working method must be captured if normal container execution is unreliable.

Critical tables to verify:

```text
approved_parent_emails
parent_users
families
children
ledger_transactions
redemption_requests
rewards
calendar_entries
school_items
```

Docs must say:

```text
Postgres healthy does not mean schema exists.
Backend /docs working does not mean DB is usable.
OAuth route existing does not mean login works.
```

---

# 12. Database Data Was Not Restored

This was probably the biggest app-level failure.

## What happened

After migrations, login worked, but the app had no data.

Postgres counts were only:

```text
parent_users: 1
families: 1
children: 0
ledger_transactions: 0
rewards: 0
approved_parent_emails: 0
```

That was only bootstrap residue from the OAuth login.

The actual Europe dev data was not in Postgres.

## Correct Europe dev data source

Found:

```text
/opt/apps/family-hero-hub/data/family_hero_hub.sqlite
```

SQLite counts:

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

This was the actual Europe dev data source.

Docs must explicitly state:

```text
For Europe dev, if no Europe pgBackRest repo exists, restore data from:
/opt/apps/family-hero-hub/data/family_hero_hub.sqlite
```

Tool:

```text
backend/scripts/migrate_sqlite_to_postgres.py
```

## Required import flow

Do not stop Postgres.

Stop only backend/frontend.

```bash
cd /opt/apps/family-hero-hub

mkdir -p /opt/apps/restore-materials/db-before-sqlite-import

docker compose exec -T postgres pg_dump \
  -U familyhero \
  -d family_hero_hub_dev \
  > /opt/apps/restore-materials/db-before-sqlite-import/family_hero_hub_dev_before_sqlite_import_$(date +%Y%m%d_%H%M%S).sql

docker compose exec -T backend python backend/scripts/migrate_sqlite_to_postgres.py \
  --dry-run \
  --source-path /opt/apps/family-hero-hub/data/family_hero_hub.sqlite

docker compose stop backend frontend

docker compose run --rm backend python backend/scripts/migrate_sqlite_to_postgres.py \
  --import \
  --yes-i-understand-this-writes-postgres \
  --clear-target \
  --source-path /opt/apps/family-hero-hub/data/family_hero_hub.sqlite

docker compose up -d backend frontend
```

Verify row counts:

```bash
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

Expected:

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

Docs must state:

```text
Login working with empty family data is not a successful restore.
```

---

# 13. US pgBackRest Repo Was Almost Used Incorrectly

Very important.

We found:

```text
us-pgbackrest-repo-20260520-034722.tar.gz
```

Codex initially proposed using it for Europe dev.

That would have been wrong unless explicitly seeding dev from US production.

## Required warning

Docs must say:

```text
Do not restore us-pgbackrest-repo-* into Europe dev unless intentionally seeding Europe dev with US production data.
```

Before any pgBackRest restore, prove:

```text
backup origin
environment
database name
stanza
timestamp
intended target
```

Docs must distinguish:

```text
US production pgBackRest repo
Europe dev SQLite source
future Europe dev pgBackRest repo if implemented
```

---

# 14. OAuth Had Multiple Layers

## DNS

`dev.familyherohub.com` was pointed to the restore server.

Docs must state that DNS movement is a separate manual/provider action.

## Google OAuth redirect

Correct redirect URI:

```text
https://dev.familyherohub.com/api/auth/google/callback
```

This must be added in Google Cloud Console.

## Caddy allowlist blocked OAuth

Caddy returned 403 until the admin/browser IP was allowed.

Caddy matcher needed:

```text
45.155.44.72
```

There was a dangerous typo-risk with:

```text
45.145.44.72
```

Docs must explicitly verify current admin public IP before allowlisting.

## OAuth failure after callback

OAuth initially reached backend but crashed because DB schema was missing.

After schema and data were restored, OAuth login worked and app data appeared.

Docs must make the OAuth validation chain explicit:

```text
1. DNS points to correct server.
2. Caddy allows browser source IP.
3. Google Console has correct callback URI.
4. Backend route exists.
5. DB schema exists.
6. approved_parent_emails exists.
7. DB data exists.
8. Login shows restored family data.
```

---

# 15. Firewall/UFW Was Not Completed

This restore test stopped before final firewall hardening.

But docs must include it.

During restore:

```text
UFW inactive
```

Public listeners seen:

```text
22/tcp
80/tcp
443/tcp
51820/udp
51830/udp
```

Private listeners:

```text
10.250.50.1:9119 Hermes dashboard
10.250.50.1:3000 Hermes workspace
10.250.50.1:51821 wg-easy admin
127.0.0.1:8000 backend
127.0.0.1:5173 frontend
```

Docs must not enable UFW until after:

```text
SSH key trust works
site mesh works
user VPN works
current admin IP is allowed
Caddy is validated
wg-easy ports are confirmed
```

---

# 16. Ops Dashboard/Internal Tools Were Not Restored/Validated

The test stopped before starting/validating:

```text
fhh-ops-dashboard
internal viewers/tools
docs viewer/editor
competitor review viewer
ports 8765/8766/8767/8768
```

Docs must include a separate phase:

```bash
sudo ss -ltnup | grep -E '8765|8766|8767|8768'
systemctl list-units --all | grep -Ei 'fhh|ops|viewer|docs|competitor'
find /opt/apps/fhh-ops-dashboard -maxdepth 3 -type f
```

Expected: internal tools must bind to VPN/private IPs only, not public internet.

---

# 17. Telegram/Hermes Messaging Was Not Validated

Hermes gateway ran, but logs showed:

```text
no messaging platforms enabled
no user allowlists configured
missing Hermes APIs for full feature set
```

Docs must include:

```text
verify Telegram config exists without printing token
verify allowlist exists
send real Telegram command
verify gateway logs receive and process it
```

Commands:

```bash
systemctl status hermes-gateway --no-pager
journalctl -u hermes-gateway -n 100 --no-pager
```

Do not print tokens.

---

# 18. Backup Timers Were Not Re-enabled

Backup timers were intentionally not enabled during test.

Docs must state:

```text
Do not enable backup timers until:
- original server is confirmed offline or restore is active
- DB data is restored
- VPN is restored
- SSH trust works
- UFW is configured
- service validation passes
- no duplicate backup streams are running
```

Validation:

```bash
systemctl list-timers --all | grep -Ei 'backup|pgbackrest|fhh|hermes'
systemctl list-unit-files | grep -Ei 'backup|pgbackrest|fhh|hermes'
```

---

# 19. Cleanup Was Not Completed

Staging directories intentionally remained.

Docs must include cleanup only after validation and docs update:

```text
/tmp/recovery
/tmp/secrets_recovery
/tmp/wg_easy_secret_checks
/tmp/wg_easy_restore_20260520_010000
/family-hero-hub
/hermes-agent
/hermes-workspace
/fhh-ops-dashboard
/caddy-configs
/systemd-units
```

Do not delete until final archive/review.

---

# 20. End-of-Test Reversion Was Needed

Because this was a test, extra cleanup was needed:

```text
Stop restore VPS wg-site.
Stop restore VPS wg-easy.
Point US/UK back to original Europe endpoint.
Point DNS back to original Europe if needed.
```

Historical original Europe endpoint from the May 2026 test only:

```text
213.199.61.244:51830
```

Historical restore endpoint used during the May 2026 test only:

```text
95.111.243.235:51830
```

Docs must include a **restore test teardown section**.

---

# Full Final Validation Checklist That Must Be Added

A restore is not complete until all pass.

## Server identity

```bash
hostname
hostnamectl
ip -br addr
curl -4 ifconfig.me
```

## SSH trust

```bash
ssh -o BatchMode=yes us-mesh 'hostname'
ssh -o BatchMode=yes uk-mesh 'hostname'
ssh -o BatchMode=yes administrator@10.250.50.2 'hostname'
ssh -o BatchMode=yes administrator@10.250.50.3 'hostname'
```

## Site mesh

```bash
sudo wg show wg-site
ping -c 3 10.250.50.2
ping -c 3 10.250.50.3
```

## User VPN

From real client:

```text
Address = 10.60.0.x/24
Endpoint = dev.familyherohub.com:51820
AllowedIPs = 10.250.50.0/24
```

Test:

```text
ping 10.250.50.1
http://10.250.50.1:51821
http://10.250.50.1:9119
http://10.250.50.1:3000
ssh administrator@10.250.50.1
```

## wg-easy

```bash
cd /opt/apps/wg-easy
docker compose ps
sudo ss -ltnup | grep -E '51820|51821'
sudo docker exec wg-easy-europe sh -lc 'wg show; iptables -t nat -S | grep -E "10.60|MASQUERADE"'
```

## Hermes

```bash
systemctl status hermes-gateway hermes-dashboard hermes-workspace --no-pager
curl -I http://10.250.50.1:9119
curl -I http://10.250.50.1:3000
```

## FHH app

```bash
cd /opt/apps/family-hero-hub
docker compose ps
curl -I http://127.0.0.1:8000/docs
curl -I http://127.0.0.1:5173
curl -I https://dev.familyherohub.com
```

## DB schema/data

```bash
docker compose exec -T postgres psql -U familyhero -d family_hero_hub_dev -c 'select * from alembic_version;'

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

Expected Europe dev counts from test:

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

## OAuth

```text
Google Cloud Console URI:
https://dev.familyherohub.com/api/auth/google/callback
```

Browser test:

```text
https://dev.familyherohub.com/api/auth/google/login
```

Success means:

```text
Login works
Parent dashboard loads
Children/family data appears
```

## Firewall

```bash
sudo ufw status verbose
sudo ss -ltnup
```

## Backup timers

```bash
systemctl list-timers --all | grep -Ei 'backup|pgbackrest|fhh|hermes'
```

Only enable after approval.

---

# Backup Script Fixes Required

Backups must include these items because they were missing or incomplete:

```text
/opt/apps/wg-easy/docker-compose.yml
/opt/apps/wg-easy/.env
/opt/apps/wg-easy/etc_wireguard/
/usr/local/sbin/hermes-dashboard-vpn-allow.sh
/usr/local/sbin/wg-personal-to-site-nat.sh
/usr/local/sbin/wg-site-mesh-forward.sh
/etc/caddy/Caddyfile
/etc/systemd/system/*.service
/opt/apps/family-hero-hub/data/family_hero_hub.sqlite
/home/administrator/.ssh/europe-to-us-backups
/home/administrator/.ssh/europe-to-uk-backups
/home/administrator/.ssh/known_hosts
```

Also preserve reports:

```text
wg-easy-summary.txt
wg-service-status.txt
wg-show.txt
wireguard-summary.txt
wireguard-endpoint-restore-notes.txt
docker-compose-files.txt
systemd-enabled-services.txt
firewall-status.txt
ssh-backup-trust-map.txt
```

But reports are not enough. The actual files must be backed up too. Reports saying a file exists are useless if the backup doesn’t contain the file.

---

# Europe Remediated Backup Proof

Final Europe remediated backup proof recorded on 2026-05-20:

```text
/opt/apps/backups/local/europe-home-hermes-20260520-160643.tar.gz
/opt/apps/backups/local/europe-secrets-20260520-160643.tar.gz.age
/opt/apps/backups/local/europe-sys-configs-20260520-160643.tar.gz
```

Verified:

```text
europe-home-hermes-20260520-160643.tar.gz has no obvious Hermes secret filenames matching auth.json, .env, token, secret, or key.
europe-secrets-20260520-160643.tar.gz.age exists.
europe-sys-configs-20260520-160643.tar.gz contains:
- app-configs/wg-easy/docker-compose.yml
- helper-scripts/wg-personal-to-site-nat.sh
- helper-scripts/wg-site-mesh-forward.sh
- helper-scripts/hermes-dashboard-vpn-allow.sh
```

The earlier restore-test backup gaps remain useful as lessons, but the Europe backup-side proof for the Hermes plaintext archive and restore-critical sys-config members is remediated at timestamp `20260520-160643`.

---

# Final Clear Statement for the Backup Chat

Use this as the blunt conclusion:

```text
The Europe restore test proved that the infrastructure can be recovered, but the current docs/backups are not yet disaster-recovery quality.

The runbook allowed services to be started before core dependencies were validated. It did not clearly identify all backup sources. It did not validate SSH trust early. It did not handle WireGuard endpoint drift early. It did not restore wg-easy completely. It did not restore helper scripts. It did not validate database schema or restore database data until very late. It nearly allowed a US production pgBackRest repo to be considered for Europe dev. It allowed OAuth testing before DB readiness. It did not complete firewall, ops dashboard, Telegram, backup timer, or cleanup validation.

The docs must be rewritten into a strict phase/gate runbook with exact commands, expected outputs, stop conditions, backup locations, and recovery paths for missing files.
```

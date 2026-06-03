# Current Deployment: Family Hero Hub

## Current Production Setup

Family Hero Hub currently uses **Caddy** for public web access.

Cloudflare Tunnel is **not** the current production deployment method. The Cloudflare Tunnel document is retained only as a future/optional reference.

## US Production

- Environment: current production
- Public app: `https://familyherohub.com`
- Mail: `https://mail.familyherohub.com`
- Public IP: `204.12.209.190`
- Host role: production source of truth
- Stack: Ubuntu server, Docker Compose, Caddy, PostgreSQL, FastAPI backend, SvelteKit frontend
- Production database: PostgreSQL is now the live US production runtime database
- Verified cutover backup: `/opt/backups/family-hero-hub/prod-cutover-20260513-083225`
- Freeze-time backup: `/opt/backups/family-hero-hub/prod-cutover-20260513-083225/family_hero_hub_freeze.sqlite`
- Production rollback backup: the original SQLite backup remains available inside the verified cutover backup set
- Production pgBackRest status: initialized and healthy on US, with first full backup `20260513-094837F` completed successfully and WAL archiving working
- Off-server pgBackRest mirror: `/opt/backups/family-hero-hub/pgbackrest/us-prod/` contains a checksum-verified tar mirror of the US repo
- Production cutover branch: `prod/postgres-cutover-20260513` was the narrow Europe-prepared branch based on production `main` at `258289c0f0283c764af76dbfe0bbbffaecfa77b1`; it has now been cut over on US production and is the current production release branch
- PostgreSQL is Docker Compose internal only; no public `5432` port is exposed
- Cutover coordination did not change Mailcow, DNS, or Caddy
- pgBackRest/WAL archive warnings from the initial cutover are resolved; the next follow-up is backup-policy hardening, restore-testing cadence, and off-server mirror retention policy
- Mail: remains on the US server only
- Hermes: removed from active US runtime and archived at `/opt/apps/hermes-removed-from-us/`
- Notes: US is pull/deploy only; normal feature work should happen on Europe/France first

## Europe/France Dev + Hermes

- Environment: development/testing
- Hostname: `vmi3285205`
- Public IP: `213.199.61.244`
- Location: Contabo, Lauterbourg, France
- Domain: `https://dev.familyherohub.com`
- PTR/rDNS: `213.199.61.244` -> `dev.familyherohub.com`
- Stack: Ubuntu 24.04.4 LTS, Docker, Docker Compose, Node/npm, SQLite, FastAPI backend, SvelteKit frontend
- Runtime database: PostgreSQL is now the live Europe dev app DB via Docker Compose
- Expired child-device link exchange now returns a clean 401/"Child link expired" response on Europe PostgreSQL instead of an internal server error
- Europe dev/Hermes daily QA uses `/opt/apps/family-hero-hub/scripts/qa/europe-dev-qa.sh` in read-only daily mode; it runs backend pytest, frontend build, Playwright read-only E2E, and smoke checks.
- The daily QA harness loads `/home/administrator/.hermes/fhh-qa.env`.
- `POST /api/dev/qa-login` is the token-based dev QA login helper. It requires `QA_LOGIN_TOKEN`, must not log the token, and must stay blocked in production and on production/public domains.
- Stateful QA stays separate and must remain backup-gated before restoration or use.
- SQLite rollback copy remains available at `/opt/apps/family-hero-hub/tmp/runtime-db-switch/sqlite_before_postgres_switch_20260509_164727.sqlite`
- Europe dev PostgreSQL backups now use pgBackRest with WAL archiving; a first full backup and a separate restore rehearsal both completed successfully
- Internal PostgreSQL 16 runs in Docker Compose with no public port exposed and now serves the live Europe dev runtime
- Alembic: baseline schema migration was applied before import, and the database now contains imported dev data
- ETL tool: `backend/scripts/migrate_sqlite_to_postgres.py` exists for controlled SQLite-to-PostgreSQL migration work; dry-run validation passed and the Europe dev SQLite data has now been imported into PostgreSQL
- Tooling: Codex CLI at `/usr/bin/codex` version `0.128.0`; Gemini CLI at `/usr/bin/gemini` version `0.41.2`
- Repo: `/opt/apps/family-hero-hub`
- Git remote: `git@github.com:itsdominoman/family-hero-hub.git`
- Branch: `main`
- Caddy routing: `/api/*` to `127.0.0.1:8000`, everything else to `127.0.0.1:5173`
- Docker container ports: `family-hero-hub-backend` bound to `127.0.0.1:8000`, `family-hero-hub-frontend` bound to `127.0.0.1:5173`
- Hermes app path: `/opt/apps/hermes-agent`
- Hermes home: `/home/administrator/.hermes`
- Hermes services: `hermes-gateway.service`, `hermes-dashboard.service`, `hermes-dashboard-vpn-allow.service`
- Hermes dashboard: `http://10.250.50.1:9119`
- Hermes status: active on Europe/France; Telegram Zeus gateway verified through live `gateway.log`
- Mail: remains on the US server only
- DNS: `dev.familyherohub.com` resolves to `213.199.61.244`
- Notes: only `dev.familyherohub.com` points to the Europe VPS

## UK Infrastructure Node

- Hostnames/IPs: `uk.familyherohub.com` -> `87.106.54.49`, `qa.familyherohub.com` -> `217.154.52.123` (reserved/future UK secondary IP; not currently in use)
- Role: infrastructure and private VPN node, not production app hosting
- Status: old playground/OpenVPN/OpenClaw/n8n/SearXNG/Caddy/Tailscale use has been cleaned up
- VPN: participates in the private WireGuard mesh and runs a UK personal `wg-easy` VPN

## Private WireGuard Mesh

- Canonical topology: [INFRASTRUCTURE_MAP.md](operations/INFRASTRUCTURE_MAP.md)
- Site mesh subnet: `10.250.50.0/24`
- Europe hub: `10.250.50.1`
- US spoke: `10.250.50.2`
- UK spoke: `10.250.50.3`
- Singapore spoke: `10.250.50.4`
- Restore node: `10.250.50.5`
- Europe wg-easy clients: `10.60.0.0/24`
- Home brain: routed through Europe wg-easy as `10.60.0.7` with `10.11.0.0/24` behind it
- US wg-easy clients: `10.8.0.0/24`
- UK wg-easy clients: `10.70.0.0/24`
- Singapore wg-easy clients: `10.10.0.0/24`
- Status: spoke-to-spoke traffic routes through Europe as the hub; home is routed through the Europe wg-easy path rather than being a direct site-mesh peer
- Verification: trusted mesh nodes can reach each other and the restore node, and the routed home peer is reachable through the Europe wg-easy path
- Note: `10.50.0.0/24` was abandoned because it conflicted with office/local routing; `10.80.0.0/24` is not active

## Private Admin URLs

- Europe `wg-easy`: `http://10.250.50.1:51821`
- US `wg-easy`: `http://10.250.50.2:51821`
- UK `wg-easy`: `http://10.250.50.3:51821`
- Hermes dashboard: `http://10.250.50.1:9119`
- Competitor review viewer: `http://10.250.50.1:8765`
- Docs viewer/editor: `http://10.250.50.1:8766`
- These URLs are mesh/VPN only and must not be exposed publicly

## Access and Security Notes

- `dev.familyherohub.com` is restricted at the Caddy layer with `remote_ip` allowlisting
- Trusted access includes `96.9.135.3` (home public), `45.155.44.72` (work public), `204.12.209.190` (US), `213.199.61.244` (Europe), `87.106.54.49` (UK), `194.233.71.132` (Singapore), `95.111.243.235` (restore), and trusted WireGuard/VPN paths
- Off-VPN or untrusted clients receive HTTP 403 on dev
- OAuth still works from trusted IPs or VPN because the browser can reach `dev.familyherohub.com`
- SQLite is no longer the live runtime on Europe dev, but the backup remains for rollback
- The current PostgreSQL database contains imported dev app data and now serves the Europe dev runtime
- Failed QA runs must not show stale PASS reports; the current report directory must reflect the latest run.
- The pgBackRest repo lives in a private named Docker volume and is not publicly exposed
- Do not assume Cloudflare Tunnel is active just because the file exists elsewhere in docs
- Europe personal VPN runs through Docker `wg-easy`; the host may see container or bridge source addresses for that traffic.
- Private routing and firewall access on reboot are restored by `/usr/local/sbin/fhh-private-network-rules.sh` and `fhh-private-network-rules.service`.
- That private rules service preserves return routing for `10.60.0.0/24` and the routed home subnet `10.11.0.0/24`, plus private service access and site-mesh forwarding.
- SSH password authentication is disabled across the managed hosts described here; key-only SSH is the expected state.
- Public break-glass SSH is allowlisted only from trusted public IPs and VPN ranges.

## App Location

`/opt/apps/family-hero-hub`

## Server User

`administrator`

## Stack

- Frontend: SvelteKit
- Backend: FastAPI
- Database: PostgreSQL for the live Europe dev runtime, with SQLite rollback backup retained locally
- Runtime/deployment: Docker Compose
- Public access / reverse proxy: Caddy

## Deployment Command

`sudo /usr/local/bin/family-hero-deploy`

## Recent Production Fixes

- Child reward requests now recover CSRF automatically for existing linked child devices when `/api/child/me` is loaded and the `csrf_token` cookie is missing.
- Child dashboards show a clearer relink message for expired or invalid child sessions.
- Reward POSTs remain CSRF-protected; `/api/child/redemptions` was not exempted.

## Deployment Rules

- Inspect first, edit second.
- Show diffs before deploy.
- Deploy only after approval.
- Commit only after deployed/visual approval.
- Push only after explicit approval.

## Notes

Before changing deployment, inspect the real Caddy/server configuration first.

## PostgreSQL Cutover Preparation

- Branch `prod/postgres-cutover-20260513` contains the minimum PostgreSQL cutover code path prepared from the Europe validation work.
- Included scope: PostgreSQL Docker service, pgBackRest-capable image/config, Alembic baseline, SQLite-to-PostgreSQL ETL script, PostgreSQL-safe runtime initialization, enum compatibility, and the child-session timezone fix observed during Europe PostgreSQL validation.
- Excluded scope: dev-only QA login, Playwright browser QA tooling, customer FAQ/manual frontend changes, scheduled reporting wrappers, Telegram/Email reporting scripts, and Europe-to-UK backup sync automation.
- Production remains on SQLite until an approved backup, rehearsal, deploy, migration, verification, and rollback window is executed.
- PostgreSQL must stay private to Docker networking or localhost/private paths only; do not publish `5432` publicly.
- Production cutover branches may exclude dev-only QA tooling, but Europe dev/Hermes operations must retain the Europe dev QA harness.

## Access Management Notes

- `PARENT_EMAILS` is the bootstrap/root admin allowlist only.
- Do not use `PARENT_EMAILS` as a growing parent-user registry.
- Normal parent access should be managed through registration approval, family invites, and `/admin/users`.
- Bootstrap admins cannot be revoked through the admin UI/API.
- Suspending a family blocks parent and child access without deleting family, child, rewards, points, calendar, or history data.

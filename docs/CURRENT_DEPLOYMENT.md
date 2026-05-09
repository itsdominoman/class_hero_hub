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
- Stack: Ubuntu server, Docker Compose, Caddy, SQLite, FastAPI backend, SvelteKit frontend
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

- Hostnames/IPs: `uk.familyherohub.com` -> `87.106.54.49`, `qa.familyherohub.com` -> `217.154.52.123`
- Role: infrastructure and private VPN node, not production app hosting
- Status: old playground/OpenVPN/OpenClaw/n8n/SearXNG/Caddy/Tailscale use has been cleaned up
- VPN: participates in the private WireGuard mesh and runs a UK personal `wg-easy` VPN

## Private WireGuard Mesh

- Site mesh subnet: `10.250.50.0/24`
- Europe hub: `10.250.50.1`
- US spoke: `10.250.50.2`
- UK spoke: `10.250.50.3`
- Future office spoke: `10.250.50.10`
- Status: spoke-to-spoke traffic routes through Europe as the hub
- Verification: all three servers can reach each other and all `wg-easy` admin panels over the mesh
- Note: `10.50.0.0/24` was abandoned because it conflicted with office/local routing

## Private Admin URLs

- Europe `wg-easy`: `http://10.250.50.1:51821`
- US `wg-easy`: `http://10.250.50.2:51821`
- UK `wg-easy`: `http://10.250.50.3:51821`
- Hermes dashboard: `http://10.250.50.1:9119`
- These URLs are mesh/VPN only and must not be exposed publicly

## Access and Security Notes

- `dev.familyherohub.com` is restricted at the Caddy layer with `remote_ip` allowlisting
- Trusted access includes `96.9.135.3` (office/current admin), `45.155.44.72` (work/trusted admin), `204.12.209.190` (US), `213.199.61.244` (Europe), `87.106.54.49` (UK primary), `217.154.52.123` (UK secondary), and trusted WireGuard/VPN paths
- Off-VPN or untrusted clients receive HTTP 403 on dev
- OAuth still works from trusted IPs or VPN because the browser can reach `dev.familyherohub.com`
- SQLite is still in use; PostgreSQL remains planned/future only
- Do not assume Cloudflare Tunnel is active just because the file exists elsewhere in docs

## App Location

`/opt/apps/family-hero-hub`

## Server User

`administrator`

## Stack

- Frontend: SvelteKit
- Backend: FastAPI
- Database: SQLite
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

## Access Management Notes

- `PARENT_EMAILS` is the bootstrap/root admin allowlist only.
- Do not use `PARENT_EMAILS` as a growing parent-user registry.
- Normal parent access should be managed through registration approval, family invites, and `/admin/users`.
- Bootstrap admins cannot be revoked through the admin UI/API.
- Suspending a family blocks parent and child access without deleting family, child, rewards, points, calendar, or history data.

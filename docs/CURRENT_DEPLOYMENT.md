# Current Deployment: Family Hero Hub

## Current Production Setup

Family Hero Hub currently uses **Caddy** for public web access.

Cloudflare Tunnel is **not** the current production deployment method. The Cloudflare Tunnel document is retained only as a future/optional reference.

## US Production

- Environment: current production
- Domains: `https://familyherohub.com` and `https://mail.familyherohub.com`
- Hostname/IP: existing US production server; hostname/IP unchanged from the previous deployment record
- Stack: Ubuntu server, Docker Compose, Caddy, SQLite, FastAPI backend, SvelteKit frontend
- Mail: remains on the US server only
- Notes: this is the production source of truth; normal work should happen elsewhere and then be promoted through GitHub

## Europe Dev

- Environment: development/testing
- Hostname: `vmi3285205`
- Public IP: `213.199.61.244`
- Domain: `https://dev.familyherohub.com`
- Stack: Ubuntu 24.04.4 LTS, Docker, Docker Compose, Node/npm, SQLite, FastAPI backend, SvelteKit frontend
- Tooling: Codex CLI at `/usr/bin/codex` version `0.128.0`; Gemini CLI at `/usr/bin/gemini` version `0.41.2`
- Repo: `/opt/apps/family-hero-hub`
- Git remote: `git@github.com:itsdominoman/family-hero-hub.git`
- Branch: `main`
- Caddy routing: `/api/*` to `127.0.0.1:8000`, everything else to `127.0.0.1:5173`
- Docker container ports: `family-hero-hub-backend` bound to `127.0.0.1:8000`, `family-hero-hub-frontend` bound to `127.0.0.1:5173`
- Mail: remains on the US server only
- Notes: only `dev.familyherohub.com` points to the Europe VPS

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
- Do not assume Cloudflare Tunnel is active just because `docs/CLOUDFLARE_TUNNEL.md` exists.

## Notes

Before changing deployment, inspect the real Caddy/server configuration first.

## Access Management Notes

- `PARENT_EMAILS` is the bootstrap/root admin allowlist only.
- Do not use `PARENT_EMAILS` as a growing parent-user registry.
- Normal parent access should be managed through registration approval, family invites, and `/admin/users`.
- Bootstrap admins cannot be revoked through the admin UI/API.
- Suspending a family blocks parent and child access without deleting family, child, rewards, points, calendar, or history data.

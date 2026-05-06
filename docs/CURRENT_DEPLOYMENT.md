# Current Deployment: Family Hero Hub

## Current Production Setup

Family Hero Hub currently uses **Caddy** for public web access.

Cloudflare Tunnel is **not** the current production deployment method. The Cloudflare Tunnel document is retained only as a future/optional reference.

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

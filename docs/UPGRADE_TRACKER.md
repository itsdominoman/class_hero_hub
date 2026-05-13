# Family Hero Hub - Upgrade Tracker

# 2026-05-13 - Narrow Production PostgreSQL Cutover Branch Prepared

### Scope
- Created local Europe branch `prod/postgres-cutover-20260513` from production `main` at `258289c0f0283c764af76dbfe0bbbffaecfa77b1`.
- Included only the PostgreSQL cutover path: Docker Compose PostgreSQL service, pgBackRest-capable PostgreSQL image/config, Alembic baseline, PostgreSQL runtime safety changes, enum compatibility, SQLite-to-PostgreSQL ETL tooling, and the child-session timezone fix needed for PostgreSQL datetime behavior.
- Hardened production defaults so the example PostgreSQL database name is `family_hero_hub`, the password remains a placeholder, and the ETL script requires `--confirm-production-cutover` for the production database.

### Verification
- This branch is prepared on Europe only and is not deployed to US production.
- Production remains SQLite until an approved backup, rehearsal, cutover, verification, and rollback window is run.
- PostgreSQL remains internal-only in Compose: no public `5432` port mapping is defined.

### Exclusions
- Dev-only QA login code was excluded.
- Playwright/browser QA tooling was excluded.
- Customer FAQ/manual frontend changes were excluded.
- Scheduled reporting wrappers, Telegram notifications, Email reporting, and Europe-to-UK backup sync/retention automation were excluded.

### Notes
- Do not push, deploy, or run US production migrations without explicit approval.
- Next gate is a rehearsal using a production SQLite backup imported into a temporary PostgreSQL database.

# 2026-05-09 - Europe PostgreSQL Backup System

### Scope
- Added pgBackRest to the Europe dev PostgreSQL image and enabled WAL archiving on the live runtime.
- Created the first full backup for the live Europe PostgreSQL database.
- Restored that backup into a separate restore volume/container and verified the restored database row counts matched the live database.

### Verification
- `pgbackrest --stanza=fhh stanza-create` completed successfully.
- `pgbackrest --stanza=fhh --type=full backup` completed successfully.
- `pgbackrest --stanza=fhh check` completed successfully after the backup existed.
- WAL archiving is active and archive segments are being written to the private repo volume.
- Restore rehearsal completed successfully into the separate `postgres_restore` volume/service.
- Restored PostgreSQL reported `pg_is_in_recovery() = false` and `transaction_read_only = off`.

### Notes
- The pgBackRest repository lives in a private Docker named volume and is not publicly exposed.
- Production PostgreSQL still needs its own pgBackRest/WAL backup and tested restore plan before any cutover.

# 2026-05-09 - Europe PostgreSQL Runtime Smoke Fix

### Scope
- Fixed the Europe PostgreSQL child-device link exchange path so expired links now return a clean 401 instead of an internal server error.
- Kept the live Europe dev runtime on PostgreSQL and preserved the SQLite rollback copy.

### Verification
- Live smoke test against `http://127.0.0.1:8000/api/child-link/exchange` returned HTTP 401 with `{"detail":"Child link expired"}` for an expired invite.
- Backend tests passed again after the timezone-aware child-link fix.
- Frontend production build passed again after the backend fix.

### Notes
- The child rewardable-task completion question remains a separate product/UX follow-up if that flow is intentionally parent-only.
- Production PostgreSQL backup design still needs pgBackRest with WAL archiving and a tested restore flow, not `pg_dump` alone.

# 2026-05-09 - Europe PostgreSQL Migration Preparation

### Scope
- Added a PostgreSQL 16 service to the Europe dev Docker Compose stack for migration testing only.
- Added Alembic and generated, then applied, an initial schema migration against the empty Europe PostgreSQL database.
- Kept the live Europe app runtime on SQLite while the migration path is prepared.

### Verification
- PostgreSQL is internal-only and has no public port exposed.
- Alembic schema exists in PostgreSQL, and the Europe dev SQLite data has been imported successfully.
- Controlled ETL dry-run validation passed from `backend/scripts/migrate_sqlite_to_postgres.py`; source/target tables and columns aligned, and the target remained unmodified.
- The actual import completed with matching source/target row counts and no orphan rows in the key relationship checks.
- Europe dev runtime `DATABASE_URL` has been switched from SQLite to PostgreSQL.
- A rollback copy of the SQLite database and the pre-switch `.env` snapshot were saved under `tmp/runtime-db-switch/`.
- Backend tests passed after isolating test settings from real Compose and `.env` values.
- Frontend build passed.

### Notes
- Keep the SQLite rollback copy available until the PostgreSQL runtime is considered stable.
- Production PostgreSQL backup design must use pgBackRest with WAL archiving and a tested restore flow, not `pg_dump` alone.
- Remaining cleanup items include the SQLAlchemy FK cycle/drop_all warnings around `families`/`parent_users` and Pydantic/SQLAlchemy deprecation warnings.

# 2026-05-09 - Internal Hermes Review Tooling and Private Access Hardening

### Scope
- Ran a read-only seven-agent review with Zeus, Athena, Hercules, Hermes, Apollo, Aphrodite, and Ares using situational model selection for orchestration, review, and summarization.
- Created and used internal/private review workspaces under `/opt/apps/family-hero-hub/tmp/competitor-review/` and `/opt/apps/family-hero-hub/tmp/docs-viewer/`.
- Added private dashboard access for the competitor review viewer at `http://10.250.50.1:8765` and the docs viewer/editor at `http://10.250.50.1:8766`.
- Persisted Europe private routing/firewall access with `fhh-private-network-rules.service` and `/usr/local/sbin/fhh-private-network-rules.sh`.
- Confirmed the Europe wg-easy Docker/NAT return-route behavior for private VPN traffic and documented it as an operational note.

### Verification
- Internal dashboards remained private/VPN-only and were not wired into the production frontend.
- `tmp/` is ignored by git and no tracked files were added under `tmp/`.
- No production app, runtime, deployment, database, or secret files were changed.
- No SQLite-to-PostgreSQL data import was performed.
- Hermes dashboard and private mesh access were verified over the Europe VPN path.

### Notes
- The review found Family Hero Hub to be a promising startup with clear strengths, but still short of a polished commercial app.
- Main follow-up areas remain mobile hero layout, trust/privacy messaging, onboarding clarity, child engagement polish, and conversion hierarchy.

# 2026-05-09 - Europe Hermes Migration, WireGuard Renumbering, and Dev Lockdown

### Scope
- Renumbered the site WireGuard mesh to `10.250.50.0/24` after `10.50.0.0/24` was abandoned because it conflicted with office/local routing.
- Moved Hermes from the US production runtime to the Europe/France VPS and kept the US archive at `/opt/apps/hermes-removed-from-us/`.
- Restricted `dev.familyherohub.com` at the Caddy layer so only trusted IPs and VPN paths can reach the dev app.

### Verification
- Site mesh connectivity was confirmed between Europe (`10.250.50.1`), US (`10.250.50.2`), and UK (`10.250.50.3`).
- All three servers could reach the private `wg-easy` admin panels at `http://10.250.50.1:51821`, `http://10.250.50.2:51821`, and `http://10.250.50.3:51821`.
- The Europe Hermes gateway and dashboard services were active, and the dashboard was reachable at `http://10.250.50.1:9119`.
- Telegram Zeus traffic was confirmed on the Europe Hermes host through live `gateway.log` entries.
- Off-VPN access to `dev.familyherohub.com` returned HTTP 403, while trusted IP/VPN access worked and OAuth still completed through the allowed path.

### Notes
- The UK server now remains an infrastructure/VPN node rather than app hosting.
- The office box uses `wg-quick` with a split tunnel that routes only `10.250.50.0/24` through the Europe VPN.
- PostgreSQL migration work now includes Alembic/schema preparation, but the runtime still stays on SQLite until ETL and validation are complete.
- PostgreSQL, mail migration, and any future SSH tightening remain separate follow-up items.

# 2026-05-07 - Europe Dev VPS Baseline Setup

### Scope
- Set up a new Europe-based development/testing VPS for Family Hero Hub at `dev.familyherohub.com`.
- Verified the stack on Ubuntu 24.04.4 LTS with Docker, Docker Compose, Node/npm, Codex CLI, and Gemini CLI installed and working.
- Cloned the repo to `/opt/apps/family-hero-hub` on branch `main` and kept production DNS and mail on the US server.
- Left PostgreSQL, mail migration, and production cutover work for later.

### Verification
- `https://dev.familyherohub.com` returned HTTP/2 200.
- `https://dev.familyherohub.com/api/health` returned `{"status":"ok"}`.
- External verification from another Ubuntu host confirmed `curl -I https://dev.familyherohub.com` returned HTTP/2 200 and `curl -sS https://dev.familyherohub.com/api/health` returned `{"status":"ok"}`.
- Backend and frontend containers were running.
- Google OAuth login/callback worked on dev.
- Parent dashboard loaded on dev.
- Admin registration requests page loaded on dev.
- Git status was clean.
- Baseline backup created: `/opt/apps/family-hero-hub-europe-dev-baseline-20260507_201438.tar.gz`.

### Notes
- Only `dev.familyherohub.com` points to the Europe VPS.
- Forward and reverse DNS are aligned for `dev.familyherohub.com` and `213.199.61.244`.
- Mail remains US-only.
- The Europe server is prepared for future Hermes use, but Hermes itself is not installed yet.

# 2026-05-07 - Child Reward Request CSRF Recovery

### Scope
- Restored reward-request flow for existing linked child devices that still have a valid `child_session` but were missing `csrf_token`.
- `GET /api/child/me` now mints `csrf_token` for authenticated child sessions when the cookie is missing, preserving the existing CSRF protection model.
- Added clearer child-device relink messaging for expired or invalid child sessions.

### Verification
- Backend HTTP tests added for missing CSRF failure, CSRF recovery via `/api/child/me`, successful redemption after recovery, invalid CSRF rejection, unauthenticated `/api/child/me`, and expired/invalid child-session rejection.
- Backend tests passed.
- Frontend production build passed.
- Live visual testing confirmed the child can request a reward, the parent sees the pending request, held points behave as expected, and approval/rejection still finalize or release points.
- Expired child-link UX is covered by backend tests and frontend build verification; it was not manually forced in production because that would require mutating production session data.

### Notes
- CSRF remains enforced for reward POSTs; `/api/child/redemptions` was not exempted.
- This is a recovery fix for existing linked devices, not a redesign of child-device management.

## 2026-05-06 - Mobile UI Consistency Pass

### Scope
- Repaired mobile consistency across parent dashboard, child dashboard, rewards/redemptions, login, request access, child-link, family-invite, calendar modal shells, and shared app layout.
- Added global browser/WebView safeguards for `100dvh`, safe-area insets, horizontal overflow, tap target minimums, and mobile form input sizing.
- Standardized phone spacing, wrapping, shrink behavior, and modal scrolling without changing product direction or adding features.

### Viewports Considered / Tested
- Phone widths: 320, 360, 375, 390, 412, 430 px.
- Tablet/desktop sanity widths: 768 and 1365 px.
- Browser viewport sweep used Chromium mobile emulation with mocked API data for dashboard, child detail, rewards, calendar, and modal states.

### Verification
- `npm install` completed.
- `npm run build` passed.
- Browser viewport sweep passed with no horizontal page scrolling or non-decorative element overflow.
- Backend tests were skipped because no backend files were changed.

### Remaining Mobile Risks
- Real Android Chrome and iPhone Safari device checks are still recommended before Capacitor/app-store packaging.
- Future mobile app work should preserve the new dynamic viewport and safe-area behavior.

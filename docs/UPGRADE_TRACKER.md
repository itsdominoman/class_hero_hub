# Family Hero Hub - Upgrade Tracker

# 2026-05-18 - Visual Layout Improvements (Child Custom Request & Parent Dashboard)

### Scope
- Improved child custom request form: added "1 point = X" conversion text and "Value: X" calculated total.
- Fixed child custom request form alignment: fields and buttons now align cleanly on both mobile and desktop.
- Fixed parent dashboard child-card layout: shortened action buttons to "Dashboard" and "Points" to prevent overlap and bleeding.
- Standardized button heights to `h-14` for consistent cross-card alignment on the parent dashboard.
- Ensured "0 pending" remains visible on parent child cards.

### Verification
- Updated `frontend/e2e/visual-layout.spec.ts` with strengthened assertions for:
  - Custom request conversion text visibility.
  - Custom request readable value text.
  - Field and button alignment for the request form.
  - Shorter button labels and cross-card alignment for parent dashboard.
- Verified all 31 visual layout tests pass across 320px to 1024px viewports.
- Verified full daily QA suite passes.

### Notes
- "Dashboard" and "Points" labels provide a much safer layout margin for mobile and small tablets compared to the previous long labels.

# 2026-05-18 - Authenticated Header Fix (HttpOnly compatibility)

### Scope
- Removed `document.cookie.includes('access_token=')` prechecks from `+layout.svelte`, `+page.svelte`, and `login/+page.svelte`.
- Transitioned frontend to rely exclusively on `/api/me` for authentication state hydration.
- Fixed header regression where "Login" was shown instead of "Parent Dashboard" due to `access_token` being `HttpOnly`.
- Improved Playwright `extractCookies` helper in `e2e/qa-support.ts` to preserve `HttpOnly` attributes during test session setup.

### Verification
- Added `frontend/e2e/header-regression.spec.ts` (reproduction case).
- Expanded `frontend/e2e/authenticated-qa-login.spec.ts` with header visibility assertions for anonymous, parent, and admin states.
- Rebuilt frontend Docker container and verified tests pass with `access_token` correctly hidden from `document.cookie`.
- Verified Admin link remains restricted to `is_admin: true` users.

### Notes
- The frontend no longer attempts to "guess" auth status via `document.cookie` for the main access token.

# 2026-05-18 - QA Coverage Expansion for Mobile Layout Regressions

### Scope
- Added a route inventory helper at `scripts/qa/list-sveltekit-routes.mjs`.
- Added a QA coverage matrix at `docs/QA_COVERAGE_MATRIX.md` to track public, parent, child, admin, and tokenized routes.
- Expanded public Playwright coverage to include `/faq` and to verify safe internal links.
- Added `frontend/e2e/visual-layout.spec.ts` with mobile-width screenshot capture and DOM-level overflow/crushed-text checks.
- Added a dev-only seeded child QA login helper and a real child visual test path.
- Added screenshot artifact output under `tmp/qa-runs/YYYYMMDD-HHMMSS-visual-layout/`.

### Verification
- The visual coverage is intentionally read-only.
- The child dashboard is exercised through a deterministic QA seed, not a parent-preview fallback.
- The Europe dev daily QA wrapper passes on the standard `8000/5173` dev services after rebuilding the dev containers.
- The child reward cards and waiting-request cards now use mobile-safe stacking on narrow widths, and the generic layout heuristic no longer flags form labels as false positives.
- The child custom request form uses block-level alignment checks on desktop/tablet widths, and the parent child-card alignment check is enforced at `1024px`.

### Notes
- The new coverage is designed to catch obvious layout explosions such as one-letter vertical wrapping, cramped reward cards, and horizontal overflow without relying on brittle pixel diffs.

# 2026-05-18 - Allowance-Linked Points Model

### Scope
- Converted allowance from a parent-only preview into allowance-linked points with child-facing read-only display when allowance is enabled.
- Added `allowance_enabled_at` as audit/history metadata for when allowance was enabled.
- Kept starting balance deferred for beta.
- Kept the app points-only when allowance is disabled.

### Verification
- Backend allowance summary now derives allowance value from the child’s current relevant point balance using integer minor units.
- Child-facing allowance summary route returns points/value breakdowns only when allowance is enabled.
- Parent dashboard and allowance setup page now surface allowance-linked summaries.
- Frontend child dashboard now shows points first and money equivalent second when allowance is enabled.

### Notes
- The app still does not automatically pay children.
- Saved points/value remain visually separate from available-to-spend balance.

# 2026-05-17 - Europe Dev Daily QA Phase A Restored

### Scope
- Restored the read-only Europe dev `/qa-daily` harness so it runs backend pytest, frontend build, Playwright read-only E2E, and smoke checks.
- Restored token-based dev QA login at `POST /api/dev/qa-login` and kept it blocked in production and on production/public domains.
- Kept stateful QA and reporting/notification wrappers out of scope.

### Verification
- Daily QA uses `/home/administrator/.hermes/fhh-qa.env`.
- The daily run completed with backend pytest PASS, frontend build PASS, Playwright read-only E2E PASS, and smoke PASS.
- Example report directory from the 2026-05-17 run was `/opt/apps/family-hero-hub/tmp/qa-runs/20260517-091715-daily`.

### Notes
- Failed QA runs must not display stale PASS reports.
- Production cutover branches may omit dev-only QA tooling, but Europe dev/Hermes operations must retain the Europe dev QA harness.

# 2026-05-17 - Parent Allowance Setup UI

### Scope
- Added the parent-facing Allowance setup page at `/allowance`.
- Added a Parent Tools link from the parent dashboard to Allowance setup.
- Parents can select a child, enable or disable allowance, choose OMR/USD/GBP/EUR, enter a human-readable allowance amount, choose weekly/monthly period, set a point goal, save settings, and view current-period preview.
- Kept rewards, redemptions, child dashboard display, and automatic payout behavior unchanged.

### Verification
- Frontend uses the existing authenticated API helper for `/api/allowance` settings and preview endpoints.
- Amount entry is converted to backend minor units before saving.
- Preview remains based on backend period ledger aggregation, not current point balances.

### Notes
- Child-facing allowance progress display remains a follow-up.
- The app still does not automatically pay children; allowance is an estimate for parents.

# 2026-05-17 - Backend Child Allowance Settings API

### Scope
- Added backend support for optional child-level allowance settings in `child_allowance_settings`.
- Added parent-authenticated allowance settings and preview endpoints under `/api/allowance`.
- Stored allowance amounts in integer minor units and derived the currency exponent from supported currencies: OMR, USD, GBP, and EUR.
- Kept rewards independent from allowance; no reward behavior, frontend allowance UI, child dashboard display, or automatic payouts were implemented.

### Verification
- Allowance preview uses current period ledger aggregation rather than current point balances.
- Eligible allowance points include awards, calendar task points, adjustments, and penalties.
- Reward holds/releases/approvals and savings transfers are excluded from allowance preview calculations.
- Backend allowance tests passed.
- Full backend test suite passed.

### Notes
- Parent and child-facing frontend allowance setup/display remains a follow-up.
- Applying the new Alembic migration is required before using these endpoints against a PostgreSQL runtime database.

# 2026-05-13 - US Production PostgreSQL Cutover Completed

### Scope
- Cut US production over from SQLite to PostgreSQL using the verified backup set at `/opt/backups/family-hero-hub/prod-cutover-20260513-083225`.
- Used the freeze-time rollback snapshot at `/opt/backups/family-hero-hub/prod-cutover-20260513-083225/family_hero_hub_freeze.sqlite` for the actual import.
- Kept PostgreSQL private to Docker Compose networking and did not expose `5432` publicly.
- Left Mailcow, DNS, and Caddy unchanged during the cutover.

### Verification
- Backend/frontend/postgres are running on US production.
- Local `/api/health` and public `https://familyherohub.com/api/health` returned `{"status":"ok"}`.
- Public homepage, login, and request-access pages returned HTTP 200.
- Backend `DATABASE_URL` is PostgreSQL.
- Freeze-time SQLite row counts and PostgreSQL row counts matched exactly.
- Manual production smoke testing passed for parent dashboard, children visibility, positive/negative points, reward request/approval, calendar, school prep/school bag, and admin users page.
- US pgBackRest is initialized and healthy, with first full backup `20260513-094837F` completed successfully and WAL archiving active.
- The Europe off-server pgBackRest mirror at `/opt/backups/family-hero-hub/pgbackrest/us-prod/` was checksum-verified.

### Notes
- The initial pgBackRest archive warnings about missing `archive.info` / `archive.info.copy` were resolved during backup hardening.
- The next follow-up is a recurring backup/mirror/restore-test policy and retention plan.
- Any new PostgreSQL writes after cutover are not represented in the old SQLite rollback backup.
- Do not treat the narrow production branch preparation as the live state anymore; production is now PostgreSQL-backed.

# 2026-05-13 - Narrow Production PostgreSQL Cutover Branch Prepared

### Scope
- Created local Europe branch `prod/postgres-cutover-20260513` from production `main` at `258289c0f0283c764af76dbfe0bbbffaecfa77b1`.
- Included only the PostgreSQL cutover path: Docker Compose PostgreSQL service, pgBackRest-capable PostgreSQL image/config, Alembic baseline, PostgreSQL runtime safety changes, enum compatibility, SQLite-to-PostgreSQL ETL tooling, and the child-session timezone fix needed for PostgreSQL datetime behavior.
- Hardened production defaults so the example PostgreSQL database name is `family_hero_hub`, the password remains a placeholder, and the ETL script requires `--confirm-production-cutover` for the production database.
- The approved production cutover branch was later deployed to US production and the live runtime is now PostgreSQL-backed.

### Verification
- This branch is prepared on Europe only and is not deployed to US production.
- Production remains SQLite until an approved backup, rehearsal, cutover, verification, and rollback window is run.
- PostgreSQL remains internal-only in Compose: no public `5432` port mapping is defined.
- The Europe off-server pgBackRest mirror exists at `/opt/backups/family-hero-hub/pgbackrest/us-prod/` and is checksum-verified.

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
- Live visual testing confirmed the child can request a reward, the parent sees the pending request, points on hold behave as expected, and approval/rejection still finalize or release points.
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

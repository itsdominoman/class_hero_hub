# Family Hero Hub – Current Status

## ✅ Completed Features

### Authentication & Access
- Google OAuth for parent accounts
- Parent sessions last 30 days by default through `ACCESS_TOKEN_EXPIRE_MINUTES`; JWT expiry, `HttpOnly` access cookie lifetime, and CSRF cookie lifetime are aligned
- Parent `last_login_at` tracking (updates on first-time and returning Google OAuth logins)
- Family-based data scoping
- Child device linking via QR code
- Parents can view linked child devices and unlink one specific child device without deleting child data
- Child-specific sessions (separate from parent auth)
- Secure token-based invite system (hashed, expiring, scoped)
- Admin registration approval flow
- Admin user-management page at `/admin/users`
- Admin user search, filtering, pagination, revoke, and restore
- Admin family suspension and restoration
- Bootstrap admin protection: `PARENT_EMAILS` is bootstrap/admin only, not a normal user registry
- Legacy bootstrap users migrated to database-approved access with `source=legacy_bootstrap_migration`
- Last-parent protection prevents revoking the only active parent in an active family
- Suspended families block parent and child access without deleting family data
- Revoked parents are hidden from normal parent-facing family member lists while remaining visible to admins

### Child System
- Child profiles linked to parent/family
- Child dashboard (kid-friendly UI)
- Dragon pet evolution visuals (displayed on homepage, parent dashboard, and child dashboard)
- Child-scoped API endpoints
- Device-based persistent sessions (no email required)

### Rewards System
- Parent-created rewards with custom point values
- Rewards displayed correctly to children
- Reward request flow implemented
- Pending reward requests visible to parents
- Existing child devices recover reward-request CSRF automatically when `/api/child/me` is loaded and the `csrf_token` cookie is missing
- Reward POSTs remain CSRF-protected; `/api/child/redemptions` is not exempted

### Family Calendar
- Parent-facing calendar page is implemented
- Parents can create, edit, and delete child calendar entries
- Supports normal events and task entries
- Supports rewardable tasks tied to the points system
- Supports simple recurrence:
  - none
  - daily
  - weekly
- Mobile calendar layout is responsive with no horizontal page scrolling
- Mobile Week Picker uses a compact `S M T W T F S` strip
- Child dashboard shows today's tasks and events through the My Day/calendar integration
- Authenticated header handles `HttpOnly` cookies correctly by using `/api/me` as the source of truth and shows correct Parent Dashboard / Admin / Logout behavior.

### School Bag / School Prep
- Dedicated `school_items` backend is implemented
- School items are stored separately from calendar events and tasks
- Parents can configure school books/classes per child and weekday
- School items do not appear in the normal calendar agenda or week view
- Child dashboard School Bag shows:
  - Pack for tomorrow
  - Needed today
  - Check stationery
- Parent dashboard School Prep shows today/tomorrow school items per child
- Today/tomorrow lookup uses the family's timezone

### Behaviour System
- Quick-tap behaviour presets (points/penalties)
- Separated from rewards (no longer mixed)
- Parent points modal supports Add points, Remove points, and Custom point actions
- Custom one-off point awards and penalties are available without creating a preset
- Adding and removing points provide short Web Audio feedback sounds
- Parent dashboard now opens a child action modal from each child avatar, with Points shown first, persistent Child Dashboard/Edit Child actions, and Requests, School Bag, Calendar, Savings, and Points Log available inside the same modal
- Edit Child supports display name changes and numeric avatar selection using avatar keys `1` through `24` resolved from `/avatars/{key}.png`
- Points Log includes Day / Week / Year filters and a behaviour ring chart that excludes savings, banking, redemptions, holds, and other system financial entries

### Allowance System
- Backend support exists for optional child-level allowance settings
- Parents can store allowance currency, amount, weekly/monthly period, point goal, and allowance enabled date per child through API endpoints
- Allowance values are derived from allowance-linked points using integer minor-unit math
- Rewards, reward holds, reward releases, and savings deposits/unlocks reduce the available balance when allowance is enabled
- Parent-facing Allowance setup page exists at `/allowance`
- Parents can select a child, enable/disable allowance, choose OMR/USD/GBP/EUR, set weekly/monthly allowance goals, save settings, and view allowance-linked summaries
- Child dashboard allowance display is now implemented for children with allowance enabled
- The app still does not automatically pay children
- Child dashboard savings banking is now implemented with a dedicated popup, savings bonus projection, next-unlock summary, and grouped unlock schedule

### UI / UX
- Responsive layout (tablet + mobile)
- Mobile UI consistency pass completed across common phone widths for parent dashboard, child dashboard, rewards, auth/linking pages, and calendar modals
- Global mobile viewport safeguards added for dynamic viewport height, safe-area insets, horizontal overflow, tap targets, and mobile form font sizing
- QR linking UI for child devices
- Reward cards fixed (no overflow issues)
- Improved contrast and readability
- Child-friendly dashboard experience
- Parent dashboard is now a minimalist `My Family` launcher with avatar buttons, point badges, and child names
- Tapping a child opens the child action modal instead of navigating directly to the child dashboard
- The modal keeps quick point actions first and preserves parent access to child dashboard, edit child, requests, school bag, calendar, savings, and points log sections
- Parent tools remain secondary under `Settings`
- Parent dashboard copy was reduced to remove duplicate headings and development-style explanatory filler

### Infrastructure
- Dockerized deployment
- Caddy reverse proxy with HTTPS
- Domain: https://familyherohub.com
- Europe dev VPS setup completed for development/testing at https://dev.familyherohub.com
- Europe dev/Hermes retains the read-only daily QA harness at `scripts/qa/europe-dev-qa.sh`; it runs backend pytest, frontend build, Playwright read-only E2E, and smoke checks, and it loads `/home/administrator/.hermes/fhh-qa.env`.
- Europe dev stack verified: Ubuntu 24.04.4 LTS, Docker, Docker Compose, Node/npm, Codex CLI, Gemini CLI
- Europe dev deployment verified with Caddy routing to local Docker ports; runtime DATABASE_URL has now been switched to PostgreSQL on Europe dev
- Internal PostgreSQL 16 service added to Europe dev via Docker Compose for migration testing only, with no public port exposed
- Alembic initial schema migration was applied to the empty Europe PostgreSQL database
- Controlled SQLite-to-PostgreSQL ETL tooling now exists at `backend/scripts/migrate_sqlite_to_postgres.py`; dry-run validation completed cleanly before import
- Europe PostgreSQL now contains imported app data from the copied SQLite DB, and row-count validation matched source counts
- SQLite backup remains available under `tmp/runtime-db-switch/` for rollback
- Europe dev runtime is now PostgreSQL-backed, but this remains a Europe-only change
- Europe dev PostgreSQL backup now uses pgBackRest with WAL archiving, and a separate restore rehearsal verified the backup can be restored cleanly
- A narrow production release branch, `prod/postgres-cutover-20260513`, has been prepared on Europe from production `main` at `258289c0f0283c764af76dbfe0bbbffaecfa77b1`; it is not deployed and does not mean production has moved to PostgreSQL.
- US production has now been cut over successfully to PostgreSQL using the verified backup set at `/opt/backups/family-hero-hub/prod-cutover-20260513-083225`
- The freeze-time rollback snapshot used for the cutover is `/opt/backups/family-hero-hub/prod-cutover-20260513-083225/family_hero_hub_freeze.sqlite`
- US PostgreSQL is Docker Compose internal only and was not publicly exposed during cutover
- US pgBackRest is initialized and healthy, with first full backup `20260513-094837F` completed successfully and WAL archiving active
- The Europe off-server pgBackRest mirror was created at `/opt/backups/family-hero-hub/pgbackrest/us-prod/` and checksum-verified
- The production cutover branch intentionally excludes dev-only QA login, browser QA tooling, customer FAQ/manual UI changes, scheduled notification/reporting scripts, and Europe-specific UK backup sync automation.
- DNS is aligned for dev: `dev.familyherohub.com` -> `213.199.61.244` and PTR `213.199.61.244` -> `dev.familyherohub.com`
- Mail remains on the US server only; production DNS records were not changed
- Dev access is locked down at Caddy with `remote_ip` allowlisting; off-VPN/untrusted clients receive HTTP 403
- WireGuard site mesh is live on `10.250.50.0/24` with Europe as hub, US/UK/Singapore as spokes, and the restore node at `10.250.50.5`
- Europe personal VPN is working on `10.60.0.0/24`
- UK personal VPN is working on `10.70.0.0/24`
- Hermes migrated to the Europe/France VPS and now runs there as the active Hermes host
- Hermes dashboard is available privately at `http://10.250.50.1:9119`
- Internal competitor review tooling is available privately at `http://10.250.50.1:8765`
- Internal docs viewer/editor is available privately at `http://10.250.50.1:8766`
- Europe private routing/firewall access is restored on reboot by `fhh-private-network-rules.service`
- US Hermes was removed from active runtime and archived at `/opt/apps/hermes-removed-from-us/`
- Ubuntu office box uses `wg-quick` with a split tunnel that routes only `10.250.50.0/24` through the Europe VPN
- Current trusted mesh topology and routed VPN ranges are documented in [INFRASTRUCTURE_MAP.md](operations/INFRASTRUCTURE_MAP.md)
- Site mesh now includes Europe `10.250.50.1`, US `10.250.50.2`, UK `10.250.50.3`, Singapore `10.250.50.4`, and the restore node `10.250.50.5`
- Europe wg-easy serves `10.60.0.0/24`; home brain is routed as `10.60.0.7` with `10.11.0.0/24` behind it
- US, UK, and Singapore wg-easy client ranges are `10.8.0.0/24`, `10.70.0.0/24`, and `10.10.0.0/24`
- SSH password authentication is disabled on the managed fleet; SSH is key-only and public break-glass access is limited to trusted public IPs and VPN ranges.
- The restore node is a DR receiving node at `95.111.243.235`, and the filtered UK replica is staged at `/srv/fhh-restore-inbox/uk/backups`.
- Backend tests passing (108 tests)
- Frontend production build passes
- Europe dev daily QA Phase A passes with backend pytest, frontend build, Playwright read-only E2E, and smoke checks
- Playwright coverage now includes `/faq`, route inventory, authenticated parent visual layout checks, and mobile screenshot artifacts for the most important parent/child surfaces
- Dev-only child QA login and seeded child visual coverage are now part of the Europe dev daily QA flow, and the full visual suite passes on the standard dev ports after rebuilding the dev containers
- The child visual suite now covers the real seeded child route, reward cards, custom request form, pending requests, tasks, events, savings snapshot, savings popup, unlock schedule, and points log, with a 1024px parent alignment check for child dashboard cards
- Europe PostgreSQL runtime smoke test now handles expired child-device links cleanly with HTTP 401 instead of a 500
- US production smoke tests and manual verification passed after the PostgreSQL cutover

---

## 🧪 Verified Working
- Child device linking (QR + link)
- Child session persistence
- Parent-managed child device list and single-device unlink
- Rewards creation → child visibility → request flow
- Child reward request CSRF recovery for existing linked devices
- Parent pending reward request card receives child requests
- Reward request hold/reserve behavior is enforced by the existing redemption hold ledger flow
- Reward rejection releases points on hold
- Reward approval finalizes points
- Parent dashboard + child dashboard interaction
- Multi-child support (e.g., Jackson, Leah)
- Parent dashboard launcher redesign visually approved after mobile review
- Parent dashboard launcher layout tested at 320, 360, 375, 390, 412, 430, 768, and desktop widths
- Parent Points modal positive/negative presets and custom one-off point awards/penalties
- Parent Tools access for rewards, allowance setup, pending reward requests, family settings, behaviour presets, calendar, add child, and child dashboard links
- Parent calendar event/task creation, editing, deletion, recurrence, and rewardable tasks
- Dev OAuth login and callback working at https://dev.familyherohub.com
- Dev health check verified at `https://dev.familyherohub.com/api/health` returning `{"status":"ok"}`
- External verification from another Ubuntu host confirmed `curl -I https://dev.familyherohub.com` returned HTTP/2 200 and `curl -sS https://dev.familyherohub.com/api/health` returned `{"status":"ok"}`
- Dev access on an untrusted client returns HTTP 403, while trusted IPs and VPN access work
- Parent dashboard loaded successfully on dev
- Admin registration requests page loaded successfully on dev
- Hermes gateway and dashboard are active on Europe, and the private dashboard is reachable over the mesh/VPN path
- Telegram Zeus gateway handling was confirmed by live `gateway.log` entries on the Europe Hermes host
- Trusted mesh nodes can reach the Europe, US, and UK `wg-easy` admin panels over the mesh; restore and home access are validated separately
- Mobile calendar layout visually tested and improved
- Mobile consistency viewport sweep completed against production frontend build at 320, 360, 375, 390, 412, 430, 768, and 1365 px widths using mocked app data; no horizontal page scrolling or non-decorative element overflow found
- Parent dashboard child cards, quick actions, School Prep cards, rewards UI, child detail/log sections, login/request access, child/family invite pages, and parent/calendar modals were included in the mobile consistency pass
- School Bag and School Prep today/tomorrow school item flows
- Admin registration request approval
- Admin users page search/filter/pagination
- Parent revoke/restore access controls
- Parent 30-day session duration with logout clearing both auth and CSRF cookies
- Family suspend/restore controls
- Revoked parent login/session blocking
- Suspended family parent and child blocking
- Bootstrap admin revoke protection

---

## ⚠️ Known Gaps / Not Yet Implemented

### Authentication Enhancements
- Parent refresh tokens/server-side session revocation are not implemented; parent logout clears browser cookies, so indefinite login is intentionally unsupported
- Longer-lived parent-managed child device sessions are a future improvement; current child links still expire and now show clearer relink messaging

### Rewards System
- Reward approval UX polish
- Reward history tracking
- Notifications for reward requests
- Clearer trust/privacy wording around parent approval and child safety
- Child-side completion of rewardable tasks is a separate follow-up/UX review if it remains intentionally unsupported

### Gamification
- Pet evolution visuals added; remaining work: animations, level-up feedback, image optimization, and deeper progression polish.
- Level progression feedback
- Animations / engagement elements
- Automatic weekly streak generation
- Polished streak and bonus UI
- More rewarding child-facing excitement and retention loops

### Productivity Features
- Dedicated child management route/shell for child-specific Points, Rewards, Calendar, School Bag, Profile, and device sections
- Component extraction/refactor for the large parent dashboard page
- Child-facing allowance progress display is now implemented for allowance-enabled children
- Full monthly calendar view
- Drag-and-drop calendar editing
- Notification/reminder system
- Warning cleanup / backend deprecation cleanup
- Optional future school timetable improvements
- Scheduled rewards / recurring behaviours
- Shared family goals / house rewards
- Avatar or character customization
- Backup and restore validation automation
- CI/test gate before deploy
- PostgreSQL migration planning and runtime schema strategy review
- Controlled ETL dry-run passed and the actual SQLite-to-PostgreSQL import completed successfully on Europe dev
- Runtime switch to PostgreSQL completed on Europe dev after import validation
- Next gate is continuing validation on PostgreSQL runtime and keeping the SQLite rollback copy available
- Failed QA runs must not reuse stale PASS reports; current daily runs should always point to the newest report directory
- Production backup strategy now needs a scheduled backup/mirror/restore-test policy and retention review, not just `pg_dump`
- Production still requires follow-up restoration drills and mirror retention hardening, even though the US cutover itself is complete.
- Real-device mobile QA on Android Chrome and iPhone Safari
- Onboarding simplification and clearer family-safe wording
- Warning cleanup remains pending for SQLAlchemy FK cycle/drop_all warnings around `families`/`parent_users` and Pydantic/SQLAlchemy deprecation warnings

### Mobile Follow-Up
- Real-device Android Chrome and iPhone Safari checks are still recommended before Capacitor packaging; current verification used Chromium mobile emulation with mocked API data.
- Device/session management now has a minimal parent-dashboard modal workflow; future mobile polish can add clearer device names once device metadata is stored.

---

## 🚀 Current State

This is now a **functional MVP product**, not a prototype.

Core loop works:
Parent sets rewards → child earns points → child requests reward → parent approves

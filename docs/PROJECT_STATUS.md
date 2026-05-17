# Family Hero Hub – Current Status

## ✅ Completed Features

### Authentication & Access
- Google OAuth for parent accounts
- Parent `last_login_at` tracking (updates on first-time and returning Google OAuth logins)
- Family-based data scoping
- Child device linking via QR code
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
- Mobile week picker uses a compact `S M T W T F S` strip
- Child dashboard shows today's tasks and events through the My Day/calendar integration

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

### Allowance System
- Backend support exists for optional child-level allowance settings
- Parents can store allowance currency, amount, weekly/monthly period, and point goal per child through API endpoints
- Allowance preview uses period ledger aggregation, not current point balances
- Rewards remain independent from allowance; reward holds, reward releases, and savings transfers are excluded from allowance preview calculations
- Parent-facing Allowance setup page exists at `/allowance`
- Parents can select a child, enable/disable allowance, choose OMR/USD/GBP/EUR, set weekly/monthly allowance goals, save settings, and view current-period allowance preview
- No child dashboard allowance display or automatic payouts are implemented yet

### UI / UX
- Responsive layout (tablet + mobile)
- Mobile UI consistency pass completed across common phone widths for parent dashboard, child dashboard, rewards, auth/linking pages, and calendar modals
- Global mobile viewport safeguards added for dynamic viewport height, safe-area insets, horizontal overflow, tap targets, and mobile form font sizing
- QR linking UI for child devices
- Reward cards fixed (no overflow issues)
- Improved contrast and readability
- Child-friendly dashboard experience
- Parent dashboard redesigned into a family-first, mobile-first launcher instead of a dense control-room layout
- Children now appear first on the parent dashboard with balanced child cards, saved balance shown consistently, and `Points` as the child card point-action entry
- Total available points and reward requests now use compact summary cards
- Parent Tools are grouped in a dedicated section with a top `Manage` button that smoothly scrolls to the tools area
- Manage Rewards, View Pending Requests, and Link child device use modal flows instead of large inline dashboard sections
- Parent dashboard copy was reduced to remove duplicate headings and development-style explanatory filler

### Infrastructure
- Dockerized deployment
- Caddy reverse proxy with HTTPS
- Domain: https://familyherohub.com
- Europe dev VPS setup completed for development/testing at https://dev.familyherohub.com
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
- WireGuard site mesh is live on `10.250.50.0/24` with Europe as hub, US as spoke, and UK as spoke
- Europe personal VPN is working on `10.60.0.0/24`
- UK personal VPN is working on `10.70.0.0/24`
- Hermes migrated to the Europe/France VPS and now runs there as the active Hermes host
- Hermes dashboard is available privately at `http://10.250.50.1:9119`
- Internal competitor review tooling is available privately at `http://10.250.50.1:8765`
- Internal docs viewer/editor is available privately at `http://10.250.50.1:8766`
- Europe private routing/firewall access is restored on reboot by `fhh-private-network-rules.service`
- US Hermes was removed from active runtime and archived at `/opt/apps/hermes-removed-from-us/`
- Ubuntu office box uses `wg-quick` with a split tunnel that routes only `10.250.50.0/24` through the Europe VPN
- Backend tests passing (60 tests)
- Frontend production build passes
- Europe PostgreSQL runtime smoke test now handles expired child-device links cleanly with HTTP 401 instead of a 500
- US production smoke tests and manual verification passed after the PostgreSQL cutover

---

## 🧪 Verified Working
- Child device linking (QR + link)
- Child session persistence
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
- All three servers can reach the `wg-easy` admin panels over the mesh at `10.250.50.1:51821`, `10.250.50.2:51821`, and `10.250.50.3:51821`
- Mobile calendar layout visually tested and improved
- Mobile consistency viewport sweep completed against production frontend build at 320, 360, 375, 390, 412, 430, 768, and 1365 px widths using mocked app data; no horizontal page scrolling or non-decorative element overflow found
- Parent dashboard child cards, quick actions, School Prep cards, rewards UI, child detail/log sections, login/request access, child/family invite pages, and parent/calendar modals were included in the mobile consistency pass
- School Bag and School Prep today/tomorrow school item flows
- Admin registration request approval
- Admin users page search/filter/pagination
- Parent revoke/restore access controls
- Family suspend/restore controls
- Revoked parent login/session blocking
- Suspended family parent and child blocking
- Bootstrap admin revoke protection

---

## ⚠️ Known Gaps / Not Yet Implemented

### Authentication Enhancements
- Device management (view/revoke sessions UI - backend done, needs dedicated UI page)
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
- Child-facing allowance progress display
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
- Production backup strategy now needs a scheduled backup/mirror/restore-test policy and retention review, not just `pg_dump`
- Production still requires follow-up restoration drills and mirror retention hardening, even though the US cutover itself is complete.
- Real-device mobile QA on Android Chrome and iPhone Safari
- Onboarding simplification and clearer family-safe wording
- Warning cleanup remains pending for SQLAlchemy FK cycle/drop_all warnings around `families`/`parent_users` and Pydantic/SQLAlchemy deprecation warnings

### Mobile Follow-Up
- Real-device Android Chrome and iPhone Safari checks are still recommended before Capacitor packaging; current verification used Chromium mobile emulation with mocked API data.
- Device/session management UI remains a future mobile workflow once the dedicated page is added.

---

## 🚀 Current State

This is now a **functional MVP product**, not a prototype.

Core loop works:
Parent sets rewards → child earns points → child requests reward → parent approves

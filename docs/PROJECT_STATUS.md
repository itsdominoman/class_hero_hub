# Family Hero Hub – Current Status

## ✅ Completed Features

### Authentication & Access
- Google OAuth for parent accounts
- Parent sessions last 30 days by default through `ACCESS_TOKEN_EXPIRE_MINUTES`; JWT expiry, `HttpOnly` access cookie lifetime, and CSRF cookie lifetime are aligned
- Parent `last_login_at` tracking (updates on first-time and returning Google OAuth logins)
- Family-based data scoping
- Family-level week start setting is parent-manageable from Calendar & School Week; default remains Sunday
- Child device linking via QR code
- Parents can view linked child devices and unlink one specific child device without deleting child data
- Parents & Caregivers management lets the family owner view grownups, remove another accepted grownup by soft-revoking access, and cancel pending invites
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
- Removed grownups lose access on their next API request because parent auth checks `parent_users.status` on every request

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
- Parent dashboard "Today" summary tile (E1): replaced the static "Points available" tile. Backed by `GET /api/calendar/summary`, which returns `configured` (family ever set up any calendar entry — hide-when-unused like the school bag tile), `tile_count` (today's events + outstanding tasks across children), and per-child `today` (primary) + `tomorrow` (lighter look-ahead) occurrence lists. Tapping opens a modal: per-child "N events · M tasks" with the items listed, and a de-emphasized "Coming up tomorrow" section. Configured-but-empty shows 0 ("Nothing on today"); never-configured hides the tile. "Outstanding" is a pure rule in `calendar_service` (`task_is_outstanding` / `count_attention_items`): events always count, a task counts until *approved* (pending/rejected still outstanding).
- Parent can mark a task complete from the Today modal (E2): `POST /api/calendar/{entry_id}/complete` (pre-existing) creates an *approved* completion immediately — no second approval step — and awards points/streak/pet exactly like an approved child-completion. Distinct from the C10 "Tasks to review" flow (approving a child's claim): a child-claimed (pending) task shows "Awaiting your review" with no complete button (the approve/reject stays in the child-modal review card), while still appearing in E1 as outstanding.
- Today modal look-ahead + full-calendar link (F1/F2): "Coming up tomorrow" now lists tomorrow's event TITLES per child (was counts only) and drops tomorrow's tasks (they resurface in their own day when actionable); children with no event fall out, and an all-empty look-ahead shows "Nothing on the calendar tomorrow". The modal footer links to the full `/calendar`. Frontend-only — `/calendar/summary` already returns full tomorrow occurrences.
- Unified task completion in the Today modal (G1): each today-task shows either E2's "Mark complete" (no claim yet → parent does it, immediately final) or, when the child has claimed it done (pending), a distinct "Says done" state with one-tap Confirm (approve) and Reject — via the existing `/calendar/completions/{id}/approve|reject`. The Today tile is now the primary place to resolve "is this done?" for both completion types; C10's per-child "Tasks to review" card stays as a secondary path. Badge unchanged (pending still counts as outstanding). Frontend-only — `/calendar/summary` already returns each pending completion's id + status.
- Expanded visual picker for presets & rewards (H1): the shared `DEFAULT_EMOJIS` set grew 24 → 69 options, ordered by category (hygiene, chores, food, school, sport, screen/entertainment, outdoors, pets, music/creativity, sleep, social/family, treats/rewards, transport, health). Also added the same picker to the reward editor (the `icon` field was persisted but had no picker UI). Emoji kept (no assets, no per-icon i18n, LTR/RTL-safe); same grid pattern, no C6 conflict. Frontend-only, no new i18n keys.
- Authenticated header handles `HttpOnly` cookies correctly by using `/api/me` as the source of truth and shows correct Parent Dashboard / Admin / Logout behavior.

### School Bag / School Prep
- Dedicated `school_items` backend is implemented
- School items are stored separately from calendar events and tasks
- Parents can configure school books/classes per child and weekday
- School items do not appear in the normal calendar agenda or week view
- Child dashboard School Bag shows:
  - Pack for tomorrow (children can now tick items off — B2)
  - Needed today (read-only, shows the previous evening's final packed state)
  - Check stationery
- Parent dashboard School Prep shows today/tomorrow school items per child
- Today/tomorrow lookup uses the family's timezone
- B2 packing state: per-item `school_item_checks(school_item_id, child_id, check_date, packed_at)`; absence of a row = not packed (implicit daily reset). Child-scope `POST`/`DELETE /api/child/school-items/{id}/pack`. A date's checklist is editable only while it is still in the future in the family timezone; once the day begins it is locked. No points awarded for packing.
- Parent-facing "School items missing" summary tile (B1): the dashboard summary-strip tile is tappable, opening a family-wide modal that shows, per child, "Needed today" (packed last night) and "Pack for tomorrow" (tonight's progress) as "N of M packed / Missing: …", with positive "All packed" / "Nothing for this day" states. The tile badge counts items still missing for *today* across all children; an empty positive state reads "School bag — all packed". Reads B2's existing `/school-items/today` packed state — no new backend endpoint.
- The school summary tile is hidden until the family has configured at least one school item (any child, any weekday), checked via read-only `GET /school-items/configured` → `{configured: bool}`. Families that have set things up still see the tile when everything is packed (positive state); only never-set-up families lose it. The reward-requests summary tile is a core always-on flow and stays visible; the Today (calendar) tile follows the same hide-until-configured rule as the school bag tile.
- The School Bag summary modal is read-only (D1): an earlier non-functional custom-points form that fell through into it has been removed; points for packing behaviour use a behaviour preset instead.
- Parents can mark a still-missing "Needed today" item packed from the summary modal (D2): `POST /api/school-items/{item_id}/pack` (parent auth, `{child_id}`) marks it for the family's local today, **bypassing** the child's midnight lock (`set_packed(..., enforce_lock=False)`). It writes the **same shared** `school_item_checks` row, so the resolution is consistent everywhere; the child's own today checklist stays locked read-only (their record of last night). This resolves the morning gap where a child packs a missing item after the checklist locked.
- The School Bag summary is time-windowed in the family's local timezone (D3) via a single aggregate `GET /api/school-items/summary` (replacing the dashboard's per-child today+tomorrow fan-out and the standalone `/configured` call for the tile): "Pack for tomorrow" is returned only 6pm→midnight (`PACK_TOMORROW_VISIBLE_FROM_HOUR = 18`), "Needed today" from midnight (`NEEDED_TODAY_VISIBLE_FROM_HOUR = 0`), and a child drops out of "Needed today" once fully resolved. The tile shows a backend-resolved `tile_count`/`tile_mode` (`missing_today` penalty-tint vs evening `pack_tomorrow` hero-tint) and hides when `tile_mode` is `none`. The window/tile rules are pure functions (`needed_today_window_open`, `pack_tomorrow_window_open`, `compute_tile_state`), ready to drive future pack/missing push notifications.

### Behaviour System
- Quick-tap behaviour presets (points/penalties)
- Separated from rewards (no longer mixed)
- Parent points modal supports Add points, Remove points, and Custom point actions
- Custom one-off point awards and penalties are available without creating a preset
- Adding and removing points provide short Web Audio feedback sounds
- Parent dashboard now opens a child action modal from each child avatar, with Points shown first, persistent Child Dashboard/Edit Child actions, and Requests, School Bag, Calendar, Savings, and Points Log available inside the same modal
- Edit Child supports display name changes and numeric avatar selection using avatar keys `1` through `24` resolved from `/avatars/{key}.png`
- Points Log includes Day / Week / Year filters and a behaviour ring chart that excludes savings, banking, redemptions, holds, and other system financial entries
- Points Log weekly filtering now follows the family's configured week start day

### Allowance System
- Backend support exists for optional child-level allowance settings
- Parents can store allowance currency, amount, weekly/monthly period, point goal, and allowance enabled date per child through API endpoints
- Weekly allowance periods use the family-level week start setting
- Allowance values are derived from allowance-linked points using integer minor-unit math
- Rewards, reward holds, reward releases, and savings deposits/unlocks reduce the available balance when allowance is enabled
- Parent-facing Allowance setup page exists at `/allowance`
- Parents can select a child, enable/disable allowance, choose from a broad searchable ISO-style currency list, set weekly/monthly allowance goals, save settings, and view allowance-linked summaries
- Allowance and savings value displays include the currency code plus a symbol where possible; the app does not perform exchange-rate conversion
- Child dashboard allowance display is now implemented for children with allowance enabled
- The app still does not automatically pay children
- Child dashboard savings banking is now implemented with a dedicated popup, savings bonus projection, next-unlock summary, and grouped unlock schedule

### UI / UX
- Responsive layout (tablet + mobile)
- English and Arabic fixed app UI support is implemented for the main app surface, with English as the default/fallback and Arabic using `lang="ar"` plus `dir="rtl"`.
- Public home, login, and request-access screens include a compact language selector so parents can choose Arabic before signing in. Parent Settings includes the same language control for logged-in parents.
- On first load, Arabic browser/device languages such as `ar`, `ar-OM`, `ar-SA`, and `ar-AE` default the UI to Arabic. A saved browser `localStorage` choice always overrides browser detection.
- The MVP stores the selected UI language in browser `localStorage`; no backend parent/family language hierarchy is implemented yet.
- Parent-entered content is not auto-translated: child names, reward names, task titles, calendar events, School Bag items, and custom point reasons remain exactly as entered.
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
- Arabic wording should receive native-speaker review before production launch, especially allowance, caregiver, reward request/redeem, and child-facing encouragement copy. See [LOCALISATION_NOTES.md](LOCALISATION_NOTES.md).
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

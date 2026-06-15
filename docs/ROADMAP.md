# Family Hero Hub – Roadmap

## 🎯 Phase 1 – MVP (COMPLETED)
- Parent authentication (Google OAuth)
- Child profiles
- Behaviour tracking (points system)
- Rewards system (parent-defined rewards)
- Child dashboard
- QR-based child dashboard links
- Secure child sessions

---

## 🔥 Phase 2 – Engagement & Retention (NEXT)

### 👶 Child Experience
- Pet system visuals integrated (dragon evolution stages)
- Animations for earning points
- Level-up/evolution feedback
- Reward unlock feedback (visual dopamine hit)
- Image optimization for pet assets
- Clear relink messaging for expired or invalid child-device links

### 🔐 Access Improvements
- Completed: Parent `last_login_at` now updates on first and returning Google OAuth logins
- Completed: Registration request approval flow
- Completed: Admin users page with search, filters, pagination, revoke/restore, and family suspend/restore
- Completed: Bootstrap admin protection; `PARENT_EMAILS` is now bootstrap/admin only
- Completed: Legacy bootstrap users migrated to database-approved access
- Completed: Last-parent revoke protection
- Completed: Parent-facing family member lists hide revoked parents
- Completed: Device/session management lets parents view linked child devices and unlink one device without deleting child data
- Completed: Family-level week start setting with Sunday default and named API values
- Completed: Parents & Caregivers removal MVP; the derived family owner can soft-revoke another grownup and cancel pending caregiver invites without deleting family data
- Child reward-request CSRF recovery for existing linked devices now happens through `/api/child/me`

### 🎁 Rewards System
- Reward approval UX improvements
- Reward history (child + parent view)
- Expiry or cooldown for rewards
- Reward request flow uses CSRF protection and automatic cookie recovery for valid child sessions
- Completed: Parent reward management and pending reward requests are available through modal flows from Parent Tools
- Follow-up: confirm whether child-side completion of rewardable tasks should be supported as a real child UX path or remain parent-only for now

---

## 📅 Phase 3 – Structure & Habit Building (IN PROGRESS)

- In progress: security and environment hardening for Phase 3, including canonical `APP_ENV`, fail-fast startup validation, loopback-only forwarded-header trust, explicit CORS origins, and an enforcing CSP.

### 📆 Family Calendar
- Completed: Parent-facing calendar page
- Completed: Normal events
- Completed: Task entries
- Completed: Rewardable tasks
- Completed: Simple recurrence (`none`, `daily`, `weekly`)
- Completed: Mobile-responsive calendar layout with compact week strip
- Completed: Child My Day integration for today's tasks/events
- Completed (E1): Parent dashboard "Today" summary tile (replaced the static "Points available" tile) — `GET /calendar/summary` aggregates today's events + outstanding tasks across children; tap opens a modal with a per-child today breakdown ("N events · M tasks") plus a lighter "Coming up tomorrow" look-ahead. Tile hides until the calendar is used at all; shows 0 when configured-but-empty.
- Completed (E2): Parent can mark a task complete directly from the Today modal (`POST /calendar/{id}/complete`) — immediately final (no approval loop) and awards points/streak like an approved child-completion. Distinct from the C10 "Tasks to review" approval flow; child-claimed tasks show "Awaiting your review" instead.
- Completed (F1): The Today modal's "Coming up tomorrow" look-ahead now lists tomorrow's event TITLES per child (was per-child counts only) and drops tomorrow's tasks entirely — tomorrow's tasks reappear in tomorrow's "Today" section when actionable, so showing them a day early is noise. Children with no events tomorrow fall out; when no child has any event tomorrow the section shows "Nothing on the calendar tomorrow". Pure frontend — the existing `/calendar/summary` already returns full tomorrow occurrences.
- Completed (F2): The Today modal footer links to the full `/calendar` view, matching the "open review"/"open calendar" footer-link pattern used by the Reward Requests and child Calendar modals.
- Completed (G1): Unified task completion in the Today modal. Per today-task it now shows either E2's "Mark complete" (no claim yet → parent does it themselves, immediately final) or, when the child has claimed it done (pending), a distinct "Says done" state with one-tap Confirm (approve) and Reject — posting to the existing `/calendar/completions/{id}/approve|reject`. The Today tile is now the primary "is this done?" surface for both completion types; C10's per-child "Tasks to review" card is kept as a secondary path. Frontend-only — `/calendar/summary` already returns each pending completion's id + status. The badge still counts a pending claim as outstanding (E1 rule, unchanged).
- Completed (H1): Expanded the shared "Select Visual (Optional)" emoji picker for behaviour presets and rewards from 24 → 69 options, ordered by category (hygiene, chores, food, school, sport, screen & entertainment, outdoors & nature, pets, music & creativity, sleep, social/family, treats & rewards, transport, health). Emoji kept (no assets, no per-icon i18n, LTR/RTL-safe). Also surfaced the picker in the reward editor, where `rewardForm.icon` was already persisted but had no UI. Same grid/selection pattern (no redesign); both editors scroll inside the modal body, so no conflict with C6's fixed-height tabbed picker. Frontend-only, no new i18n keys.
- Completed (FIX 1, audit #1): School Bag item deletion no longer fails after a child has packed the item. `replace_school_items` now soft-deletes removed items (`is_active = False`) instead of hard-deleting, which previously hit the ON DELETE NO ACTION FK from `school_item_checks` and raised a PostgreSQL FK violation. Soft-delete preserves packing history (relied on by the B2/D-series logic); no migration needed (the `is_active` column already existed and all reads filter it). Added a real-PostgreSQL FK-enforcement test (the SQLite suite couldn't catch this — coverage-gap #1).
- Future: Full monthly calendar view
- Future: Drag-and-drop calendar editing
- Future: Notification/reminder system (can reuse E1's pure `task_is_outstanding` / `count_attention_items` rules for a morning "what's on / still outstanding today" push)
- Future: Calendar warning cleanup and backend deprecation cleanup

### 🎒 School Bag / School Prep
- Completed: Dedicated `school_items` backend separate from calendar events/tasks
- Completed: Parents can configure school books/classes per child and weekday
- Completed: Child School Bag shows Pack for tomorrow, Needed today, and Check stationery
- Completed: Parent School Prep shows today/tomorrow items per child
- Completed: Family timezone-aware today/tomorrow lookup
- Completed (B2): Children tick "Pack for tomorrow" items off (per-item `school_item_checks`); the list locks at local-family midnight and "Needed today" then shows the final read-only state. No points awarded.
- Completed (B1): The parent summary tile "School items missing" is now tappable, opening a family-wide modal with, per child, "Needed today" (packed last night) and "Pack for tomorrow" (tonight's progress) as "N of M packed, Missing: …". Badge = total items still missing for today. Pure frontend read on B2's existing `/school-items/today` packed state — no new endpoint.
- Completed (B1 follow-up): The tile is hidden until the family has configured at least one school item (any child, any weekday), via read-only `GET /school-items/configured`. Families using the feature still see the tile even when everything is packed (positive state); only never-set-up families lose it.
- Completed (D1): Removed an unintended (and non-functional) custom-points form that was falling through into the School Bag summary modal — it is now a read-only summary. Points for packing behaviour are done via a behaviour preset.
- Completed (D2): Parents can mark a "Needed today" item packed from the summary modal (`POST /school-items/{id}/pack`), resolving the morning gap where a child packs a missing item after the day's checklist has locked. Writes the same shared `school_item_checks` row; the child's own today checklist stays locked read-only.
- Completed (D3): The summary is time-windowed in the family's local timezone via a single `GET /school-items/summary` aggregate — "Pack for tomorrow" shows 6pm→midnight, "Needed today" from midnight, and resolved children drop out so sections empty as the morning progresses. The tile shows a backend-resolved count/mode (missing-today vs pack-tomorrow) and hides when nothing is in-window. Window/tile rules are pure functions, ready to drive future pack/missing push notifications.
- Future: Optional school timetable improvements
- Future: School Bag push notifications (evening "pack the bag" + morning "what's missing") reusing the D3 pure window-logic functions

### ⚙️ Parent Productivity
- Completed: English/Arabic fixed UI localisation foundation with a parent Settings language selector, browser-local language persistence, English fallback, and Arabic right-to-left document direction.
- Completed: Main high-traffic surfaces now use translation keys for shared layout, public entry/login, parent dashboard/Settings/child action modal, allowance setup, and core child dashboard labels. Parent-created content remains untranslated by design.
- Completed: Parent dashboard simplified into a minimalist `My Family` view with child avatar buttons and compact point badges
- Completed: Tapping a child opens a dedicated child action modal rather than navigating to the child dashboard
- Completed: The child action modal opens on `Points` by default and keeps Add points, Remove points, and Custom point actions immediately available
- Completed: The child action modal includes persistent `Child Dashboard` and `Edit Child` actions
- Completed: The child action modal includes Requests, School Bag, Calendar, Savings, and Points Log sections
- Completed: Edit Child supports display name editing and numeric avatar selection
- Completed: Avatar assets use numeric keys `1` through `24` resolved from `/avatars/{key}.png`
- Completed: Points Log includes Day / Week / Year filters and a behaviour ring chart that excludes savings, banking, redemptions, holds, and system financial entries
- Completed: Points Log weekly filtering follows the family week start setting
- Completed: Parent tools remain secondary under `Settings`
- Completed: Duplicate Add Child entry removed from the child card area
- Completed: Child cards consistently show saved balance, including `0 saved`
- Completed: Child dashboard savings card now shows saved, available, locked, and next unlock details with a dedicated `Bank points` popup
- Completed: Child card point entry renamed from Actions to Points
- Completed: Short positive/negative Web Audio feedback sounds for successful point awards/penalties, with gain adjusted to 0.25
- Completed: Backend allowance settings and preview API for optional child-level allowance through points
- Completed: Parent-facing Allowance setup UI at `/allowance`
- Completed: Allowance-linked points summary with child-facing read-only allowance display
- Preset behaviour templates
- One-click daily routines
- Batch reward/add-or-remove-points assignment
- Future: Dedicated child management route/shell
- Future: Avatar/character customization
- Future: Shared family goals / house rewards
- Future: Component extraction from the large parent dashboard page
- Future: Native-speaker Arabic wording review and broader translation coverage for lower-traffic/admin/legal/help pages.

### 🔥 Streaks & Bonuses
- Future: Automatic weekly streak generation
- Future: Polished streak and bonus UI
- Future: Expand the savings bonus presentation with richer celebrations if needed

---

## 🤖 Phase 4 – Automation & Intelligence

- Smart suggestions (AI-assisted reward ideas)
- Behaviour insights ("most consistent habits")
- Notifications (Telegram / mobile push)
- Weekly summaries for parents

## 🧭 Infrastructure & Migration Planning

- Completed: US-Europe-UK WireGuard site mesh baseline on `10.250.50.0/24`
- Completed: Europe personal VPN on `10.60.0.0/24`
- Completed: UK personal VPN on `10.70.0.0/24`
- Completed: Hermes migration to the Europe/France server
- Completed: Private Hermes dashboard on the mesh-only URL
- Completed: Internal competitor review viewer on the private mesh
- Completed: Internal docs viewer/editor on the private mesh
- Completed: Persistent private network rules service for Europe reboot recovery
- Completed: Dev access lockdown with Caddy allowlisting for trusted IPs/VPN paths
- Completed: Internal PostgreSQL 16 service added to Europe dev for migration testing only
- Completed: Alembic baseline schema migration applied to the empty Europe PostgreSQL database
- Completed: Controlled SQLite-to-PostgreSQL ETL dry-run tool added and validated against the empty Europe PostgreSQL target
- Completed: Actual SQLite-to-PostgreSQL ETL import ran on Europe dev with row-count validation matching the source
- Completed: Europe dev runtime switched to PostgreSQL after import validation
- Completed: Europe dev PostgreSQL backup system implemented with pgBackRest + WAL archiving and restore rehearsal
- Completed: Narrow production cutover branch `prod/postgres-cutover-20260513` prepared on Europe from production `main` without unrelated dev-only QA, Playwright, FAQ/manual UI, notification, or Europe backup-sync tooling
- Completed: US production PostgreSQL cutover finished successfully using the verified backup set at `/opt/backups/family-hero-hub/prod-cutover-20260513-083225`
- Completed: US pgBackRest initialized and healthy, with first full backup `20260513-094837F` completed successfully
- Completed: Europe off-server mirror of the US pgBackRest repo created and checksum-verified at `/opt/backups/family-hero-hub/pgbackrest/us-prod/`
- Future: post-cutover PostgreSQL backup hardening, including scheduled backup/mirror/restore-test policy and retention review for US production
- Future: production cutover planning for any future hosting change, with DNS and mail handling reviewed separately
- Future: mail migration planning
- Future: SSH lockdown after all trusted/VPN access has been proven
- Future: backup automation over the private mesh
- Future: production PostgreSQL backup design using pgBackRest with WAL archiving, tested restore cadence, and off-server mirror retention, not `pg_dump` alone
- Future: CI/test gate before deploy
- Future: operational runbooks for private dashboards and VPN recovery
- Future: review whether any US personal VPN cleanup/recreation is still needed; `10.80.0.0/24` is not active and remains historical/future-only
- Future: optional office site mesh spoke at `10.250.50.10`
- Future: narrow sudo permissions for Hermes if needed
- Future: real-device mobile QA on Android Chrome and iPhone Safari
- Completed (FIX 2, audit #2): removed the inaccurate self-serve export/delete claim from public copy (FAQ, beta trust line, manuals, wording-decision doc) in EN + AR. Re-worded to the honest contact-us capability ("You can contact us to request a copy of your family data or ask us to delete it."); no self-serve export/delete exists yet. Copy-only — the actual feature is tracked in PLAN.md "Scope C — Future".
- Future: self-serve data export + family data deletion (the real feature behind FIX 2's contact-us wording; GDPR-style access/erasure)
- Completed (FIX 3, audit #2/#5 — frontend mitigation): client-side ~2s button lock on balance-affecting submits (reward redemption/request, savings deposit, points correction) reduces accidental double-taps via `src/lib/submitGuard.ts`, but remains UX-only.
- Completed (Phase 2 backend remediation): reward approve/reject now claims pending requests with an atomic conditional update; reject releases held points once; duplicate correction reversals are blocked by a partial unique index; savings maturity/bonus rows are database-unique per source deposit/type/jar; and ordinary balance/allowance/ledger GET paths no longer mature savings as a write side effect. Savings maturity is available through `POST /api/children/{child_id}/savings/mature` and the scheduler-ready `points_service.mature_savings_deposits` callable. Covered by real PostgreSQL concurrency tests in `backend/tests/test_phase2_concurrency_pg.py`.
- Future: broader API idempotency remains intentionally out of scope. Other balance-affecting write endpoints that do not have natural source rows may still need operation-specific idempotency keys, row locks, or constraints if product requirements demand retry-safe semantics.
- Future: trust/privacy copy improvements and clearer family-safe wording
- Future: onboarding simplification and stronger parent-facing conversion flow
- Future: reward history, reminders, and longer-term retention loops
- Future: replace runtime schema mutation with a clearer migration strategy

---

## 📱 Phase 5 – Platform Expansion

- Completed: Web mobile consistency pass for common Android/iPhone viewport widths before app wrapper work
- Completed: Dynamic viewport height, safe-area inset, tap-target, form font-size, and overflow safeguards for future WebView/Capacitor shells
- Mobile apps (Android APK first)
- Tablet-first UI polish
- Offline-friendly child mode
- Future: Real-device Android/iPhone QA pass before store submission

---

## 💰 Phase 6 – Monetization

- Free tier (basic families)
- Paid tier:
  - multiple parents
  - advanced analytics
  - AI features
  - extended storage/history

---

## 🧠 Long-Term Vision

A full **family operating system**:
- behaviour tracking
- education support
- gamified growth
- shared family calendar
- AI-assisted parenting tools
- full parent visibility and audit trail for all family events

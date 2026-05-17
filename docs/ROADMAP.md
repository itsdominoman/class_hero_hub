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
- Device/session management (parent can revoke child devices - backend done)
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

### 📆 Family Calendar
- Completed: Parent-facing calendar page
- Completed: Normal events
- Completed: Task entries
- Completed: Rewardable tasks
- Completed: Simple recurrence (`none`, `daily`, `weekly`)
- Completed: Mobile-responsive calendar layout with compact week strip
- Completed: Child My Day integration for today's tasks/events
- Future: Full monthly calendar view
- Future: Drag-and-drop calendar editing
- Future: Notification/reminder system
- Future: Calendar warning cleanup and backend deprecation cleanup

### 🎒 School Bag / School Prep
- Completed: Dedicated `school_items` backend separate from calendar events/tasks
- Completed: Parents can configure school books/classes per child and weekday
- Completed: Child School Bag shows Pack for tomorrow, Needed today, and Check stationery
- Completed: Parent School Prep shows today/tomorrow items per child
- Completed: Family timezone-aware today/tomorrow lookup
- Future: Optional school timetable improvements

### ⚙️ Parent Productivity
- Completed: Parent dashboard simplified into a family-first, mobile-first launcher
- Completed: Children appear first, followed by total available points / reward requests summary cards and Parent Tools
- Completed: Duplicate Add Child entry removed from the child card area
- Completed: Child cards consistently show saved balance, including `0 saved`
- Completed: Child card point entry renamed from Actions to Points
- Completed: Points modal supports Add points, Remove points, and Custom point actions
- Completed: Custom one-off point awards and penalties restored without requiring new presets
- Completed: Manage Rewards, View Pending Requests, and Link child device use modal flows
- Completed: Header Manage button smoothly scrolls to Parent Tools
- Completed: Short positive/negative Web Audio feedback sounds for successful point awards/penalties, with gain adjusted to 0.25
- Completed: Backend allowance settings and preview API for optional child-level allowance through points
- Completed: Parent-facing Allowance setup UI at `/allowance`
- Preset behaviour templates
- One-click daily routines
- Batch reward/add-or-remove-points assignment
- Future: Child-facing allowance progress display
- Future: Dedicated child management route/shell
- Future: Avatar/character customization
- Future: Shared family goals / house rewards
- Future: Component extraction from the large parent dashboard page

### 🔥 Streaks & Bonuses
- Future: Automatic weekly streak generation
- Future: Polished streak and bonus UI

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
- Future: formal US personal VPN cleanup/recreation to `10.80.0.0/24`
- Future: optional office site mesh spoke at `10.250.50.10`
- Future: narrow sudo permissions for Hermes if needed
- Future: real-device mobile QA on Android Chrome and iPhone Safari
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

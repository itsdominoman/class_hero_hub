# Family Hero Hub – Roadmap

## 🎯 Phase 1 – MVP (COMPLETED)
- Parent authentication (Google OAuth)
- Child profiles
- Behaviour tracking (points system)
- Rewards system (parent-defined rewards)
- Child dashboard
- QR-based child device linking
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
- Completed: Children appear first, followed by House Points / Reward Requests summary cards and Parent Tools
- Completed: Duplicate Add Child entry removed from the child card area
- Completed: Child cards consistently show saved balance, including `0 saved`
- Completed: Child card point entry renamed from Actions to Points
- Completed: Points modal supports Positive, Negative, and Other/custom point actions
- Completed: Custom one-off point awards and penalties restored without requiring new presets
- Completed: Manage Rewards, View Pending Requests, and Link Child Device use modal flows
- Completed: Header Manage button smoothly scrolls to Parent Tools
- Completed: Short positive/negative Web Audio feedback sounds for successful point awards/penalties, with gain adjusted to 0.25
- Preset behaviour templates
- One-click daily routines
- Batch reward/penalty assignment
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

- Future: WireGuard private link between the US and Europe servers for private rsync, backups, PostgreSQL migration/replication, mail migration prep, and private admin/internal traffic
- Future: PostgreSQL migration from SQLite when the database move is actually needed
- Future: Hermes migration onto the Europe server once that environment is ready for the main agent role
- Future: production cutover planning for a future Europe-based main server, with DNS and mail handling reviewed separately

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

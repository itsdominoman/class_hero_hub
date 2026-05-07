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
- Parent Points modal supports Positive, Negative, and Other/custom point actions
- Custom one-off point awards and penalties are available without creating a preset
- Positive point awards and negative penalties provide short Web Audio feedback sounds

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
- House Points and Reward Requests now use compact summary cards
- Parent Tools are grouped in a dedicated section with a top `Manage` button that smoothly scrolls to the tools area
- Manage Rewards, View Pending Requests, and Link Child Device use modal flows instead of large inline dashboard sections
- Parent dashboard copy was reduced to remove duplicate headings and development-style explanatory filler

### Infrastructure
- Dockerized deployment
- Caddy reverse proxy with HTTPS
- Domain: https://familyherohub.com
- Backend tests passing (60 tests)
- Frontend production build passes

---

## 🧪 Verified Working
- Child device linking (QR + link)
- Child session persistence
- Rewards creation → child visibility → request flow
- Child reward request CSRF recovery for existing linked devices
- Parent pending reward request card receives child requests
- Reward request hold/reserve behavior is enforced by the existing redemption hold ledger flow
- Reward rejection releases held points
- Reward approval finalizes points
- Parent dashboard + child dashboard interaction
- Multi-child support (e.g., Jackson, Leah)
- Parent dashboard launcher redesign visually approved after mobile review
- Parent dashboard launcher layout tested at 320, 360, 375, 390, 412, 430, 768, and desktop widths
- Parent Points modal positive/negative presets and custom one-off point awards/penalties
- Parent Tools modal access for rewards, pending reward requests, family settings, behaviour presets, calendar, add child, and child device linking
- Parent calendar event/task creation, editing, deletion, recurrence, and rewardable tasks
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

### Gamification
- Pet evolution visuals added; remaining work: animations, level-up feedback, image optimization, and deeper progression polish.
- Level progression feedback
- Animations / engagement elements
- Automatic weekly streak generation
- Polished streak and bonus UI

### Productivity Features
- Dedicated child management route/shell for child-specific Points, Rewards, Calendar, School Bag, Profile, and device sections
- Component extraction/refactor for the large parent dashboard page
- Full monthly calendar view
- Drag-and-drop calendar editing
- Notification/reminder system
- Warning cleanup / backend deprecation cleanup
- Optional future school timetable improvements
- Scheduled rewards / recurring behaviours
- Shared family goals / house rewards
- Avatar or character customization

### Mobile Follow-Up
- Real-device Android Chrome and iPhone Safari checks are still recommended before Capacitor packaging; current verification used Chromium mobile emulation with mocked API data.
- Device/session management UI remains a future mobile workflow once the dedicated page is added.

---

## 🚀 Current State

This is now a **functional MVP product**, not a prototype.

Core loop works:
Parent sets rewards → child earns points → child requests reward → parent approves

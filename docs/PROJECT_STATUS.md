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

### UI / UX
- Responsive layout (tablet + mobile)
- QR linking UI for child devices
- Reward cards fixed (no overflow issues)
- Improved contrast and readability
- Child-friendly dashboard experience

### Infrastructure
- Dockerized deployment
- Caddy reverse proxy with HTTPS
- Domain: https://familyherohub.com
- Backend tests passing (54 tests)
- Frontend production build passes

---

## 🧪 Verified Working
- Child device linking (QR + link)
- Child session persistence
- Rewards creation → child visibility → request flow
- Parent dashboard + child dashboard interaction
- Multi-child support (e.g., Jackson, Leah)
- Parent calendar event/task creation, editing, deletion, recurrence, and rewardable tasks
- Mobile calendar layout visually tested and improved
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
- Full monthly calendar view
- Drag-and-drop calendar editing
- Notification/reminder system
- Warning cleanup / backend deprecation cleanup
- Optional future school timetable improvements
- Scheduled rewards / recurring behaviours

---

## 🚀 Current State

This is now a **functional MVP product**, not a prototype.

Core loop works:
Parent sets rewards → child earns points → child requests reward → parent approves

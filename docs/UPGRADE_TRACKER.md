# Family Hero Hub - Upgrade Tracker

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

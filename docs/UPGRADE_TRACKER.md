# Family Hero Hub - Upgrade Tracker

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

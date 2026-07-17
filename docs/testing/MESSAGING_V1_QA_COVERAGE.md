# Messaging v1 QA coverage

**Status date:** 2026-07-17
**Current checkpoint:** S25i CHH Android safe-area, IME and hardware Back hardening.

## Automated S25i evidence

| Gate | Result | Coverage |
| --- | ---: | --- |
| Messaging frontend units | 5 passed | presentation/merge behavior and bounded native Back policy |
| Protected-media frontend units | 6 passed | authenticated thumbnail/view paths, native/browser blob handling and cleanup |
| EN/AR parity | 1,133 keys matched | no localization drift |
| Svelte check | 0 errors, 0 warnings | changed Svelte/TypeScript integration |
| Production frontend build | passed | static web bundle used by web and Capacitor |
| Focused Playwright | 6/6 passed | deep link/optimistic send, polling/resume, Android inset/resize/Back/draft, RTL, disabled policy, offline/revoked state |
| Messaging backend | 40 passed, 1 skipped | prerequisite defaults, API/core/integration and FHH proxy boundaries |
| Auth/school/report/update backend | 95 passed | auth/session-facing APIs, school structure/dashboard data, reports, updates/protected media |
| Android app Gradle | passed | `:app:testDebugUnitTest`, `:app:lintDebug`, `:app:assembleDebug`, `:app:assembleDebugAndroidTest` |
| APK inspection | passed | `com.classherohub.app`, SDK/version identity, fixed native API, v1/v2 debug signature |

The Android-sized Playwright regression uses a 390×844 portrait viewport and a
24-pixel bottom safe inset. It verifies sticky composer placement and inset padding,
a 48×48 send target, a 390×560 IME-resized viewport, preserved draft/focus/cursor/
selection, keyboard-first Back, conversation-to-inbox Back, draft restoration,
polling, optimistic send, new-message indication and existing shell navigation.

## Manual device gate still required

- Gesture navigation and three-button navigation, keyboard open and closed.
- OEM system-bar hit testing: composer taps must never invoke Home/Recent Apps or
  minimize CHH.
- Actual IME visibility/resize and hardware Back event ordering.
- Portrait route transitions, background/resume and authenticated session restore.
- Two-party CHH/FHH 12-second polling while typing and scrolled away from the bottom.
- Native Google account picker/login, dashboards, protected media, camera and gallery.

Record device, Android version, navigation mode, keyboard, APK checksum and tester in
`CHH_ANDROID_APK_SMOKE_TEST.md`. Automated browser/host tests cannot close this device
gate.

## Explicit exclusions

No S25i test claims coverage for messaging photos, final receipt UI, contact-hours
scheduling, notification delivery/push, safeguarding administration or retention,
because those Slice 8+ capabilities remain unimplemented.

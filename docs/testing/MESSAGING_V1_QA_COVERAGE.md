# Messaging v1 QA coverage

## S25q protected-voice gate — 2026-07-18

Focused automated evidence passed without rerunning unrelated project suites:

| Gate | Result | Scope |
|---|---:|---|
| CHH backend | 44 passed | actual ffmpeg normalization/rejection, controls/audit, idempotency, scope, cleanup, retained playback |
| CHH frontend | 12 passed | recorder/player/composer/history contracts and regressions directly affected |
| FHH backend | 28 passed | child/family/link proxy, bounded buffering, signed checksum/size, allowlist and lifecycle |
| FHH frontend | 14 passed | recorder/player state and UI parity |
| EN/AR parity | CHH 1,215; FHH 1,451 | exact key parity |
| Production web builds | CHH and FHH passed | web/Capacitor assets compile |

App-scoped Android unit, lint and dev assembly plus deployed migration/API smoke are
release gates recorded separately. Manual device coverage must exercise microphone
grant/deny, sub-600 ms cancellation, 180-second stop, hold/cancel/lock/pause/resume,
background/interruption, preview/delete/re-record/send, seek/speed/single-playback,
Bluetooth/speaker routing, Arabic RTL gestures, three-button/gesture navigation,
offline retry and access revocation. See `CHH_ANDROID_APK_SMOKE_TEST.md`.

Unimplemented receipt/contact-hours/notification/safeguarding-workflow/retention
slices remain outside this focused gate.

## Slice 8 protected-photo gate — 2026-07-18

Automated coverage proves text-only, photo-only and mixed sends; five-photo maximum;
stable upload/send retry; cross-school, cross-conversation and cross-participant
denial; revoked participant denial; actual-format sniffing; corrupt/decompression
limits; EXIF/GPS removal; derived-only storage; expired-stage cleanup; isolated broken
media; protected headers; FHH response allowlists; thumbnail-only timelines; and the
fixed 26-SELECT 50-message history budget. Frontend contracts cover browser gallery,
Android camera capture, selected previews, remove/retry, object-URL cleanup,
photo-only send, viewer pinch/pan/swipe/arrows/Escape/native Back, EN/AR parity and
the accepted sticky/safe-area/polling/draft behavior.

Required manual real-device checks remain: grant/deny camera and gallery access;
select/take five real HEIC/JPEG photos; retry one failed item; send photo-only and
mixed messages between CHH and FHH; pinch/pan/swipe in both viewers; press Back with
the viewer and keyboard open; background/resume during upload; revoke access while a
viewer is open; and confirm no full image is fetched until the viewer opens.

Slices 9–13 are not covered because they remain pending.

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

## Slice 9 receipt coverage

Focused backend coverage verifies Sent → Delivered → Read, one-of-several eligible
FHH adults, late-join exclusion, non-regression after revocation, safeguarding-admin
exclusion, all four independent policy combinations, safe FHH proxy fields, canonical
delivery/read acknowledgement bodies, and the fixed 28-SELECT budget for a 50-message
page (27 before Slice 9). Text, protected-photo and protected-voice send responses use
the same initial Sent receipt contract.

Focused presentation coverage verifies one/two tick shape distinction, accessible
Sent/Delivered/Read labels, outgoing-only placement beside timestamps, EN/AR parity,
narrow bubble containment, monotonic stale-poll merges, and legitimate projection
changes only when the policy version increases. Polling merges receipt updates into
existing rows and does not replace conversation state, drafts, media, playback, focus,
cursor, keyboard or scroll ownership.

Still excluded: all-recipient-read state, receipt identities/counts, message-info UI,
contact-hours scheduling, notification delivery/push, safeguarding administration
tools, retention automation, WebSockets and SSE.

# CHH Android APK implementation log

Status date: 2026-07-17
Scope: implementation record for the Class Hero Hub (CHH) Capacitor Android app.

## Identity and build output

- Capacitor Android project: created at `frontend/android`.
- Application ID/package: `com.classherohub.app`.
- App name: **Class Hero Hub**.
- Capacitor web directory: `frontend/build`; Android scheme: `https`.
- Canonical debug output: `frontend/android/app/build/outputs/apk/debug/app-debug.apk`.
- External debug artifacts are copied to `/opt/artifacts/apk/chh/` as
  `chh-debug-<purpose>-YYYY-MM-DD-<shortsha>.apk`, with a matching `.apk.sha256`
  file. The current camera-updates artifact is
  `chh-debug-camera-updates-2026-07-14-71ef53f.apk`.
- Debug builds use Android's debug signing; no release signing has been configured.
- S25h development retest artifact:
  `/opt/apps/class_hero_hub/tmp/class-hero-hub-messaging-usability-dev.apk`
  (`95,763,254` bytes, SHA-256
  `4461a7991b41ebac26feff63265cc7a3d5513761f30f53a32b71d1703163298b`).
  It is the debug variant, version code `1`, version name `1.0`, package
  `com.classherohub.app`, target/compile SDK 35, and uses the fixed native API
  `https://class.familyherohub.com/api`.
- S25i safe-area development artifact:
  `/opt/apps/class_hero_hub/tmp/class-hero-hub-s25i-dev.apk`
  (`95,845,408` bytes, SHA-256
  `55c777e0e344f7777fb308e6cc7d9233f672c01f93ad5b12f6554cef82077834`).
  It is the debug variant, version code `1`, version name `1.0`, package
  `com.classherohub.app`, minimum SDK 23, target/compile SDK 35, and contains the
  fixed native API `https://class.familyherohub.com/api`. The identical file is at
  `G:\My Drive\CHH\Remote\class-hero-hub-s25i-dev.apk`.
- S25q protected voice-note development artifact:
  `/opt/apps/class_hero_hub/tmp/class-hero-hub-voice-notes-dev.apk`, with an identical
  Google Drive copy at
  `G:\My Drive\CHH\Remote\class-hero-hub-voice-notes-dev.apk`. It is the debug
  variant, package `com.classherohub.app`, version code `1`, version name `1.0`, compile
  SDK 35, and contains `https://class.familyherohub.com/api`. Size is 95,893,704 bytes;
  SHA-256 is
  `b2fd998690250ac3167a6265b3bd4c0f6a2356d997d336ce6669294b545e324c`.
  App-scoped `testDebugUnitTest`, `lintDebug`, and `assembleDebug` passed; manifest,
  packaged endpoint and Android debug signature inspection passed. Device microphone,
  interruption, audio-route and navigation execution remains required.
- S26k administrator-receipt development artifact:
  `/opt/apps/class_hero_hub/tmp/class-hero-hub-admin-receipts-dev.apk`, with an
  identical Google Drive copy at
  `G:\My Drive\CHH\Remote\class-hero-hub-admin-receipts-dev.apk`. It is the debug
  variant, package `com.classherohub.app`, version code `1`, version name `1.0`, min
  SDK 23, target/compile SDK 35, and contains the fixed API
  `https://class.familyherohub.com/api`. Size is 95,986,665 bytes; SHA-256 is
  `f4ab4cf8f58f4a3e28aca49a80c57d06571f24435abe5d424803f57596310902`.
  App-scoped `testDebugUnitTest`, `lintDebug` and `assembleDebug`, ZIP integrity,
  package/endpoint and v1/v2 debug signature inspection passed. The signer certificate
  SHA-256 remains
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
- The merged Android manifest explicitly removes the transitive biometric and
  fingerprint permissions from the encrypted-preferences dependency. CHH does
  not use biometric authentication and the APK requests no camera or storage
  permission; Capacitor Camera uses the system camera/photo picker.
- Android application backup is disabled so the bearer token in encrypted
  preferences cannot be copied or restored independently of its Keystore key.
- The checked-in instrumented identity test compares the installed target
  context with CHH's real `com.classherohub.app` application ID, rather than
  Capacitor's template package. Host-side builds compile it with
  `./gradlew assembleDebugAndroidTest`; execution still requires a device or
  emulator.

## Native authentication

CHH uses a native Google sign-in path only inside Capacitor Android:

1. The Android `GoogleAuthPlugin` uses Android Credential Manager and Google ID to
   obtain a Google ID token. It tries an authorized-account request first, then the
   interactive account picker for a first-time user.
2. The app posts `{ "id_token": "..." }` to
   `POST /api/auth/google/native` (native base: `https://class.familyherohub.com/api`).
3. The backend verifies the token with `google-auth[requests]`, using the configured
   Web OAuth client ID as the audience, and returns the CHH bearer access token.
4. The native frontend keeps the bearer token in memory and stores it under
   `chh_access_token` using the `SecureStorage` Capacitor plugin backed by encrypted
   Android preferences. Native API calls use `Authorization: Bearer <token>` and omit
   browser cookies; logout clears that storage.

Browser OAuth remains a separate cookie/session flow. It continues to use its normal
CSRF/state validation and must not be weakened or disabled for the native flow.

## Native shell and mobile UX

- Android 15/target SDK 35 edge-to-edge handling sets light status-bar and navigation-
  bar icons so they remain legible against CHH's light shell.
- The app shell detects Capacitor before hydration. In the native app it bypasses the
  public homepage and routes logged-out users to login or authenticated users to their
  role dashboard; the website footer is hidden. Browser web retains the public homepage
  and footer.
- CHH branding is used for the launcher/splash/header, including `chh-logo-master.png`.
- Teacher class selection has compact mobile labels and buttons to make class choices
  practical on a phone.
- The S24 quick behaviour overlay is available from the class roster and uses the
  configured quick/other positive and needs-work behaviours.
- The S25h Messages thread listens for Capacitor app resume as well as browser focus,
  visibility and online restoration. Its 12-second delta refresh is append-only and
  does not remount the composer, dismiss the soft keyboard, overwrite a draft, or
  move selection. Auto-scroll follows only a reader already near the bottom.
- S25i reserves the Android bottom system inset inside the sticky composer, explicitly
  uses activity `adjustResize`, and lets the mobile `100dvh` workspace shrink while
  the IME is open. The send control remains a 48×48 tap target above gesture and
  three-button navigation areas.
- S25i registers one native Back dispatcher. An editable field consumes Back and
  dismisses the keyboard first; a compose overlay is next; an open conversation then
  returns to the inbox; existing mobile-menu and bounded root/history handling remain
  in place. Drafts are retained per membership/conversation when returning to the
  inbox, and no Back press silently discards an unsent draft.
- Native validation for S25h passed Gradle `testDebugUnitTest`, `lintDebug`,
  `assembleDebug`, and `assembleDebugAndroidTest`. APK signature verification passed
  v1/v2 debug schemes and the instrumented test APK assembled; execution of device
  tests and the two-party keyboard/resume flow still requires a physical device.
- Native validation for S25i passed app-scoped Gradle `testDebugUnitTest`, `lintDebug`,
  `assembleDebug`, and `assembleDebugAndroidTest`; focused Android-sized Playwright
  coverage passed 6/6 with inset, resize, focus/selection, Back and draft checks.
  APK verification passed v1/v2 debug signatures and package/app-ID inspection.
  Gesture-navigation and three-button-navigation device execution remains required.

## Updates & photos

The shared teacher Updates & photos component is used by web and the Android shell.

- **Take photo** in native Android uses `@capacitor/camera` with
  `CameraSource.Camera`, URI output, quality 85, and editing disabled. It opens the
  system camera directly.
- **Upload photos** in native Android uses `CameraSource.Photos`, opening the system
  gallery/photo picker rather than the camera.
- A native result URI is fetched and converted into a `File`, then passes through the
  existing update-photo validation and multipart upload path. Accepted formats are
  JPG/JPEG, PNG, and WEBP; HEIC/HEIF is rejected; the limits remain five photos and
  10 MB per photo.
- Native media viewing is part of the feature, not an optional follow-up. Teacher update
  photo endpoints remain protected: the Android app fetches them through the existing
  bearer-auth API helper, validates the image blob, and renders a temporary object URL
  for the thumbnail and full-screen viewer. It never places a bearer token in a URL.
  Browser viewing keeps its existing direct, cookie-authenticated image path.
- Browser/mobile web retains file inputs. Its Take photo input keeps the browser
  `capture="environment"` hint, while Upload photos remains a normal picker.
- Camera cancellation is harmless; a non-cancellation native failure shows a friendly,
  translated error and the buttons are disabled while a native picker is open.

No camera/media/storage runtime permission was added for this implementation. The
Capacitor Camera v7 system camera/photo-picker flow does not need one when
`saveToGallery` is not used.

## Related delivery and interface work

- The reporting area received mobile/control-centre polish; it remains separate from
  native authentication and photo handling.
- The Android project includes native Google login, secure token storage, CHH app
  branding, splash assets, and shell behaviour. Keep CHH package/client identifiers
  separate from FHH at every layer.

## Source pointers

- `frontend/capacitor.config.ts`
- `frontend/android/app/build.gradle`
- `frontend/android/app/src/main/java/com/classherohub/app/MainActivity.java`
- `frontend/android/app/src/main/java/com/classherohub/app/GoogleAuthPlugin.kt`
- `frontend/android/app/src/main/java/com/classherohub/app/SecureStoragePlugin.kt`
- `frontend/src/lib/nativeAuth.ts`
- `frontend/src/lib/native/back-policy.ts`
- `frontend/src/lib/native/platform-bridge.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/routes/+layout.svelte`
- `frontend/src/routes/messages/+page.svelte`
- `frontend/src/lib/components/messaging/MessageComposer.svelte`
- `frontend/src/routes/+page.svelte`
- `frontend/src/routes/teach/assignments/[id]/+page.svelte`
# Updates & Photos image optimisation (2026-07-14)

- Updates & Photos accepts JPEG/JPG, PNG, WEBP, HEIC and HEIF raw uploads up to 50 MB. HEIC/HEIF iPhone photos are converted automatically; Live Photo video sidecars are not accepted.
- The server corrects EXIF orientation, normalises colours to web-safe RGB, limits the longest edge to 1600 px, strips EXIF/other metadata, and stores a single optimised JPEG (or alpha-preserving WEBP).
- The preferred stored size is under 1 MB; the hard maximum is 1.5 MB. The raw upload is memory-only and discarded immediately after processing. CHH and FHH protected media routes serve the optimised bytes only.
- Optimisation is quality-first: JPEG/WEBP encoding starts at quality 85 and only
  reduces when the normal 1 MB target requires it. Quality 78 is the preferred
  floor; detailed artwork or writing may remain between 1 MB and 1.5 MB at that
  quality rather than being unnecessarily crushed.

## S25w app-wide safe-area shell and teacher messaging handoff

- Native CHH now fixes the branded header/logo/menu as the top flex boundary below
  `--safe-top`; route content no longer owns the document viewport.
- The single native `app-main` scroller owns `--safe-bottom` for ordinary
  authenticated routes. Messaging is explicitly viewport-managed so its accepted
  sticky composer continues to own that inset exactly once.
- The behavior applies on teacher lists and class dashboards, school administration,
  Reporting, guardian routes, and other routes rendered through the shared shell.
  Browser chrome, desktop page flow, public footer, Android Back, IME resize, session
  restoration, and existing message drafts are unchanged.
- Quick Award reuses the current protected messaging route. Its return query is
  constrained to the originating assignment and exact student, and successful send
  or explicit back restores that overlay rather than dropping the teacher at an
  inbox or dashboard.
- Android-sized Playwright coverage uses 24px/48px synthetic system insets and a long
  class list to assert fixed header geometry, one internal scroller, zero document
  scroll, and a fully tappable last class above the navigation inset.
- Fresh S25w artifact:
  `/opt/apps/class_hero_hub/tmp/class-hero-hub-mobile-shell-dev.apk`; identical Drive
  copy `G:\My Drive\CHH\Remote\class-hero-hub-mobile-shell-dev.apk`.
- Package `com.classherohub.app`, version code `1`, version name `1.0`, compile SDK
  35, fixed API `https://class.familyherohub.com/api`; 95,891,184 bytes; SHA-256
  `37a07656d91d343e8bc27db2b0ae3d22a9af0e339a20be6726237f5bc08eea7b`.
- Android debug signature verified under APK signature schemes v1 and v2; signe
  certificate SHA-256 remains
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
- App-scoped `testDebugUnitTest`, `lintDebug`, and `assembleDebug` passed on
  Temurin 21.0.11 with Android SDK/build tools 35.

## S26c physical-device bottom inset correction

- Android 15 edge-to-edge WebViews do not reliably publish the navigation-bar
  height through CSS `env(safe-area-inset-bottom)`, and Capacitor's
  `adjustMarginsForEdgeToEdge` compatibility margin is not enabled in this app.
  The S25w browser-only test supplied a synthetic CSS value, so it did not exercise
  the missing native inset delivery seen on a physical device.
- CHH now registers a small Android `SystemInsets` plugin. It reads navigation-bar
  and display-cutout insets from `WindowInsetsCompat`, including hidden/gesture
  system bars, converts physical pixels to CSS pixels, and publishes the bottom
  value as `--native-safe-bottom`. Web/browser builds retain the CSS safe-area
  fallback.
- The authenticated `app-main` scroller owns one real trailing spacer equal to the
  native bottom inset plus a 12px visual gap. Making the reservation an actual final
  scroll item avoids overflow implementations clipping edge padding. Teacher class
  lists, student grids, School setup, Reporting and other inherited routes therefore
  expose usable final scroll space without per-page padding.
- Messaging remains the explicit viewport-managed exception: its sticky composer
  continues to own the bottom inset, and the shared trailing spacer is suppressed.
  Fixed overlays retain their existing safe-area rules. The fixed header and top
  status-bar inset were not changed.
- Focused coverage validates native inset conversion, the shared shell's final
  scroll geometry across teacher list, student grid, School setup and Reporting,
  the fixed header, the unchanged messaging composer, English/Arabic key parity,
  Svelte/type checking and a production frontend build.
- The paired focused messaging API tests passed, including a Bob-like student with
  revoked CHH guardian links, active FHH-linked parents, an existing active
  conversation and an idempotent second create request. The focused Android-sized
  Playwright matrix passed 4/4, and app-scoped `testDebugUnitTest` plus
  `assembleDebug` completed successfully.
- Fresh S26c artifact:
  `/opt/apps/class_hero_hub/tmp/class-hero-hub-bottom-inset-guardian-fix-dev.apk`;
  identical Drive copy
  `G:\My Drive\CHH\Remote\class-hero-hub-bottom-inset-guardian-fix-dev.apk`.
- Package `com.classherohub.app`, version code `1`, version name `1.0`, compile and
  target SDK 35, fixed development API `https://class.familyherohub.com/api`;
  95,918,883 bytes; SHA-256
  `dec27cff2e71c725f1d223a821dc175e939b6f64cd20ea81695886314626d032`.
- APK signature verification passed v1 and v2 with the established Android debug
  certificate SHA-256
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.

## S26i Messaging receipt presentation

- Outgoing text, photo, and voice bubbles share localized accessible receipt ticks:
  one gray for sent, two gray for delivered to any eligible ordinary participant,
  and two blue for read by any eligible ordinary participant. The compact footer is
  RTL-safe and does not expose text, names, counts, or household-completion state.
- Receipt-only polling updates the existing message object and does not recreate the
  row, preserving the composer, keyboard/cursor, scroll position, and voice-player
  state. Delivery is acknowledged only after render; read is acknowledged only for
  the visible active conversation.
- `testDebugUnitTest`, `lintDebug`, and `assembleDebug` passed with the final
  synchronized web assets on Temurin 21.0.11 and Android SDK 35.
- Artifact: `/opt/apps/class_hero_hub/tmp/class-hero-hub-message-receipts-dev.apk`;
  Drive copy `G:\My Drive\CHH\Remote\class-hero-hub-message-receipts-dev.apk`.
- Package `com.classherohub.app`, version code `1`, version name `1.0`, min SDK 23,
  compile/target SDK 35, API `https://class.familyherohub.com/api`; 95,807,045 bytes;
  SHA-256
  `5dc8fbcab2cff03e0941543d08664afaae2177c6f8381b7f57f37d6b11021124`.
- APK signature verification passed with the established Android debug signer
  certificate SHA-256
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.

## S26j Messaging contact hours and notification timing

- The administrator contact-hours editor and urgent-policy capability, plus the
  unchanged staff messaging surface, were synchronized into the Android shell.
  Contact hours delay only background notification eligibility; they do not hide a
  committed parent message from staff who open CHH. Slice 10 makes no provider call.
- Host-side system-inset tests now use the exact literal ARGB values previously
  produced by Android `Color` helpers. This removes Android-framework class
  initialization from JVM tests without changing runtime pixels, inset ownership,
  safe-area behavior, or native Back behavior.
- Fresh app-scoped `testDebugUnitTest`, `lintDebug`, and `assembleDebug` passed on
  Temurin 21.0.11 with Android SDK/build tools 35 after final Capacitor sync.
- Artifact: `/opt/apps/class_hero_hub/tmp/class-hero-hub-contact-hours-dev.apk`;
  identical Drive copy
  `G:\My Drive\CHH\Remote\class-hero-hub-contact-hours-dev.apk`.
- Package `com.classherohub.app`, version code `1`, version name `1.0`, min SDK 23,
  compile/target SDK 35, API `https://class.familyherohub.com/api`; 95,954,195 bytes;
  SHA-256 `6dee024626863e0bef33e761f6c7a378a97d6bccfaa22c588bdc0085ba6f01ba`.
- APK signature verification passed under v1/v2 with debug signer certificate
  SHA-256 `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.

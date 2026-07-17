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

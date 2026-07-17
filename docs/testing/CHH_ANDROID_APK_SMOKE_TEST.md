# CHH Android APK smoke test

Use this checklist on a physical Android device after installing a debug APK. Record
device model, Android version, APK filename, checksum, date, and tester with the run.

## Install and app identity

- [ ] Install or update the APK without an installer error.
- [ ] Confirm the launcher icon and displayed app name are **Class Hero Hub**.
- [ ] Confirm the splash screen, header, and logo use CHH branding.
- [ ] Confirm status-bar and navigation-bar icons are visible and legible.

## App shell and authentication

- [ ] When logged out, opening the app goes directly to Login rather than the public
      homepage.
- [ ] Confirm the public website homepage and footer are not shown in the native app.
- [ ] Tap Google sign-in and confirm Android's native account picker appears.
- [ ] Complete login with an authorized test account and confirm the correct
      authenticated dashboard route opens.
- [ ] If login is cancelled or unavailable, confirm a clear error appears and the app
      remains usable.

## Teacher flow

- [ ] Open the teacher dashboard and confirm class-selection controls are compact and
      usable on the mobile viewport.
- [ ] Open a class successfully.
- [ ] Open the quick points/behaviour overlay from a student and confirm the configured
      actions render and can be dismissed safely.

## Updates & photos

- [ ] Open **Updates & photos**.
- [ ] Tap **Take photo** and confirm the native camera opens directly (not the gallery).
- [ ] Cancel the camera and confirm the form remains usable with no crash or stuck
      loading state.
- [ ] Capture a photo; confirm it appears in the selected-photo list and can be posted.
- [ ] Confirm the posted photo displays in the update.
- [ ] Tap the posted photo and confirm the enlarged protected-media viewer displays it.
- [ ] Tap **Upload photos** and confirm the gallery/photo picker opens (not the camera).
- [ ] Select a supported photo and confirm it attaches/posts successfully.
- [ ] Check invalid type, oversize, upload/network failure, and cancellation handling:
      errors must be clear, with no duplicate upload or stuck state.

## Other key routes

- [ ] Create/open homework or notes and verify attachments and navigation remain usable.
- [ ] Open the reporting page and verify its mobile controls and content load.
- [ ] Open and close the hamburger drawer; verify navigation destinations work.
- [ ] Log out, reopen the app, and log in again successfully.

## Messaging development pilot

- [ ] Sign in as an authorized United International School teacher/admin and confirm
      **Messages** appears; verify it remains absent for a school whose policy is off.
- [ ] Open a thread and confirm the header/inbox show `Student · grade/class`.
- [ ] With two authorized guardians, send from each FHH account and confirm every
      message shows the exact guardian name and relationship when available.
- [ ] Keep the CHH composer focused with draft text and the Android keyboard open.
      Send a reply from FHH, wait at least 12 seconds, and confirm the incoming row
      appears without losing text, selection, focus, keyboard, or optimistic rows.
- [ ] Scroll away from the bottom, receive another reply, and confirm **New messages**
      appears without jumping. Activate it and confirm it reaches the new row.
- [ ] Background and resume the app and confirm the active thread refreshes
      immediately without duplicating rows.
- [ ] Confirm Arabic/Fusha labels, RTL layout, and mixed-direction names/body text are
      readable and do not reverse timestamps or status meaning.
- [ ] Recheck Android Back, safe areas, keyboard resize, session restoration, direct
      login, protected update media, camera and gallery flows after messaging tests.

## Browser regression check

- [ ] In a desktop or mobile browser (not the APK), confirm the public homepage/footer
      still render.
- [ ] Confirm browser Google login continues to work with its normal redirect/state
      flow.
- [ ] In browser Updates & photos, confirm Upload photos is a file picker and Take photo
      retains the browser capture/file-picker behaviour.

## Result

- [ ] Pass
- [ ] Fail — attach screenshots, route, device/OS, APK checksum, and reproduction steps.
# Updates & Photos image optimisation smoke coverage (2026-07-14)

1. In a teacher assignment, create an update with a normal Android/iPhone/desktop image. Confirm JPG, PNG, WEBP and iPhone HEIC/HEIF files up to 50 MB are accepted; MOV/MP4 must be rejected.
2. Take a portrait iPhone photo and confirm it displays upright in CHH and linked FHH. Confirm output has a longest edge no greater than 1600 px and is served as an image (normally JPEG, or WEBP when transparency is needed).
3. Confirm the protected CHH and FHH image endpoints still require their normal authentication. Inspect update storage: there must be one metadata-free optimised image under 1.5 MB, with no retained raw upload.
4. Upload a detailed artwork, handwriting, or textured student-work image. Confirm
   its visual detail remains clear; output may reasonably be 600 KB–1.2 MB (up to
   the 1.5 MB hard limit) rather than being forced to the smallest possible file.

# CHH Android APK smoke test

## Slice 10 contact-hours regression matrix

Use the Slice 10 development APK against `https://class.familyherohub.com/api`.

1. As a school administrator, verify the school timezone, Sunday-Thursday
   07:30-15:00 schedule, Friday/Saturday closed state, and fixed **Delay
   notifications only** text. Add/remove a closed and custom date exception.
2. Confirm administrators see **Mark as urgent**; teachers see it only after the
   audited school control is enabled; guardians never see it.
3. Confirm the personal out-of-hours checkbox appears only when the school allows it,
   survives app restart, and disappears/becomes ineffective when permission is
   withdrawn.
4. Outside hours, send from FHH and immediately open the CHH thread. The message must
   be visible; only background notification delivery is held. Existing text, photos,
   voice notes, ticks, polling, draft, focus, safe-area and Back behavior must match
   the Slice 9 APK.
5. Repeat in English/Arabic, gesture/three-button navigation, keyboard open/closed,
   background/resume and temporary network loss. Slice 10 contains no push-provider
   call, so no lock-screen notification is expected from the new outbox.

## S25q microphone and protected voice matrix

Use `class-hero-hub-voice-notes-dev.apk` (`com.classherohub.app`) against the CHH
development API. Record device, Android/WebView version, navigation mode, keyboard,
locale, network and APK SHA-256.

1. With Voice notes disabled, confirm no microphone is shown and text/photo messaging
   is unchanged. Enable only through the UIS administrator acknowledgement modal.
2. Grant microphone permission and record with hold/release. Deny permission once,
   recover through settings and confirm text messaging remains usable.
3. Slide horizontally to cancel in English and mirrored Arabic RTL. Record under 0.6
   seconds (cancelled), then record to the three-minute automatic stop.
4. Swipe up to lock; pause/resume; background and resume; accept an interruption such
   as a call/alarm; delete, re-record, preview and send.
5. Force network loss during upload and send, restore it and Retry. Confirm exactly
   one note appears and the draft/other messages are intact.
6. Play received CHH and FHH notes. Test pause, seek near start/end, 1x/1.5x/2x and
   starting a second note. Confirm no autoplay and useful loading/failure/retry states.
7. Test speaker, wired headset if available and Bluetooth. Lock/unlock the device and
   switch conversations while audio is active; no stream/object URL may remain live.
8. Test hardware Back with keyboard, live recorder, locked recorder and preview. The
   recorder/preview closes before navigation. Repeat with gesture and three-button
   navigation in portrait and landscape.
9. Revoke conversation/link access from another session. New playback must fail
   privately without exposing a URL/path or revoking unrelated school data.
10. Disable Voice notes after sending. Confirm new recording disappears while the
    existing note remains playable to authorized participants.

Automated app-scoped `testDebugUnitTest`, `lintDebug` and `assembleDebug` passed on
2026-07-18. The delivered 95,893,704-byte APK has SHA-256
`b2fd998690250ac3167a6265b3bd4c0f6a2356d997d336ce6669294b545e324c`; package,
packaged CHH API endpoint and debug signature inspection passed. These gates do not
replace this device matrix.

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

### Slice 8 camera, gallery and protected viewe

1. In an active conversation choose one to five gallery photos, including a real
   HEIC/HEIF image where the device offers it. Confirm each preview reaches Ready.
2. Remove one selection, force one upload failure, then retry only that photo. Othe
   ready selections and the text draft must remain unchanged.
3. Use the camera control, deny permission once, then grant it and take a photo.
   Confirm denial is recoverable and the camera output is not publicly saved by CHH.
4. Send text-only, photo-only, and text plus five photos. Confirm the timeline uses
   thumbnails, preserves order, and one unavailable tile does not hide message text o
   neighboring photos.
5. Open each photo. Pinch 1×–4×, pan while zoomed, swipe only while unzoomed, and test
   double-tap, boundaries, viewer close and hardware Back. Back must close the viewe
   before returning to the inbox; keyboard-first behavior remains unchanged.
6. Background/resume during selection and after send. Confirm drafts/retries survive
   safe refresh and no duplicate message/photo appears.
7. Revoke the staff assignment/guardian link in a second session. A new thumbnail o
   full request must fail without exposing an old object URL after route reset.
8. Inspect network traffic: thumbnails only in the timeline; full bytes only afte
   open; no token in a URL; no storage key/path/public CHH URL.

Run this matrix on gesture and three-button navigation in English and Arabic/RTL.
The automated Gradle/build/signature checks do not replace it.

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

### S25i system navigation, IME and Back matrix

Run every applicable row on the same installed S25i APK in portrait phone layout.
Record device model, Android version, navigation mode and keyboard.

- [ ] Gesture navigation, keyboard closed: the complete textarea border and send
      button sit above the gesture area; tapping anywhere in the composer never opens
      Home/Recent Apps and never minimizes CHH.
- [ ] Gesture navigation, keyboard open: the composer remains fully above the IME,
      with no jump, clipped row or inaccessible send target.
- [ ] Three-button navigation, keyboard closed: the complete composer remains above
      Back/Home/Recent Apps and every composer tap stays inside CHH.
- [ ] Three-button navigation, keyboard open: the composer remains fully above the
      resized viewport and system controls.
- [ ] With draft text focused and a non-collapsed selection, press hardware Back once:
      the keyboard closes, the conversation remains open, and draft text, cursor and
      selection are unchanged.
- [ ] Press hardware Back again: the conversation closes to the messaging inbox and
      the app does not exit. Reopen the same conversation and confirm its draft is
      restored.
- [ ] Open the new-conversation overlay and press Back: the overlay closes before the
      active conversation/inbox or shell route changes.
- [ ] From the inbox, verify existing drawer/history/root Back behavior has no double
      handling or accidental exit. From a non-root route with no WebView history,
      verify Back returns safely to the app root.
- [ ] While typing, receive an FHH reply and exercise the 12-second poll, background/
      resume refresh and offline/online refresh. Draft, focus, cursor, selection,
      optimistic rows, reading position and **New messages** behavior must remain
      intact.
- [ ] Switch conversations and return; each unsent draft must remain with its own
      conversation and school membership. A successful send clears only its accepted
      draft; a failed send restores its text.
- [ ] Repeat the keyboard-open/closed sequence after app background/resume and afte
      restoring an authenticated session.

Automated S25i coverage verifies CSS inset/padding, `100dvh` resize, 48×48 send target,
focus/cursor/selection, keyboard → inbox Back order, draft restoration, polling,
optimistic send, new-message indication and native root/history policy. It cannot
prove OEM system-bar hit testing, actual IME visibility, camera/gallery UI or native
Google account selection; those rows require a physical device.

## Browser regression check

- [ ] In a desktop or mobile browser (not the APK), confirm the public homepage/foote
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

## S25w mobile shell and Quick Award messaging matrix

- [ ] On gesture navigation, open the teacher class list and scroll to the final
      class. The CHH logo/menu stay fixed below the status bar and the final button
      remains completely above the gesture area.
- [ ] Repeat with three-button navigation, then after background/resume and a
      status-bar size change. Confirm there is neither overlap nor a second blank
      inset below the content.
- [ ] Open a class and scroll its hero/context, roster, cards, and actions. The hero
      must begin below the fixed header; only the body moves and the final action is
      tappable above Android navigation.
- [ ] Repeat on School setup, another school-administration route, Reporting, a
      guardian route, and Messages. Confirm the shared header behavior and verify
      Messages has no doubled space below its sticky composer.
- [ ] With the keyboard open on a normal form and in Messages, confirm `adjustResize`
      still keeps focused controls/composer above the IME and hardware Back retains
      its keyboard-first behavior.
- [ ] From a class roster open Quick Award for a student with authorized guardians.
      Tap **Message guardians** and confirm the already-active student/guardian thread
      opens with the correct school/class/assignment context and no duplicate thread.
- [ ] Send text, one protected photo, and one protected voice note through the reused
      composer. After each successful send or explicit thread back, confirm the same
      class, student, and Quick Award overlay return with its prior mode intact.
- [ ] Test a school with messaging disabled, a student with no authorized guardians,
      and a teacher whose assignment was revoked. The action must be disabled or fail
      calmly with the clear localized reason and must not create a thread.
- [ ] Repeat the shell and shortcut checks in Arabic/RTL. Confirm labels, logical
      back direction, mixed-direction names, focus order, and minimum tap targets.

## S26c physical-device acceptance matrix

Use the fresh S26c development APK. Run the navigation checks once with gesture
navigation and once with three-button navigation; record screenshots at the final
scroll position.

- [ ] On the teacher class list, scroll to the final class button. Its complete
      outline and the normal gap below it must be visible above Android navigation.
- [ ] Open a long class/student grid and scroll to the final student card. The card
      and its last action must be fully tappable above Android navigation.
- [ ] In School setup, scroll to the final setup card/control; in Reporting, scroll
      to the final filter/action. Both must finish above Android navigation without
      an excessive empty panel.
- [ ] On every route above, confirm the CHH header remains fixed below the status bar
      and the first content row is unchanged. Repeat after background/resume.
- [ ] Open Messages with the keyboard closed and open. Confirm the sticky composer
      retains exactly one bottom inset and no new blank spacer appears below it.
- [ ] For Bob (active FHH-linked guardians and an existing active staff/student
      conversation), open Quick Award and select **Message guardians**. Confirm the
      existing conversation opens and no second conversation is created.
- [ ] Explicitly close the conversation and confirm the same class, Bob and the same
      Quick Award mode return. Reopen, send a message, and confirm the same overlay
      state returns after the successful send.
- [ ] Repeat the Bob shortcut in Arabic/RTL. Also verify the calm unavailable state
      for disabled messaging, an invalid assignment and a student with genuinely no
      current CHH or FHH guardian.

## S26i messaging receipt checks

- [ ] In a narrow text, protected-photo and protected-voice bubble, confirm the tick
      stays beside the timestamp inside the outgoing bubble in English and Arabic/RTL.
- [ ] Verify one grey tick immediately after send, two grey after one eligible
      recipient device renders/acknowledges, and two blue after that recipient views
      the active conversation. Do not open the photo viewer or play voice for Read.
- [ ] Repeat with two family grown-ups. The first eligible adult's delivery/read is
      sufficient; no name, count, partial-read, purple or all-read state may appear.
- [ ] Keep a draft and voice playback active while the other device acknowledges.
      Within the normal poll interval, only the tick should change: draft, keyboard,
      focus, playback and scroll position must remain undisturbed.
- [ ] Toggle delivery/read visibility through all four combinations and confirm the
      visible state table without deleting evidence. Confirm an admin safeguarding
      view does not change ticks.
- [ ] Repeat foreground/resume, network loss/recovery, gesture navigation,
      three-button navigation and Android Back with the composer and tick footer.

## S26l Android school-message push checkpoint

- [ ] Install the checkpoint APK, sign in as an eligible staff member, read the
      explanation, grant Android notification permission, and confirm the normal and
      urgent School messages channels exist. Denying once must not cause repeated
      prompts; Settings must offer a recovery path.
- [ ] From FHH, send text, photo and voice school messages while CHH is foregrounded
      elsewhere, backgrounded and terminated. Confirm generic notification copy only,
      a shade entry/pop-up subject to device channel settings, and no content preview.
- [ ] Tap each state and confirm the correct conversation and explicit staff
      membership/Acting-as context, including a dual-role administrator/teacher.
      Expired or revoked access must return to safe login/inbox handling.
- [ ] Outside contact hours, confirm the message commits and appears when CHH is
      opened manually, while push remains held. At reopening, several held messages
      in one conversation must produce one bundled notification.
- [ ] Confirm provider acceptance, foreground display and tap do not advance receipt
      ticks. Only the existing participant render/view acknowledgements may do so.
- [ ] Log out before another send, then switch between eligible and ineligible
      accounts on one installation. The old account must receive no push; re-login and
      token refresh must restore only the authorized registration.
- [ ] Repeat in English and Arabic/RTL and record package, endpoint, version code,
      signer, byte size, SHA-256, device/Android version and result.

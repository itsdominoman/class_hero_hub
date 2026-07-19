# Staff messaging user manual

## Recording and playing voice notes

When your school has enabled Voice notes, press and hold the microphone to record.
Keep holding and slide horizontally toward Cancel to discard, or slide upward to lock
hands-free recording. In locked mode you can pause, resume or delete. Recording stops
automatically at three minutes; a note shorter than 0.6 seconds is cancelled.

After recording, preview the note before sending. You can play/pause, delete and
re-record, or send it as its own message. Voice cannot be combined with text, photos
or Urgent. If upload or send fails, use Retry—the app preserves stable retry identity
so a successful retry does not create a duplicate.

For received notes, select Play; audio is fetched privately at that moment. Seek with
the progress control and select 1x, 1.5x or 2x. Starting another note stops the first.
Use Retry for an unavailable/transient item. There is no autoplay or transcription.

Voice notes are school records. Record only relevant, appropriate content; follow the
school's consent, safeguarding, retention and escalation rules. Offer a text or other
accessible channel when audio is unsuitable. Turning the school switch off removes
the recorder for new messages but does not hide existing authorized records.

## Sending photos (Slice 8)

An active conversation can contain text, photos, or both. Choose the gallery button
to select several images or the camera button on Android to take one. Up to five
photos can be attached to one message.

Each selected photo shows its own state. Wait until every photo is Ready. You can
remove any selection or retry only a failed photo without losing the message draft or
other ready photos. A photo-only message is allowed; an empty message with no ready
photo is not.

Messages show protected thumbnails. Select a thumbnail for the full-screen viewer;
pinch or double-tap to zoom, pan while zoomed, and swipe between photos while at the
normal scale. Android Back closes the viewer first. If one photo is unavailable, use
its Retry control; the message text and other photos still work.

Photos are private school records. The app does not publish a media URL and strips
camera location/EXIF metadata before storing only protected display versions. Do not
use messaging photos for video, voice notes, PDFs or office documents; those types are
not supported. Current conversation access is checked again every time a photo loads.

**Availability:** development pilot only, for authorized United International School
teachers and administrators. Production is not enabled.

## Find and open messages

Choose **Messages** from the authenticated navigation. The entry appears only when
the global feature and your school's policy are both enabled and your current role is
eligible. The inbox identifies each student with current grade/class context, for
example `Bob Smith · KG1A`.

Use compose/search to find a student, guardian, teacher or administrator. Student
results include current grade/class. A conversation with parents is shared by the
currently authorized guardians for that student, but each incoming message identifies
the exact sender and relationship when the school record provides it, for example
`Dom Brown · Father`. Never infer which guardian sent an ambiguously labelled row.

The conversation header stays compact: the first line identifies the student and
class, for example `Bob Smith · KG1A`; the second shows your current context and the
number of active guardians, for example `Homeroom · 3 guardians`. On the first shared-
guardian conversation opened by an account, one combined notice explains guardian
visibility and authorized school safeguarding/administrative review. Choose **I
understand** to acknowledge it. The large notice then stays hidden and a shield button
in the header reopens the same notice, participant list, relationships and status.
The acknowledgement is stored as a content-free preference for that signed-in account
on that browser/device; it never stores participant names or message content. Clearing
browser/app web storage makes the notice appear again.

## Live conversation behavior

While an active thread is visible and the device is online, it checks for newer
messages about every 12 seconds. It also refreshes immediately when the browser regains
focus, the page becomes visible, the network returns, or the Android app resumes.
Refresh does not clear a draft, move the text cursor, remove composer focus, dismiss
the Android keyboard, or discard an optimistic retry.

If you are already near the bottom, new messages remain in view. If you have scrolled
up, the thread preserves your reading position and shows **New messages**; activate it
to move to the latest row. Polling pauses while hidden, backgrounded, or offline.

## Android composer and Back button

The Android composer stays above both gesture navigation and the three-button system
bar, with or without the keyboard. Tap only inside the visible message field or Send
button; a composer tap must not open Home or Recent Apps or minimize CHH.

The compact row keeps Gallery and Camera inside the rounded message field. The action
at the far edge shows a muted microphone placeholder while the draft is empty; voice
recording is not available. As soon as you type text or select a photo, that position
becomes Send. The same row supports text-only, photo-only and mixed messages.

Hardware Back follows this order:

1. If the keyboard is open, Back closes the keyboard and keeps the conversation open.
2. If the new-conversation overlay is open, Back closes the overlay.
3. Otherwise, Back from a conversation returns to the messaging inbox.
4. From the inbox, the existing app menu, route history and root behavior applies.

An unsent draft is retained when you return from a conversation to the inbox and then
reopen the same conversation. Drafts stay associated with their conversation and
school membership. Always confirm the draft before sending, particularly after
switching conversations. A successful send clears the accepted draft; a failed send
restores its text for retry.

## Context and privacy

Names and user-entered message text use automatic direction so mixed Arabic and
English remain readable. Grade/class, guardian relationship, teacher role and subjects
come from current CHH records; users cannot type or override these labels.

Messaging is a school record. Current assignment and guardian access are checked on
every request. Do not include unrelated private family information. Existing school
notices remain the broadcast channel; Messaging v1 has no groups.

## Current limits

This development pilot supports protected message photos, protected voice notes when
the school explicitly enables them, and compact delivery/read ticks under independent
school visibility controls. Contact-hours scheduling, push notifications/deep links,
safeguarding administration tools, and retention automation are not implemented. A
feature being present in the development APK does not mean it is enabled in production.

## Message guardians from Quick Award

From a class roster, open Quick Award for a student and choose **Message guardians**.
The shortcut recognizes both current CHH guardian accounts and current FHH-linked
parent identities. If you already have an active conversation for that student, CHH
opens that exact conversation; it does not create a second thread. Otherwise, the
normal protected messaging flow creates or reuses the conversation safely.

The shortcut keeps the class, assignment, student and Quick Award mode that you came
from. Explicitly close the conversation, or send a message successfully, to return to
the same student's Quick Award overlay. If school messaging is disabled, your current
assignment is no longer valid, or the student genuinely has no authorized CHH/FHH
guardian, CHH shows the existing unavailable state instead of opening a thread.

## Delivery and read ticks

Outgoing messages show a compact indicator beside their timestamp:

- one grey tick: CHH has sent and committed the message;
- two grey ticks: at least one eligible recipient's app rendered and acknowledged it;
- two blue ticks: at least one eligible recipient viewed it in the conversation.

One eligible family adult reading is enough. CHH does not show who read, how many
people read, a partial household state or an all-read state; family coordination is
not the school's responsibility. Incoming messages do not display your sender-side
receipt. The same rules apply to text, photo and voice-note messages, and playing or
opening media is not required for Read.

School administrators can independently switch **Show delivery receipts** and
**Show read receipts** in School messaging/compliance settings. Delivery defaults on
and Read defaults off. These audited, school-scoped controls change only what senders
see; individual delivery/read evidence remains retained internally. Safeguarding-only
administrator views never change participant receipts.

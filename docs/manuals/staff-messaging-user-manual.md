# Staff messaging user manual

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
announcements remain the broadcast channel; Messaging v1 has no groups.

## Current limits

This pilot is text-only. Messaging photos, final delivery/read indicators,
contact-hours scheduling, push notifications/deep links, safeguarding administration
tools, and retention automation are not implemented. A feature being present in the
development APK does not mean it is enabled in production.

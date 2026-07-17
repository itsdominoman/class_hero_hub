# Messaging v1 text hardening

**Status:** Slice 7, S25h, and S25i implemented and validated on development,
2026-07-17
**Architecture authority:** [`../planning/2026-07-messaging-v1-architecture-plan.md`](../planning/2026-07-messaging-v1-architecture-plan.md)
**Runtime state:** enabled for development testing only; CHH is enabled only for
United International School and FHH's development proxy flag is enabled. Production
remains disabled.

## Outcome and scope

Slice 7 closes the cross-repository authorization, lifecycle, concurrency,
pagination, performance, and browser-state gate for the text-only Messaging v1
foundation built in Slices 1–6. CHH remains the only message record. FHH remains a
bounded parent-authenticated proxy and keeps no message mirror.

This slice intentionally adds no schema migration and no new product capability.
It makes four small production-code corrections:

1. CHH recipient search now applies literal, escaped, database-side search before
   the bounded result cap. Student, Arabic student, guardian, and staff names can be
   found even when the matching row sorts beyond the first candidate page.
2. CHH FHH-integration recipient discovery scopes assignments to the linked
   student's current section/subject groups before the cap and fails closed with a
   private `404` when the linked student has been archived.
3. Closing a zero-message assignment thread preserves the schema's one-based access
   window instead of attempting an invalid `1..0` grant range.
4. FHH resolves all eligible parent actor identities for a capped linked-child set
   in one query, validates the exact provider/school namespace, and excludes inactive
   children from unified unread fan-out.

There are still no messaging photos, final user-facing receipt indicators,
contact-hours scheduler, notification/push bridge, safeguarding administration UI,
retention worker, Redis, WebSockets, SSE, Celery, or FHH message storage.

## Authorization and lifecycle review

The review covered every text endpoint family and every boundary through which a
parent request travels:

| Surface | Authentication and scope | Current-access revalidation | Failure behavior |
| --- | --- | --- | --- |
| CHH staff `/api/messaging/*` | CHH cookie or native bearer, explicit school and membership actor | active school, user, membership, role, student, enrolment/assignment, participant and access grant | private `403/404`; no cross-school enumeration |
| CHH guardian `/api/guardian/messaging/*` | CHH user auth plus explicit school/student `GuardianLink` | active user, school, student, guardian link and grant | private `403/404`; never broad FHH-style aggregation |
| CHH FHH integration `/api/integrations/fhh/links/{link_id}/messaging/*` | service bearer, per-link credential, short-lived actor assertion bound to link/method/path/body | active school, FHH link, student, external identity link, participant/grant | private terminal `404/409` or retryable upstream failure; no fallback link |
| FHH `/api/school-messages/*` | active parent cookie/bearer; cookie writes require CSRF | parent family, active child, exact active `SchoolConnection`, exact active school-scoped identity grant | private `404/409/502`; no sibling fallback and no raw CHH response |
| FHH child routes `/api/children/{child_id}/school/messages/*` | same parent auth plus exact family-child ownership | exact child connection and identity linkage | revocation clears protected client state; no alternate connection |

The following scenarios are covered by focused or existing regression tests:

- two schools and two families, multiple children, siblings at the same school and
  children at different schools;
- multiple active FHH parents and two CHH guardians with individual participant
  identity/read cursors;
- users holding teacher/guardian or teacher/admin-related roles without merging actor
  capabilities;
- active and expired assignments, former teacher removal, replacement-teacher new
  conversation, student archive, and school suspension;
- CHH guardian removal, FHH grown-up removal, unlink, parent deletion, and family
  deletion with durable lifecycle retry;
- stale/revoked parent state, revoked identity link, revoked FHH link, and a link
  revoked while a thread is open;
- swapped school, student, child, link, and conversation identifiers;
- forged subject/display name, expired/wrong-audience/wrong-link actor assertions,
  assertion replay, malformed/signed-cursor tampering, and literal SQL wildcard input;
- cookie CSRF and native/bearer authentication paths.

Former teachers lose ordinary access when their current assignment ends. A
replacement teacher creates a different conversation and cannot read the historical
thread. The still-authorized guardian can retain the closed read-only record within
the recorded grant window. Historical grants never substitute for current
authorization.

## Concurrency, idempotency, pagination, and outages

- PostgreSQL row locking allocates a strictly monotonic sequence per conversation.
- Two simultaneous unique sends commit sequences `1` and `2`.
- Two simultaneous attempts with the same `(conversation, participant,
  client_message_id)` converge on one sequence and return original/duplicate results
  without a second message.
- A client retains the same random client UUID when retrying an unknown-result send.
  Timeout after commit therefore reconciles to the committed row.
- Signed cursors bind actor, route family, school/link scope, and an exclusive
  sequence/activity boundary. A newly committed message does not reshuffle an
  already-issued message-history page.
- Malformed, expired, tampered, cross-actor, and cross-link cursors are rejected.
- A CHH outage yields a retryable FHH `502`; already rendered transient content may
  remain for an explicit retry. A revocation-like `403/404` clears thread content.
- FHH unified inbox/unread fan-out is capped at 20 eligible active linked children.
  One failed upstream returns a partial-failure indication; all failures return a
  retryable service error. FHH never substitutes a sibling's link.
- Lifecycle unlink/deletion remains local-first and durable through the Slice 1
  database outbox. Message transport is independent of lifecycle retry and FHH
  stores no school-message content.

## Query and development performance evidence

The representative CHH fixture contains 100 active student/staff conversations and
100 messages in one thread. On the containerized development SQLite regression
fixture:

| Operation | SELECT statements | Representative result |
| --- | ---: | --- |
| staff inbox, 50 rows | 26 maximum after S25h context projection | bounded independently of the 100-conversation population |
| staff unread count | 17 | set-based current-access and cursor resolution |
| message history, 50 rows | 24 | ordered sequences `51..100` |
| 12 repeated inbox requests | 20 each | observed p95 `136.52 ms` |

The timing is a development regression tripwire, not a production SLO. PostgreSQL
fresh-migration concurrency coverage separately validates the locking behavior.
Recipient discovery searches before its cap and roster/participant resolution remains
set-based; no per-guardian or per-conversation query loop was introduced.

The FHH 20-connection fixture records:

| Operation | FHH SELECT statements | CHH calls |
| --- | ---: | ---: |
| bulk actor resolution | 1 | 0 |
| unified inbox | at most 3 | 20, one per eligible link |
| unified unread | at most 3 | 20, one per eligible link |

Marking one child inactive reduces unread fan-out to 19 without affecting its
siblings. Network fan-out remains intentionally bounded because each link has a
distinct CHH authorization context.

## Browser, localization, RTL, and accessibility evidence

CHH Playwright coverage verifies:

- desktop thread deep link and stable optimistic send reconciliation;
- mobile Arabic RTL navigation and mixed Arabic/English content with `dir="auto"`;
- global/school feature disablement;
- closed/read-only, offline, and revoked-content-clearing states.

FHH Playwright coverage verifies:

- desktop and mobile aggregated parent inbox/thread/compose behavior;
- child/school context, exact sender, shared-guardian and safeguarding disclosures;
- English and Fusha Arabic, RTL chrome, mixed-direction content, stable retry;
- keyboard-accessible controls and accessible names;
- empty/loading/partial/offline/closed/read-only/revoked states;
- no protected thread body after link revocation.

Protected message state remains in memory only. Route teardown, logout, or revocation
clears it; no inbox row, participant identity, draft or message body is written to
local storage or IndexedDB. S25j adds only a versioned, content-free disclosure-
acknowledgement preference keyed by authenticated account ID.

## Validation and release gate

Validation performed for this hardening checkpoint includes:

- complete CHH backend suite (**398 passed, 1 skipped**) plus focused Messaging
  API/integration/lifecycle/auth regressions;
- clean CHH Alembic upgrade from an empty disposable PostgreSQL database through
  `e4f5a6b7c8d9`;
- PostgreSQL concurrent unique and duplicate-send test;
- CHH frontend type check, unit tests, EN/AR parity, production build, and focused
  Playwright;
- complete FHH backend suite including auth, school link, lifecycle, account deletion,
  grown-up, and push-token regressions (**344 passed**);
- FHH unit tests, EN/AR parity, production build, public/authenticated smoke, public
  visual-layout, and focused messaging Playwright flows. The wider authenticated
  visual harness retains pre-existing calendar-width and missing-resource findings
  outside the Messaging routes.

The original Slice 7 deployment stayed dark:

- CHH `MESSAGING_ENABLED=false`;
- FHH `SCHOOL_MESSAGING_ENABLED=false`;
- every `SchoolMessagingPolicy.enabled=false`.

A later pilot must still complete the policy/disclosure/operations approval described
by the architecture plan. Slice 7 does not authorize enablement by itself.

## S25h live-refresh and context hardening

Real-device testing found two usability defects after the Slice 7 gate: CHH's inbox
timer reopened the selected thread and remounted its composer, while FHH had no
active-thread timer. S25h corrects both without changing the CHH-authoritative data
model or adding real-time infrastructure.

The shared client contract is:

- poll a visible active conversation every **12 seconds** with `after_sequence` set
  to the highest known authoritative message sequence;
- keep one poll in flight, discard responses for an old actor/route epoch, and merge
  only additive rows by server ID/sequence;
- never replace the composer or its draft, focus, selection, or future attachment
  state during refresh;
- pause while `document.hidden`, offline, or backgrounded, then refresh immediately
  on `focus`, visibility restoration, `online`, and Capacitor `appStateChange` resume;
- preserve the user's reading position. Auto-scroll only within 96 px of the bottom;
  otherwise expose a localized, focusable **New messages** button;
- preserve optimistic rows and stable client UUID retry/reconciliation behavior.

The API accepts either the existing signed historical `cursor` or `after_sequence`,
never both. Delta pages are ascending and include `latest_sequence`; authorization is
revalidated on every request, so revocation still fails closed.

CHH is also the only source for the added context. Current enrolment/section data
produces `Student · grade/class`; exact guardian participant/sender data produces
`Name · relationship` where available; current dated assignments produce homeroom,
subject-teacher subject lists, or school-administration context. FHH may sanitize and
display these fields but clients cannot submit them. Queries are set-based and fixed
cost; the new context projection raises the staff-inbox ceiling to 26 SELECTs but is
still independent of conversation and guardian population.

Focused S25h validation passed 22 CHH messaging API/integration tests, 54 related
authentication/CSRF/assignment/roster/integration tests (1 skipped), 4 messaging
state/presentation unit tests, 6 protected update-photo tests, 1,133-key EN/AR parity,
clean Svelte checking and production build, and 5 focused Playwright browser/mobile
flows. The Playwright resume case proves draft text, focus and selection survive a
new incoming row and exercises the non-bottom indicator. No migration was added.

Development testing is now explicitly enabled: the CHH global flag is true, only
United International School has an enabled school policy, and the FHH development
flag is true. This is not a production enablement and does not implement photos,
final receipt indicators, contact-hours scheduling, notification delivery/push,
safeguarding administration, or retention cleanup.

S25h deployment protection used CHH pgBackRest full backup `20260717-054356F`
(`--pg1-user=classhero` was required to override a stale repository setting that
still names the removed `familyhero` role) and FHH backup `20260717-054333F`. Both
live databases were already at their heads (`e4f5a6b7c8d9` and `a2b3c4d5e6f7`), so
no migration ran.

Historical S25f/S25g dark-release evidence (preserved for audit and superseded by
the S25h development-pilot enablement described above):

- CHH full backup `20260717-000934F`; FHH full backup `20260717-000941F`;
- no-op Alembic head checks: CHH `e4f5a6b7c8d9`, FHH `a2b3c4d5e6f7`;
- rebuilt/restarted only the CHH and FHH backend services;
- health and current web surfaces passed, the existing FHH→CHH linked-school
  dashboard returned its complete protected bundle, and a real protected update
  thumbnail returned non-empty image bytes;
- authenticated FHH parent/children remained available, the lifecycle worker stayed
  healthy with no pending/retry rows, and anonymous dashboard/media/message access
  remained denied;
- CHH reported zero enabled school policies/conversations/messages and FHH reported
  no conversation/message mirror tables.

## S25i CHH Android safe-area and Back hardening

Real-device testing after S25h found that the CHH composer did not reserve Android's
bottom system inset. The messaging workspace also retained a 38-rem mobile minimum
height while the IME was open, and the manifest did not explicitly select resize
behavior. On gesture and three-button devices this could place the composer in the
system-navigation hit region, so a composer tap could invoke Home or Recent Apps.
CHH also lacked the native Back dispatcher already proven in FHH.

S25i keeps the text-only messaging contract and changes only presentation/native
navigation behavior:

- the composer is a sticky, non-shrinking flex child with bottom padding equal to its
  normal padding plus `env(safe-area-inset-bottom)` and a 48×48 send target;
- the mobile workspace can shrink with `100dvh`; the 38-rem minimum remains only at
  the `sm` breakpoint;
- Android declares `windowSoftInputMode="adjustResize"` and the native shell applies
  native-only interaction/overscroll rules without changing browser behavior;
- one Capacitor Back listener dispatches a cancelable route event. Focused editable
  content consumes Back first and dismisses the keyboard; the compose overlay is
  next; an open thread then returns to the inbox; existing mobile-menu/root/history
  behavior remains bounded and a non-root route never exits accidentally;
- draft state is lifted above the composer and retained per membership/conversation,
  so conversation → inbox → conversation does not silently discard an unsent draft;
  resize, polling and app-resume refresh continue to preserve focus, cursor,
  selection, optimistic rows and scroll intent.

Focused S25i validation passed 5 messaging state/policy unit tests, 6 protected-media
unit tests, 1,133-key EN/AR parity, clean Svelte checking and production build, and
6 focused Playwright flows. The Android-sized Playwright case injects a 24-pixel
bottom inset, verifies sticky placement/padding and the 48×48 target, simulates IME
resize, verifies focus/cursor/selection, then proves keyboard → inbox Back ordering
and draft restoration. Backend regression passed 40 messaging tests with one
PostgreSQL-only skip and 95 auth/school/report/update tests. App-scoped Gradle
`testDebugUnitTest`, `lintDebug`, `assembleDebug`, and `assembleDebugAndroidTest`
passed; the debug APK verifies with v1/v2 signatures.

Deployment used CHH pgBackRest full backup `20260717-073438F`, added no migration,
and rebuilt/restarted only the CHH frontend. Runtime remains at Alembic
`e4f5a6b7c8d9`, `MESSAGING_ENABLED=true`, with only United International School's
policy enabled. At verification time CHH held 3 conversations, 17 messages,
12 participants, 9 receipt events and 230 assertion-use rows. Production remains
disabled.

The verified S25i APK is
`/opt/apps/class_hero_hub/tmp/class-hero-hub-s25i-dev.apk`: 95,845,408 bytes,
SHA-256 `55c777e0e344f7777fb308e6cc7d9233f672c01f93ad5b12f6554cef82077834`,
package `com.classherohub.app`, native API
`https://class.familyherohub.com/api`. Physical-device gesture/three-button and
camera/auth checks remain mandatory before sign-off.

S25i adds no messaging photos, final receipt UI, contact-hours worker, notification
delivery/push, safeguarding administration UI, retention worker, or CHH guardian UI.

## S25j compact conversation header and disclosure

S25j is a frontend-only presentation change. Student conversations now use a compact
two-line header: `Student · grade/class`, then current staff context and active guardian
count, such as `Homeroom · 3 guardians`. The main header no longer repeats the full
guardian-name list.

The former separate guardian and safeguarding banners are one EN/AR combined panel.
It explains shared-guardian visibility and authorized school safeguarding/
administrative review, and exposes the full participant list, relationship and active
status. The first eligible conversation opens the panel until the user chooses **I
understand**. Thereafter a focusable shield button reopens it. The acknowledgement is
a versioned boolean local preference keyed by `/me` account ID; no participant or
message content is persisted, and different accounts sharing a browser do not share
the acknowledgement.

Focused validation passed 6 messaging presentation/state/Back tests, 1,147-key EN/AR
parity, clean Svelte checking, the production frontend build, and all 6 focused
Messaging Playwright flows. Browser coverage verifies the compact header, combined
notice, full details, acknowledgement, reload persistence, account isolation, Arabic
RTL, optimistic send, polling/draft preservation, Android layout/Back behavior and
revocation safety. Deployment rebuilt only the CHH frontend; no backend, migration,
database, configuration or APK action was included.

S25j adds no messaging photos, final receipt UI, contact-hours worker, notification
delivery/push, safeguarding administration UI or retention worker.

## Operator diagnostics

For a parent proxy failure:

1. confirm the FHH parent, child, connection, identity, and identity-link rows are
   active and belong to the same family/provider/school namespace;
2. inspect lifecycle outbox state without printing payload credentials;
3. distinguish terminal `404/409` scope/revocation responses from retryable `502`;
4. retry a send with the same client UUID but a fresh actor assertion;
5. never copy a sibling link token or actor assertion between requests.

For staff access after an assignment change:

1. verify the current dated assignment and membership;
2. expect the old conversation to close and disappear from former staff access;
3. expect replacement staff to create a new conversation;
4. do not change historical access grants manually or reassign old messages.

Logs and diagnostics must not include message bodies, service/link credentials, actor
assertions, FHH family/parent IDs, emails, device tokens, or raw signed cursors.

# CHH/FHH Messaging v1 architecture and implementation plan

**Status:** authoritative architecture and implementation plan; Slices 1–2 policy,
lifecycle, and CHH core-record foundations implemented through 2026-07-17. Public
messaging APIs, inboxes, and user messaging remain unimplemented.

**Audit date:** 2026-07-16

**Primary repository:** Class Hero Hub (CHH), `/opt/apps/class_hero_hub`

**Companion:** Family Hero Hub repository, `docs/planning/2026-07-fhh-school-messaging-integration-plan.md`
**Supersedes for messaging:** `docs/CLASS_HERO_HUB_MASTER_BLUEPRINT.md` §9/§19/S15 and any earlier statement that Messaging v1 is plain-text-only, has one `(student × teacher)` table without participant/access history, uses best-effort in-request notification delivery, or has no photo, contact-hours, receipt, safeguarding, FHH-parent-identity, or durable-outbox requirement.

This is the primary cross-repository source of truth for Messaging v1. It separates
verified current code from recommended architecture. Slice 1 provides disabled feature
flags, the CHH school policy row/API, opaque school references, minimized FHH identity
lifecycle state, and durable unlink/deletion synchronization. Slice 2 provides the
disabled CHH conversation/message record model, participant/access history, internal
receipt cursor/evidence groundwork, immutable audit, and safe sequencing service. It
does **not** provide public messaging APIs, photos, user-facing receipts, contact-hours
scheduling, notification delivery, push, inbox routes, native deep links, or messaging
UI.

## 1. Executive recommendation

Build Messaging v1 as a **CHH-authoritative school record**. CHH owns conversations, messages, protected photos, participant and access history, delivery/read evidence, policy, safeguarding, moderation, retention, audit, and the durable notification outbox. FHH remains a parent-authenticated protected client/proxy for explicitly linked children. It must not mirror message history or receive CHH credentials in a browser or native client.

The decisive architecture is:

```text
CHH staff/guardian clients                       FHH parent clients
        | cookie or native bearer                       | cookie or native bearer
        v                                               v
  CHH messaging API                              FHH school-messaging API
        |                                               |
        | authoritative rows                            | family/child/link check
        |                                               v
        +---------------- CHH integration API <--- FHH server
                              service credential + per-link credential
                              + short-lived server-signed parent actor assertion
```

Key decisions:

- Parent/teacher conversations are student-scoped and shared by all guardians who are currently authorized for that student, but every individual sender and reader remains attributable.
- A replacement teacher gets a new conversation. Historical messages are not reassigned. A former teacher loses ordinary access immediately when the assignment or membership ceases.
- FHH represents each parent with a random, school-scoped opaque subject reference plus a display name and locale. CHH does not receive the FHH family ID, parent database ID, email, home data, device token, or unrelated child data.
- Read and delivery state is per human participant, including each FHH parent. It is not one family-wide cursor. Sender-facing guardian receipts are aggregate (“a guardian”) by default.
- Parent messages are accepted and visible at all times. The default contact-hours rule holds only staff push/email notifications outside the school schedule; it does not hold or hide the committed message.
- “Sent” means committed by CHH. “Delivered” requires an authenticated client acknowledgement that the message was fetched/rendered. “Read” requires a participant thread-view acknowledgement. FCM acceptance is never shown as device delivery.
- Messaging v1 supports text and photos only, up to five photos per message. Existing CHH update-photo processing should be generalized or wrapped, not copied.
- Use foreground polling, focus/resume refresh, native push, and a database-backed outbox worker. Do not add WebSockets, SSE, Redis, Celery, RQ, or PostgreSQL `LISTEN/NOTIFY` as a durability mechanism in v1.
- FHH continues to own parent device tokens. CHH hands off minimal, idempotent notification events to FHH; FHH performs parent fan-out and FCM delivery. Device tokens never move to CHH.
- School admins have disclosed safeguarding access without impersonation. Each non-participant access requires a reason and creates immutable audit evidence. Safeguarding reads do not alter participant-visible receipts.

Messaging should be disabled by default, enabled only for pilot schools after policy, retention, safeguarding disclosure, FHH lifecycle sync, and operational worker readiness are confirmed.

## 2. Repository checkpoints and audit method

### Checkpoints inspected

| Repository | Required branch/checkpoint | Current branch/HEAD | Status and drift |
| --- | --- | --- | --- |
| CHH | `main` / `4b25971fa049bcaeb1184c92fdbfa28ba59b5195` | `main` / `4b25971fa049bcaeb1184c92fdbfa28ba59b5195` | Clean and tracking `origin/main`; no drift |
| FHH | `develop` / `c9e52feec30b9d2b1377159b71bf94a3de123fa5` | `develop` / `c9e52feec30b9d2b1377159b71bf94a3de123fa5` | Clean and tracking `origin/develop`; no drift |

The audit used read-only Git status/history/tree inspection, targeted source reads, migration and test inventory, dependency and Compose inspection, and repository-wide searches for messaging, receipts, push, scheduling, workers, real-time transport, media, retention, moderation, deletion, and navigation. FHH was inspected on `10.250.50.1`; a filtered local read-only working copy was used only to author documentation safely, then documentation files are synchronized back individually.

No application tests, migrations, builds, databases, services, containers, deployments, or native packages were run or changed during this audit.

## 3. Current architecture findings with exact source evidence

### 3.1 CHH current state

CHH is a FastAPI/SQLAlchemy/Alembic/PostgreSQL application with a SvelteKit static frontend and Capacitor Android shell.

- Route registration is in `backend/app/main.py:140-161`. It mounts auth, platform, school, teacher, guardian, and FHH integration routers. It mounts no messaging, notification, WebSocket, or SSE router.
- Browser and native auth converge in `backend/app/auth.py:get_current_user` at line 86. Cookie auth is checked before `Authorization: Bearer`; unsafe cookie-authenticated requests are protected by `validate_csrf_request` at line 197. Bearer requests do not rely on a browser CSRF cookie.
- School access helpers are `backend/app/school_scope.py:require_school_role` (line 86), `require_teacher_of` (line 158), and append-only action recording through `write_audit` (line 27).
- Set-based roster resolution already exists at `backend/app/rosters.py:resolve_rosters_for_students` (line 84). Messaging audience resolution must preserve this bounded-query discipline.
- Current school-domain models are in `backend/app/models_school/models.py`: `User` (line 9), `School` (23), `Membership` (41), `BranchCampus` (61), `AcademicYear` (95), `StaffAssignment` (240), `Student` (284), `Enrolment` (310), `GuardianLink` (482), `FhhLinkInvite` (514), `FhhLink` (533), `Announcement` (628), `AnnouncementRead` (674), `HomeworkItem` (690), `HomeworkItemCompletion` (737), `CalendarEvent` (752), `UpdatePost` (785), `UpdatePhoto` (811), and `AuditLog` (854).
- `School.timezone` exists and defaults to `Asia/Muscat`. Assignments and enrolments are date-bounded. Guardian and FHH links are independently revocable.
- The Alembic chain includes school tenancy, structure, staff assignments, students/enrolments, guardian onboarding, FHH integration, announcements/read rows, homework, updates/photos, calendar, behaviour context, and performance indexes. There is no messaging, participant, receipt, notification-outbox, device-token, or contact-hours migration.
- `backend/app/database.py:Settings` includes database, SMTP, and FHH integration settings. There is no Redis, worker-broker, or Firebase Admin configuration for CHH.
- `backend/requirements.txt`, `frontend/package.json`, and `docker-compose.yml` contain no Celery, RQ, Dramatiq, Redis, or CHH push foundation. Compose runs backend, frontend, PostgreSQL, and restore services; the current backend command is a single Uvicorn process.
- CHH Android has camera support and native bearer auth (`frontend/src/lib/nativeAuth.ts`; `frontend/src/lib/api.ts:70-75`), but no push-notification dependency, device-token API, FCM send service, or messaging deep-link intent filter.

CHH guardian access remains a real current surface. Guardian dashboard/content routes derive audience from the logged-in CHH `User` and may aggregate all active `GuardianLink` children. That is appropriate for CHH guardian UI but unsafe as an FHH messaging scope. FHH integration messaging must always resolve an explicit `FhhLink` and its student.

### 3.2 Existing CHH ↔ FHH boundary

`backend/app/routes/integrations_fhh.py` is a dedicated integration surface:

- `require_fhh_service` (line 51) validates the service bearer, feature flag, rate limit, and optional IP allowlist.
- `_link` (line 105) validates the active durable link and `X-FHH-Link-Token`.
- `_scope` (line 134) resolves the linked student roster with the shared set-based resolver.
- The dashboard is `GET /api/integrations/fhh/links/{link_id}/dashboard` at line 197.
- Protected update-photo full and thumbnail endpoints are at lines 262 and 278. Announcement/homework protected bytes use the same integration-only pattern.
- No service or link token is accepted in a URL.

`backend/tests/test_integrations_fhh.py` covers service/IP checks, one-time consume, link token enforcement, cross-school/student/revoked access, safe allowlists, bounded scope query count, protected photo behavior, and log redaction.

This confirms the correct trust direction: client → FHH → CHH. Messaging extends this pattern; it must not make FHH clients call CHH or reuse broad `/api/guardian/*` aggregation.

### 3.3 CHH protected media

`backend/app/update_image_service.py` already provides the required image safety foundation:

- 50 MB raw byte cap (`MAX_RAW_IMAGE_BYTES`, line 22) and 64-million-pixel decompression limit (line 34);
- EXIF orientation correction (`ImageOps.exif_transpose`, line 62);
- ICC conversion and metadata-free re-encoding;
- no upscaling;
- full display maximum 1600 px (`MAX_IMAGE_DIMENSION`, line 25), hard 1.5 MB output budget;
- thumbnail maximum approximately 400 px (`THUMBNAIL_MAX_DIMENSION`, line 28), hard 160 KB budget.

`backend/app/routes/updates.py` enforces five photos per post (line 37/280), processes raw bytes in memory, writes only derived outputs, removes partial files on failure, and serves protected media with `Cache-Control: private, no-store`, `nosniff`, and same-origin policy. `frontend/src/lib/protected-update-photo.ts` owns memory-only object URLs and revokes them on cleanup.

Messaging should extract a neutral protected-image service interface around this implementation, retaining the current update API behavior. Copying the pipeline into a second implementation would create avoidable security drift.

### 3.4 CHH navigation, time, and real-time foundations

- CHH has role-aware `/school`, `/teach`, and `/parent` navigation in `frontend/src/routes/+layout.svelte`, with shared API behavior in `frontend/src/lib/api.ts`.
- The guardian dashboard has visibility-aware polling; there is no equivalent messaging store or global unread source.
- School report code uses `zoneinfo.ZoneInfo`; school-timezone conversion is an established pattern.
- `CalendarEvent` types are event/test/reminder/trip/civvies/charity. There is no explicit holiday calendar model. Existing events are therefore not safe as the automatic source of closed days.
- Repository-wide search found no WebSocket, EventSource/SSE, Redis, Celery, RQ, Dramatiq, durable outbox, or PostgreSQL notification loop.

### 3.5 FHH current state

FHH is a separate FastAPI/SQLAlchemy/Alembic/PostgreSQL application with a SvelteKit frontend and committed Capacitor Android and iOS projects.

- `backend/app/models.py` defines `ParentUser` (line 40), `Family` (67), `Child` (141), `SchoolConnection` (162), and `DevicePushToken` (509).
- Several active `ParentUser` rows can share one `Family`. A child is family-owned. This means “the FHH parent” is not a sufficient identity.
- `SchoolConnection` stores `family_id`, `child_id`, provider, CHH `remote_link_id`, and the per-link secret server-side. A partial unique index permits one active connection per child/provider.
- `backend/app/auth.py:get_current_parent` (line 127) accepts cookie or bearer auth and rechecks parent/family status. `backend/app/routes/family_scope.py:get_family_child_or_404` (line 7) enforces family ownership.
- `backend/app/routes/school_connections.py:sanitize_dashboard` (line 122) reconstructs a closed allowlist. `_proxy_media` (line 300) checks parent, child, and active connection before using the server-side CHH client.
- `backend/app/services/chh_integration_client.py` uses a process-wide bounded async `httpx` pool (20 connections, 10 keepalive), service bearer and `X-FHH-Link-Token`, and never returns credentials to a client.
- Dashboard 401/404/410 can revoke a local durable connection; protected media failures deliberately do not revoke it. This is the correct separation to retain for messaging.
- FHH protected media is memory-only on the client (`frontend/src/lib/school-link-photo-media.ts`) and cleared on route/child lifecycle. `/school-link/[id]` supports focus/visibility refresh, image zoom/pan/swipe, and Android private attachment export through app cache and `FileProvider`.

The current parent page is 4,126 lines and the child page 2,752 lines. Linked-school access is child-scoped and deliberately quiet: a child context/modal action plus Settings → School connections; the main family dashboard has no large school module. Messaging should not be inserted into the monolith.

### 3.6 FHH push and lifecycle findings

FHH has a useful but incomplete push foundation:

- `DevicePushToken` stores parent/child owner, platform, FCM token, timestamps, and revocation.
- `backend/app/routes/notifications.py` registers/unregisters authenticated device tokens.
- `backend/app/services/push_service.py` lazily initializes Firebase Admin and sends best-effort per token. Invalid/unregistered tokens are revoked.
- `frontend/src/lib/native/push-notifications.ts` prompts only after explicit parent opt-in, registers Android FCM tokens or an iOS token through the first-party `FcmToken` plugin, and never logs raw tokens.

Current limitations:

- send calls are synchronous/best-effort from request flows, not backed by a durable outbox;
- notification action/tap deep-link listeners are not implemented;
- there are no parent notification preferences or server-stored locale fields;
- Android App Links cover `/child-link/`, not school messages;
- iOS Firebase code is present, but the repository does not contain evidence of a checked-in push entitlement/`aps-environment` capability;
- FHH’s in-process savings maturity loop in `backend/app/main.py` uses `asyncio.create_task`; it is not crash-safe or multi-worker-safe and must not be copied for messaging.

`backend/app/services/account_deletion_service.py:delete_family_for_parent` anonymizes family content and removes device tokens, but it does not revoke/tombstone `SchoolConnection` rows or notify CHH. This is a pre-Messaging lifecycle gap: family deletion must not leave an external messaging identity or valid CHH link silently active.

### 3.7 Historical Messaging S15 status

`docs/CLASS_HERO_HUB_MASTER_BLUEPRINT.md` §19/S15 proposed:

- one row per `(school, student, teacher membership)`;
- participants derived as teacher plus all active guardians;
- plain text, per-message `message_reads`, REST polling, best-effort email;
- no photos, quiet hours, sender-visible receipts, native push, external-parent mapping, access-history grants, moderation/export, or durable outbox.

That is useful historical context but is not adequate for the current CHH/FHH product or security boundary. This document supersedes it for Messaging v1.

## 4. Product decisions and rationale

| Decision | Recommendation | Rationale |
| --- | --- | --- |
| System of record | CHH only | School communications are school records; avoids dual-write conflicts and preserves current server-to-server boundary |
| Parent/teacher thread | Student-scoped, one current thread per student × staff membership | Gives guardians one shared school context while preserving exact staff identity |
| Guardian visibility | All currently authorized guardians share the thread; new grants start at the next message by default | Supports co-guardians without silently disclosing pre-link/custody history |
| FHH parent identity | Random school-scoped opaque subject, display name, preferred locale | Enough for attribution/localization; excludes family ID, email, home data, device tokens |
| Read state | Per human participant | Multiple FHH parents and CHH guardians cannot honestly share one family/link cursor |
| Teacher reassignment | Close old thread; create a new thread for replacement | No silent reassignment or historical exposure |
| Contact-hours default | Parent can send anytime; commit and show immediately; hold staff push/email outside schedule | Preserves safeguarding record and user agency without pressuring staff |
| Default schedule | Sunday–Thursday 07:30–15:00 in school timezone; Friday/Saturday closed; admin must confirm before enablement | Appropriate current Muscat pilot default, explicit rather than hidden |
| Receipt defaults | Delivery receipt visible; read receipt hidden; independently configurable | Honest basic feedback without making read pressure the default |
| Attachments | Text + up to five photos | Strong current use case and proven pipeline; other formats add security/viewer/storage scope |
| Safeguarding | Admin capability, disclosure, reason-required access, immutable audit, no impersonation | School-appropriate oversight with accountability |
| Edit/delete | No edits; no sender hard-delete; admin tombstone with original retained | Protects safeguarding integrity |
| Real-time | Focused polling/focus refresh + push | Fits current infrastructure and expected scale |
| Background work | Separate DB-backed outbox worker with leases/locking | Durable across restarts and safe under multiple replicas |
| FHH navigation | Dedicated school inbox aggregating linked children, plus per-child entry/filter | Obvious without turning home/family dashboard into a school dashboard |
| CHH guardian UI | Keep supported, explicit student-scoped messaging surface | Existing CHH guardian access is live and cannot be assumed obsolete |
| Parent push | FHH owns FCM tokens and dispatch; CHH sends minimal durable events | Prevents device/family data leakage into CHH |
| Broadcasts/groups | Announcements remain the broadcast channel; no messaging groups | Meets the explicit product boundary and avoids reply storms |

## 5. System-of-record comparison

### Option A — CHH sole system of record (selected)

CHH stores all school-message state. FHH fetches and mutates it only through protected per-link integration endpoints.

Strengths:

- one authoritative ordering, retention, moderation, legal hold, and audit trail;
- school tenancy and assignment/guardian models already exist in CHH;
- protected media remains in the existing CHH security domain;
- FHH home/family state remains separate;
- failures in FHH cannot create conflicting message copies;
- the same core supports CHH staff, CHH guardians, and FHH parents.

Costs:

- FHH needs an explicit external-parent identity protocol;
- parent push needs a reliable cross-service handoff;
- foreground message reads depend on the FHH→CHH integration path.

Those costs are resolvable with small boundary tables and an outbox bridge; they are materially lower than dual ownership.

### Option B — CHH authoritative with a mirrored FHH copy (rejected)

A mirror would require message/content/media replication, dual receipt reconciliation, tombstone propagation, retention/hold coordination, conflict behavior during partition, and replay-safe ordering. It would also put school records in the family database and make family deletion semantics collide with school retention. Offline reading would improve, but permanent school-message storage in FHH contradicts data minimization and the current no-persistent-school-media direction.

If future offline requirements justify a cache, use encrypted, bounded, expiring client-side metadata/content under an explicit policy. Do not create a second system of record.

### Option C — separate shared messaging service (rejected for v1)

A new service would need its own tenancy, identity, auth, migrations, media protection, worker deployment, backups, monitoring, and operational support. CHH and FHH would both become clients, while school assignment, guardian link, and safeguarding decisions still originate in CHH. It adds a distributed authorization problem without reducing current complexity.

Reconsider only if messaging becomes a separately staffed multi-product platform with independently scaled traffic.

### Comparison matrix

| Criterion | A — CHH sole record | B — CHH + FHH mirror | C — shared service |
| --- | --- | --- | --- |
| Privacy/data minimization | Best; school data stays CHH-side | Worse; school history copied into family DB | Depends on a new identity/tenant boundary |
| Current trust boundary | Direct extension of existing FHH integration | Requires replication credentials/contracts | Requires both apps to trust a new service |
| Source consistency | One order/tombstone/hold source | Reconciliation and split-brain risk | One source, but authorization remains distributed |
| Parent/staff identity | CHH internal + minimal FHH external mapping | Same mapping plus mirror identity | New global identity mapping required |
| Delivery/read state | One participant cursor/event ledger | Dual cursor synchronization | Central, but both apps must submit/consume it |
| Offline behavior | Memory/session only in v1 | Better offline copy, at high privacy/consistency cost | Depends on extra client cache design |
| Protected media | Reuses CHH pipeline/endpoints | Requires copying or remote indirection | New media store/proxy |
| Quiet hours/outbox | One CHH policy/outbox | Scheduling and copy timing can diverge | Central scheduler, new operations |
| Parent push | Minimal CHH event → FHH-owned tokens | FHH can trigger locally but must reconcile authority | Service still cannot own FHH tokens without leakage |
| Failure recovery | Durable CHH row + FHH event reconciliation | Complex replay/conflict/delete propagation | Durable if built, but entirely new platform |
| Scaling | Sufficient for pilot/early schools | More storage and writes | Highest potential, premature |
| Migration complexity | Lowest/additive | High dual-write/backfill | Highest identity/data migration |
| Operations/support | Two existing apps + small workers | Two databases with mirrored incidents | Third deploy, backup, on-call surface |
| Future multi-school/child | Natural CHH school tenancy; FHH aggregates links | Mirror expands per child/school | Possible, but requires recreating CHH tenancy logic |

## 6. Identity, conversation, and participant model

### 6.1 Identifier ownership and boundary

| Value | Owner | Crosses boundary? | Purpose |
| --- | --- | --- | --- |
| CHH `User.id` | CHH | No | CHH staff/guardian identity |
| CHH `Membership.id` | CHH | No | Staff role and school identity |
| CHH `GuardianLink.id` | CHH | No | Current guardian authorization source |
| CHH `FhhLink.id` | CHH | Yes, as current integration link ID already stored by FHH | Explicit child/student authorization |
| CHH opaque school reference | CHH | Yes | Lets FHH derive/reuse one parent subject per CHH school without exposing internal school ID |
| FHH `ParentUser.id` | FHH | No | Family account identity |
| FHH `Family.id` | FHH | No | Home/family ownership; never a CHH participant |
| FHH `SchoolConnection.id` | FHH | No | Parent/family/child proxy authorization |
| FHH school-scoped `external_subject_ref` | FHH | Yes | Stable pseudonymous parent identity within one CHH school |
| Parent display name | FHH | Yes, minimized snapshot/current value | Required attribution (“sent by …”) |
| Parent preferred locale | FHH | Yes | Notification/UI localization |
| Parent email, home children, home points, family settings, device tokens | FHH | No | Not necessary for school messaging |

FHH should add a `school_messaging_identities` row per `(parent_user_id, provider, remote_school_ref)`. `external_subject_ref` is a random UUID generated by FHH, not a hash of email or database IDs. Reusing it for siblings at the same school prevents duplicate parent identities while preventing cross-school correlation.

FHH must also synchronize the minimized current parent roster for each SchoolConnection:
on link activation it provisions every active family parent’s school-scoped subject/display
name/locale and a per-connection grant; grown-up add/remove, name/locale change, unlink,
parent deletion, and family deletion produce durable incremental lifecycle events. This is
necessary so a parent who was already authorized when a teacher sent a message can read
that message even if they had never opened messaging before. The sync reveals only that
the named opaque subjects are authorized guardians for the linked student—information CHH
must know to govern the thread—and no FHH family ID, email, device token, or home data.

Every FHH messaging request must include, server-to-server:

1. existing FHH service bearer;
2. current per-link secret;
3. a short-lived signed actor assertion in a header, never a URL.

Recommended assertion claims:

```json
{
  "iss": "fhh",
  "aud": "chh-messaging",
  "sub": "<school-scoped opaque parent subject>",
  "link_id": 123,
  "display_name": "Mariam Al ...",
  "locale": "ar",
  "iat": 1784170000,
  "exp": 1784170300,
  "jti": "<random uuid>"
}
```

Use a dedicated assertion signing secret/key, not the service bearer. CHH validates issuer/audience/time/link binding, rejects replayed `jti` values for unsafe operations, and upserts only the minimized external participant. The FHH browser cannot choose or forge `sub`, display name, or link.

For idempotent retries, replay protection applies to the request/action pair: the same `jti` may be accepted only with the same idempotency key and request digest during its short window; a different payload is rejected.

### 6.2 Conversation kinds

1. `student_staff`
   - subject student required;
   - one primary staff membership required;
   - shared guardian side;
   - teacher or school admin may be the primary staff participant;
   - unique current conversation per `(school, student, staff membership)`.

2. `staff_direct`
   - exactly two ordered staff memberships;
   - used for admin ↔ teacher and permitted staff-to-staff direct communication;
   - no guardian participant and no student required;
   - no staff groups.

3. `guardian_direct`
   - one staff membership and one individual internal or external guardian identity;
   - used for a genuinely general school matter;
   - optional `subject_student_id` for a student-related but private guardian-specific matter;
   - FHH access still requires an explicit active link in the same school. If `subject_student_id` is present, it must equal the linked student.

Parent initiation defaults to `student_staff`. “Contact school office” may create a `student_staff` thread with a configured office/admin membership. `guardian_direct` creation should be staff/admin-controlled in v1 to avoid duplicate general threads.

### 6.3 Shared guardians and access history

The conversation is shared; authorization is not inferred forever.

- At conversation creation, all then-active CHH `GuardianLink` rows and active `FhhLink` rows are eligible from sequence 1.
- A guardian authorized later receives an access grant with `visible_from_sequence = conversation.last_message_sequence + 1` by default.
- An admin may explicitly grant earlier history only with a reason, immutable audit event, and disclosed UI.
- Revocation closes the grant immediately. A revoked guardian cannot access even historical messages through ordinary endpoints.
- Remaining active guardians keep their own access and receipt cursors.
- FHH synchronizes participant/grant rows for all current active parents when the link is
  activated and whenever family membership changes. A first access may refresh display/locale,
  but it must not be the event that decides whether an already-authorized parent can see an
  earlier teacher message. Teacher-originated notification fan-out still targets the active
  `FhhLink`; FHH sends only to parents whose per-connection identity grant is active/synchronized.
- A message from one guardian is visible to other guardians who have a valid grant for that sequence. The sender’s exact display name is shown; “the parent” is never used as an identity assumption.

### 6.4 Assignment and role lifecycle

- Every staff request revalidates active membership and, for `student_staff`, a current qualifying `StaffAssignment` or school-admin capability.
- Assignment end, teacher suspension, membership revocation, or school departure closes ordinary staff access immediately.
- The conversation is marked `closed_assignment_ended`; guardians with current links retain read-only access to their authorized sequence range.
- A replacement teacher gets a new `student_staff` conversation. Old messages are never silently reassigned.
- A school admin participating as the named staff member is different from an admin safeguarding viewer.
- Admin role removal ends admin capabilities; any separately valid teacher/guardian role remains.
- A teacher who is also a parent selects an explicit actor context. Staff and guardian participant records and read cursors remain separate. The API rejects sending a message to oneself in the same role/context.
- Student class transfer ends conversations whose staff authorization depended on the prior assignment and permits new conversations for current staff.
- Student archive closes conversations. Hard deletion is not a routine messaging lifecycle.
- School suspension blocks all ordinary messaging access and dispatch; committed rows remain. School archival/deletion follows export, retention, and legal-hold policy.

### 6.5 Cross-branch readiness

Current school administration is school-wide with optional `Membership.branch_campus_id`. Every messaging row remains `school_id` scoped. Policies and conversations may carry nullable `branch_campus_id` for future local administration, but v1 authorization must not infer branch restrictions that the current role model does not enforce. Future branch-local access must be additive and tested before enablement.

## 7. Exact data model, constraints, and indexes

The following is the recommended target schema. Existing CHH primary keys are integers; new high-volume append tables may use `BIGINT`. All timestamps are timezone-aware UTC. Human display uses school timezone at the edge.

### 7.1 Core CHH tables

#### `school_messaging_policies`

One row per school.

| Column | Type / nullability | Notes |
| --- | --- | --- |
| `school_id` | `INTEGER PK FK schools.id ON DELETE RESTRICT` | Tenant |
| `enabled` | `BOOLEAN NOT NULL DEFAULT false` | Master rollout flag |
| `guardian_replies_enabled` | `BOOLEAN NOT NULL DEFAULT true` | School-wide guardian reply switch |
| `delivery_receipts_visible` | `BOOLEAN NOT NULL DEFAULT true` | Presentation only |
| `read_receipts_visible` | `BOOLEAN NOT NULL DEFAULT false` | Presentation only |
| `allow_staff_out_of_hours_opt_in` | `BOOLEAN NOT NULL DEFAULT false` | School precedence |
| `teachers_may_mark_urgent` | `BOOLEAN NOT NULL DEFAULT false` | Admin always controlled separately |
| `notification_preview_mode` | `VARCHAR(24) NOT NULL DEFAULT 'generic'` | `generic`, `sender_only`, `body` |
| `retention_days` | `INTEGER NOT NULL DEFAULT 2557` | Provisional seven years |
| `email_mode` | `VARCHAR(16) NOT NULL DEFAULT 'off'` | `off`, `immediate`, `digest` |
| `policy_version` | `INTEGER NOT NULL DEFAULT 1` | Optimistic policy/audit version |
| `created_at`, `updated_at` | `TIMESTAMPTZ NOT NULL` | |
| `updated_by_membership_id` | `INTEGER NULL FK memberships.id ON DELETE SET NULL` | |

Checks: receipt booleans independent; `retention_days BETWEEN 30 AND 36500`; preview/email enums. Policy updates create an immutable messaging audit event.

#### `school_contact_windows`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `BIGINT PK` | |
| `school_id` | `INTEGER NOT NULL FK` | |
| `weekday` | `SMALLINT NOT NULL` | ISO Monday=1 … Sunday=7 |
| `start_local` | `TIME NOT NULL` | |
| `end_local` | `TIME NOT NULL` | Equal is invalid; end before start means crosses midnight |
| `is_active` | `BOOLEAN NOT NULL DEFAULT true` | |
| `created_at`, `updated_at` | `TIMESTAMPTZ NOT NULL` | |

Unique `(school_id, weekday, start_local, end_local)`. Index `(school_id, weekday) WHERE is_active`.

#### `school_contact_exceptions`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `BIGINT PK` | |
| `school_id` | `INTEGER NOT NULL FK` | |
| `local_date` | `DATE NOT NULL` | School-local date |
| `kind` | `VARCHAR(16) NOT NULL` | `closed`, `custom` |
| `start_local`, `end_local` | `TIME NULL` | Both required only for custom |
| `label`, `label_ar` | `VARCHAR(160) NULL` | Holiday/exception display |
| `created_by_membership_id` | `INTEGER NULL FK` | |
| `created_at`, `updated_at` | `TIMESTAMPTZ NOT NULL` | |

Unique `(school_id, local_date)`. Checks enforce null times for `closed` and both times for `custom`. Existing `CalendarEvent` rows are not imported automatically.

#### `messaging_external_participants`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `BIGINT PK` | |
| `school_id` | `INTEGER NOT NULL FK` | |
| `provider` | `VARCHAR(16) NOT NULL DEFAULT 'fhh'` | |
| `external_subject_ref` | `UUID NOT NULL` | Opaque school-scoped identifier |
| `display_name` | `VARCHAR(200) NOT NULL` | Current minimized attribution |
| `preferred_locale` | `VARCHAR(8) NOT NULL DEFAULT 'en'` | `en`/`ar` in v1 |
| `status` | `VARCHAR(16) NOT NULL DEFAULT 'active'` | `active`, `revoked`, `anonymized` |
| `anonymized_label` | `VARCHAR(80) NULL` | Stable lawful-history label |
| `first_seen_at`, `last_seen_at` | `TIMESTAMPTZ NOT NULL` | |
| `revoked_at`, `anonymized_at` | `TIMESTAMPTZ NULL` | |

Unique `(school_id, provider, external_subject_ref)`. No email, family ID, FHH parent ID, token, or device data.

#### `conversations`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `BIGINT PK` | |
| `public_id` | `UUID NOT NULL UNIQUE` | Opaque API identifier |
| `school_id` | `INTEGER NOT NULL FK` | |
| `branch_campus_id` | `INTEGER NULL FK branch_campuses.id` | Future scope only |
| `kind` | `VARCHAR(24) NOT NULL` | `student_staff`, `staff_direct`, `guardian_direct` |
| `student_id` | `INTEGER NULL FK students.id ON DELETE RESTRICT` | Subject/authorization student |
| `primary_staff_membership_id` | `INTEGER NULL FK memberships.id` | student/guardian direct |
| `staff_membership_low_id`, `staff_membership_high_id` | `INTEGER NULL FK memberships.id` | staff direct, sorted |
| `internal_guardian_user_id` | `INTEGER NULL FK users.id` | guardian direct |
| `external_guardian_participant_id` | `BIGINT NULL FK messaging_external_participants.id` | guardian direct |
| `context_class_section_id` | `INTEGER NULL FK class_sections.id` | Snapshot context at creation |
| `context_subject_group_id` | `INTEGER NULL FK subject_groups.id` | Snapshot context |
| `context_label`, `context_label_ar` | `VARCHAR(200) NULL` | Stable display snapshot |
| `status` | `VARCHAR(32) NOT NULL DEFAULT 'active'` | `active`, `closed_assignment_ended`, `closed_student_archived`, `closed_restricted`, `archived` |
| `last_message_sequence` | `BIGINT NOT NULL DEFAULT 0` | Lock/ordering cursor |
| `last_message_at` | `TIMESTAMPTZ NULL` | Inbox order |
| `created_by_participant_id` | `BIGINT NULL` | Deferred FK added after participant table |
| `created_at`, `closed_at` | `TIMESTAMPTZ NOT NULL/NULL` | |
| `closed_reason` | `VARCHAR(64) NULL` | |

Checks by kind:

- `student_staff`: student and primary staff set; staff pair and guardian-direct targets null.
- `staff_direct`: both staff pair values set, low < high; all student/guardian-direct values null.
- `guardian_direct`: primary staff set; exactly one internal/external guardian set; student optional; staff pair null.

Partial unique indexes:

- `(school_id, student_id, primary_staff_membership_id) WHERE kind='student_staff' AND status='active'`;
- `(school_id, staff_membership_low_id, staff_membership_high_id) WHERE kind='staff_direct' AND status='active'`;
- internal and external guardian-direct unique keys including nullable student, normalized with separate partial indexes for `student_id IS NULL` and `IS NOT NULL`.

Indexes:

- `(school_id, status, last_message_at DESC, id DESC)`;
- `(school_id, student_id, status)`;
- `(school_id, primary_staff_membership_id, status, last_message_at DESC)`.

#### `conversation_participants`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `BIGINT PK` | |
| `conversation_id` | `BIGINT NOT NULL FK conversations.id ON DELETE CASCADE` | |
| `participant_kind` | `VARCHAR(24) NOT NULL` | `staff`, `chh_guardian`, `fhh_parent` |
| `user_id` | `INTEGER NULL FK users.id` | CHH actor |
| `membership_id` | `INTEGER NULL FK memberships.id` | Staff actor context |
| `external_participant_id` | `BIGINT NULL FK messaging_external_participants.id` | FHH actor |
| `side` | `VARCHAR(16) NOT NULL` | `staff`, `guardian` |
| `display_name_snapshot` | `VARCHAR(200) NOT NULL` | Attribution fallback |
| `joined_at`, `left_at` | `TIMESTAMPTZ NOT NULL/NULL` | Participation history |
| `last_delivered_sequence` | `BIGINT NOT NULL DEFAULT 0` | Internal evidence cursor |
| `last_delivered_at` | `TIMESTAMPTZ NULL` | |
| `last_read_sequence` | `BIGINT NOT NULL DEFAULT 0` | Internal evidence cursor |
| `last_read_at` | `TIMESTAMPTZ NULL` | |

Exactly one actor shape:

- staff: user + membership, no external;
- CHH guardian: user, no membership/external;
- FHH parent: external, no user/membership.

Unique active participant per conversation/actor through partial indexes. Cursor checks: `0 <= delivered/read <= conversation.last_message_sequence` enforced in service/transaction; `last_read_sequence <= last_delivered_sequence` is not required because a read acknowledgement implies delivery and advances both atomically.

#### `conversation_access_grants`

This is the historical authorization ledger. It does not replace current-source revalidation.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `BIGINT PK` | |
| `conversation_id` | `BIGINT NOT NULL FK` | |
| `participant_id` | `BIGINT NULL FK conversation_participants.id` | Normally set; null only for a transient link-audience reconciliation row before required identity sync completes |
| `source_type` | `VARCHAR(24) NOT NULL` | `staff_assignment`, `school_admin_membership`, `guardian_link`, `fhh_link`, `manual_history_grant` |
| `staff_assignment_id` | `INTEGER NULL FK` | |
| `membership_id` | `INTEGER NULL FK` | |
| `guardian_link_id` | `INTEGER NULL FK` | |
| `fhh_link_id` | `INTEGER NULL FK` | |
| `valid_from`, `valid_to` | `TIMESTAMPTZ NOT NULL/NULL` | |
| `visible_from_sequence` | `BIGINT NOT NULL DEFAULT 1` | Prevents silent prior-history disclosure |
| `visible_through_sequence` | `BIGINT NULL` | Frozen on closure/revocation if useful |
| `grant_reason` | `VARCHAR(64) NOT NULL` | |
| `granted_by_membership_id` | `INTEGER NULL FK` | |
| `revoked_at`, `revoked_by_membership_id`, `revoke_reason` | nullable | |

Exactly one source FK must match `source_type`. Index `(conversation_id, participant_id, valid_from, valid_to)` and source-specific indexes. Access requires a matching grant **and** a currently valid source row unless the endpoint is an audited safeguarding path.

#### `messages`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `BIGINT PK` | |
| `public_id` | `UUID NOT NULL UNIQUE` | Opaque API ID |
| `school_id` | `INTEGER NOT NULL FK` | Denormalized tenant check |
| `conversation_id` | `BIGINT NOT NULL FK` | |
| `sequence` | `BIGINT NOT NULL` | Monotonic per conversation |
| `sender_participant_id` | `BIGINT NOT NULL FK` | Exact actor |
| `sender_display_name_snapshot` | `VARCHAR(200) NOT NULL` | Immutable attribution |
| `client_message_id` | `UUID NOT NULL` | Optimistic client ID/idempotency |
| `body` | `TEXT NULL` | At least body or ready media |
| `body_search` | generated/search vector or service-maintained `TSVECTOR` | Optional v1 staff/admin search |
| `state` | `VARCHAR(16) NOT NULL DEFAULT 'active'` | `active`, `tombstoned` |
| `urgent` | `BOOLEAN NOT NULL DEFAULT false` | Permission checked |
| `created_at` | `TIMESTAMPTZ NOT NULL` | Server accepted time |
| `tombstoned_at` | `TIMESTAMPTZ NULL` | |
| `tombstoned_by_membership_id` | `INTEGER NULL FK` | |
| `tombstone_reason` | `VARCHAR(160) NULL` | Visible safe reason |

Unique `(conversation_id, sequence)` and `(conversation_id, sender_participant_id, client_message_id)`. Body length check: 1–10,000 characters after normalization when present. Message rows are immutable except controlled tombstone columns. Database/service guards reject body/sender/created changes.

Sending locks the conversation row, allocates `last_message_sequence + 1`, inserts message/media links/audit/outbox in one transaction, then updates conversation activity.

#### `message_media`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `BIGINT PK` | |
| `public_id` | `UUID NOT NULL UNIQUE` | Upload/media ID |
| `school_id` | `INTEGER NOT NULL FK` | |
| `conversation_id` | `BIGINT NOT NULL FK` | Staged upload scope |
| `message_id` | `BIGINT NULL FK messages.id` | Null until attached |
| `uploaded_by_participant_id` | `BIGINT NOT NULL FK` | |
| `sort_order` | `SMALLINT NOT NULL` | 0–4 |
| `state` | `VARCHAR(16) NOT NULL` | `processing`, `ready`, `attached`, `failed`, `expired`, `deleted` |
| `storage_backend` | `VARCHAR(16) NOT NULL DEFAULT 'local'` | Future object storage |
| `full_storage_key`, `thumbnail_storage_key` | `VARCHAR(500) NULL` | Server-only |
| `content_type` | `VARCHAR(64) NULL` | Derived real type |
| `full_bytes`, `thumbnail_bytes` | `INTEGER NULL` | |
| `width`, `height`, `thumbnail_width`, `thumbnail_height` | `INTEGER NULL` | |
| `checksum_sha256` | `CHAR(64) NULL` | |
| `original_filename_safe` | `VARCHAR(160) NULL` | Display only; never a path |
| `metadata_stripped` | `BOOLEAN NOT NULL DEFAULT false` | |
| `created_at`, `attached_at`, `expires_at`, `deleted_at` | timestamps | |

Checks enforce at most five attached media per message in service plus a unique `(message_id, sort_order)` index; storage fields required only for ready/attached. Staged uploads expire after 24 hours. Authorization always checks the message conversation, never storage key possession.

#### `message_receipt_events`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `BIGINT PK` | |
| `conversation_id` | `BIGINT NOT NULL FK` | |
| `participant_id` | `BIGINT NOT NULL FK` | |
| `event_type` | `VARCHAR(16) NOT NULL` | `delivered`, `read` |
| `through_sequence` | `BIGINT NOT NULL` | Batched acknowledgement |
| `client_ack_id` | `UUID NOT NULL` | Idempotency |
| `device_session_ref` | `VARCHAR(96) NULL` | Opaque, non-token diagnostic |
| `occurred_at`, `recorded_at` | `TIMESTAMPTZ NOT NULL` | |

Unique `(participant_id, event_type, client_ack_id)`. Immutable. Receipt endpoint advances participant cursors with `GREATEST`; out-of-order or duplicate acknowledgements are safe.

#### `notification_outbox`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `BIGINT PK` | |
| `event_id` | `UUID NOT NULL UNIQUE` | Cross-service idempotency |
| `school_id` | `INTEGER NOT NULL FK` | |
| `message_id` | `BIGINT NOT NULL FK` | |
| `recipient_kind` | `VARCHAR(20) NOT NULL` | `chh_user`, `fhh_link` |
| `recipient_user_id` | `INTEGER NULL FK users.id` | |
| `recipient_fhh_link_id` | `INTEGER NULL FK fhh_links.id` | |
| `channel` | `VARCHAR(16) NOT NULL` | `push`, `email`, `in_app_event` |
| `template_key` | `VARCHAR(96) NOT NULL` | Localizable, no arbitrary body logging |
| `template_args` | `JSONB NOT NULL` | Safe allowlisted identifiers/labels |
| `deep_link` | `VARCHAR(300) NOT NULL` | Internal route only |
| `policy_version` | `INTEGER NOT NULL` | Decision provenance |
| `state` | `VARCHAR(24) NOT NULL` | `held`, `pending`, `leased`, `dispatched`, `provider_accepted`, `failed`, `dead`, `cancelled` |
| `eligible_at` | `TIMESTAMPTZ NOT NULL` | Notification scheduling only |
| `lease_owner`, `lease_expires_at` | nullable | Crash-safe worker |
| `attempt_count` | `INTEGER NOT NULL DEFAULT 0` | |
| `next_attempt_at` | `TIMESTAMPTZ NOT NULL` | |
| `provider_message_ref` | `VARCHAR(200) NULL` | Never called delivery |
| `last_error_code` | `VARCHAR(80) NULL` | Sanitized |
| `created_at`, `dispatched_at`, `provider_accepted_at`, `completed_at` | timestamps | |
| `dedupe_key` | `VARCHAR(240) NOT NULL UNIQUE` | Message/recipient/channel/bundle key |

Exactly one recipient target. Index `(state, next_attempt_at, eligible_at, id)` for dispatch and `(recipient_fhh_link_id, created_at)` for reconciliation. Message commit never depends on worker success.

### 7.2 Safeguarding/moderation/retention tables

- `messaging_restrictions`: school, scope type (`school_guardian_replies`, guardian, student, conversation), internal/external target, mode (`no_initiate`, `read_only`, `blocked`), reason, valid interval, actor, audit timestamps. Partial indexes on active scope.
- `message_reports`: reporter participant, message, category, note, state, reviewed by/at, resolution. Reporter cannot see internal admin notes.
- `message_moderation_actions`: message/conversation/participant target, action (`tombstone`, `restore`, `restrict`, `close`), public reason, confidential reason, actor/time. Immutable.
- `safeguarding_access_sessions`: admin membership, school, reason code, note, starts/expires, ended; no impersonation token. Every conversation/message view also emits an event.
- `messaging_legal_holds`: school/conversation/student/participant scope, reason, authority reference, start/release, actor. Retention cleanup excludes held rows/media.
- `messaging_exports`: school, requester, scope, status, encrypted artifact reference, checksum, expiry, counts, timestamps, failure code. Export artifacts are protected and time-limited.
- `messaging_audit_events`: append-only event ID, school, actor type/id, event type, entity references, safe metadata JSON, request correlation ID, occurred time. Prevent update/delete at ORM and preferably database trigger/permission level.

### 7.3 Minimal FHH tables/columns

FHH must not mirror `messages`.

1. Extend `school_connections` with:
   - `remote_school_ref UUID NULL` returned at consume/revalidated on dashboard;
   - lifecycle sync fields such as `chh_identity_sync_state`, `last_messaging_sync_at`.

2. Extend `parent_users` with `preferred_locale VARCHAR(8) NOT NULL DEFAULT 'en'`.

3. Extend `device_push_tokens` with `locale VARCHAR(8) NOT NULL DEFAULT 'en'` and optional privacy preference/preview mode reference. A token remains FHH-owned.

4. Add `school_messaging_identities`:
   - `id BIGINT PK`;
   - `parent_user_id FK`;
   - `provider`;
   - `remote_school_ref UUID`;
   - `external_subject_ref UUID`;
   - `display_name_snapshot`;
   - `preferred_locale`;
   - `status`, `revoked_at`, `anonymized_at`;
   - unique `(parent_user_id, provider, remote_school_ref)` and `(provider, remote_school_ref, external_subject_ref)`.

5. Add `school_messaging_identity_links`:
   - `identity_id FK school_messaging_identities.id`;
   - `school_connection_id FK school_connections.id`;
   - `status`, `visible_from_remote_sequence`, sync version/state, granted/revoked times;
   - unique `(identity_id, school_connection_id)`.

6. Add `school_notification_events`:
   - unique CHH `remote_event_id`;
   - `school_connection_id`;
   - safe template/deep-link metadata, no message body by default;
   - state/received/processed timestamps;
   - retention around 30–90 days.

7. Add `school_notification_dispatches`:
   - event, parent user, channel, state, attempts/lease/provider reference;
   - unique `(event_id, parent_user_id, channel)`.

8. Add `school_messaging_lifecycle_outbox` for parent-roster grants/revocations,
   unlink, account deletion, and identity anonymization events to CHH. This closes the
   current account-deletion gap without making local actions depend on CHH availability.

### 7.4 Sample row flows

#### 1. FHH parent sends to a teacher during contact hours

1. FHH authenticates ParentUser P, verifies family Child C and active SchoolConnection L.
2. FHH loads/creates school messaging identity E and signs an actor assertion bound to L.
3. CHH validates service token, per-link token, assertion, FhhLink L, student S, current teacher assignment A, replies policy, and restrictions.
4. CHH loads the already-synchronized external participant E′ and per-link access grant G
   (or safely reconciles a pending sync), then loads/creates the active
   `student_staff` conversation V and participant row PE.
5. CHH locks V, allocates sequence 21, inserts message M with `(V, PE, client_message_id)` uniqueness, advances V activity, inserts audit event, and creates staff push outbox row O as `pending`.
6. One transaction commits. FHH returns `Sent`.
7. Staff client later fetches/renders M and posts delivery/read cursors.

#### 2. FHH parent sends outside contact hours

Steps 1–5 are identical except O is inserted `held` with the next school opening in `eligible_at`. M is immediately visible. The response says the message was sent and the staff notification is held. At opening, the worker revalidates policy/access, bundles if necessary, and dispatches O exactly once.

#### 3. Teacher sends to both authorized guardians in one student thread

1. CHH validates the teacher assignment and locks V.
2. One message M is inserted; there is not one copy per guardian.
3. Active CHH GuardianLink targets produce CHH-user notification rows. Active FhhLink
   targets produce one FHH-link event row each, not one CHH row per device.
4. FHH receives its event and fans out only to current active ParentUsers with an active,
   synchronized identity-link grant for that SchoolConnection.
5. Each CHH guardian/FHH parent uses an individual participant and receipt cursor.
   Sender-facing UI reports aggregate guardian delivery/read according to policy.

#### 4. Admin sends a student-related message

An admin acting as the named participant creates/uses `student_staff` with the admin membership and student. It shares the authorized guardian side and normal receipt rules. An admin merely safeguarding another teacher’s thread does not send from or join that thread. A genuinely private individual guardian matter uses `guardian_direct`.

#### 5. Teacher assignment ends

Lifecycle service sets assignment-backed grants `valid_to/revoked_at`, marks the staff participant left, closes V as `closed_assignment_ended`, cancels undispatched ineligible notifications, and writes audit events. Guardians retain read-only access within their sequence grants. A replacement teacher receives a new V2 with no old messages.

#### 6. Guardian link or FHH school link is revoked

The source grant closes immediately and ordinary endpoints deny the revoked actor. Messages/media remain under school retention. Other guardian grants/cursors are unchanged. FHH unlink/family deletion first commits its local revocation plus lifecycle-outbox event, then retries CHH synchronization until acknowledged.

#### 7. Admin opens a thread for safeguarding

CHH validates school-admin role and an unexpired reason-bound safeguarding session, emits an immutable `safeguarding.thread_viewed` event with correlation metadata, and returns the thread through the safeguarding route. No conversation participant is inserted and no delivered/read cursor changes.

## 8. Access-control and lifecycle matrix

| Event/state | Ordinary access | Conversation effect | History/receipt effect | Required audit/sync |
| --- | --- | --- | --- | --- |
| Two active CHH guardians | Both share authorized sequence range | Same student/staff thread | Per-person cursors | Grant events |
| Multiple active FHH parents | Each derives own external identity through same active child link | Same thread | Per-person cursors; sender exact | Actor assertion/upsert |
| New guardian added | Access starts next sequence by default | Thread remains | No earlier history unless explicit grant | Grant + optional history reason |
| One guardian revoked | That guardian denied immediately; others remain | Thread remains | Historical rows retained internally | Revoke event |
| FHH school unlink | All FHH access through that connection stops | Thread may remain for other guardians | FHH identities retained/anonymized per lifecycle; no device data in CHH | FHH durable lifecycle outbox |
| FHH parent removed | Removed parent loses FHH auth; other family parents remain | No thread change | External participant grant closed for that parent identity when sync arrives | FHH identity revoke |
| FHH parent account deletion | No access | No thread deletion | Display name anonymized; school record retained | Durable lifecycle sync |
| FHH family deletion | All connections revoked locally and remotely | FHH grants closed | School messages retained under CHH policy | Must fix current deletion gap |
| CHH guardian link revoked | CHH guardian denied | Other guardians/FHH unaffected | Grant closed | Existing school audit + messaging audit |
| Teacher assignment ends | Former teacher denied | Old thread closes read-only for guardians | No transfer to replacement | Close reason/source |
| Teacher reassigned | New thread | Old thread unchanged | New staff sees no old messages | New grant/thread |
| Teacher suspended/departs | Denied immediately | Relevant threads close | Rows retained | Membership + messaging audit |
| Teacher also parent | Explicit actor context only | Separate participant roles | Separate cursors | Actor context logged |
| Admin role removed | Safeguarding/admin access ends | Participant threads only if another role remains | No receipt changes | Membership audit |
| Student class transfer | Prior assignment threads close | New current staff threads allowed | Prior authorized guardians retain read-only while link active | Roster/close events |
| Student school transfer/archive | Ordinary sending closes | Read-only or unavailable per link state | No hard reassignment | Archive/link workflow |
| School suspended | All ordinary access/dispatch blocked | State retained | Held notifications remain held/cancelled by policy | School lifecycle audit |
| School archived/deleted | Export/offboarding/retention process | No new messages | Hold/retention rules apply | Export + deletion authorization |
| Admin safeguarding view | Reason-bound read path | Admin is not added as participant | Does not advance delivery/read cursor | Immutable access event |
| Future branch-local admin | Only after explicit branch capability exists | Branch scope additive | No implicit current restriction | Cross-branch tests |

Revocation checks must occur in the same transaction/request that returns or writes content. Long-lived frontend state is advisory; a stale open thread receives 403/404 on the next poll/send and transitions to a calm read-only/unavailable state.

## 9. Contact-hours policy and state semantics

### 9.1 Recommended default

- Schedule: Sunday–Thursday, 07:30–15:00, school IANA timezone.
- Friday and Saturday closed.
- Parent/guardian may compose and send at any time.
- CHH commits the message immediately and makes it visible to authorized recipients.
- Staff who deliberately open the app can see it immediately.
- Staff push/email notifications for guardian-originated messages are held until contact hours reopen.
- Contact hours do not delay school-originated notifications to guardians.
- Parents cannot mark urgent or bypass the schedule.
- School admins may mark a message urgent. Teachers may do so only if the school explicitly enables it; default false.
- Personal staff opt-in outside hours is permitted only if the school enables that capability; default false. School policy wins.

Existing calendar events are not a reliable holiday source. Use explicit messaging exceptions. A future integration may suggest exceptions from a dedicated school-holiday model, but an ordinary event titled “Holiday” must not silently suppress delivery.

### 9.2 Policy-precedence truth table

| Sender | Contact window | Urgent | School permits personal override | Staff opted in | Staff notification |
| --- | --- | --- | --- | --- | --- |
| Staff/admin → guardian | Any | Any | Any | Any | Eligible immediately, subject to recipient channel preference |
| Guardian → staff | Open | No | Any | Any | Eligible immediately |
| Guardian → staff | Closed | No | No | No/Yes | Held until next open window |
| Guardian → staff | Closed | No | Yes | No | Held until next open window |
| Guardian → staff | Closed | No | Yes | Yes | Eligible immediately |
| Guardian → staff | Closed | Parent urgent attempt | Any | Any | Reject urgent flag; message accepted normally; notification held |
| Admin/system authorized urgent | Closed | Yes | Any | Any | Eligible immediately |
| Teacher urgent | Closed | Yes | Teacher urgent disabled | Any | Reject urgent flag or downgrade with explicit response; no silent bypass |
| Teacher urgent | Closed | Yes | Teacher urgent enabled | Any | Eligible immediately |

School suspension, recipient restriction, revoked link, disabled messaging, or invalid recipient always outranks time policy and cancels/blocks dispatch.

### 9.3 DST-safe calculation

Store weekly windows as local wall-clock times and evaluate with `ZoneInfo(school.timezone)`. For each outbox row:

1. convert current UTC to school-local;
2. apply the local-date exception first;
3. evaluate all weekly intervals, including prior-day intervals that cross midnight;
4. compute the next valid local opening;
5. convert that zoned instant to UTC, resolving ambiguous/nonexistent DST wall times with a documented policy:
   - ambiguous time: earliest valid instant for opening, latest valid instant for closing;
   - nonexistent time: advance to the next valid instant.

Asia/Muscat has no current DST, but tests must include a DST-observing zone.

### 9.4 Message versus notification sequence

```text
Parent taps Send at 21:10
        |
        v
FHH/CHH authorize + idempotency check
        |
        v
CHH transaction commits message (SENT/ACCEPTED)
  - message visible to authorized staff immediately
  - audit row committed
  - notification outbox row committed as HELD
        |
        +--> sender response: "Sent now; staff notifications resume at 07:30"
        |
next open window / policy reevaluation
        v
outbox HELD -> PENDING -> LEASED -> DISPATCHED
        |
provider accepts request (optional PROVIDER_ACCEPTED ops state)
        |
staff app fetches/renders and acks -> DELIVERED
        |
staff opens thread/message visible and acks -> READ
```

Do not label the message “queued” merely because its notification is held. If the network request has not completed, the client may show `Sending…`. After commit it shows `Sent`.

### 9.5 Policy changes and deduplication

- Worker re-evaluates authorization, restriction, and current policy immediately before leasing/dispatch.
- A policy that opens hours may release held rows earlier.
- A policy that closes hours may move undispatched eligible rows back to held.
- Already dispatched notifications are never recalled.
- Each row has a stable dedupe key. Reopening hours does not create another row for the same message/recipient/channel.
- A policy update increments `policy_version`; rows retain the version used to explain prior decisions but are evaluated against current policy until dispatched.

Recommended sender copy:

- EN: “Sent now. Staff notifications will resume at 7:30 AM on Sunday; staff can still see this message if they open the app.”
- AR draft: “تم الإرسال الآن. ستُستأنف إشعارات الموظفين الساعة ٧:٣٠ صباحًا يوم الأحد، ويمكن للموظفين رؤية الرسالة إذا فتحوا التطبيق.”

Arabic wording requires native-speaker review before release.

## 10. Delivery/read receipt semantics

### 10.1 State definitions

| User-facing/system term | Exact meaning |
| --- | --- |
| `Sending` | Client request is in flight; not durable evidence |
| `Failed` | Client knows the request was rejected/not committed. On timeout/unknown result, retry the same idempotency key instead of declaring failure |
| `Sent` / accepted | CHH committed the message and its audit/outbox rows |
| `Visible` | Current authorization allows the recipient to fetch it; this is not a separate sender icon |
| Notification `held` | Message is sent; only push/email eligibility is delayed |
| Notification `dispatched` | CHH/FHH sent a provider request |
| Provider accepted | FCM/APNs gateway accepted the request; operations evidence only |
| `Delivered` | An authenticated recipient client fetched/rendered the message and acknowledged through sequence N |
| `Read` | The participant opened the thread and the message was visible; client acknowledged through sequence N |
| Safeguarding viewed | Admin used safeguarding path; immutable audit only, never delivery/read |

No architecture available here can prove that a push appeared on a lock screen. The UI must never equate provider acceptance with delivery.

### 10.2 Tracking design

Use a hybrid:

- participant `last_delivered_sequence` and `last_read_sequence` for efficient inbox/unread/read queries;
- immutable batched `message_receipt_events` for security/audit evidence;
- notification outbox/provider states for operations, separate from participant receipts.

Clients batch acknowledgements with a UUID:

```json
{
  "event_type": "read",
  "through_sequence": 84,
  "client_ack_id": "uuid"
}
```

The server:

- authorizes the current participant and visible sequence range;
- caps the cursor at the latest authorized sequence;
- advances with `GREATEST`;
- for `read`, advances delivery to at least the same sequence;
- inserts one immutable event per idempotency key;
- ignores a lower/out-of-order cursor without moving state backward.

Multiple devices naturally converge on the maximum cursor. FHH never marks delivery merely because its backend fetched data from CHH; the parent client must acknowledge through FHH.

### 10.3 When the client acknowledges

- Delivery: after the active conversation response is rendered successfully. Inbox preview/polling alone does not acknowledge message delivery.
- Read: thread is foreground and the message has entered the visible message viewport. Batch the highest contiguous visible sequence after a short stability interval (for example 500 ms). Do not mark unseen messages below the scroll position.
- App resume/push tap triggers fetch, not automatic read.
- Offline acknowledgements may be retried with the same client acknowledgement ID after connectivity returns.

### 10.4 Sender-facing policy

Internal evidence is always retained. School toggles affect only presentation.

| Delivery visible | Read visible | Sender sees |
| --- | --- | --- |
| On | On | Sent → Delivered → Read |
| On | Off | Sent → Delivered |
| Off | On | Sent → Read |
| Off | Off | Sent only |

For shared guardians, show “Delivered to a guardian” / “Read by a guardian” based on at least one authorized guardian participant. Do not imply all guardians read it. Staff/admin may receive a policy-permitted participant detail view; guardians see aggregate staff/school wording. Safeguarding reads are excluded.

### 10.5 State diagrams and transition rules

Message/client state:

```text
Draft
  -> Sending
      -> Sent/accepted (CHH commit found)
      -> Failed-known (validation/auth/rejection; no commit)
      -> Outcome-unknown (timeout/connection loss)
            -> reconcile/retry same key -> Sent/accepted or Failed-known

Sent/accepted -> Tombstoned (admin moderation only)
```

There is no server message `queued` state for quiet hours. `Delivered` and `Read` are derived recipient evidence layered on an accepted message, not mutations of the message row.

Notification state:

```text
                 +---------------- policy closed ----------------+
message commit -> Held ------------------------------------------+
                 | policy opens                                  |
                 v                                               |
               Pending -> Leased -> Dispatched -> Provider accepted
                  ^          |           |
                  |          | crash     +-> Failed -> Pending(backoff)
                  |          +-> lease expiry
                  +-------------------------------+
                                  -> Dead (attempt limit)
                                  -> Cancelled (revoked/restricted/school disabled)
```

`Provider accepted` is terminal operational evidence for that attempt, not device delivery. A provider callback/error may still revoke a token or create a later failure metric.

Participant receipt state:

```text
delivered_cursor: 0 ---------------------------> N (monotonic max)
read_cursor:      0 ---------------------------> M (monotonic max)

read(M) atomically ensures delivered_cursor >= M
lower/duplicate/out-of-order acknowledgements do not move either cursor backward
safeguarding view changes neither cursor
```

End-to-end evidence:

```text
CHH commit
  -> recipient authorized to fetch
  -> notification row held/pending (optional awareness path)
  -> provider request accepted (not delivery)
  -> authenticated app fetch + client render ack = delivered
  -> thread foreground + visible-message ack = read
```

Idempotency keys:

- message: unique `(conversation_id, sender_participant_id, client_message_id)` plus `Idempotency-Key` bound to a request digest;
- staged upload: client upload UUID, conversation/uploader bound;
- receipt: `(participant_id, event_type, client_ack_id)`;
- CHH outbox/callback: stable `event_id` and unique `dedupe_key`;
- FHH bridge fan-out: `(remote_event_id, parent_user_id, channel)`;
- lifecycle sync: stable lifecycle event UUID/action/target;
- export/moderation actions: explicit request UUID where retryable.

## 11. Notification/outbox/push architecture

### 11.1 In-app and refresh

- Inbox/unread count is authoritative CHH state.
- Active thread polls every 10–15 seconds while visible; inbox polls every 30–60 seconds.
- Polling pauses when hidden/offline and refreshes immediately on focus, app resume, successful send, receipt acknowledgement, or push tap.
- Use one deduplicated request controller and retain stale content on transient failure.
- Do not introduce a global one-second badge loop or N+1 per-conversation requests.

### 11.1.1 Real-time/background option comparison

| Mechanism | v1 decision | Reason |
| --- | --- | --- |
| WebSocket | Defer | No current server/proxy/session foundation; reconnect/fan-out/replica operations add substantial scope for modest pilot benefit |
| SSE/EventSource | Defer | Browser cookie path is possible, but native bearer/reconnect and replica fan-out still need new infrastructure; one-way stream does not solve durable notification scheduling |
| Focused polling | Use | Fits current REST clients, bounded expected load, easy auth/revocation behavior, predictable fallback |
| Push-driven refresh | Use | Background awareness; client still fetches authoritative state after tap/resume |
| Database outbox + sweeper | Use | Required durability for quiet-hour schedules, retries, cross-service callbacks, and restarts |
| PostgreSQL `LISTEN/NOTIFY` | Optional later wake-up only | Notifications can be lost; never a work queue or source of truth |
| Redis + Celery/RQ/Dramatiq | Do not add in v1 | No existing operational foundation and current scale does not justify broker/worker complexity |
| FastAPI in-process loop | Reject | Duplicate execution under workers/replicas, restart gaps, and deployment coupling; FHH’s current savings loop is not a messaging precedent |

### 11.2 CHH staff push

CHH currently has no device-token or FCM support. Add an aligned foundation:

- CHH `device_push_tokens` keyed to CHH `User` plus app install/platform/locale, with revocation and last-seen;
- explicit native permission/settings flow;
- Firebase Admin service isolated behind the outbox worker;
- invalid-token revocation;
- generic previews by default;
- deep links such as `/messages/{conversation_public_id}` using opaque identifiers;
- no token/body in logs.

Do not send synchronously from the message route.

### 11.3 FHH parent push bridge (selected)

FHH owns parent tokens and current family membership. Use callback plus periodic reconciliation:

```text
CHH message transaction
   -> CHH notification_outbox (target=fhh_link)
   -> CHH worker, after policy eligibility
   -> authenticated POST to FHH /api/integrations/chh/messaging-events
   -> FHH transaction inserts unique school_notification_event
      + local dispatch rows for current active parents
   -> FHH returns 202/duplicate-safe 200
   -> FHH worker sends localized FCM using FHH-owned tokens

Recovery:
FHH periodically GETs CHH minimal notification-event feed after opaque cursor
   -> inserts missing events idempotently
   -> POSTs acknowledgement cursor/event IDs
```

Trust and credentials:

- FHH→CHH message content: existing FHH service bearer + per-link secret + actor assertion.
- CHH→FHH event callback: a separate CHH outbound bearer (or asymmetric signed request), optional mesh IP allowlist, timestamp, request ID, and HMAC/body digest.
- Reconciliation feed: dedicated service-level notification-feed credential, minimal metadata only. It does not expose message bodies or replace per-link content authorization.
- Secrets are never reused across directions.

Callback payload:

- event ID, CHH link ID, conversation/message opaque IDs;
- template key and allowlisted safe arguments (school display name, child display name, sender role/name only if preview policy permits);
- target route metadata;
- created/eligible timestamps and policy version;
- no FHH parent/family/device identifiers and no CHH/FHH secrets.

FHH maps the link to the active `SchoolConnection`, queries current active parents whose
`school_messaging_identity_links` grant is synchronized/active at dispatch time, localizes
per parent/token locale, and deduplicates `(event, parent, channel)`. If a parent is
removed before dispatch, no push is sent. If a new parent has not yet been granted in CHH,
they are not notified prematurely. If the connection is revoked, the event is cancelled
without revoking any unrelated link.

Why not callback-only: a prolonged FHH outage or lost response needs reconciliation.
Why not pull-only: scanning every active child link causes latency and unnecessary load, while a broad content feed would weaken per-link security.
Why not send tokens to CHH: it violates ownership and data minimization.

### 11.4 Preview privacy and localization

Default lock-screen preview:

- title: localized school name or “School message”;
- body: “New message about {child}” / Arabic equivalent;
- no message body.

School policy may permit sender name. Body previews should remain opt-in and device/user-overridable. Notification data payload contains opaque route IDs only, not tokens or message text.

### 11.5 Email and browser push

- Email is off by default for v1 pilot; enable immediate or digest only after templates, unsubscribe/preference behavior, and contact-hours scheduling are proven.
- Browser/PWA push is deferred. FHH native token infrastructure is further advanced and CHH has no web-push foundation. Adding a third delivery system during core messaging would increase operational risk.
- In-app unread, Android staff push, and FHH native parent push are the v1 delivery priorities. FHH iOS production push remains gated by Apple capability/provisioning verification.

### 11.6 Worker design

Run a separate worker service/process in each repository. Do not start it with FastAPI `asyncio.create_task`.

Worker claim query:

```sql
SELECT id
FROM notification_outbox
WHERE state IN ('pending','failed')
  AND eligible_at <= now()
  AND next_attempt_at <= now()
  AND (lease_expires_at IS NULL OR lease_expires_at < now())
ORDER BY eligible_at, id
FOR UPDATE SKIP LOCKED
LIMIT :batch;
```

Set a lease and commit before external I/O. Dispatch outside the claim transaction. Completion/update is conditional on lease owner. Exponential backoff with jitter, maximum attempts, dead-letter state, and manual replay tooling are required. Every external request carries the stable event ID. Duplicate execution must be harmless.

`LISTEN/NOTIFY` may later wake a sleeping worker, but the database row remains the durable source. Redis/worker framework is not justified for v1.

## 12. Photo/media architecture

### 12.1 Scope

Messaging v1 supports:

- UTF-8 text;
- JPEG/JPG, PNG, WEBP, HEIC/HEIF input converted to safe display output;
- up to five photos;
- thumbnail feed and full protected viewer.

Not in v1: PDF, DOCX, XLSX, voice notes, video. Those require different malware/content validation, viewers, export rules, storage budgets, and moderation.

### 12.2 Processing and upload transaction

Generalize `backend/app/update_image_service.py` behind a neutral protected-photo service:

1. authorize conversation send and create a staged media ID;
2. read at most 50 MB into bounded memory/temp handling;
3. decode with pixel limit, sniff real image type, correct orientation, normalize color, strip EXIF/ICC/GPS/metadata;
4. generate full image near 1600 px longest edge and thumbnail near 400 px, without upscaling;
5. write derived files under random server-owned storage keys;
6. insert/mark media `ready`;
7. client sends message referencing up to five ready staged IDs;
8. message transaction locks conversation, verifies same school/conversation/uploader and unexpired state, inserts message, attaches media, and commits;
9. sweeper removes unattached staged media after 24 hours and partial/failed artifacts promptly.

Thumbnail failure fails that photo upload and removes the full derivative; it does not create a ready media row. A broken historical photo returns a safe unavailable response and does not break the message/thread payload.

### 12.3 Authorization and serving

- Staff/CHH guardian routes authorize the conversation dynamically.
- FHH media proxy authorizes parent → family child → active SchoolConnection → CHH per-link scope → conversation visibility.
- Full and thumbnail routes use opaque IDs, never storage keys or tokens.
- Responses: `Cache-Control: private, no-store, max-age=0`, `Pragma: no-cache`, `X-Content-Type-Options: nosniff`, `Cross-Origin-Resource-Policy: same-origin`, safe `Content-Disposition`.
- Access logs use route templates/correlation IDs and redact opaque media identifiers if existing logging convention requires it. Never log tokens, filenames containing identifiers, message bodies, or object URLs.

### 12.4 FHH browser/native behavior

- Reuse the memory-only cache ownership pattern in `frontend/src/lib/school-link-photo-media.ts`.
- Cache key includes parent-visible child/link, conversation, message, media, and variant.
- Clear object URLs on route destruction, child/link switch, logout/auth revocation, and explicit eviction.
- Do not use localStorage, IndexedDB, service-worker Cache Storage, public filesystem, or permanent offline school-media storage.
- Android camera/gallery uses Capacitor Camera/photo picker; uploads through FHH with parent bearer, then FHH streams/forwards to CHH without persistent raw storage.
- Viewer supports thumbnail → full upgrade, pinch zoom, pan, swipe, hardware Back, safe areas, and per-photo retry isolation.
- Safe filename is presentation-only; Android export, if later allowed for message photos, uses private app cache/FileProvider and short retention. Default v1 viewer need not offer permanent export.

### 12.5 Storage and retention

Local disk is sufficient for a pilot if monitored. Keep `storage_backend` and opaque keys so S3-compatible private object storage can replace local files without API changes. Retention cleanup deletes derived files only after:

- message retention expired;
- no legal hold/export lock;
- tombstone/orphan rules permit;
- deletion is recorded and retryable.

Media cleanup failure never deletes or revokes a message/link. It raises an operational alert and retries.

## 13. CHH API and teacher/admin UX

### 13.1 API conventions

All public identifiers are opaque UUIDs. Pagination uses a server-signed opaque cursor containing the stable order tuple and request filters; clients cannot alter school, participant, or sequence scope.

Common behavior:

- browser: cookie auth plus CSRF for unsafe requests;
- native: bearer auth; no CSRF dependency;
- staff school selection: current `X-School-Id` convention;
- errors: 401 unauthenticated, 403 known authenticated policy denial, 404 for cross-school/resource enumeration, 409 lifecycle/idempotency conflict, 422 validation, 429 rate limit;
- private JSON: `Cache-Control: private, no-store`;
- idempotent send/create: `Idempotency-Key` header plus `client_message_id`;
- no token or credential in URL, response, analytics, filename, or UI error;
- bulk participant/search resolution is set-based.

### 13.2 Staff endpoint family

Recommended shared prefix: `/api/messaging`. Admins and teachers use the same route/component family; capabilities are returned explicitly.

| Endpoint | Auth/scope | Useful contract |
| --- | --- | --- |
| `GET /api/messaging/inbox` | current user + active staff membership for `X-School-Id` | Filters: status, unread, student, class, subject, participant, kind; cursor pagination ordered by `(last_message_at DESC, id DESC)`; returns safe preview, context, unread count, receipt policy, capabilities |
| `GET /api/messaging/unread-counts` | staff membership | One aggregate response: total and optional role/filter buckets |
| `GET /api/messaging/conversations/{public_id}` | dynamic participant grant or safeguarding session | Conversation metadata, participants, lifecycle state, policy/capabilities |
| `GET /api/messaging/conversations/{public_id}/messages` | same | `before_sequence`/signed cursor, descending DB query then chronological response; bounded page 30–50 |
| `POST /api/messaging/conversations` | teacher current assignment or admin role | Create/find deduped `student_staff`, `staff_direct`, or allowed `guardian_direct`; returns existing active conversation on identical key |
| `POST /api/messaging/conversations/{id}/messages` | current send grant, restrictions, policy | Body, staged media IDs, client message ID, urgent flag; same idempotency key returns original response |
| `POST /api/messaging/conversations/{id}/receipts` | participant only | Batch delivered/read cursor |
| `POST /api/messaging/conversations/{id}/close` | admin or lifecycle service | Controlled close reason; ordinary teachers cannot erase history |
| `GET /api/messaging/recipients/search` | staff membership | Query by parent, student, class, teacher/staff; server-enforced role/assignment scope; bounded results |
| `POST /api/messaging/conversations/{id}/media` | participant with send right | Multipart one photo; returns staged media metadata |
| `GET /api/messaging/.../media/{media_id}/thumbnail|full` | conversation view right | Protected bytes/private headers |

Search does not expose parent emails by default. It returns school-owned guardian display identity, student relationship label if available, source (`CHH guardian`/`FHH linked parent`) only when operationally useful, and ambiguity-safe context.

### 13.3 Policy, moderation, and safeguarding endpoints

Recommended school-admin prefix: `/api/school/messaging`.

- `GET/PUT /policy`: school admin; versioned optimistic update, full audit.
- `GET/PUT /contact-hours`: weekly windows/exceptions; validate timezone and overlaps.
- `GET/POST/DELETE /restrictions`: guardian/student/conversation reply/initiation restrictions.
- `GET /reports`, `POST /reports/{id}/resolve`.
- `POST /messages/{id}/tombstone`, optional controlled restore.
- `POST /safeguarding-sessions`: reason code + optional note, short expiry.
- `GET /safeguarding/conversations/{id}` and messages route: require active safeguarding session; no participant receipt effect.
- `POST /legal-holds`, `POST /exports`, `GET /exports/{id}`.
- `GET /operations/outbox` only for tightly authorized operational/admin roles; no message body/token output.

Platform admins do not automatically receive school-message browsing rights. Any future platform support access requires a separate time-boxed, school-authorized, audited model.

### 13.4 CHH guardian endpoints

Keep a CHH guardian surface under `/api/guardian/messaging`, but unlike existing aggregate dashboards, each conversation response must carry and enforce explicit school/student context.

- `GET /api/guardian/messaging/inbox?school_id=&student_id=`
- `GET /api/guardian/messaging/conversations/{id}`
- `GET .../{id}/messages`
- `POST .../{id}/messages`
- `POST .../{id}/receipts`
- protected media routes.

The backend may aggregate authorized conversations for convenience, but each row is authorized from a specific active `GuardianLink`; it must never convert the FHH integration into the broad CHH-user audience model.

### 13.5 Staff UX recommendation

Admins and teachers share `/messages` with role-scoped actions.

Desktop:

```text
+--------------------------------------------------------------------------------+
| Messages  [School selector]  [Search parent/student/class/staff]  [Compose]    |
+----------------------------+---------------------------------------------------+
| Filters                    | Sara A. · Grade 4A · Ms Noor                       |
| All  Unread  Closed        | Guardians: Mariam, Ahmed (shared thread)           |
|                            | Admins may review school communications [info]     |
| Sara · Ms Noor       2     |---------------------------------------------------|
| Last message preview       | 09:10 Mariam: ...                           Sent   |
|----------------------------| 09:14 Ms Noor: ...                   Read by a...  |
| Omar · School office       | [photo thumbnails]                                |
| ...                        |                                                   |
|                            | Contact-hours banner / restriction / closed state  |
|                            | [Add photos] [Message, dir=auto]          [Send]    |
+----------------------------+---------------------------------------------------+
```

Mobile:

```text
Messages                      [Compose]
[Search]
[All] [Unread] [Closed]
------------------------------------------------
Sara · Ms Noor                           2 unread
Grade 4A · Guardians
Last message...
------------------------------------------------

tap -> single conversation route
< Back      Sara · Ms Noor
Grade 4A · Shared with authorized guardians
[safeguarding disclosure]
messages...
[contact-hours notice]
[photo] [composer] [send]
```

Required states:

- skeleton loading, empty inbox, no search result;
- offline banner with retained messages;
- send retry using same idempotency key;
- closed/read-only thread with reason;
- participant/link/assignment revoked while open;
- one broken photo isolated;
- partial receipt/notification status worded honestly;
- deep-link target no longer available;
- rate limit and body/photo validation errors;
- keyboard focus, Escape, arrow/tab order, screen-reader live status for send.

Compose flow:

1. choose kind (student guardian, staff member, school office/general guardian only if permitted);
2. search within authorized scope;
3. choose student and current staff context;
4. server returns existing active thread or creates one;
5. show exactly which guardians share student-thread visibility;
6. no class/school “select all.” Broadcast CTA routes to announcements instead.

The conversation header should show current class/subject context but preserve creation-time context on closed historical threads. Avoid implying the current replacement teacher authored historical messages.

### 13.6 Component/state boundaries

Likely CHH frontend files:

```text
frontend/src/routes/messages/+page.svelte
frontend/src/routes/messages/[conversation]/+page.svelte
frontend/src/lib/components/messaging/
  InboxList.svelte
  InboxFilters.svelte
  ConversationHeader.svelte
  MessageTimeline.svelte
  MessageBubble.svelte
  ReceiptStatus.svelte
  MessageComposer.svelte
  PhotoPicker.svelte
  ProtectedPhotoViewer.svelte
  ContactHoursNotice.svelte
  SafeguardingDisclosure.svelte
frontend/src/lib/stores/messaging.ts
frontend/src/lib/messaging/api.ts
frontend/src/lib/messaging/polling.ts
```

The store owns inbox pages, active thread, optimistic messages keyed by client UUID, polling/focus state, receipt batching, and unread badge. Page components own route transitions/overlays. Protected object URLs have explicit cleanup.

## 14. FHH integration API and parent UX

### 14.1 CHH integration endpoints used only by FHH

All content endpoints require service bearer, per-link token, actor assertion, and active link/student scope.

| Endpoint | Contract |
| --- | --- |
| `GET /api/integrations/fhh/links/{link}/messaging/inbox` | Child-link-scoped conversations plus opaque parent-specific read/unread state; signed cursor |
| `GET .../conversations/{conversation}` | Validate conversation student equals link student, or general guardian-direct actor has same-school active link |
| `GET .../conversations/{conversation}/messages` | Allowlisted message DTO, signed cursor, no storage keys/internal IDs |
| `POST .../conversations` | Student-staff recipient selection from safe current staff list; idempotent find/create |
| `POST .../conversations/{id}/messages` | Parent actor derived from assertion; body/media/client ID |
| `POST .../conversations/{id}/receipts` | Parent actor derived from assertion; cursor acknowledgement |
| `POST .../conversations/{id}/media` | Photo upload proxy; same actor/link/conversation checks |
| `GET .../media/{id}/thumbnail|full` | Protected bytes |
| `GET .../recipients` | Current, link-student-scoped teachers/admin office options only |

Safe message DTO example:

```json
{
  "id": "opaque-uuid",
  "sequence": 42,
  "sender": {
    "side": "staff",
    "display_name": "Ms Noor",
    "role_label": "Teacher"
  },
  "body": "…",
  "photos": [
    {"id": "opaque-uuid", "thumbnail_available": true, "full_available": true}
  ],
  "sent_at": "2026-07-16T08:12:00Z",
  "status": {"kind": "sent"},
  "tombstone": null
}
```

FHH must reconstruct its own browser DTO from a closed allowlist as it does in `sanitize_dashboard`; it must not relay raw CHH JSON.

### 14.2 FHH parent-authenticated endpoints

Recommended API:

- `GET /api/school-messages/inbox`: aggregates across the current family’s children with active links by making bounded parallel/server-side CHH calls; supports child/school/unread filters and a federated signed cursor.
- `GET /api/children/{child_id}/school/messages/inbox`
- `GET /api/children/{child_id}/school/messages/conversations/{id}`
- `GET .../{id}/messages`
- `POST .../conversations`
- `POST .../{id}/messages`
- `POST .../{id}/receipts`
- `POST .../{id}/media`
- protected thumbnail/full proxy routes.

Every route:

1. authenticates current parent;
2. checks current family and child ownership;
3. loads the active `SchoolConnection`;
4. derives/loads the school-scoped messaging identity;
5. creates a server-side actor assertion;
6. calls CHH with service/link credentials;
7. sanitizes the response.

The browser request never includes `external_subject_ref`, CHH link ID, link token, service token, actor signing key, or parent identity claims.

Unified inbox aggregation must be bounded. For the current product (usually a small number of children), fetch one first page per active connection in parallel, merge by `(last_message_at, opaque stable tie-break)`, and encode per-connection continuation cursors inside an FHH-signed cursor. Cap active connections per request and measure fan-out. Do not create an FHH message mirror just to simplify pagination.

### 14.3 FHH navigation decision

Use a hybrid:

- dedicated `/school-messages` parent route aggregating all currently linked children;
- top-level/messages entry with unread badge in the authenticated parent shell, shown only when at least one active school connection exists;
- per-child “School messages” entry in the existing child action context;
- `/school-link/{child}/messages` may redirect/filter into `/school-messages?child=...`, or the child school dashboard may link to that filter.

This keeps school data visibly distinct from home points/rewards/calendar and avoids another large block on the main family dashboard. It is more discoverable than hiding all messages inside the school-profile page.

Do not put messaging state/UI into `frontend/src/routes/parent/+page.svelte`. Create a route and components.

### 14.4 FHH text wireframes

Mobile aggregated inbox:

```text
School messages                         [Unread 3]
[All children v] [All schools v]
[Search teacher/admin]
------------------------------------------------
Sara · United International School          2
Ms Noor · Grade 4A
Last message...
------------------------------------------------
Omar · School office                        1
...

Home and school messages are separate.
```

Conversation:

```text
< School messages
Sara · Ms Noor
United International School · Grade 4A
Shared with Sara's currently authorized guardians
School administrators can review school communications
------------------------------------------------
messages, dir=auto
[photo grid]
------------------------------------------------
Sent now. Staff notifications resume at ...
[camera/gallery] [Message] [Send]
```

Desktop:

```text
+---------------------------+-----------------------------------------------+
| School messages           | Sara · United International School           |
| Child/school filters      | Ms Noor · Grade 4A                            |
| inbox list + badges       | disclosure / timeline / composer              |
+---------------------------+-----------------------------------------------+
```

When one child has no school link, that child is absent from filters and gets a calm “Connect school to use school messages” entry only in child context/settings. If a link is revoked while open, retain already-rendered content only for the current memory session if policy permits, disable composer, clear protected photo URLs, and require reauthorization on any further fetch. Do not fall back to another child’s link.

### 14.5 FHH state and native behavior

Likely files:

```text
backend/app/routes/school_messages.py
backend/app/services/chh_messaging_client.py
backend/app/services/school_messaging_identity_service.py
backend/app/services/school_notification_bridge.py
frontend/src/routes/school-messages/+page.svelte
frontend/src/routes/school-messages/[conversation]/+page.svelte
frontend/src/lib/components/school-messaging/*
frontend/src/lib/school-messaging/store.ts
frontend/src/lib/native/school-message-deep-links.ts
frontend/src/lib/native/push-notifications.ts
frontend/src/lib/i18n/messages.ts
frontend/android/app/src/main/AndroidManifest.xml
frontend/ios/... capability/deep-link files as required
```

The route store owns only transient parent-visible school data. No permanent message/photo cache. Native push action listeners validate opaque route payloads, navigate through the FHH route, and let normal auth/link checks decide access. Cold-start and warm-resume delivery must be deduplicated, following the existing child-link handoff discipline without ever logging the full notification payload.

## 15. Safeguarding, moderation, retention, and audit

### 15.1 Visibility levels

1. Ordinary participant visibility
   - current, dynamically authorized staff/guardians;
   - constrained by sequence grant and restrictions.

2. School-admin safeguarding visibility
   - admin is not a participant;
   - requires a reason code (`reported_concern`, `student_safety`, `staff_supervision`, `legal_request`, `other`) and optional note;
   - short-lived safeguarding session;
   - every thread open, page fetch, export, and media access recorded immutably;
   - does not create delivery/read receipts.

3. System/audit visibility
   - tightly limited operational access to metadata and safe error codes;
   - no routine message-body logging;
   - platform support has no default content access.

Required disclosure in both apps: “School administrators may review school communications for safeguarding and school policy purposes.” Arabic copy requires legal/native review.

### 15.2 Message integrity

- No edit API in v1.
- Sender cannot hard-delete or erase a message.
- Admin moderation may tombstone it. Participants see a timestamped placeholder such as “Message removed by the school” and, where appropriate, a safe reason.
- Original content/media remains restricted for safeguarding/hold until retention permits deletion.
- Restoring a tombstone is a separate audited moderation action.
- UI copy must never imply that a tombstone erased the school record.

### 15.3 Restrictions and reporting

Defaults:

- guardian replies enabled school-wide;
- per-guardian, per-student, and per-conversation restrictions available;
- restricted guardian may retain read access while send/initiate is disabled;
- severe block can remove ordinary access, but needs admin reason and review;
- staff suspension is driven by membership/assignment, not an ad hoc message block;
- any participant can report a message; report does not hide it automatically;
- no guardian-to-guardian blocking feature because no guardian-to-guardian route exists.

Admin UI must make scope explicit to prevent accidentally disabling every guardian when intending one conversation.

### 15.4 Retention, deletion, hold, export

Recommended provisional default: retain school messages and derived media for seven years after conversation closure or last activity, whichever is later. This is an architecture default, not legal advice; Oman/GCC school-record counsel must confirm it before production.

- Legal hold overrides cleanup.
- Account deletion anonymizes identity while preserving lawful school records.
- FHH family deletion does not delete CHH school records.
- School offboarding produces protected export (JSON/CSV plus media manifest/files), checksum, counts, and expiry.
- After export/contract/legal window, retention worker hard-deletes eligible content and media in auditable batches.
- Backups may retain deleted data until normal encrypted backup rotation; policy must state this.
- Retention shortening applies prospectively through scheduled cleanup and must be audited; it does not bypass holds.

## 16. Arabic/RTL/accessibility

- Every new EN key must have an AR key in the same change; both repositories’ parity checks are release gates.
- English and Arabic keys must remain at parity. Arabic must be Fusha and reviewed
  by a native speaker before pilot.
- User-entered names/messages are rendered with `dir="auto"` and `unicode-bidi: plaintext` where appropriate. They are not machine-translated.
- The overall inbox/thread mirrors in RTL, but chronological order remains top-to-bottom and timestamps/receipt meaning do not reverse.
- Use logical CSS (`margin-inline`, flex gap) and mirror directional icons only when the icon means navigation.
- Mixed phone numbers, filenames, URLs, Latin school names, and timestamps need isolation (`bdi`, `dir="auto"`), not forced RTL.
- Store UTC; display locale-aware dates in the school timezone for school events/messages. FHH may also show device-relative wording, but the absolute school-zone time must be accessible.
- Arabic search normalization may ignore tatweel and optional diacritics for matching while preserving original text. Do not destructively normalize stored messages.
- Truncation must be grapheme-safe at the UI layer; backend body limits count Unicode code points/bytes safely.
- Receipt icons require text/ARIA labels (“Delivered to a guardian”, “Read by staff”); color alone is insufficient.
- Unread counts announce meaningful changes without repeated live-region spam.
- Photo controls have localized accessible names, keyboard activation, focus return, and viewer Escape/hardware Back.
- Composer supports Shift+Enter newline and explicit send shortcut only where safe; mobile Enter remains newline unless product testing approves otherwise.
- Focus order: conversation header → messages → composer controls. On new incoming messages, do not steal focus or scroll if the user is reading older history.

## 17. Performance, scaling, and storage estimates

### 17.1 Assumptions for one school

- 1,000 students;
- up to two school-authorized guardians/student;
- 50 teachers, 10 admins;
- 4–6 relevant staff threads/student/year: 4,000–6,000 student-staff conversations plus 100–300 staff/direct threads;
- 40–120 messages/student/year: 40,000–120,000 messages/year;
- 100–250 peak concurrent users;
- 10–20% of messages contain photos, average 1.4 photos;
- optimized full+thumbnail combined average 0.4–1.0 MB/photo;
- 1–3 notification targets/message before device fan-out;
- provisional seven-year retention.

### 17.2 Growth ranges

| Resource | Annual estimate |
| --- | --- |
| Conversation/participant/access rows | ~15,000–40,000 rows |
| Messages | 40,000–120,000 |
| Receipt events | 80,000–500,000 depending on active recipients/devices/batching |
| Notification/outbox/dispatch rows | 80,000–500,000 |
| DB storage including indexes/audit | approximately 0.3–1.5 GB/year |
| Photo count | approximately 5,600–33,600/year |
| Protected media | approximately 2–35 GB/year; plan operationally for 5–40 GB/year |
| Seven-year retained media | approximately 35–280 GB at the planning range |

These are capacity ranges, not forecasts. Instrument actual pilot values.

### 17.3 Query shapes and indexes

Inbox:

- join only current participant/grant rows;
- order from `conversations.last_message_at`;
- fetch context and last-message preview set-wise;
- calculate unread from `last_message_sequence - last_read_sequence`, adjusted for the participant’s visible sequence range and non-user-visible system rows;
- no correlated “latest message” query per conversation.

Messages:

- `WHERE conversation_id=:id AND sequence < :cursor ORDER BY sequence DESC LIMIT 50`;
- media fetched in one `IN` query;
- participant display map fetched once.

Scheduled dispatch:

- partial/compound outbox index on state/time;
- `SKIP LOCKED`;
- authorization/policy targets resolved in batches;
- no device query per parent in a Python loop when a set-based fan-out query is possible.

Search:

- indexed normalized display names for users/external participants/students;
- existing school/student/class indexes;
- optional PostgreSQL trigram for Arabic/Latin names only after measured need;
- message-body search may be staff/admin-only and can trail basic recipient search.

Moderation/export:

- indexes on message report state/time, audit school/event/time, hold scope, message school/conversation/time.

### 17.4 Performance budgets/tests

- inbox first page: ≤6 SQL statements;
- unread aggregate: ≤2;
- thread page including media metadata/participants: ≤4;
- recipient search: ≤5;
- send transaction: bounded, no per-guardian query loop;
- notification fan-out: set-based per batch;
- p95 API targets on pilot hardware: inbox <300 ms, message page <250 ms, send commit <400 ms excluding upload, unread <150 ms;
- test 1,000 students/6,000 conversations/120,000 messages synthetic dataset on PostgreSQL;
- fail tests on query-count regressions.

Current PostgreSQL and Docker topology is sufficient for one-school v1 if queries are bounded and workers are separate. Monitor disk and add private object storage before multi-year media growth or multiple large schools. Redis is not required for this load.

## 18. Security/privacy threat model

| Threat | Control | Required proof |
| --- | --- | --- |
| Cross-school IDOR | School ID derived from membership/link; opaque IDs; tenant filters; 404 on mismatch | Two-school API tests for every read/write/media/receipt/moderation route |
| Cross-family/child/link access | FHH parent → family child → active connection; CHH explicit link student | Two families/multiple children, swapped IDs/tokens/assertions |
| Stale teacher assignment | Revalidate current assignment on each request; access grant alone insufficient | Expiry/reassignment concurrent tests |
| Guardian revocation race | Lock/recheck source in send/read transaction; revocation wins before commit | Revocation versus send/fetch race tests |
| Replayed FHH request | Short-lived actor assertion, `jti`, body digest, message/client idempotency | Same/different payload replay tests |
| Forged sender identity | FHH server derives assertion; CHH ignores client identity fields | Attempted subject/name override tests |
| Service-token compromise | Separate direction/role credentials, IP allowlist, rotation, minimal reconciliation payload | Config validation and wrong-audience/credential tests |
| Per-link-token compromise | Requires service token too; link/student scope; revoke/rotate; no URL | Link-token-only and cross-link tests |
| Token leakage | Headers only; structured redaction; no analytics/filenames/errors/object URLs | Log-capture tests and frontend network scan |
| Message enumeration | Opaque UUIDs, signed cursors, tenant checks, rate limits | Sequential/random ID probing |
| Cursor tampering | HMAC-signed cursor binds filters/scope/order | Mutation/expiry/wrong-user tests |
| Receipt spoofing | Current participant derived from auth/assertion; cap to authorized sequence | Ack another participant/future sequence tests |
| Admin abuse/invisible surveillance | Disclosure, reason-required short session, immutable per-view audit, no impersonation | Safeguarding receipt isolation/audit tests |
| Malicious/decompression upload | Real decode/type sniff, pixel/byte caps, metadata strip, no active formats | Polyglot, spoofed MIME, bomb, corrupt HEIC tests |
| Preview leakage | Generic default, user/school policy, no body in data/log | Lock-screen payload unit tests |
| Duplicate sends | Conversation/sender/client UUID unique; result lookup on retry | Timeout/retry and concurrent duplicate tests |
| Out-of-order messages | Conversation row lock + per-thread sequence | Concurrent send ordering tests |
| Worker double execution | Lease + `SKIP LOCKED` + stable event/dedupe IDs | Two-worker/restart/expired lease tests |
| Deleted-account history | Anonymize external identity; close grants; retain lawful row | Parent/family deletion E2E |
| Backup/retention overhold | Document rotation, hold-aware cleanup, encrypted backup access | Cleanup/hold simulation and restore policy review |
| DoS/spam | Per-user/conversation/school rate limits; body/photo caps; compose restrictions; notification bundling | Burst/rate-limit tests |
| Notification bridge forgery | Dedicated credential/signature/timestamp/body digest/event uniqueness | Invalid/expired/signature/replay tests |
| FHH mirror creep | Schema/contract tests prohibit message-body storage outside short-lived dispatch payload | Data-minimization review and migration test |

Rate limits should distinguish sends, uploads, search, receipt acks, and safeguarding reads. Avoid one in-memory limiter as the only control under multiple replicas; use database counters/rows or proxy-level limits for critical abuse paths, with an operationally simple implementation.

## 19. Failure, retry, offline, and concurrency behaviour

### 19.1 Message send

- Client generates `client_message_id` and `Idempotency-Key`.
- Optimistic bubble shows `Sending`.
- Success replaces optimistic ID with server message/sequence.
- Known rejection shows `Failed` with safe reason and retains draft/photo selection where possible.
- Network timeout is “status unknown”; client queries/retries same idempotency key. It must not generate a new key and duplicate the message.
- CHH message commit includes message, media attachment, audit, and outbox. A post-commit push failure cannot roll it back.

### 19.2 Offline

- Existing loaded text remains in memory; no promise of durable offline history.
- Composer may retain an unsent draft in memory. Persistent drafts containing school data are deferred unless encrypted/approved.
- Send disabled or retryable while offline; v1 does not maintain a background offline send queue.
- Protected photos are not permanently cached.
- On reconnect/focus, refresh active thread then inbox, reconcile optimistic/idempotent sends, then send receipt acknowledgements.

### 19.3 Partial failures

- One photo upload failure does not remove successful staged photos; user chooses retry/remove before send.
- One broken received photo shows unavailable tile; text and other photos remain.
- FHH/CHH media failure never revokes a valid link.
- CHH→FHH callback failure leaves CHH outbox retryable.
- FHH FCM failure leaves message/inbox intact; invalid token is revoked; transient failure retries.
- Email failure never affects push/in-app.
- Worker crash after provider request but before row completion can duplicate a push. Stable collapse/dedupe keys and conservative provider payloads reduce impact; message itself remains single.

### 19.4 Notification bundling/spam

Default:

- one immediate notification for the first unread message in a conversation within a five-minute bundle window;
- subsequent messages update/collapse the same conversation notification where platform supports it;
- on contact-hours reopen, generate at most one summary notification per conversation/recipient bundle, not one lock-screen alert per held message;
- urgent admin messages bypass bundling only when explicitly authorized;
- in-app unread always reflects every message.

### 19.5 Revocation during an open session

The next poll/send/media request denies access. UI:

- stops polling;
- clears composer and protected object URLs;
- shows “This school conversation is no longer available” or read-only closure if history remains authorized;
- never tries another child/link automatically.

## 20. Migration, deployment, rollback, observability, and pilot rollout

### 20.1 Migration/release order

1. Documentation/policy approval; messaging remains disabled.
2. Add nullable/additive CHH core schema and policy flags. No routes use it.
3. Deploy CHH core services/APIs behind global and school feature flags.
4. Deploy CHH staff UI hidden unless enabled.
5. Add FHH lifecycle/identity/locale/bridge schema and account-deletion sync before parent messaging.
6. Deploy FHH proxy APIs/UI hidden.
7. Validate cross-repo text messaging without notifications.
8. Add photo schema/routes/UI.
9. Add receipt acknowledgement; presentation toggles remain configurable.
10. Add contact-hours/outbox workers with dispatch disabled/dry-run metrics.
11. Add CHH staff token registration/push and FHH callback/reconciliation/push.
12. Add safeguarding/moderation/export/retention worker.
13. Pilot one school/selected classes; expand only after success gates.

Migrations are additive first. Do not drop/rename until all supported clients ignore old fields. Messaging starts disabled by default at both global config and school policy.

### 20.2 Client compatibility

- Old clients see no messaging entry and continue current routes.
- APIs return explicit capability/policy fields; unknown fields are ignored.
- Native deep links first land on a normal authenticated FHH/CHH route; old native versions may open the app without routing and still show unread on refresh.
- Notification rollout is separate from message rollout. A school can use in-app text messaging before push is enabled.
- No media backfill: messaging has no old media. Existing update photos stay in their current model.

### 20.3 Rollback

- UI rollback: hide/disable feature flags; data remains.
- API rollback: retain additive tables/columns and old-compatible responses; stop new sends if necessary while preserving reads/export.
- Worker rollback: stop worker service; rows remain pending/held and are replayable.
- Push rollback: disable channel/policy only; in-app state continues.
- Native rollback: deep-link payload degrades to app open/inbox.
- Schema rollback: avoid destructive downgrade after real messages exist. Forward-fix preferred. Any downgrade script may remove only unused pre-pilot tables after proving zero rows.
- Media rollback: disable uploads, preserve/view existing protected photos.

### 20.4 Observability

Structured logs/metrics must exclude message bodies, tokens, raw filenames, assertion claims, and family data.

Metrics:

- message send accepted/rejected/unknown latency;
- idempotent replay count;
- authorization denials by safe reason and endpoint;
- inbox/thread query p50/p95/p99 and query count;
- unread lag after commit;
- outbox held age, eligible lag, lease conflicts, retries, dead rows;
- CHH→FHH callback success/latency/reconciliation gap;
- FHH dispatch/provider acceptance/failure/invalid-token rate;
- upload decode/optimization/failure/bytes/time;
- broken media rate;
- receipt acknowledgement lag;
- safeguarding access/report/moderation/export counts;
- retention cleanup/hold exclusions;
- active conversations/messages/photos per school.

Dashboards/alerts:

- oldest eligible outbox row;
- dead-letter count;
- callback outage/reconciliation backlog;
- storage capacity;
- authorization denial spike;
- send error/latency spike;
- FCM credential/init failure;
- cleanup failures.

Support runbook must cover link/identity diagnostics, idempotent send lookup, outbox replay, token revocation, policy timing, safeguarding reason/audit review, media cleanup, and no-secret logging.

### 20.5 Pilot gates and success measures

Before enabling:

- retention/legal/disclosure approved;
- two-school/two-family authorization suite green;
- FHH deletion/unlink lifecycle sync proven;
- worker restart/double-execution tests green;
- generic preview and Arabic copy reviewed;
- backup/storage/runbook ready;
- staff/parent training explains shared guardians/admin visibility/contact hours.

Pilot metrics:

- send success >99.5% excluding client validation;
- p95 send commit <400 ms excluding upload;
- eligible outbox p95 dispatch lag <60 seconds, held rows released within five minutes of opening;
- no cross-tenant incident;
- notification invalid-token/failure understood and below agreed threshold;
- teacher/parent weekly active messaging adoption;
- support tickets and after-hours expectations;
- percentage of messages seen/read within 24 hours, interpreted under receipt policy.

## 21. Testing strategy

Every authorization fixture includes at least:

- School A and School B;
- Family 1 and Family 2;
- multiple children, including siblings;
- two active guardians for one student;
- multiple active FHH parents in one family;
- teacher who is also a parent;
- teacher/admin overlapping memberships;
- active and expired assignments/enrolments;
- active/revoked GuardianLink, FhhLink, SchoolConnection;
- old and replacement teacher.

### 21.1 Models/constraints

- every conversation-kind check and partial unique index;
- duplicate active thread prevention under concurrency;
- actor-shape XOR checks;
- message sequence/idempotency uniqueness;
- message body/media requirement and length;
- five-photo ordering;
- receipt event idempotency/cursor monotonicity;
- contact window/exception validation including overnight;
- outbox target/state/dedupe constraints;
- audit immutability;
- hold-aware deletion.

### 21.2 Authorization/lifecycle

- cross-school staff/guardian/external IDs on every endpoint;
- cross-family child/connection swaps in FHH;
- link token from one child with another conversation/assertion;
- both guardians see shared current thread;
- newly linked guardian does not see prior sequence by default;
- one guardian revoked while another remains;
- multiple FHH parents have separate sender attribution/read cursors;
- parent removal/family deletion/unlink closes correct access only;
- assignment expiry/reassignment/suspension/departure;
- admin role removal;
- student class/school transfer/archive;
- school suspension;
- teacher-parent actor-context isolation;
- safeguarding access with reason and no receipt.

### 21.3 Contact hours/time

- exact open/close boundary;
- Friday/Saturday;
- explicit holiday closed/custom exception;
- overnight interval before/after midnight;
- Asia/Muscat and DST zone spring/fall transitions;
- personal opt-in allowed/disallowed;
- parent urgent rejected;
- teacher/admin urgent permission;
- policy change releases/reholds undispatched rows;
- reopen bundling/deduplication;
- application-open outside hours sees message.

### 21.4 Receipts/idempotency/concurrency

- delivery/read presentation toggles independent;
- internal events retained when hidden;
- multiple devices out-of-order/max cursor;
- read implies delivered;
- ack beyond authorized/latest sequence rejected/capped;
- optimistic send timeout and retry returns same message;
- simultaneous sends get strict sequences;
- pagination stable while new messages arrive;
- safeguarding view creates no participant cursor.

### 21.5 Media

- real type versus declared MIME;
- JPEG/PNG/WEBP/HEIC orientation;
- EXIF/ICC/GPS stripped;
- no upscaling, size/dimension budgets;
- decompression bomb/corrupt/polyglot rejection;
- max five/count/size;
- staged upload ownership/cross-school reuse rejection;
- transaction rollback/orphan sweeper;
- thumbnail failure cleanup;
- broken photo isolation;
- protected headers/log redaction;
- FHH proxy sanitization and no direct CHH URL/token;
- browser memory cleanup;
- Android camera/gallery/viewer/pinch/pan/back;
- private export behavior if enabled.

### 21.6 Notification/outbox/native

- message commit survives all notification failures;
- held/eligible transitions;
- `SKIP LOCKED` two-worker claims;
- crash after lease, lease expiry, restart recovery;
- callback auth/signature/replay/idempotent duplicate;
- callback lost response plus reconciliation;
- FHH current-parent fan-out;
- removed parent not notified;
- invalid token revocation/transient retry;
- generic/localized EN/AR payload;
- deep link cold/warm start, revoked target, duplicate action;
- CHH staff Android registration;
- FHH Android and production-provisioned iOS verification.

### 21.7 UI/i18n/accessibility

- EN/AR key parity;
- Fusha review checklist;
- RTL screenshots mobile/desktop;
- `dir=auto` mixed Arabic/English, URLs, phone numbers, filenames;
- unread badge labels;
- keyboard navigation/focus return/Escape;
- screen-reader receipt and contact-hours announcements;
- offline/stale/retry/partial-photo states;
- desktop split pane and mobile back stack;
- no giant parent-page growth: component ownership review.

### 21.8 Performance/E2E

- PostgreSQL query-count budgets;
- 6,000 conversations/120,000 messages data volume;
- inbox/unread/message page latency;
- held notification burst at opening;
- export/cleanup batches;
- full E2E:
  1. FHH parent → teacher during hours;
  2. FHH parent → teacher outside hours → held push → release;
  3. teacher → two CHH/FHH guardians → distinct reads;
  4. assignment ends → former teacher denied → replacement new thread;
  5. FHH unlink/deletion;
  6. admin safeguarding view;
  7. text + five photos;
  8. native push tap to conversation.

## 22. Implementation slices with exit criteria

Each slice is separately deployable/testable. File lists are likely touch points, not permission to widen scope.

### Slice 1 — policy decisions, flags, and lifecycle prerequisites

**Objective:** encode approved defaults and close the FHH deletion/unlink gap before message data exists.

**Implementation status (2026-07-16): implemented as S25a / FHH-A.**

- CHH migration `c2d3e4f5a6b7` adds `schools.messaging_remote_ref`,
  `school_messaging_policies`, minimized FHH lifecycle identity/link state, and the
  idempotent lifecycle-event ledger.
- `MESSAGING_ENABLED=false` remains the global default. Every school policy is also
  created with `enabled=false`; the school-admin policy API reports a separate
  `effective_enabled` value and audits versioned changes.
- FHH migration `a2b3c4d5e6f7` adds `remote_school_ref`, server-owned parent/device
  locale, school-scoped opaque identities, identity-link lifecycle state, and
  `school_messaging_lifecycle_outbox`.
- FHH unlink, grown-up removal, verified parent roster/profile reconciliation, and
  family deletion commit locally before remote delivery. A dedicated database-backed
  lifecycle worker leases rows with `SKIP LOCKED`, preserves event UUIDs across
  retries, applies exponential backoff, and distinguishes retryable transport/service
  failures from terminal link/schema conflicts.
- The CHH receiver requires the existing FHH service bearer and per-link credential,
  serializes school lifecycle application, is repeat-safe, rejects payload extras,
  and writes the existing append-only school audit log.
- No conversation, participant, message, media, receipt, contact-window,
  notification-outbox, push, inbox, parent messaging API, or messaging UI was added.

- CHH likely files: `backend/app/database.py`, `backend/app/models_school/models.py`, `backend/app/schemas.py`, new Alembic revision, school settings routes/UI, `frontend/src/lib/i18n/messages.ts`.
- FHH likely files: `backend/app/models.py`, `backend/app/services/account_deletion_service.py`, new lifecycle outbox service/route/client changes, Alembic revision, tests.
- Scope: feature flags disabled, policy model, remote school reference, parent/token locale, durable unlink/delete sync skeleton.
- Privacy: no message schema/API; no family data sent.
- Tests: config fail-closed, family deletion revokes connections/queues CHH lifecycle event, retry/idempotency.
- Deploy: migrations → backends → hidden settings.
- Rollback: flags off; additive schema retained.
- Dependency: legal/product confirmation of provisional defaults.
- Exit: deletion/unlink cannot leave a silently active messaging identity/link, and messaging remains unavailable.

### Slice 2 — CHH core schema, participant/access history, audit

**Objective:** create conversations, participants, grants, messages, policies, immutable messaging audit without public UI.

**Implementation status (2026-07-17): implemented as S25b.**

- CHH migration `d3e4f5a6b7c8` adds `conversations`,
  `conversation_participants`, `conversation_access_grants`, `messages`,
  `message_receipt_events`, and `messaging_audit_events`, including opaque public UUIDs,
  conversation-kind checks, partial current-thread uniqueness, actor-shape checks,
  message idempotency/sequence constraints, source indexes, and append-only database
  guards.
- The already implemented minimized `fhh_messaging_identities` table is used as the
  plan's external-participant registry rather than duplicating the same school-scoped
  identity in a second table.
- `backend/app/messaging_service.py` revalidates current memberships, assignments,
  guardian links, and FHH link/identity grants in addition to the historical ledger.
  The approved `school_admin_membership` source also represents an ordinary current
  teacher membership only in `staff_direct`; student access remains assignment-backed.
- Sending locks the conversation row, allocates a monotonic sequence, preserves an
  immutable sender snapshot, reconciles duplicate client UUIDs, and writes message
  audit evidence in the same transaction.
- PostgreSQL fresh upgrade, downgrade/re-upgrade, and two-session concurrent send
  validation passed. Messaging remains globally and per-school disabled; no public
  route, UI, media, notification outbox, contact-hours logic, or push work was added.

- Files: `backend/app/models_school/models.py`, `backend/app/schemas.py`, new messaging service modules, Alembic, model/constraint tests.
- Schema: core tables through messages/receipt events; feature disabled.
- Authorization: reusable dynamic grant resolver; no route hand-filtering.
- Tests: constraints, dedupe, lifecycle grants, two schools, assignment/guardian source checks.
- Deploy: migration before code; no rows created automatically.
- Rollback: disable; forward-fix schema after data.
- Exit: exact model invariants and access resolver proven on PostgreSQL.

### Slice 3 — CHH messaging APIs, pagination, unread, text send

**Objective:** staff and CHH guardian text APIs.

- Files: new `backend/app/routes/messaging.py`, service/query modules, `backend/app/main.py`, tests.
- API: inbox, recipients, find/create, messages, send, receipts internal but receipt UI off.
- Privacy: explicit school/student scope; signed cursors; idempotency.
- Tests: authorization matrix, query count, ordering/concurrency/retry.
- Deploy: backend hidden by flag.
- Rollback: disable write endpoints; retain reads/data.
- Dependency: Slice 2.
- Exit: text flow works via API with bounded queries and no FHH dependency.

### Slice 4 — CHH teacher/admin inbox and conversation UI

**Objective:** polished shared `/messages` staff surface and unread badge.

- Files: routes/components/store described in §13, layout nav, i18n.
- Scope: inbox/search/filter/compose/thread/offline/retry/mobile/desktop; no photo/push yet.
- Authorization: UI consumes capability flags; backend remains authority.
- Tests: component/E2E/RTL/accessibility/deep-link fallback.
- Deploy: frontend after API; school flag still controlled.
- Rollback: hide nav/route.
- Exit: staff can complete text conversations without using raw CRUD views.

### Slice 5 — FHH external identity and integration API

**Objective:** resolve individual multi-parent identity and expose safe link-scoped text messaging to FHH backend.

- CHH files: integration router, actor assertion validation, external participant service, tests/config.
- FHH files: models/migration, identity service, CHH messaging client, school-message routes/schemas.
- Privacy: only opaque school subject, display name, locale; no email/family/device data.
- Tests: forged identity, replay, sibling same-school reuse, cross-link/family, parent deletion.
- Deploy: FHH migration/backend, CHH config/API; UI hidden.
- Rollback: disable integration messaging; lifecycle events continue.
- Exit: two parents sharing a family act/read as distinct people in the same CHH thread.

### Slice 6 — FHH parent inbox/navigation/UI

**Objective:** dedicated aggregated school inbox plus child entry points.

- Files: new FHH routes/components/store, parent shell/layout entry, small child-context links, i18n.
- Scope: text read/send/reply, filters, badges, contact-hours copy placeholders, no photo/push.
- Privacy: memory-only state; sanitized DTOs; no parent monolith implementation.
- Tests: multiple children/schools/parents, revoked/no-link behavior, RTL/accessibility/mobile back.
- Deploy: frontend behind feature flag.
- Rollback: hide route/nav.
- Exit: parent text flow is obvious, separate from home features, and cross-repo E2E works.

### Slice 7 — cross-repository text E2E hardening

**Objective:** stabilize identity, lifecycle, concurrency, errors, and support diagnostics before media/notifications.

- Files: tests, safe observability, runbook/docs; minimal fixes only.
- Scope: all lifecycle sample flows, load/query tests, idempotency, revocation races.
- Deploy: pilot-like staging with flags restricted.
- Rollback: keep disabled.
- Exit: complete two-school/two-family E2E matrix and security review green.

### Slice 8 — protected photo media and viewers

**Objective:** text + up to five safe photos end-to-end.

- CHH: generalize image service, media model/routes/cleanup.
- FHH: multipart proxy, memory cache, camera/gallery, viewer.
- Tests: full media matrix/orphans/broken isolation/Android.
- Deploy: schema/backend before clients; upload capability separately flaggable.
- Rollback: disable new uploads; existing photos viewable.
- Dependency: hardened text flow.
- Exit: raw originals discarded, derived protected photos work on browser/Android, no public/persistent cache.

### Slice 9 — delivery/read receipts

**Objective:** participant cursors/events and independent school presentation toggles.

- Files: receipt services/routes/UI/policy settings in both repos.
- Scope: batch ack, multi-device, aggregate guardian wording.
- Tests: toggles, race/order, safeguarding isolation.
- Deploy: internal collection first, presentation off; then delivery on/read off default.
- Rollback: hide presentation while retaining evidence.
- Exit: sender claims remain honest and schema supports later policy changes.

### Slice 10 — contact hours and durable CHH outbox

**Objective:** separate message acceptance from notification scheduling.

- Files: policy/window/exception routes/UI, outbox model/service, separate worker entrypoint/Compose service, tests.
- Scope: scheduling only; dispatch may use a fake/dry-run provider.
- Tests: truth table, DST, policy changes, leases/restarts/bundling.
- Deploy: migration → backend → worker dry-run → policy UI.
- Rollback: stop worker; messages continue; rows retained.
- Exit: held/pending transitions are durable, idempotent, and observable.

### Slice 11 — CHH staff push and FHH parent push bridge

**Objective:** background awareness without sharing device tokens.

- CHH: device tokens/FCM registration and sender; callback/reconciliation.
- FHH: bridge event/local outbox workers, deep-link handling, locale/preview.
- Native: Android; FHH iOS only after capability proof.
- Tests: provider failures, invalid token, callback outage/reconcile, deep links, privacy.
- Deploy: token registration → callback dry-run → selected internal devices → pilot.
- Rollback: disable channels/workers; in-app continues.
- Exit: committed messages survive every delivery failure and no FHH token/family data enters CHH.

### Slice 12 — safeguarding, moderation, restrictions, export/hold

**Objective:** school-ready governance before general pilot messaging.

- Files: models/routes/admin UI/audit/export worker/tests; disclosures/i18n.
- Scope: reason-bound view, reports, tombstone, restrictions, legal hold/export foundation.
- Tests: access abuse, audit immutability, receipt isolation, hold/export authorization.
- Deploy: backend/admin UI before widening school flag.
- Rollback: disable actions but retain audit/data.
- Exit: school can investigate/report/restrict/export without impersonation or silent deletion.

### Slice 13 — retention, performance, observability, production hardening

**Objective:** operational readiness and controlled pilot.

- Files: cleanup worker, metrics/logging, dashboards/runbooks, query/index refinements, load tests.
- Scope: retention batches, alerts, storage thresholds, dead-letter replay.
- Deploy: dry-run cleanup/metrics → backup verification → one-school pilot.
- Rollback: stop cleanup/worker; do not reverse committed data.
- Exit: success gates in §20.5 met and support runbook rehearsed.

## 23. Risks, unresolved questions, and explicit non-goals

### 23.1 Top unresolved decisions/risks

1. **Retention/legal/export policy:** seven years is the recommended technical default, but Oman/GCC legal counsel and school contracts must confirm retention, disclosure, legal hold, parent data-subject handling, and offboarding format before production.
2. **External-parent lifecycle policy:** the technical deletion/unlink gap is closed by
   S25a/FHH-A. Local removal now commits first and durable lifecycle events reconcile
   CHH without transferring family IDs, parent database IDs, email, home data, device
   tokens, or message content. Product/legal sign-off is still required for the
   long-term naming/anonymisation and record-retention policy before Messaging v1 is
   enabled.
3. **Native push operations:** CHH has no staff push foundation, FHH push is best-effort without outbox/deep links/preferences, and checked-in iOS push entitlement evidence is absent. Messaging must not promise reliable background delivery until credentials, capabilities, workers, metrics, and real-device tests are complete.

Additional follow-ups:

- confirm whether staff may see individual guardian receipt details or only aggregate guardian receipts; default aggregate;
- confirm whether a newly linked guardian may ever receive prior history without an explicit admin action; default no;
- native-speaker/legal review of safeguarding/contact-hours/notification Arabic;
- decide whether school-message photo export is disabled or allowed through private app cache; default viewer only;
- define school offboarding artifact format/encryption/expiry;
- design branch-local admin scope only when membership authorization supports it.

### 23.2 Explicit v1 non-goals

- group conversations of any kind;
- guardian-to-guardian messaging;
- parent class groups or staff groups containing parents;
- school/class broadcast chat; use announcements;
- comments on announcements;
- voice notes, video, PDF, DOCX, XLSX;
- reactions, forwarding, presence, online status, typing indicators;
- message editing;
- machine translation;
- end-to-end encryption that prevents school safeguarding;
- public media URLs/CDN;
- permanent offline school-message/media storage;
- browser/PWA push;
- WhatsApp delivery;
- bot/AI moderation or content generation;
- replacing an SIS/LMS or homework submission workflow.

## 24. Documentation maintenance ledger

This ledger records the documentation-only maintenance performed by the audit. Paths in the FHH repository are explicitly prefixed.

### Created

- CHH `docs/planning/2026-07-messaging-v1-architecture-plan.md` — this authoritative source.
- FHH `docs/planning/2026-07-fhh-school-messaging-integration-plan.md` — parent/integration companion.

### Updated

CHH:

- `README.md` — authoritative messaging plan added to current docs.
- `docs/CLASS_HERO_HUB_MASTER_BLUEPRINT.md` — marked partially superseded for Messaging v1; §19/S15 explicitly historical.
- `docs/product/CLASS_HERO_HUB_PRODUCT_STRATEGY_NOTES.md` — messaging/notification recommendations retained as strategy history and linked to the current plan.
- `docs/implementation/CHH_FHH_INTEGRATION_API_AUDIT.md` — current checkpoint correction and messaging boundary supersession note.
- `docs/implementation/CLASS_HERO_HUB_IMPLEMENTATION_LOG.md` — documentation-only architecture audit entry.
- `docs/DOCS_CLEANUP_REPORT.md` — current documentation authority/index note.
- `docs/planning/2026-07-messaging-v1-architecture-plan.md` — Slice 1 implementation
  status, migrations, lifecycle protocol, retry behavior, and remaining non-implemented
  scope recorded; later updated with the Slice 2 core-schema implementation and its
  plan-compatible live-code adjustments.
- `docs/implementation/CLASS_HERO_HUB_IMPLEMENTATION_LOG.md` — S25a implementation,
  validation, deployment, and the pre-existing unrelated full-suite failure recorded;
  later updated with S25b schema, tests, backup, migration, and deployment evidence.

FHH:

- `README.md` — companion plan/index and corrected committed iOS-project statement.
- `docs/PROJECT_STATUS.md` — current linked-school/push foundation, messaging not implemented, and stale deployment statement corrected.
- `docs/ROADMAP.md` — Messaging v1 planned work and push remaining work.
- `docs/DESIGN.md` — school-messaging design/RTL/component boundary note.
- `docs/PUSH_NOTIFICATIONS_PLAN.md` — changed from fully superseded to partially superseded; foundation versus remaining durable messaging work clarified.
- `docs/CURRENT_DEPLOYMENT.md` — Europe source branch corrected to `develop`; messaging remains planned.
- `docs/IOS_BUILD_AND_RELEASE_PLAN.md` — marked historical/superseded by current runbook.
- `docs/IOS_BUILD_AND_RELEASE_RUNBOOK.md` — removed contradictory “commit iOS project” open item and linked messaging push requirements.
- `docs/ANDROID_BUILD_AND_RELEASE_RUNBOOK.md` — corrected the obsolete claim that native child sessions are unsupported and linked planned message deep links.
- `docs/GOOGLE_PLAY_COMPLIANCE.md` — recorded the messaging disclosure update gate and the current SchoolConnection deletion gap.
- `docs/implementation_s18_school_link_setup.md` — linked companion and clarified messaging is not part of implemented school link.
- `docs/implementation/FHH_LINKED_SCHOOL_DASHBOARD_IMPLEMENTATION.md` — linked companion; dashboard remains current media/navigation foundation, not messaging spec.
- `docs/audit/2026-07-fhh-linked-school-dashboard-ux-media-refresh-audit.md` — marked historical/implemented and prevented from appearing current.
- `docs/UPGRADE_TRACKER.md` — documentation-only audit entry and stale PostgreSQL cutover verification corrected.
- `docs/QA_COVERAGE_MATRIX.md` — explicitly records that linked-school/push tests are not Messaging v1 coverage.
- `docs/manuals/parent-user-manual.md`, `docs/manuals/quick-start-for-parents.md`, and `docs/manuals/faq.md` — current linked-school usage documented and messaging clearly marked unavailable.
- FHH `docs/operations/SCHOOL_MESSAGING_LIFECYCLE_OUTBOX.md` — lifecycle event,
  retry/recovery, privacy, and operations runbook.
- FHH companion/status/roadmap/deployment/upgrade documents — FHH-A implementation
  state and remaining messaging scope recorded.

### Marked historical/partially superseded

- CHH master blueprint messaging §19/S15 — partially superseded.
- CHH product strategy messaging/notification sections — strategy history; architecture superseded.
- CHH/FHH integration API audit — historical implementation audit; messaging extension superseded.
- FHH push plan — partially superseded; token/FCM foundation implemented, durable message delivery not implemented.
- FHH iOS build plan — historical/superseded by runbook.
- FHH linked-school UX audit — historical recommendations implemented by the current dashboard implementation document.

### Reviewed and intentionally left unchanged

CHH:

- `docs/implementation/CHH_UPDATE_PHOTO_THUMBNAILS.md` — accurate current media implementation evidence.
- `docs/implementation/FHH_LINKED_SCHOOL_MEDIA_ANDROID.md` — accurate protected Android media evidence.
- `docs/testing/CHH_ANDROID_APK_SMOKE_TEST.md` and `docs/ops/CHH_ANDROID_GOOGLE_OAUTH_SETUP.md` — current native/auth references; messaging is not implemented.
- `docs/BACKEND_PERFORMANCE.md` and roster optimization docs — current bounded-query foundation.
- existing guardian/onboarding/report/behaviour plans — not messaging specifications.

FHH:

- `docs/LOCALISATION_NOTES.md` and `docs/ARABIC_FUSHA_AUDIT.md` — current localization foundations.
- `docs/ANDROID_PUBLISHING_AND_APP_LINKS.md` — current child-link contract; future messaging deep links must extend, not rewrite it.
- `docs/refactors/2026-07-07-parent-child-dashboard-refactor-plan.md` — plan remains useful evidence against growing monoliths.
- FHH child manual/quick-start/troubleshooting/glossary — current child/home guidance remains
  accurate; school messaging is parent-facing and not implemented. Parent manual/quick-start/FAQ
  were updated separately above for the existing linked-school feature.

### Deferred documentation gaps

- legally reviewed messaging privacy/retention/safeguarding notice;
- school admin policy and moderation user guide;
- staff/guardian/FHH parent user manuals after UI exists;
- messaging operations/outbox/incident runbook;
- data export/offboarding specification;
- Android/iOS message deep-link and push release checklist;
- updated Play/App Store data-safety/privacy disclosures when message content collection is implemented;
- branch-local administration policy if introduced.

## 25. Evidence appendix listing inspected files/symbols

### CHH

- Git/tree/deployment: `.git`, `docker-compose.yml`, `backend/requirements.txt`, `frontend/package.json`, Android manifest.
- Routing/config/auth: `backend/app/main.py`, `backend/app/database.py:Settings`, `backend/app/auth.py:get_current_user/validate_csrf_request`, `backend/app/security.py`.
- School auth/audit/rosters: `backend/app/school_scope.py:write_audit/require_school_role/require_teacher_of/open_interval_expression`; `backend/app/rosters.py:resolve_rosters_for_students`.
- Models: `backend/app/models_school/models.py` symbols listed in §3.1.
- Integration: `backend/app/routes/integrations_fhh.py:require_fhh_service/_link/_scope` and all dashboard/media/link routes.
- Guardian/content: `backend/app/routes/guardian.py`, `announcements.py`, `homework.py`, `updates.py`, `calendar.py`, `behaviour.py`.
- Media: `backend/app/update_image_service.py`, `backend/app/routes/updates.py`, `backend/app/update_thumbnail_backfill.py`, `frontend/src/lib/protected-update-photo.ts`.
- Frontend/native/i18n: `frontend/src/routes/+layout.svelte`, `/school/+page.svelte`, `/teach/+page.svelte`, `/parent/+page.svelte`, `frontend/src/lib/api.ts`, `nativeAuth.ts`, `i18n/index.ts`, `i18n/messages.ts`, Android sources/manifest.
- Migrations: all `alembic/versions/*.py`, especially school identity, assignments, students/enrolments, guardian onboarding, FHH integration, announcements/read, homework, updates, calendar, behavior context, performance indexes.
- Tests: `backend/tests/test_integrations_fhh.py`, `test_guardian_dashboard.py`, `test_guardian_onboarding.py`, `test_staff_assignments.py`, `test_updates.py`, `test_calendar.py`, `test_user_auth.py`, school/report suites.
- Docs: README, master blueprint, product strategy, integration audit, implementation log, media/native implementation/runbook docs, planning/audit indexes.

### FHH

- Git/tree/deployment: remote `.git`, `docker-compose.yml`, `backend/requirements.txt`, `frontend/package.json`, Android/iOS projects and manifests/project files.
- Models/auth/family: `backend/app/models.py:ParentUser/Family/Child/SchoolConnection/DevicePushToken`; `backend/app/auth.py:get_current_parent`; `backend/app/routes/family_scope.py:get_family_child_or_404`.
- CHH integration: `backend/app/routes/school_connections.py:sanitize_dashboard/_proxy_media` and route family; `backend/app/services/chh_integration_client.py`.
- Push: `backend/app/routes/notifications.py`, `backend/app/services/push_service.py`, `frontend/src/lib/native/push-notifications.ts`, Android notification permission, iOS Firebase/AppDelegate/FcmToken files.
- Lifecycle: `backend/app/services/account_deletion_service.py:delete_family_for_parent`, grown-up management routes/services.
- Frontend/media/navigation: `frontend/src/routes/+layout.svelte`, `parent/+page.svelte`, `child/[id]/+page.svelte`, `school-link/[id]/+page.svelte`, `frontend/src/lib/school-link-photo-media.ts`, native child-link/deep-link helpers, Android attachment export/FileProvider.
- i18n: `frontend/src/lib/i18n/index.ts`, `messages.ts`, parity script.
- Background: `backend/app/main.py:_savings_maturity_loop/start_savings_maturity_worker`.
- Migrations: school connections, device push tokens, account deletion tombstones, family child privacy acknowledgements, inherited PostgreSQL/ledger revisions.
- Tests: `backend/tests/test_school_connections.py`, `test_push_notifications.py`, `test_account_deletion.py`, `test_family_grownup_management.py`, auth/family tests; frontend push/media/native tests.
- Docs: README, current deployment, project status, roadmap, design, push plan, Android/iOS runbooks/plans, linked-school setup/implementation/audit, localization/compliance, dashboard refactor plan, manuals/FAQ.

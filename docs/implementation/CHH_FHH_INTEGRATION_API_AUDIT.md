# CHH ↔ FHH Integration API — Audit & Design

**Date:** 2026-07-11
**Status:** Design/audit only — no code changed, nothing committed.
**Scope:** Read-only audit of Class Hero Hub (CHH, restore server 10.250.50.5,
`/opt/apps/class_hero_hub`, branch `main` @ `bab9ae3`) and Family Hero Hub (FHH, dev
server 10.250.50.1, `/opt/apps/family-hero-hub`, branch `develop` @ `fcacb34`, dirty
working tree with in-flight push-notification work).

---

## 1. Executive summary

CHH and FHH are sibling FastAPI + SvelteKit stacks (CHH is an FHH fork), which makes
integration unusually cheap: both share the same token-hash invite pattern
(`secrets.token_urlsafe` → SHA-256 hash stored, raw token never persisted), the same
`BoundedInMemoryRateLimiter`, the same session/cookie conventions, and near-identical
project layout.

**The single most important architectural finding:** every CHH guardian read path
(`/api/guardian/*`) is keyed off `current_user.id` → active `GuardianLink` rows via a
shared `_guardian_audience(db, current_user)` helper (announcements.py:381). There is no
per-student/per-link query path today — guardian endpoints aggregate *all* of a
guardian's children. The FHH integration is per-link (one FHH child ↔ one CHH student),
so the integration layer needs thin per-link variants of these helpers, or an internal
"scope = one GuardianLink" adapter. The underlying audience logic (school /
class_section / subject_group clause building) is directly reusable.

**Recommendation:** build a dedicated `/api/integrations/fhh/*` surface on CHH secured
by a service bearer token over the mesh (10.250.50.1 → 10.250.50.5), backed by two new
tables (`fhh_link_invites`, `fhh_links`), reusing the existing `GuardianInvite` printing
UI pattern for QR issuance and the existing guardian audience/query helpers internally.
FHH never calls `/api/guardian/*` or `/api/teach/*` directly. One dashboard bundle
endpoint serves the MVP. FHH gets a new `school_connections` table keyed by `child_id`,
a scan/enter-code flow modelled on its existing child-device QR flow (kept strictly
separate from it), and a "School" card on the parent/child dashboards that renders only
when a connection exists. No FHH family data ever flows to CHH; the only write-back is
homework done/not-done.

Estimated effort: 5 slices (S17–S21 below), each roughly the size of the recent
S13–S16 CHH slices.

### Implemented-status note — 2026-07-12

The original audit/design remains historical and is intentionally not rewritten.
Since it was authored, S19 and S20 have been implemented across CHH and FHH:

- S19 linked-school dashboard/display slice is implemented. FHH owns the parent-authenticated
  link/dashboard UI and uses an explicit sanitized allowlist; the browser/app talks only
  to FHH, never CHH. The final parent UX keeps school access out of the main dashboard:
  only a linked child modal/action-sheet action and Settings → School connections expose it.
- S20 protected media proxy is implemented. CHH now serves scoped integration-only bytes
  for announcement attachments, homework attachments, and update photos; FHH proxies them
  through parent/family-scoped routes. Service and per-link tokens remain server-side.
- Media 401/403/404/410 failures are treated as media-unavailable and do not revoke a
  durable FHH school connection. Dashboard/link validation remains a separate revocation
  path.
- The S20 media endpoint tests, safe school-avatar plumbing, and homework write-back remain
  deferred. See the dated S19/S20 implementation-log entries for exact files, QA findings,
  deployment notes, and validation results.

---

## 2. Access & repo status (Part 1 verification)

| Item | Result |
|---|---|
| CHH path | `/opt/apps/class_hero_hub` on restore (10.250.50.5) |
| CHH branch | `main`, clean, in sync with `origin/main`, HEAD `bab9ae3` "Add school calendar MVP" |
| FHH path | `/opt/apps/family-hero-hub` on dev (10.250.50.1), reachable via `ssh dev` |
| FHH branch | `develop`, tracking `origin/develop`, HEAD `fcacb34` — **dirty**: ~20 modified files + untracked (push notifications, child privacy acknowledgements) |
| SSH | `ssh dev` works non-interactively; `FHH_FOUND` confirmed |

FHH's dirty tree means S18+ work on FHH must coordinate with (or land after) the
in-flight push-notification branch.

---

## 3. CHH API inventory

Backend: FastAPI, routes in `backend/app/routes/`, mounted in `main.py:111-133`.
Auth: session cookie `access_token` → `auth.get_current_user`; CSRF double-submit
cookie for unsafe methods. Role scoping per prefix:

- `/api/school/*` — school_admin (via `require_school_role` / `_staff_membership`), `X-School-Id` header for school context.
- `/api/teach/*` — teacher membership (`_teacher_membership`), `X-School-Id` header.
- `/api/guardian/*` — any logged-in user; data scoped by their active `GuardianLink` rows.
- `/api/join/*` — guardian invite claim flow (short codes `CHH-XXXX-XXXX`).
- `/api/platform/*` — platform admin.

### 3.1 Guardian-facing endpoints (the reuse candidates)

All use `Depends(auth.get_current_user)` + GuardianLink-derived scoping. "Reuse
internally" = the query/payload helpers can back integration routes; **none should be
called by FHH directly** (they need a CHH browser session cookie, aggregate all
children, and their payload shape is CHH-frontend-specific).

| Endpoint | File | Returns | Internal reuse |
|---|---|---|---|
| `GET /api/guardian/dashboard` | guardian.py:43 | children[] with school/class/grade names, avatars, points total + recent events | Yes — per-child payload shape is close to what FHH needs |
| `GET /api/guardian/points` | behaviour.py:105 | `guardian_points_payload(db, user_id)` — per-child totals + recent events | Yes — service function already factored out |
| `GET /api/guardian/announcements` (+ `/{id}`, `/{id}/attachments/{id}/download`) | announcements.py:752+ | published announcements filtered by `_guardian_query`; file download via FileResponse | Yes — `_guardian_audience`/`_guardian_query` are the core scoping helpers |
| `GET /api/guardian/homework` (`?status=active\|completed`), `/{id}`, `/{id}/attachments/{id}/download` | homework.py:346+ | homework/diary items, resource_links, attachments | Yes |
| `POST/DELETE /api/guardian/homework/{id}/done` | homework.py:370,380 | toggles `HomeworkItemCompletion` (unique per item + guardian_user_id) | Yes — but see §3.4 completion-identity note |
| `GET /api/guardian/updates`, `/{id}`, `/{id}/photos/{id}/view` | updates.py:304+ | update posts + photo metadata; photo bytes streamed via `_photo_response` | Yes |
| `GET /api/guardian/calendar?start=&end=` | calendar.py:417 | calendar events + homework due dates merged, sorted | Yes |

### 3.2 Linking / invite endpoints (the pattern to copy)

| Endpoint | File | Notes |
|---|---|---|
| `GET/POST /api/school/students/{id}/guardian-invites` | school.py:2659,2691 | admin creates guardian invite; short-code token, hash stored (`token_hash` unique), 30-day TTL, `display_code_last4` |
| `POST /api/school/guardian-invites/{id}/revoke` | school.py:2763 | invite revocation |
| `POST /api/school/guardian-links/{id}/revoke` | school.py:2809 | **school-side link revocation already exists** |
| `GET /api/join/guardian` / `/details` / `POST /confirm` | join.py | preview → authed details (student first name, class, already_linked) → confirm creates/reactivates `GuardianLink`, audits, ensures guardian membership. Rate-limited (10/min/IP), generic 404 error to avoid token oracle |

This is exactly the preview→confirm→durable-link shape Part 7 asks for; the FHH flow is
a service-to-service re-skin of it.

### 3.3 Staff/teacher/school endpoints

`/api/teach/*` (dashboard, students/search, homework/updates/announcements/calendar
CRUD, behaviour events) and `/api/school/*` (full SIS CRUD: branches, stages, years,
grade levels, class sections, subjects, subject groups, teachers, students, imports,
enrolments, behaviour categories, announcements, calendar) are **out of scope for FHH**
— never expose. The only touchpoint: the QR-issuance UI for FHH invites belongs beside
the existing guardian-invite UI in the school/teach frontends.

### 3.4 Relevant models (models_school/models.py)

- `GuardianInvite` (l.431): token_hash unique, expires_at (30d default), revoked/claimed
  audit fields, slot/contact linkage.
- `GuardianLink` (l.463): unique (student_id, user_id), status active/revoked,
  revoked_at/by, relationship, `email_matched_contact`.
- `HomeworkItemCompletion` (l.646): unique (homework_item_id, **guardian_user_id**) —
  completion identity is a CHH user. See §6.3 for how the integration handles this.
- Content models (Announcement, HomeworkItem, UpdatePost/UpdatePhoto, CalendarEvent,
  BehaviourEvent/Category) all carry school_id + audience_type
  (school/class_section/subject_group) with DB check constraints.
- `AuditLog` (l.763) + `write_audit(db, actor, action, entity, detail, school_id)`
  (school_scope.py:27) — reusable for integration auditing.

### 3.5 Reusable infrastructure

- `invite_tokens.py`: `generate_token()` (43-char urlsafe), `hash_token()` (SHA-256),
  `generate_short_code()`/`normalize_short_code()` (`CHH-XXXX-XXXX`), `exchange_invite()`
  generic consume-with-rate-limit, `revoke_token()`.
- `security.py`: `BoundedInMemoryRateLimiter`, trusted-proxy IP extraction.
- `database.py`: strict settings validation (fails closed on placeholder/short secrets
  in production) — the integration service token should plug into this validator.
- File serving: attachments/photos stored on disk under `HOMEWORK_UPLOAD_DIR` /
  announcement/update equivalents, streamed via authenticated FileResponse routes —
  there are no public URLs, which is the right starting point for §6.4.

---

## 4. FHH structure summary

Backend mirrors CHH: FastAPI, `backend/app/routes/`, SQLAlchemy models in one
`models.py`, alembic, docker-compose, Caddy, SvelteKit frontend (+ Capacitor native
Android/iOS — camera access for QR scanning is plausible; there is already an in-app
QR display flow for child devices).

- **Auth:** parent session cookie (web) or bearer token (native) → `ParentUser`;
  child devices use a separate `child_session` opaque-token session
  (`child_auth.py`), created by exchanging a `ChildDeviceInvite` QR token
  (`/api/child-link/exchange` and `/exchange-native`). CSRF double-submit for web.
- **Family scoping:** `routes/family_scope.py::get_family_child_or_404` — every
  child-scoped route checks `child.family_id == current_parent.family_id`.
- **Models:** ParentUser, Family, FamilyInvite, Child (id, family_id, display_name,
  avatar_name, active), ChildDeviceInvite/Session, CalendarEntry, SchoolItem(+Check)
  ("school bag" packing — home-side, unrelated to CHH), LedgerTransaction (home
  points), RedemptionRequest, Reward, PetProgress, WeeklyStreak, allowance,
  DevicePushToken.
- **Frontend:** `frontend/src/lib/api.ts` central fetch wrapper (cookie or native
  bearer, CSRF header, child-session path awareness). Parent dashboard
  `routes/parent/+page.svelte` (single large page, `onMount(loadDashboard)`, no
  interval polling — refreshes on action), child dashboard `routes/child/[id]/+page.svelte`,
  child-device landing `routes/child-link/`.
- **Server-to-server:** `httpx` and `requests` are already in `backend/requirements.txt`;
  no outbound API client exists yet. Env pattern is flat vars in `.env` consumed by a
  validated settings module (same shape as CHH) — e.g. `API_BASE_URL`, `JWT_SECRET`,
  `TRUSTED_PROXY_IPS` (names only).
- **Where school data fits:** a new "School" card/section on the parent dashboard per
  child (beside points/allowance/school-bag cards), and optionally a read-only slice on
  the child dashboard later. Connection storage: new `school_connections` table keyed
  by `child_id` + `family_id` (see §9).
- **Important separation:** FHH's existing QR flow is *parent → child device*
  (ChildDeviceInvite). The CHH school link QR is *school → parent* and must be a
  distinct scan entry point and distinct token namespace (CHH short codes are prefixed
  `CHH-`, which already disambiguates).

FHH repo state caveat: `develop` has substantial uncommitted work (push notifications,
privacy acknowledgements) touching `models.py`, `schemas.py`, parent/child pages —
integration slices touching those files should rebase on whatever lands.

---

## 5. Proposed integration architecture

```
Parent's phone (FHH app)                FHH server (10.250.50.1)             CHH server (10.250.50.5)
  scan QR / enter CHH-code  ──────────▶  POST /api/children/{id}/school-connections/verify
                                            │  (parent session auth)
                                            ▼
                                         CHH client (httpx, mesh IP)  ─────▶  POST /api/integrations/fhh/link/verify
                                            │                                   (service bearer token)
  confirmation screen  ◀────────────────  safe preview payload  ◀────────────  school/child/class/expiry
  parent confirms  ────────────────────▶  .../school-connections (POST)  ───▶  POST /api/integrations/fhh/link/consume
                                            store link_id + link_token  ◀────  durable revocable fhh_link
  dashboard  ◀──────────────────────────  GET .../school (bundle)  ──────────▶ GET /api/integrations/fhh/links/{id}/dashboard
```

Principles:

1. **FHH's browser/app never talks to CHH.** All CHH traffic is FHH-server → CHH-server
   over the mesh. Attachments/photos are proxied through FHH (§6.4).
2. **CHH exposes a purpose-built `/api/integrations/fhh/*` router** — its own module,
   its own auth dependency, its own response schemas. Existing guardian helpers
   (`_guardian_audience` clause-building, `guardian_points_payload`, homework/updates
   payload builders) are reused *internally*, generalised to accept an explicit
   (school_id, student_id, section_ids, group_ids) scope instead of `current_user`.
3. **One bundle endpoint for the MVP dashboard**; detail/action endpoints only where
   needed (homework done, attachment/photo bytes). This minimises round trips over the
   mesh, matches FHH's load-on-mount pattern, and keeps the contract small. Split into
   per-resource endpoints later only if payload size or cache needs force it.
4. **Strictly one-way data flow** plus two explicit write-backs: homework done/not-done
   and link removal. The integration API accepts no other FHH-originated data; request
   schemas make it structurally impossible to send family data.

## 6. Proposed endpoint contract (CHH side)

All under `/api/integrations/fhh`, all requiring `Authorization: Bearer <FHH_SERVICE_TOKEN>`.

### Linking

- `POST /link/verify` — body `{ "code": "CHH-XXXX-XXXX" | raw token }`.
  Validates an *FHH link invite* (not consumed/revoked/expired, school active, student
  active). Returns confirmation-safe data only:
  `{ school_name, school_name_ar, student_display_name, class_section_name, grade_level_name, expires_at }`.
  No IDs beyond what's needed, no points/content. Rate-limited, generic 404 on any
  failure (mirrors join.py's `GENERIC_JOIN_ERROR` anti-oracle behaviour).
- `POST /link/consume` — body `{ "code": ..., "fhh_child_ref": "<opaque FHH-side id>" }`.
  Atomically marks the invite consumed and creates an `fhh_links` row. Returns
  `{ link_id, link_token, school, student, created_at }` where `link_token` is a fresh
  high-entropy per-link secret (hash stored CHH-side). Idempotent re-consume of an
  already-claimed invite fails closed.
- `DELETE /links/{link_id}` — parent-initiated unlink from FHH. Sets revoked_at.

### Dashboard bundle

- `GET /links/{link_id}/dashboard` → the MVP payload:

```jsonc
{
  "school":   { "name", "name_ar", "logo?": null },
  "student":  { "display_name", "first_name", "initials", "avatar_url?",
                "class_section_name", "grade_level_name" },
  "points":   { "total", "recent_events": [ { "points_delta", "category_label",
                "category_type", "note?", "created_at" } ] },
  "homework": { "active":   [ { "id", "item_type", "title", "body", "due_at",
                                "target_name", "resource_links", "attachments":
                                [ { "id", "original_filename", "content_type", "size_bytes" } ],
                                "done": false } ],
                "completed": [ ...same shape, "done": true ] },
  "announcements": [ { "id", "title", "body", "audience_type", "target_name",
                       "created_at", "attachments": [...] } ],
  "updates":  [ { "id", "body", "author_name", "created_at",
                  "photos": [ { "id", "content_type" } ] } ],
  "calendar_upcoming": [ { "id", "kind": "event|homework_due", "title", "event_type?",
                           "starts_at", "ends_at?", "all_day", "target_name" } ],
  "permissions": { "can_mark_homework_done": true },
  "link": { "link_id", "status": "active" },
  "server_time": "2026-07-11T12:00:00Z"
}
```

Sensible caps (mirror guardian routes): homework 100, announcements ~20, updates 50,
calendar next 30 days. Bodies included (guardian list endpoints omit bodies, detail
adds them — for MVP one bundle with bodies is simpler; revisit if payloads grow).

### Details / actions

- `GET  /links/{link_id}/homework/{item_id}` — full item (fallback/deep-link).
- `POST /links/{link_id}/homework/{item_id}/done` and
  `DELETE .../done` — write-back, audited.
- `GET  /links/{link_id}/homework/{item_id}/attachments/{attachment_id}/download`
- `GET  /links/{link_id}/announcements/{announcement_id}/attachments/{attachment_id}/download`
- `GET  /links/{link_id}/updates/{post_id}/photos/{photo_id}/view`

Every route: (1) service token valid, (2) link exists, active, not revoked, matches the
per-link `link_token` (sent as `X-FHH-Link-Token` header, compared by hash), (3) the
requested resource falls inside that link's student audience — computed with the same
clause logic as `_guardian_audience` but for exactly one student. 404 on any mismatch.

### 6.3 Homework-completion identity

`HomeworkItemCompletion` is unique per (item, guardian_user_id). Options:

- **(a) Recommended for MVP:** each `fhh_links` row references the `guardian_links` row
  it was issued against (FHH invites are issued per student like guardian invites, and
  can carry an optional guardian association). If the school issued the FHH invite
  without a CHH guardian account existing, create a *shadow* completion identity: add a
  nullable `fhh_link_id` column to `homework_item_completions` with a partial unique
  index (item_id, fhh_link_id), so FHH completions don't require a CHH user row.
- (b) Auto-provision a CHH `User` per FHH link — rejected: creates phantom accounts,
  complicates auth/email logic.

Teachers today don't see completion state (it's parent-side tracking), so (a) is low
risk; if teacher visibility is added later, both identity types aggregate the same way.

### 6.4 Attachments & photos strategy

MVP: **FHH server proxies bytes.** FHH exposes
`GET /api/children/{child_id}/school/attachments/...` (parent-session-authed), which
streams from the CHH integration download route (service token + link token) using
httpx streaming. Pros: no CHH exposure to devices, CHH auth model unchanged, works on
web and native. Cons: double bandwidth through FHH — acceptable at POC scale, photos
are already size-capped on upload. Later option: short-lived signed URLs from CHH if
both apps share a public edge.

## 7. Security model

POC (S17–S19):

- **Transport:** mesh/private IPs only (10.250.50.1 → 10.250.50.5). The integration
  router is additionally guarded by an IP allowlist (`FHH_INTEGRATION_ALLOWED_IPS`,
  reusing `parse_ip_networks`/`is_ip_trusted` from security.py) so even if Caddy/
  cloudflared exposes the path publicly by accident, requests fail closed. Do not
  publish `/api/integrations/*` in the public Caddyfile/cloudflared config.
- **Service auth:** static bearer token, ≥32 chars, stored as env on both servers —
  CHH: `FHH_INTEGRATION_SERVICE_TOKEN` (validated by database.py's secret validator:
  required non-placeholder in production, feature disabled + routes 404/503 if unset);
  FHH: `CHH_API_BASE_URL` (e.g. `http://10.250.50.5:<port>`), `CHH_SERVICE_TOKEN`,
  `CHH_INTEGRATION_ENABLED`. Compare with `hmac.compare_digest`.
- **Per-link auth:** the per-link `link_token` (hash stored in `fhh_links`) accompanies
  every link-scoped call. Service token proves "this is the FHH server"; link token
  proves "this FHH server still holds the credential minted at consume time". Revocation
  of either kills access.
- **Link-scope enforcement on every request** — no resource fetched by bare ID without
  re-deriving the student's audience.
- **No DB sharing** in either direction, ever.
- **No FHH→CHH data:** request schemas accept only codes/ids/the done flag.
- **Audit:** `write_audit` on link verify-success, consume, revoke, homework done/undo,
  and (sampled or on-failure) content access. Actor = a sentinel (`actor_user_id`
  nullable or a dedicated system user) + `fhh_link_id` in detail.
- **Rate limiting:** `BoundedInMemoryRateLimiter` per IP + per link (verify/consume
  tight, e.g. 10/min; reads looser, e.g. 60/min/link).
- **Fail closed:** missing/blank/placeholder token config disables the router entirely.
- **Revocation:** school-side (per link, per student, or school-wide kill via
  `FHH_INTEGRATION_ENABLED=false`), parent-side (DELETE from FHH), and platform-side
  (rotate service token).

Production later: keep mesh/VPN (WireGuard already runs on dev: `wg-easy`) or same-VPC
private networking; if public HTTPS ever needed, upgrade to per-instance mTLS or signed
requests (HMAC with timestamp/nonce) + token rotation; never direct DB access.

## 8. QR / linking model

Two token layers, deliberately mirroring guardian invites vs. sessions:

1. **FHH link invite (short-lived, single-use).** Created by school admin (later:
   class teacher) from CHH UI next to the existing guardian-invite button. Token =
   `generate_short_code()` 8-char code displayed `CHH-XXXX-XXXX` + QR encoding of a
   URL/payload containing the code. Only the SHA-256 hash is stored
   (`token_hash` unique). **TTL 72 h** (vs 30 d for guardian invites), single-use
   (`consumed_at`), revocable, `display_code_last4` for the office to identify printed
   codes. Carries school_id + student_id (+ optional guardian_link/contact reference).
2. **FHH link (durable).** Created at consume time. No expiry; revocable by school and
   parent. Per-link secret `link_token` (hash stored). Unique constraint prevents
   duplicate active links for the same (invite) and limits active links per student to
   a sane cap (e.g. ≤4 — two parents × two devices/households).

Flow (matches the required 10 steps): print/show QR → parent scans in FHH (or types
the code — same normalizer as join.py strips the `CHH` prefix) → FHH server →
`/link/verify` → FHH shows confirmation card (school name, child display name, class,
expiry) → parent confirms → `/link/consume` → FHH stores `{link_id, link_token,
school/student display snapshot}` → dashboard calls → school or parent can revoke.

QR payload should be an FHH deep link (e.g. `https://<fhh-host>/school-link?c=CHH-...`)
so the phone's camera app routes into FHH; FHH's scan screen also accepts manual entry.

**Separation from FHH child-device QR:** different scan entry point, different token
prefix (`CHH-`), different backend namespace. A child's FHH device session never gains
school data access in MVP; a child-dashboard school view later reads through the
parent-established connection server-side, still without new CHH credentials.

## 9. FHH UI behaviour rules

- **No link ⇒ no school UI.** No empty placeholder panels; the only affordance is an
  "Add school connection" action tucked into the child settings/manage sheet (so
  non-CHH schools' families see essentially nothing).
- Once linked: a distinct **School card/section per child** on the parent dashboard
  (clearly branded as school data, e.g. school name header) showing the §6.2 bundle.
- School data is display-only except homework done toggle.
- FHH home points and school points are never merged, summed, or cross-posted.
- Unlink: child settings → remove school connection (confirm dialog); also render a
  "connection revoked by school" state gracefully when CHH returns 404/410 for the link.
- Refresh: fetch bundle in `loadDashboard` (FHH's existing on-mount/on-action pattern);
  no interval polling in MVP. FHH may cache the last bundle briefly (e.g. 60 s in-process)
  to keep mesh chatter low.
- Privacy copy: linking screen states what flows in (school→family, listed data) and
  that nothing about the family is sent to the school beyond homework done marks.

## 10. Gap analysis

### CHH needs (nothing integration-specific exists today)

| Gap | Notes |
|---|---|
| `routes/integrations_fhh.py` router | new module, mounted at `/api/integrations/fhh`, absent from public proxy config |
| Service auth dependency | bearer check + IP allowlist + enabled flag; fail-closed |
| Models + migration: `fhh_link_invites`, `fhh_links` | per §8; plus nullable `fhh_link_id` on `homework_item_completions` (partial unique index) |
| Invite issuance endpoint + UI | `POST /api/school/students/{id}/fhh-invites` (+list/revoke), button beside guardian invites; QR render (guardian invite UI already prints codes — check for reusable component) |
| Per-link scope helper | refactor `_guardian_audience` clause-building to accept explicit student scope; reuse `guardian_points_payload` equivalent for one student |
| verify/consume/revoke + dashboard bundle + detail/action routes | per §6 |
| Attachment/photo integration download routes | reuse existing `_file_response`/`_photo_response` |
| Audit log calls, rate limiters | reuse `write_audit`, `BoundedInMemoryRateLimiter` |
| Config: `FHH_INTEGRATION_ENABLED`, `FHH_INTEGRATION_SERVICE_TOKEN`, `FHH_INTEGRATION_ALLOWED_IPS` | wire into database.py validation |
| Tests | token auth (missing/wrong/disabled), invite lifecycle (expiry/single-use/revoked), scope enforcement (cross-student 404s), bundle shape, done toggle, download authz |

### FHH needs

| Gap | Notes |
|---|---|
| `school_connections` model + migration | child_id (unique or per-provider unique), family_id, provider (`chh`), remote link_id, link_token (encrypted-at-rest or hashed? — must store raw to replay: store raw in DB, rely on DB/host security; note as open question), display snapshot (school/student/class names), status, created_at, revoked_at |
| CHH client service | `services/chh_client.py` using httpx, base URL + tokens from env, timeouts, error mapping (link-revoked vs CHH-down) |
| Config: `CHH_API_BASE_URL`, `CHH_SERVICE_TOKEN`, `CHH_INTEGRATION_ENABLED` | fail closed: integration UI hidden if unset |
| Routes: verify/confirm/unlink under `/api/children/{child_id}/school-connection` + `GET .../school` bundle passthrough + attachment/photo proxy | all parent-session-authed, family-scoped via `get_family_child_or_404` |
| Scan/enter-code UI + confirmation screen | new route e.g. `/school-link`; camera scan on native (new capability — check Capacitor barcode plugin), manual code entry everywhere |
| Parent dashboard School card | conditional render on connection presence |
| Unlink flow + revoked-by-school state | |
| i18n strings + privacy copy update | FHH is bilingual like CHH |
| Tests | connection CRUD authz, client error handling (mock CHH), no-school-UI-when-unlinked |

## 11. Implementation plan (slices)

- **S17 — CHH Integration API Foundation** (CHH only, deployable dark)
  Config + fail-closed service auth dependency; `fhh_link_invites`/`fhh_links` models +
  migration; school-admin invite issuance/list/revoke endpoints (+minimal UI);
  `/link/verify` + `/link/consume` + `DELETE /links/{id}`; dashboard bundle endpoint
  (reusing refactored per-student scope helpers); tests. No FHH changes; testable with curl
  from dev over the mesh.
- **S18 — FHH School Link Setup** (FHH)
  Env/config + `chh_client`; `school_connections` model/migration; verify/confirm/
  unlink routes; scan/enter-code + confirmation UI; store connection. Depends on S17.
- **S19 — FHH Linked School Dashboard** (FHH + small CHH additions)
  School card rendering the bundle (points, homework active/completed, announcements,
  updates, calendar); attachment/photo proxy routes + viewer; no-link ⇒ no UI rule;
  revoked-state handling.
- **S20 — Limited write-back** (both)
  Homework done/not-done end-to-end (CHH completion identity per §6.3 if not done in
  S17); parent unlink polish; school-side revoke UI in CHH (list active FHH links per
  student, revoke button).
- **S21 — Hardening**
  Rate limits tuned, audit coverage, revocation edge cases (mid-session revoke),
  integration tests exercising real mesh calls dev→restore, privacy/docs (FHH privacy
  page + CHH blueprint update), token rotation runbook, production auth notes.

Order rationale: S17 is independently testable and unblocks everything; write-back is
deferred past read-only display so the riskiest surface (any FHH→CHH write) lands after
the auth model has soaked.

## 12. Risks & open questions

1. **FHH `develop` is dirty** — S18/S19 must sequence after the push-notification work
   lands (models.py/schemas.py/parent page all touched).
2. **Link-token storage on FHH** must be replayable, so it's stored raw (unlike CHH
   hashes). Mitigation: mesh-only transport, DB on same host, revocable. Flag for Dom.
3. **Who may issue FHH invites** — school admin only at first, or class teachers too?
   MVP: school admin (matches guardian invites); teacher issuance is a follow-up.
4. **Invite ↔ guardian relationship**: should an FHH invite require an existing CHH
   guardian link/contact, or be issuable for any student? MVP: any active student, with
   optional association — schools without CHH-guardian rollout can still offer FHH.
5. **In-memory rate limiters** are per-process; fine for single-container CHH, revisit
   if CHH scales out.
6. **Avatar/photo URLs in the bundle** must not leak CHH-internal URLs; either omit
   avatars in MVP or proxy like photos.
7. **Timezone/locale**: CHH is bilingual (name_ar) and Oman-based; bundle carries UTC
   timestamps and both name variants, FHH renders per its locale.
8. **Native QR scanning** capability in FHH Capacitor app is assumed but unverified —
   manual code entry is the guaranteed fallback.
9. **Multiple FHH families per student** (divorced households): allowed by design (each
   invite → one link); cap active links per student.

## 13. Recommended next slice — S17 prompt outline

> **S17 — CHH Integration API Foundation.** In CHH: (1) add
> `FHH_INTEGRATION_ENABLED` / `FHH_INTEGRATION_SERVICE_TOKEN` /
> `FHH_INTEGRATION_ALLOWED_IPS` to settings with production validation, router mounted
> only when enabled and token valid — fail closed; (2) new models + alembic migration:
> `fhh_link_invites` (token_hash unique, expires_at 72h, consumed/revoked audit
> columns, school_id, student_id, created_by) and `fhh_links` (link_token_hash,
> school_id, student_id, source invite, fhh_child_ref, status, revoked audit columns,
> unique active-per-invite); (3) school-admin endpoints to create/list/revoke FHH
> invites for a student (mirror guardian-invite endpoints in school.py:2659-2825,
> reuse invite_tokens helpers) + minimal UI button beside guardian invites; (4)
> integration router `/api/integrations/fhh` with service-auth dependency
> (bearer + IP allowlist + rate limits + `hmac.compare_digest`), `POST /link/verify`,
> `POST /link/consume`, `DELETE /links/{link_id}`, `GET /links/{link_id}/dashboard`
> returning the §6.2 bundle by refactoring `_guardian_audience`/guardian payload
> helpers to take an explicit single-student scope — do not change guardian route
> behaviour; (5) `write_audit` on verify/consume/revoke; (6) tests: auth failures,
> disabled config 404s, invite lifecycle, cross-student scope 404s, bundle shape.
> Read `docs/implementation/CHH_FHH_INTEGRATION_API_AUDIT.md` first. No public proxy
> exposure. Minimal-code philosophy applies.

---
*Audit performed read-only on 2026-07-11. No code, migrations, services, commits, or
pushes were touched in either repo.*

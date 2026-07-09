# S9 — Guardian QR Onboarding: Plan (2026-07-09)

Status: **planning only — no implementation, no migrations, no code changes.**

Grounding: this plan was written against the actual code at commit `ee5a021`
(models in `backend/app/models_school/models.py`, auth in
`backend/app/routes/authentication.py`, invite token machinery in
`backend/app/invite_tokens.py`, scope guards in `backend/app/school_scope.py`),
the master blueprint §8/§9/§18, and the S7 correction entry in the
implementation log (which created `student_guardian_contacts` specifically as
S9's input).

---

## 1. Product recommendation for the S9 MVP

Ship the blueprint §18 **letter-token model**, admin-only, one student at a
time, with the smallest possible post-link surface:

- A school admin, from a student's row on the `/school` Students tab, generates
  a **per-guardian-slot invite** (up to 2 active at a time, matching the S7
  slot model). Where a draft `student_guardian_contact` exists for that slot,
  the invite is generated *from* it and displays as
  **"Fatima Ahmed · Mother"** — never as a raw email.
- The invite is a short human-typeable code (e.g. `CHH-7K3M-92QT`) plus a QR
  encoding `https://<app>/join?c=CHH-7K3M-92QT`. Admin prints a simple one-page
  letter (or just copies the code) and the school hands it to the family.
- The guardian scans/types the code on a public `/join` page that shows **only
  the school name** pre-auth, signs in with Google or magic link (both already
  auto-create/reuse a `User`), then sees a confirmation card with the student's
  **first name + class** and a relationship picker, and confirms.
- Confirming creates a `guardian_link` (user ↔ student), ensures a
  `Membership(role="guardian")` row, marks the invite used, flips the draft
  contact to `linked`, and lands the guardian on a tiny "You're connected to
  Sara" success page. **The full guardian dashboard is S10.**

Why this shape: it reuses every existing primitive (token hash/expiry/revoke in
`invite_tokens.py`, Google + magic-link auto-create-User auth, the
`Membership` role model, the S7 draft contacts), sends **zero outbound email**
(the letter is physical/manual — consistent with the S7/S8 binding
no-outbound rule), and defers everything a guardian would *do* after linking.

Key product decisions (each argued in §6/§8 below):

| Question | Decision |
|---|---|
| One family code or per-guardian codes? | **Per guardian slot** (blueprint §18: "one token = one guardian slot"), single-use |
| Approval queue for unmatched emails? | **No** — possession of the letter is the authorization (blueprint §18 explicitly rejects approval); mismatches are *recorded and surfaced*, not blocked |
| User created at invite time? | **No** — only after Google/magic-link auth, via the existing auth flows, unchanged |
| Teacher-generated invites? | **Admin-only in S9**; teacher generation is a school setting for later |
| Bulk per-class letter printing? | **Deferred** to a follow-up slice (S9c) — per-student first, pilot schools start small |

## 2. Exact user flows

### 2a. School admin flow

1. `/school` → Students tab → a student row gains a **Guardians** panel
   (expand or detail view). It shows, per slot 1/2:
   - the draft contact, displayed as `name · relationship` ("Fatima Ahmed ·
     Mother"; email shown only as secondary small text for the admin, never as
     the primary label; a contact with no name shows "Guardian 1"),
   - contact status (`draft` / `linked` / `ignored`),
   - any active invite for the slot (created date, expiry, status),
   - any active `guardian_link` (linked user's name, relationship, linked date).
2. Admin clicks **"Generate invite"** on a slot → backend creates a
   `guardian_invite` and returns the raw code + join URL **once** (only stored
   hashed). UI shows the code, the QR, a **Print letter** button, and a copy
   button.
3. **Print letter** opens a print-styled view: school name (EN/AR), student
   first name + class, addressed to the contact name/relationship where known
   ("For Fatima Ahmed (Mother of Sara Ahmed)"), QR, the typed code, bilingual
   instructions ("Scan or visit `<app>/join` and enter this code"), and the
   expiry date.
4. Admin can **Revoke** an invite (lost/misdelivered letter) and generate a
   fresh one; revoking one slot's invite never touches the other slot.
5. Admin can mark a draft contact **Ignored** (wrong data, custody issue) —
   ignored contacts can't have invites generated from them; the admin can
   still generate a blank-slot invite deliberately.
6. Admin can **Revoke a guardian link** later (custody change); revocation
   takes effect on next request via the same status-check idiom used for
   memberships.

### 2b. Printed QR/code flow (what's physically on the paper)

One A5/A4 page per guardian slot: school name (+ Arabic name), "Connect with
**Sara** — Class KG 1 A", the QR (encodes the full join URL), the typed code in
large monospace groups (`CHH-7K3M-92QT`), EN/AR instructions, expiry date,
and a "if you did not expect this letter, return it to the school office"
line. No guardian email printed. QR is rendered client-side with the
already-installed `qrcode` npm package (no new dependency, no backend image
generation).

### 2c. Guardian flow

1. Scan QR → lands on public `/join?c=CHH-7K3M-92QT` (or visits `/join` and
   types the code). Page calls a rate-limited public preview endpoint and
   shows **only**: "You've been invited to connect with a student at
   **United International School**." No student name, no class, pre-auth.
2. Guardian taps **Continue with Google** (with `return_to=/join?c=…`) or
   enters an email for a **magic link** (`returnTo=/join?c=…`). Both existing
   flows auto-create or reuse the `User` and return to `/join?c=…` signed in.
3. Signed in, the page calls the authenticated claim-preview endpoint and
   shows the confirmation card: student **first name + class section name**,
   plus a relationship selector (mother/father/guardian/other) pre-filled from
   the draft contact's relationship when the invite was generated from one.
   Copy: "Are you Sara Ahmed's mother? Confirm to connect."
4. Guardian confirms → link created → success page: "You're connected to
   **Sara** ✓. The school will switch on your family updates soon." plus a
   list of all children this account is linked to, and (if signed in already
   with another child linked) this doubles as the sibling add flow — same
   code entry on `/join`, same account.
5. Done. No dashboard yet (S10).

### 2d. Failure / retry flows

| Case | Behaviour |
|---|---|
| Invalid/unknown code | Generic "This code is not valid or has expired. Please contact the school office." (same message for invalid/expired/revoked — don't leak which) |
| Expired / revoked code | Same generic message; admin regenerates from the student page |
| Already-used code (photo forwarded, or guardian retries) | If the *same signed-in user* already holds the link: show the success page (idempotent, safe retry). Otherwise the generic invalid message. |
| Student archived, or school suspended, between print and scan | Generic invalid message (checked at preview and at confirm) |
| Guardian signs in but abandons before confirming | Nothing created; invite stays unused and valid |
| Same user, second child | Works — one `User`, second `guardian_link` |
| Same user scans both slots of the same student | Second confirm rejected: "You are already connected to this student" (one active link per user × student); the second invite stays unused for the real second guardian |
| Rate limit hit | 429 with a "try again in a minute" message |

## 3. Data model proposal

Two new tables (both already sketched in blueprint §9), one migration, no
changes to existing tables.

```
guardian_invites
  id                     PK
  school_id              FK schools NOT NULL, indexed
  student_id             FK students NOT NULL, indexed
  contact_id             FK student_guardian_contacts NULL   -- set when generated from a draft contact
  slot                   INT NULL CHECK (slot IN (1,2))      -- copied from contact, or chosen for blank-slot invites
  relationship_hint      TEXT NULL CHECK in ('mother','father','guardian','other')
  token_hash             TEXT UNIQUE NOT NULL                -- sha256 of the normalized typed code
  created_by_user_id     FK users NOT NULL
  created_at             timestamptz default now()
  expires_at             timestamptz NOT NULL                -- default now() + 30 days
  revoked_at             timestamptz NULL
  revoked_by_user_id     FK users NULL
  accepted_at            timestamptz NULL                    -- single-use: set on confirm
  accepted_by_user_id    FK users NULL
  INDEX (school_id, student_id)

guardian_links
  id                     PK
  school_id              FK schools NOT NULL, indexed
  student_id             FK students NOT NULL, indexed
  user_id                FK users NOT NULL, indexed
  relationship           TEXT NOT NULL CHECK in ('mother','father','guardian','other')
  display_name           TEXT NULL      -- from draft contact name; falls back to User.name in UI
  status                 TEXT NOT NULL default 'active' CHECK in ('active','revoked')
  created_via            TEXT NOT NULL default 'invite' CHECK in ('invite','admin')
  source_invite_id       FK guardian_invites NULL
  source_contact_id      FK student_guardian_contacts NULL
  email_matched_contact  BOOLEAN NULL   -- did the authenticated email equal the staged contact email? NULL when no contact/no staged email
  created_at             timestamptz default now()
  revoked_at             timestamptz NULL
  revoked_by_user_id     FK users NULL
  UNIQUE (student_id, user_id)          -- one link row per pair; re-link after revoke = restore in place (S4 lifecycle idiom)
  INDEX (school_id, user_id)
```

Existing tables, used unchanged:

- `student_guardian_contacts` — S9 reads drafts for display/prefill and flips
  `status` `draft → linked` (on claim) or `draft → ignored` (admin action).
  Exactly the lifecycle the S7 model docstring reserved for S9. Re-imports
  already skip non-draft rows, so no import changes needed.
- `users` — created/reused only by the existing Google/magic-link auth code.
  **No new user-creation path.**
- `memberships` — on link creation, ensure an active
  `Membership(role="guardian")` for (school, user) (blueprint §8: guardian
  membership is created/removed automatically with links so `/api/me` and
  access checks have one source of truth). On revoking a user's **last**
  active link in a school, revoke that guardian membership too.
- `audit_logs` — every generate / claim / revoke / ignore writes an entry.

Why **no reuse of `StaffInvite`**: it is email-bound (`email` column +
must-match-email check in `exchange_staff_invite`), role-based, and 7-day
single-recipient. Guardian invites are student-bound, deliberately *not*
email-bound (the letter model), 30-day, and need `contact_id`/`slot`. Forcing
both into one table means nullable-column soup and conditional validation —
two small honest tables beat one confused one. The *token mechanics*
(`generate_token`/`hash_token`/expiry/revoke/rate-limit from
`invite_tokens.py` + `security.py`) are reused as-is.

Token/code format: generate 8 random characters from a Crockford-style base32
alphabet (no `0/O/1/I/L/U`), displayed as `CHH-XXXX-XXXX` (~40 bits — see §6
for why that's sufficient here), normalized (uppercase, strip dashes/spaces)
before hashing with the existing `invite_tokens.hash_token`. Only the hash is
stored; the raw code is returned exactly once at generation.

## 4. Backend endpoint proposal

**Admin — `backend/app/routes/school.py`, under the existing
`require_school_role("school_admin")` router dependency:**

| Endpoint | Purpose |
|---|---|
| `GET /api/school/students/{student_id}/guardians` | One payload for the panel: contacts (name/relationship/status, email as admin-only detail), active+recent invites (status, expiry, slot, contact name — never the raw code), active links (linked user display name, relationship, `email_matched_contact`, created date) |
| `POST /api/school/students/{student_id}/guardian-invites` | Body: `{contact_id}` **or** `{slot, relationship_hint?}`. Validates student active + contact belongs to student + contact not `ignored` + no other unexpired unrevoked unused invite for the same slot (revoke-then-regenerate, never two live letters per slot). Returns `{invite_id, code, join_url, expires_at}` — the only time the raw code exists |
| `POST /api/school/guardian-invites/{invite_id}/revoke` | Sets `revoked_at`; idempotent |
| `POST /api/school/guardian-contacts/{contact_id}/ignore` | `draft → ignored`; also auto-revokes any live invite generated from that contact |
| `POST /api/school/guardian-links/{link_id}/revoke` | Sets `status='revoked'`; revokes guardian membership if it was the user's last active link in the school |

All writes audit-logged (`school.guardian_invite.created`, `.revoked`,
`school.guardian_link.revoked`, `school.guardian_contact.ignored`).

**Public/guardian — new small `backend/app/routes/join.py` (`/api/join`):**

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /api/join/preview?code=` | none | Rate-limited (reuse `BoundedInMemoryRateLimiter`, ~10/min/IP). Valid live code → `{school_name, school_name_ar}` **only**. Any other case → 404 with the one generic message |
| `GET /api/join/details?code=` | signed-in user | Same validation + student must be active + school not suspended → `{student_first_name, class_section_name, relationship_hint, already_linked}` |
| `POST /api/join/confirm` | signed-in user | Body `{code, relationship}`. Re-validates everything in one transaction: mark invite accepted (single-use), create-or-restore `guardian_link` (with `email_matched_contact` computed against the staged contact email via `auth.normalize_email`), ensure guardian membership, flip contact to `linked`, audit. Idempotent for the same user (returns success if the active link already exists) |

Consume-on-POST-only mirrors the existing magic-link SafeLinks fix: `GET`s
never mutate, so a link scanner can't burn an invite.

**Registration-order note:** the new literal routes under
`/students/{student_id}/…` must be registered before any conflicting
parameterized route in `school.py`, same Starlette gotcha the import routes
hit (see S7 log entry).

**Query shape:** the guardians panel endpoint is 3–4 batched queries fixed per
student, and `/api/join/*` endpoints are all single-token lookups — nothing
scales with school size. No `perf_check.py` additions needed (student-page
scale, not list scale).

## 5. Frontend page/UI proposal

- **`/join` (new public route):** code entry (pre-filled from `?c=`), school
  name reveal, Google/magic-link sign-in handoff (reusing the existing
  `/login` flows with `return_to`), post-auth confirmation card with
  relationship picker, success page. Mobile-first, EN/AR via the existing
  `svelte-i18n` setup.
- **`/school` Students tab:** per-student **Guardians** panel as described in
  §2a, plus the print-letter view (a print-styled component or
  `/school/guardian-letter` print route; QR via the installed `qrcode`
  package). Display rule enforced here: guardians render as
  `name · relationship` with "Guardian 1/2" fallback; email is secondary
  admin-facing detail only.
- **Naming rule as a shared helper** (`guardianDisplayName(contact|link)`),
  so S10/S15 inherit "never address guardians as raw emails" for free.
- **Note on the stale `/parent` route:** `frontend/src/routes/parent` is
  inherited FHH surface; S9 does not touch it. Guardians land on the success
  page; `/home` comes in S10 (blueprint §17). Flag for S10: either build
  `/home` or clean `/parent` up then.

## 6. Security / privacy rules

- **Entropy:** ~40 bits (8 chars × base32) for a **hand-typeable** code, and
  that is defensible only in combination with the other layers: hashed at
  rest, 30-day expiry, single-use, revocable, and an IP rate limit of ~10
  attempts/min on `/api/join/*`. Blind guessing needs on the order of 10¹¹
  attempts against a live code window at ~14k attempts/day/IP. The QR encodes
  the same code (URL form), so there is one code system, not two. If we ever
  drop the typed fallback, switch to the full 256-bit `generate_token`.
- **Expiry:** 30 days default (blueprint §18), checked at preview, details,
  and confirm.
- **One-time vs reusable:** **single-use** (`accepted_at` set atomically at
  confirm). This is the main anti-forwarding control: a photographed letter
  whose code was already claimed is dead, and if a stranger claims it first,
  the real guardian's failure ("code not valid") surfaces at the school
  office, where the admin sees who claimed it (`accepted_by_user_id`, audit
  log) and can revoke the link and reissue. Two guardians = two letters.
- **Revocation:** invites revocable pre-claim; links revocable post-claim;
  contact `ignored` kills its live invite. All admin-visible on the student
  page.
- **Audit trail:** generate/claim/revoke/ignore all write `audit_logs` with
  school_id, actor, student id, invite/link id — no emails or codes in
  `detail`.
- **Rate limiting:** `BoundedInMemoryRateLimiter` per IP on all three
  `/api/join` endpoints (stricter than the magic-link 20/min — say 10/min).
- **Per student or per guardian slot?** Per slot: single-use then works (a
  family code shared by two parents can't be single-use), each invite can
  carry its contact's name/relationship prefill, and revocation is per
  guardian, matching custody-dispute reality.
- **Safe pre-auth info:** school name only. Student first name + class appear
  only after authentication (there's an accountable `User` on record before
  any child data is shown). Never: surname beyond need ("Sara Ahmed" only on
  the printed letter and confirm card), DOB, gender, contact emails, roster.
- **Must the email match the staged contact?** **No** (blueprint §18:
  possession model; parents' real emails frequently differ from what the
  school has on file, and hard-matching would strand exactly the families
  with messy data). But the mismatch is **recorded** (`email_matched_contact
  = false` on the link + audit) and shown as a subtle badge in the admin
  panel so an admin reviewing links can spot anomalies.
- **Unmatched email → pending approval instead of active?** **No approval
  queue** (blueprint §18 explicitly rejects it: the approver has no way to
  verify the claimant, so it adds friction with zero security). Risk is
  bounded because S9's post-link surface is a success page only — before S10
  ships any real child data, admins have the mismatch badge + revoke.
- **Wrong-student prevention:** the token is bound server-side to exactly one
  `student_id`; there is no browse/search/enumerate path anywhere in
  `/api/join`; the confirm card shows the student's name so a guardian
  holding a misdelivered letter stops before linking; `UNIQUE(student_id,
  user_id)` prevents duplicate links; cross-school is impossible because the
  token resolves to one school's student and every write derives `school_id`
  from the invite row, never from client input.
- **No outbound communication:** S9 sends zero emails other than the
  guardian's *own* magic-link sign-in request (existing, self-initiated,
  already implemented — permitted by the constraints). Test must assert
  invite generation makes no mailer calls.

## 7. Deferred — and where to

| Deferred item | Where |
|---|---|
| Guardian home dashboard (`/home`), child cards, school switcher, PWA install + push prompt | **S10** |
| Bulk per-class letter generation/printing, link-status dashboard per class ("Release 214 invites" flow) | **S9c or S10-adjacent** |
| Teacher-generated invites (per school setting) | post-pilot |
| Approval-queue / "request access" mode for lost letters at scale | explicitly rejected for MVP (blueprint §18); revisit only with evidence |
| Messaging guardians ("Sara Ahmed's guardians" as recipients) | **S15** (S9's name·relationship display rule and `guardian_links` are its inputs) |
| Notifications (incl. "guardian linked" notify-admin) | **S16** |
| Posts/photos/diary | S11–S13 |
| Guardian profile/language settings page | S10 |
| WhatsApp anything | evaluate per blueprint follow-up, not S9 |

**Must not be built in S9:** any mass-email/"send invites by email" path (the
S7 contact emails stay cold), any guardian-facing student data beyond first
name + class, guardian browse/search of students, parent-to-parent anything,
password auth, native app deep links.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Letter photographed/forwarded, stranger claims first | Single-use + confirm-card speed bump + admin sees claimer + revoke/reissue; real guardian's failure surfaces at the office (§6) |
| Stranger claims and *is not noticed* | S9 exposes only first name + class post-link; mismatch badge; S10 should add a "recently linked guardians" review list before real data ships |
| Typed-code brute force | 40-bit space + 10/min/IP rate limit + expiry + generic error (no valid/invalid oracle distinction) |
| Magic-link scanner prefetch burns codes | Already solved pattern: GET never consumes; only authenticated POST confirms |
| Admin generates invite from a contact with a wrong/stale name | Letter shows student name prominently; guardian corrects relationship at confirm; contact fields aren't trusted as identity, only as display prefill |
| Same guardian double-links via both slots | `UNIQUE(student_id, user_id)` + idempotent confirm; second invite remains valid for the actual second guardian |
| Guardian membership drifts out of sync with links | Membership ensured/revoked inside the same transaction as link create/revoke; test both directions |
| Student archived / school suspended after letters go home | Checked at preview and confirm |
| `student_guardian_contacts` re-import overwriting linked state | Already handled in S7 (non-draft rows skipped on re-import, test-covered) |
| In-memory rate limiter resets on deploy / multi-process | Accepted for pilot scale (same as existing magic-link limiter); note for later hardening |
| Scope creep into "small dashboard" | Success page is static text + linked-children list; anything more is S10 |

## 9. Implementation slices

S9 as specified above is too big for one slice. Cut it as:

- **S9a — core backend + claim flow (build first):** migration
  (`guardian_invites`, `guardian_links`), admin endpoints (generate/revoke
  invite, guardians panel payload, ignore contact, revoke link), `/api/join`
  preview/details/confirm, guardian membership ensure/revoke, contact status
  flips, audits, rate limits, full test suite. Minimal UI: guardians panel on
  the Students tab (list + generate + code/URL display + revoke) and the
  `/join` page end-to-end. No printed letter yet (admin copies the code/URL —
  functional for a pilot family from day one).
- **S9b — printed letter + polish:** print-styled letter view with QR
  (installed `qrcode` pkg), bilingual letter copy, mismatch badge styling,
  link-revoke UI affordances, success-page linked-children list.
- **S9c (optional, may merge into S10 prep):** bulk per-class letter print +
  per-class link-status counts.

S9a alone is a complete, safe, pilot-usable vertical slice.

## 10. Implementation prompt for the S9a slice (Codex/Claude, paste-ready)

```
You are implementing S9a — Guardian Onboarding core — for Class Hero Hub at
/opt/apps/class_hero_hub. Read docs/planning/2026-07-09-s9-guardian-qr-onboarding-plan.md
first; it is the authoritative spec (§3 data model, §4 endpoints, §6 security
rules). Also read the S7/S8 entries in
docs/implementation/CLASS_HERO_HUB_IMPLEMENTATION_LOG.md for house patterns.

Coding philosophy (binding): write the minimum code that works. Reuse before
writing: invite_tokens.generate/hash/expiry/revoke helpers, BoundedInMemoryRateLimiter,
require_school_role, auth.normalize_email, write_audit, the existing Google +
magic-link auth flows (do NOT add any new auth or user-creation path). Do not
add dependencies. Do not cut corners on validation, error handling, or the
security rules below.

Build exactly:

1. Migration (single new head on top of `alembic heads`) adding
   guardian_invites and guardian_links exactly per plan §3, with the listed
   constraints/indexes. Models in backend/app/models_school/models.py
   (+ __init__.py exports).

2. Short-code helper in backend/app/invite_tokens.py: generate_short_code()
   returning 8 chars from a Crockford base32 alphabet (excluding 0,O,1,I,L,U)
   using `secrets`, and normalize_short_code(raw) that uppercases and strips
   spaces/dashes (accepts "chh-7k3m-92qt" and "7K3M92QT" alike; the "CHH-"
   prefix is display-only). Store only hash_token(normalized_code).

3. Admin endpoints in backend/app/routes/school.py under the existing
   school_admin router dependency, per plan §4 (guardians panel GET, invite
   POST, invite revoke, contact ignore, link revoke). Rules: one live invite
   per (student, slot) — reject with 409 telling the admin to revoke first;
   invite generation from an `ignored` contact rejected; ignoring a contact
   auto-revokes its live invite; revoking a user's last active link in the
   school also revokes their guardian membership; every mutation writes an
   audit entry; never return the raw code except from the generate response;
   never include contact emails in guardian *link* payloads (contact email may
   appear in the contacts section of the panel payload only). Register literal
   /students/{student_id}/guardian-* routes before parameterized conflicts
   (Starlette registration-order gotcha, see S7 log).

4. New backend/app/routes/join.py mounted at /api/join with preview (public),
   details (authenticated), confirm (authenticated POST), exactly per plan §4
   and security §6: 10/min/IP rate limit on all three; one generic error
   message for missing/expired/revoked/used codes (no oracle); preview returns
   school name(s) only; details/confirm require student active + school not
   suspended; confirm runs in one transaction: set accepted_at/by (single-use),
   create-or-restore guardian_link (UNIQUE(student_id,user_id); restore-in-
   place if a revoked row exists), compute email_matched_contact via
   normalize_email against the staged contact email (NULL if none), ensure
   active Membership(role="guardian"), flip source contact draft→linked,
   write_audit. Confirm is idempotent for an already-linked same user
   (return success, mutate nothing). GET endpoints must not mutate anything.

5. Frontend: (a) public /join route — code entry prefilled from ?c=, preview
   reveal (school name only), sign-in handoff to existing Google
   (return_to=/join?c=...) and magic-link (returnTo) flows, post-auth
   confirmation card (student first name + class + relationship picker,
   prefilled from relationship_hint), success page listing linked children;
   mobile-first, EN+AR i18n keys in messages.ts. (b) /school Students tab
   Guardians panel: per-slot contact display as "name · relationship" with
   "Guardian 1/2" fallback (email as small secondary admin-only text — never
   the primary label), generate invite (show code + join URL once, copy
   button), revoke invite, ignore contact, active links with
   email_matched_contact badge and revoke. Add a shared guardianDisplayName
   helper in frontend/src/lib. No printed letter view in this slice.

6. Tests (backend/tests/test_guardian_onboarding.py), covering at minimum:
   generate happy path (code returned once, hash stored); one-live-invite-per-
   slot 409; generate from ignored contact rejected; preview shows school name
   only and never student data; unauth details/confirm rejected; generic error
   for bad/expired/revoked/used codes; confirm creates link + guardian
   membership + flips contact to linked + sets accepted_at; email match true/
   false/NULL cases; relationship from payload overrides hint; confirm
   idempotent for same user; second user on used code rejected; same user two
   slots rejected via unique link; revoked link restore-in-place on re-claim
   with a fresh invite; last-link revoke also revokes guardian membership (and
   not when another child link remains); archived student and suspended school
   blocked at details+confirm; cross-school isolation (admin of school A
   cannot generate/revoke for school B's student; token never leaks other
   students); guardian role gets no /api/school or /api/teach access; rate
   limit 429; zero outbound communication (monkeypatch mailer.send_staff_invite
   and send_magic_login; assert zero calls and zero StaffInvite/MagicLoginToken
   rows from generate+claim); GET endpoints do not consume the invite; audit
   rows written for generate/confirm/revoke/ignore.

Validation before you finish (all must pass): full backend pytest in docker
compose per the log's commands; `cd frontend && npm run check` and
`npm run check:i18n` and `npm run build`; `alembic heads` single head. Do not
send any email. Do not touch imports code except reading contacts. Do not
build letters, bulk flows, messaging, notifications, posts, or any guardian
dashboard. Update docs/implementation/CLASS_HERO_HUB_IMPLEMENTATION_LOG.md
with an S9a entry following the existing format. Do not commit.
```

---

### Direct answers to the brief's 14 questions (index)

1. **What does the guardian scan/open?** An HTTPS URL `https://<app>/join?c=<code>` (QR) or types the code at `/join` — §2c.
2. **What's printed?** Per-slot letter: school name, student first name + class, QR + typed code, EN/AR instructions, expiry — §2b.
3. **Family code or per-contact code?** Per guardian slot, single-use — §1, §6.
4. **Wrong-student exposure?** Token bound to one student server-side; no browse path; confirm card; unique link — §6.
5. **Forwarded QR photo?** Single-use + expiry + revoke + rate limit + audit + minimal post-link surface — §6, §8.
6. **Identity claim?** Possession of the school-delivered code + authenticated email (Google/magic link); match recorded, not required — §6.
7. **User created when?** Only at authentication, by the existing auth flows — §3.
8. **Use of draft contacts?** Display (name · relationship), invite prefill (slot/relationship hint), email-match computation, status lifecycle — §3.
9. **Draft → linked when?** At successful confirm of an invite generated from that contact — §4 confirm.
10. **Different email?** Link still created; `email_matched_contact=false` recorded + admin badge; no approval queue — §6.
11. **No contacts yet?** Blank-slot invite (slot + optional relationship hint); flow identical; nothing to flip — §2a, §4.
12. **Post-link view?** Success page: connected confirmation + linked-children list only — §2c.
13. **S10?** Guardian home, PWA install/push moment, bulk letters, review list — §7.
14. **Must not build?** Mass email, richer student data pre-S10, browse/search, approval queue, messaging/posts/notifications, passwords — §7.

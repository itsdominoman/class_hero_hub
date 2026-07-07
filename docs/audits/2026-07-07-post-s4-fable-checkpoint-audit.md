# Class Hero Hub — Checkpoint Audit (post-S4, pre-S5)

**Date:** 2026-07-07
**Author:** Claude (Fable 5), fresh-eyes checkpoint audit — no code changed
**Scope:** S1a/S1b (identity/tenancy + auth v2), S2a/S2b (household removal + rebrand), DB reset, S3 (platform admin panel v1), S4 (school structure) including the three S4 cleanups (hide archived, edit records, restore-on-recreate lifecycle policy)
**Source of truth:** the codebase at commit `ecb7dca` ("Improve school setup lifecycle behaviour"), verified by direct inspection. Companion docs: `docs/CLASS_HERO_HUB_MASTER_BLUEPRINT.md`, `docs/implementation/CLASS_HERO_HUB_IMPLEMENTATION_LOG.md`.

---

## 1. Executive verdict

**On track, no hard stop.** S1–S4 are implemented cleanly, match the blueprint's spirit, and the lifecycle cleanup work (hide-archived, edit, restore-on-recreate) is genuinely well done — consistent policy, documented, tested (110 backend tests, two-school isolation everywhere).

**But do not start S5 yet.** There are **two schema decisions and one reliability fix** that S5/S6 will build directly on top of, and they are 10× cheaper to resolve now:

1. **Subject groups are hard-bound to exactly one class section** — this silently makes cross-section teaching sets (streamed maths sets, elective groups drawing from 7A+7B) impossible to model. The blueprint had `class_section_id NULL` for exactly this reason; the implementation made it `NOT NULL`. S5 assignments and S6 enrolments will cement this.
2. **`class_sections.homeroom_teacher_user_id` conflicts with the S5 design.** The blueprint says homeroom teacher = a `staff_assignments` row (`role='homeroom'`), referenced by *membership*, not user. If Codex builds S5 around this placeholder column there are two competing sources of truth.
3. **Invite emails can 500 the request after the school/invite is already committed.** `send_staff_invite` raises inside `create_school`; SMTP down → platform admin sees an error, retries, creates a duplicate school. S5 multiplies invite volume (dozens of teachers per school) — fix the failure mode first.

Recommended path: one short "S4.9" cleanup slice (Section 6), then S5.

---

## 2. Current implementation audit

**Solid:**
- Tenancy discipline: every S4 table has `school_id NOT NULL + index`; every route resolves scope via `require_school_role`; relationships validated with `_ensure_owned`; cross-school and wrong-role tests exist for list/create/update/archive/restore.
- The active/inactive/archived lifecycle policy is coherent and *the same for all seven entities*. Restore-in-place keyed on natural key with no schema change was the right call; keeping full unique constraints is exactly correct under restore-in-place.
- Relationships are by id, codes are safely editable (verified in tests), audit rows are written for restores/settings/platform actions.
- Invite token machinery (hashed, expiring, revocable, rate-limited) is properly inherited, and `StaffInvite.role` + the generic exchange endpoint mean S5 teacher invites are nearly free.
- Platform/school role separation is clean: platform admins are correctly *rejected* from `/api/school/*` (tested) — no accidental bypass path.

**Risky:**
- **Status is free text.** `StructureBase.status` accepts any ≤40-char string; nothing validates against `{active, inactive, archived}`. Worse, the frontend `StatusInput` *offers "Archived"* in the create/edit form — an admin who selects it makes the row vanish instantly, bypassing the trash-button semantics, with no visible recovery. A typo status like `"Active "` would break every `status == "active"` filter.
- **Tests run on SQLite** (`backend/tests/conftest.py` forces `DATABASE_URL=sqlite://`), directly contradicting blueprint §10 ("PostgreSQL-only for new work; tests run against PostgreSQL"). Harmless for S4 CRUD; a real gap at S7 (upsert semantics) and fatal at S14 (partial unique indexes / PG concurrency tests). Decide a PG-harness deadline now (recommend: S7 at the latest).
- **`write_audit` commits internally.** Fine for single-row CRUD; in S5+ multi-step operations (accept invite + create membership + close assignments) mid-flow commits will produce partially-committed states on failure. Convert to add/flush-in-caller's-transaction before building bigger flows.
- **`School.status` never leaves `pending_setup`.** Nothing transitions a school to `active` — not invite acceptance, not checklist completion. `require_school_role` only blocks `suspended`, so it works today, but any future logic keyed on "active school" (S16 notifications, S20 RLS, platform dashboards) will misfire.

**Missing (small boring admin features):**
- No way to remove/revoke a school-admin *membership* (only invites can be revoked).
- The invite accept URL is never surfaced in the platform UI — if the email fails, the only recovery is issuing another invite (and old pending invites for the same email stay valid; nothing auto-revokes them).
- No confirmation on archive (single tap on the trash icon). Restore-on-recreate softens this, but the row disappearing without warning is a "WTF" generator.
- Sections and subject-group forms have no status field, so they can't be set inactive from the UI (branches/stages/years/subjects/levels can). Inconsistent.

**Can wait:** PG test harness (needed by S7/S14), checklist label i18n (backend returns hardcoded English labels — an AR-locale admin sees an English checklist; fold into S17), migration-chain squash (fresh DBs still replay the whole FHH schema then drop it — ugly but correct; cosmetic).

---

## 3. School-structure model review

- **Branch/campus** — the model (first-class school-owned rows, required on sections, self-healing default `MAIN`) is right, and adding it pre-S5 was correct. Two caveats: (a) `_default_branch` actually returns "the first non-archived branch by sort order", not a designated default — for a multi-branch school, a section created without an explicit branch silently lands on whichever branch sorts first. Acceptable since the UI always sends it, but don't let the S7 CSV importer rely on it for multi-branch schools. (b) `memberships` has `UNIQUE(school_id, user_id, role)` — when branch-local admins arrive, one user can't be admin of two branches via two membership rows. Not a today-problem; don't pour concrete on it in S5.
- **Education stages** — good: optional, nullable on grade levels, school-defined. No issues.
- **Academic years** — the weakest entity. Only code/name/sort/status: **no `is_current`, no start/end dates**. S5 assignments are date-bounded ("valid_from = ?"), S6 enrolments need "which year am I enrolling into", and every year dropdown needs a default. The dual unique constraints (code AND name) also leave the documented restore corner-case. Add `is_current` (and ideally start/end dates) before S6, preferably in S4.9.
- **Grade/year levels** — good; configurable label, stage optional, keyed on code only.
- **Class sections** — structurally fine except `homeroom_teacher_user_id` (see §1) and the free-text `name` being both required and unconstrained (S7 auto-creation needs a naming rule — decide in the S7 prompt, not the schema).
- **Subjects** — fine.
- **Subject groups** — the one real modelling flaw, per §1. Recommendation: make `class_section_id` nullable, add nullable `grade_level_id` for context, and replace the unique constraint carefully (NULLs make plain unique constraints non-unique in Postgres — use a partial/expression index or keep uniqueness app-enforced via the existing `_find_by_natural_key`, which already handles it). One small migration now; a data-migration nightmare after S6.
- **Lifecycle** — consistent and sane across all seven entities. Gaps: status enum validation (§2); update-path 409s use the generic "Duplicate record" message and don't detect the "you renamed onto an archived row's code" case, which is invisible because archived rows are hidden — low priority.

---

## 4. Annoying-issue forecast

- **Setup/admin UX:** archive with no confirm; "Archived" selectable in status dropdowns; checklist items not clickable and English-only; "Basic setup complete" claims completion with 1 section and 1 grade level (accurate-ish but will mislead — consider "required steps complete"); quick-create with no grade level selected fires 400s mid-loop.
- **Permissions:** `require_school_role(...)` executes **twice per request** (router-level dependency + per-endpoint parameter are distinct closures, so FastAPI doesn't cache-dedupe them) — double school+membership queries on every call; drop the router-level one. Frontend `/school` picks *the first* school_admin membership — an admin of two schools can never reach the second.
- **Invites/auth:** exchange doesn't bind to the invited email — anyone who obtains the link becomes school admin (forwarded email, shared inbox). For *staff* invites, email binding is cheap and right. Exchange also works for suspended schools. A **revoked** admin can reactivate their membership with any still-pending invite token. Multiple concurrent pending invites for the same email all stay valid.
- **CSV import (S7):** the blueprint CSV spec has no **branch** column — multi-branch schools can't import; imports colliding with archived sections will now *restore* them (good — state this in the prompt so Codex keeps it); Windows-1256 Arabic encoding, not just UTF-8-BOM.
- **Teacher assignment (S5):** teacher-is-also-admin (two memberships, one user) breaking "my classes" queries; assignments referencing archived sections; assignment to inactive sections; what "deactivate teacher" does to open assignments and (later) threads.
- **Student enrolment (S6):** duplicate-name students; enrolment into archived/inactive sections; move-class must be close+open rows, never update (the S4 "edit in place" habit is the wrong pattern here — say so explicitly to Codex).
- **Guardian onboarding (S9):** hard Google dependency (see §5 — pull magic-link earlier); guardians with a shared family email (two guardians, one email = one `users` row — decide the semantics before S9).
- **Posts/media/diary/points/messaging/notifications:** biggest structural precursor is the SQLite test harness (S14 idempotency needs PG) and `write_audit`'s commit behaviour; also archived-section audiences (guardian of a child in an archived section — do old posts stay visible? Decide at S11).
- **Rollover (S19):** doable *only if* academic years get dates/`is_current` and S5/S6 rows are genuinely date-bounded. That's why those two things matter now.

---

## 5. Plan adjustments

- **Update the blueprint** (one editing pass, no redesign): add branches/campuses, education stages, `grade_level_label`, and the S4 lifecycle policy to §9/§15; correct `class_sections` to code/name; record the SQLite-tests deviation and its deadline (PG harness before S14, ideally at S7). *(Done as "Post-S4 checkpoint amendments" in the blueprint.)*
- **Reorder: pull email magic-link login forward, before or alongside S5.** The blueprint already flags this (§36.2) for parents, but it hits **teachers first**: GCC private schools commonly run Microsoft 365 — a teacher with no Google account cannot accept an S5 invite at all. Same "technically secure but unusable" failure class as the SMTP saga. Magic link only depends on S1 + mailer; both exist.
- **S5 prompt additions:** everything in §7/§8 below.
- **S6 prompt additions:** enrolments are date-bounded rows, close+open on move, never update in place; require `is_current` year semantics; roster views must exclude archived sections but preserve history.
- **S7/S8 CSV prompt additions:** optional `branch` column (default branch when absent); collision-with-archived → restore per S4 policy; encoding matrix (UTF-8, UTF-8-BOM, CP-1256); section auto-create naming rule; run the import suite against PG.
- **S9 adjustment:** magic link is already done by then (moved earlier); add the shared-guardian-email decision to the prompt.
- Everything else stays in blueprint order.

---

## 6. Recommended fixes before S5 (the "S4.9" slice)

| # | Issue | Why it matters | Suggested implementation | Blocking? | Model | Acceptance |
|---|---|---|---|---|---|---|
| 1 | Subject group bound to one section | Cross-section sets impossible; S5/S6 cement it | Migration: `class_section_id` nullable + nullable `grade_level_id`; keep app-level natural-key dedupe; require section XOR grade-level context | **Blocking (decision + small migration)** | gpt-5.5 | Group creatable with grade level and no section; existing section-bound groups unaffected; dedupe still works with NULL section |
| 2 | `homeroom_teacher_user_id` placeholder | Competing source of truth vs S5 `staff_assignments` | Drop the column in the S5 migration; homeroom = assignment row, referenced by membership id | **Blocking (decision only — execute in S5)** | — | S5 tests assert homeroom comes from assignments |
| 3 | Invite email failure → 500 after commit | Duplicate schools; unusable teacher invites at S5 volume | Wrap `send_staff_invite` call: catch, log, store `email_error` on invite, return 201 with warning + surface accept URL / resend in platform UI | **Blocking** | gpt-5.4-mini | SMTP down → school+invite created, 201 with warning, resend works |
| 4 | Status free text + "Archived" in form dropdown | Data corruption + vanishing-row footgun | Backend: validate status ∈ {active, inactive} on create/update (archive only via DELETE); frontend: remove "archived" from `StatusInput` | Non-blocking, trivial | gpt-5.4-mini | PUT with `status=archived` or garbage → 422; dropdown shows two options |
| 5 | Academic year has no `is_current`/dates | S5 `valid_from` defaults, S6 enrolment target, S19 rollover | Migration: `start_date`/`end_date` nullable + `is_current` bool; "mark current" endpoint (one current per school); UI checkbox | Non-blocking but do before S6 | gpt-5.4-mini | Exactly one current year enforceable; dropdowns default to it |
| 6 | `pending_setup` never → `active`; exchange ignores suspension; no email binding on staff invites | Lifecycle debt + invite-forwarding risk | On staff-invite accept: school `pending_setup`→`active`; exchange rejects suspended school (403) and requires `current_user.email == invite.email` for staff roles; revoke prior pending invites for same (school, email, role) on reissue | Non-blocking, small | gpt-5.4-mini | Tests: mismatch email → 403; suspended → 403; accept activates school |
| 7 | `require_school_role` runs twice; `write_audit` commits internally | Perf noise now; transaction traps in S5+ | Remove router-level dependency; change `write_audit` to add+flush (callers commit) | Non-blocking | gpt-5.4-mini | Suite green; one membership query per request |

Items 1–3 before S5; 4–7 can ride in the same cleanup slice (roughly half a day of Codex work total). Also decide (no code): PG test harness deadline — recommend "S7 at the latest".

---

## 7. Specific warnings for S5 (teachers & assignments)

- **Model traps:** `staff_assignments` must reference `membership_id`, not `user_id` (a teacher-parent has multiple memberships; branch scope lives on membership). Date-bounded rows: **never update, close (`valid_to`) + open new** — explicitly tell Codex the S4 edit-in-place pattern does *not* apply here, and neither does the archived-status pattern (assignments end, they don't archive). Enforce section-XOR-group per row.
- **Permission traps:** `require_teacher_of(section/group)` must check *active* membership + *open* assignment; build it as a reusable dependency in `school_scope.py`, not inline. Wrong-school, wrong-role, unassigned-teacher, and *ex*-teacher (closed assignment) tests all required.
- **Branch traps:** don't put `branch_campus_id` on assignments — derivable from the section. Don't build branch-scoped permissions yet.
- **Invite traps:** reuse `StaffInvite` with `role='teacher'` and the existing exchange; issuing must be `require_school_role('school_admin')` (not platform admin); accepted teacher lands on `/teach`, not `/school`; email binding per fix #6; invites to an email that already has a teacher membership → clear 409, not a duplicate.
- **UI traps:** assignment dropdowns offer only **active** sections/groups (reuse `SelectInput` semantics); teacher list must show pending invites vs active members distinctly; "deactivate teacher" needs a defined effect on open assignments (recommend: closes them, audit-logged).
- **Tests required:** invite lifecycle for the teacher role; assignment close-and-reopen preserves history; teacher sees only own classes; two-school isolation; archived-section assignment rejected.
- **Codex must NOT build:** students/enrolments, CSV, branch-local admin enforcement, timetables, teacher self-service profile, messaging stubs, any `/teach` functionality beyond the class-cards stub.

---

## 8. Revised S5 prompt (paste-ready, gpt-5.5)

> *Coding philosophy: write the minimum code that actually works. Reuse existing helpers/patterns in this repo before writing new ones; prefer stdlib and already-installed deps; no new dependencies. Never cut corners on validation, error handling, security, or tests. Follow existing code style (FastAPI deps, SQLAlchemy models in `backend/app/models_school/`, pytest patterns in `backend/tests/`, svelte-i18n EN+AR parity).*
>
> Task: S5 — teachers & assignments for Class Hero Hub in `/opt/apps/class_hero_hub`. Read first: `backend/app/models_school/models.py`, `backend/app/school_scope.py`, `backend/app/routes/school.py` (lifecycle helpers `_ensure_owned`, `_get_owned`, `_create_response`, restore policy), `backend/app/routes/platform.py` (StaffInvite issue/exchange), `backend/tests/school_fixtures.py`, `backend/tests/test_school_structure.py`, `frontend/src/routes/school/+page.svelte`.
>
> 1) **Migration + models.** New table `staff_assignments`: id, school_id FK NOT NULL indexed, membership_id FK→memberships NOT NULL (the teacher's membership — never user_id), class_section_id FK nullable, subject_group_id FK nullable, role string ('homeroom'|'subject'), valid_from Date NOT NULL (default today), valid_to Date nullable, created_by_user_id, created_at. CHECK: exactly one of class_section_id / subject_group_id set. In the same migration, **drop `class_sections.homeroom_teacher_user_id`** — homeroom teacher is now an assignment row with role='homeroom' on the section.
> 2) **Teacher invites.** School-admin endpoints under `/api/school` (existing `require_school_role("school_admin")` + X-School-Id pattern): `POST /teachers/invites` {email} → StaffInvite role='teacher' via the existing `_issue_staff_invite` mechanics (email failure must not fail the request — follow the established warning + resend pattern), `GET /teachers` (active teacher memberships + pending invites, distinct), `DELETE /teachers/invites/{id}` revoke. The existing `/api/invites/exchange` must create a **teacher** membership for role='teacher' invites, enforce invite-email == current-user email, and the frontend accept page must route teachers to `/teach` and school admins to `/school` based on the returned role.
> 3) **Assignments.** `POST /teachers/{membership_id}/assignments` (section or group id + role), `GET /teachers/{membership_id}/assignments`, `DELETE /assignments/{id}` = **close** (set valid_to=today), never delete. Reassignment = close + create new row; never update an assignment's target in place (assignments are date-bounded history, unlike the S4 status-lifecycle entities — do not add archived/inactive status to them). Validate targets with `_ensure_owned`: must belong to the school and must not be archived; only one *open* homeroom assignment per class section (409 otherwise). `POST /teachers/{membership_id}/deactivate`: sets membership status='revoked'+revoked_at/by and closes all open assignments, audit-logged.
> 4) **Scope guard.** Add `require_teacher_of(...)` dependency in `school_scope.py`: resolves current user's active teacher membership for the school and verifies an open assignment covering the given section/group. Not heavily used yet, but S11/S13/S14 depend on it — cover it with tests now.
> 5) **Frontend.** `/school` gains a Teachers tab: invite by email, list teachers (name/email/status/assignment count), pending invites with revoke, per-teacher assignment editor (dropdowns offer only **active** sections/groups, matching `SelectInput` semantics), deactivate with confirm. New `/teach` route: reads `/api/me/v2`, if the user holds teacher memberships shows card-per-open-assignment (school name, section/group name, role) — display only, no class view yet. Multi-membership users see all their teacher cards. All strings EN+AR; `npm run check:i18n` must stay green.
> 6) **Tests** (extend the two-school fixture): teacher invite lifecycle incl. email-mismatch 403 and revoked-invite reuse; exchange creates teacher membership; assignment create/close preserves history (closed row keeps valid_to, new row independent); duplicate open homeroom 409; archived section/group rejected as assignment target; `require_teacher_of` passes for assigned teacher, 403 for unassigned / ex-teacher (closed assignment) / wrong school; deactivate closes assignments; wrong-school and wrong-role on every new endpoint; platform-admin-without-membership 403.
> 7) **Do NOT build:** students, enrolments, CSV import, branch-scoped permission enforcement, timetables, class rosters, messaging, posts, points, teacher CSV. Do not touch docker/Caddy/.env handling.
> Acceptance: `docker compose exec backend python -m pytest tests -q` green; `cd frontend && npm run check && npm run check:i18n && npm run build` green; manual golden path: school admin invites teacher → email accept → teacher membership → admin assigns homeroom + one subject group → teacher logs in and sees both cards on `/teach`.

(If the S4.9 cleanup runs first, fixes #1/#3/#6 are already in place; otherwise fold #3 and the email-binding into this prompt — but don't fold #1, it deserves its own review.)

---

## 9. Self-audit / decisions needed from Dom

- **Highest-confidence findings:** the subject-group nullability issue, the homeroom-column conflict, and the SMTP-failure 500 — all verified directly in code, all cheap now and expensive later.
- **Least certain:** how much cross-section setting actually matters for the pilot school. If the pilot is KG–primary homeroom-only, fix #1 is still right (one-line nullability change now) but not urgent. **Blueprint §36.6's advice stands and hasn't been done: walk one real school's structure through the model on paper before S5.**
- **Possibly over-weighted:** magic-link urgency. If the pilot school's staff all have Google/Gmail, deferring to S9 is fine for teachers (still mandatory before guardians). Check the pilot school's email situation before S5.
- **Deliberately not recommended:** RLS acceleration, migration squashing, a multi-school switcher — all real, none pay for themselves before the pilot. The two-school test harness is doing its job.
- **Decisions needed from Dom before proceeding:**
  - (a) approve fix #1's schema change (nullable section + grade-level context on subject groups) or explicitly accept the one-section limitation;
  - (b) magic-link timing (pre-S5 vs S9);
  - (c) PG test harness deadline (recommend S7);
  - (d) whether staff-invite email binding is wanted (recommended yes; slightly changes the "forward the invite to a colleague" workflow).
- **Not audited deeply:** Playwright/E2E state, the deployed Caddy/tunnel config, and the June audit docs' competitor sections — none block S5.

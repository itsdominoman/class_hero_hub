# Class Hero Hub — Checkpoint Audit (post-S5, pre-S6)

**Date:** 2026-07-07
**Author:** Claude (Fable 5), fresh-eyes checkpoint audit — no code changed
**Scope:** S5 Teachers & Assignments plus the three S5 pre-commit fixes (shared error normalisation, subject-group UX defaults, subject-group product-logic cleanup + bulk creation), audited against the blueprint, the post-S4 audit's §7/§8 warnings, and the S4.9 foundation work.
**Source of truth:** the codebase at commit `fbe92ac` ("Add teachers and assignment foundation"), verified by direct inspection. Backend suite re-run during this audit: **126 passed** in Docker.
**Companions:** `docs/CLASS_HERO_HUB_MASTER_BLUEPRINT.md`, `docs/audits/2026-07-07-post-s4-fable-checkpoint-audit.md`, `docs/implementation/CLASS_HERO_HUB_IMPLEMENTATION_LOG.md`.

---

## 1. Executive verdict

**Continue to S6. No hard stop, and this time no mandatory intermediate slice.** S5 is the cleanest slice so far: every trap flagged in the post-S4 audit's §7 was avoided — assignments reference `membership_id` (never `user_id`), homeroom is a `staff_assignments` row (the placeholder column is gone from the schema), assignments are date-bounded close-and-open rows with no archive/status lifecycle, invites are email-bound and reject suspended schools, and platform admins are correctly rejected from `/api/school/*` teacher management. The permission test matrix (wrong school, wrong role, unassigned teacher, ex-teacher, platform-admin-without-membership) exists and passes.

Two small items must be **folded into the S6 prompt** (or done as a 1-hour pre-S6 patch) because S6 enrolments will copy the staff-assignment pattern verbatim, including its gaps:

1. **Assignment date fields are unvalidated** — `valid_from`/`valid_to` accept any date, so a backdated `valid_from` on a homeroom reassignment silently rewrites the *previous* teacher's close date, and `valid_to` can precede `valid_from`, producing a row that was never valid. Harmless at today's volumes, history-corrupting if enrolments inherit it.
2. **Decide the deactivated-teacher recovery story** — deactivated teachers vanish from the teachers list entirely, their assignment history becomes unviewable (the list endpoint 409s on non-active memberships), and a still-pending invite for their email lets them reactivate themselves. Each piece is defensible; together they need a one-paragraph policy decision before S6 repeats the pattern for archived students.

Everything else found is non-blocking polish (Section 5).

## 2. Focus-area findings (the fourteen questions)

1. **Teachers as memberships, not users — ✅ correct.** `staff_assignments.membership_id → memberships.id`; the teach dashboard iterates the user's *teacher memberships* per school; a teacher-who-is-also-admin holds two membership rows and each surface filters by role. Verified in `models_school/models.py`, `routes/teach.py`, `routes/school.py`.
2. **Homeroom via `staff_assignments` — ✅ correct.** No homeroom field exists on `class_sections` (dropped in S4.9 migration `a7b8c9d0e1f2`); homeroom = assignment row with `role='homeroom'` + `class_section_id`; one open homeroom per section enforced (409), one open homeroom per teacher enforced by auto-close-and-reopen.
3. **Date-bounding — ✅ mostly correct.** `valid_from` defaults to today; `valid_to` is treated as an **exclusive** end date consistently in all three open-row predicates (`require_teacher_of`, teach dashboard, `_open_assignments_query`), so closing with today's date removes access immediately. Gaps: no validation that `valid_to ≥ valid_from`, no guard on backdated/future `valid_from` (Section 4.1), and the open-interval predicate is now copy-pasted in three files — extract it before S6 adds a fourth copy.
4. **Close/reassign preserves history — ✅ correct and tested.** Close sets `valid_to`, never deletes; reassignment closes the old row and inserts a new one (test asserts both rows exist, old row has `valid_to`); deactivation closes all open rows and audit-logs their ids. `_close_assignment_row` can only shorten, never extend or reopen — good.
5. **Permission boundaries — ✅ clean.** `/api/school/*` requires an active school-admin membership resolved from `X-School-Id`; targets validated with school-scoped lookups (`_get_owned`, `_teacher_membership_or_404` filter on `school_id`); wrong-school actors get 404s that don't leak existence. Residual noise: `require_school_role("school_admin")` still executes **twice** per request (router-level dependency at `school.py:30` *and* per-endpoint parameter) — the post-S4 audit's fix #7 was half-done (`write_audit` was fixed; the duplicate dependency was not).
6. **Teacher sees only own assignments — ✅ yes, tested.** Dashboard queries assignments by the teacher's own membership id per non-suspended school; unassigned teacher gets an empty list; no-role user gets 403; `require_teacher_of` additionally demands an *open* assignment on the exact target and is tested for the ex-teacher (closed assignment) case. By design, a multi-school teacher sees all their schools' cards in one dashboard.
7. **School admin manages only their school — ✅ yes, tested** (beta admin mutating alpha's teacher → 404). Frontend caveat unchanged from S4: `/school` picks the *first* school_admin membership, so an admin of two schools still can't reach the second — becoming less theoretical with every slice.
8. **Platform admin bypass — ✅ no accidental path, tested** (platform admin without membership → 403 on `/api/school/teachers`). The remaining path is deliberate, not accidental: a platform admin can invite *themselves* as school admin of any school and accept it — visible in audit logs, acceptable for MVP, worth remembering when support/impersonation tooling is designed.
9. **Teacher invite safety — ✅ good.** Tokens are `secrets.token_urlsafe(32)` (256-bit), SHA-256-hashed at rest, 7-day expiry, single-use, rate-limited exchange; exchange enforces normalized-email match, rejects revoked/used/expired and suspended schools; reissue auto-revokes prior pending invites for the same (school, email, role); inviting an already-active teacher → clear 409; SMTP failure returns 201 + warning with `send_status`/`last_send_error` stored. Magic-link login **auto-creates the `User` row on first exchange**, so a non-Google (Microsoft 365) teacher can genuinely complete the invite flow — the S4 audit's biggest S5 worry is resolved. Two residual weaknesses: (a) the GET `/api/auth/magic-link/exchange?token=…` consumes the token on first GET, which Outlook SafeLinks / email scanners may prefetch — precisely the mailboxes non-Google teachers use (Section 5.6); (b) deactivating a teacher does not revoke pending invites for their email (Section 4.2).
10. **Subject groups rational for S6 — ✅ yes.** Both section-specific and grade-level/cross-section contexts work; deterministic codes (`G1A-ENG` / `G1-ENG`); bulk per-section creation with per-item skip/restore/fail reasons; consistency checks (section must belong to the chosen year and grade). One S6 design decision must be made explicitly: **do section-specific subject groups require explicit student enrolment rows, or does section enrolment imply membership?** The blueprint says explicit rows (`enrolments.subject_group_id`); state it in the prompt so Codex doesn't invent auto-membership.
11. **S6 fit — ✅ clean.** Enrolments can mirror `staff_assignments` exactly (school_id, student_id, section-XOR-group, valid_from, valid_to, close+open on move); `is_current` academic year exists for defaults; `require_teacher_of` is built and tested, ready for teacher roster endpoints; the restore-on-recreate lifecycle covers student archive/restore if students adopt the same status idiom. The only structural prep worth doing in-slice: extract the shared open-interval helper (finding 3).
12. **UX problem check — ✅ largely addressed.** `[object Object]` is fixed at the source (`normalizeErrorMessage` in the shared `api.ts` wrapper — all screens benefit); required fields now have client-side inline validation; generated subject-group codes are deterministic and editable; invite/assignment mistakes are recoverable (revoke + reissue, close + recreate, archived-restore). Remaining papercuts: homeroom reassignment silently closes the teacher's previous homeroom with no UI warning; Close assignment has no confirm (deactivate does); a failed-send invite's accept URL is still never shown to the admin, so SMTP-down recovery is "invite again later" rather than "copy the link"; deactivated teachers disappear from the Teachers tab with no visible trace.
13. **Schema decisions before S6 — nothing blocking.** Watch-list items: `subject_groups` uniqueness with NULL context columns is app-enforced only on PostgreSQL (NULLs defeat the unique constraint — a concurrency race could create duplicates; falls out naturally when the PG test harness lands, keep it on the S20 list); `memberships.school_id`/`user_id` are nullable in the schema (tighten in a later hardening migration); no DB-level exclusion constraint prevents overlapping open homerooms (app-enforced; PG `EXCLUDE USING gist` is an S20 option); `DELETE /assignments/{id}` accepts an optional request body (`valid_to`) — DELETE bodies are stripped by some proxies; the frontend never sends one today, so if backdated closes become a real feature, move to `POST /assignments/{id}/close`.
14. **Missing tests before S6 —** see Section 6. Nothing that invalidates S5's green suite; all are additive.

## 3. What S5 got right (worth keeping as precedent)

- Every §7 model/permission/invite/UI trap from the post-S4 audit was implemented as specified — the audit-amendment-prompt loop is working.
- The three pre-commit fixes (error normalisation in the shared API wrapper, generated defaults that never overwrite manual edits, bulk creation with per-item reasons) are exactly the right altitude — small, systemic, no new frameworks.
- Test style matured: audit-log assertions, lifecycle sequences in one test, guard tested in isolation with a synthetic FastAPI app.
- `valid_to`-exclusive semantics decided once and applied consistently; documented in the log.

## 4. Fold into the S6 prompt (or a 1-hour pre-S6 patch)

### 4.1 Assignment date validation (and don't let enrolments inherit the gap)
`AssignmentRequest.valid_from` and `CloseAssignmentRequest.valid_to` accept any date. Consequences today: (a) creating a homeroom with a backdated `valid_from` closes the *previous* teacher's homeroom at that past date, silently rewriting history; (b) a future-dated `valid_from` creates a not-yet-open assignment that the duplicate/homeroom-conflict checks ignore (they only consider currently-open rows), so two future homerooms for one section are possible; (c) `valid_to` may precede `valid_from`, producing a never-valid row. Fix: reject `valid_to < valid_from`; either reject non-today `valid_from` for now (YAGNI — the UI never sends it) or bound it to the current academic year; make the homeroom-conflict check date-range-aware only if future-dating is kept. **The S6 enrolment endpoints must ship with these validations from day one.**

### 4.2 Deactivated-teacher policy (one decision, three symptoms)
Decide and record: (a) deactivation should **also revoke pending teacher invites for that email** (currently a pending invite lets the deactivated teacher reactivate their own membership); (b) the Teachers tab should show deactivated teachers (e.g. a collapsed "Former teachers" list) or at least the API should allow listing them — today they vanish; (c) `GET /teachers/{id}/assignments` should work for non-active memberships so history stays viewable (today `_teacher_membership_or_404` 409s on reads and writes alike — split read from mutate). Recommendation: do (a) in code pre-S6 or in-slice (it is a 5-line change plus a test); (b)/(c) can ride along with S6's people-listing work since students will need the identical "archived but visible" treatment.

## 5. Non-blocking issues (fix opportunistically)

1. **Duplicate `require_school_role` execution** — remove the router-level dependency at `school.py:30`; the per-endpoint parameters already enforce it (post-S4 fix #7, still half-done).
2. **`/school` binds to the first school_admin membership** — multi-school admins can't reach school #2. Add a simple school switcher when a second real school exists, at latest with S7 imports.
3. **Open-interval predicate duplicated three times** (`school_scope.require_teacher_of`, `teach.teacher_dashboard`, `school._open_assignments_query` / `_is_open_assignment`) — extract one helper before S6 makes it five.
4. **Subject-group target check ignores the parent section's status** — `_ensure_active_target` checks the group's own status; a group whose *section* was archived after group creation is still assignable. Rare (archiving a section should arguably cascade-inactivate its groups — a lifecycle question for S19 rollover), but cheap to check both.
5. **Failed-send invites: accept URL still unrecoverable** — `send_status='failed'` is stored and a warning shown, but no admin surface exposes the accept link or a true "resend" (re-invite mints a new token and revokes the old, which is fine — label it as such). Carried over from the post-S4 audit.
6. **Magic-link GET exchange is prefetch-consumable** — Outlook SafeLinks and similar scanners GET links in email bodies; the current design consumes the single-use token on first GET, so exactly the Microsoft-365 teachers magic link exists for may find their links "already used". Mitigation: make the emailed link land on a tiny page that POSTs the token on user click (the POST endpoint already exists). Recommend fixing before inviting real teachers.
7. **Homeroom reassignment is silent** — assigning a teacher who already holds a homeroom quietly closes the old one (documented backend behaviour). Surface it: either a confirm ("This will end their Year 1 Red homeroom") or a notice in the response toast.
8. **Close assignment has no confirm** — one tap ends an assignment (recoverable by recreating, but the old row keeps its history and a new row starts today — a same-day close+recreate leaves a cosmetic duplicate pair). Deactivate has a confirm; closing should too.
9. **Teach dashboard 403 message** — a teacher whose only school is suspended gets "Teacher access required", which reads as "you are not a teacher". A suspended-specific message would save a support call.
10. **`_assignment_card` does per-row lookups** (N+1 per assignment: section, branch, year, level, subject) — irrelevant at teacher scale, just don't copy the pattern into S6 rosters (30 students × N lookups); use joins there.
11. **Checklist/setup labels remain backend-hardcoded English** — unchanged from S4; the Teachers tab strings are properly i18n'd. Fold into S17.
12. **`README.md`/`PROJECT_STATUS`/`ROADMAP` still describe Family Hero Hub** — increasingly confusing for anyone new (or any tool) reading the repo. A short "this repo is Class Hero Hub; see docs/CLASS_HERO_HUB_MASTER_BLUEPRINT.md" banner at the top of README costs five minutes.

## 6. Missing tests before S6 (additive, none invalidate current green)

- `require_teacher_of` **cross-school** case: teacher of school A requesting school B's section id (should 404) — the guard test covers assigned/unassigned/ex-teacher but not wrong-school.
- **Dual-role user**: one user with school_admin + teacher memberships at the same school — `/api/school/*` works with the admin membership, `/api/teach/dashboard` shows only teacher assignments. This is the §7 "teacher-is-also-admin" trap; the code looks correct but nothing pins it.
- **Suspended school excluded from teach dashboard**: teacher with memberships at two schools, one suspended → only the active school's cards (the filter exists; untested).
- **Date-validation tests** once 4.1 lands: `valid_to < valid_from` rejected; backdated/future `valid_from` policy enforced.
- **Deactivation + pending invite** once 4.2 lands: deactivate revokes pending invites; exchange after deactivation fails.
- Close-then-recreate same target same day: assert two rows, no constraint surprise.

## 7. S6 prompt amendments (deltas to the blueprint's S6 slice)

1. **Enrolments mirror `staff_assignments` exactly**: `school_id` NOT NULL indexed, `student_id` FK, `class_section_id` XOR `subject_group_id` (CHECK constraint), `valid_from` NOT NULL default today, `valid_to` nullable **exclusive**, `created_by_user_id`, timestamps. No status/archive lifecycle on enrolment rows — they close, they don't archive. Never update an enrolment's target in place; move = close + open (the S4 edit-in-place habit does not apply — restate this, it worked for S5).
2. **Ship date validation from day one** (per §4.1): `valid_to ≥ valid_from`; `valid_from` today-or-explicitly-bounded; duplicate-open checks; and apply the same validations to staff assignments in the same slice.
3. **Extract the shared open-interval helper** (one function used by staff assignments and enrolments and the guards) instead of a fourth copy of the predicate.
4. **Students** get the S4 status lifecycle (active/inactive/archived, restore-on-recreate keyed on `(school_id, external_ref)` when external_ref present); `external_ref` nullable, unique per school when set (app-enforced for NULLs, same idiom as subject groups); names EN + optional AR; no login, no PII beyond the blueprint fields.
5. **One open homeroom enrolment per student** (409 otherwise); subject-group enrolments may be multiple concurrent; **section-specific subject groups require explicit enrolment rows — section enrolment does not imply group membership** (blueprint §9/§13 semantics; say it or Codex will invent auto-membership).
6. **Enrolment targets**: active sections/groups only (reuse `_ensure_active_target`), and also reject groups whose parent section is archived (fixes §5.4 for the new surface).
7. **Rosters**: admin roster per section under `/api/school` (join queries, not per-student lookups); teacher roster under `/api/teach` guarded by `require_teacher_of` — decide the URL shape so the guard finds `school_id` (recommend path params: `/api/teach/schools/{school_id}/sections/{class_section_id}/roster`). Teacher rosters are read-only in S6.
8. **Deactivation/visibility policy** from §4.2 applied consistently: archived students visible via `include_archived`, history (closed enrolments) viewable for archived students; split read vs mutate guards.
9. **Tests**: the standard two-school/wrong-role matrix on every endpoint, move-preserves-history, teacher-sees-only-own-rosters, archived-section handling, dual-role user, plus the §6 backfill items (cross-school `require_teacher_of`, suspended-school dashboard).
10. **Do NOT build**: CSV import, guardian anything, posts/diary/points/messaging, attendance, photos, bulk student tools beyond simple add, branch-scoped permissions, timetables.

## 8. Manual tests Dom should run (golden path, ~30 minutes)

1. **Non-Google teacher end-to-end**: invite a teacher to a real (non-Gmail, ideally Outlook.com) address → open the email on a phone → magic-link login → invite auto-accepts → lands on `/teach`. *Watch for the link arriving "already used" — that would confirm the SafeLinks prefetch risk (§5.6).*
2. **Assignment lifecycle**: assign homeroom + a subject group → teacher sees both cards on `/teach` → reassign homeroom to another section → old teacher's card disappears, `GET /teachers/{id}/assignments` shows the closed row with `valid_to` = today.
3. **Deactivate + re-invite**: deactivate the teacher (confirm dialog) → their `/teach` shows the access-denied state → re-invite the same email → accept → membership active again, assignment list empty. Note the UX of the teacher having "disappeared" from the Teachers tab in between.
4. **Suspension**: suspend the school from `/platform` → teacher's dashboard no longer shows that school's cards → a pending teacher invite for it fails exchange with the suspended message → reactivate.
5. **Cross-school spoof**: as school A's admin, replay a `/api/school/teachers` request with school B's id in `X-School-Id` (devtools) → 403.
6. **Bulk subject groups**: one grade, several sections including an inactive one → per-item results show created + the inactive rejection reason; re-run → all skipped as duplicates; archive one group, re-run → restored.
7. **Error UX regression check**: submit the subject-group form missing the English name and the teacher-invite form with a bad email → readable inline messages, no `[object Object]`.
8. **Arabic pass**: switch to AR and walk the Teachers tab and `/teach` — strings present, layout sane in RTL.

## 9. Docs to update

- **Blueprint §0a** — add S5 amendments: homeroom is singular per teacher *and* per section in this phase (auto-close on reassign); `valid_to` is exclusive; teacher invites reuse `StaffInvite` with email binding; deactivation = revoke membership + close assignments; magic-link auto-creates users. *(Recommended; not done in this audit.)*
- **Implementation log** — audit entry. *(Done alongside this audit.)*
- **README.md** — five-minute banner pointing at the blueprint (§5.12). *(Recommended.)*
- Record the §4.2 deactivation policy decision wherever Dom makes it (log entry or blueprint amendment).

## 10. Revised S6 Codex prompt outline (gpt-5.5)

> *Standard philosophy preamble (minimum code, reuse repo patterns, no new deps, never skimp on validation/security/tests, EN+AR parity).*
>
> **Task: S6 — Students & enrolments.** Read first: `backend/app/models_school/models.py` (StaffAssignment — enrolments mirror it), `backend/app/routes/school.py` (lifecycle helpers `_create_response`/`_ensure_owned`/`_ensure_active_target`, assignment endpoints as the pattern), `backend/app/school_scope.py` (`require_teacher_of`), `backend/tests/test_staff_assignments.py`, `frontend/src/routes/school/+page.svelte`, `frontend/src/routes/teach/+page.svelte`.
> 1. **Migration + models**: `students` (school_id NOT NULL idx, external_ref nullable, first/last/preferred names, name_ar, dob/gender nullable, status active/inactive/archived, created_at; app-enforced uniqueness of (school_id, external_ref) when set) and `enrolments` (school_id NOT NULL idx, student_id FK, class_section_id XOR subject_group_id CHECK, valid_from NOT NULL default today, valid_to nullable **exclusive**, created_by_user_id, timestamps). No status column on enrolments.
> 2. **Shared helper**: extract one open-interval helper (`valid_from <= today AND (valid_to IS NULL OR valid_to > today)`) and use it in `require_teacher_of`, teach dashboard, staff-assignment queries, and enrolment queries.
> 3. **Date validation** on both enrolments *and* staff assignments: `valid_to >= valid_from` (400); `valid_from` must be today unless explicitly passed within the section's academic year; duplicate open enrolment 409; one open homeroom (section) enrolment per student 409.
> 4. **Endpoints** under `/api/school` (school_admin): students CRUD with S4 lifecycle + restore-on-recreate; `POST /students/{id}/enrolments` (section or group), `DELETE /enrolments/{id}` = close; move-class = close + open in one request (`POST /students/{id}/move-section`); section roster (join query). Under `/api/teach` (require_teacher_of, path-param school id): read-only roster for an assigned section/group.
> 5. **Semantics**: enrolment targets must be active (and a group's parent section not archived); section-specific subject groups need explicit enrolment rows — section enrolment does NOT imply group membership; archived students keep viewable history (`include_archived`, read/mutate guards split).
> 6. **Deactivation policy ride-alongs**: teacher deactivation also revokes pending teacher invites for that email; teachers list gains an include-deactivated view; `GET /teachers/{id}/assignments` works for non-active memberships (reads split from mutates).
> 7. **Frontend**: `/school` Students tab (list/search by section, add/edit/archive, move-class with confirm, enrolment list per student); `/teach` class card → roster view (names only). EN+AR, parity green.
> 8. **Tests**: two-school + wrong-role matrix on every endpoint; move preserves history (two rows); roster scope (teacher sees only assigned section; ex-teacher 403; cross-school 404); archived student/section handling; dual-role (admin+teacher) user; date-validation cases; suspended-school dashboard exclusion (backfill); `require_teacher_of` cross-school (backfill).
> 9. **Do NOT build**: CSV import, guardians/invites for guardians, posts/diary/points/messaging, attendance, photos, timetables, branch-scoped permissions. Do not touch docker/Caddy/.env.
> **Acceptance**: full pytest suite green in Docker; `npm run check`, `check:i18n`, `build` green; manual golden path — admin adds three students to Year 1 Red, moves one to Year 1 Green, archives one; teacher sees the correct roster on `/teach`.

---
*End of post-S5 audit.*

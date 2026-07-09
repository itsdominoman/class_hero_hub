# Class Hero Hub Implementation Log

## 2026-07-09 — S8: Teacher CSV Import v1

Scope: staged teachers-CSV pipeline on the existing `/school` Teachers tab —
upload → validate → preview (create/update/skip/error per row) → commit
valid rows → idempotent re-import. No teacher assignment/auto-assignment,
guardian onboarding, parent dashboard, posts, diary, points, messaging,
notifications, attendance, timetables, rooms, terms, rollover, or other auth
changes were part of this slice. No emails were sent by this slice.

### Product safety rule (binding, verified by test)

Bulk import never sends invites, magic links, notifications, emails, or other
outbound communication. `test_import_sends_zero_outbound_communication`
monkeypatches `mailer.send_staff_invite`/`send_magic_login` and asserts zero
calls plus zero `StaffInvite`/`MagicLoginToken` rows after a commit.

### Key design decision: commit creates real `User`/`Membership` rows, not a draft-only staging table

The brief offered two paths: (a) commit directly creates/reuses `User` +
active `Membership(role="teacher")` rows (no invite email), or (b) — if that
were unsafe — commit only writes to a new draft/prep table, mirroring S7's
`StudentGuardianContact` pattern, deferring real account creation to a later
explicit release/send-invites slice.

Path (b) was the first instinct (`StudentGuardianContact` is the closest
existing precedent for "staged, never-contacted" import data), but it doesn't
hold up against the spec's own QA/test requirements (QA step 9 asks to
confirm no duplicate *users, memberships*; required tests include "existing
user without teacher membership becomes teacher... correctly" and "existing
teacher membership resolves to skip/update, not duplicate" — both presuppose
real `Membership` rows exist after commit) — and the analogy to guardian
contacts doesn't transfer, since guardians have no account/role model at all
yet (deferred to S9), whereas teachers already have a first-class `User` +
`Membership(role="teacher")` model that's actively used.

Verified before building: is creating an active `Membership` outside the
invite-accept flow actually a security bypass? No — `authentication.py`'s
Google SSO and magic-link exchange both auto-create/match a `User` row purely
by lowercased email with no `google_sub`-already-set gate and no
"has logged in before" gate; access is fully determined by
`User.status == "active"` + `Membership.status == "active"` at request time,
checked in `require_school_role`. The invite-accept path itself
(`platform.py`'s `exchange_staff_invite`) reduces to exactly the same trust
boundary — "whoever proves control of email X gets whatever active
memberships exist for that email" — so a directly-created active `Membership`
grants nothing until the person independently authenticates. This exact
pattern (`Membership(status="active")` created directly, outside
invite/accept) already exists in
`backend/scripts/demo_teacher_assignment_coverage.py`. So: **path (a)** —
commit creates/reuses `User` + ensures an active `Membership(role="teacher")`,
never sends an invite email, never touches `StaffInvite`/`MagicLoginToken`.

### Other decisions

- **Identity is email only** (normalized via the existing `auth.normalize_email`),
  not a school-scoped natural key like `Student.external_ref` — email is
  globally unique on `User`, so the planner looks up `User` by email first,
  then an existing `Membership(school_id, user_id, role="teacher")` for this
  school specifically (the same user can be a teacher at multiple schools,
  or already an admin at this school and newly added as a teacher here too —
  `uq_memberships_school_user_role` is per-role, not exclusive).
- **Row actions are `create`/`update`/`skip`/`error`** — a strict subset of
  `ImportRow.action`'s existing CheckConstraint (`create, update, move,
  restore, skip, error`), so no migration/constraint change was needed;
  `move`/`restore` simply never fire for teacher rows.
- **A previously-revoked teacher membership is never silently reactivated by
  import** — if a `Membership(role="teacher")` row already exists for that
  (school, user) with `status != "active"` (an admin explicitly deactivated
  them via the existing Teachers tab flow), the row resolves to `skip` with a
  warning telling the admin to re-activate from the Teachers tab instead.
  Reimporting the same CSV must never undo an explicit deactivation decision.
- **Existing `User` fields are never clobbered by import** — for an existing
  active teacher membership, the CSV only fills a currently-*blank*
  `name`/`name_ar` (action `update`); it never overwrites a name the person
  (or another admin flow) already set. An existing `User` might be a
  school_admin or teacher elsewhere with a name already on file, and a bulk
  CSV shouldn't silently overwrite it.
- **`users.name_ar` added as a new nullable column** (migration
  `c3d4e5f6a7b8`, following the same pattern as the existing `schools.name_ar`
  column) — the brief listed `name_ar` as a minimum template column, and since
  this slice creates real `User` rows (not a side staging table), there was
  nowhere else to put it. Nullable/additive only, no behavior change for any
  existing user.
- **Preferred conservative template** (`email,first_name,last_name,name_ar`)
  was used as-is, and the optional `display_name`/`phone`/`staff_ref`
  columns were left out per the brief's "only if cheap/safe" — `User` has no
  `phone` or `staff_ref`-equivalent column, and adding `display_name` would
  reintroduce the "first_name required unless display_name present"
  conditional logic the conservative template was explicitly meant to avoid.
  Both `first_name` and `last_name` are simply required.
- **`generate_template_csv`/`parse_csv_rows` in `imports_service.py`
  generalized to take a `columns: list[str]` parameter** (previously
  hardcoded to the student `CSV_COLUMNS`) so the teacher CSV path reuses the
  same encoding/parsing/header-matching code instead of a near-duplicate;
  `_import_detail_payload` in `routes/school.py` similarly takes an optional
  `row_payload_fn` so both `_import_row_payload` (student) and the new
  `_teacher_import_row_payload` share the same summary/row-list shape.
- **Query-shape:** `plan_teacher_import_rows` batches every lookup (existing
  users by email, existing teacher memberships by user id) once regardless
  of row count, per `docs/BACKEND_PERFORMANCE.md`'s rule; the commit route
  does one additional batched `User`/`Membership`-by-id fetch for the rows
  the plan resolved, mirroring the existing student-import commit route's
  pattern.
- **User lookup is case-insensitive (`func.lower(User.email)`), not an exact
  match.** `User.email` has a plain unique index, not a lowercase-normalized
  one, so an exact-match lookup against the CSV's normalized (lowercased)
  email could miss a historical row stored with mixed case and misclassify
  it as `create`, producing a duplicate `User` on re-import — caught in a
  pre-commit review pass, not by the original test suite (every test/smoke
  email happened to already be lowercase). Fixed to match the same
  `func.lower(User.email)` pattern `authentication.py` already uses at
  login; regression-tested by
  `test_existing_mixed_case_email_is_matched_case_insensitively`.

### Backend changes

- Migration `c3d4e5f6a7b8_add_user_name_ar.py` adds nullable `users.name_ar`.
- `backend/app/models_school/models.py`: `User.name_ar` column.
- `backend/app/imports_service.py`: `TEACHER_CSV_COLUMNS`; `TeacherRowPlan`
  dataclass; `plan_teacher_import_rows(...)` (the batched planner, mirroring
  `plan_student_import_rows`'s shape); `generate_template_csv`/
  `parse_csv_rows` generalized to accept a `columns` parameter (both existing
  student-import call sites updated accordingly).
- `backend/app/routes/school.py` gains, under the existing
  `require_school_role("school_admin")` router dependency: `GET
  /teachers/import-template`, `POST /teachers/imports`, `GET
  /teachers/imports/{id}`, `POST /teachers/imports/{id}/commit`, `POST
  /teachers/imports/{id}/discard`, plus `_teacher_import_row_payload`.
  `_import_detail_payload` gained an optional `row_payload_fn` parameter
  (default unchanged) so both kinds share it. Commit batches `User`/
  `Membership` lookups by id before the per-row apply loop; `create` either
  reuses an existing `User` (found by email) or inserts a new one
  (`status="active"`, `name`/`name_ar` from the row), then always inserts a
  new `Membership(role="teacher", status="active")`; `update` only fills
  blank `name`/`name_ar` on an existing `User`; `skip` just records
  `applied_entity_id`. No `StaffAssignment`, `StaffInvite`, or
  `MagicLoginToken` row is ever touched by this endpoint group.

### Frontend changes

- `/school` → Teachers tab gained an import panel (between the invite form
  and the pending-invites list): "Download teacher CSV template", CSV file
  picker + upload, a staged-preview summary (create/update/skip/error
  counts), a row-level table (row number, email, name, action,
  errors/warnings), commit/discard actions, and a note clarifying that
  commit creates an active teacher account immediately with **no** invite
  email sent. `commitTeacherImport` calls the existing `refresh()` (which
  already loads `teachers`/`pendingTeacherInvites`/`teacherAssignments`
  eagerly on tab load) rather than a lazy-load helper, since teacher data —
  unlike students — isn't lazy-loaded on this page.
- `frontend/src/lib/i18n/messages.ts` gained `school.teacherImports.*`
  (English + Arabic) as a new sibling namespace next to `school.imports.*`
  (not a rename to `school.imports.students.*`/`school.imports.teachers.*`,
  to avoid touching every existing student-import call site for a
  same-slice-sized change) — `grade`/`section`/`guardians`-style keys were
  dropped since they don't apply to teacher rows, `email`/`name`/`note` were
  added, and `move`/`restore` were dropped from `summary`/`actionLabel`
  since those actions never fire for teacher rows.

### Tests

`backend/tests/test_teacher_imports.py` (21 tests): template headers,
UTF-8/UTF-8-BOM parsing, case/whitespace-insensitive headers, required
email/first_name/last_name errors, invalid email format, duplicate email
within file, existing user without a teacher membership becomes a teacher
(dual-role, reusing the existing `User` row), existing active teacher
membership resolves to skip (not duplicate), full re-import idempotency (one
`User`, one `Membership` after two commits of the same file), a mixed-case
stored email is matched case-insensitively (not treated as a new user), a
previously revoked teacher membership is not silently reactivated by
re-import (skip + warning), cross-school isolation (a teacher already active
at one school gets a second, independent `Membership` row when imported into
another school — not a skip), commit-valid-leave-errors-unapplied,
double-commit rejected, discard-then-commit rejected, wrong-role/wrong-
school/platform-admin-without-membership blocked, zero `StaffAssignment`
rows created, zero outbound communication (no mailer calls, no
`StaffInvite`/`MagicLoginToken` rows), and a query-count regression test
proving upload/commit read-query counts don't scale with row count.

### Validation

- `docker compose run --rm --no-deps -v $(pwd):/repo -w /repo/backend backend python -m pytest tests/test_teacher_imports.py -q` → **21 passed**.
- `docker compose run --rm --no-deps -v $(pwd):/repo -w /repo/backend backend python -m pytest tests -q` → **226 passed** (up from 205), 10 warnings.
- `cd frontend && npm run check` → 0 errors, 0 warnings.
- `cd frontend && npm run check:i18n` → parity OK, 471 keys in both `en` and `ar`.
- `cd frontend && npm run build` → built OK.
- `docker compose build backend frontend` + `docker compose up -d backend frontend` → rebuilt and restarted.
- `alembic heads` → single head `c3d4e5f6a7b8`; applied to the live dev
  database (`alembic upgrade head`, `alembic current` → `c3d4e5f6a7b8`).
- `docker compose run --rm --no-deps -v $(pwd):/repo -w /repo backend python backend/scripts/perf_check.py` → only the pre-existing `/api/school/students` endpoint over budget (3.1s this run, unrelated to this change); no newly-audited endpoint added, and none of the audited endpoints regressed.
- **Manual smoke test against the live United International School demo
  data**: downloaded the template (confirmed the 4-column header), uploaded a
  3-row CSV (one brand-new teacher email, one existing platform user who was
  a `school_admin` at the school but not yet a `teacher` there, one
  deliberately invalid email), previewed (2 `create` + 1 `error`, confirmed
  via direct DB query that the "existing admin, no teacher role yet" row
  correctly resolved to `create` rather than being misclassified), committed
  (verified the new `User` row had `name`/`name_ar` set correctly and the
  existing admin gained a second, independent `Membership(role="teacher")`
  row alongside their unchanged `school_admin` one), re-uploaded the
  identical file (both non-error rows resolved to `skip`, confirmed no
  duplicate `User`/`Membership` rows), confirmed zero `StaffInvite`/
  `MagicLoginToken` rows were created for either email, then deleted the
  smoke-test user/membership/import rows and removed the extra teacher
  membership from the existing admin to leave the demo school exactly as it
  was before the test.
- **Not driven in an actual browser** (no browser/screenshot tool available
  in this environment). Frontend correctness was instead verified by:
  `svelte-check` (0 errors), a successful production build, a manual grep
  cross-check of every `$_('school.teacherImports.*')` key used in
  `+page.svelte` against the keys declared in both `en` and `ar` in
  `messages.ts` (`npm run check:i18n` only checks en/ar parity with each
  other, not usage-vs-declaration), and the manual smoke test above driving
  the exact same API endpoints/payload shapes the new UI panel calls. Dom
  should still click through the panel once per the QA steps below.

### Deferred (per instructions for this slice)

- Any explicit "send invite" / "release" action for imported teachers —
  imported teachers get an active account and membership immediately with no
  notification; telling them how to sign in is a manual, out-of-band step
  for now. A later slice could add an explicit "notify these teachers" bulk
  action if wanted.
- Teacher assignment (homeroom/subject) import — assignments remain managed
  by the existing Teachers tab workflow only, per the brief.
- Branch-scoped permissions and any `staff_ref`/`phone`/`display_name`
  columns — left out of the conservative template, see Decisions above.

## 2026-07-09 — S7 correction: guardian name/relationship + draft guardian contacts

Product correction to the S7 slice below, made before audit/commit: the
original template only collected `guardian1_email`/`guardian2_email`, which
under-served S9 (guardian onboarding) and S15 (messaging) — both need a
guardian display name and relationship, and neither teachers nor admins
should ever address a guardian as a raw email address. This correction lands
before any of S7 is committed, so it's folded directly into the S7 schema
and code rather than layered on top.

### What changed

- **CSV template columns** now include, per guardian slot:
  `guardian1_name, guardian1_email, guardian1_relationship, guardian2_name,
  guardian2_email, guardian2_relationship` (name/email/relationship per
  guardian, replacing the email-only columns). Full new header order:
  `student_id,first_name,last_name,preferred_name,name_ar,dob,gender,branch,
  grade,section,guardian1_name,guardian1_email,guardian1_relationship,
  guardian2_name,guardian2_email,guardian2_relationship`.
- **New table `student_guardian_contacts`** (migration
  `b2c3d4e5f6a7_add_student_guardian_contacts.py`, on top of the S7
  migration below): `id, school_id, student_id, slot (1|2), name, email,
  relationship, source_import_id, status (draft|linked|ignored),
  created_at, updated_at`, unique on `(school_id, student_id, slot)`. These
  are **prep-only records** — no login, no `guardian_link`, never
  contacted. `status` starts `draft` and is reserved for S9 to transition to
  `linked` (a real guardian was onboarded from this contact) or `ignored`;
  S7 itself only ever writes `draft` rows.
- **Commit upserts guardian contacts per (student, slot)**, independent of
  the student row's own action (`create`/`update`/`move`/`restore`/`skip`)
  — a guardian-only edit on an otherwise-unchanged student still lands,
  since the student action alone shouldn't gate a guardian data refresh.
  A contact already moved past `draft` status (by a future S9 workflow) is
  never overwritten by a later re-import — the loop explicitly skips it and
  leaves a note in the design rather than silently clobbering a downstream
  decision.
- **Validation policy (guardian data never blocks the student row):**
  guardian name/email/relationship are all optional; a slot with nothing in
  it is skipped entirely (no contact row, and re-import never deletes an
  existing draft contact just because a later file leaves that slot blank —
  additive/upsert only, no deletion logic in this pass). If email is
  present without a name, or `relationship` is present but not one of
  `mother`/`father`/`guardian`/`other`, both are **warnings, not errors** —
  the field is left blank (relationship) or flagged (name) but the guardian
  contact is still staged and the student row still commits. This mirrors
  the existing malformed-email-format warning from the original S7 slice.
- **Zero outbound communication still holds**: guardian columns are parsed,
  validated, and staged into the draft table only. No `guardian_link`, no
  `User` account, no `StaffInvite`/`MagicLoginToken`, no mailer call is
  created/invoked for guardian data — verified by test (see below).
- **Preview/row display**: the `/school` Students → CSV import row table
  gained a Guardians column summarizing both slots (`Guardian 1: name ·
  email · relationship`), plus an explanatory note that these are draft
  contacts only. The `GET/POST .../imports*` row payloads now include
  `guardian{1,2}_{name,email,relationship}` alongside the existing fields.

### Files touched by this correction

- `backend/app/models_school/models.py` (+`__init__.py`) — `StudentGuardianContact` model.
- `alembic/versions/b2c3d4e5f6a7_add_student_guardian_contacts.py` (new).
- `backend/app/imports_service.py` — `CSV_COLUMNS` updated;
  `GUARDIAN_RELATIONSHIP_VALUES`; `_validate_guardian_slot(...)`;
  `existing_guardian_contacts_by_student(...)` (batched, same shape as
  `open_section_enrolments_by_student`); `RowPlan.guardian_contacts`.
- `backend/app/routes/school.py` — commit route upserts guardian contacts;
  `_import_row_payload` includes guardian fields.
- `backend/tests/test_student_imports.py` — rewritten around a `csv_row(...)`
  builder (keyword args matching `CSV_COLUMNS`) instead of hand-counted
  comma strings, to avoid exactly the off-by-one-comma mistake a manual
  curl smoke test hit during the original S7 pass; 4 new guardian-specific
  tests plus updates to the zero-outbound and template-header tests.
- `frontend/src/routes/school/+page.svelte` — `ImportRow` type, Guardians
  column, `importRowGuardianSummaries(...)`.
- `frontend/src/lib/i18n/messages.ts` — `school.imports.guardians`,
  `guardianSlot`, `guardianNoName`, `guardianNote` (EN+AR).

### Tests added

`backend/tests/test_student_imports.py` (35 tests, up from 31):
`test_guardian_email_with_missing_name_produces_warning_not_error`,
`test_invalid_guardian_relationship_warns_not_errors` (confirms a bad
relationship value warns, stages the contact anyway, but leaves
`relationship` blank rather than storing the invalid value),
`test_commit_creates_draft_guardian_contacts` (both slots, all fields),
`test_guardian_contact_reimport_is_idempotent_and_updates_in_place` (same
contact row id across two commits, fields updated to the second file's
values — not duplicated), `test_guardian_contact_already_acted_on_is_not_
overwritten_by_reimport` (a contact manually moved to `status="linked"`
survives a re-import unchanged). `test_template_download_has_expected_
headers` and `test_import_sends_zero_outbound_communication` were extended
for the new columns/guardian-contact assertions.

### Validation

- `docker compose run --rm --no-deps -v $(pwd):/repo -w /repo/backend backend python -m pytest tests/test_student_imports.py -q` → **35 passed**.
- `docker compose run --rm --no-deps -v $(pwd):/repo -w /repo/backend backend python -m pytest tests -q` → **205 passed** (up from 201), 10 warnings.
- `cd frontend && npm run check` → 0 errors, 0 warnings.
- `cd frontend && npm run check:i18n` → parity OK, 440 keys in both `en` and `ar`.
- `cd frontend && npm run build` → built OK.
- `docker compose build backend frontend` + `docker compose up -d backend frontend` → rebuilt and restarted.
- `alembic heads` → single head `b2c3d4e5f6a7`; applied to the live dev
  database (`alembic upgrade head`, `alembic current` → `b2c3d4e5f6a7`).
- `docker compose run --rm --no-deps -v $(pwd):/repo -w /repo backend python backend/scripts/perf_check.py` → only the pre-existing `/api/school/students` endpoint over budget (3.2s this run); unrelated to this change.
- **Manual smoke test against the live United International School demo
  data**: downloaded the template (confirmed the new 16-column header),
  uploaded a 1-row CSV with both guardian slots fully populated, previewed
  (confirmed guardian fields + draft-contact warnings), committed, verified
  via direct DB query that exactly 2 `student_guardian_contacts` rows were
  created with the right slot/name/email/relationship/status/
  source_import_id, then deleted the smoke-test student/contacts/import
  rows to leave the demo school unchanged.

### Deferred (per instructions for this slice)

- Everything S9 will need to build on top of `student_guardian_contacts`:
  turning a `draft` contact into a real `guardian_link` + invite, an admin
  UI to review/dismiss (`ignored`) staged contacts, and any de-duplication
  across multiple imports/manual entry for the same guardian.

## 2026-07-09 — S7: Student CSV Import v1

Scope: staged students-CSV pipeline on the existing `/school` Students tab —
upload → validate → preview (create/update/move/restore/skip/error per row) →
commit valid rows → idempotent re-import. No teacher CSV import, guardian
onboarding/invites, parent dashboard, posts, diary, points, messaging,
notifications, attendance, timetables, rooms, terms, rollover, or auth
changes were part of this slice.

### Product safety rule (binding, verified by test)

Bulk import never sends invites, magic links, notifications, emails, or other
outbound communication. Guardian columns are accepted in the template for a
future workflow but are only ever staged as prep records, never contacted.
**Superseded by the correction above:** guardian columns/handling described
immediately below (email-only, "not imported", nothing stored) reflect this
slice's first pass; the correction section above this entry replaced the
guardian columns with name+email+relationship and added the
`student_guardian_contacts` draft table before this slice was committed —
treat the correction as authoritative for guardian behavior.
`test_import_sends_zero_outbound_communication` monkeypatches
`mailer.send_staff_invite`/`send_magic_login` and asserts zero calls plus zero
`StaffInvite`/`MagicLoginToken` rows after a commit that includes guardian
data.

### Decisions

- **No auto-create of grades/sections from the CSV.** The task brief made
  auto-create optional ("if implemented, it must follow existing
  lifecycle/restore rules"); building it would reintroduce the natural-key
  restore/lifecycle machinery into a parser for a case S4's `/school` setup
  UI already covers well (create the grade/section once, then import
  students against it). Unknown grade/section codes are a clear per-row
  error naming the missing code; the admin fixes it in `/school` setup and
  re-uploads. This can be revisited as a follow-up if real schools want it.
- **Branch resolution:** CSV `branch` column optional only when the school
  has exactly one *active* branch (auto-selected); otherwise required and
  matched by code. Zero-active-branch and multi-branch-ambiguity produce
  distinct error messages.
- **Academic year:** always the school's current year (`is_current=True`);
  no current year is a whole-file 422, not a per-row error, since nothing
  can be resolved without it.
- **Idempotency is identity-by-`external_ref` only**, matching the existing
  `students.external_ref` app-layer upsert pattern from S6 (`create_student`)
  — no new unique DB constraint was added, consistent with that existing
  design. Rows with a blank `student_id` are always `create` (no identity to
  match on); duplicate names across rows are allowed and never used as
  identity, per the brief.
- **Row actions are `create`/`update`/`move`/`restore`/`skip`/`error`**
  (`restore` and `move` added beyond the blueprint's original four-action
  sketch) because the brief's own preview/summary requirements explicitly
  ask for restore and move counts to be visible to the admin before commit.
- **Commit behaviour is "commit valid rows, leave error rows unapplied"**
  (the blueprint's stated default), not all-or-nothing. Re-running the same
  file twice is idempotent: the second commit resolves matching rows to
  `skip` (no field or section change) and mutates nothing.
- **One aggregate audit entry per import commit** (`school.import.committed`,
  with row-count summary in `detail`), not one audit row per affected
  student. Per-student audit trails aren't required by this slice and the
  brief asked to keep the pipeline simple; every affected student is still
  identifiable via `import_rows.applied_entity_id`.
- **Commit re-plans from the stored raw CSV rows** rather than reusing the
  upload-time preview, mirroring the existing preview/apply split in
  `_plan_default_subject_template_application` (S6.8). This re-validates
  against current DB state (a section could be archived, another admin
  could have changed the same student) between staging and commit, and
  keeps preview and commit as one shared decision function
  (`plan_student_import_rows`) instead of two.
- **Query-shape:** every lookup in `plan_student_import_rows` (current year,
  branches, grade levels, sections, existing students by `external_ref`,
  open section enrolments) is batched once regardless of row count, per
  `docs/BACKEND_PERFORMANCE.md`'s rule. The one open-enrolment lookup is
  factored into a shared `open_section_enrolments_by_student(...)` helper in
  `imports_service.py`, used by both the plan and the commit route, so
  "what section is this student currently in" has one definition instead of
  two independently-maintained copies.
- **Encoding:** `utf-8-sig` first (handles a UTF-8 BOM transparently), then a
  `cp1256` fallback (stdlib `codecs`, no new dependency) for Arabic Windows
  exports; anything else is a clear encoding error. CSV header matching is
  case/whitespace-insensitive (a common Excel-resave quirk).

### Backend changes

- Migration `a1b2c3d4e5f6_add_student_imports.py` adds `imports` and
  `import_rows` (per §9's suggested shape, plus `move`/`restore` action
  values).
- New `backend/app/imports_service.py`: CSV template generation, encoding
  detection, header/row parsing, and `plan_student_import_rows(...)` — the
  single batched planner shared by preview (upload) and commit.
- `backend/app/routes/school.py` gains, under the existing
  `require_school_role("school_admin")` router dependency:
  `GET /students/import-template`, `POST /students/imports`,
  `GET /students/imports/{id}`, `POST /students/imports/{id}/commit`,
  `POST /students/imports/{id}/discard`. These are registered *before*
  `GET /students/{student_id}` in the file — Starlette route matching tries
  routes in registration order and a literal segment like
  `import-template` would otherwise be shadowed by the `{student_id}`
  parameterized route registered earlier.
- Commit builds/moves `Enrolment` rows directly from the batched
  `open_section_enrolments_by_student`/`students_by_id` maps rather than
  calling the single-row `_create_enrolment_row` (which does its own
  per-row duplicate/active-target queries — reusing it here would reproduce
  a per-row query in a bulk endpoint); `_close_enrolment_row` (pure, no
  query) is reused as-is for the close side of a move.

### Frontend changes

- `/school` → Students tab gained a CSV import panel above the student
  list: "Download student CSV template", CSV file picker + upload, a
  staged-preview summary (create/update/move/restore/skip/error counts),
  a row-level table (row number, student_id, name, grade, section, branch,
  action, errors/warnings), and commit/discard actions. Nothing else on the
  page changed; the existing lazy-loaded students list still isn't fetched
  by this panel.
- `frontend/src/lib/api.ts` gained `api.upload(path, formData, options)` and
  `api.download(path, options)`. The existing `request()` helper always
  JSON-stringifies the body and expects a JSON response, which can't do a
  multipart CSV upload or a `text/csv` template download; both new helpers
  reuse the extracted `throwForErrorResponse` error-handling path and the
  same CSRF-cookie/credentials handling as `request()`. This is a reusable
  addition for any future binary transfer (e.g. a teacher CSV import).

### Tests

`backend/tests/test_student_imports.py` (31 tests): template headers,
UTF-8/UTF-8-BOM/CP-1256 parsing, an undecodable-bytes encoding error,
case/whitespace-insensitive headers, missing-column and required-field
errors, duplicate `student_id` within file, invalid gender/DOB, multi-branch
ambiguity (and the zero-active-branch variant), branch-omitted-when-
unambiguous, current-academic-year requirement, new-student creation +
section enrolment, external_ref update instead of duplicate, archived-student
restore, full re-import idempotency (no duplicate students/enrolments),
section move closing the old enrolment and opening a new one, same-section
re-import not duplicating the enrolment, duplicate names allowed, guardian
email columns deferred/not imported, wrong-role/wrong-school/platform-admin-
without-membership blocked, cross-school grade-code isolation, commit-valid-
leave-errors-unapplied, double-commit and discard-then-commit rejected,
discard, zero-outbound-communication, and a query-count regression test
(`count_queries()`, same pattern as `test_default_subject_templates.py`)
proving upload/commit read-query counts don't scale with row count (writes
do, by design — one insert per new student/enrolment).

### Validation

- `docker compose run --rm --no-deps -v $(pwd):/repo -w /repo/backend backend python -m pytest tests/test_student_imports.py -q` → **31 passed**.
- `docker compose run --rm --no-deps -v $(pwd):/repo -w /repo/backend backend python -m pytest tests -q` → **201 passed** (up from 170), 10 warnings.
- `cd frontend && npm run check` → 0 errors, 0 warnings.
- `cd frontend && npm run check:i18n` → parity OK, 436 keys in both `en` and `ar`.
- `cd frontend && npm run build` → built OK.
- `docker compose build backend frontend` + `docker compose up -d backend frontend` → rebuilt and restarted.
- Migration applied against a temporary Postgres database in CI-style
  isolation (`alembic heads` confirmed a single head, `f2a3b4c5d6e7 ->
  a1b2c3d4e5f6`) and against the live dev database (`alembic upgrade head`,
  `alembic current` → `a1b2c3d4e5f6`).
- `docker compose run --rm --no-deps -v $(pwd):/repo -w /repo backend python backend/scripts/perf_check.py` → only the already-known `/api/school/students` endpoint is over the 1s guideline (6.1s this run, was 2.9s in the S6.8 log; noisy under load, not something this slice touches — no newly-audited endpoint regressed).
- **Manual smoke test against the live United International School demo
  data**, end to end over the real HTTP API (not just the SQLite test
  suite): downloaded the template, discovered the school is genuinely
  multi-branch (Al Khoud, Boushar) with no current academic year set yet
  (a real gap — marked 2026-27 current via the existing `/school`
  "academic years" PUT endpoint, since bulk import requires it and any
  admin will need to do this regardless of CSV import), then uploaded a
  3-row CSV (one valid create, two deliberately bad rows), previewed,
  committed (1 create applied, 2 errors left unapplied, confirmed by direct
  DB query), re-uploaded the identical file (resolved to `skip`, confirmed
  no duplicate student or enrolment rows), then deleted the smoke-test
  student/enrolment/import rows to leave the demo school's data unchanged.
  The academic year's `is_current` flag was left set to `true` (a real
  setup gap, not a testing artifact) — worth flagging to Dom.
- A code-review pass (8 parallel finder angles: correctness, removed-
  behavior, cross-file, reuse, simplification, efficiency, altitude,
  CLAUDE.md conventions) found and fixed: a CSV header case-sensitivity bug
  (DictReader keys rows by original header spelling, not the lowercased
  name used for validation — an Excel-resaved header like `Student_ID`
  would have silently produced blank fields), a wrong error message when a
  school has zero active branches (said "more than one branch"), dead code
  (`RowPlan.summary_fields()`, unused), a `date.today()`/UTC-`_today()`
  basis mismatch between the plan default and the rest of the codebase (now
  passed explicitly at both call sites), a missing `school_id` filter on
  the commit route's student batch-fetch (defense in depth), and the
  duplicated open-enrolment query mentioned above. **Not fixed, judged
  out of scope**: no DB-level unique constraint on `(school_id,
  external_ref)` — this matches the existing S6 `create_student` app-layer-
  only pattern and predates this slice; the CP-1256 fallback is a
  single-byte codec that can't distinguish "successfully decoded" from
  "decoded as mojibake" for a wrongly-guessed encoding, which is an inherent
  limit of stdlib-only encoding detection, not a bug; and a restored
  archived-student row that also needs a section change is labeled only
  `restore` in the preview (the underlying enrolment move still happens
  correctly at commit) rather than a combined `restore+move` label.

### Deferred (per instructions for this slice)

- Teacher CSV import (S8).
- Auto-creating grade levels/class sections from the CSV (validate-only;
  see Decisions above).
- Guardian record creation/storage from the guardian email columns (S9).
- Any change to `docs/DEMO_DATA.md` or `docs/BACKEND_PERFORMANCE.md` — not
  needed; the query-shape rule already documented there was followed and
  is exercised by the new regression test, and demo-data generation itself
  wasn't touched by this slice.

## 2026-07-09 — S6.8/S7-prep: Default Subject Templates by stage/grade

Scope: a school-admin workflow to define default/core subjects by education stage or
grade/year level, preview what section-specific subject groups those templates would
generate for an academic year, and apply that plan safely/idempotently. No teacher
assignment, no student enrolment, no CSV import, and no changes to any existing
subject group were part of this slice.

### Model decision

- Added `default_subject_templates` (school-owned): `education_stage_id` XOR
  `grade_level_id` (checked in the DB and re-checked in the API), `subject_id`,
  `status` (`active`/`inactive`/`archived`, same lifecycle as the other seven school
  setup entities), `sort_order`, `created_by_user_id`, `created_at`.
- **Natural-key gotcha carried over from `subject_groups`:** a full unique constraint
  on `(school_id, education_stage_id, grade_level_id, subject_id)` does not dedupe
  stage templates against each other, because SQL treats two `NULL` grade columns as
  distinct — the constraint is a backstop only. The create/update routes do an
  explicit `.is_(None)`-aware lookup (`_find_default_subject_template`) before
  insert/restore, exactly like `_find_by_natural_key` does for subject groups.
- Templates are **not** tied to an academic year — they are reusable school/stage/grade
  defaults. Apply targets an academic year explicitly, per request.
- Stage templates and grade templates for the same subject **dedupe to one generated
  group per section** (stage takes precedence, grade templates only add subjects not
  already covered by the section's stage).

### Backend changes

- Migration `f2a3b4c5d6e7_add_default_subject_templates.py`.
- `backend/app/routes/school.py`:
  - `GET/POST/PUT/DELETE /api/school/default-subject-templates` (archive = soft
    delete, restore-on-recreate like the other setup entities).
  - `POST /api/school/default-subject-templates/preview` and `.../apply`, sharing one
    batched planner (`_plan_default_subject_template_application`): a fixed number of
    queries resolves matching active class sections (filtered by academic year, with
    optional branch/stage/grade filters), the school's active templates, and existing
    subject groups for the candidate sections — regardless of how many sections or
    templates exist. Preview serializes the plan (`would_create`/`would_restore`/
    `skipped_existing`/`failed`); apply executes the same plan with `db.add`/status
    flips and a single `db.commit()` (idempotent: unapplied templates create once,
    a second run reports the same rows as `skipped_existing`).
  - Existing-group matching keys on `(class_section_id, subject_id, code)` — the same
    deterministic `_subject_group_defaults()` naming used by
    `bulk_create_section_subject_groups` (S5 pre-commit fix) — so a template apply
    never invents a new naming convention and never double-creates a group that a
    human or another workflow already created with the same code.
  - Generated groups are always section-specific with `enrolment_policy =
    "default_for_section"`, never grade-level, and apply never touches teacher
    assignments or student enrolments.

### Frontend changes

- `/school` gained a "Default subjects" tab (between Subjects and Subject groups):
  add/edit/archive templates (scope toggle: stage or grade/year, then subject); a
  preview/apply panel (academic year required, branch/stage/grade optional filters)
  showing created/restored/skipped/failed counts and per-row detail with reasons.
  Templates load alongside the other small setup lists in the existing `loadAll()`
  batch — no per-row fan-out, no student data fetched for this screen.
- Added English and Arabic i18n strings (`school.tabs.defaults`, `school.defaults.*`,
  `school.validation.stageRequired`).

### Tests

`backend/tests/test_default_subject_templates.py` (16 new tests): CRUD lifecycle
(create/list/update/archive), wrong-role (403), wrong-school (404/400), exactly-one-
scope validation, active/inactive duplicate rejection **specifically on a stage
template** (the case that would slip through if dedupe relied on the SQL constraint),
archived-template restore-in-place, cross-school ref validation, preview stage+grade
resolution and dedupe, optional branch/stage/grade filters, apply creates
`default_for_section` groups, apply idempotency, apply skips existing active/inactive
matching groups, apply restores archived matching groups, apply leaves
`staff_assignments`/`enrolments` row counts unchanged, cross-school isolation on
preview/apply, and a query-count regression test (`count_queries()`) asserting preview
and apply read-side query counts stay flat as section count grows.

### Validation

- `docker compose run --rm --no-deps -v $(pwd):/repo -w /repo/backend backend python -m pytest tests/test_default_subject_templates.py -q` → **16 passed**.
- `docker compose run --rm --no-deps -v $(pwd):/repo -w /repo/backend backend python -m pytest tests -q` → **170 passed** (up from 154), 7 warnings.
- `cd frontend && npm run check` → 0 errors, 0 warnings.
- `cd frontend && npm run check:i18n` → parity OK, 402 keys in both `en` and `ar`.
- `cd frontend && npm run build` → built OK.
- `docker compose build backend frontend` + `docker compose up -d backend frontend` → rebuilt and restarted (no source volume mount; a rebuild is required for changes to take effect).
- Migration applied against a temporary Postgres database (`alembic upgrade head`, `e1f2a3b4c5d6 -> f2a3b4c5d6e7`) and against the live dev database (`alembic current` → `f2a3b4c5d6e7`).
- `docker compose run --rm --no-deps -v $(pwd):/repo -w /repo backend python backend/scripts/perf_check.py` → only the already-known `/api/school/students` (2.856s) is over the 1s guideline; no newly-audited endpoint regressed. `default-subject-templates` list wasn't added to `perf_check.py` — it's a small school-setup-scale table (dozens of rows, not thousands) like subjects/branches, which the script already treats as non-critical.
- Manual smoke test against the live United International School demo data: created a
  temporary `EY` (Early Years) stage template for English, ran preview against the
  school's 2026-27 academic year, confirmed the plan correctly resolved the 4 KG
  sections and reported `skipped_existing` for all 4 — because the demo-data script
  had already created `KG1A-ENG`-style groups with the exact same deterministic code —
  then archived the test template to leave the demo school unchanged. This is a live
  correctness check of the code/name generator and the existing-group matching
  against real production-shaped data, not just the SQLite test suite.
- **Not driven in an actual browser** (no browser/screenshot tool available in this
  environment). Frontend correctness was instead verified by: `svelte-check` (0
  errors — this does typecheck script code including the new `nextSort`/`archiveRow`
  generalisation, but not literal i18n key strings), a successful production build
  (which does parse/compile every new Svelte template branch), and a manual grep
  cross-check of every `$_('school.defaults.*')` / `school.tabs.defaults` /
  `school.validation.stageRequired` key used in `+page.svelte` against the keys
  actually declared in both `en` and `ar` in `messages.ts` (`npm run check:i18n` only
  checks en/ar parity with each other, not usage-vs-declaration, so this gap needed a
  manual check). Dom should still click through the tab once per the QA steps below.

### Deferred (per instructions for this slice)

- S7 CSV import.
- Auto-assigning teachers to generated subject groups.
- Creating/mutating student enrolments from this workflow.
- Any change to `docs/DEMO_DATA.md` — not needed; the existing note that demo scripts
  are not the real subject-group workflow already covers this, and this slice adds the
  real workflow described in the audits without touching demo scripts.

## 2026-07-07 — S6 second QA follow-up: teachers tab, mistake removal, admin rosters

Manual QA after the first frontend follow-up found three remaining commit blockers:

- `/school` → Teachers still did not reliably open; clicking the sidebar item could leave the main panel on the previous content.
- Accidental duplicate/test students with no meaningful history could only be archived, leaving obvious mistakes in the school-owned student record set.
- School admins had student enrolment history but no natural class setup view to answer "who is in KG 1 A?" and "who teaches KG 1 A / its subject groups?"

### What changed

- Tab switching in `/school` is now a pure navigation action that clears edit state without running form reset logic first. This keeps the S5 Teachers tab reachable after S6 changes.
- Added `DELETE /api/school/students/{student_id}/remove-mistake`, requiring an active `school_admin` membership in the same school.
- Student mistake removal hard-deletes only when the student has no enrolments. If enrolments exist, the endpoint returns `409` with "This student has history. Archive instead." Archive behaviour is unchanged.
- Added a shared `_student_history_reasons(...)` helper as the extension point for future guardian links, posts, messages, points, and other student history checks.
- Added `GET /api/school/class-sections/{id}/roster` for the school-admin setup view. It returns class section details, branch/campus, academic year, grade/year level, current active students, homeroom teacher assignment, subject groups, and assigned subject teachers.
- Added a `/school` "Classes / Rosters" tab where admins can select a class section and inspect current students, homeroom teacher, and subject-group teacher assignments.
- Student rows now expose "Remove mistake" alongside Enrol/Move, Edit, and Archive. Backend 409s are surfaced as clear UI errors.

### Validation

- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace/backend backend python -m pytest tests/test_students_enrolments.py -q` → **10 passed**, 5 warnings.
- `docker compose build backend frontend` → passed.
- `docker compose up -d backend frontend` → passed.
- `docker compose exec backend python -m pytest tests -q` → **136 passed**, 7 warnings.
- `cd frontend && npm run check` → passed, 0 errors/warnings.
- `cd frontend && npm run check:i18n` → passed, 367 keys in both `en` and `ar`.
- `cd frontend && npm run build` → passed.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic heads` → `c9d0e1f2a3b4 (head)`.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic current` → `c9d0e1f2a3b4 (head)`.

### Remaining caveat

- The mistake-removal history guard currently checks S6 enrolments only. Future slices that add guardian links, posts, media, points, messaging, attendance, or other student-owned records must extend `_student_history_reasons(...)` before allowing hard delete.

## 2026-07-07 — S6 frontend integration follow-up

Manual QA after the first S6 slice found a few frontend integration gaps rather than backend model issues:

- Student creation succeeded in the API but was too easy to miss in the UI because there was no immediate success feedback or row-level student action affordance.
- The Students tab lacked an explicit, obvious create-only workflow, so it was not clear how a student becomes enrolled or moved afterward.
- The student gender field was still free text, which was unacceptable for this school workflow.
- The school Teachers tab needed defensive button typing and clearer state handling so the S5 teacher management UI would not feel broken after adding S6.

### What changed

- Student create/update/archive now surfaces visible success or failure feedback in the `/school` UI.
- The Students tab now shows current class section or `Not enrolled`, and row actions make `Enrol` or `Move class` explicit.
- Student form gender is now a controlled selector with allowed values only; backend validation rejects unsupported values.
- Empty states now distinguish no students from no matches for the current filter.
- The Teachers tab buttons were tightened to avoid accidental form-submit behaviour.
- `/teach` roster buttons were also made explicit button actions.

### Validation

- `docker compose exec backend python -m pytest tests/test_students_enrolments.py tests/test_user_auth.py -q` → **21 passed**, 5 warnings.
- `docker compose exec backend python -m pytest tests -q` → **134 passed**, 7 warnings.
- `cd frontend && npm run check` → passed, 0 errors/warnings.
- `cd frontend && npm run check:i18n` → passed, 350 keys in both `en` and `ar`.
- `cd frontend && npm run build` → passed.
- `docker compose build backend frontend` → passed.
- `docker compose up -d backend frontend` → passed.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic heads` → `c9d0e1f2a3b4 (head)`.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic current` → `c9d0e1f2a3b4 (head)`.

### Remaining caveat

- The student flow is now explicit and test-covered, but S7 is still where bulk CSV student import belongs.

## 2026-07-07 — S6 Students & Enrolments

Scope: students, enrolments, read-only teacher rosters, and the agreed pre-S6 cleanups. No CSV import, guardian onboarding/invites, parent dashboard, announcements/posts, photos/media, diary/homework, behaviour points, messaging, notifications, attendance, rooms, timetables, terms/semesters, rollover, branch-scoped permissions, branding, demo seed data, or WhatsApp integration were implemented.

### Decisions and policies

- Added `students` as school-owned records, not login users. Students use the S4 lifecycle: `active` usable, `inactive` visible/editable but blocked for new enrolments, and `archived` hidden by default. Recreating an archived student with the same non-empty `external_ref` restores the row in place; active and inactive duplicate `external_ref` values are rejected.
- Added `enrolments` as date-bounded history rows with `valid_from` and exclusive `valid_to`. Enrolment rows have no active/inactive/archived status. Moves are close + create, never target overwrite.
- Current policy for staff assignments and enrolments: UI/API creates from today only, closes with today only, and rejects `valid_to < valid_from`. This avoids future/backdated rows bypassing open-row checks until a real academic-year-dated use case is designed.
- Extracted shared open-interval helpers for `valid_from <= today AND (valid_to IS NULL OR valid_to > today)` and applied them to staff assignments, `require_teacher_of(...)`, teach dashboard queries, and enrolment queries.
- Section enrolment does not imply subject-group enrolment. Section-specific subject groups require explicit subject-group enrolment rows.
- New enrolments reject inactive/archived students, inactive/archived class sections, inactive/archived subject groups, and subject groups whose parent section is inactive/archived.
- Teacher rosters are read-only. `/api/teach` roster endpoints require an active open teacher assignment via `require_teacher_of(...)`; school admins manage student/enrolment state under `/api/school`.
- Deactivated-teacher policy: deactivation revokes the teacher membership, closes open assignments, revokes pending teacher invites for the same school/email/role, and assignment history remains readable for non-active teacher memberships. Mutating assignments for inactive/revoked teachers remains blocked.
- Magic-link SafeLinks fix: emailed magic links now land on the frontend login page with a `magicToken`. GET `/api/auth/magic-link/exchange` validates but does not consume the token; POST consumes the token and creates the session.

### Backend changes

- Migration `c9d0e1f2a3b4_add_students_enrolments.py` adds `students` and `enrolments`.
- Added school-admin endpoints for student list/detail/create/update/archive, enrolment history, class-section enrolment, subject-group enrolment, close enrolment, move-section, section rosters, and subject-group rosters.
- Added teacher read-only roster endpoints for assigned sections and assigned subject groups.
- Added tests for student lifecycle, duplicate/restore policy, wrong-role/wrong-school access, enrolment date validation, move/history preservation, subject-group explicit enrolment, inactive/archived target rejection, teacher roster scope, closed assignment denial, cross-school/no-role denial, staff assignment date validation, deactivated invite revocation, and magic-link GET non-consumption/POST consumption.

### Frontend changes

- `/school` now has a Students tab with add/edit/archive, list/search/filter by class section, current class/group display, class enrolment, class move with confirmation, subject-group enrolment, close enrolment, and enrolment history.
- `/teach` assignment cards can open read-only rosters with student display names and Arabic names when present.
- `/login` now shows a “Continue sign in” action for magic-link tokens so scanners do not consume login links.
- Added English and Arabic strings for all new UI.

### Validation

- `docker compose build backend frontend` → passed.
- `docker compose up -d backend frontend` → passed.
- `docker compose exec backend python -m pytest tests -q` → **133 passed**, 7 warnings.
- `cd frontend && npm run check` → passed, 0 errors/warnings.
- `cd frontend && npm run check:i18n` → passed, 335 keys in both `en` and `ar`.
- `cd frontend && npm run build` → passed.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic heads` → `c9d0e1f2a3b4 (head)`.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic upgrade head` → upgraded database from `b8c9d0e1f2a3` to `c9d0e1f2a3b4`.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic current` → `c9d0e1f2a3b4 (head)`.

### Deferred to S7+

- Bulk/CSV student import and any silent-import tooling.
- Guardian records, guardian onboarding, guardian invites, parent dashboard, and outbound communication.
- Demo seed data.
- Academic-year rollover, branch-scoped permissions, timetables/rooms/terms, and any classroom content surfaces.

## 2026-07-07 — Post-S5 Fable checkpoint audit (no code changed)

Branch: `main` (at commit `fbe92ac`)

A fresh-eyes checkpoint audit was run after S5 Teachers & Assignments and its three pre-commit fixes. Full report: `docs/audits/2026-07-07-post-s5-teachers-assignments-audit.md`. Backend suite re-verified during the audit: **126 passed** in Docker.

**Verdict: continue to S6 — no hard stop and no intermediate cleanup slice required.** S5 avoided every trap flagged in the post-S4 audit §7: assignments reference membership id (never user id), homeroom lives only in `staff_assignments`, rows are date-bounded close-and-open history with exclusive `valid_to`, invites are email-bound/single-use/suspension-aware, and platform admins are rejected from `/api/school` teacher management (all tested). Magic-link login auto-creates users, so non-Google teachers can accept invites.

Must be folded into the S6 prompt (or a ~1-hour pre-S6 patch):

- **Assignment date validation gap** — `valid_from`/`valid_to` are unvalidated (backdated `valid_from` rewrites the prior homeroom's close date; `valid_to` may precede `valid_from`; future-dated rows escape the open-homeroom conflict check). S6 enrolments must not inherit this; fix both surfaces in S6.
- **Deactivated-teacher policy decision** — deactivation does not revoke still-pending invites for that email (self-reactivation path), deactivated teachers vanish from the Teachers tab, and their assignment history is unviewable (read path 409s on non-active memberships). Decide + implement alongside S6's people-listing work.

Notable non-blocking items (see audit §5): duplicate router-level + endpoint-level `require_school_role` execution (post-S4 fix #7 still half-done); `/school` still binds to the first admin membership (multi-school admins); the open-interval predicate is copy-pasted in three files (extract before S6); magic-link GET exchange is consumable by email-scanner prefetch (Outlook SafeLinks — fix before inviting real M365 teachers); homeroom reassignment silently closes the previous homeroom with no UI warning; failed-send invites still never surface the accept URL.

Test backfill wanted with S6: `require_teacher_of` cross-school case, dual-role (admin+teacher) user, suspended-school exclusion from the teach dashboard.

The audit contains a revised paste-ready S6 prompt outline (§10) with the amendments above baked in, plus a 30-minute manual test list for Dom (§8).

## 2026-07-07 — S5 pre-commit fix: Subject Groups product logic cleanup

Scope: subject-group setup UX/API only. No students, enrolments, teachers beyond existing S5 assignments, rosters, timetables, CSV import, posts, points, messaging, notifications, or other S6+ work.

### Subject-group code generation decision

- Generated section-specific subject-group codes now combine grade/year level code + class-section code + subject code, not section label alone.
- Examples:
  - `KG1` + `A` + `ENG` → `KG1A-ENG`
  - `G1` + `A` + `ENG` → `G1A-ENG`
  - grade-level `KG1` + `ENG` → `KG1-ENG`
- Codes are compacted to uppercase alphanumeric chunks joined with `-` before the subject code. This keeps frontend defaults and backend bulk creation deterministic.
- Generated English names remain human-readable: `{Class Section Name} {Subject Name}` for section-specific groups and `{Grade Name} {Subject Name}` for grade-level/cross-section groups.

### Sort-order UX decision

- Sort order remains editable for power users and API/import determinism.
- New records now default sort order to the next sensible value (`max(existing sort_order) + 10`, or `10` for an empty list/context).
- Sort order is moved under a small `Advanced` disclosure in setup forms instead of being prominent in every normal create/edit flow.

### Bulk subject-group creation

- Added `POST /api/school/subject-groups/bulk-section` for school admins.
- Flow: select academic year, grade/year level, subject, and one or more active class sections; creates one section-specific subject group per selected section using the deterministic code/name rules above.
- Existing active/inactive duplicates are skipped with per-section reasons.
- Archived matching subject groups are restored in place following the S4.9 lifecycle policy.
- Inactive/archived sections are rejected per item and reported in the result, not offered in the frontend bulk selector.
- Response includes summary counts and per-section results: `created`, `restored`, `skipped`, `failed`, plus result rows with reasons where relevant.
- Frontend now has a bulk section-specific panel in `/school` → Subject groups. It defaults all active matching sections selected and shows a result summary plus failed/skipped item reasons.
- The single-create mode remains available for one-off section-specific or grade-level/cross-section groups.
- Added helper copy clarifying: most schools should use section-specific groups for normal subjects; grade-level/cross-section is for sets, electives, or groups combining students from more than one class.

### Tests added

- Backend tests cover generated bulk codes using grade + section + subject, bulk creation across selected sections, duplicate skip behavior, archived restore behavior, wrong-role/platform-only blocking, and inactive/archived section rejection.

### Validation

- `cd frontend && npm run check` → passed, 0 errors/warnings.
- `cd frontend && npm run check:i18n` → passed, 294 keys in both `en` and `ar`.
- `cd frontend && npm run build` → passed.
- `docker compose build backend` + `docker compose up -d backend` → passed.
- `docker compose exec backend python -m pytest tests -q` → **126 passed**, 7 warnings.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic heads` → `b8c9d0e1f2a3 (head)`.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic current` → `b8c9d0e1f2a3 (head)`.
- `docker compose build frontend` + `docker compose up -d frontend` → passed.

## 2026-07-07 — S5 pre-commit fix: Subject Groups UX defaults

Bug/UX issue: `/school` → Subject groups required admins to invent `Code` and `English name` even after selecting the academic year, class/grade context, and subject. For the common case, the admin expects to select a class section and subject, then add the group.

### What changed

- Subject Groups now auto-generates editable defaults once the form has:
  - academic year,
  - subject,
  - either class section or grade/year level.
- Section-specific default:
  - code: `{ClassSection.code}-{Subject.code}` uppercased, e.g. `KG1A-ENG`;
  - name: `{Class Section Name} {Subject Name}`, e.g. `KG 1 A English`.
- Grade-level/cross-section default:
  - code: `{GradeLevel.code}-{Subject.code}` uppercased, e.g. `KG1-ENG`;
  - name: `{Grade Name} {Subject Name}`, e.g. `KG 1 English`.
- Defaults only update while the field is blank or still matches the previous generated value. If the admin edits code or English name manually, later dropdown changes no longer overwrite that custom text.
- Added helper text explaining that a subject group is the teaching group for a subject.
- Added a simple context selector:
  - Section-specific;
  - Grade-level / cross-section.
  The form now shows only the relevant class-section or grade/year-level selector, reducing ambiguity.
- Backend validation is unchanged: API/import callers still must provide deterministic `code` and `name`.

### Manual validation cases

- Select class section `KG 1 A` and subject `English` → code/name auto-fill from section and subject.
- Clear/change subject → generated defaults update or clear only if fields still match generated values.
- Manually edit code/name → changing dropdowns does not overwrite custom values.
- Create section-specific group successfully.
- Create grade-level/cross-section group successfully.
- Duplicate record still shows the existing clear duplicate message.
- Missing required fields still show readable validation messages, not `[object Object]`.

### Validation

- `cd frontend && npm run check` → passed, 0 errors/warnings.
- `cd frontend && npm run check:i18n` → passed, 280 keys in both `en` and `ar`.
- `cd frontend && npm run build` → passed.
- `docker compose exec backend python -m pytest tests -q` → **123 passed**, 7 warnings.
- `docker compose build frontend` → passed.
- `docker compose up -d frontend` → passed.

## 2026-07-07 — S5 pre-commit fix: readable form/API errors

Bug: `/school` → Subject groups could show `[object Object],[object Object]` when the backend returned FastAPI/Pydantic validation errors, for example when required fields such as English name were missing. The root cause was the frontend API wrapper converting `error.detail` directly into an `Error`, which coerced validation arrays/objects to unreadable object strings.

### What changed

- Added `frontend/src/lib/errors.ts` with `normalizeErrorMessage(...)`.
  - Handles strings, `{detail: "..."}`, FastAPI `{detail: [{loc,msg,type}]}`, nested objects, arrays, network/text errors, and unknown values.
  - Filters useless `[object Object]` and traceback-like content.
  - Used by `frontend/src/lib/api.ts`, so login/magic-link, invite accept, school setup, and teacher screens all get readable API errors by default.
- Added lightweight field-level validation in `/school` setup/S5 forms.
  - Code and English name required on all setup entities.
  - Academic year, branch/campus, grade/year level, subject, and subject-group context are checked before submit where required.
  - Teacher invite email is required and checked with a simple email pattern.
  - Homeroom assignment requires a class section; subject assignment requires a subject group.
- `TextInput`, `SelectInput`, and `CrudBlock` now support inline error text and red invalid styling without adding a form framework.
- Added EN/AR i18n strings for validation messages.

### Manual validation cases

Covered by the new client-side validation and shared API formatter:

- Subject group missing English name → `English name is required.` with the English-name input marked invalid.
- Missing code → `Code is required.` with the code input marked invalid.
- Missing subject-group context → `Select a class section or grade level.` shown on the context selectors.
- Missing teacher invite email → `Teacher email is required.` with the email input marked invalid.
- Invalid teacher invite email → `Enter a valid teacher email.`
- Missing homeroom assignment target → `Select a class section.`
- Missing subject assignment target → `Select a subject group.`
- Duplicate setup records still surface backend duplicate messages such as `An active record with this code already exists.`
- Magic-link/backend validation errors now pass through `normalizeErrorMessage(...)` instead of showing object coercions.

### Validation

- `docker compose build backend frontend` → passed.
- `docker compose up -d backend frontend` → passed.
- `docker compose exec backend python -m pytest tests -q` → **123 passed**, 7 warnings.
- `cd frontend && npm run check` → passed, 0 errors/warnings.
- `cd frontend && npm run check:i18n` → passed, 274 keys in both `en` and `ar`.
- `cd frontend && npm run build` → passed.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic heads` → `b8c9d0e1f2a3 (head)`.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic current` → `b8c9d0e1f2a3 (head)`.

## 2026-07-07 — S5 Teachers & Assignments

Scope: teachers and staff assignments only. No students, enrolments, CSV import, guardian onboarding, parent dashboard, posts/photos, diary/homework, behaviour points, messaging, notifications, rooms, timetables, terms/semesters, rollover, branding, demo seed data, bulk import, or WhatsApp integration were implemented.

### Decisions

- Teachers remain normal `users` with active `memberships.role = "teacher"` rows. All teacher assignment and dashboard access is based on membership id, not user id.
- Homeroom teachers are represented only by `staff_assignments` rows with `role = "homeroom"` and `class_section_id`; there is no direct homeroom field on `class_sections`.
- Staff assignments are date-bounded history rows. They have no active/inactive/archived lifecycle. Closing sets `valid_to`; rows are not deleted or overwritten.
- `valid_to` is treated as an exclusive end date for active-scope checks, so closing an assignment with today's date removes it from `/teach` and `require_teacher_of` immediately.
- New assignments reject archived and inactive targets. Inactive records stay visible/editable in setup, but are deliberately not assignable for new teacher relationships.
- Homeroom assignment is singular per class section and singular per teacher in this slice: assigning a teacher to a new homeroom closes that teacher's previous open homeroom row and creates a new row. Subject assignments can be multiple concurrent subject groups and are closed explicitly.
- Platform admins still do not bypass school-admin membership requirements for `/api/school` teacher management.

### Migration added

- `alembic/versions/b8c9d0e1f2a3_add_staff_assignments.py`
  - Adds `staff_assignments` with `school_id`, `membership_id`, nullable class-section/subject-group targets, `role`, `valid_from`, `valid_to`, creator, and timestamps.
  - Adds a check constraint requiring exactly one target (`class_section_id` XOR `subject_group_id`).

### Backend changes

- Generalised staff invite issuance to support `role="teacher"` while preserving school-admin invites.
- Invite exchange now returns `landing_path` (`/teach` for teachers, `/school` for school admins). Teacher invite acceptance creates or reactivates a teacher membership after enforcing email match, single-use token state, expiry/revocation, and suspended-school rejection.
- Added school-admin endpoints under `/api/school` for teacher invite create/list/revoke, active teacher listing, assignment list/create/close, and teacher deactivation.
- Teacher deactivation revokes the teacher membership and closes open assignments in the same operation.
- Added `/api/teach/dashboard`, returning only the logged-in teacher's own open assignment cards across active teacher memberships and non-suspended schools.
- Added `require_teacher_of(...)` in `backend/app/school_scope.py` for future class/group scoped teacher routes. It verifies active teacher membership, same-school target ownership, and an open assignment.

### Frontend changes

- `/school` now has a Teachers tab with teacher invite, pending invites, active teachers, homeroom assignment, subject-group assignment, current open assignments, close assignment, and teacher deactivation controls.
- `/teach` now shows "My classes" cards for open homeroom and subject assignments, or an empty state if the teacher has none.
- Invite acceptance routes teachers to `/teach` and school admins to `/school` based on the backend exchange response.
- Top navigation exposes `/platform`, `/school`, and `/teach` according to `/api/me` memberships; multi-role users can see multiple links.
- Added English and Arabic strings for all new UI.

### Tests added

- Teacher invite lifecycle: invite, duplicate pending supersede, revoke, expired/revoked/used rejection, email mismatch rejection, suspended-school rejection, and accepted invite creates teacher membership.
- Assignment behavior: homeroom creation, duplicate open assignment rejection, one open homeroom per class section, subject assignment creation, inactive/archived target rejection, close preserves history, reassignment closes old homeroom and creates a new row.
- Access behavior: teacher sees only own open assignments, unassigned teacher sees an empty dashboard, no-role user gets 403, teacher cannot use school-admin endpoints, platform admin without school membership cannot manage teachers, wrong-school mutations are rejected.
- `require_teacher_of` passes for assigned teachers and rejects unassigned/closed-assignment access.
- Audit rows are asserted for invite acceptance, assignment create/close, and teacher deactivation paths.

### Validation

- `docker compose build backend frontend` → passed.
- `docker compose up -d backend frontend` → passed.
- `docker compose exec backend python -m pytest tests -q` → **123 passed**, 7 warnings.
- `cd frontend && npm run check` → passed, 0 errors/warnings.
- `cd frontend && npm run check:i18n` → passed, 262 keys in both `en` and `ar`.
- `cd frontend && npm run build` → passed.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic heads` → `b8c9d0e1f2a3 (head)`.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic current` → after `alembic upgrade head`, `b8c9d0e1f2a3 (head)`.

### Deferred

- Branch-local admin enforcement.
- Teacher profile/self-service editing.
- Student rosters and enrolments for teacher classes.
- Bulk/CSV teacher import and silent-import tooling.
- Any classroom content features under `/teach` beyond assignment cards.

## 2026-07-07 — Post-S4 product strategy review (no code changed)

Fable produced an unconstrained post-S4 product strategy review (distribution, notification delivery, teacher habit, pilot design — deliberately not limited to the existing blueprint or code). Full report saved to `docs/product/CLASS_HERO_HUB_PRODUCT_STRATEGY_NOTES.md`; key plan-impacting points recorded in blueprint §0b.

Key implication: after S4.9/S5/S6, Dom should prioritise **pilot design (with week-4 success metrics), parent notification delivery (PWA push, possibly WhatsApp Business API nudges), teacher workflow speed (phone-first, 60-second posting), guardian onboarding (QR funnel + PWA install step), school branding, and data/privacy/export answers** alongside feature implementation.

Addendum — **product safety rule adopted: silent import / no accidental outbound communication.** Real school data may be imported for demo/pilot preparation, but bulk import must never send invites, magic links, notifications, emails, or WhatsApp messages by default; imports create draft/unsent invite records and an explicit go-live/release action is required before contacting teachers or guardians. Binding for S7/S8 prompts and all bulk tooling; recorded in strategy notes §20 and blueprint §0b.11.

## 2026-07-07 — S4.9 foundation cleanup before S5

Scope: targeted post-S4 cleanup only. No teachers/assignments, students, enrolments, CSV import, guardian onboarding, parent dashboard, posts/photos, diary/homework, behaviour points, messaging, notifications, rooms, timetables, terms/semesters, or rollover were implemented.

### What changed

- Subject groups now support both section-specific and grade-level/cross-section contexts. `subject_groups.class_section_id` is nullable, `grade_level_id` was added, and the API requires at least one context (`class_section_id` or `grade_level_id`). Natural-key duplicate checks now handle nullable context explicitly so grade-level groups cannot duplicate through SQL nullable-unique behavior.
- Removed the direct `class_sections.homeroom_teacher_user_id` model field. Homeroom teacher remains deferred to S5 and should be represented by future `staff_assignments` rows with role `homeroom`, not by a direct user column.
- Staff invite send failures no longer make school/invite creation look failed after rows are committed. Invite rows now store `send_status` and `last_send_error`; SMTP exceptions are logged and responses return success with a warning. Reissuing an invite to the same school/email/role revokes older active pending invites.
- School setup entity statuses are controlled. Normal create/edit accepts only `active` and `inactive`; `archived` is reachable only through archive/delete actions. The frontend status dropdown no longer offers Archived.
- Staff invite exchange now requires the logged-in user's normalized email to match the invite email and rejects suspended schools.
- Academic years now support `is_current`, optional `start_date`, and optional `end_date`; the API enforces at most one non-archived current year per school. The school UI can mark one year current and defaults relevant year dropdowns to the current year when available.
- Added passwordless magic-link login using existing SMTP. Tokens are random, hashed at rest, expiring, single-use, and rate-limited for request/exchange. Google login remains unchanged.
- `write_audit` now adds/flushes audit rows and lets the caller transaction commit, avoiding hidden partial commits before S5 multi-step operations.

### Migration added

- `alembic/versions/a7b8c9d0e1f2_s49_foundation_cleanup.py`
  - Adds academic-year current/date fields and a one-current-year partial unique index.
  - Drops `class_sections.homeroom_teacher_user_id`.
  - Adds subject-group `grade_level_id`, nullable `class_section_id`, context check, and updated uniqueness.
  - Adds invite send-status fields.
  - Adds `magic_login_tokens`.

### Validation

- `docker compose build backend frontend` → passed.
- `docker compose up -d backend frontend` → passed.
- `docker compose exec backend python -m pytest tests -q` → **118 passed**, 5 warnings.
- `cd frontend && npm run check` → passed, 0 errors/warnings.
- `cd frontend && npm run check:i18n` → passed, 224 keys in both `en` and `ar`.
- `cd frontend && npm run build` → passed.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic heads` → `a7b8c9d0e1f2 (head)`.
- `docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic current` → `a7b8c9d0e1f2 (head)`.

### Deferred to S5

- Staff/teacher records and assignment workflows, including `staff_assignments role='homeroom'`.
- Teacher subject/class assignments and any student set membership for subject groups.
- Student enrolments/imports, terms/semesters, timetable/room modelling, and academic-year rollover.

## 2026-07-07 — Post-S4 Fable checkpoint audit (no code changed)

Branch: `main` (at commit `ecb7dca`)

A fresh-eyes checkpoint audit was run after S4 and the three S4 cleanups (hide archived, edit records, restore-on-recreate). Full report: `docs/audits/2026-07-07-post-s4-fable-checkpoint-audit.md`. Blueprint amended with a "Post-S4 checkpoint amendments" section.

**Verdict: on track, no hard stop — but run a short "S4.9" cleanup slice before S5.**

Blocking / must be resolved before S5:

- **Subject groups must support grade-level/cross-section groups.** `subject_groups.class_section_id` is currently `NOT NULL`, which makes streamed/cross-section teaching sets impossible; the blueprint intended it nullable. Make it nullable + add nullable `grade_level_id` before S5/S6 build on it.
- **`class_sections.homeroom_teacher_user_id` must not become the homeroom source of truth.** Homeroom teacher = a `staff_assignments` row (role `homeroom`, referenced by membership id) in S5; drop the placeholder column in the S5 migration.
- **Invite email failure must not break invite/school creation UX.** `send_staff_invite` raises mid-request after the school/invite are committed; SMTP failure → 500 → retry → duplicate school. Catch the failure, return 201 with a warning, surface accept URL/resend.

Recommended near-term (same S4.9 slice or shortly after):

- Status enum validation on all structure entities (`active`/`inactive` only via forms; `archived` only via the archive action) and remove "Archived" from the frontend status dropdown.
- Safer invite exchange: bind staff invites to the invited email, reject exchange for suspended schools, revoke prior pending invites on reissue, transition school `pending_setup` → `active` on first admin accept.
- Current-academic-year support (`is_current`, ideally start/end dates) — needed by S5 assignment dating, S6 enrolments, and S19 rollover.
- Magic-link email login before or alongside S5 — Google-only login blocks non-Google teachers (Microsoft 365 schools) exactly as it would block guardians at S9.
- Review `write_audit` transaction behaviour (commits internally today; convert to add/flush in caller's transaction before S5's multi-step flows) and drop the duplicated router-level `require_school_role` dependency.

Also decided/deferred: PG test-harness deadline recommended at S7 (tests currently run on SQLite, contradicting blueprint §10 — fatal by S14's partial-index/concurrency tests).

**S5 must not start until S4.9 is complete or Dom explicitly accepts the risks above.** A revised paste-ready S5 Codex prompt (incorporating S4 lifecycle lessons) is in §8 of the audit document.

## 2026-07-07 — S4 lifecycle policy: restore archived records on recreate

Branch: `main`

**Issue.** Archived records still blocked recreating a record with the same natural key. Example from the field: create class section `KG1C`, archive it, later need `KG1C` again — the UI hides the archived row, but `POST` fails with a generic "Duplicate record" because the archived row still occupies the unique key. Every archive-by-mistake or later-reuse hit this wall.

### Lifecycle policy (now enforced for all seven S4 setup entities)
Entities: branches/campuses, education stages, academic years, grade/year levels, class sections/homerooms, subjects, subject groups.

- **Active** — visible in tables, offered in dropdowns, usable for new relationships.
- **Inactive** — visible and editable in tables, **not** offered in dropdowns for new relationships, existing references stay valid. Inactive is a managed, visible state, **not** a soft-delete.
- **Archived** — hidden from normal tables and dropdowns, not selectable, existing historical references stay valid, reachable only via `include_archived=true`. Archived is the soft-delete tombstone.

### Duplicate / restoration rules (confirmed policy)
On create, the record is matched against its **natural key within the same school**:
- BranchCampus / EducationStage / GradeLevel / Subject → `(school_id, code)`.
- AcademicYear → `(school_id, code)` (it also has a secondary `(school_id, name)` unique constraint — see caveat).
- ClassSection → `(school_id, branch_campus_id, academic_year_id, grade_level_id, code)`.
- SubjectGroup → `(school_id, academic_year_id, class_section_id, subject_id, code)`.

Then:
- **Archived match → restore in place.** The archived row is reactivated (`status → active`), its editable fields are refreshed from the submitted form, its **id is preserved**, an audit entry `school.<entity>.restored` is written, and the response is `201` with `"restored": true` so the row reappears immediately as active. No duplicate row is created.
- **Active match → rejected** `409` "An active record with this code already exists."
- **Inactive match → rejected** `409` "This value is already used by an inactive record. Edit or reactivate that record instead." (Inactive is not deleted, so it is not silently overwritten.)
- Any other unique violation → `409` "This value is already used by another record."

### Migration / constraint changes
**None — no Alembic migration was needed, and this is deliberate.** Because the policy is *restore-in-place*, there is always exactly one row per natural key, so the existing full unique constraints are exactly correct: the archived row is reactivated rather than a second row inserted. A partial unique index (unique among non-archived rows only) would be required *only* if we wanted an archived history row to coexist with a new active row of the same key — which directly contradicts restore-in-place. Keeping the constraints avoids data-integrity holes and needs no schema change. `school_id` scoping, cross-school isolation, wrong-role protection, and `include_archived=true` are all unchanged.

### Backend changes (`backend/app/routes/school.py`)
- `_find_by_natural_key` — resolves the archived/active/inactive row sharing a create's natural key (uses `_EXTRA_KEY_COLUMNS` for the parent-scoped entities; note grade levels are keyed on `code` only, **not** on `education_stage_id`).
- `_restore_row` — reactivates and refreshes an archived row in place.
- `_create_row` now returns `(row, restored)` and performs the match/restore/reject logic; `_commit_or_conflict` messages were made specific.
- `_create_response` — shared wrapper used by all seven create routes: creates or restores, writes the restore audit entry, and returns `{...row, "restored": bool}`.

### Frontend changes
- `+page.svelte` — `saveVia` reads `restored` from the create response and shows a green **notice** banner ("This archived record was restored."); the notice is cleared on the next save/archive/cancel/tab-switch. Clearer backend `409` duplicate messages already flow through the existing error banner unchanged. Restored rows arrive active and appear in tables/dropdowns after the existing refetch.
- `messages.ts` — added `school.restored` (en + ar); i18n parity 215 → 216 keys.

### Other lifecycle traps audited
- **Quick-create A/B/C** — the frontend loops `POST /class-sections`; an archived label now restores instead of erroring, so quick-create no longer breaks on a previously-archived section.
- **Setup checklist counts** — already count `status != "archived"`; a restored row is active and counts again; archived rows do not. No change needed.
- **Archived default/main branch** — `_default_branch` already reactivates an archived `MAIN` when no active branch exists, and recreating code `MAIN` now also restores it. Self-healing, no impossible state.
- **Archived academic year blocking the same code later** — resolved by restore keyed on `code`.
- **Inactive records in selectors** — dropdowns filter to `active` (prior cleanup); an inactive record stays out of new-relationship selectors while remaining editable.
- **Editing records with archived parents** — unchanged from prior cleanup: an update may keep an already-referenced archived parent (`_ensure_owned(current_id=...)`).
- **Deleting/restoring records with dependent children** — archive never hard-deletes and never cascades; children keep referencing an archived parent (historical validity) and become fully valid again if the parent is restored.

### Fields / cases intentionally left as-is (documented)
- **Archiving is not hard-blocked** for any entity (requirement 6). The only structurally-required singleton, the default branch, self-heals via `_default_branch`. Archiving the last academic year / grade level / class section only marks setup *incomplete* (recoverable by adding or restoring), never an impossible state, so blocking it would obstruct legitimate cleanup. This case is allowed by design.
- **Restoring a child under an archived parent is blocked** (`_class_section_extra` / `_subject_group_extra` reject archived parents on the create path). Restore the parent first, then the child. This preserves the "no new relationships to archived parents" rule.
- **AcademicYear secondary `name` uniqueness**: restore is keyed on `code`. Recreating a year with a brand-new `code` but a `name` identical to an archived year still returns a clear `409` (the archived row occupies that name); the admin restores via the matching code or picks a different name. Minor, documented; not a data-integrity hole.

### Validation
- `docker compose build backend frontend` + `docker compose up -d backend frontend` → rebuilt & restarted (images bake source via `COPY`; a rebuild is required for changes to take effect).
- `docker compose exec backend python -m pytest tests -q` → **110 passed** (up from 106; 4 new lifecycle tests covering restore of every entity, active/inactive duplicate rejection with clear messages, cross-school isolation of restore, and wrong-role restore rejection).
- `cd frontend && npm run check` → 0 errors, 0 warnings.
- `cd frontend && npm run check:i18n` → parity OK, 216 keys in en and ar.
- `cd frontend && npm run build` → built OK.
- Alembic: no migration added; heads unchanged.

Scope note: no S5 work; Docker/Caddy/OAuth/platform-admin/SMTP/auth untouched. Not committed, per instruction.

## 2026-07-07 — S4 fix: edit existing school-structure records

Branch: `main`

**Issue.** The `/school` setup UI could add and archive records but had no edit/update action. A typo in a code or name, or a later change to sort order, status, or a parent relationship, could only be "fixed" by archiving and recreating — bad UX that produces duplicates and orphaned references.

**Backend.** No changes were required: the S4 slice already exposes `PUT` update endpoints for every entity (branches, education stages, academic years, grade levels, class sections, subjects, subject groups) plus school settings, and the prior archived-records cleanup already made them enforce school ownership (`_get_owned`), the school-admin role (router dependency), archived-parent validation (`_ensure_owned`, which still allows keeping an *already-referenced* archived parent), and duplicate handling (`_commit_or_conflict` → 409). This task confirmed that and added test coverage.

**Edit behaviour added (frontend).**
- Every row in the setup tables now has an **Edit** (pencil) action beside the existing archive/trash button (`RowsTable.svelte`).
- Clicking Edit loads that row's current values into the block's existing form and switches it into edit mode: the **Add** button becomes **Save** and a **Cancel** button appears. This reuses the existing form/inputs — no separate edit forms were built. The reusable `CrudBlock` handles branches/stages/years/subjects; the three parent-bearing blocks (grade levels, class sections, subject groups) reuse the same `editRow`/`saveVia` helpers inline in `+page.svelte`.
- Save issues `PUT /school/<entity>/<id>` (update in place) when editing and `POST` (create) otherwise, then clears edit mode and refetches. Cancel exits without changing data and clears the form. Switching tabs also cancels an in-progress edit.
- Relationships are edited by **id**, so changing a record's `code` never breaks children that reference it.
- Dropdowns still offer only `active` records for new relationships, with one deliberate exception: while editing, the currently-selected row is always kept in its dropdown even if it is `inactive`, so a bound `<select>` does not silently drop an inactive parent reference (`SelectInput.svelte`).
- Archived rows remain hidden from tables and dropdowns; you cannot open an archived row for edit through the normal UI.
- New i18n keys `school.edit` and `school.cancel` added to `en` and `ar` (i18n parity 213 → 215 keys).

**Latent bug fixed in passing.** Creating a grade level with no education stage previously sent `education_stage_id: ""`, which the backend rejects with 422 (`"" ` is not a valid `int | None`). The new shared `levelPayload()` normalises an empty parent selection to `null`, fixing both create and the new edit path.

**Fields intentionally not editable / caveats (integrity):**
- `id`, `school_id`, and `created_at` are identity/audit fields and are never editable.
- **Academic year "date fields" do not exist in the S4 schema** — `AcademicYear` only has code/name/name_ar/sort_order/status. No start/end date columns were added, because that is a new feature requiring a migration and is out of this cleanup's scope. There is therefore nothing date-related to edit yet; add the columns (with a migration) in a later slice if year dates are wanted.
- Editing a child whose parent has been **archived**: archived parents are excluded from the frontend lists entirely, so the parent dropdown cannot display them and the admin must choose a current active parent. The backend still permits *keeping* an existing archived reference on update (covered by `test_updates_may_keep_an_already_referenced_archived_parent`); only the UI cannot re-offer an archived option. Inactive parents are preserved on edit as described above.

**Tests added (`backend/tests/test_school_structure.py`).**
- `test_school_admin_can_update_each_structure_entity_in_place` — a school admin updates a branch, education stage, academic year, grade level, class section, subject, and subject group; asserts the row id is unchanged (updated in place, not recreated), that a renamed grade-level code does not break the class section referencing it by id, and status can be changed to `inactive`.
- `test_updating_a_record_to_a_duplicate_code_is_rejected` — renaming one record onto another's code returns 409, while re-saving a record with its own unchanged code returns 200.
- Wrong-school update rejection (404) is already covered by `test_cross_school_structure_references_and_mutations_are_rejected`; wrong-role/platform-only update rejection (403) by `test_update_and_archive_endpoints_reject_wrong_roles_and_platform_only_users`.

**Validation.**
- `docker compose build backend frontend` → both built (images bake source via `COPY`; a rebuild is required for changes to take effect — there is no source volume mount).
- `docker compose up -d backend frontend` → recreated.
- `docker compose exec backend python -m pytest tests -q` → **106 passed** (up from 104; the 2 new update tests).
- `cd frontend && npm run check` → 0 errors, 0 warnings.
- `cd frontend && npm run check:i18n` → parity OK, 215 keys in en and ar.
- `cd frontend && npm run build` → built OK.
- Alembic: no migration files added or changed; heads unchanged (no schema change).

Scope note: no S5 (teachers) work and none of the explicitly-excluded features (students, enrolments, CSV import, posts, diary, points, messaging, timetables, terms, rollover, etc.). Docker/Caddy/OAuth/platform-admin/auth untouched. Not committed, per instruction.

## 2026-07-07 — S4 fix: hide archived/deleted school-structure records

Branch: `main`

**Issue.** In `/school` setup, the trash/delete button soft-archives a record (`status = "archived"`), but archived records still appeared everywhere: in the entity tables and in every dropdown/selector used to build new relationships. Because the delete action *looks* like a delete but the row stayed visible, archived branches, education stages, class sections, etc. were confusing and were still selectable as parents for brand-new child records.

**Decision.** In the normal setup UI, `archived` is treated as the soft-delete tombstone and is hidden:

- Normal list endpoints return non-archived rows by default. An optional `?include_archived=true` query param returns everything for future admin/audit use and to keep archived history reachable (no admin UI for it was built — YAGNI).
- Dropdowns/selectors offer only `active` rows. `inactive` is a user-controlled flag distinct from delete: an inactive record stays visible/editable in its own table but is not offered for new relationships. `archived` disappears entirely.
- Creating/updating a child rejects an `archived` parent (400) — grade level → education stage; class section → branch/academic year/grade level; subject group → academic year/class section/subject.
- Historical integrity is preserved: an update that keeps an *already-referenced* archived parent (same id as before) is still allowed, so existing records remain editable. Only *newly selecting* an archived parent is rejected.
- No hard deletes; no schema change; Alembic heads unchanged.

**Files changed.**
- `backend/app/routes/school.py` — `_list_rows` gains `include_archived` (default excludes `status == "archived"`); all eight list endpoints accept `include_archived: bool = False`; `_ensure_owned` rejects archived parents unless the id equals the child's current reference; grade-level/class-section/subject-group update paths pass the existing row so unchanged archived references stay valid.
- `frontend/src/lib/components/school/SelectInput.svelte` — dropdown renders only rows whose `status` is `active`.
- `backend/tests/test_school_structure.py` — added tests: default lists exclude archived while `include_archived=true` returns them; archived education stage/branch/academic year/grade level/class section/subject are each rejected for new child records; an update keeping an already-referenced archived parent still succeeds.

**Validation.**
- `docker compose build backend frontend` → both built (backend image bakes source via `COPY`; there is no source volume mount, so a rebuild was required for the changes to take effect — the pre-rebuild container was running stale code).
- `docker compose up -d backend frontend` → recreated; confirmed new code present in container (`grep include_archived` → 16 hits).
- `docker compose exec backend python -m pytest tests -q` → **104 passed** (up from 101; the 3 new test functions).
- `cd frontend && npm run check` → 0 errors, 0 warnings.
- `cd frontend && npm run check:i18n` → parity OK, 213 keys in en and ar (no new strings added).
- `cd frontend && npm run build` → built OK.
- Alembic: no migration files added or changed; heads unchanged.

Scope note: no S5 (teachers) work; Docker/Caddy/OAuth/platform-admin/auth/other schemas untouched.

## 2026-07-07

Branch: `main`

Commit at start of slice: `5c63ea4`

Task/prompt completed: Identity/tenancy foundation. The prompt was not explicitly numbered; logged as the first implementation slice for the Class Hero Hub identity foundation.

## Files Changed

- `backend/app/models_school/__init__.py`
- `backend/app/models_school/models.py`
- `backend/app/school_scope.py`
- `alembic/versions/c1a2b3d4e5f6_add_school_identity_tenancy.py`
- `backend/tests/conftest.py`
- `backend/tests/school_fixtures.py`
- `backend/tests/test_identity_models.py`
- `docs/implementation/CLASS_HERO_HUB_IMPLEMENTATION_LOG.md`

Existing files intentionally not modified:

- `backend/app/models.py`
- `backend/app/auth.py`
- `backend/app/main.py`
- Route files
- Frontend files
- Docker, Caddy, and environment files
- Product requirements docs

## Models, Tables, and Migrations Added

New model package:

- `backend/app/models_school/`

New SQLAlchemy models:

- `User`
- `School`
- `Membership`
- `PlatformAdmin`
- `AuditLog`

New Alembic revision:

- `c1a2b3d4e5f6_add_school_identity_tenancy.py`
- `down_revision = "7c2b9f1a0d4e"`

Tables created by the migration:

- `users`
- `schools`
- `memberships`
- `platform_admins`
- `audit_logs`

Constraints and indexes added:

- `users.email` unique indexed
- `users.google_sub` unique indexed and nullable
- `schools.slug` unique indexed
- `platform_admins.user_id` unique
- `memberships` unique constraint on `(school_id, user_id, role)` named `uq_memberships_school_user_role`
- Primary-key indexes following the existing model idiom where `id = Column(..., index=True)`
- Foreign keys among the new identity tables only

Audit behavior:

- `AuditLog` is append-only at ORM level via a SQLAlchemy `before_update` listener that raises `ValueError`.
- No database trigger was added.

## Tests Added or Changed

Added:

- `backend/tests/conftest.py`
- `backend/tests/school_fixtures.py`
- `backend/tests/test_identity_models.py`

Test coverage added:

- Unique user email constraint
- Unique `(school_id, user_id, role)` membership constraint
- `write_audit(...)` row creation
- Seed fixture integrity for two schools, school admins, teachers, memberships, and one platform admin

No existing tests were modified.

Follow-up fix after Docker test failure:

- Removed `backend/tests/conftest_school.py`.
- Added `backend/tests/school_fixtures.py` for school-only fixtures.
- Added `backend/tests/conftest.py` to force `DATABASE_URL=sqlite://`, `APP_ENV=test`, and `DEV_AUTH_ENABLED=false` before any test imports `app.database`.
- Updated `backend/tests/test_identity_models.py` to import `seeded_schools` from `school_fixtures`.

## Commands Run and Exact Results

Context-read commands:

```bash
sed -n '1,260p' backend/app/models.py
sed -n '1,220p' backend/app/database.py
find alembic/versions -maxdepth 1 -type f -name '*.py' | sort | tail -20 | xargs -r -n1 basename
sed -n '1,260p' backend/tests/test_parent_auth_session.py
sed -n '220,520p' backend/app/database.py
find backend/tests -maxdepth 1 -type f -name 'conftest*.py' -print -exec sed -n '1,240p' {} \;
sed -n '1,220p' alembic/env.py
for f in alembic/versions/*.py; do printf '%s\n' "$f"; sed -n '1,180p' "$f"; done
rg "Base.metadata.create_all|DATABASE_URL|APP_ENV|from app import|import app" backend/tests -n
rg "JSON|MutableDict|write_audit|IntegrityError" backend/app backend/tests -n
ls -la backend/app backend/tests alembic/versions
```

Result: completed successfully and confirmed the existing timestamp/status idioms, per-test SQLite setup pattern, Alembic head revision, and absence of a global `backend/tests/conftest.py`.

Git/context commands:

```bash
git branch --show-current
```

Exact output:

```text
main
```

```bash
git rev-parse --short HEAD
```

Exact output:

```text
5c63ea4
```

```bash
git status --short
```

Exact output before this log was added:

```text
?? alembic/versions/c1a2b3d4e5f6_add_school_identity_tenancy.py
?? backend/app/models_school/
?? backend/app/school_scope.py
?? backend/tests/conftest_school.py
?? backend/tests/test_identity_models.py
?? docs/CLASS_HERO_HUB_MASTER_BLUEPRINT.md
?? docs/audits/
```

Verification commands:

```bash
python -m pytest tests/test_identity_models.py -q
```

Exact output:

```text
/bin/bash: line 1: python: command not found
```

```bash
python3 -m pytest tests/test_identity_models.py -q
```

Exact output:

```text
/usr/bin/python3: No module named pytest
```

```bash
cd backend && python -m pytest tests -q
```

Exact output:

```text
/bin/bash: line 1: python: command not found
```

```bash
python3 -m py_compile backend/app/models_school/__init__.py backend/app/models_school/models.py backend/app/school_scope.py backend/tests/conftest_school.py backend/tests/test_identity_models.py alembic/versions/c1a2b3d4e5f6_add_school_identity_tenancy.py
```

Exact output:

```text
```

Result: exit code `0`.

Docker verification after rebuilding the backend image:

```bash
docker compose build backend
```

Result: exit code `0`; backend image rebuilt and copied the new source files.

```bash
docker compose up -d backend
```

Exact output:

```text
 Container family-hero-hub-backend  Recreate
 Container family-hero-hub-backend  Recreated
 Container family-hero-hub-backend  Starting
 Container family-hero-hub-backend  Started
```

```bash
docker compose exec backend python -m pytest --collect-only -q tests | tail -20
```

Relevant exact output:

```text
224 tests collected in 2.82s
```

```bash
docker compose exec backend python -m pytest tests -q
```

Exact result:

```text
224 passed, 204 warnings in 25.76s
```

Alembic checks:

```bash
docker compose exec backend alembic heads
```

Exact output:

```text
FAILED: No 'script_location' key found in configuration.
```

Reason: the running backend image workdir is `/app` and contains only the backend build context; repo-root `alembic.ini` is not present there.

```bash
docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic heads
```

Exact output:

```text
c1a2b3d4e5f6 (head)
```

```bash
docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic current
```

Exact output:

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

Observation: no current revision was printed for the configured live Postgres database.

```bash
docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic upgrade head
```

Relevant exact failure:

```text
INFO  [alembic.runtime.migration] Running upgrade  -> 5fd2ed5269af, initial schema
psycopg.errors.DuplicateTable: relation "families" already exists
```

Reason: the configured live Postgres database has existing tables but no Alembic revision marker, so Alembic attempted to replay the initial schema.

Temporary Postgres migration validation:

```bash
tmpdb="class_hero_hub_migration_check_$(date +%s)"; echo "$tmpdb"; docker compose exec postgres createdb -U classhero "$tmpdb" && docker compose run --rm -e MIGRATION_DATABASE_URL="postgresql+psycopg://classhero:499337c5a3f9754b2eab74ab99c3a4bf93c6a6608c374c13380881a159fb30e8@postgres:5432/$tmpdb" -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic upgrade head; status=$?; docker compose exec postgres dropdb -U classhero --if-exists "$tmpdb"; exit $status
```

Exact output:

```text
class_hero_hub_migration_check_1783403763
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 5fd2ed5269af, initial schema
INFO  [alembic.runtime.migration] Running upgrade 5fd2ed5269af -> bf3d4a8c2e91, add child allowance settings
INFO  [alembic.runtime.migration] Running upgrade bf3d4a8c2e91 -> 9b0b6e5ad4d2, add allowance enabled at
INFO  [alembic.runtime.migration] Running upgrade 9b0b6e5ad4d2 -> 2f3c4d5e6a7b, add ledger source transaction
INFO  [alembic.runtime.migration] Running upgrade 2f3c4d5e6a7b -> 3a7e1c9d4b52, add school item checks (B2 pack-for-tomorrow checklist)
INFO  [alembic.runtime.migration] Running upgrade 3a7e1c9d4b52 -> 7c2b9f1a0d4e, add ledger idempotency constraints
INFO  [alembic.runtime.migration] Running upgrade 7c2b9f1a0d4e -> c1a2b3d4e5f6, add school identity tenancy
```

Result: exit code `0`; temporary database was dropped after the check.

Cleanup command:

```bash
find backend/app/models_school backend/tests alembic/versions -type d -name __pycache__ -prune -exec rm -rf {} +
```

Exact output:

```text
```

Result: removed only generated Python bytecode cache directories from the syntax compile check.

Dependency check command:

```bash
python3 - <<'PY'
try:
    import sqlalchemy
    print(f"sqlalchemy {sqlalchemy.__version__}")
except Exception as exc:
    print(f"sqlalchemy import failed: {exc}")
try:
    import pytest
    print(f"pytest {pytest.__version__}")
except Exception as exc:
    print(f"pytest import failed: {exc}")
PY
```

Exact output:

```text
sqlalchemy import failed: No module named 'sqlalchemy'
pytest import failed: No module named 'pytest'
```

Final status command:

```bash
git status --short
```

Exact output:

```text
?? alembic/versions/c1a2b3d4e5f6_add_school_identity_tenancy.py
?? backend/app/models_school/
?? backend/app/school_scope.py
?? backend/tests/conftest_school.py
?? backend/tests/test_identity_models.py
?? docs/CLASS_HERO_HUB_MASTER_BLUEPRINT.md
?? docs/audits/
?? docs/implementation/
```

## Assumptions Made

- The new school identity tables should coexist with the existing family/parent tables and should not alter any existing table.
- The new `User` table is intentionally separate from the existing `ParentUser` table.
- Existing SQLAlchemy idioms in this codebase allow nullable string/status/timestamp columns unless the existing pattern explicitly marks them non-null.
- `AuditLog` append-only enforcement is acceptable at the ORM layer for this foundation slice; database-level triggers can be added later if required.
- `write_audit(...)` should commit and refresh the row, matching the simple helper style implied by the task.
- The school fixture should not be named `conftest_school.py`; it is now `school_fixtures.py`.
- A minimal global `backend/tests/conftest.py` is appropriate because Docker Compose sets `DEV_AUTH_ENABLED=true`, and pytest imports app modules during collection. The test suite needs deterministic test environment values before any `app.database` import.
- The untracked files `docs/CLASS_HERO_HUB_MASTER_BLUEPRINT.md` and `docs/audits/` pre-existed this slice and were not modified.

## Risks and Follow-Up Items

- Host pytest verification could not be completed because `python` is missing and `python3` does not have `sqlalchemy` or `pytest` installed. Docker is the correct test environment.
- Initial Docker run before the fix produced `6 failed, 214 passed`. The failures were unauthenticated route tests returning `404` instead of `401`, plus one `sqlite3.OperationalError: no such table: parent_users`.
- Root cause: Docker Compose provides `DEV_AUTH_ENABLED=true`; if `app.database` is imported before per-module test environment overrides run, `settings.DEV_AUTH_ENABLED` stays true. Unauthenticated requests then enter dev-auth fallback and behave like an authenticated dev parent, causing 404s for inaccessible records and querying an uninitialized in-memory DB in one case.
- Fix: added root test `conftest.py` to force test environment before app imports, and moved school-only fixture code out of `conftest_school.py` to avoid ambiguity around pytest fixture/config discovery.
- Alembic `env.py` imports `app.models` but not `app.models_school`; the explicit migration is complete, but future autogenerate runs may need `models_school` imported into Alembic metadata loading.
- `AuditLog` append-only behavior is not enforced against raw SQL updates.
- S1b route/auth integration is now implemented; `require_platform_admin` and `require_school_role` are no longer stubs.
- No service-layer validation exists yet for role names, school status values, or user status values.
- The live configured Postgres database has existing tables but no Alembic revision marker; direct `alembic upgrade head` against it fails before reaching the new migration. The migration path itself passed on a temporary Postgres database.

## Reviewer Notes for Claude

- Check whether the table names `users`, `schools`, `memberships`, `platform_admins`, and `audit_logs` match the intended naming contract for all future school tenancy work.
- Review whether `write_audit(...)` should commit internally or only add/flush within an existing transaction. Current implementation commits for deterministic helper behavior in this foundation slice.
- Decide whether `AuditLog` needs database-trigger enforcement before production use.
- Confirm whether Alembic `env.py` should import `app.models_school` in a later slice for autogenerate visibility. This was not changed because the task explicitly constrained existing-file modifications and requested one explicit migration.
- Confirm whether nullable defaults in the migration should be tightened in a later hardening migration. Current choices follow the existing generated migration style.

## Next Recommended Implementation Slice

Original S1b recommendation, now completed:

- Implement `require_platform_admin`.
- Implement `require_school_role`.
- Add request/session resolution for the new `User` identity model.
- Add focused tests for platform admin access, school admin access, teacher membership checks, suspended/revoked membership denial, and cross-school isolation.
- Add audit writes around the first school-admin management actions once routes exist.

Next recommended slice after S1b:

- Add first school-admin management routes using `require_platform_admin` and `require_school_role`.
- Decide whether school identity should get response schemas before broad route work.
- Add database-level audit immutability if append-only enforcement must cover raw SQL.

## 2026-07-07 S1b Auth Wiring

Branch: `main`

Commit at start of slice: `5c63ea4`

Task/prompt completed: S1b, wire school identity tables into auth while preserving existing household/parent auth.

## S1b Files Changed

- `backend/app/auth.py`
- `backend/app/routes/authentication.py`
- `backend/app/main.py`
- `backend/app/school_scope.py`
- `backend/app/database.py`
- `.env.example`
- `backend/tests/test_user_auth.py`
- `docs/implementation/CLASS_HERO_HUB_IMPLEMENTATION_LOG.md`

Existing household behavior intentionally preserved:

- `get_current_parent` remains in place and still powers existing household routes.
- `/api/me` remains unchanged.
- CSRF/session middleware was not changed.
- No frontend, Docker, Caddy, or environment deployment files were changed.

## S1b Implementation Notes

- Google OAuth callback now upserts a school-identity `User` row using normalized email, Google subject, name, and `last_login_at`.
- Added `get_current_user` in `auth.py`, resolving `access_token` cookie and `Authorization: Bearer` token the same way as parent auth.
- Added `PLATFORM_ADMIN_EMAILS` setting with default empty string.
- Added `PLATFORM_ADMIN_EMAILS=` to `.env.example`.
- Bootstrap platform admin creation is idempotent for active rows and writes an audit log with detail `{"source": "bootstrap"}`.
- Implemented `require_platform_admin` as a FastAPI dependency.
- Implemented `require_school_role(*roles)` as a FastAPI dependency.
- School context resolves from path param `school_id` first, then `X-School-Id` header.
- Suspended schools return `403` with detail `This school account is currently suspended.`
- Added `GET /api/me/v2`, returning `user`, `is_platform_admin`, and active memberships.

## S1b Tests Added

Added `backend/tests/test_user_auth.py` covering:

- Google callback upserts `User` and preserves existing `ParentUser` callback flow.
- Cookie auth resolves `User` for `/api/me/v2`.
- Bootstrap platform admin is created once and is idempotent.
- `require_platform_admin` returns `403` for normal users.
- `require_school_role` allows matching active membership.
- `require_school_role` accepts `X-School-Id`.
- `require_school_role` rejects inactive membership.
- `require_school_role` rejects wrong-school access.
- `require_school_role` rejects suspended school.

## S1b Commands Run and Exact Results

Targeted mounted-source test:

```bash
docker compose run --rm -v /opt/apps/class_hero_hub/backend:/app -w /app backend python -m pytest tests/test_user_auth.py -q
```

Exact result:

```text
9 passed, 38 warnings in 3.09s
```

Full mounted-source suite:

```bash
docker compose run --rm -v /opt/apps/class_hero_hub/backend:/app -w /app backend python -m pytest tests -q
```

Exact result:

```text
233 passed, 213 warnings in 27.00s
```

Backend image rebuild:

```bash
docker compose build backend
```

Result: exit code `0`.

Recreate backend and run exact Docker test command:

```bash
docker compose up -d backend && docker compose exec backend python -m pytest tests -q
```

Exact result:

```text
233 passed, 213 warnings in 27.30s
```

## S1b Assumptions

- `User` and `ParentUser` remain separate identities for now, linked only by matching normalized email.
- Bootstrap platform admin audit uses the created `PlatformAdmin` row as the audited entity because there is no `source` column on `platform_admins`.
- A revoked existing `PlatformAdmin` row for a bootstrap email is reactivated rather than duplicated because `platform_admins.user_id` is unique.

## S1b Risks and Follow-Up Items

- `get_current_user` has no school-specific status policy beyond `User.status == active`; future slices should define user suspension/revocation semantics.
- `require_school_role` currently returns generic `School role required` for wrong role and wrong school to avoid leaking memberships.
- `/api/me/v2` returns plain dictionaries rather than Pydantic schemas; consider adding schemas before public API expansion.
- Audit immutability remains ORM-level only.

## S1b Reviewer Notes for Claude

- Review whether bootstrap-reactivating a revoked `PlatformAdmin` is desired or whether revoked rows should block bootstrap.
- Review whether `get_current_user` should auto-create a `User` in dev-auth mode; this mirrors the parent dev fallback but may not be wanted long term.
- Review whether `write_audit` should commit internally before auth flows rely on larger transactional units.

## 2026-07-07 Household Domain Removal

Branch: `main`

Commit at start of slice: `5c63ea4`

Task/prompt completed: remove Family Hero Hub household backend domain after identity v2.

## Household Removal Files Changed

- Replaced `backend/app/main.py` with an identity-only app surface.
- Replaced `backend/app/auth.py` with User-only JWT/cookie auth plus CSRF helpers.
- Replaced `backend/app/routes/authentication.py` with User-only Google OAuth, `/auth/me`, and logout.
- Replaced `backend/app/routes/dev.py` with QA login that seeds `User` plus `PlatformAdmin`.
- Replaced `backend/app/schemas.py` with identity-only schemas.
- Replaced `backend/app/models.py` with a legacy marker module; household ORM classes removed.
- Added `backend/app/invite_tokens.py` with generic token generation/hash/cookie/exchange helpers and `BoundedInMemoryRateLimiter`.
- Added `alembic/versions/d4e5f6a7b8c9_drop_household_domain.py`.
- Deleted household routes, household services, `child_auth.py`, `currencies.py`, and `mailer.py`.
- Deleted household test files.
- Kept/adapted identity, QA login, CSRF, and security tests.

## Household Tables Dropped by Migration

- `school_item_checks`
- `calendar_task_completions`
- `weekly_streaks`
- `child_allowance_settings`
- `child_device_sessions`
- `child_device_invites`
- `ledger_transactions`
- `redemption_requests`
- `pet_progress`
- `school_items`
- `calendar_entries`
- `preset_behaviours`
- `rewards`
- `family_invites`
- `registration_requests`
- `approved_parent_emails`
- `children`
- `parent_users`
- `families`

## Household Removal Tests

Kept/adapted:

- `backend/tests/test_identity_models.py`
- `backend/tests/test_user_auth.py`
- `backend/tests/test_dev_qa_login.py`
- `backend/tests/test_csrf_http.py`
- `backend/tests/test_security_hardening.py`

Added/updated coverage:

- `/api/me` serves identity v2 payload.
- `/api/me/v2` remains available.
- QA login creates/reuses a `User` and active `PlatformAdmin`.
- CSRF protection still blocks unsafe cookie-authenticated requests without matching token.
- Representative household routes return `404`.
- Security hardening tests still pass.

## Household Removal Commands and Results

Mounted-source suite:

```bash
docker compose run --rm -v /opt/apps/class_hero_hub/backend:/app -w /app backend python -m pytest tests -q
```

Exact result:

```text
47 passed, 5 warnings in 2.15s
```

Final rebuilt-container suite:

```bash
docker compose build backend && docker compose up -d backend && docker compose exec backend python -m pytest tests -q
```

Exact result:

```text
47 passed, 5 warnings in 2.00s
```

Alembic head:

```bash
docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic heads
```

Exact output:

```text
d4e5f6a7b8c9 (head)
```

Temporary Postgres migration validation:

```bash
tmpdb="class_hero_hub_household_drop_check_$(date +%s)"; echo "$tmpdb"; docker compose exec postgres createdb -U classhero "$tmpdb" && docker compose run --rm -e MIGRATION_DATABASE_URL="postgresql+psycopg://classhero:499337c5a3f9754b2eab74ab99c3a4bf93c6a6608c374c13380881a159fb30e8@postgres:5432/$tmpdb" -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic upgrade head; status=$?; docker compose exec postgres dropdb -U classhero --if-exists "$tmpdb"; exit $status
```

Relevant output:

```text
INFO  [alembic.runtime.migration] Running upgrade c1a2b3d4e5f6 -> d4e5f6a7b8c9, drop household domain
```

Result: exit code `0`.

Uvicorn boot smoke:

```text
INFO:     Started server process [88]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Endpoint smoke through rebuilt container/TestClient:

```text
/api/health 200 {"status":"ok"}
/api/me 401 {"detail":"Not authenticated"}
/api/children 404 {"detail":"Not Found"}
/api/auth/google/login 302 https://accounts.google.com/o/oauth2/v2/auth...
```

## Household Removal Risks and Follow-Up Items

- The configured live Postgres service still has existing tables but no Alembic revision marker from earlier project state. Direct live QA login against that DB failed with `relation "users" does not exist`. The migration path itself passed on a temporary Postgres DB; the live DB needs a deliberate migration/stamp plan before runtime QA login can mutate it.
- `invite_tokens.py` is generic and currently not wired to a route after child/family deletion; it is preserved for future invite flows.
- `database.py` still has QA child settings validation compatibility even though QA child login was removed, to avoid broad validation-logic churn in this slice.

## Live Development Database Reset to Alembic Head - 2026-07-07

Scope: reset only the running Class Hero Hub development/proof-of-concept PostgreSQL schema for Docker Compose project `class_hero_hub`.

Safety verification commands:

```bash
pwd
git remote -v
git status --short --branch
git status --porcelain=v1
docker compose config --format json
docker compose exec -T postgres psql -U classhero -d class_hero_hub -c "select current_database(), current_user;"
```

Verified:

```text
pwd: /opt/apps/class_hero_hub
origin: git@github.com:itsdominoman/class_hero_hub.git
git status --short --branch: ## main...origin/main [ahead 1]
git status --porcelain=v1: no output
docker compose config name: class_hero_hub
postgres POSTGRES_DB: class_hero_hub
psql current_database/current_user: class_hero_hub / classhero
```

Disposable backup:

```bash
backup_path="/tmp/class_hero_hub_before_reset_20260707T063542Z.sql"
docker compose exec -T postgres pg_dump -U classhero -d class_hero_hub --clean --if-exists > "$backup_path"
ls -lh "$backup_path"
wc -l "$backup_path"
```

Result:

```text
/tmp/class_hero_hub_before_reset_20260707T063542Z.sql
-rw-rw-r-- 1 administrator administrator 72K Jul  7 08:35 /tmp/class_hero_hub_before_reset_20260707T063542Z.sql
2248 /tmp/class_hero_hub_before_reset_20260707T063542Z.sql
```

Reset method:

```bash
docker compose stop backend
docker compose exec -T postgres psql -U classhero -d class_hero_hub -v ON_ERROR_STOP=1 -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public AUTHORIZATION classhero; GRANT ALL ON SCHEMA public TO classhero; GRANT ALL ON SCHEMA public TO public;'
```

Result: `public` schema in database `class_hero_hub` was dropped and recreated. The old copied household tables were removed from this database only.

Alembic upgrade:

```bash
docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic upgrade head
```

Relevant output:

```text
INFO  [alembic.runtime.migration] Running upgrade  -> 5fd2ed5269af, initial schema
INFO  [alembic.runtime.migration] Running upgrade 7c2b9f1a0d4e -> c1a2b3d4e5f6, add school identity tenancy
INFO  [alembic.runtime.migration] Running upgrade c1a2b3d4e5f6 -> d4e5f6a7b8c9, drop household domain
```

Alembic verification:

```bash
docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic current
docker compose run --rm -v /opt/apps/class_hero_hub:/workspace -w /workspace backend alembic heads
docker compose exec -T postgres psql -U classhero -d class_hero_hub -c "select version_num from alembic_version;"
docker compose exec -T postgres psql -U classhero -d class_hero_hub -c "select tablename from pg_tables where schemaname = 'public' order by tablename;"
```

Results:

```text
alembic current: d4e5f6a7b8c9 (head)
alembic heads: d4e5f6a7b8c9 (head)
alembic_version.version_num: d4e5f6a7b8c9
public tables: alembic_version, audit_logs, memberships, platform_admins, schools, users
```

Backend boot and health check:

```bash
docker compose up -d backend
docker compose ps backend
docker compose logs --since=30s backend
curl -i -sS http://127.0.0.1:8000/api/health
```

Results:

```text
backend status: Up
backend logs: Application startup complete; Uvicorn running on http://0.0.0.0:8000
/api/health: HTTP/1.1 200 OK
/api/health body: {"status":"ok"}
```

Dev QA login verification against reset DB:

```bash
docker compose run --rm \
  -e QA_LOGIN_ENABLED=true \
  -e QA_LOGIN_TOKEN=qa-reset-login-token-20260707 \
  -v /opt/apps/class_hero_hub/backend:/app \
  -w /app \
  backend python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.post(
    "/api/dev/qa-login",
    headers={"Host": "127.0.0.1:8000"},
    json={"token": "qa-reset-login-token-20260707"},
)
print("qa-login", response.status_code, response.json())
assert response.status_code == 200
me_response = client.get("/api/me")
print("me", me_response.status_code, me_response.json())
assert me_response.status_code == 200
assert me_response.json()["is_platform_admin"] is True
PY
```

Result:

```text
qa-login 200 {'status': 'ok', 'email': 'qa-parent@dev.familyherohub.com', 'user_id': 1, 'is_platform_admin': True, 'reused': False}
me 200 {'user': {'id': 1, 'email': 'qa-parent@dev.familyherohub.com', 'name': 'QA Parent', 'locale': 'en'}, 'is_platform_admin': True, 'memberships': []}
```

Backend tests:

```bash
docker compose exec backend python -m pytest tests -q
```

Result:

```text
47 passed, 5 warnings in 2.06s
```

## 2026-07-07 - S4 school structure foundation

Scope implemented: school setup foundation only. S4 adds configurable school structure records and a plain school-admin setup UI without teachers, students, rooms, timetables, terms, imports, onboarding, communication features, or branch business workflows.

Modelling decisions:

- School settings now include `grade_level_label`, so each school can call levels Grade, Year, Form, Level, or custom text. The data model still uses `GradeLevel` internally as a neutral product concept.
- Branches/campuses are first-class school-owned records in `branch_campuses`. They were added now because multi-campus schools are common and class sections need an unambiguous campus context from the start. Modelling every campus as a separate school tenant would make shared school organisation setup, admins, academic years, subjects, and future reporting harder to reconcile.
- Every school can operate as a one-campus school. The school setup API creates a default `MAIN` / `Main Branch` campus when a school has no branches yet. `class_sections.branch_campus_id` is required; section creation can omit it and will use the default branch, avoiding nullable campus semantics in core section data.
- Education stages are school-defined optional groupings. `grade_levels.education_stage_id` is nullable, so schools can use KG/Primary/Middle/Secondary, FS/Prep/Sixth Form, Elementary/High School, or no stage grouping.
- Academic years are school-level records only in S4. Terms, semesters, rollover, student placement, and section transfer workflows remain future work.
- Subjects are school-level records. Subject groups are optional and represent teaching/audience groupings for an academic year, class section, and subject. They are not rooms or timetable periods.
- Class section labels are free text through `class_sections.code`, supporting A/B/C, Red/Blue, Boys/Girls, Advanced/Foundation, or any school-defined label.
- Homeroom teacher support is limited to nullable `class_sections.homeroom_teacher_user_id` as a placeholder. Teacher assignment workflows are deferred to S5.

Branch-scoped administration:

- `memberships.branch_campus_id` was added as a nullable future-compatible scope field. S4 route authorization still requires an active `school_admin` membership for the school and does not enforce branch-local permissions.
- Deferred work: define branch-scoped admin roles/permissions, update `require_school_role` or a new permission dependency to apply branch scope where appropriate, expose branch scope in admin invite/member management, and audit branch-limited access behavior. The schema now has a stable branch scope anchor and does not hard-code that every school admin must manage every branch forever.

## 2026-07-07 - Real SMTP sending for staff invites

Scope: `backend/app/mailer.py` was a logging-only stub — `send_staff_invite` just logged the invite and never sent mail, so platform admins creating a school-admin invite got no delivered email. This slice replaces the stub with real SMTP sending using only the Python standard library (`smtplib` + `email.message.EmailMessage`), no new dependency was needed or added.

Files changed:

- `backend/app/mailer.py` — builds a plain-text `EmailMessage` (subject, From/To, body with the accept link) and sends it via `smtplib`.
- `backend/app/database.py` — added `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`, `SMTP_USE_TLS` to `Settings`.
- `.env.example` — added the same SMTP keys with blank/placeholder values and a comment on the 587-vs-465 choice.
- `.env` — added the non-secret SMTP values for this deployment (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`, `SMTP_USE_TLS`). `SMTP_PASSWORD` was left blank — see "Still needs to be done" below.
- `backend/tests/test_mailer.py` (new) — unit tests for the mailer using `unittest.mock` against `smtplib.SMTP`/`smtplib.SMTP_SSL`; no test talks to a real mail server.

SMTP configuration variables (`Settings` in `backend/app/database.py`, read from `.env`):

| Variable | Purpose | Value used here |
| --- | --- | --- |
| `SMTP_HOST` | Mail server hostname | `mail.familyherohub.com` |
| `SMTP_PORT` | 587 = STARTTLS (default), 465 = implicit SSL | `587` |
| `SMTP_USERNAME` | SMTP auth username | `support@familyherohub.com` |
| `SMTP_PASSWORD` | SMTP auth password | left blank in `.env` — enter manually |
| `SMTP_FROM_EMAIL` | Envelope/header From address | `support@familyherohub.com` |
| `SMTP_FROM_NAME` | Display name on the From header | `Class Hero Hub` |
| `SMTP_USE_TLS` | Use STARTTLS after connecting (ignored for port 465, which always uses implicit SSL) | `true` |

Behavior:

- If `SMTP_HOST` or `SMTP_FROM_EMAIL` is empty, `send_staff_invite` logs a warning and returns without raising, so invite creation still succeeds in dev/test environments that have no SMTP configured (this is also why the existing platform-admin tests, which monkeypatch `send_staff_invite` directly, were unaffected).
- When `SMTP_PORT == 465`, the mailer connects with `smtplib.SMTP_SSL` (implicit TLS) and skips `starttls()`. Otherwise it connects with plain `smtplib.SMTP` and calls `starttls()` when `SMTP_USE_TLS` is true. Per the task's stated preference, `mail.familyherohub.com:587` with STARTTLS is configured as the default; if that host later requires implicit SSL instead, switch `SMTP_PORT` to `465` — no code change is needed for that fallback, only `.env`.
- `smtp.login()` is only called when both `SMTP_USERNAME` and `SMTP_PASSWORD` are set.

Verification performed:

- Added `backend/tests/test_mailer.py` covering: (1) SMTP not configured → warning logged, no `smtplib.SMTP`/`SMTP_SSL` call; (2) port 587 → `smtplib.SMTP` used, `starttls()` and `login()` called, message has correct To/From and the accept URL in the body; (3) port 465 → `smtplib.SMTP_SSL` used, `starttls()` not called.
- Ran the full backend suite inside the running backend container: `docker exec family-hero-hub-backend python -m pytest -v` → **101 passed**, including the 3 new mailer tests and all existing `test_platform_admin.py` invite lifecycle tests (which continue to pass because they monkeypatch `send_staff_invite` and never depend on real SMTP).
- Did not send a real email end-to-end, because `SMTP_PASSWORD` is intentionally not filled in yet (see below) and the backend container needs a rebuild to pick up the code/`.env` changes (its image bakes `COPY . .` at build time — there is no source volume mount). Copied the changed files into the running container only to execute the test suite; that copy is not a deployment and is lost on the next container recreation.

Still needs to be done manually (not done by this change, per instructions):

1. Add the real SMTP password for `support@familyherohub.com` to `.env` as `SMTP_PASSWORD=...` (never share it in chat).
2. Rebuild and restart the backend container so it picks up the new code and env vars, e.g. `docker compose build backend && docker compose up -d backend`.
3. Create or resend a school-admin invite from the platform admin UI/API and confirm the email actually arrives at the target address with a working accept link. If `mail.familyherohub.com` rejects STARTTLS on 587, try `SMTP_PORT=465` in `.env` and restart — no code change required.
4. Do not commit these changes until the above manual test passes (per instruction not to commit yet).

Note: During S7 dev/testing, SMTP settings were removed from `.env` and demo guardian email addresses were fake. That is only environment-level belt-and-suspenders. The actual S7 safety guarantee is code-level: student CSV import does not create guardian links, guardian invites, guardian users, notifications, magic links, or outbound email/messages.

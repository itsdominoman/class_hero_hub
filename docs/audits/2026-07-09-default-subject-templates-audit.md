# Audit — Default Subject Templates (S6.8 / S7-prep)

**Date:** 2026-07-09
**Auditor:** fresh-eyes review (Claude, read-only)
**Scope:** uncommitted working-tree slice adding default subject templates by education
stage / grade-year level, with preview + idempotent apply into an academic year.
**Method:** read the code and migration, verified every helper the routes depend on, ran
the full backend suite, frontend `check` / `check:i18n` / `build`, and `perf_check.py`.
Implementation summary and log were **not** trusted — findings below come from reading code
and running checks.

---

## Executive verdict

**Safe to manually test.** No blocker or high-severity issue found. The data model,
tenancy, lifecycle, dedupe, and idempotency all behave as specified, and the whole test +
build + perf matrix is green. The findings below are medium-and-below refinements; none
block Dom's manual QA, and none require a fix before he tests.

Recommendation: **let Dom test, then commit as-is** (optionally folding in the low-effort
polish items). Nothing here warrants revert/rework.

---

## Checks run (exact results)

| Check | Command | Result |
|---|---|---|
| Slice tests | `docker compose exec -T backend python -m pytest tests/test_default_subject_templates.py -q` | **16 passed** |
| Full backend suite | `docker compose exec -T backend python -m pytest tests -q` | **170 passed**, 7 warnings |
| Type/Svelte check | `npm run check` | **0 errors, 0 warnings** |
| i18n parity | `npm run check:i18n` | **OK: 402 keys in both en and ar** |
| i18n usage (grep) | grepped keys the new tab uses | All present in **both** en+ar: new `school.defaults.*` / `school.tabs.defaults` / `school.validation.stageRequired`, and reused `school.advanced`, `school.sortOrderOptional`, `common.loading`, `school.restored` |
| Build | `npm run build` | **✓ built** (adapter-static wrote `build/`) |
| Perf | `backend/scripts/perf_check.py` | Only `/api/school/students` over guideline (**3.556s**) — pre-existing, out of scope, **not worsened** |
| **Migration up/down (Postgres)** | `alembic downgrade -1` then `alembic upgrade head` against the dev Postgres DB | **Clean both ways.** Downgrade drops the table (verified gone); upgrade recreates it with all 3 indexes, the unique constraint, the XOR check constraint, 5 FKs, and correct server-defaults (`'active'`, `0`, `now()`) and nullability. DB left at head. |

> Note on the test suite: it builds its schema via `Base.metadata.create_all` on
> `sqlite://`, so "170 passed" validates the **model**, not the **migration**. The migration
> was therefore executed separately against Postgres (last row above) — the environment Dom's
> manual QA actually runs on — and the recreated Postgres schema matches the model exactly
> (XOR `CHECK`, `server_default` values, and nullable-column uniqueness all as intended).

Perf detail: the school page-load sequence is 4.2s, dominated entirely by the known
`/api/school/students` roster resolver. Every other endpoint (settings, checklist,
branches, stages, years, grade-levels, sections, subjects, 214 subject-groups, teachers,
assignments) is 30–110ms. The new `default-subject-templates` list is a light `_list_rows`-style
batched query; the new `preview`/`apply` planners are covered by a query-count regression
test (below) rather than by `perf_check.py`.

---

## What the slice gets right (verified, not assumed)

- **Tenancy is airtight.** Every FK the planner touches is school-scoped: academic year,
  branch, stage, grade validated via `_ensure_owned` (400 on wrong-school); sections,
  templates, and existing subject-groups all filtered by `school_id`; the stage→grade
  subquery is `WHERE school_id = …`. Cross-school preview/apply returns 400 and leaks
  nothing (`test_cross_school_isolation_on_preview_and_apply`).
- **All six endpoints are `require_school_role("school_admin")`.** Teacher → 403,
  wrong-school → 404/400 (tested).
- **XOR scope** enforced in the DB (`ck_…_exactly_one_scope`) *and* re-checked in the API
  (`_validate_template_scope`) — belt and suspenders. Tested (neither / both → 400).
- **NULL natural-key gotcha handled correctly.** Because SQL treats two NULL grade columns
  as distinct, the composite unique constraint cannot dedupe stage templates against each
  other; `_find_default_subject_template` does the `.is_(None)`-aware lookup before
  insert/restore. Explicitly regression-tested on a stage template.
- **Lifecycle matches the existing seven setup entities:** archive = soft delete (`status =
  "archived"`), hidden from default list, `?include_archived=true` reveals it, recreate
  restores the archived row in place (`restored: true`, original id). No second lifecycle
  system was invented.
- **Preview uses active templates only** (`status == "active"` filter in the planner).
- **Apply targets an academic year, never binds templates to one** — templates carry no
  year; the year is a per-request argument.
- **Stage + grade dedupe** to one group per section (stage first, grade adds only new
  subjects); generated groups are section-specific with `enrolment_policy =
  "default_for_section"` and `grade_level_id = None`. Tested.
- **Apply is non-destructive:** skips existing active/inactive matching groups, restores
  archived matching groups, and `staff_assignments` / `enrolments` row counts are asserted
  unchanged.
- **Idempotency & concurrency:** second run reports every row as `skipped_existing`; a
  concurrent-insert `IntegrityError` is caught and returned as 409 with a re-run message.
- **No N+1** in the planner or list payloads — subjects/stages/grades/existing-groups are
  each fetched once with `IN(...)`. A `count_queries()` regression test asserts the query
  count does **not** scale with section count (8 extra sections add < 10 queries).
- **Frontend is light:** templates load inside the existing fixed `loadAll()` `Promise.all`
  (no per-row fan-out); the Defaults tab never triggers the heavy student fetch
  (`ensureStudentsLoaded` is gated to the Students tab / roster picker only).

---

## Findings by severity

### Blocker
None.

### High
None.

### Medium

**M1 — Apply dedupes by generated code, so a same-subject group created under a
non-standard code is not detected and a second group for that subject is created.**
`file:` `backend/app/routes/school.py` (`_plan_default_subject_template_application`, the
`existing = next(... g.code == code ...)` match).
The planner detects an existing group only when its `code` equals the deterministic
`_subject_group_defaults()` code (`{level}{section}-{subject}`). A school that already
created an English group for a section under a custom code (e.g. `MYENG`) will get a
**second** English group (`Y1RED-ENG`) when it applies the template — two default groups
for the same subject in one section.
*Why it matters:* for real schools that set up subject groups by hand before adopting
templates, apply can silently create subject-level duplicates.
*Mitigating context:* this is **identical to the existing** `bulk_create_section_subject_groups`
behaviour (both key on the generated code via the natural key), so it is consistent with
the shipped product, not a regression this slice introduces. The demo data uses the same
deterministic codes, so the demo is unaffected.
*Suggested fix (optional, product decision):* if same-subject-per-section should be unique
regardless of code, match existing groups on `(class_section_id, subject_id)` and surface a
`skipped` with a "different code already exists" reason instead of creating. Otherwise,
document the code-based dedupe contract in the apply help text so admins know custom-coded
groups aren't recognised. Recommend leaving as-is for now (matches existing workflow) and
noting it.

### Low

**L1 — Restore-on-recreate ignores the requested `status`.**
`create_default_subject_template` restore branch forces `existing.status = "active"` and
does not honour a submitted `status = "inactive"` (it does apply `sort_order`). The generic
`_restore_row` used by other entities respects the submitted status (only forcing active if
still archived). Minor divergence; unlikely to bite (recreate-as-inactive is a rare intent).

**L2 — `PUT` into a slot occupied by an *archived* template returns 409 rather than
restoring.** `update_default_subject_template`'s duplicate check treats any row sharing the
natural key (including archived) as a conflict, whereas `create` would restore it. Slightly
inconsistent with the create path; edge case, low impact.

**L3 — Inactive templates excluded from apply is correct but untested.** The planner filters
`status == "active"`, so inactive templates are (correctly) ignored — but no test asserts
this. Cheap to add.

**L4 — Archived-subject → `failed` branch untested.** The planner marks a plan row `fail`
("Subject is archived") when a template's subject was later archived. Correct behaviour, no
test. (The "Subject not found" branch is effectively dead — subject ids derive from
same-school templates and are always fetched — so no test needed there.)

**L5 — `BACKEND_PERFORMANCE.md` audit table not updated for the two new POST endpoints.**
The doc's stated purpose is "so the next slice doesn't have to re-derive it," but
`preview`/`apply` aren't listed. Their query-shape is protected by the `count_queries()`
test; a one-row table entry would keep the doc complete.

**L6 — Restore of an archived subject group silently flips its `enrolment_policy` to
`default_for_section`.** In apply's `restore` branch, an archived group that matches the
generated code is reactivated *and* its `enrolment_policy` is overwritten to
`default_for_section` (plus `name`). If that archived group had been an `explicit_only`
group, its policy changes on restore. This is arguably the template asserting its intent and
matches the "restore archived matching group" requirement, but it is a quiet mutation worth
being aware of. Note only.

### Polish

**P1 — Apply has no confirmation and does not require a preview first.** The Apply button is
enabled as soon as an academic year is selected (validated), sitting next to Preview.
Because apply is idempotent and non-destructive this is low-risk, but a "preview recommended"
nudge or a confirm on first apply would reduce accidental early applies.

**P2 — Template list is fetched on every school-page load** (part of the fixed `loadAll`
`Promise.all`), even when the Defaults tab is never opened. It is a tiny list query, so this
is fine; only noting it against the slice's own "students is lazy" philosophy if the setup
lists are ever trimmed further.

---

## Test coverage vs. required checklist

| Required coverage | Present? |
|---|---|
| create / list / update / archive | ✅ `test_school_admin_can_crud_templates` |
| wrong role | ✅ `test_wrong_role_is_blocked` (403) |
| wrong school | ✅ `test_wrong_school_is_blocked` (404 update / 400 create) |
| duplicate active template rejected | ✅ `test_active_and_inactive_duplicate_stage_template_rejected` (409, incl. inactive) |
| archived restore | ✅ `test_archived_template_recreate_restores_in_place` |
| XOR scope validation | ✅ `test_exactly_one_scope_required` |
| same-school validation for refs | ✅ `test_template_refs_must_belong_to_same_school` |
| stage preview | ✅ (covered within dedupe/filters tests) |
| grade preview | ✅ `test_preview_resolves_stage_and_grade_templates_and_dedupes` |
| stage+grade dedupe | ✅ same |
| filters (branch/stage/grade) | ✅ `test_optional_branch_stage_grade_filters_narrow_sections` |
| apply creates `default_for_section` groups | ✅ `test_apply_creates_section_specific_default_for_section_groups` |
| idempotency | ✅ `test_apply_is_idempotent_on_second_run` (2nd run only — see gap) |
| skip existing groups | ✅ `test_apply_skips_existing_active_and_inactive_matching_groups` |
| restore archived groups | ✅ `test_apply_restores_archived_matching_group` |
| no teacher-assignment changes | ✅ `test_apply_does_not_touch_teacher_assignments_or_enrolments` |
| no enrolment changes | ✅ same |
| cross-school isolation | ✅ `test_cross_school_isolation_on_preview_and_apply` |
| query-shape / perf protection | ✅ `test_preview_and_apply_query_count_does_not_scale_with_section_count` |

**Coverage gaps (all minor):**
- Idempotency asserted only on the **2nd** run, not the 3rd/4th. Logic is deterministic
  (post-create groups are active → matched → `skipped`; post-restore groups are active →
  `skipped`), so a 3rd run is guaranteed to behave like the 2nd — but the audit brief asked
  specifically to confirm beyond the second run. Adding a 3rd `_apply` assertion would close
  it cheaply.
- No test that an **inactive template** is excluded from preview/apply (L3).
- No test for the **archived-subject → failed** plan row (L4).

Nothing is *claimed* in the implementation log that the tests don't actually assert.

---

## Manual QA checklist for Dom

1. **Create templates:** Defaults tab → add ENG at *stage* Primary, MATH at *grade* Year 1.
   Both appear in the list with the right scope label.
2. **XOR guard:** try to save with neither scope, then rely on the toggle — confirm the
   stage/grade toggle blanks the other field and you can't submit an empty scope.
3. **Duplicate:** re-add ENG at stage Primary → expect a clear "already exists" error.
4. **Archive + restore:** archive ENG (trash icon) → it disappears from the list; re-add the
   same ENG stage template → it comes back (the "restored" notice shows).
5. **Preview:** pick an academic year with class sections → Preview shows a per-section /
   per-subject list and a "would create / restore / already exist / failed" summary. Confirm
   ENG appears once per section even though it's templated at both stage and grade.
6. **Filters:** narrow Preview by branch, then by stage, then by grade — confirm the section
   list shrinks accordingly and the empty-state message shows when nothing matches.
7. **Apply, then apply again:** Apply → groups are created (`default_for_section`). Open the
   Subject groups tab and confirm they're there with the right names/codes. Apply a second
   time → everything reports "skipped / already exist," no duplicates.
8. **Demo-data idempotency:** run apply against the seeded United International School and
   confirm its existing default groups (e.g. `KG1A-ENG`) report as already existing, not
   duplicated (this exercises M1's happy path where codes match).
9. **Arabic:** switch locale to AR and confirm the Defaults tab, help text, and
   preview/apply summaries render (RTL, no missing-key placeholders).
10. **No side effects:** confirm applying did not create teacher assignments or change any
    student's enrolments.

---

## Final recommendation

**Commit as-is after Dom's manual QA.** The slice is correct, well-tested, tenancy-safe,
idempotent, and performance-conscious; the full check matrix is green. The medium finding
(M1) is a pre-existing, product-level dedupe contract shared with the current bulk-section
workflow, not a regression — flag it to Dom as a known behaviour rather than a fix-first
blocker. The low/polish items (status-on-restore parity L1, 3rd-run idempotency + inactive/
archived-subject tests L3/L4, and the `BACKEND_PERFORMANCE.md` table entry L5) are worth a
quick follow-up but do not gate this commit.

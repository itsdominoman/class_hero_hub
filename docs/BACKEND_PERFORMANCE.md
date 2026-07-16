# Backend performance: expectations and anti-patterns

This exists because two N+1 bugs shipped the same morning (2026-07-09): the school admin
page fired one HTTP request per teacher to fetch assignments, and `GET /api/school/students`
called the subject-group roster resolver once per student — both invisible at small scale,
both catastrophic once the demo had 502 students and 214 default-policy subject groups.
This doc records the rule that would have caught them, and the current state of each
audited endpoint so the next slice doesn't have to re-derive it.

## The rule

**No endpoint that returns a list may call a per-row helper that hits the database.**

If a function takes one row and does a `db.query(...)` inside it, it must never be called
inside a loop over many rows from a list endpoint. Two fixes, both used throughout this
codebase now:

1. **Batch the lookups.** Collect every foreign key referenced across all rows into a
   `set`, fetch the related rows once with `.filter(Model.id.in_(ids))`, build an
   `{id: row}` dict, then build each item's payload from the dict. Fixed cost regardless
   of row count.
2. **Make the single-row version delegate to the bulk version**, not the other way round
   (see `rosters.current_subject_groups_for_student` → `bulk_subject_groups_for_students`,
   or `school._assignment_payload` → `_assignment_payloads_bulk`). This keeps one
   implementation instead of two copies drifting apart.

Frontend mirror of the same rule: **no page may fire one request per teacher/student/subject
row.** If a page needs data for every row in a list, add a batch backend endpoint
(`GET /api/school/teachers/assignments` is the template) rather than fanning out
`Promise.all(rows.map(row => api.get(...)))`.

## Endpoint audit (2026-07-09)

| Endpoint | Before | After |
|---|---|---|
| `GET /api/school/students` | Called `current_subject_groups_for_student` per student, then an interim bulk implementation still issued 2–3 queries per group. At the 2026-07-16 demo scale this was 779 route-handler queries and 2.7–3.3s internally. | `resolve_rosters_for_students` loads groups, active class enrolments, and explicit member/exclusion rows once, then derives defaults in memory. **5 route-handler queries and 174–329ms internally** for 502 students / 258 groups before deployment; see the dedicated roster audit. |
| `GET /api/teach/dashboard` | `_assignment_card` did up to 6 single-row queries per assignment (class_section, branch, year, grade_level, subject_group, subject). Bounded by one teacher's own assignment count, so low risk today, but a real violation of the rule. | `_assignment_cards` batches all referenced entities via `IN(...)` once per request regardless of assignment count. |
| `GET /api/school/teachers/assignments` (batch) | Fixed the *frontend* fan-out (67 concurrent requests → 1), but `_assignment_payload` still ran 2 queries per assignment row inside the batch endpoint — the N+1 moved server-side instead of disappearing. | `_assignment_payloads_bulk` batches class_section/subject_group lookups once per request. |
| `GET /api/school/teachers/{id}/assignments` (single teacher) | Same `_assignment_payload` per-row pattern; bounded by one teacher's assignment count. | Now shares `_assignment_payloads_bulk`. |
| `GET /api/school/class-sections/{id}/roster` (class roster setup) | Already batched subject/assignment lookups, but `_teacher_ref_payload` still ran 2 queries per subject group in the section for the assigned-teacher lookup. Bounded by subject groups per section (~9), low risk today. | `_teacher_ref_payloads_bulk` batches membership/user lookups once per request. |
| `GET /api/school/teachers` | Single joined query + one aggregate query for assignment counts + one query for pending invites. Clean already. | No change. |
| `GET /api/school/class-sections`, `/subject-groups`, `/subjects`, `/branches`, etc. | `_list_rows` — one query, pure in-memory serialization. Clean already. | No change. |
| `GET /api/school/setup-checklist` | 7 independent `COUNT(*)` queries. Fixed, small number regardless of school size — acceptable. | No change. |
| `GET /api/me`, `/api/me/v2` | One joined query for memberships, one for platform-admin check. Bounded by a single user's own membership count, never large. Clean already. | No change. |
| `GET /api/teach/schools/{id}/sections/{id}/roster`, `/subject-groups/{id}/roster` | Resolve one target's roster via `rosters.roster_payload` — a small constant number of queries per call. Correct for a single-target request; each teacher-triggered "view roster" click is one legitimate request, not a fan-out. | No change. |
| Frontend `/school` page | Single `Promise.all` of 11 fixed calls (not per-row — fine), but always included `GET /api/school/students`, the heaviest call, even when the Students tab was never opened. `/school` is tabbed (`{#if activeTab === ...}`), so most visits paid for data they never saw. | `students` is now lazy: fetched once, on first need, triggered by opening the Students tab or opening a subject-group roster's "add student" picker (`ensureStudentsLoaded()`), not on every page load. `loadAll()` keeps it fresh afterwards if already loaded, so mutations elsewhere still sync it. |
| Frontend `/school` Teachers panel (historical) | One `GET /teachers/{id}/assignments` per teacher on page load — 67 concurrent requests with 67 teachers, the incident that started this audit. | Replaced with the single batch endpoint above. |

### `GET /api/school/students`: set-based resolution completed 2026-07-16

The dedicated roster optimisation replaced the interim per-group loop. At the current
demo scale (502 students, 258 non-archived subject groups), the whole-school helper now
uses three queries rather than 775 and completes in 132–153ms warm internally. The
Students route adds the student-list query and caller context for five handler queries
total. Class-filtered and one-student callers pass their selected student IDs so they do
not hydrate unrelated enrolments.

`backend/tests/test_roster_resolution.py` asserts explicit/default/exclusion semantics,
school/year/branch/archive scope, deterministic output, and a query count that stays
constant when another 20 groups are added. The detailed evidence and rollback procedure
are in `docs/audit/2026-07-chh-roster-query-optimisation.md`.

The endpoint remains lazy on the frontend and runs when the Students tab or a student
picker actually needs it.

## Indexes added (migration `e1f2a3b4c5d6`)

Composite indexes were missing for the exact `WHERE` clauses these endpoints (and the
underlying roster resolver) run constantly. All additive, no behavior change:

- `enrolments(school_id, class_section_id, kind)` and `enrolments(school_id, subject_group_id, kind)`
  — the roster-resolution hot path (`_section_roster_rows`, `_default_group_rows`, `_explicit_group_rows`).
- `staff_assignments(school_id, membership_id)` — teacher-assignment batch lookups.
- `memberships(school_id, role, status)` — `list_teachers`, admin/teacher-role filtering.
- `subject_groups(school_id, status)` — the group scan in `bulk_subject_groups_for_students`.
- `students(school_id, status)` — the single most repeated filter in the codebase.

Not added: trigram/full-text indexes for the student search (`ILIKE` on name/external_ref).
Not justified at current data volume; add if search becomes slow at real scale.

## Regression tests

`backend/tests/test_roster_resolution.py`, `backend/tests/test_students_enrolments.py`, and `backend/tests/test_staff_assignments.py`
include query-shape regression tests: they monkeypatch the per-group resolver or count raw
SQL statements via a SQLAlchemy `before_cursor_execute` listener, and assert the count stays
roughly flat as the number of students/assignments/subject-groups grows, instead of scaling
with row count. Follow that pattern (`count_queries()` context manager in
`test_staff_assignments.py`) for any new list endpoint.

## Dev perf script

`backend/scripts/perf_check.py` times every audited endpoint against whatever data currently
exists in the target school and flags anything over 1s. Run it after any change that
touches a list/dashboard endpoint:

```
docker compose run --rm --no-deps -v $(pwd):/repo -w /repo backend python backend/scripts/perf_check.py
```

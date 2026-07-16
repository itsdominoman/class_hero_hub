# CHH roster query optimisation audit

**Date:** 2026-07-16
**Environment:** CHH development
**Data changes:** none
**Frontend/FHH changes:** none

## Outcome

The shared subject-group resolver performed three SQL queries for every
non-archived group: exclusions, policy-default members, and explicit members.
With 258 groups, one whole-school resolution executed 775 queries. The same
whole-school work was also used by one-student admin context and guardian
announcement audience resolution.

The replacement uses three set-based queries regardless of group count:

1. relevant non-archived subject groups;
2. active students' open class enrolments joined to active class sections; and
3. open explicit member/exclusion enrolments for the selected groups.

It combines section defaults, grade/year defaults, explicit membership, and
exclusions in deterministic in-memory maps. On the live development data, the
whole-school helper fell from 775 queries and 2.9–3.6s to three queries and
132–153ms warm. The Students route fell from 779 handler queries to five.

## Method and privacy

Profiling used SQLAlchemy cursor listeners around read-only service/route calls
and three low-volume HTTP GET samples for routes without path identifiers. It
recorded only anonymous caller labels, counts, timings, query-shape labels, and
response hashes. No name, email, token, media identifier, route identifier, or
payload was logged. No seed/import/apply route was invoked and no database row
was changed.

Cold means the first measured invocation in the diagnostic process. Warm means
the two immediately following invocations. These are development-server
measurements, not load-test results.

## Caller inventory

| Caller | Endpoint/use case | Input scale measured | Before queries | Before duration | User-facing frequency |
|---|---|---:|---:|---:|---|
| School Students list | `GET /api/school/students` | 502 students / 258 groups | 779 handler queries | 2.72–3.34s internal warm; 3.37–4.10s HTTP | Frequent when Students tab/search is used |
| Class-filtered Students list | Same endpoint with one section filter | 24 students / 258 groups | 780 | 2.84–3.23s warm | Frequent admin filter |
| Single student context | Student detail/create/update response helper | 1 student / 258 groups | 775 in group helper | 3.18–3.36s | Moderate admin row actions |
| Guardian announcement audience | Guardian list/detail/download authorisation | 2 linked students / 1 school / 258 groups | 778 including caller lookup | 3.11–5.83s internal; 2.71–3.32s HTTP warm | High parent-feed frequency |
| Whole-school group reverse map | `bulk_subject_groups_for_students` | 502 students / 258 groups / 4,629 edges | 775 | 2.88–3.58s | Shared service workload |
| One-grade scope | Grade's 37 current students | 37 students / 258 groups | 775 through old whole-school helper | 2.64–2.92s | No direct route; representative scoped workload |
| Admin class roster | Section students/setup roster | 24 students | 2 | 9.5–24.7ms | Frequent per selected class |
| Admin/teacher subject-group roster | One group | 23 students | 5 | 21.5–52.0ms | Frequent per selected group |
| Teacher dashboard | Assigned-class cards | Teacher with 10 active group assignments | 9 | 20.5–62.1ms | High; no roster expansion |
| Teacher assignment detail | One assigned class/group roster | One group from the 10 assignments | 5 roster queries | 26.8–34.3ms | High per opened assignment |
| Behaviour award validation | One selected class/group roster | 23 students | 5 roster queries | 15.3–22.4ms | High; mutation was not invoked |
| Behaviour reporting | Overview/event-time roster attribution | Existing event set | 3 | 37.2–73.1ms | Admin reporting; separate set-based query |
| Protected FHH integration | One linked student's scope | 1 section / 8 groups | 3 scope queries | 9.4–30.2ms | High for linked dashboard/media |
| Imports/setup planners | Student imports and default-subject setup | Existing code inspection | No shared roster call | Not applicable | Mutating flows deliberately not profiled |
| Background/demo helpers | Production service search | Existing code inspection | No shared roster call | Not applicable | Development-only or background use |

The only direct whole-school expansion callers were the school Students path and
guardian announcement audience. The single-student wrapper was a hidden
whole-school caller. Teacher/admin target rosters and behaviour validation were
already bounded to one target. Reports use their own event-time set-based query.

## Demo-data scale

The representative school contained:

- 502 active/visible students;
- 258 non-archived subject groups;
- 258 `default_for_section` groups;
- zero `default_for_grade` groups;
- zero explicit subject-group memberships and zero exclusions;
- 4,629 resolved student/group edges;
- 24 students in the largest measured class;
- 37 students in the largest measured grade/year;
- 10 active subject-group assignments for the measured teacher;
- two active links for the measured guardian.

No school in the development database had an explicit subject-group membership
or exclusion row. Those branches were therefore validated with isolated truth-
table tests rather than by mutating demo data.

## Existing membership semantics

A student is a current member when any applicable inclusion path exists:

- an open explicit `kind=member` subject-group enrolment;
- an open class enrolment in the exact active section for
  `default_for_section`; or
- an open class enrolment in any active section with the same grade level and
  academic year for `default_for_grade`.

The exact rules preserved or tightened are:

- an open explicit exclusion for the group is applied last and wins over both
  explicit and default inclusion;
- explicit inclusion wins over a duplicate default path for source metadata;
- enrolment intervals are `valid_from <= today` and exclusive
  `valid_to > today`;
- students must be active and belong to the requested school;
- enrolments, groups, and class sections must belong to the requested school;
- archived groups do not produce current membership;
- inactive but non-archived groups remain visible/resolvable, matching the
  existing API lifecycle contract; new enrolments into them remain blocked;
- default membership requires an active class section;
- section defaults require the group's section and academic year to match;
- grade defaults span branches by design but require the same grade and
  academic year;
- explicit membership is not restricted to a student's homeroom section,
  preserving cross-section/elective groups;
- closed enrolments and inactive/archived students do not appear;
- duplicate paths produce one student/group result;
- students sort by last name, first name, then ID; groups sort by sort order,
  then ID.

There is no global `academic_year.is_current` filter in the resolver. Current
membership is driven by open enrolments and the group/section academic-year
match, preserving historical-year workflows that deliberately keep an open
row.

## Before profiling and query proof

| Scope | Cold | Warm runs | Queries | Returned scale |
|---|---:|---:|---:|---:|
| One student | 3,357ms | 3,180–3,299ms | 775 | 8 groups |
| One class roster | 24.7ms | 9.5–10.5ms | 2 | 24 students |
| One grade via old bulk path | 2,874ms | 2,644–2,917ms | 775 | 37 students / 370 edges |
| Whole-school helper | 3,584ms | 2,879–3,171ms | 775 | 502 students / 4,629 edges |
| Students handler | 3,337ms | 2,721–3,060ms | 779 | 502 students |
| Class-filtered Students handler | 3,433ms | 2,842–3,226ms | 780 | 24 students |
| Guardian audience | 3,107ms | 3,156–5,831ms | 778 | 2 linked students |
| Subject-group target | 52.0ms | 21.5–32.8ms | 5 | 23 students |

For each of the 258 groups, `subject_group_members` ran an exclusion query, a
section-default query, and an explicit-member query: 774 membership statements
plus one group statement. No lazy ORM relationship access was involved; the
N+1 was an explicit function loop.

`EXPLAIN (ANALYZE, BUFFERS)` disproved a missing-index root cause:

- a representative explicit-member query used
  `ix_enrolments_school_group_kind` and executed in 0.135ms;
- a representative section-default query used
  `ix_enrolments_school_section_kind` and executed in 0.447ms;
- the 258-row group scan executed in 0.418ms;
- the replacement set-based class query used the section/student indexes and
  returned 502 rows in 1.934ms;
- the replacement explicit/exclusion query returned the empty live set in
  0.216ms.

The bottleneck was accumulated SQL round trips and repeated ORM/payload work,
not a slow individual query, lock wait, or missing index. No index or migration
was justified.

## Implementation

`backend/app/rosters.py` now owns `resolve_rosters_for_students`, returning one
`RosterResolution` with:

- ordered active class sections by student;
- ordered subject-group refs by student;
- ordered students by group; and
- ordered excluded students by group.

The resolver accepts optional `student_ids` and optional caller-owned `groups`.
Whole-school calls use three queries. One-target subject-group calls reuse the
already loaded group and restrict the class query to the group's section or
grade/year context. Empty student scopes return without querying.

Caller changes:

- Students list/detail passes only the rows being returned and reuses the
  resolver's loaded class sections;
- guardian announcements groups link students by school and resolves only
  those students;
- protected FHH integration resolves only its linked student through the same
  semantics;
- teacher/admin target rosters and behaviour continue to request one target;
- reporting and import/setup code remains unchanged because it did not use the
  shared expansion.

## Before/after performance

| Caller/scope | Before queries | After queries | Before cold / warm | After cold / warm | Rows/students/groups |
|---|---:|---:|---:|---:|---:|
| One student | 775 | 3 | 3,357 / 3,180–3,299ms | 45.2 / 26.4–34.6ms | 1 / 8 groups |
| One class roster | 2 | 2 | 24.7 / 9.5–10.5ms | 12.4 / 7.1–12.5ms | 24 students |
| One grade | 775 | 3 | 2,874 / 2,644–2,917ms | 101.3 / 92.8–97.7ms | 37 students / 370 edges |
| Whole-school helper | 775 | 3 | 3,584 / 2,879–3,171ms | 302.2 / 132.1–152.8ms | 502 / 258 / 4,629 edges |
| Students handler | 779 | 5 | 3,337 / 2,721–3,060ms | 218.6 / 173.9–328.7ms | 502 / 258 |
| Class-filtered Students | 780 | 6 | 3,433 / 2,842–3,226ms | 78.4 / 49.2–71.3ms | 24 / 258 |
| Guardian audience | 778 | 5 including caller lookup | 3,107 / 3,156–5,831ms | 42.9 / 45.0–48.4ms | 2 linked students / 258 groups |
| Subject-group roster | 5 | 4 | 52.0 / 21.5–32.8ms | 49.1 / 21.7–26.7ms | 23 students |
| Teacher group roster | 5 | 4 | 34.3 / 26.8–27.0ms | 18.5 / 19.5–24.6ms | 23 students / 10 assignments available |
| Behaviour target roster | 5 | 4 | 22.4 / 15.3–19.0ms | 20.9 / 27.6–32.1ms | 23 students |
| Teacher dashboard | 9 | 9 | 62.1 / 20.5–39.6ms | 51.6 / 22.8–32.1ms | 10 assignments; no expansion |
| Reporting overview | 3 | 3 | 73.1 / 37.2–43.0ms | 77.6 / 33.2–38.7ms | Separate report query |
| Protected FHH scope | 3 | 3 | 30.2 / 9.4–12.3ms | 45.9 / 26.0–27.2ms | 1 student / 8 groups |

The protected scope remains three queries and well below the previous media
path's multi-second failure. Its small CPU/ORM increase comes from using the
shared fully shaped resolver; the end-to-end media check is repeated after
deployment.

## Correctness evidence

Canonical SHA-256 hashes matched between the deployed pre-change code and the
new code for all five sampled outputs:

- 502-row Students response;
- class roster;
- subject-group roster;
- guardian audience sets; and
- protected FHH section/group scope.

Truth-table coverage includes explicit-only, section default, grade default,
section/grade exclusions, explicit-over-default deduplication, moved section,
archived group, closed/inactive enrolment context, cross-school isolation, no
group, mixed branch/year, deterministic ordering, and no duplicate results.

## Tests

- Focused roster/integration tests: 14 passed.
- Relevant students, assignments, imports, announcements, behaviour,
  reporting, and FHH integration suite: 140 passed.
- Post-deployment roster/students/announcements/behaviour/reporting/FHH suite:
  91 passed.
- Full backend suite: 358 passed; one unrelated existing demo-seeder test
  failed because its monkeypatched `persist_task` stub does not accept the
  already-present `seed_namespace` keyword. Neither file is part of this
  change.
- Query-count tests add 20 groups and assert no increase for whole-school,
  one-student, teacher-target, and guardian-audience resolution.
- Python compile check and `git diff --check`: passed.

## Deployment and rollback

The CHH development backend was rebuilt and recreated with:

```text
docker compose build backend
docker compose up -d --no-deps backend
```

Only `family-hero-hub-backend` is rebuilt/recreated. PostgreSQL and both CHH/FHH
frontends remained untouched. The prior CHH backend image ID was
`sha256:92cadee11199...`; the deployed image ID is
`sha256:a1493a197864...`.

Post-deployment validation:

| Check | Result |
|---|---|
| CHH `/api/health` | 200 |
| School Students HTTP | 200; 502 rows; 842ms cold, 708–980ms warm |
| Guardian announcements HTTP | 200; 9 rows; 132ms cold, 92–111ms warm |
| Teacher dashboard HTTP | 200; 62ms cold, 40–45ms warm |
| Reporting overview HTTP | 200; 89ms cold, 86–88ms warm |
| Authenticated roster route contracts | School-admin class, school-admin group, and teacher group all 200; 14-student sample |
| Class roster internal live route logic | 2 queries, 21ms, 24 students |
| Teacher subject-group roster internal live route logic | 4 queries, 41ms, 14 students |
| Protected FHH scope | 3 queries; 55ms cold, 27–39ms warm |
| FHH protected photo through existing endpoint | 200; 201ms cold, 75–82ms warm; byte count matched; private/no-store; image content type |
| Media access-log privacy | 3 redacted lines at each tier; zero raw numeric media paths; zero credential header markers |

The behaviour POST was not invoked because it would create a behaviour event,
contrary to the no-data-mutation requirement. Its assignment/target roster
validation and the read-only reporting flow passed focused tests and live
read-only checks. The existing QA4 APK path/schema is unchanged; the same FHH
server endpoint it uses returned the protected photo successfully. No physical
APK interaction was performed in this server-side task.

Rollback requires no database action: restore the previous CHH backend image or
the prior versions of `backend/app/rosters.py`, the three affected caller files,
and their tests, then recreate only `family-hero-hub-backend`. Verify health,
Students, one class/group roster, guardian announcements, and one protected FHH
photo.

## Remaining performance debt

- Whole-school in-memory payload construction is now the main measured helper
  cost (about 117–138ms warm beyond SQL) for 4,629 membership edges. It is below
  the one-second guideline and does not justify caching or a more complex query.
- The Students response still serializes 502 rich rows. Pagination can be
  considered when real-school scale requires it; it is separate from the
  eliminated N+1.
- Reporting's correlated event-time attribution is independent of current
  roster expansion and remained fast in this sample.
- Live demo data has no explicit/exclusion rows; production-scale selectivity
  for those branches should continue to be monitored, although correctness and
  constant query count are covered in tests.

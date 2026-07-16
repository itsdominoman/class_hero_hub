# CHH roster resolution implementation

**Implemented:** 2026-07-16
**Scope:** shared current class/subject-group roster resolution
**Schema/data changes:** none

## Public behaviour

Roster response shapes and ordering remain unchanged:

- class rosters return `class_section`, `subject_group: null`, and ordered
  `students`;
- subject-group rosters return the group, optional parent section,
  `enrolment_policy`, ordered `students`, and ordered `excluded_students`;
- student payloads retain `source`, `enrolment_id`, and `enrolled_from`;
- Students list/detail retains `current_class_section` and
  `current_subject_groups`;
- guardian and FHH callers still receive only their existing audience/scope
  sets.

## Membership rules

For a non-archived group in the requested school, membership is derived as:

```text
(section-default members OR grade/year-default members OR explicit members)
MINUS explicit exclusions
```

Rules:

- `explicit_only`: only open explicit member rows apply.
- `default_for_section`: active students with an open member enrolment in the
  exact active class section apply. The section's academic year must equal the
  group's academic year.
- `default_for_grade`: active students with an open member enrolment in any
  active same-school section with the group's grade level and academic year
  apply. Branch is intentionally not a constraint for grade-wide groups.
- Open interval is `valid_from <= today` and
  `valid_to IS NULL OR valid_to > today`.
- Explicit inclusion replaces default source metadata if both paths exist.
- Exclusion is applied last and always wins.
- Student, enrolment, section, and group school scope is checked independently.
- Archived groups and inactive students/sections do not produce current
  default membership.
- Inactive but non-archived groups remain resolvable, preserving the existing
  lifecycle contract; writes into inactive targets remain blocked elsewhere.
- Explicit membership may intentionally cross homeroom sections for electives
  and streamed groups.

## Set-based architecture

`backend/app/rosters.py::resolve_rosters_for_students` returns a
`RosterResolution` containing:

- `class_sections_by_student`;
- `subject_groups_by_student`;
- `students_by_subject_group`; and
- `excluded_students_by_subject_group`.

The full-school/selected-student path performs at most three queries:

1. ordered non-archived subject groups for one school;
2. active students + open class enrolments + active class sections; and
3. active students + open subject-group member/exclusion enrolments.

It builds these in-memory indexes once:

```text
section_id -> [(student, enrolment, section)]
(grade_level_id, academic_year_id) -> [(student, enrolment, section)]
group_id -> explicit member rows
group_id -> exclusion rows
```

It then walks ordered groups, selects the relevant default bucket, overlays
explicit rows, removes exclusions, and writes both group→students and
student→groups result maps. There is no per-group SQL and no lazy relationship
access.

When a caller already owns one group, it passes `groups=[group]`. The resolver
does not reload the group and restricts class rows to that group's exact
section or grade/year context. Explicit-only target rosters need only the
combined explicit/exclusion query after target loading.

When a caller knows selected students, it passes `student_ids`. Both enrolment
queries are narrowed to those IDs. An empty selected scope returns immediately.

## Caller scoping

| Caller | Scope supplied |
|---|---|
| Whole-school Students list | Only returned student IDs; currently 502 |
| Class-filtered/search Students list | Only the filtered student IDs |
| Single student detail/create/update | One student ID |
| Guardian announcements | Linked student IDs, partitioned by school |
| FHH integration dashboard/media | One linked student ID |
| Admin/teacher subject-group roster | One already loaded group |
| Behaviour class/group award validation | One target through `roster_payload` |
| Admin/teacher class roster | Existing two-query section path |
| Reports | No shared resolver; event-time set-based reporting query |
| Imports/default setup | No roster expansion call |

The legacy `bulk_subject_groups_for_students` and
`current_subject_groups_for_student` functions remain as compatibility wrappers
over the set-based resolver. The single-student wrapper now passes one ID rather
than invoking an unscoped whole-school expansion.

## Ordering and duplicate handling

- Groups are loaded by `sort_order`, then `id`.
- Student roster rows sort by `last_name`, `first_name`, then `id`.
- Current class enrolments are processed by enrolment ID; if inconsistent data
  contains more than one open section, consumers retain the existing last-row
  class-context behaviour while scope callers can see the complete unique set.
- Dictionaries keyed by student/group ID prevent duplicate output.
- If inconsistent data has several current explicit/exclusion rows, the last
  enrolment ID supplies metadata and exclusion still wins.

## Security

- Every resolver query filters by `school_id` on all participating tenant
  entities rather than trusting `enrolments.school_id` alone.
- Student `status=active`, active class-section status, group archive state,
  academic-year consistency, and open dates are enforced before membership is
  emitted.
- Teacher assignment checks remain outside and before roster access.
- Behaviour category/assignment/target checks remain unchanged.
- FHH service authentication, per-link authentication, school/student/media
  scope, private media, and FHH-only device path remain unchanged.
- No token, identifier, roster payload, or personal field is logged or cached.
- There is no persistent or indefinite membership cache.

## Query-count contract

Expected resolver statements:

| Workload | Expected maximum |
|---|---:|
| Whole school or selected students | 3 |
| One student | 3 |
| One default-policy subject group after target load | 2 |
| One explicit-only subject group after target load | 1 |
| One class roster including target lookup | 2 |
| FHH linked-student scope | 3 |

The route adds its own authentication/target/student-list queries. On the live
demo, the Students handler used five statements and class-filtered Students used
six when called below the authentication dependency.

No index was added. Existing section/group enrolment indexes support narrow
queries, while the whole-school set-based scans execute in under 2ms at the
measured scale. Query round trips, not scan time, were the proven bottleneck.

## Test coverage

`backend/tests/test_roster_resolution.py` contains the membership truth table,
deterministic/no-duplicate checks, archived/inactive/cross-school/year/branch
cases, and constant query-count assertions with another 20 groups.

Existing suites cover:

- school Students list, detail, class roster, and subject-group roster;
- teacher assignment and roster scope;
- guardian announcement audience and attachments;
- behaviour award target validation;
- reporting filters and event-time attribution;
- imports/setup regressions; and
- FHH link/media scope, including its three-query assertion.

Canonical response hashes for Students, class/group rosters, guardian audience,
and FHH scope matched the pre-change implementation on existing live data.

## Deployment and rollback

Deployment rebuilds/recreates only the CHH `backend` Compose service
(`family-hero-hub-backend`). PostgreSQL, CHH frontend, FHH services, and APKs are
not rebuilt or restarted.

The CHH development deployment completed on 2026-07-16. `/api/health` returned
200; Students, guardian announcements, teacher dashboard, reporting, class/group
roster logic, and protected FHH scope passed. The existing FHH protected-photo
endpoint returned byte-identical private/no-store image bytes in 75–82ms warm,
confirming the unchanged QA4 contract. The previous/deployed backend image IDs
are recorded in the audit document.

No schema/data rollback is needed. Restore the prior backend image/source and
recreate only `family-hero-hub-backend`, then verify:

1. `/api/health`;
2. Students list and one class/group roster;
3. teacher assignment roster;
4. guardian announcements;
5. behaviour/reporting read paths; and
6. one FHH protected photo.

## Remaining debt

The 502-student/4,629-edge whole-school result spends about 0.12–0.14s building
Python response dictionaries after SQL. This is acceptable at current scale.
Pagination or leaner list payloads should be considered only with real scale
evidence. Redis, indefinite membership caching, and a single opaque mega-query
are intentionally not part of this design.

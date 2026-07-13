# S23a CHH Management Reports Audit and Implementation Plan

## 1. Title and scope

This is an audit and implementation plan for a CHH management reporting foundation. It is **planning only**: S23a does not implement endpoints, UI, migrations, seeders, database changes, service changes, tests, commits, pushes, or tags.

Reports are CHH school/admin features. They must not expose Family Hero Hub (FHH) private home/family data, and no parent or FHH UI gains a management-report path.

## 2. Current architecture findings

### Backend routes and authorization

- `backend/app/main.py` registers staff-admin routes below `/api/school`, teacher routes below `/api/teach`, guardian routes below `/api/guardian`, and the FHH server-to-server integration only below `/api/integrations/fhh`.
- `backend/app/routes/school.py` is the existing large school-admin router. `backend/app/routes/behaviour.py` separates an admin category router, teacher award routes, and guardian points route.
- `backend/app/school_scope.py` provides `require_school_role(...)`. It takes the school context from `X-School-Id` (or a path parameter), confirms the school is not suspended, and requires an active, non-revoked membership in that exact school. This is the required boundary for every report endpoint.
- Admin behaviour category routes already use `require_school_role("school_admin")`; teacher award routes independently validate a same-school active teacher membership. Reports should use the former, never the teacher or guardian path.
- Existing tests use FastAPI `TestClient`, in-memory SQLite fixtures, bearer auth headers, and `X-School-Id`. `backend/tests/test_behaviour_points.py` covers category authorization, same-school event creation, context validation, guardian closed-world payloads, and cross-school rejection. `backend/tests/test_school_structure.py` has extensive role and tenancy-isolation patterns.

### Models and relationships

- `BehaviourEvent` belongs to a school, student, behaviour category, and actor user. It has event-time `class_section_id`, `subject_group_id`, `context_type`, `duty_context`, signed `points_delta`, `created_at`, and reversal fields.
- `BehaviourCategory` is school-scoped and constrained to `positive` or `needs_work`; its point sign is constrained to match its type. It has a school/type/label uniqueness constraint.
- Class events link directly to `ClassSection`, which links to branch, academic year, and grade level. Subject events link to `SubjectGroup`, which links to subject and may link to a class section or grade level.
- `Membership` connects a school and user with an active/revoked role state. Staff assignments and enrolments are interval-based, so they are useful for operational UI but must not replace event-time report dimensions.

### Behaviour event schema, constraints, and indexes

The live PostgreSQL `behaviour_events` table has these relevant columns: `school_id`, `student_id`, `category_id`, `actor_user_id`, `points_delta`, `note`, `source`, `created_at`, `reversed_at`, `reversed_by_user_id`, `reversal_reason`, `class_section_id`, `subject_group_id`, `context_type`, and `duty_context`.

- Foreign keys exist to schools, students, categories, users (actor and reverser), class sections, and subject groups.
- Checks restrict source, context type, duty values, and valid context-field combinations. A class event has only a class section; a subject event has only a subject group; a duty event has only a controlled duty context; a general event has none of those dimensions.
- The S22a migration is `alembic/versions/f2a3b4c5d6e8_add_behaviour_event_context.py`. The original points migration is `alembic/versions/d5e6f7a8b9c0_add_behaviour_points.py`.
- Actual live indexes: primary key; individual indexes on `school_id`, `student_id`, `category_id`, `actor_user_id`, `class_section_id`, and `subject_group_id`; composite `ix_behaviour_events_school_student_created (school_id, student_id, created_at)`; and composite `ix_behaviour_events_school_context_created (school_id, context_type, duty_context, created_at)`.
- There is not currently a direct `(school_id, created_at)` report-range index, nor school-prefixed composite indexes for class, subject, actor, or category reporting.

### Frontend routes, navigation, and patterns

- The actual school-admin page is `frontend/src/routes/school/+page.svelte`, not merely a handover artifact. It is a school-admin-only page that selects the first `school_admin` membership from `/api/me/v2`, sends `X-School-Id`, and provides a large tabbed setup/admin workspace.
- The page currently has a Behaviour & points category tab, but no reports tab or reports route. It uses Svelte 5 `$state`, `$derived`, `onMount`, `$lib/api`, responsive cards/tables, and modal dialogs. It deliberately avoids initially loading the heaviest student dataset.
- `frontend/src/routes/teach/+page.svelte` is a distinct teacher workspace for assignments, awarding, announcements, and calendar. It is not a management reporting home.
- `frontend/src/routes/parent/+page.svelte` consumes only guardian endpoints. It has no school-management report navigation or direct FHH connection.
- `frontend/src/routes/+layout.svelte` exposes role-specific global links. A Reports link can be rendered only when `hasSchoolAdmin` is true, in both desktop and mobile navigation.
- Localized English and Arabic messages are centrally maintained in `frontend/src/lib/i18n/messages.ts`. Existing school card/table styling and modal patterns can be reused; no chart library is currently present.

### FHH privacy boundary

- `backend/app/routes/integrations_fhh.py` is service-token plus per-link-token server-to-server functionality. Its dashboard is scoped to one linked child and purpose-built safe fields.
- It does not provide management reports, and reports must not be added to it. FHH browsers must never call CHH report endpoints directly.
- A management report response must exclude FHH link/invite data, service or link tokens/hashes, emails, storage keys, raw paths, private home/family information, raw ORM/object dumps, and unnecessary internal identifiers.

## 3. Seeded data shape summary

Read-only live PostgreSQL aggregates on 2026-07-13 found:

- 10,233 total behaviour events; all 10,233 are currently unreversed.
- Event range: 2026-05-18 07:00 UTC through 2026-08-23 09:50 UTC.
- Context distribution: class 2,545; subject 2,549; duty 2,544; general 2,595.
- Category type distribution: positive 7,479; needs-work 2,754.
- Duty distribution: assembly 509; break 512; hallway 513; lunch 503; playground 507. Bus and general-duty currently have zero events, so report UI must render zero/empty states rather than omit supported values.
- Event-linked contexts: 2,545 class-linked, 2,549 subject-linked, and 2,595 general events.
- Rough active-event cardinalities: 501 students, 28 actor teachers, 28 class sections, 143 subject groups, 8 subjects, 14 grade levels, and 1 branch. All 16 positive and all 16 needs-work categories are represented.

This is sufficient for credible overview, trend, comparison, teacher-usage, category, and support-pattern demonstrations. The single-branch shape limits branch comparison credibility; branch filtering should still be implemented because the data model supports it.

## 4. Recommended report UX location

Create a dedicated `/school/reports` route, with a `Reports` global navigation label visible only to `school_admin` users. Keep the existing `/school` Behaviour & points tab for category configuration; do not add the reporting dashboard to that already large setup page.

The route must make its own `/me/v2` role gate and show an unavailable state for non-admins, but backend authorization remains authoritative. It is separate from `/teach`; teachers do not receive management reports in this slice. `/parent` and FHH-linked dashboards must never expose this route, a report link, or management aggregates.

## 5. Recommended backend endpoint design

Create `backend/app/routes/school_reports.py` with a router dependency of `require_school_role("school_admin")`, registered in `backend/app/main.py` under `/api/school`.

Recommended focused GET endpoints:

- `/api/school/reports/behaviour/overview`: `{ filters, metrics: { total_events, positive_count, needs_work_count, positive_ratio, active_students, active_teachers, signed_points_total } }`.
- `/api/school/reports/behaviour/trends`: `{ filters, interval, series: [{ date, positive_count, needs_work_count, total_events, signed_points_total }] }`.
- `/api/school/reports/behaviour/breakdowns`: `{ filters, classes, grades, subjects, duty_contexts, categories }`, each row containing a display label, total/positive/needs-work counts, signed points, and active-student count where meaningful. Context-specific arrays must remain distinct; never combine duty rows into class/subject rows.
- `/api/school/reports/behaviour/students`: `{ filters, comparison_period, repeated_needs_work, top_positive, improving, worsening }`. Rows should contain a student display name, current report-period counts, signed total, and only the delta metrics needed for support interpretation.
- `/api/school/reports/behaviour/teachers`: `{ filters, teachers: [{ display_name, total_events, positive_count, needs_work_count, active_students }] }`. Label it as activity/awarding volume, not performance.
- `/api/school/reports/behaviour/matrix`: constrained single- or two-dimension aggregates for a leadership Deep Dive. It accepts `row_dimension`, optional `column_dimension`, `date_from`, `date_to`, `branch_campus_id`, `grade_level_id`, `class_section_id`, `subject_id`, `subject_group_id`, `duty_context`, `category_id`, `actor_user_id`, `student_id`, `category_type`, `limit`, and `order_by`. Return `{ filters, row_dimension, column_dimension, measures, rows, truncation }`, where each row has an allow-listed safe row label/key, optional cells with safe column labels/keys, and aggregate measures (`total_events`, `positive_count`, `needs_work_count`, `signed_points_total`, and `active_students` only where meaningful).
- `/api/school/reports/behaviour/events`: `{ filters, pagination: { limit, offset, total }, events: [...] }` for drilldown. Use cursor pagination later only if product requirements need stable traversal under concurrent inserts; bounded `LIMIT/OFFSET` is adequate for this first slice.

The matrix dimension allow-list is exactly `student`, `class_section`, `grade`, `subject`, `subject_group`, `teacher`, `duty_context`, `category`, `category_type`, and `date_bucket`. It must reject unknown dimensions, identical row/column dimensions, and combinations that cannot be attributed from event-time facts or explicitly documented historic interval joins. `order_by` is also allow-listed (initially `total_events`, `positive_count`, `needs_work_count`, or `signed_points_total`), and `limit` caps returned row groups and total cells; do not let a cross product become an unbounded pivot. A request with no column dimension returns a one-dimension grouped aggregate.

The matrix is the explicit cross-dimensional foundation, not a "build every report" escape hatch. It must support the following practical combinations through one dimension plus filters or two grouped dimensions: student by subject, class, teacher, duty context, or category; teacher by subject, class, or category; subject by teacher, class, or grade/year; class by subject or category; grade/year by subject or duty context; category by class, subject, or teacher; and a subject/class/teacher/duty-filtered student grouping for repeated needs-work or top-positive students. Examples include `student` by `subject`, `teacher` by `subject`, `class_section` by `category`, `grade` by `duty_context`, `subject` by `category_type`, and `student` by `teacher`.

Dimension semantics must be explicit in the response and UI. Student, teacher/actor, category, category type, duty context, and date bucket are event fields. Class and subject-group dimensions use the event's stored context where present; subject uses the event subject group then subject. A subject group's stored class/grade relationship supports subject-by-class and subject-by-grade/year. For duty/general events where leadership requests a class or grade dimension, use an enrolment interval containing the event date, not the student's current enrolment; if no unique historical attribution exists, bucket it as `Unattributed` or reject that exact combination rather than silently misclassifying it. This preserves historic reporting while allowing grade-by-duty-context and student/class support views.

Shared query parameters: `date_from`, `date_to`, `branch_campus_id`, `grade_level_id`, `class_section_id`, `subject_id`, `subject_group_id`, `duty_context`, `category_id`, `actor_user_id`, `student_id`, and `category_type` (`positive` or `needs_work`). Validate each supplied ID belongs to the requesting school; validate duty values against the existing controlled set; reject invalid date order and incompatible context filters rather than silently widening a query.

Default to the latest 30 school-local calendar days, inclusive start and exclusive next-day end. Convert school-local dates using `School.timezone`, return ISO timestamps/dates, and cap an interactive query at 366 days. The student trend endpoint must request a previous matching period separately in its implementation. Drilldowns default to 50 and cap at 100 rows.

Every base query, including matrix requests, must include `BehaviourEvent.school_id == membership.school_id`, date bounds, and `reversed_at IS NULL` by default. A future explicit `include_reversed` capability requires a separate policy and is out of scope. Matrix and event outputs use explicit serializers and safe display fields only: no notes by default, emails, FHH data, service/link tokens, token hashes, storage keys, raw paths, raw ORM/object dumps, or internal raw IDs unless a minimal opaque/safe dimension key is needed to construct an authorized event-drilldown filter. Safe event output is limited to event ID, timestamp, category label/type, points delta, context type, display-safe class/subject/duty labels, student display name, and staff display name.

## 6. Recommended frontend report sections

- A filter bar with date range first, followed by branch, grade/year, class, subject, duty context, category, teacher, and positive/needs-work filters. Populate selectors from already authorized school metadata or a dedicated safe filter-options response if needed.
- Overview metric cards: total events, positive count, needs-work count, positive ratio, active students, and active teachers.
- A positive-versus-needs-work trend chart with a table/accessible text fallback. Implement charting only after selecting a repository-appropriate lightweight solution; there is no existing chart dependency to copy.
- Separate comparison sections for classes, grades/year groups, subjects, and duty contexts. Subject points and class points must be visibly separate; duties must be a distinct hotspot section.
- Student support tables for repeated needs-work, top positive, improving, and worsening students. Avoid a public-ranking visual treatment and include minimum-volume thresholds for trend lists.
- A teacher usage table with awarding volume and positive/needs-work split. Place the wording guardrail adjacent to it: this measures recorded activity, not teacher performance, quality, or bias.
- Category/reason breakdown cards or table.
- A Deep Dive / Matrix Explorer after the core dashboard is established: it reuses the shared filter bar, offers an allow-listed row selector and optional column selector, and renders a sortable, bounded result table. Clicking a row or cell applies its safe dimensions to the existing paginated event drilldown rather than loading raw events into the browser. Labels must retain the distinction between class, subject, duty, and general contexts and must describe teacher dimensions as activity/awarding context, never teacher performance.
- A paginated drilldown table opened or filtered from a summary card/table. It should display only safe event fields and keep reports server-aggregated/server-paginated.

## 7. SQL aggregation approach

Use SQLAlchemy Core/ORM expressions that compile to PostgreSQL aggregation, not Python aggregation over an event collection. Start every query from a shared, school-scoped, date-bounded, unreversed base predicate.

- Overview: `count(*)`, `count(*) FILTER (WHERE category.type = 'positive')`, `count(*) FILTER (WHERE category.type = 'needs_work')`, `sum(points_delta)`, and distinct student/actor counts. `CASE` is an acceptable portable alternative in tests.
- Trends: group by `date_trunc('day', behaviour_events.created_at AT TIME ZONE school_timezone)` and category type. Generate any missing presentation dates in the frontend or SQL series without inventing events.
- Class comparison: join `class_sections` only for `context_type = 'class'`, group by event-time class-section ID/name and its event-time branch/grade metadata. Do not classify duty/general events here.
- Grade comparison: for class events, join `class_sections.grade_level_id`; for subject events, resolve the subject group's direct grade level, falling back to its linked class section's grade. Keep the source context in output or separate subcounts so that class and subject contributions are not confused. Do not join current enrolment.
- Subject comparison: for `context_type = 'subject'`, join `subject_groups` then `subjects`, group by subject group and/or subject ID/name/code. The frontend can roll up groups to subject while retaining group-level drilldown filters.
- Duty hotspots: filter `context_type = 'duty'`, group by controlled `duty_context`, and include zero-supported contexts in the response or UI reference list.
- Teacher usage: group by `actor_user_id`, left join `users` for display name, and report counts/splits only. Do not use current staff assignments as an exposure denominator.
- Category breakdown: join `behaviour_categories`, group by category ID/type/label, and count/sum. Historical categories should remain visible even if currently inactive.
- Student support: group by `student_id` and category type/sign. Repeated needs-work sorts needs-work count descending; top positive sorts positive count descending. For improving/worsening, compute the same aggregates for the selected period and immediately preceding equal-duration period, then compare counts or signed totals with a documented minimum event threshold.
- Matrix explorer: map each allow-listed dimension to a fixed SQL expression and required joins, apply the shared school/date/reversal predicates and validated filters, then `GROUP BY` one or two expressions. Use event fields for student, actor, category/type, duty, and date; join subject groups/subjects for subject dimensions; use direct event class context and subject-group metadata for class/grade dimensions; and, only where necessary, join enrolments by `student_id` and an interval containing the event date for historical duty/general class or grade attribution. Never use current enrolment as a shortcut. Return only bounded aggregate rows/cells, and reject a request whose validated grouping cannot produce a trustworthy event-time attribution. Do not aggregate raw rows in Python or the frontend.
- Event drilldown: use the same indexed, date-bounded base predicate, deterministic `ORDER BY created_at DESC, id DESC`, and bounded `LIMIT/OFFSET`. Join only the display dimensions required by the selected columns.

## 8. Index/migration recommendations

Existing indexes are the live database indexes listed in section 2, including the useful student chronology and context/duty composites. Individual foreign-key indexes do not satisfy the common school/date report predicate.

First implementation slice recommendation: add only these report composites after confirming plans with `EXPLAIN (ANALYZE, BUFFERS)` on a representative non-production copy or read-only-safe environment:

- `(school_id, created_at)` for the universal report base range, overview/trend scans, and event drilldown ordering.
- `(school_id, class_section_id, created_at)` for class comparison/filter/drilldown.
- `(school_id, subject_group_id, created_at)` for subject comparison/filter/drilldown.
- `(school_id, actor_user_id, created_at)` for teacher-usage aggregation/filter.
- `(school_id, category_id, created_at)` for category breakdown/filter.

Do not initially add the suggested `(school_id, context_type, duty_context, created_at)` because it already exists as `ix_behaviour_events_school_context_created`. Do not initially add a student duplicate because `ix_behaviour_events_school_student_created` already exists. Do not add a separate grade index: grade is reached through low-cardinality dimensions, and an event-level grade column does not exist. Avoid partial indexes on `reversed_at IS NULL` until query plans show the unreversed predicate is selective enough to justify their write/storage cost.

If the validation supports these additions, create one migration named `alembic/versions/<revision>_add_behaviour_report_indexes.py` in S23b and mirror each index in `BehaviourEvent.__table_args__` in `backend/app/models_school/models.py`. No aggregate or materialized table is justified at 10k events; direct SQL aggregation is the first design.

## 9. Exact files likely to change in S23b/S23c

From the live repository structure, likely changes are:

- `backend/app/routes/school_reports.py` (new report router, query validation, aggregation, safe serializers).
- `backend/app/main.py` (register the new school report router under `/api/school`).
- `backend/app/models_school/models.py` (declare any approved report composite indexes).
- `alembic/versions/<revision>_add_behaviour_report_indexes.py` (only if post-implementation plan inspection validates the first-slice indexes).
- `backend/tests/test_school_reports.py` (new focused endpoint, tenancy, aggregation, privacy, and pagination tests).
- `frontend/src/routes/school/reports/+page.svelte` (new admin report route and report UI).
- `frontend/src/routes/+layout.svelte` (admin-only Reports navigation in desktop and mobile layouts).
- `frontend/src/lib/i18n/messages.ts` (English and Arabic navigation, filters, empty states, metric labels, guardrails, and report strings).
- `frontend/src/lib/api.ts` is already the shared request helper and should not need modification unless response/error needs prove otherwise.

`frontend/src/routes/school/+page.svelte`, `frontend/src/routes/teach/+page.svelte`, and `frontend/src/routes/parent/+page.svelte` should not be changed for the first dedicated-route approach, except only if a later product decision explicitly adds a school-page shortcut. No FHH integration route should change.

## 10. Focused tests for implementation

- A `school_admin` can access each report endpoint with the correct school header.
- Teacher and guardian users receive denial for every management report endpoint.
- An admin cannot query another school's data by changing `X-School-Id`, dimension IDs, or filter IDs.
- Default, custom, invalid, and overlong date range handling works, including school-local date boundaries.
- Branch, grade, class, subject/group, duty, category, teacher, and category-type filters produce the expected scoped aggregates.
- Known fixture events validate overview, trend, class, subject, duty, teacher, category, and student-support aggregation correctness.
- Matrix tests cover every allow-listed single dimension; representative two-dimension combinations (`student`/`subject`, `teacher`/`subject`, `class_section`/`category`, `grade`/`duty_context`, `subject`/`category_type`, and `student`/`teacher`); support-pattern student grouping under selected subject, class, actor, and duty filters; unknown/duplicate/incompatible dimension rejection; matrix cell and row limits; and safe cell-to-drilldown filtering.
- Class and subject contexts remain separate; duty events never appear in classroom comparison totals.
- Historic matrix class/grade attribution uses the event-time enrolment interval where required and never current enrolment; missing/ambiguous attribution is visible as `Unattributed` or rejected according to the documented combination rule.
- Event drilldown is deterministically ordered and paginated, with max page size enforced.
- Reversed events are excluded by default, including every aggregate and drilldown; any later explicit include-reversed behavior gets separate tests.
- Response keys are allow-listed: no FHH/private/link/token/hash/email/storage/path fields, no note by default, and no raw object data.
- Add a frontend route smoke test only if a frontend test runner is present and already used by the repository; otherwise verify the route manually in its dedicated implementation slice rather than introducing an unrelated test stack.

## 11. Suggested implementation slices

- S23b: backend reporting query helpers, fixed dashboard endpoint contracts plus the constrained matrix endpoint contract, safe response serializers, focused tests, and only validated index migration.
- S23c: admin reports UI shell, shared filter bar, overview cards, and positive/needs-work trend presentation. Deliberately defer Matrix Explorer UI until the core dashboard contracts are stable.
- S23d: comparison tables, duty hotspots, category breakdown, paginated drilldown, and the first bounded Matrix Explorer UI using the completed S23b contract.
- S23e: student support and teacher usage sections, with trend thresholds and interpretation guardrails.
- S23f: accessibility/polish, query-plan review, range-limit review, empty/zero states, and realistic demo verification.

## 12. Risks and guardrails

- Privacy: enforce admin/school scope server-side, use explicit serializers, and never expose FHH/private home data, links, tokens, hashes, emails, storage keys, raw paths, notes, or object dumps.
- Query safety: require bounded dates, cap interactive range/page size, validate all filters against the membership school, and do all aggregation in SQL.
- Matrix safety: use only explicit dimension and ordering allow-lists, cap row/cell cardinality, reject incompatible or historically untrustworthy combinations, and keep matrix aggregation in SQL rather than Python or the browser.
- UI safety: fetch summaries rather than raw events, fetch drilldowns only on demand, and never aggregate giant datasets in the browser.
- Join correctness: keep joins narrow and inspect plans before adding indexes or materialization. Never substitute a student's current enrolment for the class/subject attached to the event.
- Time semantics: define school-local date input and inclusive/exclusive range behavior once; return ISO values and test daylight/timezone boundaries.
- Interpretation: distinguish class, subject, duty, and general contexts in every comparison. A positive English subject event and a negative Maths subject event must remain independently visible. Duty reports must not be mixed into classroom reports.
- Teacher usage: label it as usage/recording volume, not teacher performance, bias, quality, or supervision coverage.
- Reversals: exclude reversed events by default across all endpoints; never rely on client filtering.
- Historic fidelity: use event-time context. Current staff assignments/enrolments can change and would corrupt historical reports if used as substitutes.

## 13. Final recommendation

The event model, school-role guard, event-time context fields, live index baseline, and seeded distribution are sufficient to build a privacy-safe first reporting foundation. Proceed only through the proposed small slices, keeping SQL aggregation, bounded ranges, explicit serializers, and context separation mandatory.

APPROVE IMPLEMENTATION PLAN

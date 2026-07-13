# S23c Management Reporting UI Audit

**Date:** 2026-07-13

**Scope:** Uncommitted S23c reporting UI and the minimum backend/API inspection needed to assess it

**Reference:** `docs/planning/2026-07-s23-management-reports-plan.md`

**Backend baseline:** S23b commit `64ebed4`, tag `chh-s23b-management-reporting-backend-2026-07-13`

## 1. Executive summary

**Decision: DO NOT COMMIT YET.**

The route, role gates, navigation, core aggregates, category-type/category cascade, safe event serializer, pagination, i18n parity, type checking, and production build are present and working at a structural level. The page is not yet a trustworthy finished management-reporting experience.

The most important blockers are functional, not cosmetic:

- Teacher usage names render blank because the UI reads `row.label` while the endpoint returns `display_name`.
- Summary-row clicks change a global filter but do not open the underlying events or explain the new active context.
- Matrix cell drilldown is incorrect: it applies only the clicked column, loses the row context, and some matrix dimensions either do nothing or open unfiltered events.
- Selecting `order_by` in Deep Dive changes server ordering but the matrix still displays `total_events`, which can make the visible numbers disagree with the chosen ordering.
- Most selectors come from broad configuration/admin endpoints rather than activity in the chosen date/filter context. Impossible combinations remain selectable, and “All” can conceal an empty or irrelevant option set.
- Several backend breakdowns have no explicit ordering; users are not told how any table is sorted.
- The effective default 30-day period is invisible because the frontend leaves both date fields blank and ignores the normalized filters returned by the API.
- The page reads teacher and student options from oversized admin payloads. The teacher response includes email addresses, and student search is only truncated after an unbounded, data-rich response reaches the browser.
- The visual hierarchy is a succession of dense tables. It reads as an API/admin console rather than a guided leadership dashboard.

S23c should receive a focused pre-commit correction slice for the broken labels, truthful drilldowns, effective-filter display, deterministic ordering, and human-facing Deep Dive labels. Fully intelligent cascading should follow with a dedicated, bounded report `filter-options` endpoint.

## 2. Current state

### What works

- `/school/reports` exists at `frontend/src/routes/school/reports/+page.svelte`.
- Desktop and mobile global navigation show Reports only when `hasSchoolAdmin` is true (`frontend/src/routes/+layout.svelte:67-74`, `101-108`).
- The school admin sidebar has a prominent Reports link (`frontend/src/routes/school/+page.svelte:2253-2258`).
- The page independently requires a `school_admin` membership before loading data (`frontend/src/routes/school/reports/+page.svelte:54`).
- Every reporting backend route has the `school_admin` dependency, and the base query is school-scoped, date-bounded, and excludes reversed events (`backend/app/routes/school_reports.py:29`, `143-205`).
- Parent/FHH route files are untouched. No report endpoint is registered under guardian or FHH prefixes.
- Positive/needs-work category filtering works locally, and an incompatible selected category is cleared (`frontend/src/routes/school/reports/+page.svelte:21`, `51`).
- Grade filters class-section metadata by the correct `grade_level_id` field, and an incompatible selected class is cleared (`frontend/src/routes/school/reports/+page.svelte:22`, `52`).
- The reports endpoints accept the shared report filters and validate supplied school-owned IDs.
- Events are ordered by `created_at DESC, id DESC`, paginated, and serialized without note/email/token/FHH/storage fields (`backend/app/routes/school_reports.py:388-397`).
- English/Arabic key parity passes with 967 keys in each locale.
- `npm run check`, `npm run check:i18n`, and `npm run build` pass.

### What is incomplete

- Context-aware/faceted option loading for grade, class, subject, duty, category, teacher, and student.
- Branch/campus filtering in the UI even though the backend supports it.
- Clear active-filter chips and an effective date-range summary.
- Reliable row/cell-to-event drilldown that carries every selected dimension.
- Deterministic, documented sorting across all report sections.
- Category type in breakdown rows for badges/grouping.
- A chart-like trend presentation and management-oriented visual hierarchy.
- Empty-state reasons, zero-data entities, and data-coverage views.
- Minimum-volume interpretation for improving/worsening lists.
- Tests for the uncommitted `dimension_key` response additions and frontend click-through behavior.

### What is misleading

- “All” often means “all configured metadata,” not “all options relevant to this report context.”
- Blank dates look like an unbounded report even though the backend silently uses its latest-30-day default.
- Matrix cells appear to be two-dimensional drilldowns, but a click applies only one dimension.
- Deep Dive can say “Order by Positive” while showing total-event values.
- Clicking a comparison row looks actionable but silently changes the whole dashboard without opening events or showing an explicit drilldown banner.
- A class selector with only “All” does not distinguish “this grade has no configured current sections,” “historic activity has no current metadata option,” and “metadata failed.”
- Teacher usage currently displays empty names, making rows uninterpretable.

## 3. Git/worktree review

Initial worktree state:

```text
## main...origin/main
 M backend/app/routes/school_reports.py
 M frontend/src/lib/i18n/messages.ts
 M frontend/src/routes/+layout.svelte
 M frontend/src/routes/school/+page.svelte
?? frontend/src/routes/school/reports/
```

Initial tracked diff: 108 insertions and 16 deletions across four tracked files; the untracked reports page is 89 compressed lines and is not included in ordinary `git diff --stat` until staged.

| File | Purpose | Assessment |
|---|---|---|
| `backend/app/routes/school_reports.py` | Adds `dimension_key` to breakdown, student, teacher, and matrix results | Needed for safe click-through and consistent with the plan, but untested in the focused backend tests and paired with broken frontend drilldown semantics. Do not commit it without response-contract/click-through tests. |
| `frontend/src/routes/school/reports/+page.svelte` | Entire reporting page | In scope, but has pre-commit functional blockers and is too compressed for safe maintenance/review. |
| `frontend/src/routes/+layout.svelte` | Desktop/mobile admin-only Reports links | In scope and correctly role-conditional. Global layout is the right place for the global link. |
| `frontend/src/routes/school/+page.svelte` | School admin sidebar shortcut | In scope and useful. It is an intentional exception to the original first-slice plan and does not touch FHH. |
| `frontend/src/lib/i18n/messages.ts` | English/Arabic report/nav strings | In scope and parity is complete, but wording/formatting and missing UX strings need correction. |

No accidental parent, guardian, FHH, migration, model, generated, or unrelated application changes were found. The local frontend build output remains ignored. The only file created by this audit is this document.

`git diff --check` passes. The implementation should **not** be committed as-is.

## 4. Critical findings

No access-control or cross-school **Critical** defect was found in the inspected code. The following High findings are still release/commit blockers because they make management output blank, ambiguous, or materially misleading.

### H1 — Teacher usage rows have no visible teacher name

- **Severity:** High
- **Evidence:** The endpoint returns `display_name` (`backend/app/routes/school_reports.py:300-301`), while `SummaryTable` renders `row.label` (`frontend/src/routes/school/reports/+page.svelte:85`). `usage` is assigned without adapting the field (`:39`).
- **Why it matters:** Management cannot identify the teacher associated with a usage row. This defeats the section’s primary purpose.
- **Recommended fix:** Normalize teacher rows to the common UI row shape (`label: display_name`) or give teacher usage a typed, dedicated component. Add a focused UI/contract test.

### H2 — Summary and matrix drilldowns do not preserve or disclose context

- **Severity:** High
- **Evidence:** Summary rows call `filter(...)`, which changes one filter and reloads reports but does not set `eventsOpen` (`frontend/src/routes/school/reports/+page.svelte:48`, `85`). Matrix cell buttons call `matrixFilter` with only the column dimension (`:49`, `81`); the row dimension is discarded. `subject_group` and `date_bucket` fall into the fallback and open events without applying their dimension. `category_type` maps to a key that `filter` never assigns.
- **Why it matters:** A leader can click a number believing they are seeing its evidence while actually seeing a broader or unchanged dataset. This is a reporting-trust failure.
- **Recommended fix:** Use one typed drilldown context containing the current filters plus row and column keys. Open/refresh events immediately, scroll/focus the drilldown, show active context chips, and provide “Back to overview”/clear controls. Disable unsupported dimension clicks rather than widening silently.

### H3 — Deep Dive ordering can disagree with the displayed measure

- **Severity:** High
- **Evidence:** `matrixOrderBy` is sent to the API (`frontend/src/routes/school/reports/+page.svelte:46`), but every two-dimensional cell always renders `cell.total_events` (`:81`). One-dimensional rows also always render `row.total_events`.
- **Why it matters:** “Order by Needs work” or “Order by Signed points” can produce a table whose visible totals do not explain the order. Users may conclude results are arbitrary or incorrect.
- **Recommended fix:** Render the selected measure, label it explicitly, and show “Sorted by …”. Optionally retain total as a secondary value, never as the unexplained primary value.

### H4 — Filter options are broad configuration data, not report-context options

- **Severity:** High
- **Evidence:** Grades, sections, subjects, categories, and teachers are loaded once from unrelated admin endpoints (`frontend/src/routes/school/reports/+page.svelte:32-35`). Only category type→category and grade→section are locally cascaded. A source comment itself defers safe teacher narrowing (`:44`).
- **Why it matters:** Impossible combinations remain selectable; subject+duty can produce a backend 422; selected teachers/students do not narrow any related choices; and “All” does not describe the valid report universe.
- **Recommended fix:** Add the bounded `GET /api/school/reports/behaviour/filter-options` endpoint described in section 10. Until then, clear known incompatible pairs, label configuration-derived selectors honestly, and never imply contextual narrowing that is not implemented.

### H5 — Effective dates and drilldown context are hidden

- **Severity:** High
- **Evidence:** Date inputs initialize blank (`frontend/src/routes/school/reports/+page.svelte:15`), while the API applies a default bounded period and returns normalized `filters`; the frontend ignores every returned `filters` object (`:39`). No active chips or report-period heading exist.
- **Why it matters:** Management cannot tell what period a number covers and may mistake blank dates for all-time data. After a row click, the changed selector may be off-screen and there is no local explanation.
- **Recommended fix:** Hydrate/display the API’s effective inclusive dates, add a “Last 30 days” preset, show a report-period subtitle, and render removable active-filter chips above results and events.

### H6 — Several report sections have arbitrary or nondeterministic ordering

- **Severity:** High
- **Evidence:** Grade, subject, duty, and category breakdown queries have no `ORDER BY` (`backend/app/routes/school_reports.py:269-272`). Class rows have total-descending but no tie-breaker (`:268`). No frontend table displays sort state (`frontend/src/routes/school/reports/+page.svelte:85`).
- **Why it matters:** Leadership cannot infer priority, repeated requests may reorder tied rows, and the dashboard feels unfinished.
- **Recommended fix:** Apply the policy in section 7 server-side with deterministic label/key tie-breakers, and display a small sort label or sortable column indicator.

### H7 — Report option loading retrieves excessive fields and one GET can write

- **Severity:** High
- **Evidence:** `/school/teachers` includes `user.email` (`backend/app/routes/school.py:542-547`, `1863-1902`). `/school/students` returns external reference, date of birth, gender, timestamps, and context (`backend/app/routes/school.py:624-641`) and has no server result limit (`:2206-2236`); the reports UI slices to 20 only after receipt (`frontend/src/routes/school/reports/+page.svelte:45`). `/school/behaviour/categories` calls `seed_default_categories` and commits during GET (`backend/app/routes/behaviour.py:83-86`).
- **Why it matters:** The report page fetches more personal/administrative data than it needs, student search is not safely bounded at the server, and a read-only report load can cause a database write. The current teacher endpoint also omits school-admin actors who may have recorded events, so its “All” list is incomplete.
- **Recommended fix:** Move every option to the dedicated safe report endpoint. Return only ID/key plus display label/type/status where necessary, cap student search server-side, include every actor with matching report activity, and ensure GET is side-effect free.

### M1 — Grade 2 showing only “All” is not a field mapping bug in this component

- **Severity:** Medium
- **Evidence:** Class section payloads include `grade_level_id` (`backend/app/routes/school.py:345-359`), and the UI compares that exact field (`frontend/src/routes/school/reports/+page.svelte:22`). `/class-sections` excludes archived rows and returns configuration rows, not activity-date rows (`backend/app/routes/school.py:1222-1224`, `362-367`).
- **Why it matters:** Grade comparison can include event-time/historic Grade 2 activity while the current metadata selector has no non-archived Grade 2 sections. The UI then presents only “All,” hiding whether this is missing seed/configuration, archived history, or genuinely no section.
- **Recommended fix:** Verify the school’s Grade 2 current/historic section configuration separately. The contextual endpoint should derive safe options from matching event-time facts and label historic/inactive options where needed. Show a reasoned empty state, not just “All.” No evidence supports faking Grade 2 sections in the frontend.

### M2 — Student improvement/worsening semantics need correction and explanation

- **Severity:** Medium
- **Evidence:** The backend orders all deltas descending and limits to 20 before separating improving and worsening (`backend/app/routes/school_reports.py:290-293`). This can omit the most negative students when more than 20 students have activity. The UI labels only a bare signed number (`frontend/src/routes/school/reports/+page.svelte:86`).
- **Why it matters:** The “worsening” list can be incomplete in exactly the population it intends to highlight, and signed-points change is not explained or volume-qualified.
- **Recommended fix:** Query improving and worsening independently (or rank after a complete bounded aggregate), apply a documented minimum volume, include comparison dates, and label the displayed measure.

### M3 — The page is compressed into an unsafe maintenance shape

- **Severity:** Medium
- **Evidence:** The complete page is 89 lines, with most handlers and entire report sections collapsed onto single lines (`frontend/src/routes/school/reports/+page.svelte:27-55`, `63-89`). It uses `any`, an unused snippet argument, and broad shared row types.
- **Why it matters:** Review misses are more likely (the teacher label mismatch and broken matrix drilldown are examples), and future filter/drilldown work will be fragile.
- **Recommended fix:** Reformat and split typed filter, summary, table, matrix, events, badge, and empty-state components without changing product behavior accidentally.

### L1 — Navigation is correct but lacks current-page state

- **Severity:** Low
- **Evidence:** Reports links are role-conditional but have no active-route treatment (`frontend/src/routes/+layout.svelte:67-74`, `101-108`; `frontend/src/routes/school/+page.svelte:2253-2258`).
- **Why it matters:** Minor orientation issue, especially on mobile.
- **Recommended fix:** Add `aria-current="page"` and the established active-link treatment.

## 5. Cascading filter findings

All existing option endpoints are school-admin protected and school-scoped. That makes them authorization-safe, but not necessarily data-minimal, bounded, historically accurate, or context-aware for reporting.

| Filter | Current behaviour/source | Expected behaviour | Fix needed | Layer |
|---|---|---|---|---|
| Effective date range | Blank native date inputs; backend silently defaults to latest 30 school-local days | Show effective inclusive range; changing dates refreshes all available facets and results | Consume returned filters; add presets and contextual option request | Frontend + backend options |
| Branch/campus | Not present, although backend accepts `branch_campus_id` | Available when the school has multiple branches; narrows all other facets | Add bounded branch options and selector | Backend + frontend |
| Category type | Static allow-list; locally filters categories and clears stale category | Positive shows only positive categories; Needs work only needs-work; also narrows every activity-derived facet | Existing local cascade is correct; contextual narrowing still needed | Frontend now; backend for full cascade |
| Grade/year | All non-archived configured grades | Show grades with matching activity (or clearly marked zero-data mode); narrow sections, subjects, teachers, categories, duties, students | Replace broad metadata with contextual options | Backend needed |
| Class section | All non-archived configured sections, locally filtered by selected grade; stale class clears | Show matching event-time sections for grade/date/context; distinguish none configured from none active | Context endpoint; explicit empty reason; reload options | Backend + frontend |
| Subject | All non-archived configured subjects; does not narrow anything | Show subjects with matching activity and narrow grade/class/teacher/category/student; clear duty incompatibility | Context endpoint and incompatible-selection handling | Backend + frontend |
| Duty context | Static controlled list; does not narrow anything | Show matching duty contexts/counts, narrow teachers/categories/students/grades where attribution is safe; clear subject incompatibility | Context endpoint and incompatible-selection handling | Backend + frontend |
| Category | All visible historical/inactive categories; only narrowed by type | Show matching categories with type and inactive/historic indication; narrow all activity facets | Side-effect-free contextual options | Backend + frontend |
| Teacher/staff | Active teacher memberships from admin endpoint; broad, email-bearing response; excludes non-teacher actors | Matching event actors for date/current filters; ID + display name only; narrow grade/class/subject/category/duty/student | Dedicated contextual options | Backend needed |
| Student | Search after 2 characters; current-class filter only if selected; server sends unbounded rich payload; stale selection is not cleared when other filters change | Bounded matching-activity search, safe label/key only; selection narrows subject/class/teacher/category/duty; stale selection retained only if valid | Dedicated search facet with limit/query and validity response | Backend + frontend |
| Subject group | Backend/matrix supports it, but no core filter control | Optional advanced facet when needed to distinguish multiple groups of one subject | Add only if leadership terminology supports it; use a human label | Backend + frontend |

### Grade 2 diagnosis

The frontend grade→section comparison is structurally correct and uses the API’s real `grade_level_id`. If Grade 2 displays only “All,” one of these is more likely than a mapping mismatch:

1. there is no non-archived Grade 2 class section in `/school/class-sections`;
2. the Grade 2 activity belongs to an archived/historic section excluded by current metadata;
3. Grade 2 exists as seeded structure without seeded class sections;
4. report activity is attributable to grade through subject-group or event-time enrolment while no current selectable section exists; or
5. metadata loading failed as part of the all-or-nothing `Promise.all`, in which case the page currently reports only a generic error.

This audit did not query live authenticated metadata because the current category metadata GET may seed/commit data. The implementation should add a read-only diagnostic/test fixture for this case rather than infer or fabricate sections client-side.

### Stale and impossible combinations

- Category type clears an incompatible category; grade clears an incompatible class.
- No equivalent clearing occurs for subject+duty even though the backend rejects that pair.
- Changing class does not clear/revalidate a selected student.
- Changing teacher, student, subject, category, or duty does not refresh any option list.
- Student search results can remain from an older context.
- Clearing a stale value in `$effect` does not itself communicate why it changed.
- Metadata loading is one `Promise.all`; one failed option endpoint prevents all report loading and gives no per-filter recovery.

## 6. Drilldown behaviour

| Source | Current click behaviour | Assessment and required correction |
|---|---|---|
| Class comparison row | Sets `class_section_id`, reloads dashboard; events refresh only if already open | Key is correct, but not a genuine immediate drilldown. Open events and show the class chip/context. |
| Grade comparison row | Sets `grade_level_id`, reloads dashboard | Key is correct. Clear/revalidate class, open events, and explain grade scope. |
| Subject comparison row | Sets `subject_id`, reloads dashboard | Key is correct. Clear incompatible duty, open events, show subject context. |
| Duty hotspot row | Sets controlled `duty_context`, reloads dashboard | Key is correct. Clear incompatible subject, open events, localize the selected duty label. |
| Category breakdown row | Sets `category_id`, reloads dashboard | Key is correct. Sync/display category type and open events. |
| Repeated needs-work student | Sets `student_id`, reloads all reports | Student key is correct, but the click does not automatically keep/declare needs-work context; the list’s meaning can be lost. Open events with `category_type=needs_work`. |
| Top-positive student | Sets `student_id`, reloads all reports | Same issue; preserve/apply `category_type=positive` for the evidence view. |
| Improving/worsening student | Sets `student_id`, reloads all reports | Does not expose current vs comparison periods or the events behind the delta. Add a two-period profile/drilldown. |
| Teacher usage row | Intended to set `actor_user_id` | Name is blank; click key works only after the row is found. Open events and label as recorded activity. |
| Matrix row | Applies one mapped dimension; one-dimensional numeric total is not clickable | Apply row dimension to event context and open events. Unsupported keys must be disabled. |
| Matrix cell | Applies only column dimension | Incorrect. Apply both row and column dimension keys plus global filters, then open events. |
| `subject_group`/`date_bucket` matrix click | Opens events without applying the clicked value | Misleading widening. Add supported event filters/parameters or disable click. |
| `category_type` matrix click | Calls a filter assignment that does not exist | No effective filtering. Implement the typed assignment and open matching events. |

The event response itself is appropriately restricted: event ID/timestamp, safe display names, category label/type, points, and display-safe context only. Notes, emails, tokens, hashes, FHH data, storage paths, and raw objects are excluded. Pagination ordering is deterministic, but the UI needs an explicit zero-row state (it currently can show `1–0 / 0`), page-size wording, styled controls, and current drilldown context.

## 7. Sorting/order findings

Recommended global policy: overview cards use fixed logical order; time series use date ascending; ranked comparisons use the relevant default measure descending then localized label/key ascending; events use timestamp/id descending; every ranked section displays its sort rule; and any user-selected matrix order controls both ordering and the primary displayed value.

| Report section | Current order | Desired order | UI indication needed |
|---|---|---|---|
| Behaviour trend | Backend local day ascending | Date ascending, filling visual gaps without inventing events | “Daily, oldest to newest”; chart axis/accessible fallback |
| Class comparison | Total descending; no tie-breaker | Total descending, label/key ascending tie-break | “Sorted by total events”; active Total header indicator |
| Grade comparison | No explicit order | Total descending by default; optional needs-work ratio view | “Sorted by total events” or selected metric |
| Subject comparison | No explicit order | Total descending by default | Same |
| Duty hotspots | No explicit order | Total descending; only use school-day semantic order if explicitly labeled | “Largest hotspots first” |
| Category breakdown | No explicit order; type not returned | Type group then total descending, or total descending with type badges; deterministic label tie-break | Type badges and “Sorted by total events” |
| Student: repeated needs-work | Total descending after needs-work filter; no tie-break | Needs-work count descending, then name/key | Label number as “needs-work events” |
| Student: top positive | Total descending after positive filter; no tie-break | Positive count descending, then name/key | Label number as “positive events” |
| Student: improving | Signed-points delta descending within a pre-limited set | Positive delta descending with minimum volume and deterministic tie-break | “Change vs previous equal period” plus dates |
| Student: worsening | Reversed subset of the same pre-limited set; may omit worst students | Most negative delta first (absolute deterioration descending), independently ranked | Same, with negative-direction semantics |
| Teacher usage | Total descending; no tie-break | Total descending, name/key; optionally allow activity split sort | “Recording activity — sorted by total events” |
| Underlying events | `created_at DESC, id DESC` | Keep | “Newest first” |
| Deep Dive matrix | Server orders selected row and column groups by `order_by` descending then label; UI always displays totals | Keep deterministic selected ordering but display the selected measure; define zero/blank cells | Selected-column indicator and “Sorted by …”; show truncation |

Overview card order should be: Total events, Positive, Needs work, Positive ratio, Active students, Active staff, Signed points. Signed points should be visually de-emphasized or explained because it mixes positive and negative values.

## 8. Visual/design findings

The page is spreadsheet-like. This is not mainly because it uses tables; it is because almost every section has equal visual weight, the tables use the same generic four columns, and the page offers little interpretation, prioritization, or state explanation.

Specific problems:

- Seven equal metric cards create an undifferentiated wall of numbers. There is no primary insight or date context.
- The trend is a second generic table nested inside a card with the title “Behaviour trend” repeated twice.
- Five comparison tables follow in a uniform grid with no subtitles, ranking explanation, visual bars, badges, or “click to inspect” cue.
- Student support compresses four different interpretations into small lists with unexplained numbers.
- Positive and needs-work values have no consistent subtle green/amber/rose treatment or type badges.
- Category breakdown cannot show type styling because the API omits category type.
- Deep Dive preset chips display raw API names such as `class_section` and `category_type` (`frontend/src/routes/school/reports/+page.svelte:81`). Matrix labels can also expose raw `needs_work`, duty keys, and “Not duty.”
- Filter labels are all uppercase and dense; ten controls appear at once without primary/advanced grouping.
- There are no active filter chips, saved time presets, result count, “last updated,” or reset-one-filter actions.
- Empty states are generic and reused for fundamentally different conditions. “No activity,” “no valid options,” “search for a student,” and “failed metadata” need different copy/actions.
- Rows become clickable only through hover color; there is no chevron, button label, focus treatment explanation, or “Select a row to view events.”
- Native tables have a fixed `min-width: 520px`; mobile relies on horizontal scrolling and does not prioritize essential columns or offer stacked rows.
- Event pagination buttons and matrix cells are visually underdeveloped relative to CHH card/button styles.
- No truncation warning from the matrix API is rendered, so a bounded partial matrix can look complete.

Recommended product-aligned treatment:

1. Add a leadership header with effective period, active filter chips, and quick ranges (7 days, 30 days, this term, custom).
2. Make Total, Positive/Needs work split, ratio, and active coverage the primary insight band; place secondary metrics in compact chips.
3. Replace the trend table’s primary view with a lightweight accessible positive-vs-needs-work chart (stacked bars or two lines) and keep a collapsible/visually secondary table fallback.
4. Introduce section hierarchy: “At a glance,” “Where attention is needed,” “Student support,” “Recording coverage,” then “Explore the data.”
5. Use compact proportional bars in class/grade/subject/duty rows, subtle type badges, and one emphasized default metric.
6. Give each section a one-sentence management question and sort statement.
7. Add chevrons/action text and keyboard-visible row buttons for drilldown.
8. Use human labels everywhere: “Class section × category,” “Needs work,” “Date,” and localized duty names—never snake_case.
9. On mobile, render ranked rows as cards or hide secondary columns behind expansion; keep the identity and priority metric visible without horizontal scrolling.
10. Give every empty state a reason and next action, for example “No Grade 2 sections have matching activity in this period” and “Clear subject filter.”

## 9. Management question coverage

“Direct” means the current page displays the answer without constructing a matrix. “Drilldown” includes using the existing filters/summary click and, where necessary, opening events. A coverage label does not imply the current presentation is well sorted or polished; defects are noted.

| # | Management question | Current coverage | Notes/gap |
|---:|---|---|---|
| 1 | How many behaviour events were recorded in the period? | Direct | Total card, but effective default period is hidden. |
| 2 | What is the positive vs needs-work split? | Direct | Cards and trend table. |
| 3 | Is activity rising or falling day by day? | Direct | Daily table only; no chart or period comparison. |
| 4 | Which classes have the most needs-work events this month? | Direct | Counts visible, but table defaults to total rather than needs-work sort. |
| 5 | Which grade has the highest needs-work ratio? | Deep Dive | Can inspect grade × category type, but no ratio or truthful selected-measure presentation. |
| 6 | Which subjects generate the most needs-work? | Direct | Counts visible but unsorted/arbitrary. |
| 7 | Which duty context is the biggest hotspot? | Direct | Counts visible but duty order is arbitrary. |
| 8 | Which categories are most common in hallway incidents? | Drilldown | Select Hallway then inspect categories; ordering remains arbitrary. |
| 9 | Which students repeatedly appear in Maths needs-work? | Drilldown | Subject + Needs work filters then student support. |
| 10 | What happened for one student over the last 30 days? | Drilldown | Student search + events; effective dates/context need clearer display. |
| 11 | Which teacher recorded points for this student? | Deep Dive | Student × teacher can answer; matrix click-through is currently wrong. |
| 12 | Which teachers are recording behaviour in Year 5? | Not yet | Teacher usage names render blank; grade filter is otherwise available. |
| 13 | Which teacher records the most needs-work in a class? | Deep Dive | Teacher/category type with class filter; selected ordering/display is misleading. |
| 14 | Which classes have low or no records? | Not yet | Breakdown returns activity rows only; no exposure/zero baseline. |
| 15 | Which subjects have no data? | Not yet | No configured-vs-active coverage comparison. |
| 16 | Are students improving or worsening versus the prior period? | Direct | Lists exist, but worsening ranking can omit the worst students and lacks thresholds/dates. |
| 17 | Can I see the underlying events behind a class number? | Drilldown | Possible only by row filter then separately opening events; not immediate or clearly contextual. |
| 18 | Which categories dominate in each class? | Deep Dive | Class section × category preset; cell drilldown loses class context. |
| 19 | Which subjects drive behaviour in each grade? | Deep Dive | Subject × grade can be configured manually; no guided preset. |
| 20 | Which duty issues affect each grade? | Deep Dive | Grade × duty preset. Historic attribution can be “Unattributed.” |
| 21 | Which students receive the most positive recognition? | Direct | Top-positive list; bare number needs a label. |
| 22 | Which staff members are recording very little or nothing? | Not yet | Endpoint only includes actors with events and lacks an exposure denominator; teacher names are blank. |
| 23 | Are positive/needs-work patterns different by teacher and subject? | Deep Dive | Teacher × subject plus category-type filter, but not a three-axis view. |
| 24 | Which categories are increasing week over week? | Not yet | Trend is school-total by day, not category-period comparison. |
| 25 | Are hallway incidents concentrated among particular students? | Drilldown | Duty filter + repeated-needs-work/student lists or student matrix. |
| 26 | Are there unattributed class/grade records that need data cleanup? | Deep Dive | Matrix can show “Unattributed,” but there is no explicit data-quality summary. |
| 27 | How much of the student population has any record? | Direct | Active students count exists, but no enrolled-population denominator/coverage rate. |
| 28 | Can I export the evidence for a leadership meeting? | Not yet | No export/print-friendly report view. |

The biggest usefulness gaps are zero/low-coverage reporting, ratios/denominators, category change over time, properly explained prior-period comparisons, truthful evidence drilldown, and export/meeting-ready presentation.

## 10. Backend/API fit and recommendations

### Current fit

- Authorization and school scoping are appropriate: router and endpoint dependencies require `school_admin`, `_filters` validates school-owned IDs, and `_query` repeats the school predicate.
- The uncommitted `dimension_key` additions are the correct general direction. Integer IDs and controlled duty/category-type/date keys are minimal safe keys for authorized drilldown.
- The events endpoint has enough safe labels for a first evidence table and correctly excludes notes/private fields.
- Breakdown rows need category `type`, and optionally stable context metadata, so the UI can label and style them without guessing.
- Breakdown ordering must move into the API for stable pagination/rendering and consistent clients.
- Matrix output is technically bounded and allow-listed, but API-ish labels are passed through unchanged. The UI must localize dimension/value labels; the API can additionally return display metadata/selected measure without becoming presentation-specific.
- Matrix `truncation` is sufficient but currently ignored by the UI.
- Matrix/event click-through is not complete for `subject_group` and `date_bucket`. Either events must accept equivalent safe filters or those matrix cells must not claim drilldown.
- Student improvement/worsening needs independent ordering/limits and a documented minimum-volume rule.
- Existing backend tests cover access, safe events, matrix limits, representative dimensions, date locality, and privacy, but do not assert the new `dimension_key` fields or that each key round-trips into the matching events request.

### Add `GET /api/school/reports/behaviour/filter-options`

**Recommendation: yes, add it in S23d.** Client-side inference from current configuration/assignment metadata would be misleading because report activity is event-time data and may include historical classes/categories or actors outside the current teacher-membership list.

Required contract:

- `school_admin` only, with the same explicit `X-School-Id` membership enforcement.
- Accept the current shared report filters: effective date bounds, branch, grade, class, subject/group, duty, category/type, actor, and student.
- Be school-scoped, unreversed, and date-bounded exactly like report queries.
- Compute faceted options from matching report activity. When calculating one facet, ignore that facet’s own selected value while honoring the others, so a selected value does not erase all alternatives.
- Return only bounded safe options, for example `{ key/id, label, type?, status?, matching_event_count? }`.
- Return branches, grades, class sections, subjects/subject groups, duty contexts, categories, staff actors, and a bounded student search result.
- For students, require a query or an already selected student, enforce a small server limit (for example 20), and return only key + display name + optional safe class label. Do not return an unbounded school roster.
- Include normalized `effective_filters`, selected-option validity, and an `empty_reason`/availability signal so “All” never hides a failed/empty facet.
- Include historical/inactive options only when matching activity requires them, visibly flagged for display.
- Use deterministic option ordering (school sort order where meaningful, otherwise localized label; activity-ranked student/actor search where useful).
- Never return emails, external references, birth dates, gender, notes, tokens, hashes, FHH/guardian data, storage keys/paths, raw ORM objects, or unrestricted student/staff lists.
- Be side-effect free. It must not seed categories or commit on GET.

The endpoint can return all non-student facets in one bounded response after each applied filter change. Student search can be the same endpoint with `student_search` and `student_limit`, or a dedicated subordinate endpoint with identical guards.

## 11. i18n audit

- Automated English/Arabic parity passes: 967 keys in both locales.
- Navigation and core filter/metric/section labels have translations.
- Dimension selectors use translated labels, but the preset buttons interpolate raw API keys, exposing `class_section`, `category_type`, and `duty_context`.
- Matrix value labels can expose raw `needs_work`, duty keys, and backend fallback text.
- Missing strings include effective period, quick ranges, active filters, remove/clear-one, sort explanations, row drilldown affordance, no-options reasons, no event rows, matrix truncation, selected measure, comparison-period wording, category badges, inactive/historic labels, and zero-data coverage.
- “Deep Dive” / “استكشاف متعمق” is understandable but still technical. A leadership-facing label such as “Explore patterns” / “استكشاف الأنماط” is more approachable, with the matrix mechanics described secondarily.
- “Bounded server-side aggregates for leadership exploration” is implementation language and should not be user-facing. Replace it with the management question the feature answers.
- English/Arabic report additions are formatted as long comma-separated single lines after `teacherUsageGuardrail`; reformat them into normal object properties for maintainability.
- Context labels should never fall back to raw `context_type`; add localized General/Class/Subject/Duty labels.
- Date/number formatting should follow the selected application locale and direction, not only the browser default.

## 12. Recommended correction slices

### S23c-fix1 — blockers before commit

- Fix teacher usage row normalization/name rendering.
- Replace ad hoc `filter`/`matrixFilter` with typed filter and drilldown context functions.
- Make summary rows open events with the correct applied filter and show active chips/effective date range.
- Make matrix cells apply both axes; disable unsupported drilldowns; fix `category_type` assignment.
- Render the selected matrix measure and its ordering; render truncation.
- Add deterministic server ordering/tie-breakers to every breakdown and support/teacher list.
- Return category type in category breakdown rows and add subtle badges.
- Clear/reject subject+duty combinations in the UI before requests.
- Add correct empty events state and pagination wording.
- Replace every raw preset/value label with i18n labels.
- Reformat/split the reports page into typed maintainable components.
- Add focused backend contract tests for new dimension keys and round-trip filters plus focused frontend interaction tests if the existing test setup supports them.

### S23d — filter-options endpoint and smarter cascading

- Implement the side-effect-free, bounded `filter-options` endpoint.
- Add branch/campus and contextual options for every facet.
- Add safe bounded activity-aware student search.
- Preserve valid selections, clear invalid ones with an explanation, and distinguish no options from load failure.
- Cover teacher↔grade/class/subject/category/duty, subject↔teacher/class/grade/student, duty↔teacher/category/student/grade, and student↔subject/class/teacher/category/duty cascades.
- Add tenancy, privacy, range, bound, historic-option, and incompatible-filter tests.

### S23e — better drilldown and profiles

- Add dedicated student, subject, class/grade, duty, category, and staff activity profiles/drawers.
- Give improving/worsening views explicit current/prior periods, independent ranking, and minimum-volume thresholds.
- Add zero/low recording coverage using appropriate denominators without calling it teacher performance.
- Add shareable/query-string report state and reliable back/reset behavior.
- Add data-quality views for unattributed event-time context.

### S23f — visual polish, charts, export, and data quality

- Add the accessible trend chart and compact comparison bars.
- Apply CHH card hierarchy, badges, responsive ranked cards, and polished empty/loading/error states.
- Add print/export only through explicit safe aggregate/event columns and bounded server generation.
- Add realistic demo fixtures and visual/mobile/RTL verification.
- Review query plans and option endpoint limits against realistic volume.

## 13. Exact files likely to change

### Frontend

- `frontend/src/routes/school/reports/+page.svelte`
- `frontend/src/routes/+layout.svelte` (active state only)
- `frontend/src/routes/school/+page.svelte` (active state/shortcut copy only)
- `frontend/src/lib/i18n/messages.ts`
- Likely new components under `frontend/src/lib/components/reports/`, such as filter bar, active chips, metric cards, ranked comparison, trend, matrix, and event drilldown
- Likely a typed report API/state module under `frontend/src/lib/` if that matches repository conventions
- Existing frontend e2e/spec files, or a focused new reports spec under `frontend/e2e/`

### Backend

- `backend/app/routes/school_reports.py`
- `backend/tests/test_school_reports.py`
- Possibly a dedicated report schema/service module if endpoint logic outgrows the route file
- No model or migration change is required for these UI corrections unless later query-plan evidence justifies one

### Explicitly not expected

- `frontend/src/routes/parent/+page.svelte`
- Any guardian/FHH route
- `backend/app/routes/integrations_fhh.py`
- FHH payload schemas or guardian data models

## 14. Validation performed

| Check | Result |
|---|---|
| `git status -sb` | Completed; five uncommitted implementation areas identified before this document |
| `git diff --stat` | Completed; tracked implementation diff reviewed; untracked reports route inspected separately |
| `git diff --check` | Pass |
| `npm run check` | Pass: 0 errors, 0 warnings |
| `npm run check:i18n` | Pass: 967 English and Arabic keys |
| `npm run build` | Pass; local static output only, no service restart/deploy |
| Safe route smoke | `http://127.0.0.1:5173/school/reports` returned HTTP 200 from the existing frontend service |
| Unauthorized API smoke | `/api/school/reports/behaviour/overview` returned HTTP 401 without credentials |
| Authenticated/live filter smoke | Not run: current category metadata GET can seed/commit categories, so doing so could mutate DB and breach the audit rules |
| Backend test suites | Not run, per scope |
| Database mutation/migration | None |
| Service rebuild/restart | None; `npm run build` generated local artifacts only |

Static code tracing verified the category-type cascade, grade-section mapping, broad teacher/subject behavior, drilldown handlers, matrix presets, and admin-only link conditions. It also established why the remaining authenticated manual checklist cannot be truthfully marked passed without either a read-only fixture or a side-effect-free options endpoint.

## 15. Final recommendation

S23c has a sound protected route and a useful backend reporting foundation, but the current UI can display blank teacher identities, silently widen matrix drilldowns, hide its effective period, and present unexplained/arbitrary ordering. Those are trust and usability blockers for management reporting, not optional polish.

Complete **S23c-fix1** before creating the S23c commit. Then implement contextual facets in S23d rather than attempting to infer report activity from unrelated current metadata.

**DO NOT COMMIT S23c YET**

# S24a: Quick Behaviour Award UX Audit and Implementation Plan

## Executive summary

The current teacher class/subject page has the right roster and context data but does not make student cards actionable. Awarding points requires opening a separate Points modal, choosing one or more students, choosing a behaviour type and category, then submitting. This is materially more than the required common path of `tap student -> tap behaviour`.

Implement school-wide quick actions as metadata on the existing `BehaviourCategory` records: `is_quick_action` plus `quick_action_order`. This reuses the same category IDs that awards and management reports already use, keeps configuration school-scoped, avoids a second configuration universe, and allows active non-quick categories to populate Other automatically. The teacher quick-award overlay should continue to call the existing `POST /api/teach/behaviour/events` endpoint with a single student and the page-derived context.

## Current-state findings

### Teacher and class UX

- `frontend/src/routes/teach/assignments/[id]/+page.svelte` loads an assignment and its active roster from `GET /api/teach/assignments/{id}`. It renders each student as an `article` avatar card. The card has no click or keyboard action, so tapping an avatar currently does nothing.
- The same page has a Points action card that opens `pointsModalOpen`. The modal requires: open Points, choose student(s), choose positive/needs-work, choose a category from a select, optionally enter a note, then Save. Typical single-student use is at least five deliberate interactions after reaching the page; batch selection is intentionally supported but is not a fast per-child flow.
- The assignment page already constructs award context safely: a `subject_group` assignment posts `context_type: subject` and `subject_group_id`; a homeroom/class assignment posts `context_type: class` and `class_section_id`.
- `frontend/src/routes/teach/+page.svelte` has a separate duty/global “find students” modal. It searches students, supports multiple selections, requires a duty-context select and category select, and posts `context_type: duty` with `duty_context`. It is not an avatar-card class/subject flow.
- Existing responsive modal conventions are sound and reusable: fixed backdrop, bottom-sheet presentation on small screens, centred rounded dialog from `sm` upward, scrollable content, `role="dialog"`, `aria-modal`, and an in-flight save guard.
- The existing assignment page refreshes its full detail payload after a successful award to update point totals. That is correct but could make the quick flow feel slow; the quick overlay should close after a successful event, update the selected student's total from the returned `points_delta` optimistically, and reconcile via the normal detail refresh without blocking the next award.

### Behaviour backend and model

- `backend/app/models_school/models.py` defines school-scoped `BehaviourCategory` rows with `type` (`positive` or `needs_work`), signed `points_value`, `sort_order`, and `active`. It has type/sign constraints, a per-school/type/label uniqueness constraint, and an index on `(school_id, active, type, sort_order)`.
- `backend/app/behaviour_service.py` returns categories ordered by type, sort order, then label. Active-only category retrieval is already used for teachers; school admins can retrieve inactive rows too.
- `POST /api/teach/behaviour/events` in `backend/app/routes/behaviour.py` validates a maximum of 40 de-duplicated students, active same-school category and students, and exact context combinations. `create_events` then validates an active teacher membership; class/subject target availability, assignment, and roster membership; and writes events using the selected existing category ID and category point value.
- Class, subject, duty, and general context are already first-class event data. Class/subject are assignment-authorised; duty requires only active teacher membership, valid duty context, and active same-school students. General is valid when no context fields are supplied.
- Existing category management is school-admin-only. `GET /api/school/behaviour/categories` currently calls `seed_default_categories` and commits, so it is a read-shaped endpoint with a mutation side effect; S24 implementation should not add similar side effects to teacher quick-action reads.
- There is no behaviour-event reversal route exposed to teachers and no event idempotency key/unique constraint. The frontend has a generic `submitGuard` utility whose own comments correctly state that it cannot prevent concurrent scripted requests.

### School admin UI and localisation

- The Behaviour & points tab in `frontend/src/routes/school/+page.svelte` already lists positive and needs-work categories separately, creates categories, edits label/point value/sort order/active status, and shows inactive rows struck through. It is the correct home for quick-action configuration.
- The UI uses a single global `saving`, `error`, and `notice` pattern and lazy-loads behaviour categories when the tab is opened. Extend this table rather than introducing a separate school settings screen.
- English and Arabic message trees are co-located in `frontend/src/lib/i18n/messages.ts`; both have existing `school.behaviour` and `teach.points` keys. New quick-award and quick-configuration strings must be added in both locales.
- The realistic demo seeder already uses existing active behaviour categories and does not need a second category source. It should assign quick metadata deliberately once the field exists.

## Recommended architecture

Choose option A: add fields to `BehaviourCategory`.

```text
behaviour_categories
  is_quick_action       boolean, non-null, default false
  quick_action_order    integer, nullable
```

Why this is preferred over a `school_behaviour_quick_actions` table:

- Each category is already school-owned, typed, active/inactive, ordered, and uniquely identifies the reporting category.
- The proposed fields express only one property of that category: whether it appears in a school's quick list and where. A join/configuration table would duplicate type checks, require cleanup on category lifecycle changes, and make Other queries more complex without supporting an S24 requirement.
- Category type naturally creates separate positive and needs-work quick lists. `quick_action_order` is only meaningful when `is_quick_action` is true.
- Deactivating a category automatically excludes it from the teacher query. Its quick flag may remain for a future reactivation, avoiding broken references. The admin payload can show it as inactive/quick for correction, but it must not count toward active quick limits.

Keep the existing general category `sort_order` for administration and Other ordering. Use `quick_action_order` only to order selected quick buttons. Do not add a new event type, category table, or quick-action history flag: an event remains a normal event against its existing `BehaviourCategory` ID.

Recommended operational limits: minimum zero and maximum six active quick actions per type (allowing a school with a smaller taxonomy). Six remains scannable in a two-column dialog and comfortably fits common mobile sheets. Limit enforcement must be server-side and client-side.

## Recommended teacher UX

### Class and subject assignment pages

1. Make the full student avatar card a semantic `button`, retaining the avatar, name, and point total. Its accessible name should identify the child and the action, for example, “Award behaviour to Samir Ahmed”.
2. On tap/click, open a lightweight quick-award overlay for that one student. Load quick actions once per school/assignment page (ideally when the assignment detail loads); if unavailable, show an error/retry state rather than silently offering incomplete categories.
3. Header: student avatar/name, current points total, and a small context caption derived by the page, such as the class name or subject plus class. Teachers do not select or edit this context.
4. Body: two labelled columns on desktop, Positive in green and Needs work in amber/red. On narrow screens, retain two visually distinct stacked sections rather than compressing buttons below a safe tap target.
5. Every action button shows the category label and signed point value (`+1`, `+2`, `-1`). A final Other button appears in each type section whenever active non-quick categories of that type exist.
6. Tapping a quick action immediately calls the existing event endpoint with `student_ids: [student.id]`, the standard category ID, `note: null`, `school_id`, and the page-derived class/subject context. This is exactly two user taps from a roster: avatar, behaviour.
7. Lock all action buttons synchronously before dispatching the request; show a compact in-button saving state, not a confirmation dialog. On success, update the card total by the returned event delta, announce success in an `aria-live` region/toast, and close the overlay. Closing is recommended so the roster is immediately ready for the next child. Do not force a full-page reload before dismissal; refresh/reconcile in the background.
8. On failure, retain the overlay, re-enable actions, and display a clear inline error. Do not optimistically adjust totals until a successful response.
9. Tapping Other replaces or expands only that type's quick button set with its remaining active categories; include a Back-to-quick control. This makes uncommon awards three taps total while preserving the two-tap common path. Other must exclude active quick categories to avoid duplication.

### Duty and general contexts

S24d should implement the avatar flow on the class/subject assignment roster only. The global duty search UI does not currently render class cards and needs a duty-context selection before a context-safe award can be made. Preserve its existing batch modal unchanged in S24d.

For a later duty quick flow, context must be selected or persisted before a student tap. The quick overlay may then reuse the same component with `context_type: duty` and the already-selected duty value. A general-context variant can do the same with no context fields. Never infer a duty context from a student's class or from a quick category.

### Mistake handling

There is no existing teacher undo route or recent-event management UI. Do not add an unreviewed correction workflow to the initial fast path. S24e should assess a short-lived, actor-authorised reversal endpoint only if product requires it; it must use `reversed_at`, `reversed_by_user_id`, and an audit entry. Until then, success feedback should state the category and signed points so a mistake is obvious immediately.

## Backend and API plan

### Category payload and queries

Extend `category_payload` with:

```json
{
  "id": 42,
  "type": "positive",
  "label": "Great effort",
  "points_value": 1,
  "sort_order": 60,
  "active": true,
  "is_quick_action": true,
  "quick_action_order": 2
}
```

Add a pure `quick_categories(db, school_id)` service helper that returns only active quick categories, ordered by `type`, `quick_action_order`, `sort_order`, and label. It must not seed, commit, or mutate data.

### Teacher endpoint

Add `GET /api/teach/behaviour/quick-actions?school_id={school_id}`.

- Authentication: current user plus `active_teacher_membership`; suspended schools and non-teachers receive the same 403 posture as existing teacher category access.
- School scope: `school_id` is required and all rows filter by it.
- Response:

```json
{
  "quick_actions": {
    "positive": [{ "id": 42, "label": "Great effort", "points_value": 1 }],
    "needs_work": [{ "id": 61, "label": "Not listening", "points_value": -1 }]
  }
}
```

- Prefer also returning active `other_actions` grouped by type in this endpoint so opening Other is local and never creates a third-tap loading wait. If payload size is a concern, category counts are small and the complete active taxonomy is already fetched by the current teacher modal; return both groups now:

```json
{
  "quick_actions": { "positive": [], "needs_work": [] },
  "other_actions": { "positive": [], "needs_work": [] }
}
```

No new award endpoint is needed. Reuse `POST /api/teach/behaviour/events`; its category, school, teacher, student, assignment/roster, and context checks are the correct enforcement boundary. The UI must not assume quick metadata grants an award permission.

### Admin configuration

Use the existing category endpoints rather than a separate quick-actions resource.

- `POST /api/school/behaviour/categories` accepts optional `is_quick_action` and `quick_action_order`; new categories default to not quick.
- `PATCH /api/school/behaviour/categories/{category_id}` accepts those same fields, with existing label/value/order/active controls.
- Add a focused batch endpoint for reliable ordering and limit validation: `PUT /api/school/behaviour/quick-actions`.

Request:

```json
{
  "positive_category_ids": [42, 44, 45],
  "needs_work_category_ids": [61, 62]
}
```

Response: the complete category payload list or grouped quick lists after update.

The batch endpoint is preferred for the reorder UI because it applies both columns atomically, derives orders by array index, clears quick status/order for omitted same-school categories, and avoids transient duplicate/limit states from several PATCH requests. Single-category PATCH remains useful for a simple toggle on a category form but must enforce the same rules.

Validation and error handling:

- Require `school_admin`; use membership school scope only, never a body/header school ID.
- IDs must be unique within and across lists, belong to the admin's school, be active, and match the specified type.
- Reject more than six IDs per type with 422; reject missing/foreign/inactive/type-mismatched IDs with 400 or 422 consistently with the existing route style; return 404 only where the resource itself is absent in school scope.
- Run query/update in one transaction, audit `behaviour.quick_actions.updated` with submitted IDs and resulting order, then commit.
- When a category is patched inactive, it must be excluded from quick teacher payload immediately. Recommended: preserve quick fields but ensure inactive categories do not count toward active limit; alternatively clear quick fields in the same patch for a cleaner admin state. Prefer clearing them, and audit that automatic removal, so reactivation is intentional.

### Duplicate protection

S24d must use one `submitting` state synchronously set before the network call and disable every quick/Other button plus backdrop-close while saving. It should use the project's `submitGuard` only if its cooldown semantics fit a quick repeat workflow; otherwise local modal state is sufficient for accidental double taps.

The existing API intentionally accepts two concurrent equivalent requests. Do not claim the client lock is a security/idempotency guarantee. S24e should decide whether to add an optional `Idempotency-Key` for one-student quick awards, with a short server-side request ledger or another durable strategy. A timestamp-based unique constraint would be unsafe because legitimate repeated awards are permitted.

## Database and migration plan

Create a new Alembic revision after the current head, `a9b0c1d2e3f4` at audit time.

1. Add `is_quick_action BOOLEAN NOT NULL DEFAULT false` to `behaviour_categories`.
2. Add nullable `quick_action_order INTEGER`.
3. Add a check constraint: `NOT is_quick_action OR quick_action_order IS NOT NULL`. Do not require null order when non-quick because a single category PATCH can first unflag it; application writes should clear stale orders.
4. Add an index matching the teacher fetch: `(school_id, active, is_quick_action, type, quick_action_order, sort_order)`. Retain the existing category list index for Other/admin views.
5. Downgrade drops the index/constraint/columns in reverse order, following repository Alembic conventions and SQLite-compatible handling where needed.

Backfill strategy: new fields default to false/null, making the migration safe and non-disruptive. In the same migration, set sensible defaults only for active rows that match the existing standard default labels, using type-specific ordered mappings, capped at six each. This gives established schools an immediately usable quick path without creating new category rows or changing historic events. Unknown/custom schools remain at zero quick actions and see an explicit empty quick state directing their admin to configure them; do not silently select arbitrary categories by sort order.

Initial default mapping proposal:

- Positive: Listening well, Good work, Teamwork, Helping others, Kindness, Great effort.
- Needs work: Not listening, Disrupting others, Unkind behaviour, Unsafe behaviour, Off-task, Not following instructions.

The migration must update only categories that exist, are active, match the exact school/type/label, and are not already intentionally configured. The schema addition is what lets the seeder set explicit quick metadata for demo schools. Update `backend/scripts/seed_realistic_demo_school.py` and its tests to ensure its active standard categories have the intended ordered quick defaults. Do not execute the seeder as part of implementation verification.

## Frontend implementation plan

### Teacher side

Likely files:

- `frontend/src/routes/teach/assignments/[id]/+page.svelte`: load/cache quick action payload for its assignment school; change student cards to buttons; maintain selected student/modal state; derive the existing class/subject event context; submit through the current event endpoint; update point total; retain the existing batch Points modal as an advanced/bulk path.
- New `frontend/src/lib/components/QuickBehaviourAwardModal.svelte` (recommended): encapsulate focus management, student/context header, grouped actions, Other expansion, submit/error/success/live state, and mobile sheet presentation. Accept a student, context payload, school ID, quick/other category data, and `onawarded`/close callbacks. Avoid duplicating this UI later for duty flow.
- `frontend/src/lib/i18n/messages.ts`: English and Arabic quick-award text, Other/Back, context cues, saving and error/success statements, no-quick-configured fallback, and accessible button labels.

Load category data when assignment detail is loaded or in parallel with it, not on avatar tap, so the overlay appears immediately. Cache it only in the current page instance and invalidate/reload after a returned category error or a page revisit; cross-school data must never be shared in a global unkeyed cache.

Accessibility/mobile specifics:

- Use a real button for every card and action; support Enter/Space naturally.
- Move focus into the dialog on open, return it to the initiating student button after close, support Escape when not saving, and expose errors/success via `aria-live`.
- Keep 44px minimum targets, visible focus rings, and non-colour labels/headings for positive versus needs-work.
- Use a two-column grid from a suitable small/tablet breakpoint and a stacked sheet on narrow mobile. Do not force horizontal scrolling or hide values.

### Admin side

Likely files:

- `frontend/src/routes/school/+page.svelte`: add a “Quick actions” control to active category rows, clear visible status for inactive rows, and a per-type ordering UI. Prefer checkbox/select-to-add plus move-up/move-down controls in S24c over introducing drag-and-drop dependency/complexity. Render a “selected quick actions” ordered list above all categories for each type.
- `frontend/src/lib/i18n/messages.ts`: both language entries for quick toggle, selected list, ordering controls, limit, inactive warning, saved/error messages, and empty-state guidance.

Admin interaction: choose active categories in each type, arrange them with keyboard-accessible move controls, and save both arrays using the batch endpoint. Allow removing an item from the quick list without deleting or deactivating it. The ordinary category form continues to manage label, signed points, order, and active state.

## Data and reporting impact

- Every quick award writes the exact existing `BehaviourCategory.id`; management category/report queries and their indexes continue to operate unchanged.
- `context_type`, `class_section_id`, `subject_group_id`, and `duty_context` retain the S22a validation and persistence path. The overlay receives context from its caller; it does not derive or alter it.
- `is_quick_action` and `quick_action_order` are present-day configuration only. They must not be copied to `BehaviourEvent`, included as a reporting dimension, or alter historical reports.
- The feature uses school, teacher, roster, and category data only. It neither reads nor exposes FHH private/home data. Teacher quick-action response payloads must contain only the category fields needed to award.

## Tests to propose

### Backend

- Admin can configure ordered positive and needs-work quick lists and retrieve correct category payload metadata.
- Teacher fetch returns only active quick categories and active non-quick Other categories, grouped and correctly ordered.
- Teacher/non-admin cannot configure lists; unauthenticated and inactive/suspended memberships are blocked.
- A configured category must belong to the admin school, be active, have the correct type, and appear at most once; cross-school IDs are blocked without data leakage.
- Six-per-type limit and ordering are enforced transactionally; remove/reset behaviour is correct.
- Deactivating a configured category removes it from teacher quick results and does not leave it in Other.
- Existing event endpoint records the chosen quick category ID and signed value with class, subject, duty, and general contexts unchanged; existing roster/assignment/cross-school checks still pass.
- Client/API duplicate strategy is explicitly tested once selected: immediate duplicate action is blocked in the UI; any introduced idempotency key has same-key replay and different-key legitimate-repeat coverage.
- Existing reporting tests confirm category aggregates and context-filtered reports still include quick-created normal events.

### Frontend/manual

- Tapping/clicking a roster student avatar opens the overlay with the correct child and class/subject caption.
- A positive quick action awards once, updates visible total, gives success feedback, and closes to the roster.
- A needs-work quick action behaves identically with a negative value.
- Other shows only remaining active same-type categories, and awarding one preserves context.
- All action buttons are disabled during submit; rapid double tap cannot send two browser requests.
- Error retains the modal and permits retry; empty quick configuration has an understandable fallback.
- Keyboard focus, Escape, focus restoration, screen-reader labels/live messages, and RTL Arabic layout are verified.
- Small mobile sheet and desktop two-column layout have usable tap targets and no clipped buttons.
- Admin can choose, order, remove, deactivate, and save quick actions; English/Arabic i18n parity is checked.

## Risks and adoption guardrails

- Preserve the two-tap common path. No notes, confirmation prompt, category type toggle, or context picker may appear between avatar tap and quick-button tap.
- Keep existing batch award UI available for intentional whole-class/multi-student awards; replacing it outright would regress a valid workflow.
- Do not fetch categories only after the avatar tap if avoidable; overlay latency undermines perceived speed.
- Do not let missing admin configuration produce an empty, dead dialog. Show a short configured-by-admin message and retain a clear path to the existing full category/batch workflow until defaults are configured.
- Context correctness is more important than speed: class/subject must use assignment-derived IDs; duty/general must be explicit caller modes.
- Use colours as reinforcement only: text headings, signed values, and iconography must distinguish columns.
- No user-visible undo is promised until a secure, auditable reversal endpoint is designed.

## Implementation slices

### S24a: audit and plan

Completed by this document. No application, migration, seed, or runtime changes.

### S24b: backend quick-action configuration

- Add model fields, Alembic migration, payload/helper/query changes, admin batch and category PATCH validation, teacher quick-actions endpoint, audit logging, and focused backend tests.
- Do not run migrations or seeders until explicitly approved for the implementation slice.

### S24c: admin quick-action configuration UI

- Extend the existing Behaviour & points tab with per-type selection/order/remove controls and complete English/Arabic text.
- Add frontend checks/manual QA for limits, inactive states, and save errors.

### S24d: teacher quick-award overlay

- Add reusable overlay, cached category data, actionable roster avatar cards, two-tap class/subject award wiring, client submit lock, accessible/mobile presentation, point-total update, and manual/component coverage.
- Retain batch Points and duty-search award flows.

### S24e: polish and operational review

- Apply explicit demo quick defaults in the realistic demo seeder/tests, review category-empty fallback, mobile/RTL polish, duplicate-submit behaviour, and decide whether an audited undo/idempotency enhancement is required.

## Final recommendation

**APPROVE IMPLEMENTATION PLAN**

The existing category/event architecture supports this feature without changing the reporting category universe or weakening context authorisation. The recommended category-field design is the smallest safe schema change, and reuse of the current award endpoint limits behavioural risk while achieving the required two-tap teacher path.

## S25w implemented extension: Message guardians

The teacher Quick Award context now includes a guarded `Message guardians` shortcut.
It deliberately reuses the existing messaging recipient lookup, idempotent
student-conversation creation, protected thread/composer, and authorization policy.
The originating assignment/student/mode are carried through a same-origin validated
return target, so back or a successful send restores Quick Award without altering
award state. No messaging backend or schema extension was needed.

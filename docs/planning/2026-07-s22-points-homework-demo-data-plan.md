# S22 Points, Homework Completion, and Demo Data Plan

**Status:** planning recommendation only
**Date:** 2026-07-12
**Decision:** no reports, schema changes, seed execution, or production-data changes in this pass

## 1. Current state summary

### CHH points

- `behaviour_events` stores school, student, category, awarding `actor_user_id`, signed `points_delta`, optional note, a broad `source` (`teacher`, `admin`, or `correction`), timestamps, and reversal metadata.
- It does **not** store `class_section_id`, `subject_group_id`, subject, duty context, or a controlled event context.
- Both award entry points call the same `POST /api/teach/behaviour/events` request. The assignment roster page knows whether its target is a class section or subject group, but currently sends only school, students, category, and note. The global student search (the duty flow) sends the same shape and therefore loses the fact that it was a duty award.
- `create_events()` checks active teacher membership, school/category/student scope, but cannot validate a target because no target is supplied. It creates `source="teacher"` for both flows.
- The CHH guardian points helpers expose category, signed points, note, staff/teacher display name, and date. They do not expose subject or duty context.
- The FHH integration dashboard exposes an allow-listed point shape with `staff_display_name` and `class_section_name`. The latter is the linked student's **current** section snapshot, not the event-time award context.
- Existing default categories include duty-relevant labels such as Safe play, Helping at break, Wandering halls, and Out of bounds. Category text alone is not a reliable duty dimension because the same category can occur in several settings.

### CHH homework

- `homework_items` already targets exactly one class section or subject group and has due date, resources, attachments, status, and author.
- CHH guardians can mark and unmark homework through browser-to-CHH guardian endpoints.
- `homework_item_completions` is unique by `(homework_item_id, guardian_user_id)`. It has no `student_id`, reporting channel, FHH link identity, or revocation history. For an item visible to several linked children, this is a guardian-level preference rather than an unambiguous child completion.
- Teachers can create/read their assigned homework, but have no student completion summary.
- The FHH integration bundle currently returns every visible item as `done: false`, an empty completed list, and `can_mark_homework_done: false`. There is no FHH write-back route yet.

### FHH current state

The FHH checkout was inspected over the private host at `10.250.50.1:/opt/apps/family-hero-hub`. FHH stores one active `SchoolConnection` per child/provider, including the CHH remote link ID and per-link token server-side. The browser calls only FHH's child-scoped routes. `school_connections.py` family-scopes the child, the `ChhIntegrationClient` makes service-to-service calls, and `sanitize_dashboard()` rebuilds all nested CHH data from a closed-world allowlist. The school page already renders the safe staff and class context in the point log. Homework remains read-only.

### Existing demo tooling

- `backend/scripts/demo_teacher_assignment_coverage.py` is dry-run by default and idempotently fills assignment gaps for the United International School slug.
- It is not a broad realistic-data seeder and does not create point patterns, homework, announcements, updates/photos, or calendar data.
- `docs/DEMO_DATA.md` documents this limited purpose and warns against using it as a real-school workflow.

## 2. Point subject-context recommendation

Add nullable event-time target foreign keys to `behaviour_events`:

- `class_section_id -> class_sections.id`
- `subject_group_id -> subject_groups.id`

Use a database check allowing zero or one target, never both. A subject-group award records `subject_group_id`; its subject and containing class section are resolved through `SubjectGroup.subject_id` and `SubjectGroup.class_section_id`. A homeroom award records `class_section_id` and has no subject. Do not infer a subject from the awarding teacher because a teacher can have several assignments.

The assignment page must send its known target. CHH must treat it as an authorization claim, not trusted display metadata:

1. Confirm the target belongs to the submitted school and is active.
2. Confirm the actor has a current assignment to that target.
3. Confirm every student is on the target roster using existing roster rules, including default subject enrolment policies.
4. Persist the validated target on every created event.

Payload builders should join `SubjectGroup -> Subject` and emit only:

- `subject_name`
- `subject_code`
- event-time `class_section_name`

Do not expose `subject_group_id`, `subject_id`, `class_section_id`, or actor IDs to parent/FHH point payloads. Names and codes are display/report dimensions; internal IDs remain server-side.

For historical consistency, the foreign keys preserve the event-time relationship, but later renaming a subject or section will change its displayed name. This is acceptable for S22a. If immutable historical labels become a regulatory/reporting requirement, add explicit snapshots later rather than prematurely duplicating names now.

## 3. Duty and unstructured-time recommendation

Add nullable `duty_context` to `behaviour_events` with a closed database/API vocabulary:

- `break`
- `lunch`
- `playground`
- `hallway`
- `assembly`
- `bus`
- `general_duty`

The UI may render these as Break, Lunch, Playground, Hallway, Assembly, Bus, and General duty. Do not store arbitrary free text in this field. The existing optional note remains the place for a concise incident explanation.

Add a controlled `context_type` column with `class`, `subject`, `duty`, or `general`, or derive it from the target/duty columns. **Recommendation: persist it** because it gives report queries a stable indexed dimension and avoids interpreting null combinations repeatedly. Enforce these combinations:

- `subject`: `subject_group_id` set; section target and duty null.
- `class`: `class_section_id` set; subject target and duty null.
- `duty`: `duty_context` set; both assignment targets null.
- `general`: all three nullable context fields null.

Keep `source` for actor/workflow provenance; do not overload it with subject/duty semantics. Index `(school_id, context_type, duty_context, created_at)` and retain the existing student chronology index. Future reports can then compare classroom (`class` + `subject`) with unstructured (`duty`) events and group by student, category, current class/year, duty context, and actor without parsing notes.

The global search award modal should include an optional controlled duty selector, defaulting to `general_duty` when opened from the explicit duty action. A separate truly general award can submit `context_type=general`. The backend must reject duty context from an assignment-page request and reject assignment targets from a duty request.

Fair interpretation matters: reports should show counts and signed totals alongside exposure/time period and context. “Awarded by” is an audit/filter dimension, not a teacher-bias ranking. Never infer bias from raw award counts without assignment/duty coverage and opportunity denominators.

## 4. Safe point payload and display

Recommended parent/FHH event allowlist:

```json
{
  "id": 123,
  "created_at": "2026-07-12T08:15:00Z",
  "points_delta": -1,
  "category_label": "Wandering halls",
  "category_type": "needs_work",
  "note": "Returned to class after reminder",
  "staff_display_name": "Ms Taylor",
  "class_section_name": "Grade 6 A",
  "subject_name": null,
  "subject_code": null,
  "duty_context": "hallway",
  "context_type": "duty"
}
```

`context_type` and `duty_context` must be serialized from enums/allowlists, never from arbitrary model data. Keep closed-world sanitization at both boundaries: CHH constructs a purpose-built response and FHH reconstructs an independently allow-listed DTO before returning to its browser. Staff email, actor/staff IDs, model dumps, hashes/tokens, debug values, storage keys, and raw paths remain forbidden.

Display order:

1. Date/time, signed points, category, and optional note.
2. Staff display name.
3. If subject exists, show subject name (optionally code) and class section when both exist.
4. Otherwise show duty label when present.
5. Otherwise show class section when present.
6. If none exist, show only staff/date context; do not invent “General” unless `context_type=general` was explicitly stored.

The FHH browser must continue calling FHH only. FHH backend fetches CHH server-to-server and sanitizes the response.

## 5. Homework completion/write-back recommendation

### Product semantics

Use the wording **Marked done** or **Reported complete**, never “submitted”, “checked”, “verified”, or “graded”. A parent marking work done is useful self-reporting, not evidence that a teacher received or assessed it.

Parent marking is a core requirement because a child may have no account or device. The action belongs on the linked child's FHH school homework view and must not require a child session.

### Durable completion model

Do not create a fake CHH guardian, staff user, or shadow email account. Make completion student-scoped and preserve its reporting identity. Recommended replacement model (name illustrative: `homework_student_completions`):

- `id`
- `school_id` (required)
- `homework_item_id` (required)
- `student_id` (required)
- `status` (`marked_done`; extensible later only by migration)
- `reported_via` (`chh_guardian`, `fhh_parent`; later `student` or `staff` only if explicitly designed)
- `reported_by_guardian_user_id` nullable FK
- `fhh_link_id` nullable FK
- `marked_done_at`
- `revoked_at` nullable
- optional `revoked_via`/reporter references if undo ships

Enforce exactly one reporter identity for the two current channels and one active completion per `(homework_item_id, student_id)`, preferably with a partial unique index where `revoked_at IS NULL`. Validate that item, student, and link are in the same school and that the item audience includes that student at action time.

This corrects the current guardian-keyed ambiguity and means two parents see the same child state rather than producing competing completion rows. Existing guardian completion rows need an explicit migration policy in S23: map only where the guardian/item audience resolves to exactly one linked eligible child; quarantine or retain ambiguous legacy rows for reviewed backfill rather than guessing.

### Server-to-server flow

1. Parent presses Mark done in FHH for one linked child and item.
2. Browser calls an authenticated, child-family-scoped FHH endpoint only.
3. FHH resolves the active school connection and calls CHH with the service credential plus per-link token.
4. CHH validates active link, school/student scope, and homework audience; it upserts the active completion using `fhh_link_id` and the link's `student_id`.
5. CHH writes an audit entry without parent PII and returns a small allow-listed state (`homework_item_id`, `marked_done`, `marked_done_at`, `reported_via`).
6. FHH sanitizes the response, updates its view, and refreshes/reconciles the bundle.

Recommended CHH routes:

- `PUT /api/integrations/fhh/links/{link_id}/homework/{item_id}/completion`
- `DELETE /api/integrations/fhh/links/{link_id}/homework/{item_id}/completion` if undo is included

Use idempotent `PUT`, not a create-only `POST`: retries after mesh timeouts must not duplicate marks. The dashboard must compute completion for the linked student and set `can_mark_homework_done: true` only when write-back is configured and authorized.

### MVP undo decision

Recommend **mark and undo** in S23a because CHH already presents a reversible guardian toggle and accidental taps are realistic. Undo should soft-revoke the active row, not delete history. If S23a must be reduced, mark-done-only is safe but the UI must clearly say it cannot yet be undone; do not silently omit correction semantics.

## 6. Visibility and future reporting

### Parent/FHH

- See only completion state for the linked child and homework items within that child's audience.
- No sibling state unless that sibling has a separately authorized link/view.
- Show who reported it only as friendly channel text if needed (“Marked done in Family Hero Hub”), never expose FHH link/internal IDs.

### Teacher (S23b)

For homework they are authorized to manage, teachers should see eligible-student denominator, marked-done count/rate, and a roster list with `marked_done_at` and reporting channel. Clearly label missing marks as “Not marked done”, not “Incomplete”. Apply the same assignment and roster authorization used for the homework item; teachers must not query unrelated students.

### Management/principal (S24)

School-authorized summaries may group by class, subject, homework item, author/teacher, and student support pattern. Rates require a stable denominator: students eligible for the item's audience at the chosen reporting cutoff. Define whether transfers use assignment-time, due-time, or current enrolment before reports ship; recommended default is eligibility at due time, falling back to creation time when there is no due date.

Reports should answer low marked-complete patterns, not assert non-completion. Include minimum sample sizes and both numerator/denominator. Student-level detail is restricted to authorized school staff; other families/students never receive it.

## 7. Realistic demo-data seeder design

Create a dedicated script, proposed as `backend/scripts/seed_realistic_demo_school.py`, separate from assignment coverage. It must be dry-run by default and require all of the following to write:

- `--apply`
- `APP_ENV=development` (exact normalized match)
- `DEMO_SEED_CONFIRM=united-international-school`
- database production detection must also fail closed (for example, reject known production environment markers even if the other variables were mistakenly set)

Target `School.slug == "united-international-school"` and require exactly one row whose normalized name is also `United International School`. Abort on zero, duplicates, name mismatch, suspended school, missing current academic year, or unexpected target structure. Never accept a numeric school ID alone.

The script must not call HTTP routes, mailers, invite/token generation, push/WhatsApp providers, or notification jobs. It must not create/change auth credentials, emails, memberships, guardian/FHH links, token hashes, or secrets. Use a transaction, print a deterministic plan, and roll back on any validation error.

### Idempotency

Use a stable namespace such as `s22-demo-v1` and deterministic natural keys. Prefer a small `demo_seed_records` manifest table only if provenance cannot be represented safely without schema overhead; otherwise use stable, unique content titles/codes and deterministic timestamps plus existence checks. Behaviour events lack a natural unique key, so the robust recommendation is an optional nullable `demo_seed_key` with a unique constraint, or a dedicated manifest keyed by `(seed_namespace, entity_type, entity_key)`. Do not use note text as identity.

Re-running should report `created`, `already_present`, `updated_safe_fields`, and `skipped` counts. It may update only records previously owned by the same demo namespace, never similarly named manual data. No blanket delete/reset mode. A future cleanup command, if added, must remove only manifest-owned rows and remain development-guarded.

### Dataset shape

Use deterministic relative dates anchored by `--as-of YYYY-MM-DD` (default today) so the next-30-day calendar stays useful. Seed enough data for distributions rather than a few screenshots:

- Several active classes/year groups and at least 20-30 existing demo students across them; do not fabricate identities if the target structure is missing.
- Several existing demo teachers with valid assignments.
- English, Maths, Science, and at least two additional subjects across subject groups.
- Roughly 6-10 behaviour events per selected student over 6-8 weeks, mixed signs, teachers, subjects, classes, and days.
- Duty events across break, lunch, hallway, playground, and assembly.
- A named deterministic persona with English positives and Maths needs-work events.
- A persona strong in class but with repeated break/hallway needs-work events.
- A persona strong in Maths but with Homework incomplete/Forgot equipment patterns and, after S23, low marked-done homework.
- One class with a clearly positive distribution and one with more needs-work events, without making every child identical.
- Homework across class and subject audiences, varied due dates (recent past and next 14 days), resources only where local/safe.
- Announcements at school/class/subject scope.
- Updates with generic school-safe photos.
- Calendar events spread across the next 30 days (test, trip, reminder, civvies/charity where appropriate).

Use fixed persona keys, not assumptions about a real child's first name. Resolve an existing demo student deterministically and document the mapping in dry-run output. Do not seed homework completions until the student-scoped S23 schema exists; afterwards create only `reported_via=demo` if that controlled channel is deliberately added, never impersonate a guardian or FHH link.

## 8. Demo photos: sourcing, storage, licensing

- Never hotlink. Store verified files under the existing protected update upload root using normal storage-key conventions and create matching `UpdatePhoto` metadata.
- Prefer locally generated neutral placeholders if network/licence verification is unavailable.
- If downloading, use Wikimedia Commons file description pages as the source of truth and accept only clearly compatible public-domain or Creative Commons licences. Record creator, work title, source page URL, direct file URL, licence/version, retrieval date, required attribution text, SHA-256, and local filename in `docs/demo-assets/ATTRIBUTION.md`.
- Avoid identifiable children and personal data. Use books, classroom supplies, art materials, sports/playground equipment, library shelves, robotics components, or a generic science setup.
- Validate declared MIME type, decoded image format, pixel dimensions, file size, and hash before storage. Reject SVG/HTML/polyglot content and unknown licensing.
- The seeder itself should consume a reviewed local asset manifest. A separate opt-in download/preparation utility may fetch assets; normal seeding must not require internet access.

## 9. Required schema changes

### S22a

- `behaviour_events.class_section_id` nullable FK/index.
- `behaviour_events.subject_group_id` nullable FK/index.
- `behaviour_events.context_type` required controlled value, backfilled as `general` for legacy rows.
- `behaviour_events.duty_context` nullable controlled value.
- Check constraints for valid target/context combinations.
- Optional demo provenance table/key should be decided with S22b, not mixed into the point API migration unless selected.

### S23a

- Student-scoped homework completion model with reporter channel/identity, timestamps, soft revocation, and active uniqueness.
- Migration/backfill strategy for current guardian-keyed rows; never infer a child when more than one is eligible.
- Audit action support for FHH mark and undo.

No reporting aggregate tables are recommended yet. Begin with normalized event/completion data and appropriate indexes; introduce snapshots/materialized aggregates only after report query and scale evidence.

## 10. Exact CHH files likely to change

S22a:

- `backend/app/models_school/models.py`
- `backend/app/models_school/__init__.py`
- new `alembic/versions/*_add_behaviour_event_context.py`
- `backend/app/routes/behaviour.py`
- `backend/app/behaviour_service.py`
- `backend/app/routes/guardian.py`
- `backend/app/routes/integrations_fhh.py`
- `frontend/src/routes/teach/+page.svelte`
- `frontend/src/routes/teach/assignments/[id]/+page.svelte`
- `frontend/src/routes/parent/+page.svelte`
- relevant `frontend/src/lib/i18n/*` locale files (confirm actual locale paths during implementation)
- `backend/tests/test_behaviour_points.py`
- `backend/tests/test_guardian_dashboard.py`
- `backend/tests/test_integrations_fhh.py`

S22b:

- new `backend/scripts/seed_realistic_demo_school.py`
- possibly new `backend/scripts/demo_assets_manifest.json`
- possibly new provenance migration/model if the manifest-table approach is chosen
- `backend/tests/test_demo_data_seeder.py`
- `docs/DEMO_DATA.md`
- new `docs/demo-assets/ATTRIBUTION.md`
- reviewed local demo assets under the configured protected demo/update upload staging path, not public static hotlinks

S23a/S23b:

- `backend/app/models_school/models.py`
- `backend/app/models_school/__init__.py`
- new homework completion migration
- `backend/app/routes/homework.py`
- `backend/app/routes/integrations_fhh.py`
- `backend/app/school_scope.py` if a reusable explicit-student audience helper is extracted
- `frontend/src/routes/parent/+page.svelte`
- `frontend/src/routes/teach/+page.svelte`
- `backend/tests/test_homework.py` (create if tests are currently elsewhere)
- `backend/tests/test_integrations_fhh.py`
- teacher/guardian frontend tests where available

## 11. Exact FHH files likely to change

Verified FHH paths at `10.250.50.1:/opt/apps/family-hero-hub`:

- `backend/app/routes/school_connections.py`: extend `sanitize_dashboard()` for controlled point context; add family-scoped homework completion PUT/DELETE proxy routes.
- `backend/app/services/chh_integration_client.py`: add CHH completion PUT/DELETE methods using service and stored per-link credentials.
- `backend/tests/test_school_connections.py`: pin family scope, strict nested allowlist, safe errors, idempotent action behavior, and absence of credential leakage.
- `backend/tests/test_chh_integration_client.py`: pin method/path/body/header behavior without exposing secrets.
- `frontend/src/routes/school-link/[id]/+page.svelte`: render subject/class/duty context and Mark done/Undo controls, action loading/error state, and refresh/reconciliation.
- `frontend/src/lib/i18n/messages.ts`: add matching English and Arabic context/completion wording.
- `backend/app/models.py` and an FHH migration are **not required** for the recommended MVP because CHH is authoritative and the existing `SchoolConnection` already carries the server-side link identity. Add cached completion state only with a demonstrated offline/cache requirement.
- `frontend/src/lib/api.ts` should not require a change if the existing generic `api.put`/`api.delete` methods cover the action; confirm during implementation.

FHH must keep `sanitize_dashboard()` as a closed-world reconstruction and must never pass through arbitrary CHH JSON.

## 12. Tests needed

### Points

- Migration/backfill sets legacy events to controlled `general` context.
- Subject assignment award persists validated group and resolves subject name/code and section.
- Homeroom award persists section with null subject.
- Duty award persists only an allowed duty value.
- Invalid context values/combinations fail at API and DB levels.
- Teacher cannot spoof another assignment, school, or out-of-roster student.
- Batch award gives every event the same validated context.
- Guardian and FHH responses include only the safe fields, preserve ordering/sign, and exclude emails/internal IDs/storage/token/debug fields.
- FHH event section is event context, not silently substituted current enrolment.
- Reversal totals and filtering continue to work.
- Query-count/performance check avoids per-event subject/section lookups.
- FHH sanitizer drops unknown injected fields and rejects/normalizes unknown enum values.

### Homework

- Completion is per item and student, shared consistently across authorized reporters.
- A parent linked to siblings cannot mark the wrong child's item.
- FHH link/token/school/student/audience mismatch returns generic 404 and writes nothing.
- Idempotent repeated PUT creates one active completion.
- Undo soft-revokes; retry is idempotent; remark creates/re-activates according to the chosen audit policy.
- Revoked FHH links cannot read/write; service token alone is insufficient.
- FHH browser route enforces family ownership and never exposes CHH credentials.
- Dashboard active/completed lists and permission flag reflect the linked student's state.
- Teacher summary denominator and roster authorization are correct for class and subject audiences.
- Legacy backfill handles zero/one/multiple eligible children without guessing.

### Seeder

- Dry-run performs no commit.
- Missing any guard aborts before mutation.
- Production marker overrides confirmation and aborts.
- Wrong/ambiguous school aborts.
- Second run creates no duplicates and reports existing owned records.
- Similar manual records are not modified.
- External messaging/auth/token functions are never called.
- Transaction rollback leaves no partial dataset after a forced failure.
- Relative dates, pattern invariants, context distribution, and cross-school isolation are deterministic.
- Asset manifest rejects missing attribution, unapproved licence, wrong MIME, unsafe format, or hash mismatch.

## 13. Manual QA checklist

- Award from an English subject roster; CHH parent and FHH show English plus class and safe staff name.
- Award from a Maths roster; confirm it is distinguishable from English in both logs.
- Award from a homeroom roster; show class but no fabricated subject.
- Award through duty search for Break and Hallway; show the correct friendly duty label.
- Award a general event; show staff/date without a misleading duty/subject.
- Move a demo student to another current section and confirm old events do not acquire the new section context.
- Inspect browser network on FHH: no request goes directly to CHH and no CHH link/service token is present.
- Inspect JSON for forbidden emails, staff/internal IDs, hashes, storage keys, raw paths, and unknown passthrough fields.
- From FHH, mark one linked child's homework done; verify only that child's state changes in CHH.
- Undo and remark; verify soft history/audit and idempotency.
- Confirm wording says Marked done/Reported complete, not submitted/checked/graded.
- Confirm a teacher sees only assigned homework completion summaries and “Not marked done” wording.
- Run the future seeder without flags, with one missing flag, and against a non-development environment; all must refuse to write.
- Run dry-run twice and applied seeding twice in an isolated development DB; the second applied run creates no duplicate junk.
- Verify each photo is local/protected, generic, face-free, correctly licensed, and represented in attribution docs.

## 14. Recommended slice split

### S22a: point subject and duty context

Model/migration, validated creation context, guardian/FHH allow-listed payloads, CHH/FHH display, and focused tests. Do this before realistic behaviour seeding so demo events use the final dimensions.

### S22b: guarded realistic demo data seeder

Dry-run/apply guards, provenance/idempotency, deterministic behaviour/content patterns, reviewed local assets, docs, and isolated tests. Exclude homework completion rows until S23's child-scoped schema lands.

### S23a: FHH parent homework completion/write-back

Student-scoped completion schema and legacy policy, CHH integration PUT/DELETE, FHH family-scoped proxy/action UI, audit, allowlists, and tests. Parent action does not require a child device/account.

### S23b: teacher homework completion visibility

Authorized per-item counts/rates and roster detail with careful “marked done” language and correct eligibility denominator.

### S24: reporting foundations

Subject/class versus duty pattern queries and homework marked-complete summaries for authorized management. First define time windows, exposure/eligibility denominators, transfer handling, minimum samples, and fair teacher interpretation. Do not build reports from free text or current-section substitution.

## 15. Decision summary

- Store validated event-time class/subject targets plus controlled duty/context dimensions on each behaviour event.
- Keep `source` as provenance and do not infer subject or duty from teacher/category/note.
- Make homework completion per child and item, with FHH link as a real reporter identity, no phantom CHH user.
- Prefer idempotent mark plus soft-revocable undo and label it as reported/marked done.
- Build the realistic seeder only after S22a, dry-run by default, multiply guarded, namespace-owned, deterministic, and incapable of messaging or auth mutation.
- Defer all reports to S24 after the dimensions and completion semantics are trustworthy.

# S22b Demo Seeder Implementation Shape

**Status:** planning recommendation only  
**Date:** 2026-07-12  
**Scope:** inspect-only pass; no data mutation, no seeder execution, no commit/push/merge/tag

## 1. Existing setup-data inventory

United International School is present exactly once in the dev database:

| Item | Value |
| --- | --- |
| School | `United International School` |
| Slug | `united-international-school` |
| School status | `pending_setup` |
| Suspended | no |
| Current academic year | `2026-27` / `2026/27` |

Current structure available for demo generation:

- 3 branches total: `ALK` active, `BOU` active, `MAIN` archived.
- 14 grade levels: `KG1` through `G12`.
- 32 class sections.
- 14 subjects.
- 261 subject groups.
- 68 active teacher memberships.
- 284 staff assignments.
- 502 active students.
- 503 member enrolments.
- 32 behaviour categories.

Subject coverage is sufficient for the requested demo mix:

- English, Maths, Science, Arabic, Art, ICT, PE, Tajweed, Social Studies, and Global Perspectives all exist.
- Core subjects have broad group coverage.
- The school has enough classes, teachers, and students to create multiple personas without inventing new structure.

## 2. Existing manual activity counts

These are the small amount of manual test records already in the school. They are **not** the target demo dataset and should not be treated as such.

| Table | Count | Notes |
| --- | ---: | --- |
| `behaviour_events` | 95 | All existing events are general/manual test activity at the moment. |
| `announcements` | 16 | Mix of school, class, and subject announcements. |
| `homework_items` | 8 | 7 active, 1 archived. |
| `update_posts` | 4 | Manual update posts only. |
| `update_photos` | 4 | Matching manual photos. |
| `calendar_events` | 1 | Single manual calendar entry. |

Current behaviour event context is not yet a demo dataset:

- `context_type=general` for all 95 existing behaviour events.
- No existing point history should be repurposed as the seeded demo narrative.

## 3. Feasibility

Yes. There are enough existing classes, teachers, subjects, students, and subject groups to generate a realistic demo layer.

The main reason this is feasible:

- 502 students is enough for many distinct award patterns.
- 32 sections and 261 groups are enough to vary class, subject, and duty context.
- 68 active teacher memberships give enough actor diversity.
- The current manual activity layer is small enough to leave in place and layer the demo dataset on top.

## 4. Proposed script path

Recommended seeder script:

- `backend/scripts/seed_realistic_demo_school.py`

Keep it separate from `backend/scripts/demo_teacher_assignment_coverage.py`.

## 5. Proposed guard checks

The seeder should fail closed unless all of the following are true:

- `APP_ENV=development`
- `DEMO_SEED_CONFIRM=united-international-school`
- `--apply` is supplied for any write path
- the target school resolves to exactly one row
- the school slug is exactly `united-international-school`
- the normalized school name is exactly `United International School`
- the school is not suspended
- the current academic year exists and is unambiguous
- any production/runtime marker check fails closed if the database or environment looks non-development

The script should also abort if:

- the school row is missing
- the school row is duplicated through an unexpected data anomaly
- the slug/name pair does not match the expected target
- the current academic year is absent
- the script would need to invent missing structure instead of using existing setup data

The script must not:

- send emails
- create invites
- create magic links
- send notifications
- call WhatsApp integrations
- mutate auth credentials or tokens
- change guardian/FHH links
- change FHH link ownership or child linkage
- touch Bob or any other already-linked child used for FHH testing

## 6. Proposed idempotency strategy

Recommendation: use a dedicated manifest table, not note text, as the primary idempotency mechanism.

Proposed manifest shape:

- `demo_seed_records`
- keyed by `(seed_namespace, entity_type, entity_key)`
- stores the created model id, seed version, timestamps, and ownership metadata

Why this is preferred:

- Behaviour events do not have a natural unique key.
- Updates, announcements, homework, calendar events, and photos all benefit from explicit ownership tracking.
- A manifest is safer than trying to infer ownership from titles or notes.
- It avoids overwriting similar manual data that already exists.

Natural keys can still be used where they are genuinely stable, but they are not enough on their own for the full dataset.

Recommended namespace:

- `s22-demo-v1`

Rerun behavior:

- `created`
- `already_present`
- `updated_safe_fields`
- `skipped`

The seeder should never do a blanket delete/reset.

## 7. Manifest decision

Answer: **yes, a manifest table is needed**.

Reason:

- The point-event layer needs durable ownership across reruns.
- `demo_seed_key` on existing tables would spread provenance logic into multiple business tables and would still need special handling for photos and bulk-generated events.
- A dedicated manifest keeps the implementation explicit and makes cleanup or future extensions safer.

Natural keys are sufficient only for a small subset of records. They are not sufficient for behaviour events.

## 8. Recommended deterministic personas

Do not use Bob Smith as a demo persona. He is already FHH-linked and should remain protected.

Recommended personas should resolve by stable student IDs and existing school structure, not by guesses about identity:

| Persona | Recommended existing student | Student id | Current section | Purpose |
| --- | --- | ---: | --- | --- |
| English-strong, Maths support | Reem Costa | 53 | `G1 A` | Strong English positives, Maths needs-work, a gentle early-primary narrative. |
| Good in class, slips at break/hallway | Aleena Kruger | 8 | `G4 B` | Good in-class behaviour but repeated duty-context negatives. |
| Strong in Maths, weak on homework/organisation | Ayaan Iqbal | 166 | `G10 B` | Upper-grade organisation pattern with homework/follow-through weaknesses. |

Recommended class anchors:

- Positive-behaviour class: `G1 A`
- Needs-work-heavy class: `G4 B`

These are only recommended anchors. The final script should resolve them deterministically from existing students and sections and should refuse to run if the chosen student is linked or otherwise unsafe.

## 9. Proposed point-event volume and patterns

Recommended behaviour-event volume:

- about 120 to 150 total seeded events
- 8 to 12 focal students with 7 to 10 events each over a 6 to 8 week window
- the remainder spread across many other students so the dataset does not look hand-authored around only a few children

Recommended pattern mix:

- English awards and corrections across subject events
- Maths awards and needs-work events across subject events
- Science subject events for variety
- duty events for `break`, `lunch`, `hallway`, `playground`, and `assembly`
- some general awards, but not enough to dominate the dataset

Persona-specific patterns:

- English-strong persona: more positive English subject events than Maths needs-work events.
- Duty-slip persona: mostly good classroom behaviour, but repeated negative duty-context events at break and hallway.
- Maths-strong persona: stronger Maths and Science positives, but recurring homework incomplete / forgot equipment / organisation-related negatives.
- Positive class: net positive points with visible consistency across multiple teachers.
- Needs-work-heavy class: net negative or near-neutral totals driven by recurring duty and organisation issues.

Distribution guidance:

- mix positive and needs-work categories
- vary actors across several teachers
- vary timestamps across school days and times of day
- keep the timestamps deterministic and anchored to `--as-of YYYY-MM-DD`

## 10. Proposed homework, announcement, update, and calendar volumes

Recommended seeded volumes:

- 12 homework items total
  - roughly half class-section audience
  - roughly half subject-group audience
  - due dates split between recent past and the next 14 days
- 6 announcements total
  - 2 school-wide
  - 2 class-section
  - 2 subject-group
- 5 update posts total
  - each with 1 or more photos
  - local safe assets only
- 8 calendar events total
  - spread across the next 30 days
  - include test, trip, reminder, civvies, and charity variants where appropriate

These counts are intentionally higher than the existing manual layer but still small enough to inspect manually.

## 11. Photo strategy

No hotlinks.

Recommended photo approach:

- use reviewed local placeholder assets only
- or reuse existing safe local demo assets if they already exist
- store them through the protected upload/storage path used by the app
- reference them via a local asset manifest

If a local reviewed asset is not available, the seeder should skip the photo rather than pull anything from the internet.

The seeder itself should not fetch assets from the network.

## 12. Exact files likely to change

Recommended implementation file set:

- `backend/scripts/seed_realistic_demo_school.py`
- `backend/app/models_school/models.py` if the manifest table is modeled in-app
- `backend/app/models_school/__init__.py` if the manifest model needs export wiring
- `alembic/versions/*_add_demo_seed_records.py` or equivalent migration if the manifest table is added
- `backend/tests/test_demo_data_seeder.py`
- `docs/DEMO_DATA.md`
- `docs/planning/2026-07-s22b-demo-seeder-implementation-shape.md`

If the manifest-table design is adopted, there should be no need to change the existing teacher-assignment coverage script.

## 13. Exact tests needed

Recommended focused test file:

- `backend/tests/test_demo_data_seeder.py`

Test cases:

- dry-run does not commit
- `--apply` is required to write
- `APP_ENV=development` is required
- `DEMO_SEED_CONFIRM=united-international-school` is required
- wrong or duplicated school aborts
- suspended school aborts
- missing current academic year aborts
- rerun creates no duplicate junk
- rerun reports owned rows as already present
- manual records that were not seeded are left untouched
- behaviour events get the correct `context_type` and `duty_context` patterns
- local photo manifest validation rejects missing or unsafe assets
- external mail, invite, notification, WhatsApp, auth, and token helpers are never invoked
- forced failure rolls back the transaction cleanly

## 14. Risks

Main risks to call out:

- Existing manual test activity could be mistaken for the new demo dataset unless the manifest ownership is explicit.
- Bob Smith and other linked children must be excluded from persona selection.
- Photos require curated local assets; if those are missing, the seeder must fail closed or skip photos.
- Behaviour events need explicit idempotency support; natural keys alone are not enough.
- The school is currently `pending_setup`, so guards must not incorrectly assume only `active` schools are valid.
- Reruns must not update similarly named manual rows outside the manifest namespace.

## 15. Model recommendation

This implementation can safely use a lower/cheaper model.

Reason:

- The work is a bounded seeder plus a small manifest/migration/test surface.
- The guard conditions are explicit.
- The data patterns are deterministic.
- The main failure mode is missing a guard or idempotency edge, which focused tests can catch.

Use a medium model only if the same pass also expands the manifest/migration/asset-prep work beyond this scoped plan.

## 16. Recommendation

Proceed with S22b implementation using:

- a new guarded demo seeder script
- a dedicated manifest table for provenance/idempotency
- deterministic persona mapping to existing unlinked students
- no internet dependency
- no changes to existing FHH/CHH link data
- local reviewed photos only


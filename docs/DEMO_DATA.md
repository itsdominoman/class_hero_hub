# Demo Data Utilities

`backend/scripts/demo_teacher_assignment_coverage.py` is for generated demo data only.

The script is idempotent and fills teacher assignment gaps for the generated United International School demo school: missing homerooms, missing teacher coverage on default/core subject groups, and demo teacher accounts without assignments.

It should not be used as a real production assignment workflow. Real schools need explicit operational decisions, approvals, and timetable-aware assignment management.

The demo school's default/core subject groups (e.g. `KG1A-ENG`) were created by ad hoc
demo seeding, not by a real admin workflow. `Default subjects` under `/school` (default
subject templates by education stage or grade/year level, plus preview/apply) is the
real workflow schools should use to generate section-specific subject groups; it is
idempotent against the demo data's existing groups (matching on the same deterministic
code), so running it against the demo school reports those groups as already existing
rather than duplicating them.

## S22b realistic activity seeder

`backend/scripts/seed_realistic_demo_school.py` seeds realistic demo activity for
United International School on top of the existing setup data.

Key properties:

- dry-run by default
- writes only with `--apply`
- writes also require `APP_ENV=development`
- writes also require `DEMO_SEED_CONFIRM=united-international-school`
- the target school must resolve to the exact UIS slug/name pair
- the current academic year must exist
- behaviour events are seeded with the S22a event-time context fields
- re-runs use the `demo_seed_records` manifest table for idempotency
- no homework completion rows are seeded yet
- no internet downloads or hotlinked images are used
- if no reviewed local photo asset manifest is present, update photos are skipped cleanly
- Bob Smith and any already-linked students are excluded from persona selection

Dry-run example:

```bash
cd /opt/apps/class_hero_hub
python backend/scripts/seed_realistic_demo_school.py --as-of 2026-07-12
```

Development-only apply example:

```bash
cd /opt/apps/class_hero_hub
APP_ENV=development DEMO_SEED_CONFIRM=united-international-school \
python backend/scripts/seed_realistic_demo_school.py --apply --as-of 2026-07-12
```

The apply form is intentionally guarded and should only be used after review in a
development environment.

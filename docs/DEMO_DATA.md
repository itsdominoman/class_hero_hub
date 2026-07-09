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

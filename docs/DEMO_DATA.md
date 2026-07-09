# Demo Data Utilities

`backend/scripts/demo_teacher_assignment_coverage.py` is for generated demo data only.

The script is idempotent and fills teacher assignment gaps for the generated United International School demo school: missing homerooms, missing teacher coverage on default/core subject groups, and demo teacher accounts without assignments.

It should not be used as a real production assignment workflow. Real schools need explicit operational decisions, approvals, and timetable-aware assignment management.

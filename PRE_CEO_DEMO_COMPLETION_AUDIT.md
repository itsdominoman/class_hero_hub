# CHH/FHH pre-CEO-demo completion audit

Audit date: 2026-08-06  
Mandate source: the original 20-point `/goal` request  
Purpose: distinguish implemented code and automated evidence from a genuinely
demonstrable, deployed and manually accepted CEO journey.

## Executive finding

The original goal is not complete. The checkpoint history contains substantial
backend, schema, test and documentation work, but it does not establish that all
20 requested user journeys are available and accepted in the target environments.

Current deployment truth:

- CHH pilot is deployed at `931eef68cd9566c9f7eed8d97a9474d4006f11ed`.
  Its database is current at `d8e9f0a1b2c3`; backend, frontend, database and
  workers are healthy; public home and readiness endpoints return HTTP 200.
- FHH development is deployed at `97003047bb5d06a58d50658056b98aef15ce33be`.
  Its database is current at `d3e4f5a6b7c8`; all five services are healthy and
  public home/readiness endpoints return HTTP 200. FHH production and the Play
  Store release were not changed.
- CHH contains no Principal, Deputy Principal, HOD or Support Staff membership,
  no department, and no staff-department assignment.
- The deployed CHH frontend now exposes supported staff-role invitations,
  searchable staff, department lifecycle and dated department assignments.
- No `pre-ceo-demo-complete-2026-08-06` final tag exists in either repository.
- No prepared set of live demo credentials, no linked parent journey and no
  completed manual CEO-demo run are recorded.

The original completion standard required server-side enforcement, deployed
cross-system behaviour, prepared accounts, physical English/Arabic and mobile
checks, and a completed runbook journey. On that standard the project cannot be
marked complete.

## Requirement-by-requirement completion state

| # | Requirement | Current truth | Work still required for completion |
|---:|---|---|---|
| 1 | FHH parent dashboard visual parity | The redesigned parent School dashboard and common language control are deployed on FHH development. Automated desktop/mobile/Android-shell fixtures passed. The reported FHH production header and unlinked-parent Survey exposure were not changed because production is outside this development/UAT gate. | Physically verify the development parent dashboard in desktop, mobile browser and Android shell in EN/AR. Before any production promotion, reproduce and fix the production-only header/Survey defects if they remain present. |
| 2 | Demo relationships and accounts | Jason Green remains an active CHH teacher with assignments. The supported staff/department UI is deployed, but CHH still has no Principal, Deputy, HOD, Support Staff, department or dated assignment, and no deterministic linked FHH parent journey is recorded. | The user must supply or select the real invitation identities. Then use the supported UI to provision Principal, Deputy and HOD, create the department/assignment, complete the parent/child link and record the approved demo identities. |
| 3 | Safe seeded-content cleanup | A verified backup and manifest-only cleanup removed 1,041 proven seeded notices, calendar items, homework items and updates while preserving manual data. Ten surveys, 11 conversations and 132 messages were retained because there was no reliable seed provenance. | Visually review the retained demo content. Remove any unwanted retained records only after establishing explicit provenance or obtaining item-level confirmation; do not weaken the existing safety boundary. |
| 4 | Teacher-to-parent messaging restrictions | Server-side assignment and exact-student restrictions are deployed, with focused tests for class, subject, temporary, expired, unrelated and cross-school cases. The live direct-manipulation journey was not executed. | Run bounded live tests for authorised and unauthorised recipient discovery, conversation creation, direct identifiers and attachment sharing. Fix only failures found. |
| 5 | Staff-to-staff messaging | Same-school active-staff discovery and messaging are deployed. The user's basic Teacher Messages check passed. The required notifications, unread state, receipts, attachments, disabled-account, cross-school and mobile cases were not manually accepted. | Execute the remaining bounded staff-message matrix with two staff identities and one disabled/cross-school negative case. |
| 6 | One-time safeguarding acknowledgement | CHH and FHH development persistence, UI and authoritative version lookup are deployed; both databases are current. | Physically verify first display, checkbox/action, persistence across reload/device session, and controlled version-change re-prompt on parent and staff paths. |
| 7 | Search across long lists | CHH gained reusable debounced search for teacher setup and scoped messaging discovery. The original request required an audit across staff, students, parents, classes, subjects, assignments, conversations, reports, certificates and survey recipients; that full UI inventory was not completed. | Inventory each named long-list surface, retain existing adequate search, add missing permission-scoped search where lists are genuinely long, and physically test keyboard/mobile/Arabic behaviour. |
| 8 | Predictable sorting and grouping | Natural education-aware ordering and deterministic setup ordering were added to CHH, with presentation tests. No documented final CHH/FHH list inventory or physical Subject Groups acceptance exists. | Audit the named list families in both apps, verify Subject Groups visually with real data, and correct any remaining creation-order or lexical-grade defects. |
| 9 | Hide infrastructure status from schools | School operations pages and navigation were removed; platform monitoring remains separate. This is deployed. | Perform one school-role direct-route/API denial check and one platform-admin monitoring check, then record acceptance. |
| 10 | Language selector | The opposite-language globe action is deployed in CHH and FHH development. Automated i18n parity and presentation tests passed. | Physically switch EN/AR on CHH and FHH desktop/mobile, confirm route persistence, session persistence, RTL/LTR and no layout collision. |
| 11 | Communication Oversight | The audited, read-only safeguarding review backend is deployed with leadership/HOD scope and a clearly labelled `Communication oversight` navigation/home entry. Existing safeguarding permission boundaries remain intact. | Provision the roles and verify school-wide versus department scope, filters, audit events and read-only behaviour through the live journey. |
| 12 | HOD access | HOD role constants, migration, reporting/oversight enforcement and the staff/department administration frontend are deployed. Live data still has no HOD or department. | Create the department, HOD and dated assignments through the deployed UI; verify assigned-department access and unrelated-department denial through UI and API. |
| 13 | Principal and Deputy Principal access | Backend roles, routing, reporting, messaging, recognition permissions and the school-admin provisioning frontend are deployed. There are still no live Principal or Deputy memberships. | Provision both identities and verify school-wide reports, recognition, staff messaging and oversight while denying setup administration, infrastructure, platform and cross-school access. |
| 14 | School setup navigation hierarchy | The CHH menu hierarchy and visual grouping changes are deployed and covered by presentation tests. The physical desktop/mobile acceptance was not recorded. | Verify the real school menu at desktop and phone widths in EN/AR and correct any weak or crowded hierarchy found. |
| 15 | Student recognition location | Positive Recognition was already in the Behaviour & recognition group and remains there. The user confirmed the live page opens. | No implementation work currently identified; retain it during later navigation changes. |
| 16 | Star of the Week and certificate branding | Branding fields, leadership permissions, certificate/report generation and UI are deployed. UIS currently has an HTTPS logo and `gold` accent configured. No live EN/AR print/PDF acceptance was recorded. | Generate a real positive-recognition certificate, verify browser print and protected PDF in EN/AR, logo/accent appearance, recipient scope and message sharing. |
| 17 | Reporting scope | CHH behaviour overview, filters, trends, student-support lists, staff usage and matrix views are deployed with leadership/HOD scope. Staff context now compares only with the same staff member's equal prior period, requires minimum samples, uses neutral wording, and is suppressed under category filters. | Verify school, Principal/Deputy and department-scoped HOD results with real demo data; confirm low-sample and filtered views suppress the indicator as designed. |
| 18 | CSV and PDF exports | Filter-preserving, audited behaviour CSV/PDF export and UI actions are deployed on CHH. They were rendered locally but not downloaded from the live role journeys. | Download live CSV/PDF under school and scoped management roles, confirm filters, context, EN/AR rendering, formula neutralisation, audit events and access denial. |
| 19 | Share generated items through messaging | CHH report, certificate and aggregate-only survey-summary sharing is deployed. FHH development receives the protected documents through exact-child School Chats. Survey summaries exclude individual free text and identities, are audited and use the staged retention flow. | Send each generated type to the linked demo parent and verify exact-child visibility, download, retention and unauthorised denial on CHH/FHH development. |
| 20 | FHH/CHH avatar alignment | Shared CHH avatars are deployed on FHH development with additive `avatar_catalogue_id`. The legacy `avatar_name` 1-24 API contract is preserved for the existing Play Store app; old and new writes synchronise without rewriting the old field into an unsupported range. | Physically verify old APK display/write behaviour and new development parent/child mappings and fallbacks in EN/AR before any production promotion. |

## Cross-cutting work that remains

### 1. Finish acceptance of CHH product surfaces

- finish the long-list search and deterministic-sorting inventory;
- preserve Positive Recognition and the improved setup hierarchy;
- verify the deployed Staff and Departments and Communication Oversight journeys;
- correct defects found by focused live role testing.

### 2. Accept the paired FHH development work

- verify acknowledgement, protected documents and avatars;
- physically regression-test the existing Play Store APK against the preserved
  legacy avatar/API contract;
- resolve the production mobile-header and unlinked-parent Survey defect before a
  later production promotion if those defects reproduce there.

### 3. Provision and accept the actual demo

- create the Principal, Deputy, HOD, department and dated assignments;
- complete one deterministic parent/child link through the supported invitation;
- record account identities and expected landing pages in the runbook;
- execute the full teacher, parent, Principal/Deputy and HOD journey;
- run focused negative permission checks and physical EN/AR/mobile checks;
- update the result document with observed evidence rather than planned checks;
- create the final tags only after both repositories and the live journey satisfy
  the original completion standard.

## Efficient completion strategy

Do not repeat broad test suites merely to generate another large evidence count.
Reuse the existing passing suites as regression evidence, add focused tests only
for changed or previously untested behaviour, and use the user for bounded
physical checks at explicit gates. A sensible execution order is:

1. Physical CHH/FHH development smoke checks and long-list inventory.
2. Demo identity/relationship provisioning through supported UI.
3. Focused role, permission, document and old-APK regression checks.
4. One complete physical CEO run and evidence update.

The project should not be declared complete at an intermediate code, migration,
container-health or automated-test checkpoint.

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

- CHH pilot is deployed through application commit `7001a16e2d2e`; the server
  worktree is at documentation commit `d2590930562a`. Its database is at
  `c7d8e9f0a1b2` and all five CHH containers are healthy.
- FHH development is deployed only through `02d6965673f5`. Local FHH source is
  at `413e960`; five later commits are not deployed: parent messaging-policy
  acknowledgement, authoritative CHH policy-version lookup, protected generated
  documents, shared CHH avatars, and final browser hardening.
- FHH development remains at database revision `c1d2e3f4a5b6`; its pending
  acknowledgement migration is not applied.
- CHH contains no Principal, Deputy Principal, HOD or Support Staff membership,
  no department, and no staff-department assignment.
- The backend exposes school-admin APIs for staff-role invitations, departments
  and department assignments, but the frontend contains no calls to those APIs.
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
| 1 | FHH parent dashboard visual parity | The redesigned parent School dashboard and common language control are deployed on FHH development at `02d6965`; automated desktop/mobile/Android-shell fixtures passed. No physical acceptance was recorded. The separately reported production mobile header and unlinked-parent Survey exposure remain unresolved. | Physically verify parent desktop, mobile browser and Android shell in EN/AR on the chosen demo environment. Fix the production header and Survey authorisation defect if production will be shown or used. |
| 2 | Demo relationships and accounts | Jason Green remains an active CHH teacher with assignments, but no deterministic linked FHH parent journey was completed. Live CHH has no leadership/HOD identities or departments. The runbook names roles, not usable accounts or credentials. | Add a supported school-admin management UI, provision Principal, Deputy and HOD accounts, create a department and HOD assignment, complete one real invitation/link flow for the demo parent and child, then record usable account identities through the approved credential channel. |
| 3 | Safe seeded-content cleanup | A verified backup and manifest-only cleanup removed 1,041 proven seeded notices, calendar items, homework items and updates while preserving manual data. Ten surveys, 11 conversations and 132 messages were retained because there was no reliable seed provenance. | Visually review the retained demo content. Remove any unwanted retained records only after establishing explicit provenance or obtaining item-level confirmation; do not weaken the existing safety boundary. |
| 4 | Teacher-to-parent messaging restrictions | Server-side assignment and exact-student restrictions are deployed, with focused tests for class, subject, temporary, expired, unrelated and cross-school cases. The live direct-manipulation journey was not executed. | Run bounded live tests for authorised and unauthorised recipient discovery, conversation creation, direct identifiers and attachment sharing. Fix only failures found. |
| 5 | Staff-to-staff messaging | Same-school active-staff discovery and messaging are deployed. The user's basic Teacher Messages check passed. The required notifications, unread state, receipts, attachments, disabled-account, cross-school and mobile cases were not manually accepted. | Execute the remaining bounded staff-message matrix with two staff identities and one disabled/cross-school negative case. |
| 6 | One-time safeguarding acknowledgement | CHH persistence and UI are deployed. Matching FHH commits `bdda9d4` and `35964c4` and migration `d2e3f4a5b6c7` remain local only. | Back up and migrate FHH development, deploy the two commits, then verify first display, checkbox/action, persistence across reload/device session, and version-change re-prompt on parent and staff paths. |
| 7 | Search across long lists | CHH gained reusable debounced search for teacher setup and scoped messaging discovery. The original request required an audit across staff, students, parents, classes, subjects, assignments, conversations, reports, certificates and survey recipients; that full UI inventory was not completed. | Inventory each named long-list surface, retain existing adequate search, add missing permission-scoped search where lists are genuinely long, and physically test keyboard/mobile/Arabic behaviour. |
| 8 | Predictable sorting and grouping | Natural education-aware ordering and deterministic setup ordering were added to CHH, with presentation tests. No documented final CHH/FHH list inventory or physical Subject Groups acceptance exists. | Audit the named list families in both apps, verify Subject Groups visually with real data, and correct any remaining creation-order or lexical-grade defects. |
| 9 | Hide infrastructure status from schools | School operations pages and navigation were removed; platform monitoring remains separate. This is deployed. | Perform one school-role direct-route/API denial check and one platform-admin monitoring check, then record acceptance. |
| 10 | Language selector | The opposite-language globe action is deployed in CHH and FHH development. Automated i18n parity and presentation tests passed. | Physically switch EN/AR on CHH and FHH desktop/mobile, confirm route persistence, session persistence, RTL/LTR and no layout collision. |
| 11 | Communication Oversight | The existing audited, read-only safeguarding review backend was extended for leadership/HOD scope. It is still surfaced through Safeguarding rather than a clearly discoverable Communication Oversight journey, and no leadership/HOD data exists to exercise it. | Add or clarify a discoverable management entry and wording, preserve safeguarding permission boundaries, provision roles, and verify school-wide versus department scope, filters, audit events and read-only behaviour. |
| 12 | HOD access | HOD role constants, migration, reporting scope and oversight enforcement are deployed. No management frontend exists to create the role/department relationship, and live data contains neither HODs nor departments. | Build staff-role and department administration UI; create a department, HOD and dated assignments; verify assigned-department access and unrelated-department denial through UI and API. |
| 13 | Principal and Deputy Principal access | Backend roles, routing, reporting, messaging and recognition permissions are deployed. There are no live Principal or Deputy memberships and no school-admin UI to provision them. | Build the role-management UI, provision both identities and verify school-wide reports, recognition, staff messaging and oversight while denying setup administration, infrastructure, platform and cross-school access. |
| 14 | School setup navigation hierarchy | The CHH menu hierarchy and visual grouping changes are deployed and covered by presentation tests. The physical desktop/mobile acceptance was not recorded. | Verify the real school menu at desktop and phone widths in EN/AR and correct any weak or crowded hierarchy found. |
| 15 | Student recognition location | Positive Recognition was already in the Behaviour & recognition group and remains there. The user confirmed the live page opens. | No implementation work currently identified; retain it during later navigation changes. |
| 16 | Star of the Week and certificate branding | Branding fields, leadership permissions, certificate/report generation and UI are deployed. UIS currently has an HTTPS logo and `gold` accent configured. No live EN/AR print/PDF acceptance was recorded. | Generate a real positive-recognition certificate, verify browser print and protected PDF in EN/AR, logo/accent appearance, recipient scope and message sharing. |
| 17 | Reporting scope | CHH's behaviour overview, filters, trends, student-support lists, staff usage and matrix views are deployed with leadership/HOD backend scope. The promised live role paths are unreachable. The documented immediate gaps for supportive-review indicators, own-baseline/sample-size context and broader recognition/communication summaries were not implemented. | Decide the minimum CEO-visible management overview, implement the remaining explicitly promised neutral indicators/summaries, then verify school, Principal/Deputy and department-scoped HOD results with real demo data. |
| 18 | CSV and PDF exports | Filter-preserving, audited behaviour CSV/PDF export and UI actions are deployed on CHH. They were rendered locally but not downloaded from the live role journeys. | Download live CSV/PDF under school and scoped management roles, confirm filters, context, EN/AR rendering, formula neutralisation, audit events and access denial. |
| 19 | Share generated items through messaging | CHH can stage reports/certificates into Messages. FHH receiving commit `cc15c95` is not deployed, so the required staff-to-parent protected-document journey cannot complete live. | Deploy the FHH receiving work, then send a report/certificate to the linked demo parent and verify exact-child visibility, download, retention and unauthorised denial. Survey-summary sharing was not implemented and should either be completed if needed for the demo or explicitly deferred with the user's agreement. |
| 20 | FHH/CHH avatar alignment | Local FHH commit `434a91a` implements the shared catalogue and deterministic legacy mapping. It is not deployed to development and no APK containing it was built as part of this project. | Deploy to FHH development, verify existing parent/child mappings and fallbacks in EN/AR, then include and physically verify it in the chosen Android demo build if the APK is part of the demonstration. |

## Cross-cutting work that remains

### 1. Complete the missing CHH frontend

Build a school-admin Staff and Departments area using the already deployed APIs:

- list/search active and inactive staff;
- invite Principal, Deputy Principal, HOD and Support Staff roles;
- display each membership role and status;
- create/edit/archive departments;
- assign department heads and members with validity dates;
- close assignments without deleting history;
- expose clear links to reports and Communication Oversight for authorised roles.

This is the largest unimplemented frontend slice and is required before the role
work can be described as a product feature rather than backend capability.

### 2. Finish incomplete CHH product surfaces

- make Communication Oversight discoverable without weakening safeguarding;
- complete the agreed minimum management overview and neutral indicators;
- finish the long-list search and deterministic-sorting inventory;
- preserve Positive Recognition and the improved setup hierarchy;
- correct defects found by focused live role testing.

### 3. Finish and deploy the paired FHH work

- take and verify a fresh FHH development backup;
- apply acknowledgement migration `d2e3f4a5b6c7`;
- deploy local commits through `413e960` in dependency order;
- rebuild/restart only affected FHH development services;
- verify acknowledgement, protected documents and avatars;
- resolve the production mobile-header and unlinked-parent Survey defect before
  production is used in any demonstration.

### 4. Provision and accept the actual demo

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

1. CHH staff/department frontend and leadership provisioning path.
2. CHH oversight/reporting/search completion and focused deployment.
3. FHH development migration/deployment plus the production browser P0 fix.
4. Demo data provisioning and one complete physical CEO run.

The project should not be declared complete at an intermediate code, migration,
container-health or automated-test checkpoint.

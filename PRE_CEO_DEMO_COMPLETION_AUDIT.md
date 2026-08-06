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

- CHH pilot is deployed at product commit `ea8507523c8b6dfc397f88b84289e8aedc95b186`.
  Its database is current at `d8e9f0a1b2c3`; backend, frontend, database and
  workers are healthy; public home and readiness endpoints return HTTP 200.
- FHH development is deployed at `d0121b7014f7442560ddea15ded278f04187118f`.
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
| 1 | FHH parent dashboard visual parity | The redesigned parent School dashboard and common language control are deployed on FHH development. The duplicate School Chats and Surveys destinations were removed from the global desktop/mobile header, restoring logo/title space. The Surveys API returns 404 unless the household has an active same-family CHH-linked child; non-CHH, inactive, revoked and other-family links are excluded. The complete 12-test FHH Survey backend file passes alongside focused frontend/desktop/mobile/Android-shell fixtures and production builds. On 2026-08-07 the user physically accepted the development mobile header and confirmed that an unlinked parent has no Survey entry/direct access. | Physically verify the linked-parent dashboard and Android shell in EN/AR. |
| 2 | Demo relationships and accounts | Jason Green remains an active CHH teacher with assignments. The supported staff/department UI is deployed, but CHH still has no Principal, Deputy, HOD, Support Staff, department or dated assignment. One active development FHH link exists and is synchronised, but its consumed legacy invitation has no guardian-contact reference or recipient identity and it is not the Jason/Green demo relationship; it cannot serve as the deterministic documented demo account. | The user must supply or select the real invitation identities. Then use the supported UI to provision Principal, Deputy and HOD, create the department/assignment, complete the parent/child link and record the approved demo identities. |
| 3 | Safe seeded-content cleanup | A verified backup and manifest-only cleanup removed 1,041 proven seeded notices, calendar items, homework items and updates while preserving manual data. At cleanup time, ten surveys, 11 conversations and 132 messages were retained because there was no reliable seed provenance. Read-only reconciliation found exactly one later ordinary message, so the current total is 133 rather than a cleanup/reseed discrepancy. | Visually review the retained demo content. Remove any unwanted retained records only after establishing explicit provenance or obtaining item-level confirmation; do not weaken the existing safety boundary. |
| 4 | Teacher-to-parent messaging restrictions | Server-side assignment and exact-student restrictions are deployed. After removing local/UTC calendar dependence from the fixtures, isolated current-source tests passed for multiple classes, subject and temporary assignments, expired and unrelated targets, cross-school/revoked resource enumeration, assignment replacement and archived-school handling. The live direct-manipulation journey was not executed. | Run bounded live tests for authorised and unauthorised recipient discovery, conversation creation, direct identifiers and attachment sharing. Fix only failures found. |
| 5 | Staff-to-staff messaging | Same-school active-staff discovery and messaging are deployed. The user's basic Teacher Messages check passed. Current isolated tests passed for same-school staff discovery/creation and cross-school denial. Read-only live reconciliation found two active staff-direct conversations, five active messages, 17 delivered and 18 read receipt events; two staff-direct notification events were provider-accepted and one was correctly cancelled because the recipient had no active device. The required attachment, disabled-account and mobile cases were not manually accepted. | Execute the remaining bounded staff-message matrix with two staff identities and one disabled-account negative case. |
| 6 | One-time safeguarding acknowledgement | CHH and FHH development persistence, UI and authoritative version lookup are deployed; both databases are current. The isolated CHH management-role file and all 25 FHH School Messages proxy tests pass, including user-scoped versioned acknowledgement behaviour. | Physically verify first display, checkbox/action, persistence across reload/device session, and controlled version-change re-prompt on parent and staff paths. |
| 7 | Search across long lists | The full named-surface inventory is documented in `LONG_LIST_SEARCH_AND_SORTING_AUDIT.md`. Shared 250 ms / 2-character search now covers CHH staff, students, class rosters, Subject Groups, report staff and survey recipients; exact numeric identifiers search immediately. Sensitive staff/student searches execute server-side after school/role scoping and cover English/Arabic identity, email/IDs, department, class, grade and subject context. Existing authorised messaging searches were retained. Six presentation tests and two cross-school backend tests pass. The live `G12B` Subject Groups result was accepted by the user; exact numeric student query `1` returned one result; a two-character Arabic student query returned nine results and persisted under RTL; a no-match query showed an explicit zero-result state; and a stale-response guard prevents slower earlier requests from replacing newer results. | Physically verify keyboard and narrow-mobile behaviour on the remaining representative deployed lists. |
| 8 | Predictable sorting and grouping | The full list inventory is documented in `LONG_LIST_SEARCH_AND_SORTING_AUDIT.md`. CHH uses educational grade/class ordering, then subject ordering for Subject Groups, deterministic staff/student ordering, and explicit report/survey ordering. FHH household and school surfaces retain deterministic urgency/activity ordering. The live Subject Groups page showed KG1 A subjects alphabetically before KG1 B, and the user confirmed `G12B` returns the expected nine groups. | Physically verify the remaining representative CHH/FHH lists on narrow mobile and Arabic after deployment. |
| 9 | Hide infrastructure status from schools | School operations pages and navigation were removed; platform monitoring remains separate. This is deployed. | Perform one school-role direct-route/API denial check and one platform-admin monitoring check, then record acceptance. |
| 10 | Language selector | The opposite-language globe action is deployed in CHH and FHH development. Automated i18n parity and presentation tests passed. Live CHH browser acceptance switched the student-search route from English to Arabic without losing `/school/students?search=1`, observed `lang=ar`/`dir=rtl`, and restored English with `lang=en`/`dir=ltr` on the same route. | Physically switch EN/AR on FHH desktop/mobile and the Android shell, and confirm no layout collision; repeat CHH on narrow mobile. |
| 11 | Communication Oversight | The audited, read-only safeguarding review backend is deployed with leadership/HOD scope and a clearly labelled `Communication oversight` navigation/home entry. Existing safeguarding permission boundaries remain intact. | Provision the roles and verify school-wide versus department scope, filters, audit events and read-only behaviour through the live journey. |
| 12 | HOD access | HOD role constants, migration, reporting/oversight enforcement and the staff/department administration frontend are deployed. Live data still has no HOD or department. | Create the department, HOD and dated assignments through the deployed UI; verify assigned-department access and unrelated-department denial through UI and API. |
| 13 | Principal and Deputy Principal access | Backend roles, routing, reporting, messaging, recognition permissions and the school-admin provisioning frontend are deployed. There are still no live Principal or Deputy memberships. | Provision both identities and verify school-wide reports, recognition, staff messaging and oversight while denying setup administration, infrastructure, platform and cross-school access. |
| 14 | School setup navigation hierarchy | The CHH menu hierarchy and visual grouping changes are deployed and covered by presentation tests. The physical desktop/mobile acceptance was not recorded. | Verify the real school menu at desktop and phone widths in EN/AR and correct any weak or crowded hierarchy found. |
| 15 | Student recognition location | Positive Recognition was already in the Behaviour & recognition group and remains there. The user confirmed the live page opens. | No implementation work currently identified; retain it during later navigation changes. |
| 16 | Star of the Week and certificate branding | Branding fields, leadership permissions, certificate/report generation and UI are deployed. UIS currently has an HTTPS logo and `gold` accent configured. All 11 current student-recognition backend tests pass, including positive-only safeguards, role/school scope and certificate generation/branding. No live EN/AR print/PDF acceptance was recorded. | Generate a real positive-recognition certificate, verify browser print and protected PDF in EN/AR, logo/accent appearance, recipient scope and message sharing. |
| 17 | Reporting scope | CHH behaviour overview, filters, trends, student-support lists, staff usage and matrix views are deployed with leadership/HOD scope. Staff context compares only with the same staff member's equal prior period, requires minimum samples and uses neutral wording. The deployed whole-school report loaded with real metrics and the full filter/action set in English. Its live Teacher usage section displayed the equal prior-period range, explicit 20-current/10-prior minimums and the approved `This pattern may warrant a supportive review.` wording without diagnostic labels. Applying a Positive category filter showed that own-baseline indicators were unavailable while filtered, then the default range was restored. Switching to Arabic preserved `/school/reports`, applied RTL and translated the report, filters and PDF/CSV/share actions. | Verify Principal/Deputy and department-scoped HOD results with real demo identities. |
| 18 | CSV and PDF exports | Filter-preserving, audited behaviour CSV/PDF export and UI actions are deployed on CHH. The complete current 10-test report file passed, including filters, cross-school denial, PDF/CSV, rollback safety, matrix limits and time bucketing. Outputs were rendered locally but not downloaded from the live role journeys. | Download live CSV/PDF under school and scoped management roles, confirm filters, context, EN/AR rendering, formula neutralisation, audit events and access denial. |
| 19 | Share generated items through messaging | CHH report, certificate and aggregate-only survey-summary sharing is deployed. The current report suite passed staged message-document creation and rollback safety, and all 19 current CHH survey tests passed, including aggregate-only summary generation/sharing and privacy-safe exports. FHH development receives protected documents through exact-child School Chats; all 25 proxy tests pass, including generated-document metadata and private-field rejection. Survey summaries exclude individual free text and identities, are audited and use the staged retention flow. | Send each generated type to the linked demo parent and verify exact-child visibility, download, retention and unauthorised denial on CHH/FHH development. |
| 20 | FHH/CHH avatar alignment | Shared CHH avatars are deployed on FHH development with additive `avatar_catalogue_id`. The legacy `avatar_name` 1-24 API contract is preserved; old and new writes synchronise without rewriting the old field into an unsupported range. The actual signed production code-16 APK was verified as package `com.familyherohub.app`, version `1.4.7-child-logout`, production API target, correct production signer and stable SHA-256. A static production-to-development API comparison found all 119 production endpoint-decorator signatures retained with only two acknowledgement endpoints added. The current development source re-passed all five backend legacy-contract tests and all four frontend compatibility tests. | Physically install/use the code-16 APK to verify display and legacy writes, then verify new development parent/child mappings and fallbacks in EN/AR before any production promotion. |

## Cross-cutting work that remains

### 1. Finish acceptance of CHH product surfaces

- physically accept the completed long-list search and deterministic-sorting inventory;
- preserve Positive Recognition and the improved setup hierarchy;
- verify the deployed Staff and Departments and Communication Oversight journeys;
- correct defects found by focused live role testing.

### 2. Accept the paired FHH development work

- verify acknowledgement, protected documents and avatars;
- physically regression-test the existing Play Store APK against the preserved
  legacy avatar/API contract;
- physically accept the development mobile-header and unlinked-parent Survey fix
  before the later production promotion.

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

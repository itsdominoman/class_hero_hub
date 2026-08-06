# CHH/FHH pre-CEO-demo audit

Audit date: 2026-08-06  
Target environments: CHH pilot/public (`class.familyherohub.com`, `main`) and FHH development (`dev.familyherohub.com`, `develop`)  
Scope rule: no FHH production work, push or deployment is authorised by this project.

## Verified baseline

| System | Repository HEAD | Tracking state | Database revision | Runtime state |
|---|---|---|---|---|
| CHH | `37f5201bc56abdc04929925281ee95a12a0b313a` | `main` equals `origin/main`; clean | `a2b3c4d5e6f7` | PostgreSQL, backend, frontend, messaging worker and notification scheduler healthy |
| FHH | `85616ee0fcc255ca7198d26447e1a7911724a28c` | `develop` equals `origin/develop`; clean | `c1d2e3f4a5b6` | PostgreSQL, backend, frontend, lifecycle worker and notification worker healthy |

Both repositories have the local annotated tag `pre-ceo-demo-baseline-2026-08-06` at the stated HEAD. CHH messaging and the UIS school messaging policy are enabled; all 14 current UIS entitlements are enabled, and the only jurisdiction-sensitive feature control is voice notes (enabled, control version 2). FHH development school messaging is enabled.

## Architecture traced

- CHH owns school, staff, student, structure, assignments, points, content, reports, recognition, safeguarding and school-side messaging records.
- FHH owns parent, family, child, household, child-session and device-token identity. Protected school reads and messaging are proxied through FHH; FHH clients do not call CHH directly.
- CHH school tenancy is enforced from `X-School-Id`, active membership and same-school resource predicates. Teacher access uses open-ended or date-bounded `staff_assignments` and current rosters.
- CHH membership roles at baseline are only `school_admin` and `teacher`. `StaffAssignment` supports overlapping class/subject assignments and validity intervals but only `homeroom` and `subject` are accepted by the current setup API.
- Messaging uses conversation participants plus provenance-bearing access grants. Teacher access to a student conversation is revalidated against an active assignment and current exact-student roster; expired assignment access is reconciled without deleting authorised history.
- Safeguarding review is a separate, read-only access path with explicit permissions, reason/acknowledgement, time-limited sessions and append-only audit events. It does not impersonate participants or write participant receipts.
- Realistic generated activity is tracked by `demo_seed_records(seed_namespace, entity_type, entity_key, model_name, model_id, metadata_json)`. Current manifests cover 166 announcements, 308 calendar events, 512 homework items, 155 update posts and 10,138 behaviour events. Surveys and messages have no matching manifest evidence and are therefore ambiguous until proven otherwise.
- CHH reports already implement school behaviour overview, trends, class/grade/subject/duty/category breakdowns, student support patterns, teacher usage, a bounded matrix explorer and event drill-down. They are school-admin-only and do not yet export CSV/PDF.
- CHH avatar IDs are the illustrated 31-90 catalogue excluding retired ID 74, with 128/256/512 variants. FHH linked-school views already use its 256px copy, but ordinary FHH family profiles still use a separate 1-24 PNG catalogue.
- Recognition is positive-only, staff-reviewed and printable. Its response contains a placeholder `logo_url: null`; there is no shared school certificate logo/accent setting and no server PDF artefact.
- The FHH parent linked-school route and the child school workspace are separate implementations. The parent route is capable but does not reuse the polished extracted child workspace layout/patterns.

## Requirement-by-requirement state

Status terms: **working**, **incomplete**, **inaccessible**, **missing**, or **blocked by data/architecture**.

| # | Requirement | Baseline state | Evidence, defect or risk | Implementation decision |
|---:|---|---|---|---|
| 1 | FHH parent dashboard parity | **Incomplete** | Parent `/school-link/[id]` has all guardian modules, protected media and responsive states, but it is independently maintained and visually diverges from extracted `ChildSchoolWorkspace`. | Extract/reuse presentation primitives while retaining notices, surveys, chats and guardian actions only for parents. Validate EN/AR, browser and native-safe layout. |
| 2 | Demo relationships/accounts | **Blocked by data/architecture** | Jason Green is active at UIS and has three active assignments (Grade 9 B English, Grade 5 B homeroom and KG 1 A ICT). Prior invitations for two synthetic pupils remain unconsumed; no Jason FHH parent exists. HOD/principal roles do not exist. | Add general leadership/department scopes, then establish one deterministic linked demo family without hard-coded permission exceptions. |
| 3 | Safe seeded cleanup | **Incomplete** | Strong manifest provenance exists for five entity types, but no bounded cleanup utility/report exists. Surveys/messages are ambiguous. | Add dry-run-first cleanup for manifest-linked content only; cascade only rows owned by those manifests. Never delete unmanifested surveys/messages or manual rows. Keep report behaviour events for the management demo unless separately selected. |
| 4 | Teacher-to-parent restriction | **Working** | Recipient discovery returns only students reached through active assignments; conversation creation rechecks the exact student; access grants are school-scoped and revalidated; attachment/message endpoints require current participant access. | Preserve and add explicit multi-class, inactive/historical, URL/API and cross-school regression tests. |
| 5 | Staff-to-staff messaging | **Incomplete** | Discovery returns staff only to admins and `_create_staff_direct` rejects teacher-to-teacher conversations unless one participant is an admin. | Permit every active same-school staff membership to discover/message other active same-school staff; keep disabled/revoked and cross-school records closed. |
| 6 | One-time safeguarding acknowledgement | **Missing** | The notice is remembered only as `localStorage` per account, has no checkbox, server record, timestamp or version and can reappear on another device. FHH mirrors conversation disclosure without a durable policy acknowledgement. | Add versioned CHH acknowledgement records/endpoints for staff and CHH guardians, proxy the same CHH policy/version through FHH, and use a checkbox plus explicit action. |
| 7 | Search long lists | **Incomplete** | Messaging and student administration have search, and oversight has rich filters. `/school?tab=teachers` has no search; several setup/catalogue tables rely on full in-memory lists. | Add a shared accessible debounced query input, starting suggestions at two name characters while allowing immediate exact identifiers. Scope all server searches before matching. |
| 8 | Sorting/grouping | **Incomplete** | Many lists explicitly order, but school structure generically orders by `sort_order, id`; default zero values therefore reproduce creation order. Subject Groups inherits this and can mix educational levels unnaturally. | Add central natural educational ordering and deterministic tie-breakers; expose a relevant sort control only where user choice is useful. |
| 9 | Hide infrastructure status | **Missing/security defect** | `/school/operations` exposes archive disk percentage, backup freshness, worker health, job queues and database pressure to school administrators. | Remove school navigation/access to platform infrastructure. Preserve operational tooling behind platform-admin authority only; retain school-owned retention/policy controls separately if needed. |
| 10 | Language selector | **Incomplete** | Both apps use a two-option select. Locale persistence and direction handling exist, but the required opposite-language globe action is not consistently presented. | Replace both shared selectors with an immediate globe button showing only `العربية` in English and `English` in Arabic; keep route/context and persisted locale. |
| 11 | Communication oversight | **Implemented but poorly discoverable/incomplete role scope** | Safeguarding message review already provides participant/student/class/grade/branch/date/type/direction filters, read-only sessions and audit logging for search/session/view. It is labelled and granted as safeguarding, not discoverable as management Communication Oversight, and has no HOD department scope. | Reuse this hardened path and surface it as Communication Oversight. Add leadership/HOD scope filters server-side; do not create a second message-reading system. |
| 12 | HOD access | **Missing** | No HOD membership role, departments or department assignment model. | Add explicit departments plus validity-bounded staff-department assignments and HOD assignments. Scope reports and oversight by assigned departments. |
| 13 | Principal/deputy access | **Missing** | No leadership roles; management capabilities require `school_admin`. | Add school-wide `principal` and `deputy_principal` roles without platform or infrastructure authority. |
| 14 | Setup navigation hierarchy | **Incomplete polish** | Semantic groups already exist and mobile/desktop share them, but headings use small muted grey styling close to child items. | Strengthen group heading colour, weight, spacing and indentation using the current purple/hero design tokens. |
| 15 | Recognition location | **Working** | Positive recognition is already under the Behaviour & recognition school-menu group, not System & Compliance. Route and entitlement tests exist. | Preserve; update wording/breadcrumb only if needed by the final navigation pass. |
| 16 | Star/certificate branding | **Incomplete** | Positive safeguards and staff confirmation work. Browser print/PDF works, but logo is always null and accent is hard-coded amber. | Add shared, school-configurable certificate logo/accent settings with safe defaults and apply them to EN/AR print output. |
| 17 | Reporting scope | **Working foundation/incomplete roles** | Required behaviour overview, trends, support, staff usage and matrix foundation already exist with neutral warnings. No HOD/leadership scope; recognition/communication summaries are limited. | Extend authorization/scope, add a clean management landing overview, and document pilot-requested broadly useful follow-ups. Do not build generic BI/MIS. |
| 18 | CSV/PDF exports | **Missing for reports** | Student/import CSV export exists; behaviour reports have no export endpoint or action. Certificates rely on browser print. | Add server-authorised, filter-preserving CSV and human-readable PDF for behaviour overview and audit-log generation. |
| 19 | Share generated items | **Missing** | Messaging attachments support protected photos and voice notes, not generated reports/certificates/documents. | Add a narrowly scoped generated-document attachment type and open the existing composer with a secure staged item; no public links or duplicate chat path. |
| 20 | Avatar alignment | **Incomplete** | Linked-school FHH views use CHH IDs/assets, but ordinary child/family profiles use old 1-24 catalogue. | Switch the shared FHH avatar catalogue to CHH IDs, deterministically map legacy selections and use initials if invalid. Remove old assets only after reference and mapping tests pass. |

## Cross-cutting security/privacy findings

1. School infrastructure telemetry is currently exposed too broadly and is Priority 0.
2. Adding leadership roles by treating them as administrators would over-grant setup, deletion and infrastructure access; capability and data scope must be separate.
3. HOD oversight cannot be safely inferred from job title text. It requires explicit, validity-bounded department relationships.
4. Seed cleanup must use manifest foreign identities and model checks. Content signatures alone are insufficient for deletion.
5. The safeguarding disclosure cannot be satisfied by client storage because it is neither durable across devices nor auditable.
6. FHH child sessions remain exact-child and view-only. This project must not expose notices, surveys, chats, siblings or guardian actions to child sessions.
7. Existing authorised conversation history must remain intact when assignments or memberships end; only future access/sending should close according to current grants and lifecycle rules.

## Database and migration plan

No database write or migration was made during this audit. Before the first migration or data deletion, take and verify fresh CHH and FHH development backups. Planned schema changes are limited to:

- CHH leadership/department scope;
- CHH versioned messaging-policy acknowledgement;
- school certificate branding;
- generated-document message attachments and audit evidence where the selected implementation requires it.

FHH should proxy CHH messaging acknowledgement rather than duplicate school policy authority. FHH avatar alignment can retain the existing string column and validate/migrate values deterministically unless database inspection proves a typed column is necessary.

## Small demo-confidence defects deliberately identified

- Teacher setup becomes visually overwhelming and has no search.
- Subject Group ordering inherits creation order when sort orders tie.
- School setup headings are semantically correct but visually weak.
- Infrastructure terminology (archive disk, workers, backup marker, database pool) appears in a school-facing route.
- The language control presents both languages instead of a clear next action.
- Communication review is hidden behind safeguarding terminology even for authorised leadership oversight.
- Certificate branding advertises a logo field in the frontend type but the backend always returns `null`.

## Audit conclusion

The current platform has a credible secure foundation, especially for tenancy, teacher-family messaging and audited conversation review. The pre-demo work should reuse those foundations. The highest-risk implementation is role/department scope; the fastest visible gains are parent dashboard parity, staff chat, durable acknowledgement, infrastructure hiding, consistent language switching, teacher search and natural ordering.

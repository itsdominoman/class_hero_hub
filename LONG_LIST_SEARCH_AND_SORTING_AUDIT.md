# Long-list search and sorting audit

Date: 2026-08-06  
Scope: original requirements 7 and 8 across CHH pilot/development and FHH development  
Rule: permission filtering is authoritative and occurs before or as part of search; a search control must never expand a user's access.

## Shared behaviour

- CHH's shared `EntitySearch` control waits for two characters, except exact numeric identifiers which run immediately, and debounces ordinary input by 250 ms.
- It uses a native search input, supports keyboard submission/clearing, supplies accessible label/help text, and has English and Arabic copy.
- Server-backed CHH staff and student searches escape wildcard characters and keep their existing school/role scope.
- Selected class or Subject Group options remain visible while a query filters the available options.

## CHH inventory

| Named surface | Search decision and fields | Permission boundary | Ordering/grouping |
|---|---|---|---|
| Staff and `/school?tab=teachers` | Server search: exact staff ID/email; English/Arabic name, email, role, department, class, grade, Subject Group and subject. | School-admin school scope; open assignments/departments only. | Localized natural name, then stable ID. |
| Students | Server search: exact student ID/external reference; English/Arabic/preferred name, guardian name/email/reference, class and grade. | School-admin school scope; active guardian contacts and current placements only. | Surname, first name, then ID; paginated. |
| Parents/guardians | There is intentionally no standalone school-wide parent directory. Guardian discovery is through the authorized student record; survey family recipients are searched in the server-supplied audience context. | Linked student/school context only. | Student/family context order from the scoped endpoint. |
| Classes | Shared search on the class-roster selector: ID, code, English/Arabic class, academic year and grade. | School setup context available only to authorized school roles. | Academic year, educational grade rank, then natural class code/name. |
| Subjects | Current pilot list is bounded (14), so the CRUD list remains directly scannable. Subject selectors inherit the sorted setup context. | School setup context only. | Localized subject name, then stable ID. |
| Subject Groups | Shared search on both the existing table and roster selector: ID/code, English/Arabic name, year, class/grade, subject and policy. | School setup context only. | Educational grade, natural class section, subject, then stable ID. |
| Assignments | Staff search above the teaching-assignment context uses the server-backed staff endpoint and assignment fields. | Same school and active/open records only. | Current assignment context, localized natural staff name. |
| Conversations | Existing inbox and compose searches were retained; candidates come from same-school active staff or authorized guardian/student relationships. | Endpoint scope is applied before client filtering; disabled and cross-school identities are excluded. | Most recent activity first with deterministic stable tie-breaks. |
| Reports | Shared staff search plus existing server student autocomplete; report results retain explicit matrix/table ordering and bounded pages. | Role scope is applied by the report endpoint (teacher/HOD/leadership boundaries). | Educational class/grade and explicit metric/category ordering. |
| Certificates/recognition | Pilot review/configuration lists are small and remain directly scannable; no unbounded selector is exposed. | Role-gated recognition endpoints. | Pending/current context first, then deterministic recent activity. |
| Survey recipients | Shared search across server-supplied recipient ID, English/Arabic name and label; selected recipient IDs persist while filtering. | Audience endpoint returns only the current school's eligible classes, grades or linked families. | Server audience order with stable ID fallback; survey list is reverse chronological. |

## FHH development inventory

| Surface | Search/scope decision | Ordering/grouping |
|---|---|---|
| Children/family members | Household-sized cards; no global directory or unbounded selector. | Family-defined display order/stable ID. |
| School messages | Existing search filters an already-authorized household inbox; compose targets derive from active CHH-linked children. | Unread/activity context, then newest conversation activity. |
| Surveys | No cross-school recipient directory exists in FHH. The list is available only with an active CHH connection and separates open, completed and closed responses. | Open action first, then completion/closing chronology and stable title/ID. |
| Rewards/redemptions | Household-scoped lists; no cross-family search surface. | Pending action first, newest pending, then reviewed/resolved history. |
| Avatars | Fixed shared catalogue, not an arbitrary long entity list. | Catalogue numeric/semantic order, with legacy 1–24 IDs retained. |

## Automated evidence

- `frontend/tests/long-list-search-presentation.test.mjs`: six presentation/interaction contract tests.
- `backend/tests/test_students_enrolments.py`: Arabic, guardian, identifier, placement and cross-school-negative search coverage.
- `backend/tests/test_school_management_roles.py`: identity, assignment, department, exact-ID and cross-school-negative staff search coverage.
- Svelte check: zero errors/warnings.
- English/Arabic parity: 2,378 keys in each locale.
- Production frontend build: passed.

## Remaining acceptance gate

After deployment, physically check one representative server-backed list (Students), one setup list (Subject Groups or Class Rosters), one report selector and one survey-recipient selector in English and Arabic at desktop and narrow-mobile width. Confirm keyboard clear/submit, empty state, selected-option retention and that an unauthorized school record cannot appear. This is acceptance work, not missing implementation.

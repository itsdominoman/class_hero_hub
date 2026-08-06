# CHH/FHH role and permission matrix

Policy date: 2026-08-06. This is the target policy for the pre-CEO-demo implementation. Backend enforcement is authoritative; hidden UI alone never grants or removes access.

## Scope vocabulary

- **Platform**: platform administration only; no automatic right to read school conversations, safeguarding content or student records.
- **School-wide**: exactly one active school membership; never cross-school.
- **Department**: staff and school records attributable to one of the HOD's active department assignments.
- **Assigned**: exact active class/subject/temporary assignment and exact active student roster.
- **Linked child**: exact active guardian/household/school/child link.
- **Own child session**: exact FHH child-device session and exact active school connection.
- **Explicit grant**: separately recorded pastoral/safeguarding/oversight authority; never inferred from a broad job title.

Action codes: `V` view, `S` search, `C` create, `E` edit, `D` archive/delete, `X` export, `A` attach/share, `M` message, `O` supervise read-only. A dash means no access. Every action is limited by the scope shown.

## Role definitions

| Role | Default data scope | Important boundary |
|---|---|---|
| Platform administrator | Platform | Manages schools, entitlements and platform operations; school content access needs an explicit audited support process. |
| School administrator | School-wide | School configuration and authorised school management; no platform infrastructure or cross-school access. |
| Principal | School-wide | School-wide management/reporting/oversight; not a platform administrator and not automatically a system/setup owner. |
| Deputy principal | School-wide | Same management visibility as principal for this slice; not platform administration. |
| Head of Department | Department | Only explicit active HOD department assignments and subordinate staff in those departments. |
| Teacher | Assigned | Active teaching relationships only for students/families; may message all active same-school staff. |
| Support staff | School membership plus explicit grants | May message staff. Student/family or oversight access requires a recorded pastoral/safeguarding/administrative grant. |
| Parent/guardian | Linked child | Guardian actions, family messages, notices and surveys for linked children only. |
| Student | Own child session | View-only Updates, Homework, Calendar and Points for that exact linked child. No notices, surveys or school chats. |

## Feature permissions

| Feature | Platform admin | School admin | Principal | Deputy | HOD | Teacher | Support | Parent | Student |
|---|---|---|---|---|---|---|---|---|---|
| Platform schools/entitlements | `V,S,C,E` Platform | — | — | — | — | — | — | — | — |
| Platform health/deploy/storage | `V,S` Platform | — | — | — | — | — | — | — | — |
| School structure/settings | Explicit support only | `V,S,C,E,D` School | `V` School | `V` School | `V` Department context | `V` Assigned | `V` where operationally needed | — | — |
| Staff accounts/roles | Explicit support only | `V,S,C,E,D` School | `V,S` School | `V,S` School | `V,S` Department | `V` own | `V` own | — | — |
| Departments/assignments | Explicit support only | `V,S,C,E,D` School | `V,S` School | `V,S` School | `V,S` Department | `V` own | `V` own | — | — |
| Students/enrolments | Explicit audited support only | `V,S,C,E,D,X` School | `V,S,X` School | `V,S,X` School | `V,S,X` Department | `V,S` Assigned | Explicit grant | `V` Linked child | — |
| Behaviour categories/setup | Explicit support only | `V,S,C,E,D` School | `V,S` School | `V,S` School | `V,S` Department | `V` Assigned | Explicit grant | — | — |
| Award/correct points | — | `V,S,C,E` School | `V,S,C,E` School | `V,S,C,E` School | `V,S,C,E` Department where assigned | `V,S,C,E` Assigned | Explicit grant | `V` Linked child | `V` Own child session |
| Behaviour/points reports | Explicit audited support only | `V,S,X,A` School | `V,S,X,A` School | `V,S,X,A` School | `V,S,X,A` Department | `V` own/assigned operational view only | Explicit grant | `V` Linked child summary | `V` Own child summary |
| Recognition configuration | Explicit support only | `V,S,C,E,D` School | `V,S,E` School | `V,S,E` School | `V,S,E` Department | `V,S,C` nomination/evidence if authorised | Explicit grant | `V` only if explicitly published to linked family | — |
| Recognition review/certificate | Explicit audited support only | `V,S,C,E,X,A` School | `V,S,C,E,X,A` School | `V,S,C,E,X,A` School | `V,S,C,E,X,A` Department | `V,S,C` assigned evidence; confirm only if granted | Explicit grant | `V` shared item | — |
| Notices/updates/homework/calendar | Explicit support only | `V,S,C,E,D,A` School | `V,S,C,E,A` School | `V,S,C,E,A` School | `V,S,C,E,A` Department | `V,S,C,E,A` Assigned | Explicit grant | `V` Linked child; guardian actions where defined | `V` Updates/Homework/Calendar only |
| Surveys | Explicit support only | `V,S,C,E,D,X,A` School | `V,S,C,E,X,A` School | `V,S,C,E,X,A` School | `V,S,X` Department if granted | Target/author access only | Explicit grant | `V,C` Linked child/household response | — |
| Staff-to-staff messaging | Explicit support only | `V,S,C,A,M` School | `V,S,C,A,M` School | `V,S,C,A,M` School | `V,S,C,A,M` School staff directory | `V,S,C,A,M` School staff directory | `V,S,C,A,M` School staff directory | — | — |
| Staff-to-parent messaging | Explicit audited support only | `V,S,C,A,M` School | `V,S,C,A,M` School | `V,S,C,A,M` School | `V,S,C,A,M` Department | `V,S,C,A,M` Assigned | Explicit grant | `V,S,C,A,M` Linked child | — |
| Recipient discovery | Explicit support only | `S` School | `S` School | `S` School | `S` Department families + school staff | `S` Assigned families + school staff | `S` school staff; family only by grant | `S` assigned staff for linked child | — |
| Communication oversight | No default; audited support grant only | `V,S,O,X` School if granted | `V,S,O,X` School | `V,S,O,X` School | `V,S,O,X` Department | — | Explicit safeguarding grant only | — | — |
| Safeguarding case tools | Explicit audited support only | Explicit grant | Explicit grant | Explicit grant | Explicit department grant | Explicit grant | Explicit grant | Participant reporting only where provided | — |
| Generated report/certificate share | — | `X,A,M` School recipient scope | `X,A,M` School | `X,A,M` School | `X,A,M` Department | `A,M` only authorised generated item/recipient | Explicit grant | Receive/download linked item | — |
| Audit logs | Platform audit only | `V,S,X` School security/admin subset | `V,S` management subset | `V,S` management subset | `V,S` Department subset | Own events where surfaced | Own events where surfaced | — | — |

## Messaging rules

1. A teacher may initiate or continue a student-family conversation only while an active assignment reaches that exact active student through a current class or subject roster. Cover/temporary assignments use the same validity interval and do not create a special bypass.
2. Every active staff membership may discover and message every other active staff membership in the same school, regardless of management status. Disabled users, revoked memberships and other schools are excluded.
3. Guardian discovery is a closed world: active exact-child links may discover only currently authorised staff for that child plus explicitly available school administration contacts.
4. Existing authorised history is not silently deleted when a relationship ends. Future visibility/sending follows the access-grant lifecycle and recorded history grants.
5. One eligible family adult receiving or reading is sufficient for delivery/read status. Receipts remain one grey tick, two grey ticks and two blue ticks.
6. Participant messaging, participant receipts/notifications and management review are separate paths. Oversight cannot send, edit, impersonate or silently delete.

## Leadership and HOD enforcement

- `principal` and `deputy_principal` are active school memberships with school-wide management capabilities, not aliases of platform or school administration.
- HOD scope is the intersection of active HOD-department assignments, active staff-department assignments and same-school data. A person may hold overlapping or acting HOD assignments with independent validity dates.
- Teaching assistants, cover teachers and multi-subject/class/branch staff retain explicit overlapping assignments. Nothing in the role model grants unrelated student access merely because a person is staff.
- Branch restriction is additive where a membership/assignment carries one; it can narrow school scope but never widen department or teaching scope.

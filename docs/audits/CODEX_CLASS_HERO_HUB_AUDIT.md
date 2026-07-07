# Class Hero Hub Audit and Product Architecture Report

Date: 2026-06-16  
Repository audited: `/opt/apps/class_hero_hub`  
Public proof-of-concept URL provided: `https://class.familyherohub.com`  
Scope: read-only product, architecture, security, data-model, UX, implementation, and competitive audit  
Output-only exception: this report file

## 1. Executive summary

Class Hero Hub should not be implemented as a simple rename of Family Hero Hub. The current application is a family reward and routine product with a parent-led data model. It has useful engineering assets, especially FastAPI/SvelteKit structure, PostgreSQL migration work, family-scoped access checks, CSRF protection, hashed invite tokens, child-device sessions, Arabic/English i18n scaffolding, QA documentation, and some concurrency hardening around points and redemptions. Those assets are reusable as patterns.

The current product model is not reusable as the core school model. It is built around `families`, `parent_users`, `children`, household rewards, allowance, savings jars, redemptions, child dashboards, family invites, and parent-created point actions. Class Hero Hub needs school tenants, staff roles, academic years, grades, classes, subjects, teaching groups, staff assignments, student enrolments, guardian relationships, school-controlled parent invitations, behaviour categories, messaging, feeds, media consent, imports, audit logs, and tenant-aware reporting. None of those exist as first-class production entities today.

The most important blocker is tenancy. The current app uses `family_id` as a household boundary and relies on application-layer query filters such as "child belongs to current parent's family." Class Hero Hub needs a tenant key on nearly every table, role scopes by school and assignment, tenant-aware unique constraints and indexes, audit logs, media prefixes, notifications, jobs, tests, and preferably PostgreSQL Row Level Security for high-risk data paths. A pilot at one school must still use the multi-school architecture from day one.

The second blocker is role design. The current "admin" is derived from a bootstrap email allowlist and the primary authenticated human is a parent. Class Hero Hub needs a platform super administrator, school owner/admin, senior leader/coordinator, teacher, teaching assistant, parent/guardian, and student profile. Teachers must not inherit parent powers. Parents must not award points. Students do not need login initially.

The third blocker is product surface. Class Hero Hub needs safe school-family communication, controlled posts/feed, school-owned behaviour points, imports, media consent, calendar/homework/project tools, and reporting. The current application has none of the messaging/feed/media/import primitives and only household versions of points/calendar/school-bag concepts.

Recommendation: keep the repo as a scaffold and migration reference, but design a new Class Hero Hub domain layer and database schema. Remove or quarantine the household reward/allowance/savings/redemption/child-device-login product before any school pilot. Build the pilot on the production tenant/RBAC/import/audit foundations, even if the first pilot has only one school.

## 2. Current repository and deployment overview

The repository is a FastAPI backend, SvelteKit frontend, PostgreSQL-backed Docker Compose deployment, and operational documentation set. Main backend files include `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/main.py`, route modules under `backend/app/routes/`, and service modules under `backend/app/services/`. Frontend routes live under `frontend/src/routes/`. English/Arabic strings live in `frontend/src/lib/i18n/messages.ts`.

Current backend routes are family-product routes:

- `/api/auth/*`: Google OAuth parent login, invite verification, logout.
- `/api/children/*`: child CRUD, ledger, award, penalty, savings, adjustment.
- `/api/rewards`, `/api/redemptions`: parent-created rewards and child redemption requests.
- `/api/presets`: reusable household behaviour presets.
- `/api/family/*`: family settings, grownups, family invites.
- `/api/child/*`: child dashboard session endpoints.
- `/api/child-link/*`: child device link exchange.
- `/api/calendar/*`: family child calendar entries and rewardable tasks.
- `/api/school-items/*`: household "school bag" items.
- `/api/allowance/*`: child allowance settings and previews.
- `/api/admin/*`: registration requests, user access management, family suspension.

Current frontend routes include `/`, `/login`, `/parent`, `/child/[id]`, `/child-link/[token]`, `/family-invite/[token]`, `/calendar`, `/allowance`, `/redemptions`, `/admin/registration-requests`, and `/admin/users`. These names and pages are mostly parent/child/family routes, not school SaaS routes.

Deployment documentation says the production Family Hero Hub runtime was cut over to PostgreSQL in May 2026, Docker Compose keeps PostgreSQL internal, pgBackRest/WAL archiving is documented, Caddy is the public proxy, and dev access is Caddy-allowlisted. The current repo path in this audit is `/opt/apps/class_hero_hub`, while several docs still refer to `/opt/apps/family-hero-hub`.

## 3. What is reusable from Family Hero Hub

Keep as implementation patterns:

- FastAPI project layout and dependency-injected database sessions.
- SvelteKit frontend build, route structure, and API wrapper pattern.
- Alembic migration discipline and PostgreSQL production direction.
- Runtime configuration validation for production secrets, CORS, proxy trust, and app environment.
- CSRF double-submit protection for cookie-authenticated unsafe requests.
- Secure-cookie session posture: `HttpOnly` auth cookies and `SameSite=Lax`.
- Hashed, expiring, revocable invitation token pattern.
- PostgreSQL partial unique index use for idempotent ledger operations.
- Test culture: backend pytest, real PostgreSQL concurrency tests, Playwright visual checks, i18n parity script.
- English/Arabic i18n scaffolding and document `dir` switching.
- Family suspension/revocation concepts as a starting analogy for school suspension/offboarding.
- Soft-delete lesson from school-item history preservation.

Reuse with major changes:

- Ledger/point-event mechanics: useful append-only pattern, but replace jars/savings/redemptions with behaviour point events and corrections.
- Calendar service: recurrence and date windows are useful, but it must become school/class/subject/student scoped.
- School items: useful "required items" concept, but not parent-configured per child; convert to teacher/school assignments.
- Admin screens: patterns for lists and access management are useful, but current records are parent/family records.
- Child link QR flow: token security pattern is useful, but should become parent/guardian invitation and student connection codes.

## 4. What must be removed

Remove from the Class Hero Hub product:

- Household rewards and reward redemptions.
- Allowance settings and all money-equivalent point value UX.
- Savings jars, locked savings, savings maturity, savings bonus, and bank metaphors.
- Parent-created behaviour presets as the main behaviour authority.
- Parent-as-points-awarder flows.
- Child dashboard login/device linking for initial school product.
- Pet/dragon progression if tied to rewards/allowance rather than school feedback.
- Home routines, chores, household reminders, sibling/family wording, caregiver-as-household-manager wording.
- Family invitation logic as an access model for school guardians.
- Public beta family pricing and family consumer landing-page copy.

## 5. What must be renamed

Rename or replace these concepts:

- `Family Hero Hub` -> `Class Hero Hub`.
- `family`, `families`, `family_id` -> `school`, `schools`, `school_id` or `tenant_id`, depending on table.
- `parent_users` -> split into `users`, `staff_profiles`, and `guardian_profiles`.
- `children` -> `students`.
- `grownups`/`caregivers` -> guardians only where they are legal/authorised child contacts.
- `presets` -> behaviour categories or point reasons.
- `ledger_transactions` -> behaviour point events and corrections.
- `School Bag` -> required items or class materials.
- `Parent Dashboard` -> Guardian Dashboard.
- `Child Dashboard` -> Student profile, not a student-login product in MVP.
- `/parent` -> `/guardian` or role-aware `/app`.
- `/child/[id]` -> remove from MVP or replace with staff/guardian student profile route.
- `/family-invite/[token]` -> `/guardian-invite/[token]`.

## 6. What must be heavily redesigned

Authentication, authorisation, data model, imports, points, calendar, admin, and dashboards require heavy redesign. The current app is single-household oriented and cannot represent a teacher who teaches Grade 3A English, Grade 3B English, Grade 4A Science, and Grade 5D English while another staff member covers temporary lessons. It also cannot preserve academic-year assignment history or enforce teacher access by assignment.

The frontend also needs a new information architecture. A school SaaS product needs staff dashboards, student rosters, class/subject selectors, announcement/feed authoring, message inboxes, import screens, consent management, reporting, and guardian views. The current parent dashboard is large and feature-rich but points to the wrong workflows.

## 7. Current architectural blockers

- No tenant model for multiple schools.
- No `school_id`/`tenant_id` on core product tables.
- No role table or scoped permission model.
- Admin authority is bootstrap email based.
- Parent identity is the primary user identity.
- Teachers, teaching assistants, senior leaders, guardians, and school admins do not exist.
- Students are children in a family, not enrolments in academic structures.
- No academic years, terms, grades, homerooms, subjects, teaching groups, or assignment history.
- No guardian-student relationship model.
- No school-controlled parent invite flow.
- No import jobs, previews, dry runs, row errors, or idempotent re-import model.
- No messaging, announcements, posts/feed, comments, moderation, read receipts, quiet hours, or retention.
- No file/media storage model.
- No media consent model.
- No audit log table covering all sensitive actions.
- No tenant-aware background job design.
- No tenant-aware test suite.
- Hard-coded/default Family Hero Hub values such as `Asia/Muscat`, `OMR`, `families.loginto.me`, `familyherohub.com`, `Parent Dashboard`, and family consumer copy.

## 8. ClassDojo verified feature inventory

The following ClassDojo features are verified from public sources. They should inform, not dictate, Class Hero Hub.

- Family invitations: ClassDojo publicly documents individual printouts containing a unique parent code and QR code, plus email/text invites, class links, and class QR codes. Families can scan or type a code to connect to a child's profile/class, and class-link requests require teacher approval. Sources: ClassDojo Help, "Invite Families to ClassDojo" and "How to Connect Parents with a Class Link" [Invite Families](https://help.classdojo.com/hc/en-us/articles/202794025-Invite-Families-to-ClassDojo), [Class Link](https://help.classdojo.com/hc/en-us/articles/360046903851-How-to-Connect-Parents-with-a-Class-Link).
- Class Story and School Story: teachers share class photos, videos, and announcements with connected families; approved teachers and school leaders share school-wide posts. Visibility is limited to relevant teachers/leaders/families, and district deletion/access is handled through support. Source: [Class Story and School Story](https://help.classdojo.com/hc/en-us/articles/211889103-What-is-Class-Story-and-School-Story).
- Schoolwide points: school leaders/admins create schoolwide skills; verified school leaders, teachers, and staff can award school points; school leaders/admins can download CSV point reports; notes on school points are not currently supported according to the FAQ. Source: [School Point FAQs for School Leaders](https://help.classdojo.com/hc/en-us/articles/28306157542669-School-Point-FAQs-for-School-Leaders).
- Class and school points: public help says ClassDojo has school points and class points; class points are awarded within classes and added to both class and school point balances. Source: [How To Award Points to Students](https://help.classdojo.com/hc/en-us/articles/207811096-How-To-Award-Points-to-Students).
- Family translation: families can translate Class Story posts, School Story posts, and messages based on preferred language. Source: [How Families Can Translate Posts and Messages](https://help.classdojo.com/hc/en-us/articles/204885716-How-Families-Can-Translate-Posts-and-Messages).
- School leader tools: public help says school leaders have teacher functionality plus ability to track engagement and manage student roster and staff list in School Directory. Source: [What Can School Leaders See and Do?](https://help.classdojo.com/hc/en-us/articles/207813176-What-Can-School-Leaders-See-and-Do).
- School/district offerings: ClassDojo public district pages mention attendance, digital portfolios, and AI features such as Sidekick. Source: [ClassDojo for Districts](https://www.classdojo.com/districts/).
- Privacy and controls: public materials claim COPPA/FERPA/GDPR posture and distinguish school-controlled in-school features from parent-controlled at-home features. Sources: [Privacy & Security](https://www.classdojo.com/privacy-and-security/), [Parental and Child Controls FAQ](https://help.classdojo.com/hc/en-us/articles/41204302339981-ClassDojo-Parental-and-Child-Controls-FAQ).
- Pricing: public ClassDojo Plus page says core messaging, class points, and class story updates are free, while Plus is an optional family subscription with additional at-home features. Source: [ClassDojo Plus](https://www.classdojo.com/plus/).

Inferred or less directly verified from public sources:

- Detailed SIS rostering, SSO, audit logs, CSAM/keyword scanning, and district oversight are described in ClassDojo's public `llms.txt`, but that should be treated as company-provided summary metadata rather than deep help-center documentation. Source: [ClassDojo llms.txt](https://www.classdojo.com/llms.txt).

## 9. Competitive feature matrix

| Area | ClassDojo public capability | Verification | Current Class Hero Hub/FHH capability | Reuse | Rewrite/Build | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| School onboarding | School leaders, school directory, rosters | Verified in help | None | Admin list patterns | New tenant/school setup | Build from day one |
| Classes | Class points and connected families | Verified | No classes; only children/families | None | Full academic structure | Build |
| Student rosters | School leaders manage roster | Verified | Family child list | Child profile UI patterns | Student/enrolment model | Build |
| Parent connections | QR/code/email/class link, approval | Verified | Family invites; child-device QR | Token hashing/expiry | School-controlled guardian invites | Build |
| Points | Class and school points; skills | Verified | Parent award/penalty ledger | Append-only ledger concept | Behaviour point events | Rewrite |
| Behaviour skills | Schoolwide skills and class skills | Verified | Preset behaviours per family | UI category pattern | School categories/policies | Rewrite |
| Reports | CSV schoolwide point reports | Verified | Ledger summaries per child | Query/test patterns | Tenant reports | Build |
| Class feed | Class Story | Verified | None | None | Posts/audiences/media | Build |
| School feed | School Story | Verified | None | None | School posts | Build |
| Messaging | Two-way family messaging publicly referenced | Verified broadly | None | None | Conversations/messages | Build |
| Translation | Translated posts/messages | Verified | Static UI English/Arabic | i18n foundation | Content/notification localisation | Extend heavily |
| Events | Public product suggests events/tools | Partially verified | Family calendar | Recurrence/date code | School calendar/homework | Rewrite |
| Portfolios | District page mentions portfolios | Verified on public page | None | None | Defer unless needed | Later |
| Attendance | District page mentions attendance | Verified on public page | None | None | Defer unless pilot demands | Later |
| Family accounts | Parent app/family connections | Verified | Parent Google OAuth | Account/session patterns | Guardian accounts | Rewrite |
| Student accounts | Student web app is listed publicly | Inferred/company summary | Child device login | Token patterns | Not MVP | Avoid initially |
| Notifications | Public app supports notifications broadly | Inferred | None | None | Notification service | Build |
| Privacy/safety | COPPA/FERPA/GDPR claims | Public claim | Some security hardening | Config/tests | Compliance program | Legal review |
| AI | Sidekick and AI homework help | Verified public pages | None | None | Later only | Defer |
| Premium/family offerings | Plus optional family subscription | Verified | FHH family monetisation copy | None | Not school MVP | Avoid consumer upsell |

## 10. Opportunities to outperform ClassDojo

- Build teacher workload protections from day one: quiet hours, escalation rules, office-hour expectations, and emergency exceptions.
- Make negative behaviour handling safer: configurable parent visibility, review workflows, dignity safeguards, no public leaderboards, no humiliation patterns.
- Offer robust import/re-import with previews, dry runs, downloadable error reports, stable identifiers, and history preservation.
- Design media consent deeply, including per-child categories, revocation, expiry, group-photo checks, and audit evidence.
- Support English and Arabic from day one with proper RTL accessibility, not only machine translation.
- Give schools transparent audit logs and controlled safeguarding access instead of support-ticket-only access.
- Separate school-owned records from optional home/family entertainment features; avoid consumer upsell friction in school workflows.
- Provide tenant-aware export/offboarding and restore procedures that schools can understand.
- Make teaching-group and subject assignment models stronger than homeroom-only classroom tools.

## 11. Proposed Class Hero Hub product definition

Class Hero Hub is a multi-tenant K-12 school-family engagement platform. It helps schools manage behaviour points, safe communication, class/school feeds, homework/events/required items, parent/guardian access, media consent, and reporting across academic structures. It is school-owned, staff-administered, guardian-facing, and student-profile based.

Initial delivery should be a responsive web/PWA. Mobile apps can later use the same API and auth model. Students do not need independent login in the initial version. Guardians access dashboards for linked children. Teachers and teaching assistants access students through assignments, not family relationships.

## 12. User roles and permission model

Recommended roles:

- Platform super administrator: manages platform settings, schools, billing/status, tenant suspension, emergency support, controlled break-glass. No casual access to student data.
- School owner/school administrator: manages school setup, staff, imports, academic years, classes, subjects, teaching groups, parent links, settings, reports, and policy.
- Senior leader/year coordinator/department coordinator: scoped oversight for grades, year groups, departments, or subjects; can view reports and moderate according to policy.
- Teacher: sees assigned teaching groups/classes/subjects/students; awards points; posts; messages linked guardians; creates homework/events.
- Teaching assistant: scoped support role; permissions configured by school policy, often view plus limited point/post/event actions.
- Parent/guardian: sees linked children only; receives posts/messages/events/points according to visibility policy; can message staff when allowed.
- Student profile: record only in MVP; no independent login.

Use RBAC plus ABAC. RBAC grants capability classes; ABAC checks school, assignment, academic year, student relationship, message participant, post audience, and policy state.

## 13. Multi-school tenancy design

Use `schools` as tenants. Every school-owned data row should include `school_id` directly unless it is truly platform-global. Use `school_id` in unique constraints and indexes.

Tenant design requirements:

- The request context must resolve active user, active school, role scopes, and assignment scopes.
- All APIs must filter by `school_id` and scope. Avoid relying on client-provided school ids alone.
- Super-admin access must be explicit, audited, reasoned, time-bounded where practical, and visually indicated.
- School admins must access only their school.
- Teachers and assistants must access only assigned students/groups, with temporary-cover grants represented as dated assignments.
- Guardians must access only students linked through active guardian-student relationships.
- Historical records keep their original `school_id`, academic year, class/subject context, and actor id.
- Use tenant-aware soft deletion for people, groups, classes, categories, and posts.
- School offboarding should support suspension, export, retention hold, deletion/anonymisation workflow, and media purge queue.
- Tenant-aware background jobs must always include `school_id` in job payloads and lock keys.
- Tenant-aware media storage should use object prefixes like `schools/{school_id}/...`, but never trust prefixes alone for access.
- Tenant-aware backups/restores need school-level export and full-environment restore tests. Single-tenant restore into production is risky and needs tooling.
- Consider PostgreSQL Row Level Security for high-risk tables such as students, guardian links, messages, media, point events, and consent records. RLS should supplement, not replace, application-layer authorisation.

## 14. Proposed school/class/subject structure

Hierarchy:

Platform -> School -> Academic year -> Term/semester -> Grade/year group -> Homeroom/class -> Subject -> Teaching group -> Staff assignments -> Students -> Guardians.

Important modelling choices:

- Homeroom/class is not the same as teaching group. Grade 3A is a homeroom; Grade 3A English is a teaching group tied to subject English.
- A teaching group can include one homeroom, selected students, or a cross-class set.
- Staff assignments are dated and role-specific: lead teacher, co-teacher, assistant, cover teacher, coordinator.
- Student enrolments are dated and preserve moves between classes/grades/academic years.
- Assignment changes close the old record and create a new one; do not overwrite history.
- Academic-year rollover creates new enrolments and teaching assignments while preserving prior year records.

## 15. Proposed PostgreSQL data model

Major entities:

- `schools`: tenant record. Tenant key: `id`. Constraints: unique slug/domain where applicable, status. Audit: creation, suspension, deletion. Index: status.
- `school_settings`: one-to-one school settings. Includes locale defaults, timezone, week start, communication hours, negative-point policy, media policy.
- `campuses`: optional school sites. `school_id`, name, address metadata, active dates.
- `academic_years`: `school_id`, name, start/end dates, rollover state. Unique `(school_id, code)`.
- `terms`: `school_id`, `academic_year_id`, name, dates. Ensure term dates fall inside academic year.
- `grades`: `school_id`, code/name/sort order. Unique `(school_id, academic_year_id, code)` if grade definitions vary by year.
- `homerooms`: `school_id`, `academic_year_id`, `grade_id`, name. Unique `(school_id, academic_year_id, name)`.
- `subjects`: `school_id`, code/name, active flag. Unique `(school_id, code)`.
- `teaching_groups`: `school_id`, `academic_year_id`, optional `grade_id`, optional `homeroom_id`, `subject_id`, name, status.
- `users`: platform login identity with email/phone/password/OAuth fields. Email unique globally if login is global; profiles carry school scopes.
- `staff_profiles`: `school_id`, `user_id`, staff number, display name, status. Unique `(school_id, staff_number)` and optionally `(school_id, user_id)`.
- `staff_role_assignments`: `school_id`, staff profile, role, scope type/id, start/end dates. Supports coordinators and admins.
- `teacher_assignments`: `school_id`, teaching group, staff profile, assignment role, start/end dates, temporary-cover reason.
- `students`: `school_id`, stable student identifier, legal/preferred names, DOB if required, status. Unique `(school_id, student_number)`.
- `student_enrolments`: `school_id`, student, academic year, grade, homeroom, start/end dates, reason. History required.
- `guardian_profiles`: `user_id`, contact fields. A guardian may connect to multiple schools.
- `guardian_student_relationships`: `school_id`, guardian, student, relationship type, permissions, custody notes flag, start/end, status. Never rely on display name matching.
- `guardian_invitations`: `school_id`, student, token hash/code hash, created by, expiry, revoked/used timestamps, delivery mode, print batch id.
- `behaviour_categories`: `school_id`, optional subject/grade scope, positive/negative/neutral, points value, visibility policy, active dates.
- `point_events`: `school_id`, student, category, points, actor staff, teaching group, subject, event date, note, evidence media, visibility state, source/import id.
- `point_corrections`: `school_id`, original point event, correction event, reason, actor, timestamp. Corrections append; never rewrite.
- `audit_entries`: `school_id`, actor user/profile, action, target type/id, reason, metadata, IP/device, timestamp. Immutable.
- `conversations`: `school_id`, type, student context, class/group context, status, retention policy.
- `conversation_participants`: `school_id`, conversation, participant user/profile, role, active/read state.
- `messages`: `school_id`, conversation, sender, body, language, created_at, edited/deleted state, moderation state.
- `attachments`: `school_id`, owner object, media object, filename, MIME, size, virus status.
- `posts`: `school_id`, author, post type, title/body, language, scheduled/published/archived state, moderation state.
- `post_audiences`: `school_id`, post, audience type/id such as school, grade, homeroom, teaching group, selected students.
- `comments`: `school_id`, post, author guardian/staff, body, approval state, moderation fields.
- `media_consents`: `school_id`, student, guardian relationship, category, granted/denied, expiry, evidence, source, timestamps.
- `calendar_events`: `school_id`, scope, title/body, event type, dates/timezone, recurrence, acknowledgement requirement.
- `assignments_homework`: `school_id`, teaching group or selected students, title/body, due date, completion/ack rules.
- `required_items`: `school_id`, group/student scope, item, due/use date, recurrence, acknowledgement/completion.
- `notifications`: `school_id`, user, channel, locale, template, payload, status, delivery attempts.
- `notification_preferences`: user/school/channel preferences and quiet-hour settings.
- `communication_hours`: `school_id`, staff or role scope, normal hours, emergency rules.
- `import_jobs`: `school_id`, type, file object, dry-run/write status, actor, summary, idempotency key.
- `import_rows`: `school_id`, job, row number, parsed payload, action preview, status.
- `import_errors`: `school_id`, job/row, field, code, message.
- `file_objects`: `school_id`, object storage key, hash, MIME, size, metadata, scanner status, retention/deletion state.
- `safeguarding_flags`: `school_id`, target message/post/student/conversation, severity, reporter, status, controlled access.
- `reports`: saved report definitions and generated export metadata.

All school-owned tables should have `(school_id, id)` indexes where joins and authorisation checks are frequent. Soft-delete fields should include `deleted_at`, `deleted_by`, and deletion reason where records affect history.

## 16. Authentication and onboarding

Staff authentication:

- MVP: email/password plus magic-link recovery, with optional Microsoft/Google OAuth once domains are configured.
- Later: school-managed SSO via Google Workspace/Microsoft Entra/SAML/OIDC.
- Require MFA for platform super admins and school admins. Offer MFA for staff.
- Session management: secure `HttpOnly` cookies, CSRF protection, short access lifetime plus refresh/session records, device/session list and revocation.

Guardian authentication:

- Recommended MVP: email/password with magic-link verification/recovery. This avoids requiring Google/Apple and works internationally.
- Optional OAuth can be added later, but must not be the only route.
- Phone/SMS can help in some regions but adds cost, deliverability, and SIM-swap risk.
- Magic-link-only login is simple but can be risky if email accounts are shared or links are forwarded; combine with account creation and session controls.

Account recovery must preserve school-controlled guardian links. A guardian changing email should require verification and school-visible audit.

## 17. Parent QR/invitation flow

Recommended flow:

1. School admin or authorised teacher selects students and generates invitations.
2. The system creates opaque, high-entropy tokens plus optional short typed fallback codes.
3. Printed invite shows QR and fallback code, but no sensitive student information in the URL or unauthenticated response.
4. Parent scans QR, creates or logs into account, verifies email, and then redeems code.
5. Only after authentication does the system reveal the student match and relationship prompt.
6. Existing known guardian emails can auto-connect if school policy permits; unknown guardians should create a pending link for staff approval or require a student-specific printed code.
7. Codes expire, can be revoked, and can be regenerated.
8. Multiple guardians can connect to one student; one guardian can connect to multiple children.
9. School admins can view, suspend, revoke, and audit links.

Security requirements:

- Store only token hashes/code hashes.
- Rate-limit code attempts by IP, account, school, and invite batch.
- Never match solely by child display name.
- Do not leak whether a student exists before authentication.
- Record invite issuer, delivery method, expiry, acceptance, revocation, and linked guardian.

## 18. CSV import and academic-year rollover design

Import types:

- School setup, grades, classes/homerooms, subjects, teaching groups.
- Teachers and teaching assistants.
- Students.
- Parent/guardian contacts.
- Guardian-student relationships.
- Teacher assignments and teaching assistant assignments.
- Student enrolments.

Stable identifiers:

- Staff: school staff number or school email plus optional external SIS id.
- Students: school admission/student number or external SIS id.
- Guardians: verified email/phone plus external contact id where available.
- Classes/subjects/groups: school-defined codes, not display names alone.

Import workflow:

- Download localised templates.
- Upload file to object storage as a file object.
- Parse and validate into `import_jobs`, `import_rows`, and `import_errors`.
- Preview create/update/move/end-date actions before writing.
- Support dry-run and write modes.
- Generate downloadable error report.
- Use idempotency keys per job and row natural keys.
- Wrap write batches in transactions with safe partial failure strategy: either all-or-nothing for tightly coupled files or row-level failure with clear status.
- Preserve history by closing old enrolments/assignments and opening new ones.
- Rollover creates next-year records without destroying prior-year reports.

## 19. Behaviour points design

Points are school feedback records, not household rewards. There are no redeemable rewards.

Support:

- School-wide positive and negative categories.
- Configurable values and visibility rules.
- Teacher-created categories only if permitted by school policy.
- Individual, selected-student, whole-class, and whole-teaching-group awarding.
- Optional notes and evidence.
- Undo/correction via append-only reversal/correction event.
- Reason required for manual corrections.
- Actor staff identity, date/time, teaching group, class, subject, and category on every event.
- Parent visibility controls, especially for negative points.
- Approval/moderation for high-severity negative points if school policy requires.
- Reports by student, class, grade, teacher, subject, behaviour, and date range.

Safeguards:

- No public leaderboards by default.
- No classroom display of negative individual status.
- Rate/volume anomaly detection for staff misuse.
- Clear audit trail and school policy warnings before negative bulk actions.
- Separate concern events from ordinary low-stakes behaviour feedback.

## 20. Parent dashboard design

Guardian dashboard should show linked children, today/upcoming school items, recent approved-visible points, homework/tests/projects, calendar events, announcements, class/school feed, messages, media consent status, and acknowledgement requests.

It must not allow point awarding, reward creation, household chores, savings, allowance, or redemptions. It should support guardian language preference, multiple children across schools, and clear school/class context.

## 21. Teacher dashboard design

Teacher dashboard should be assignment-first:

- Today schedule: teaching groups, cover assignments, deadlines.
- Quick class selector by subject/group.
- Point award panel with categories and selected students.
- Recent class activity and corrections.
- Parent messages with working-hours controls.
- Draft/scheduled posts.
- Homework/events/required items authoring.
- Student profile quick access.
- Alerts for media consent issues when posting photos.

## 22. School admin dashboard design

School admin dashboard:

- Setup progress: academic year, terms, grades, classes, subjects, groups.
- Imports and error queues.
- Staff and role assignments.
- Student enrolments and guardian links.
- Invitation batches and QR printouts.
- Behaviour category policy.
- Communication hours and moderation policy.
- Reports and exports.
- Audit log search.
- Data retention/offboarding controls.

## 23. Super-admin dashboard design

Platform super admin:

- School tenant creation/status/suspension.
- Domain/SSO configuration status.
- Operational health, job status, storage usage.
- Support access requests with reason, approval, and expiry.
- Security events across tenants without exposing child content unless break-glass is authorised.
- Feature flags by school.

## 24. Messaging design

Allowed communication:

- Teacher to parent.
- Parent to teacher.
- School/year/department/class announcements.
- Direct teacher-parent conversations.
- Multi-guardian conversations for one child.

Disallowed:

- Parent-to-parent messaging.
- Unrestricted parent group chats.
- Student private messaging.
- Student-to-adult messaging in MVP.

Messaging requirements:

- Conversation participants must be derived from assignments and guardian relationships.
- Teachers see only students they teach or temporarily cover.
- Quiet hours and staff working hours should delay notifications, not necessarily block message creation.
- Emergency/safeguarding exceptions require policy and audit.
- Read receipts by participant.
- Attachments through scanned file objects.
- Search with tenant and permission filters.
- Retention/export/legal hold.
- Moderation/reporting and safeguarding access under controlled policy.
- Blocking/abuse handling for guardian misuse.

## 25. School/class feed design

Feed audiences:

- Whole school.
- Grade/year group.
- Homeroom/class.
- Subject teaching group.
- Selected students/guardians where appropriate.

Features:

- Photos, multiple photos, documents, announcements, celebrations, project updates, homework reminders.
- Drafts, scheduling, pinning, archiving, search.
- Translation-ready content with author language and target locale support.
- Parent acknowledgements where required.
- Comments optional per post.
- Parent comments require approval before visible.
- Comments must not become parent-to-parent messaging; guardians should not see each other's direct contact details.

## 26. Media consent design

On first guardian login, prompt for media consent per child. The school should configure consent categories:

- Photo.
- Video.
- Internal-only.
- Public marketing.
- School event.
- Yearbook or other local categories.

Records need grant/deny, guardian, timestamp, expiry/renewal, revocation, evidence, and policy version. Teachers posting media should select tagged students or group-photo context. The system should warn or block when consent is missing or denied according to policy. Group photos need regional rules and staff override policy only where legally appropriate.

## 27. Calendar/homework/tests/projects design

Use distinct entities or typed records for:

- Calendar events: school/grade/class/group/student scoped events.
- Homework/assignments: academic work with due date, attachments, selected students, completion/ack rules.
- Tests/projects: assessment-related deadlines with clear visibility.
- Required items: books, equipment, uniform reminders, trip forms.

Support recurrence, timezone, academic-year boundaries, changes/cancellations, notifications, parent acknowledgement, and future calendar export. Do not blur announcements, feed posts, events, homework, and required items; they have different workflows.

## 28. Notifications design

Channels:

- In-app notifications.
- Email.
- Web push/PWA.
- Mobile push later.

Design:

- Notification templates localised by user language.
- Digest and immediate modes.
- Staff quiet hours and communication hours.
- Parent preferences.
- Emergency notices that bypass normal quiet hours with audit.
- Delivery status, retries, deduplication, and idempotency keys.
- Background jobs with tenant id, payload version, and retry policy.
- Audit for sensitive notifications.

## 29. Reporting and analytics

Reports:

- Behaviour by student/class/grade/teacher/subject/category/date range.
- Positive/negative trends over time.
- Guardian connection rates.
- Message response and unread reports.
- Announcement acknowledgement rates.
- Import quality/error reports.
- Media consent coverage.
- Staff activity audit.

Avoid student-shaming outputs. Default reports should be school-improvement and support oriented, not public ranking.

## 30. Internationalisation and RTL design

Current state:

- `svelte-i18n` is in use.
- English and Arabic messages live side by side.
- `html lang` and `dir` are synchronised.
- Local storage key is `familyHeroHub.language`.
- Docs note Arabic is partial/non-admin and needs native-speaker review.

Required changes:

- Rename local storage key for Class Hero Hub.
- Expand supported locales data model: `en`, `ar` from day one; later `fr`, `de`, `af`, etc.
- Store school default language and user preference.
- Use ICU pluralisation for points, days, messages, and counts.
- Use `Intl.DateTimeFormat`/`Intl.NumberFormat` for locale-aware dates, numbers, times.
- Persist content language for posts/messages and notifications.
- Decide fallback rules: user locale -> school default -> English.
- Localise emails, notification templates, CSV templates, import errors, and PDFs.
- Support RTL layout testing for all dashboards, forms, modals, tables, calendars, and message bubbles.
- Handle mixed-language content without forcing direction incorrectly.
- Avoid hard-coded region defaults such as Oman/GCC, `Asia/Muscat`, Sunday week start, or OMR.

## 31. Accessibility

Requirements:

- WCAG 2.2 AA target.
- Keyboard navigation for dashboards, modals, tables, feed, messaging, imports.
- Screen-reader labels for icons/buttons.
- Focus management for modals and drawers.
- Colour contrast for positive/negative states.
- No information conveyed by colour alone.
- RTL accessibility testing.
- Responsive layouts for mobile guardians and tablet/desktop school staff.
- Reduced-motion support.
- Large touch targets for PWA use.

## 32. Safeguarding and privacy

Key risks:

- Child personal data exposure.
- Guardian access after separation/custody changes.
- Teacher access to unrelated students.
- Negative behaviour visibility harming student dignity.
- Media posted without consent.
- Message misuse or out-of-hours pressure.
- School admin overreach into private conversations without policy.

Controls:

- Data minimisation.
- Assignment and relationship-based access.
- Media consent enforcement.
- Audit logs for sensitive reads/writes.
- Safeguarding flags and legal holds.
- Export/deletion workflows.
- Retention policies per school and region.
- Controlled break-glass access.
- Professional legal review for COPPA, FERPA, GDPR, UK GDPR, Oman/GCC and other regional privacy laws. Do not claim certification without legal/compliance process.

## 33. Security risks

Current positive controls:

- Startup config validation catches weak production secrets and bad CORS/proxy trust.
- CSRF middleware exists.
- Cookies use `HttpOnly` for auth and `secure` in production.
- Invite/session tokens are high entropy and hashed.
- Some rate limiting exists for child link exchange.
- Some real PostgreSQL concurrency/idempotency tests exist.

Current gaps for Class Hero Hub:

- No tenant isolation model.
- No scoped RBAC/ABAC.
- No MFA.
- No password auth or recovery.
- No staff departure/session revocation workflow.
- No guardian custody-sensitive access model.
- No audit log.
- No file upload scanning.
- No CSP currently deployed per docs because Svelte inline bootstrap blocked prior CSP.
- No production-grade messaging abuse/rate-limit model.
- No tenant-aware cache/job safeguards.

## 34. Media/file-storage design

Do not use the server filesystem as permanent school media storage.

Recommended design:

- S3-compatible object storage.
- Keys prefixed by school and object type.
- Database `file_objects` are the source of truth.
- Direct browser uploads through short-lived signed upload URLs.
- Download through permission-checked signed URLs or proxy.
- MIME sniffing and extension validation.
- Size limits by file type and school quota.
- Virus/malware scanning before publication.
- Image resizing and thumbnail generation.
- EXIF/geolocation stripping.
- Metadata minimisation.
- Retention and deletion queues.
- CDN later, with private origin controls.
- Abuse detection and moderation hooks.
- Cost dashboards and per-school quotas.

## 35. Performance and scaling

Early scale concerns:

- Point-event reporting will grow quickly. Use indexes on `(school_id, student_id, occurred_at)`, `(school_id, teaching_group_id, occurred_at)`, `(school_id, category_id, occurred_at)`, and actor/date combinations.
- Feed and messages need cursor pagination.
- Imports should run in background jobs, not web request threads.
- Notification sends need queues and dedupe.
- Media processing needs asynchronous workers.
- Avoid N+1 queries in dashboards; use scoped aggregate endpoints.
- Cache only tenant-safe data and include school id in cache keys.
- Use read replicas later only after tenant and consistency design is mature.

## 36. Testing strategy

Required tests:

- Unit tests for permission policies.
- API tests for every role/scope combination.
- Tenant isolation tests that create two schools and attempt cross-access.
- PostgreSQL tests for constraints, partial indexes, transactions, and concurrent point corrections/imports.
- Import dry-run/write/idempotency tests.
- Guardian invite token security tests.
- Messaging participant and quiet-hour tests.
- Media consent enforcement tests.
- File upload validation/scanning state tests.
- i18n key parity and RTL visual tests.
- Playwright smoke/visual tests for staff, admin, and guardian dashboards.
- Accessibility checks with axe or equivalent.
- Migration tests from current FHH-derived schema to new schema.

## 37. Migration strategy from current FHH-derived schema

Because this is a new school SaaS product, not a household rebrand, migration should be selective.

Recommended:

- Create new school schema tables rather than mutate `families` into `schools`.
- Keep legacy tables temporarily read-only or behind feature flags during transition.
- Write explicit ETL for any demo data worth preserving.
- Do not import household rewards, allowance, savings, redemptions, pet progress, child-device sessions, or family invites into production Class Hero Hub.
- Map only reusable concepts if needed: children -> students for demo school, parent users -> guardians for demo, calendar school-like events -> events if manually validated.
- Build migration assertions to ensure no household financial/reward data leaks into school pilot.

## 38. Recommended API and backend changes

Backend should move toward:

- `/api/schools` for tenant admin.
- `/api/school/settings`.
- `/api/academic-years`, `/api/terms`, `/api/grades`, `/api/homerooms`, `/api/subjects`, `/api/teaching-groups`.
- `/api/staff`, `/api/students`, `/api/guardians`.
- `/api/imports`.
- `/api/guardian-invitations`.
- `/api/behaviour/categories`, `/api/behaviour/points`, `/api/behaviour/reports`.
- `/api/messages`.
- `/api/posts`.
- `/api/media`.
- `/api/consents`.
- `/api/calendar`, `/api/homework`, `/api/required-items`.
- `/api/notifications`.
- `/api/audit`.

Use dependency functions like `get_current_user`, `get_active_school`, `require_permission`, and `require_student_scope`. Avoid route-level copy/paste filters.

## 39. Recommended frontend route and component changes

New role-aware frontend:

- `/app` role router.
- `/staff` teacher/senior leader dashboard.
- `/guardian` guardian dashboard.
- `/admin` school admin dashboard.
- `/platform` super admin dashboard.
- `/setup/imports`, `/setup/academic-years`, `/setup/classes`, `/setup/staff`, `/setup/students`.
- `/behaviour`, `/behaviour/reports`.
- `/messages`.
- `/feed`.
- `/calendar`.
- `/consents`.

Component priorities:

- Role-aware shell and school switcher.
- Student/class selector.
- Teaching group roster table.
- Point category grid.
- Import preview/error table.
- Conversation list/message thread.
- Post composer/audience selector.
- Media consent status badges.
- Audit log table.

## 40. Features to remove from the current UI

- Rewards page and reward request flows.
- Allowance page.
- Savings/bank panels.
- Redemptions page.
- Parent-created reward and preset modals as-is.
- Child dashboard route.
- Child guide.
- Parent guide as family product copy.
- Family invite page.
- Household landing-page sections about chores, allowance, family routines, child devices, dragon/pet assets, and family beta pricing.

## 41. Exact Family Hero Hub wording and routes that need attention

Routes needing removal or replacement:

- `/parent`
- `/child/[id]`
- `/child-link/[token]`
- `/family-invite/[token]`
- `/allowance`
- `/redemptions`
- `/parent-guide`
- `/child-guide`
- `/admin/registration-requests` in current parent-registration form

Backend route groups needing replacement or quarantine:

- `routes/children.py`
- `routes/ledger.py`
- `routes/redemptions.py`
- `routes/rewards.py`
- `routes/allowance.py`
- `routes/child_access.py`
- `routes/child_devices.py`
- `routes/child_link.py`
- `routes/family.py`
- `routes/presets.py`

Wording categories to remove:

- Family Hero Hub.
- Parent-led family hub.
- Parent Dashboard.
- Child Dashboard.
- family, grownup, caregiver in household sense.
- rewards, reward requests, redeem, redemptions.
- allowance, OMR, savings, jars, bank, locked savings, bonus.
- chores, home routines, sibling/family operating system.
- dragon/pet progression if used as household gamification.

Code/default values to revisit:

- `DATABASE_URL` default `sqlite:///./data/family_hero_hub.sqlite`.
- `Family.timezone` and schema default `Asia/Muscat`.
- allowance currency default `OMR`.
- SMTP/domain defaults under `familyherohub.com`.
- CORS default `families.loginto.me`.
- i18n storage key `familyHeroHub.language`.
- static asset `family-hero-hub-logo.png`.

## 42. MVP scope

MVP must include:

- Multi-school tenant foundation even with one pilot school.
- Staff/guardian authentication.
- Role and scope permissions.
- Academic year, grades, homerooms, subjects, teaching groups.
- Staff assignments and student enrolments with history.
- Guardian-student links through secure invitations.
- CSV import dry run, preview, validation, write, error report for core setup.
- Behaviour categories and point events with corrections/audit.
- Guardian dashboard for linked children.
- Teacher dashboard for assigned groups.
- School admin dashboard for setup and imports.
- English/Arabic UI and RTL.
- Basic notifications: in-app and email.
- Audit logs.

## 43. Closed pilot scope

Closed pilot may defer:

- Native mobile apps.
- SIS integration.
- Advanced analytics.
- AI features.
- Portfolios.
- Attendance.
- Public marketing media workflows beyond consent capture and warnings.
- Complex district hierarchy.
- Calendar export.

Closed pilot must not defer:

- Tenant model.
- RBAC/ABAC.
- Guardian invitation security.
- Student/staff stable identifiers.
- Historical enrolment/assignment records.
- Audit trail.
- Media consent foundation if photos/feed are piloted.

## 44. Production launch scope

Production launch should add:

- Hardened password/MFA/session management.
- Complete import idempotency and rollover.
- Messaging with retention, reporting, quiet hours, and safeguarding controls.
- Feed with moderation and comment approval.
- Media storage/scanning/thumbnail/EXIF stripping.
- Full notification preferences and delivery audit.
- School offboarding/export/deletion workflows.
- Monitoring, backups, restore rehearsals, and incident runbooks.
- Legal-reviewed policies and DPAs.

## 45. Later roadmap

Later:

- Native mobile apps.
- SIS rostering.
- SSO/SAML/OIDC.
- Attendance.
- Portfolios.
- Translation assist for school-created content.
- Advanced BI dashboards.
- AI teacher assistant only after privacy review.
- District/multi-campus hierarchy.
- Offline teacher tools.

## 46. Dependency-ordered implementation phases

### Phase 0: Product and legal decisions

Goal: freeze the school product boundary before engineering rework.  
Features: role definitions, data ownership, pilot policy, consent categories, negative-point rules, messaging rules.  
Backend changes: none beyond design docs.  
Frontend changes: none.  
Database changes: none.  
Security considerations: legal/compliance review begins.  
Tests: acceptance criteria/checklists.  
Dependencies: Dom/school decisions.  
Risks: vague policy causes rework.  
Acceptance criteria: signed-off MVP/pilot scope and policy matrix.  
Complexity: medium.

### Phase 1: Tenant, identity, and RBAC foundation

Goal: build production multi-school foundation.  
Features: schools, users, staff/guardian profiles, roles, school context, MFA-ready sessions.  
Backend changes: new auth dependencies and permission engine.  
Frontend changes: role-aware shell and login/onboarding.  
Database changes: `schools`, `users`, profile and role tables, audit base.  
Security considerations: tenant isolation, super-admin controls, session revocation.  
Tests: two-school isolation and role access tests.  
Dependencies: Phase 0.  
Risks: painful rework if underbuilt.  
Acceptance criteria: every protected route requires school and permission context.  
Complexity: very large.

### Phase 2: Academic structure and imports

Goal: represent real school structure and onboard data safely.  
Features: academic years, terms, grades, homerooms, subjects, teaching groups, staff assignments, student enrolments, CSV import preview/write/errors.  
Backend changes: setup APIs, import service, history-preserving updates.  
Frontend changes: admin setup and import screens.  
Database changes: structure, assignment, enrolment, import tables.  
Security considerations: admin-only writes, audit import changes.  
Tests: idempotent import, duplicate detection, move history, cross-tenant import isolation.  
Dependencies: Phase 1.  
Risks: weak identifiers create duplicates.  
Acceptance criteria: pilot school can be loaded, previewed, corrected, and re-imported safely.  
Complexity: very large.

### Phase 3: Guardian invitations and dashboard

Goal: connect guardians to students securely.  
Features: QR/code invites, expiry/revoke/regenerate, multi-guardian/multi-child links, guardian dashboard.  
Backend changes: guardian invitation API and relationship checks.  
Frontend changes: invite redemption flow, guardian dashboard.  
Database changes: guardian relationships and invitation tables.  
Security considerations: no student leak pre-auth, rate limits, audit.  
Tests: token security, code brute-force, wrong-guardian attempts, revoked links.  
Dependencies: Phases 1-2.  
Risks: custody/access errors.  
Acceptance criteria: school can print invites and guardians see only linked children.  
Complexity: large.

### Phase 4: Behaviour points

Goal: replace household ledger with school behaviour point events.  
Features: categories, individual/selected/class/group points, corrections, notes/evidence hooks, reports.  
Backend changes: point event APIs and reporting aggregates.  
Frontend changes: teacher point panel, student/class reports, guardian visibility.  
Database changes: categories, point events, corrections.  
Security considerations: teacher assignment scope, negative-point policy, audit.  
Tests: bulk awarding, corrections, parent visibility, misuse safeguards.  
Dependencies: Phases 1-3.  
Risks: importing old reward logic accidentally.  
Acceptance criteria: teacher can award/correct points only for assigned students.  
Complexity: large.

### Phase 5: Calendar, homework, required items

Goal: provide school-family operational information.  
Features: events, homework/tests/projects, required items, acknowledgements.  
Backend changes: scoped event/assignment APIs.  
Frontend changes: teacher authoring, guardian calendar, admin overview.  
Database changes: calendar/events/homework/required items tables.  
Security considerations: audience scoping and notifications.  
Tests: selected-student scope, timezone, cancellations.  
Dependencies: Phases 1-3.  
Risks: conflating posts/events/homework.  
Acceptance criteria: guardians receive accurate child-specific schedule/homework.  
Complexity: large.

### Phase 6: Messaging and notifications

Goal: safe staff-family communication.  
Features: conversations, read receipts, attachments, quiet hours, in-app/email notifications.  
Backend changes: messaging, notification queue, retention policy.  
Frontend changes: inbox/thread UI, staff hours controls.  
Database changes: conversation/message/notification tables.  
Security considerations: participants, moderation, safeguarding access, abuse controls.  
Tests: participant isolation, quiet hours, retention/export.  
Dependencies: Phases 1-3.  
Risks: staff workload and privacy incidents.  
Acceptance criteria: no parent-to-parent or unrelated student messaging path exists.  
Complexity: very large.

### Phase 7: Feed, media, and consent

Goal: controlled school/class social feed.  
Features: posts, photos, documents, audience selection, comments with approval, media consent warnings.  
Backend changes: post/media APIs and processing jobs.  
Frontend changes: feed, composer, moderation queue, consent prompts.  
Database changes: posts, audiences, comments, media consent, file objects.  
Security considerations: object storage, scanning, EXIF stripping, consent enforcement.  
Tests: media permissions, consent blocks/warnings, comment approval.  
Dependencies: Phases 1-3 and media storage.  
Risks: child media exposure.  
Acceptance criteria: media cannot be posted without policy-aware consent checks.  
Complexity: very large.

### Phase 8: Production hardening

Goal: launch-ready operations and compliance posture.  
Features: exports, offboarding, monitoring, backups, restore tests, security headers/CSP, DPA/policies.  
Backend changes: export/offboarding jobs, audit search.  
Frontend changes: admin export/offboarding and audit views.  
Database changes: retention/legal hold fields if not already present.  
Security considerations: full review, penetration testing, legal review.  
Tests: restore rehearsal, security regression, accessibility, RTL.  
Dependencies: prior phases.  
Risks: launching without operational maturity.  
Acceptance criteria: production checklist passes and pilot data can be exported/restored.  
Complexity: large.

## 47. Risks and unknowns

- Legal jurisdiction and data residency requirements are undecided.
- School policy for negative points and parent visibility is undecided.
- Media consent category requirements vary by region and school.
- Whether the pilot school has stable student/staff IDs is unknown.
- Whether staff require Microsoft/Google SSO in pilot is unknown.
- Messaging retention and safeguarding access policy require school/legal input.
- Existing FHH code may slow progress if too much is preserved.
- Arabic needs native review for school-specific terminology.
- Current production URL and deployment docs still carry Family Hero Hub assumptions.

## 48. Decisions required from Dom

- Confirm MVP modules: behaviour points only, or points plus messaging/feed/calendar in pilot?
- Confirm first pilot school's data format and stable identifiers.
- Choose guardian auth: email/password plus magic-link recovery is recommended.
- Decide if negative points are visible to parents immediately, delayed, summarised, or moderated.
- Define media consent categories and renewal cadence.
- Decide school communication hours and emergency exceptions.
- Decide whether teachers can create categories or only use school-approved categories.
- Decide whether any student login is explicitly out of MVP.
- Decide supported countries for first launch and legal review priority.
- Decide whether to pursue ClassDojo-like free model, school subscription, or pilot contract pricing.

## 49. Suggested first implementation sprint

Goal: create the non-negotiable foundation without touching household features in-place.

Sprint work:

- Add new school-domain schema draft and migration plan.
- Build `schools`, `users`, `staff_profiles`, `guardian_profiles`, `role_assignments`, and `audit_entries`.
- Implement role/school context dependencies.
- Create two-school tenant isolation tests.
- Create minimal role-aware shell.
- Quarantine household routes behind feature flags or separate legacy namespace for development only.
- Draft CSV templates and identifier policy with pilot school.

Acceptance:

- A platform admin can create a school.
- A school admin user can be scoped to that school.
- A teacher in School A cannot read School B records in tests.
- Audit entries are written for sensitive setup actions.
- No Family Hero Hub household reward/allowance flow is used in the school shell.

## 50. Final recommendation

Use Family Hero Hub as a technical scaffold, not as the product model. The school platform should be rebuilt around tenants, roles, academic structures, guardian relationships, and auditability before any pilot data is entered. The fastest safe path is not to rename current tables and screens; it is to introduce a clean Class Hero Hub domain beside or in front of the legacy family product, then remove household features from the school experience.

The foundations that must be correct from day one are tenant isolation, RBAC/ABAC, stable identifiers, history-preserving enrolments/assignments, guardian invitation security, audit logs, i18n/RTL architecture, and media/data protection. Messaging, feed, media processing, advanced reporting, mobile apps, SIS, SSO, attendance, portfolios, and AI can be phased, but their future needs should shape the schema now.

Top ten critical findings:

1. The current schema is family-scoped, not school-tenant scoped.
2. Parents currently award points; teachers/staff do not exist.
3. Household rewards, allowance, savings, jars, and redemptions must be removed.
4. There is no academic-year/class/subject/teaching-group model.
5. There is no guardian-student relationship model or school-controlled parent connection flow.
6. There is no import preview/dry-run/idempotent re-import system.
7. There is no messaging/feed/media-consent/file-storage architecture.
8. Current admin is bootstrap-email based, not scoped school/platform RBAC.
9. i18n exists, but product copy, dynamic content, notifications, CSVs, emails, and RTL school workflows need redesign.
10. A one-school pilot built without true tenancy would cause painful rework and data-protection risk.


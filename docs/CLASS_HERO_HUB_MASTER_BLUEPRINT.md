# Class Hero Hub — Master Implementation Blueprint

**Date:** 2026-07-07
**Author:** Claude (Fable 5), planning engagement — no code changed
**Repo:** `/opt/apps/class_hero_hub`
**Companion documents:** `docs/audits/CLAUDE_CLASS_HERO_HUB_AUDIT.md` and `docs/audits/CODEX_CLASS_HERO_HUB_AUDIT.md` (2026-06-16). Those cover the inherited system and competitor research in depth; this blueprint is the *decision and execution* document. Where this document and the audits disagree, this document wins — it reflects the 2026-07-07 product brief (points/behaviour is in scope, child views may come later, compliance analysis deferred).

**Current authority note (2026-07-16):** this blueprint remains historical/current context for the earlier CHH build sequence, but its messaging schema, §19, S15, and related S16 notification assumptions are **partially superseded**. The authoritative cross-repository Messaging v1 specification is
[`docs/planning/2026-07-messaging-v1-architecture-plan.md`](planning/2026-07-messaging-v1-architecture-plan.md).
Do not implement the simple `(student × teacher)`/plain-text/`message_reads` design below as the current product.

---

## 0. How to use this document

- Sections 1–13 are the audit, reuse analysis, and the target architecture (data model, tenancy, roles, permissions).
- Sections 14–28 are per-surface designs (panels, onboarding, messaging, feed, calendar, points, notifications, CSV import, navigation, API/frontend/backend changes).
- Sections 29–33 are test strategy, risks, deferrals, and implementation order.
- Section 34 is the vertical slice plan — the unit of work you feed to Codex.
- Section 35 contains the first five Codex prompts, ready to paste.
- Section 36 is the self-audit and missing-features list.

Rule of engagement for Codex: **one slice per prompt, never more.** Every slice ends with green `pytest`, green `npm run check` + `check:i18n`, and a working screen.

---

## 0a. Post-S4 checkpoint amendments (2026-07-07)

Recorded after the post-S4 checkpoint audit (`docs/audits/2026-07-07-post-s4-fable-checkpoint-audit.md`). Where these amendments conflict with §9/§15/§33 below, the amendments win — they reflect the implemented reality and decisions taken during S4.

1. **Branches/campuses are part of the school model** (contrary to §9 decision 6). `branch_campuses` is a first-class school-owned table; `class_sections.branch_campus_id` is required, with a self-healing default `MAIN` branch for one-campus schools; `memberships.branch_campus_id` (nullable) anchors future branch-local admin scope. Consequence for S7: the students CSV needs an optional `branch` column (default branch when absent).
2. **Education stages and a configurable grade/year label are part of S4.** `education_stages` is an optional school-defined grouping (`grade_levels.education_stage_id` nullable); `schools.grade_level_label` lets each school call levels Grade/Year/Form/Level/custom. Class sections use free-text `code`/`name` rather than §9's `label`/`display_name`.
3. **School setup lifecycle policy (all seven structure entities):**
   - **active** — visible in tables, offered in dropdowns, usable for new relationships;
   - **inactive** — visible/editable in tables, **not** offered for new relationships, existing references stay valid;
   - **archived** — hidden from normal tables and dropdowns, non-selectable, historical references stay valid (`include_archived=true` reaches them);
   - **recreating an archived natural key restores the archived row in place** (id preserved, fields refreshed, audit `*.restored`); active/inactive duplicates are rejected with specific 409 messages. Full unique constraints therefore stay correct — no partial indexes needed for these tables.
4. **Subject groups must support both section-specific and grade-level/cross-section groups** (streamed sets, electives drawing from several sections). The S4 implementation made `subject_groups.class_section_id` NOT NULL; amend to nullable with a nullable `grade_level_id` for context **before S5/S6 build on it** (pre-S5 "S4.9" fix #1).
5. **Homeroom teachers are represented by `staff_assignments` in S5** (role `homeroom`, referenced by *membership id*), never by direct user fields on class sections. The S4 placeholder `class_sections.homeroom_teacher_user_id` is to be dropped in the S5 migration.
6. **Magic-link email login may move earlier than S9** (before or alongside S5): Google-only login blocks non-Google teachers (Microsoft 365 schools) at S5 invite acceptance, the same way it would block guardians at S9. §36.2 anticipated this for parents; it applies to staff first.
7. **Known deviation:** backend tests currently run on SQLite (contra §10). Acceptable through S5–S6; a PostgreSQL test path is required by S7 (import upserts) and non-negotiable by S14 (partial unique indexes, concurrency suites).

---

## 0b. Product strategy amendments from post-S4 review (2026-07-07)

Full report: `docs/product/CLASS_HERO_HUB_PRODUCT_STRATEGY_NOTES.md`. Key plan-impacting decisions/recommendations recorded here:

1. **Treat WhatsApp as the main competitor**, not ClassDojo — the pitch is "the school gets back control of the channel", and every surface must beat the class WhatsApp group on control while not losing to it on immediacy or speed.
2. **Parent notification delivery is existential** and must be explored before/around guardian onboarding (S9), not deferred to native apps.
3. **Consider PWA web push** (with an "add to home screen" step built into guardian onboarding — required for iOS push) **and possibly WhatsApp Business API** for notification nudges; evaluate or explicitly reject the latter.
4. **Teacher flows must be phone-first** (amending §16's tablet-first framing) and optimised for **60-second posting** — budget flows in taps/seconds and treat regressions as P1.
5. **Safeguarding/admin visibility is a selling point**, especially for messaging (S15): admins can review threads, disclosed in-UI to both sides — decide before S15 ships.
6. **School branding (logo/accent colour) moves earlier**, around the parent-facing launch (~S10–S11), rather than the §31 deferral pile.
7. **Behaviour points (S14) must not block the first pilot** if posts/photos/diary/notifications are ready — the announcement/diary loop is the WhatsApp displacement; points can land mid-pilot.
8. **The pilot needs measurable week-4 success metrics** agreed in advance (e.g. ≥70% of classes posting ≥3×/week, ≥60% guardians linked, posts seen within 24h) — pilot as experiment, not deployment.
9. **Demo school seed data** (fictional bilingual school with full content) should be created after S6 — sales demo, screenshot factory, QA fixture, Playwright target.
10. **A data/privacy/export one-pager** (hosting location, access, retention, export, deletion, offboarding) should be written before serious school sales conversations.
11. **Product safety rule — silent import / no accidental outbound communication (binding for S7/S8 and all bulk tooling):** real school data may be imported for demo/pilot preparation, but bulk import must **never** send invites, magic links, notifications, emails, or WhatsApp messages by default. Imports create draft/unsent invite records only; contacting teachers or guardians requires an explicit, separately-confirmed go-live/release action showing who will be contacted and how many messages will go out. S7/S8 Codex prompts must state this rule; tests must assert an import run produces zero outbound sends. (Detail: strategy notes §20.)

---

## 1. Executive summary

The inherited system is a well-engineered single-family household app: FastAPI + SQLAlchemy + Alembic + PostgreSQL backend, SvelteKit (Svelte 5) + Tailwind frontend, Docker Compose + Caddy + pgBackRest deployment, English/Arabic i18n with RTL and a parity checker, 207 backend tests including PostgreSQL concurrency tests, and a genuinely good security posture (hashed single-use invite tokens, CSRF double-submit, fail-closed config validation, trusted-proxy handling).

What it does **not** have is the school domain. The only tenant is `Family`; there is no school, class, subject, teacher, student-guardian relationship, messaging, feed, media upload, CSV import, notification, or role system (admin = an env-var email list). Roughly 60–70% of the business logic (rewards, redemptions, allowance, savings jars, pet, streaks, school-bag packing, child device login) is household-specific and should be removed, not adapted.

**Strategy: keep the platform, replace the domain, in this repo.**

- Keep: the stack, deployment, i18n architecture, auth/CSRF/token machinery, config validation, test culture, ledger idempotency *pattern*, calendar recurrence *pattern*.
- Replace: the entire domain model. New school-rooted schema via a fresh Alembic baseline. Do **not** mutate `families` into `schools` — there is no Class Hero Hub production data to migrate, so a clean schema is free now and priceless later.
- Build in vertical slices (Section 34): each slice ships a usable capability, is small enough for a single Codex task, and keeps tests green.

MVP = one pilot school running: company admin creates the school → school admin imports classes/teachers/students via CSV → teachers invite parents via QR letters → teachers post announcements/photos, set homework/events, award behaviour points, and message guardians → parents see everything mobile-first in English or Arabic. That is slices S1–S16, in order.

---

## 2. Existing system audit (concise)

Verified by direct inspection on 2026-07-07 (full detail in the two audit docs):

**Architecture.** Monolithic FastAPI app (`backend/app`, ~5,400 lines of routes+services), 17-table SQLAlchemy model (`models.py`), Alembic (6 revisions, PostgreSQL production / SQLite dev path retained), SvelteKit static-adapter frontend with client-side fetch only, Docker Compose (backend, frontend, postgres, postgres_restore), Caddy TLS proxy, pgBackRest WAL backups.

**Auth & sessions.** Parents: Google OAuth only → 30-day JWT in an HttpOnly cookie; CSRF double-submit cookie; admin = membership in `PARENT_EMAILS` env var. Children: QR link tokens (SHA-256-hashed, single-use, 24h expiry, rate-limited exchange) → 30-day device-session cookie. Suspension/revocation enforced per request via DB status checks.

**Domain (all family-scoped via `family_id`).** Children, points ledger (dual jars: spending/savings, 12 transaction types, partial-unique-index idempotency, reversals), rewards + redemption approval flow, allowance (real money, currency minor units), behaviour presets, calendar entries (event/task, daily/weekly recurrence, rewardable tasks, completion approval, weekly streak multipliers), school-bag items with pack-checks, pet progression, family invites, registration requests + approved-email allowlist.

**i18n.** `svelte-i18n`, EN+AR side by side in `frontend/src/lib/i18n/messages.ts` (2,477 lines), RTL via `dir` on `<html>`, parity checker script (`npm run check:i18n`). Backend emails are English-only.

**Tests.** 207 backend tests (incl. PG concurrency + FK suites), Playwright E2E (public/auth/child/visual), i18n parity gate, smoke scripts, documented QA harness.

**Docs.** Extensive but describe Family Hero Hub. Treat `README.md`, `PLAN.md`, `docs/PROJECT_STATUS.md`, `docs/ROADMAP.md`, manuals, and `AGENT_WORKFLOW.md` as inherited-system documentation only.

---

## 3. Reuse analysis — inherited capabilities useful for Class Hero Hub

| Inherited capability | Verdict | How it's used |
|---|---|---|
| Stack (FastAPI/SQLAlchemy/Alembic/PG/SvelteKit/Tailwind/Docker/Caddy/pgBackRest) | Keep as-is | Foundation for everything |
| Config validation (`database.py: validate_runtime_configuration`) | Keep, extend | Add new settings (platform admin emails, media limits) |
| CSRF double-submit + trusted-proxy middleware (`auth.py`, `security.py`) | Keep | Applies unchanged to new session types |
| Google OAuth flow (`routes/authentication.py`) | Keep, generalise | Becomes login for *users* (any role), not parents |
| QR token machinery (`child_auth.py`: hash, single-use, expiry, revoke, rate-limit) | Keep, repurpose | Becomes **guardian invite** exchange — the single most transferable feature |
| Invite-token pattern (`FamilyInvite`: token_hash/expiry/revoke/accept) | Keep, generalise | School-admin invites, teacher invites, guardian invites |
| Ledger idempotency pattern (partial unique indexes, reversal rows) | Keep the *pattern* | Behaviour point events + corrections |
| Calendar recurrence/occurrence logic (`calendar_service.py`) | Keep the *pattern* | Class diary items; audience changes from child→class |
| Soft-delete/status + audit columns idiom (revoked_by/at/reason) | Keep the idiom | All new entities |
| i18n catalogue + RTL + parity checker | Keep architecture | Content rewritten for school domain |
| Mobile-first parent UI patterns, Tailwind design system (`docs/DESIGN.md`) | Keep | Parent app reuses layout/card/modal patterns |
| Mailer (`mailer.py`) | Keep, extend | Invites, notifications digest; needs AR templates |
| Test culture + QA harness + Playwright setup | Keep | New domain tests replace old ones slice by slice |
| Backup/restore runbooks | Keep | Unchanged |

## 4. Inherited assumptions that must change / be removed

**Change (rename/extend):**
1. **Tenant = Family → Tenant = School.** New `schools` root; `family_id` scoping replaced by `school_id` everywhere.
2. **One user ↔ one family → global user with per-school memberships.** A guardian with children at two schools, or a teacher who is also a parent, must be one login.
3. **Admin = env email list → DB-backed roles.** Env list survives only as the bootstrap for the *first platform admin*.
4. **Parent awards points → teacher awards points.** Ownership of behaviour categories moves from parent to school.
5. **Calendar audience = one child → audience = class/subject-group/school/student.**
6. **Points label config (`POINTS_LABEL` env) → per-school setting.**
7. **Timezone default `Asia/Muscat` on Family → per-school timezone/locale settings.**
8. **"School items" (bag packing) → "required items" attached to diary/calendar items.**

**Remove (household-economy; do not port):**
- Rewards + redemptions approval flow, allowance/currency, savings jars + maturity sweep, pet progression, weekly streak multipliers, school-bag packing, child device login (v1), self-service registration ("Join the Free Beta"), `ApprovedParentEmail` allowlist flow.
- Frontend routes: `/child/[id]`, `/allowance`, `/redemptions`, `/request-access`, `/child-link`, `/child-guide`, family-invite pages; household wording throughout `messages.ts`.

---

## 5. Product vision

Class Hero Hub is a **multi-school, mobile-first, English/Arabic-native classroom communication platform** for KG–12: schools onboard once, teachers reach every guardian in one place (announcements, photos, homework, behaviour recognition, direct messages), and parents get one login for all their children — across classes and even across schools.

Positioning against ClassDojo and peers: **school-governed, privacy-respecting, Arabic/RTL-native.** No public leaderboards, no student shaming, no parent-to-parent chat, school-controlled data. Gamification is a tool schools can opt into, not the product's identity. (Competitor detail: audit docs §9–§12.)

---

## 6. Recommended SaaS tenancy model

**Pooled multi-tenancy, shared schema, `school_id NOT NULL` on every tenant-owned row.**

- **App-layer enforcement from day one:** a single FastAPI dependency resolves `(user, active membership, school)` and every query goes through school-scoped helpers (the `family_scope.py` idiom, generalised). No route hand-rolls its own filter.
- **Cross-tenant tests from day one:** the test harness always seeds *two* schools and asserts School A actors get 404/403 on School B resources. This is the cheapest insurance available and is mandatory in every slice.
- **PostgreSQL RLS is deferred to a dedicated hardening slice (S20) before the second real school onboards.** Diverging from the June audits (which wanted RLS from commit one) deliberately: RLS adds session-variable plumbing to every request and complicates Codex-sized slices, and a single-pilot deployment with a two-school test harness gets 90% of the safety at 20% of the cost. The schema is designed so RLS can be switched on without schema change (every table already has `school_id NOT NULL`).
- **Global (non-tenant) tables:** `users`, `platform_admins`, plus cross-school linking tables (`guardian_links` carries `school_id` via the student; a user's memberships span schools).
- **School lifecycle:** `status ∈ {pending_setup, active, suspended, archived}` with actor/reason/timestamp columns (reuse the family suspension idiom). Suspension blocks all school members at the auth dependency, exactly as family suspension does today.

Single deployment, one Postgres — the current VPS topology is fine through the pilot and first few schools. Object storage, job queue, Redis, and replicas are scaling work, not MVP work (Section 31).

---

## 7. Core user roles

| Role | Scope | Login | Notes |
|---|---|---|---|
| **Platform admin** | Cross-school | Yes | Class Hero Hub staff. Bootstrap via `PLATFORM_ADMIN_EMAILS` env, then DB rows. |
| **School admin** | One school | Yes | Owner/administrator; can also hold teacher role. |
| **Teacher** | Assigned classes/subject groups within one school | Yes | The primary daily user. |
| **Guardian** | Linked students (any school) | Yes | One login, many children, mobile-first. |
| **Student** | Profile only | **No login in v1** | A record, not an account. Child-friendly views are a later, separate decision. |

A `memberships` row = `(user_id, school_id, role)`; a user may hold multiple rows (teacher at school A + guardian of students at schools A and B). Guardian "membership" is implied by having an active `guardian_link` to a student of that school — model it as a membership row too, created/removed automatically with links, so navigation and access checks have one source of truth.

Deferred roles (post-MVP): teaching assistant, coordinator (grade/department scope), substitute/cover teacher. The `memberships.role` string and date-bounded `staff_assignments` leave room for them without schema change.

## 8. Permissions matrix (MVP)

| Capability | Platform admin | School admin | Teacher | Guardian |
|---|---|---|---|---|
| Create/suspend schools | ✅ | — | — | — |
| Invite school admins | ✅ | ✅ (co-admins) | — | — |
| School settings, academic years | — | ✅ | — | — |
| Classes/subjects/groups CRUD, CSV import | — | ✅ | — | — |
| Invite/deactivate teachers | — | ✅ | — | — |
| Students CRUD, enrolments | — | ✅ | view own classes | — |
| Generate/revoke guardian invites | — | ✅ | ✅ (own classes) | — |
| Behaviour categories config | — | ✅ | — | — |
| Award/correct points | — | ✅ (any) | ✅ (own classes) | view own children |
| Class posts/photos | — | ✅ (any class) | ✅ (own classes) | view (linked classes) |
| School-wide announcements | — | ✅ | — | view |
| Diary items (homework/events/items) | — | ✅ (any) | ✅ (own classes) | view own children |
| Message guardians | — | ✅ (any student) | ✅ (own students) | reply; initiate to own child's teachers |
| View any student in school | — | ✅ | own classes only | own children only |
| Cross-school anything | audited actions only | — | — | own children across schools |

Enforcement: three reusable dependencies — `require_platform_admin`, `require_school_role(roles)`, and scope guards `require_teacher_of(class/group/student)` / `require_guardian_of(student)`. Never inline-filter in routes.

Platform admin explicitly does **not** browse school content (posts, messages, points) in MVP. Support/impersonation is deferred; when built, it must be explicit, time-boxed, and audited.

---

## 9. Data model recommendation

Design principles: `school_id NOT NULL` on every tenant row; enrolments and staff assignments are **date-bounded rows, never updated in place** (history survives class changes and year rollover); events (points, posts, messages) reference the context at the time; integer PKs internally, random opaque tokens for anything in a URL/QR.

```
users (global)                    id, email UNIQUE, name, google_sub, locale, status, timestamps
platform_admins (global)          user_id UNIQUE, granted_by, granted_at, revoked_at

schools                           id, name, name_ar, slug, timezone, locale_default, points_label,
                                  status, suspended_at/by/reason, settings JSONB, created_at
memberships                       id, school_id, user_id, role ('school_admin'|'teacher'|'guardian'),
                                  status, created_by, revoked_at/by  UNIQUE(school_id,user_id,role)

academic_years                    id, school_id, name, start_date, end_date, is_current
                                  UNIQUE(school_id, name)
grade_levels                      id, school_id, code ('KG1'…'G12'), sort_order  UNIQUE(school_id, code)
class_sections                    id, school_id, academic_year_id, grade_level_id, label ('A','B'),
                                  display_name ('Grade 1A'), homeroom_teacher_membership_id NULL,
                                  status  UNIQUE(school_id, academic_year_id, grade_level_id, label)
subjects                          id, school_id, name, name_ar NULL  UNIQUE(school_id, name)
subject_groups                    id, school_id, academic_year_id, class_section_id NULL, subject_id,
                                  name ('Grade 7B English')  — optional layer; KG/primary may not use it

staff_assignments                 id, school_id, membership_id (teacher), class_section_id NULL,
                                  subject_group_id NULL, role ('homeroom'|'subject'), valid_from,
                                  valid_to NULL  CHECK(section XOR group)
students                          id, school_id, external_ref NULL (SIS/import id), first_name,
                                  last_name, preferred_name NULL, dob NULL, gender NULL, status,
                                  created_at  UNIQUE(school_id, external_ref)
enrolments                        id, school_id, student_id, class_section_id NULL,
                                  subject_group_id NULL, valid_from, valid_to NULL
                                  (homeroom enrolment = section row; subject enrolment = group row)

guardian_invites                  id, school_id, student_id, relationship_hint NULL, token_hash UNIQUE,
                                  short_code_hash UNIQUE NULL, created_by, created_at, expires_at,
                                  revoked_at, used_at, used_by_user_id NULL
guardian_links                    id, school_id, student_id, user_id, relationship ('mother'|'father'|
                                  'guardian'|'other'), status, created_via ('invite'|'admin'),
                                  invite_id NULL, revoked_at/by  UNIQUE(student_id, user_id)

behaviour_categories              id, school_id, name, name_ar NULL, icon, points (+/-), kind
                                  ('positive'|'needs_work'), is_active, sort_order
point_events (append-only)        id, school_id, student_id, category_id NULL, points, note NULL,
                                  kind, awarded_by (membership), class_section_id NULL,
                                  subject_group_id NULL, occurred_at, reversed_by_event_id NULL,
                                  source_event_id NULL (for corrections; partial unique index —
                                  reuse ledger reversal pattern)

posts                             id, school_id, author_membership_id, audience ('school'|'section'|
                                  'group'), class_section_id NULL, subject_group_id NULL, kind
                                  ('post'|'announcement'), title NULL, body, is_pinned,
                                  published_at, edited_at, deleted_at
media_objects                     id, school_id, uploader_membership_id, storage_key, mime, bytes,
                                  width/height NULL, checksum, exif_stripped BOOL, created_at,
                                  deleted_at
post_media                        post_id, media_object_id, sort_order

diary_items                       id, school_id, kind ('homework'|'assignment'|'project'|'test'|
                                  'event'|'reminder'|'required_item'), audience ('school'|'section'|
                                  'group'|'student'), class_section_id NULL, subject_group_id NULL,
                                  student_id NULL, title, details NULL, date, due_date NULL,
                                  created_by, created_at, updated_at, cancelled_at

conversations                     id, school_id, student_id, teacher_membership_id,
                                  UNIQUE(school_id, student_id, teacher_membership_id)
                                  (participants derived: the teacher + all active guardians of student)
messages (append-only)            id, school_id, conversation_id, sender_user_id, body, sent_at,
                                  deleted_at
message_reads                     message_id, user_id, read_at  (drives unread badges; receipts later)

notifications                     id, school_id, user_id, kind, title, body, link_path, created_at,
                                  read_at, dedupe_key UNIQUE NULL
imports                           id, school_id, kind ('students'|'teachers'), filename, status
                                  ('staged'|'committed'|'discarded'), uploaded_by, created_at,
                                  committed_at, summary JSONB
import_rows                       id, import_id, row_number, raw JSONB, action ('create'|'update'|
                                  'skip'|'error'), errors JSONB NULL, applied_entity_id NULL

audit_logs (append-only)          id, school_id NULL, actor_user_id, action, entity_type, entity_id,
                                  detail JSONB, created_at
```

> **Historical Messaging S15 schema:** the three messaging rows above are retained only to preserve
> the original blueprint. They are superseded by the participant/access-history, external-FHH-parent,
> media, receipt, policy, outbox, moderation, and audit schema in the 2026-07 Messaging v1 plan.

Key modelling decisions and why:

1. **Grade level and section are separate.** "Grade 1A" is `grade_level=G1` + `label=A`. Rollover, reporting, and subject-group defaults all key off grade level; a single free-text class name can't support that.
2. **Subject groups are an optional layer.** KG–6 with one homeroom teacher never needs them; Grade 7–12 departmentalised teaching does. A student's homeroom enrolment is required; subject-group enrolments are added only where the school uses them. Don't force every school through subject setup.
3. **Conversations are (student × teacher), not (parent × teacher).** All guardians of the student see the same thread — this matches how schools think ("about Sara"), gives two-parent families equal visibility for free, and structurally prevents parent-to-parent chat.
4. **`point_events` is append-only with correction rows**, reusing the FHH ledger's partial-unique-index idempotency trick — but with no jars, no balances-as-currency, no redemption.
5. **`users` is global; `memberships` and `guardian_links` are the tenancy bridges.** This is what makes "one parent login, children at different schools" work.
6. **No Campus, Terms, houses/teams, attendance tables in MVP** — all are additive later (Section 31).

## 10. Database migration strategy

- **Fresh Alembic baseline.** Squash to a single new initial revision containing only the Class Hero Hub schema. The six FHH revisions and household tables are dropped — the PoC database contains nothing worth keeping. Archive the old schema knowledge in git history.
- **No data migration.** There is no Class Hero Hub production data. Do not write `families→schools` ETL.
- **PostgreSQL-only for new work.** Drop the SQLite runtime path and `Base.metadata.create_all` bootstrapping for the new schema; tests run against PostgreSQL (the repo already has PG test patterns). This removes a whole class of partial-index/`func` divergence bugs.
- Practical sequencing: the new baseline lands in slice S1 with the identity/tenancy tables; each subsequent slice adds its tables in its own revision. Household tables are dropped in S2.

## 11. New entities required

All tables in §9 are new. Priority order: `users`, `schools`, `memberships`, `platform_admins`, `audit_logs` (S1) → structure tables (S4) → `students`, `enrolments`, `staff_assignments` (S5–S6) → `imports`/`import_rows` (S7) → `guardian_invites`/`guardian_links` (S9) → `posts`/`media_objects` (S11–S12) → `diary_items` (S13) → `behaviour_categories`/`point_events` (S14) → `conversations`/`messages`/`message_reads` (S15) → `notifications` (S16).

## 12. Existing entities to rename / extend / remove

- **Remove models + routes + services + frontend:** `Family`, `FamilyInvite`, `Child`, `ChildDeviceInvite`, `ChildDeviceSession`, `ChildAllowanceSetting`, `CalendarEntry`/`CalendarCompletion` (pattern preserved, table replaced), `SchoolItem`, `SchoolItemCheck`, `WeeklyStreak`, `LedgerTransaction`, `RedemptionRequest`, `PetProgress`, `PresetBehaviour`, `Reward`, `RegistrationRequest`, `ApprovedParentEmail`; routes `rewards, redemptions, allowance, presets, school_items, child_*, registration, family, children, ledger, calendar (family version)`; services `allowance_service, rewards_service, school_items_service, points_service (family version), calendar_service (family version)`; `currencies.py`; the savings-maturity worker in `main.py`.
- **Rename/generalise:** `ParentUser` → `User` (new table; the Google OAuth + JWT cookie flow is retained nearly verbatim); `get_current_parent` → `get_current_user`; `PARENT_EMAILS` → `PLATFORM_ADMIN_EMAILS` (bootstrap only); `family_scope.py` idiom → `school_scope.py` dependencies; `child_auth.py` token functions → `invite_tokens.py` (generic hash/issue/exchange/revoke used by all invite types).
- **Keep verbatim:** `security.py`, CSRF machinery, config validation (extended), mailer (extended), i18n plumbing, Playwright/QA scaffolding, `dev.py` QA-login pattern (retargeted at new roles).

## 13. Parent / student / teacher relationship model

Covered structurally in §9. The requirements from the brief, mapped:

- Parent has one login; multiple children → one `users` row, many `guardian_links`.
- Student has multiple guardians → many `guardian_links` per student (each invite letter carries two token slots, or admin reissues; see §18).
- Student: one homeroom (`enrolments` row with `class_section_id`), many subject groups (rows with `subject_group_id`), changes per year (date-bounded rows under an `academic_year` via the section/group).
- Teacher: many classes/subjects → many `staff_assignments`.
- Parent ↔ multiple teachers → conversations derived from the student's active teachers.
- Parents with children in different schools → memberships in both; school switcher in the parent UI.
- Teacher who is also a parent → two membership rows, one login, role switcher.

---

## 14. Company admin panel design (MVP-minimal)

Route namespace: `/platform` (desktop-first, plain).

- **Schools list:** name, status, created date, setup progress (admin joined? year created? students imported? guardians linked? — derived counts), teacher/student/class/guardian counts.
- **Create school:** name (EN/AR), timezone, default locale, admin email → creates school (status `pending_setup`) + school-admin invite email with accept link.
- **School detail:** re-send/revoke admin invite, add another admin, suspend/reactivate (with reason), notes field.
- **Nothing else.** No billing, no usage analytics dashboards, no impersonation, no support ticketing. Each is a later bolt-on; building them now is waste.

Auth: `platform_admins` table; bootstrap via `PLATFORM_ADMIN_EMAILS` env exactly like today's bootstrap-admin idiom (first login by a listed email auto-creates the row).

## 15. School admin panel design

Route namespace: `/school` (desktop-friendly, must work on mobile).

- **Setup checklist home** (drives onboarding): 1) school profile 2) academic year 3) classes 4) subjects (optional) 5) teachers 6) students (CSV or manual) 7) guardian invites. Progress states persist; this is the school admin's dashboard until setup completes, then becomes a summary + shortcuts.
- **School settings:** names, timezone, locale default, points label, behaviour categories, toggles (negative points on/off, parent replies on/off).
- **Academic years:** create; mark current; archive. (Rollover wizard is post-MVP, S19.)
- **Classes:** grid by grade level; create sections (bulk "Grade 1: A,B,C" creator); assign homeroom teacher; view roster; archive.
- **Subjects & groups:** subject list; per-section subject-group creation with teacher assignment (skippable entirely).
- **Teachers:** list, invite by email, revoke, view assignments, reassign.
- **Students:** list with search/filter by class; add/edit; move class (closes + opens enrolment rows); archive; per-student guardian status (0/1/2 linked) and invite management.
- **Imports:** upload → staged preview → fix/commit (Section 24).
- **Guardian access:** per class, print invite letters (bulk PDF/print view), see link status, revoke/reissue per student.

## 16. Teacher dashboard design

Route namespace: `/teach` (tablet/desktop-friendly, usable on phone).

- **Home = "My classes"**: card per class/subject group with roster count, unread messages badge, quick actions.
- **Class view (tabs):** Roster (tap student → award points / view guardians / message) · Feed (compose post/photo) · Diary (homework/test/event/required item) · Points (class log, quick multi-select award).
- **Award flow:** select student(s) or whole class → category grid (school-defined, icons, +/- values) → optional note → done. Two taps for the common case; this is the make-or-break teacher interaction, keep it fast.
- **Messages:** inbox of student-threads across classes, unread-first.
- **Guardian invites:** per-student QR/letter generation for their own classes (schools can restrict to admin-only via settings later).

## 17. Parent dashboard design (mobile-first)

Route namespace: `/home` (the default post-login surface for guardians).

- **Home:** child cards (name, class, school if multi-school) + a merged "Today/This week" strip (due homework, events, new posts, unread messages) across all children.
- **Child view (tabs):** Feed (class + school posts) · Diary (agenda list: homework/tests/events/required items, grouped by day) · Points (recent recognition, private to this family) · Messages (threads with this child's teachers).
- **Messages:** unified inbox across children; can initiate a thread with any current teacher of their child (if school setting allows).
- **Profile:** language (EN/AR), notification preferences, linked children, add-a-child (enter new invite code — supports siblings joining an existing account).
- No points economy, no rewards store, no pet. Recognition is presented as "what the teacher noticed", not a wallet.

## 18. QR / invite onboarding design

**MVP workflow (letter-token model — recommended):**

1. School admin (or teacher, per school setting) generates **per-student invite letters** — a printable page per student (bulk per class): school logo, student first name + class, EN/AR instructions, one QR code + short typed code (e.g. `CHH-7K3M-92QT`), expiry date (default 30 days).
2. Parent scans QR (or visits `/join` and types the code) → sees only "You've been invited to connect with a student at **{School}**" — **no student name pre-auth**.
3. Parent signs in / signs up (Google OAuth at MVP launch; email magic-link added in the same phase — see below) → token exchanged → sees student name + class for confirmation → picks relationship (mother/father/guardian) → `guardian_link` created, guardian membership ensured.
4. Existing logged-in parent adds a sibling via "Add a child" with the sibling's code — same exchange, same account.

Security semantics (all inherited from `child_auth.py` and kept): tokens hashed at rest, expiring, revocable, rate-limited exchange, audited. **One token = one guardian slot.** Each student gets two independent active invites by default (two guardians); admin can issue more. A used/lost/expired letter is handled by revoke + regenerate from the student page — reissue invalidates nothing else.

Design decisions, per the brief's questions:

- **No manual teacher approval step.** Possession of a per-student token *is* the authorization — the school handed the letter to the family. An approval queue adds friction for zero security (the approver has no way to verify who is asking). Wrong-child linking is prevented by per-student tokens + the post-auth confirmation screen; misdelivered letters are handled by revoke.
- **Classroom-poster QR: rejected for MVP.** A class-wide displayed code is claim-based ("I am Sara's mother") and *does* require approval + identity checking, which schools will do badly. Revisit later as "request access" mode with admin approval, for lost-letter recovery at scale.
- **Lost letters / device changes:** reissue letter; account is email-based so a new phone just logs in again.
- **Parents without Google:** email **magic-link auth is part of the MVP auth slice** (S9 depends on it; `mailer.py` already exists). Do not ship guardian onboarding Google-only — in the GCC market a hard Google dependency will lose real families. Passwords: not offered (magic link + OAuth covers everyone with an email and avoids password storage entirely).
- **Future native app:** the QR encodes an HTTPS URL (`https://…/join?c=…`) so the same code works in browser and future app deep links.
- **Revoking access:** admin revokes a `guardian_link` (custody changes etc.); revocation takes effect on next request via the same status-check-per-request idiom used today.

## 19. Messaging architecture

> **Historical and superseded for implementation.** This section records the original S15 scope.
> Use [`docs/planning/2026-07-messaging-v1-architecture-plan.md`](planning/2026-07-messaging-v1-architecture-plan.md)
> for all current Messaging v1 decisions.

- **Model:** one thread per (student × teacher) — see §9 decision 3. School-admin↔guardian threads reuse the same table with an admin membership as `teacher_membership_id`.
- **MVP includes:** parent replies (per-school toggle, default on); teacher inbox grouped by class; guardian unified inbox; unread tracking (`message_reads`); plain text (no attachments); i18n UI. New-message email notification (best-effort, deduped by thread+hour).
- **MVP excludes:** read receipts shown to senders, quiet hours, machine translation, attachments, group-composed messages (announcements cover one-to-many), message search, edit/delete UX beyond soft-delete by admins.
- **Broadcast** ("message all parents in class/school") is **not messaging — it's an announcement post** (§20), optionally with "notify" flag. This keeps threads personal and prevents reply-storms. School-wide urgent messages: announcement with notification.
- Privacy guardrails: teachers can only open threads for students in their active assignments; guardians only for their linked children; no guardian↔guardian path exists in the data model at all; all messages school-scoped and retained (append-only, soft-delete) for safeguarding.
- Transport: plain REST + polling (parent app polls unread counts on navigation). No WebSockets in MVP.

## 20. Class space / photo feed architecture

- `posts` with audience school/section/group; teacher composes text + up to N photos; pinning for important notices; guardians see a merged feed per child (their sections/groups + school).
- **Media pipeline (MVP, deliberately simple):** upload → MIME + size validation → **EXIF/geo strip + re-encode via Pillow** → store on the existing `./data` volume under `media/{school_id}/{uuid}` → serve through an authenticated backend endpoint that checks the viewer's access to the post (no public URLs, no direct static serving). Thumbnails generated at upload (single derived size). S3-compatible storage is a later swap behind the same `media_objects` abstraction.
- **MVP excludes:** comments (biggest moderation liability — add later with approve-before-publish), reactions, video (storage/transcode cost), scheduled posts, per-student consent engine. Interim consent control: a per-student `media_opt_out` flag admins can set, surfaced as a warning chip on the composer roster. The full consent module (per-type, expiring, renewal) is a post-MVP differentiator — architecture note: keep `media_objects` separate from `posts` now so consent/moderation can attach to media later without migration.
- Deletion: author/admin soft-delete; file removal via periodic cleanup.

## 21. Calendar / homework / assignment architecture

- One entity, `diary_items`, with `kind` (homework/assignment/project/test/event/reminder/required_item) and `audience` (school/section/group/student). This mirrors how teachers think ("add to the class diary") and avoids four near-identical tables. Student-specific items supported via `audience='student'`.
- Parent view is an **agenda list** (grouped by day, mobile-first), not a month grid — month grids are poor on phones and the inherited week-strip pattern can be reused later. Teacher/class view: simple week list + add form.
- `date` = when it appears/happens; `due_date` for homework-like kinds. Required items ("bring art smock Thursday") are just a kind with a date.
- **MVP excludes:** recurrence (the FHH recurrence engine is proven and can be re-added when demanded), attachments, acknowledgements/completion tracking, ICS export, child-friendly view. Homework *submission* is explicitly out of scope — Class Hero Hub is communication, not an LMS.
- Notifications: new diary item → in-app notification to affected guardians; daily-digest email option (S16).

## 22. Points / behaviour architecture

- **School-managed `behaviour_categories`** (not per-teacher): positive ("Helping others +2") and `needs_work` ("Missing homework −1"), icons, values, active flags, EN/AR names. Seed a sensible default set on school creation so teachers aren't blocked on admin config. Teacher-level custom presets: later, if asked.
- **`point_events` append-only** with correction rows (undo = reversal event with reason; reuse the ledger partial-unique-index pattern so double-taps and double-undos are idempotent). Award to one student, multi-select, or whole class (one event per student, batched request).
- **Visibility:** parents see their own child's events (category, points, note, teacher, subject context). No class totals, no rankings, no leaderboards anywhere in v1. Negative points: per-school toggle (default on, since many GCC schools expect it), always framed as `needs_work`, notes visible to parents (teachers are told this at compose time — private staff notes are a later feature, don't mix them into parent-visible events).
- **Not ported:** rewards/redemption economy, jars, allowance, savings, pet, streak multipliers. If schools later want a rewards store or house/team points, they are additive modules on top of `point_events` — nothing in MVP blocks them.
- Reports: per-student recent log + simple weekly summary per class for teachers/admins. Anything more is post-MVP.

## 23. Notification model

- `notifications` table (in-app) + email via existing mailer. Kinds at MVP: new announcement/post, new diary item, new message, points summary (weekly, not per-event — avoid notification fatigue and behaviour-surveillance feel; per-event opt-in later), guardian-invite accepted (to admin).
- Badge counts computed from `notifications.read_at` and `message_reads`.
- Email: per-user preference `immediate | daily_digest | off` (default: messages immediate, everything else digest). Rendered in the recipient's locale (mailer needs AR templates + RTL email layout — real work, one slice).
- Dedupe: `dedupe_key` unique index (e.g. `msg:{thread}:{hour}:{user}`); fires best-effort in-request; a durable queue is a scaling concern, not MVP (the FHH background-loop pattern is available if a sweep is needed for digests).
- Web push / native push: deferred; the model above doesn't change when it arrives (push is another delivery channel off the same notification row).

## 24. CSV import design

**Two files, not one; not four.**

1. **Teachers CSV:** `email*, first_name*, last_name, name_ar` → creates invites + membership stubs.
2. **Students CSV:** `student_id*, first_name*, last_name*, grade*, section*, name_ar, dob, gender, guardian1_email, guardian2_email` → creates students, auto-creates grade levels + class sections on the fly ("G1"+"A" → Grade 1A), enrolments, and (if guardian emails present) pre-addressed guardian invites.

Rationale: one combined file forces schools to denormalise teachers onto student rows (error factory); four files (classes, subjects, students, links) forces schools to understand our schema. Classes fall out of the students file; subjects/groups are UI-driven (per §9 decision 2); guardian linking is primarily QR letters, with the optional email columns enabling emailed invites where schools have good parent-email data.

**Pipeline (staged, always):** upload → parse + validate every row (encoding incl. Arabic/UTF-8-BOM, required columns, duplicate `student_id` in-file and in-DB, unknown grade codes) → **staged preview**: counts (create/update/error), per-row error table, downloadable error CSV → admin fixes file and re-uploads, or commits valid rows (choice: "commit valid" or "all-or-nothing", default commit-valid) → committed import writes rows transactionally and logs to `audit_logs`. Re-import of the same file is idempotent: upsert by `(school_id, student_id)`; changed section → enrolment move (close+open), never duplicate.

Templates downloadable from the import screen (EN headers; AR column-description legend). Imports run in-request for MVP (school-scale files are hundreds to a few thousand rows); background jobs when file sizes prove it.

## 25. Navigation architecture

Role-based shells, one login, role/school switcher in the header for multi-role users:

- `/platform/…` — platform admin (schools list/detail).
- `/school/…` — school admin (checklist home, settings, years, classes, subjects, teachers, students, imports, guardian access).
- `/teach/…` — teacher (my classes, class tabs, messages).
- `/home/…` — guardian (children home, child tabs, messages, profile). Default landing for guardians; bottom-tab navigation on mobile (Home · Diary · Messages · Profile).
- `/join` — invite code entry/exchange (public). `/login` — shared.
- Public marketing pages (`/`, faq, contact, privacy, terms) — rewritten copy, structure kept.

Post-login routing: single membership → its shell; multiple → last-used with switcher. Header/i18n/language-selector components shared across shells.

## 26. API changes

- New routers under `/api`: `platform` (schools admin), `school` (settings/years/grades/sections/subjects/groups), `staff`, `students`, `imports`, `guardian-invites` + `/api/join/exchange` (public, rate-limited), `posts`, `media`, `diary`, `behaviour` (categories + events), `conversations`/`messages`, `notifications`, `me` (profile, memberships, children).
- Auth endpoints gain magic-link (`/api/auth/magic-link/request|verify`); Google OAuth retained; `/api/me` returns user + memberships + linked children (replaces the parent/family payload).
- Kill the household routers (S2). Keep `/api/health`, dev/QA login (retargeted to seed new-domain personas — the QA harness depends on it).
- Conventions: every tenant route resolves school context via dependency; scope guards from §8; idempotency via natural unique keys (point events correction pattern, import upserts, notification dedupe). No API versioning prefix yet — single consumer, pre-launch; add `/v1` when a native app ships.

## 27. Frontend changes

- Remove household routes/components (S2 list in §12); keep `+layout.svelte` skeleton, i18n plumbing, `lib/api.ts` fetch pattern, submitGuard, Tailwind config, design tokens.
- New route trees per §25. Componentise early: `RosterList`, `StudentChip`, `PostCard`, `DiaryItemCard`, `PointCategoryGrid`, `ThreadList`, `InviteLetterSheet` (print CSS), `CsvPreviewTable`, `SetupChecklist`.
- i18n: prune household keys, add school-domain keys EN+AR simultaneously (parity gate stays mandatory); keep the "user-entered content is never translated" policy; `dir="auto"` on user-content elements (post bodies, names, messages).
- Mobile-first is a hard requirement only for `/home`; `/teach` must be comfortable on tablet/phone; `/school` and `/platform` desktop-first but responsive.

## 28. Backend changes

- `models.py` → split into `models/` package per domain area as new schema lands (17 tables becomes ~30; one file will hurt).
- `auth.py`: `get_current_user`, membership resolution, `school_scope.py` dependencies, magic-link issuance/verification (token machinery from `invite_tokens.py`), platform-admin bootstrap.
- `invite_tokens.py`: generic issue/hash/exchange/revoke extracted from `child_auth.py` (used by school-admin invites, teacher invites, guardian invites, magic links).
- New services: `imports_service`, `points_service` (school version, ledger-pattern), `posts_service`, `diary_service`, `messaging_service`, `notify_service`, `media_service` (Pillow re-encode/EXIF strip), `letters_service` (invite letter data; rendering is a frontend print view).
- `main.py`: drop savings worker; wire new routers; keep CSRF middleware, CORS, proxy middleware, health.
- Config: add `PLATFORM_ADMIN_EMAILS`, `MEDIA_ROOT`, `MEDIA_MAX_BYTES`, magic-link settings; extend fail-closed validation accordingly. New Python deps: `Pillow` (media), a QR generator (`segno`, tiny) — QR can also be rendered client-side; prefer one place (backend letter endpoint returns token URL; frontend renders QR with a ~2KB lib in the print view).

---

## 29. Test strategy

- **Every slice ships its tests.** Backend: pytest against PostgreSQL (drop SQLite matrix for new domain). Frontend: `svelte-check`, i18n parity, Playwright smoke for the new surface.
- **Two-school harness (non-negotiable, built in S1):** shared fixtures seed School A + School B with full personas (admin, teacher, guardian, students). Every new endpoint gets: wrong-school actor → 404/403; wrong-role actor → 403; unassigned teacher → 403; unlinked guardian → 403.
- **Domain-critical suites:** invite lifecycle (issue/exchange/expire/revoke/reuse-blocked/rate-limit) — port the existing child-link tests; point-event correction idempotency + concurrency (port the PG concurrency approach); import staging (idempotent re-import, move-not-duplicate, error report); messaging governance (no guardian↔guardian path, scope checks); media (EXIF stripped, size/MIME rejected, unauthorized fetch blocked).
- **E2E golden path** (Playwright, QA-login seeded): platform admin creates school → admin sets up class → invites teacher → imports students → generates guardian invite → guardian joins → teacher posts/awards/messages → guardian sees all — in EN and AR.
- Keep the daily QA harness pattern (`scripts/qa/europe-dev-qa.sh`) retargeted as surfaces land.

## 30. Risks and edge cases

**Top risks:**
1. **S1 (identity refactor) breaks auth subtly** — mitigations: it's the first slice, smallest possible scope, port the existing parent-auth session tests to user-auth before touching routes.
2. **Family concepts leak into the school domain** (naming, "family_id" habits, economy semantics) — mitigation: S2 deletes household code *early* so Codex can't pattern-match on it.
3. **CSV import correctness** (duplicate students, re-import duplication, Arabic encoding) — mitigation: staged-always pipeline, upsert-by-external-id, dedicated idempotency tests.
4. **Cross-tenant leak** — mitigation: two-school harness in every slice; RLS hardening slice before school #2.
5. **Media mishaps** (EXIF/geo leakage, public URL guessing) — mitigation: strip+re-encode always, authenticated serving only, no static mount.
6. **Teacher adoption fails if awarding points or posting takes >10 seconds** — mitigation: UX budget on the award flow; pilot feedback loop.
7. **Notification fatigue → parents mute everything** — mitigation: digest defaults, weekly points summary, no per-event behaviour pings by default.

**Edge cases to test explicitly:** two guardians linking with the same email (second link attempt → "already linked" not error); divorced/custody guardian revocation; student changes class mid-year (old teacher loses access at `valid_to`, thread history retained but read-only for them); teacher leaves school (assignments closed, threads reassigned/visible to admin); sibling in a different school on one account; duplicate student names in one class (external_ref disambiguates); Arabic-only guardian on an English-default school; invite letter scanned twice (second scan → "already used" with recovery path); school suspension mid-session.

## 31. Things that should be delayed (post-MVP, in rough order of expected demand)

Attendance visibility · message machine-translation (EN↔AR — likely the first "wow" upgrade for this market) · read receipts + quiet hours · comments on posts (with approve-before-publish) · full media-consent module · recurrence on diary items + ICS export · acknowledgements ("seen by 18/24 parents") · academic-year rollover wizard (S19 — needed before year 2, not day 1) · RLS + durable job queue + S3 media + Redis rate limiting (S20 scaling gate before school #2 at real scale) · timetables · report cards/progress reports · house/team points and reward stores (school-opt-in) · student/child-friendly views · native apps + push · SIS integrations · billing/subscription management · platform analytics · teaching-assistant/coordinator/substitute roles · impersonation support tooling.

## 32. Things that should not be rebuilt

Google OAuth flow · JWT cookie session + CSRF machinery · token hash/issue/exchange/revoke mechanics · config validation · trusted-proxy middleware · rate limiter (fine in-process until multi-replica) · i18n system + parity checker · Tailwind design system + mobile patterns · mailer transport · Docker/Caddy/pgBackRest deployment · QA login harness + Playwright scaffolding · ledger idempotency technique · the `dev.py` seeding pattern.

## 33. Recommended implementation order

S1 identity/tenancy → S2 household removal + rebrand → S3 platform panel → S4 school structure → S5 teachers → S6 students → S7 student CSV → S8 teacher CSV (optional, can trail) → S9 magic-link + guardian QR onboarding → S10 parent home → S11 announcements/posts → S12 photos → S13 diary → S14 points → S15 messaging → S16 notifications → S17 AR/RTL completion pass → S18 guardian-access admin → **pilot** → S19 rollover → S20 hardening/RLS → school #2.

Dependency notes: S3–S8 are sequential-ish (each builds on the previous); S11–S15 are parallelisable after S10; S13/S14 don't depend on S11/S12. If pilot pressure demands cuts: S8 (teacher CSV — schools have few teachers, manual invite is fine), S16 email delivery (keep in-app only), and S17 can compress.

---

## 34. Vertical slice plan (Codex-ready)

Global conventions for every slice: work on a feature branch; do not touch `docker-compose.yml`, Caddy, `.env` handling, `postgres/`, backup config, or `scripts/qa` unless the slice says so; keep `npm run check:i18n` parity (add EN+AR together); every new endpoint gets two-school + role-scope tests.
**Standard validation:** `cd backend && python -m pytest tests -q` · `cd frontend && npm run check && npm run check:i18n && npm run build` · manual: `docker compose build backend frontend && docker compose up -d`.

---

### S1 — Identity & tenancy core
- **Goal:** `users`, `schools`, `memberships`, `platform_admins`, `audit_logs` tables (fresh Alembic baseline); Google OAuth logs into a `User`; membership resolution + scope dependencies; two-school test harness.
- **User value:** none visible yet — everything depends on it.
- **Files:** `backend/app/models.py` (new `models/` pkg), `auth.py`, `routes/authentication.py`, new `school_scope.py`, `alembic/versions/*` (new baseline), `backend/tests/` (new fixtures), `/api/me`.
- **DB:** new baseline revision with the five tables; household tables untouched (removed in S2).
- **Backend:** `get_current_user`, `require_platform_admin`, `require_school_role`, bootstrap from `PLATFORM_ADMIN_EMAILS`; audit-log write helper.
- **Frontend:** login works against new `/api/me` (memberships payload); temporary post-login "no role yet" page.
- **Tests:** port `test_parent_auth_session.py` semantics to user auth; two-school fixture; membership resolution; bootstrap admin.
- **Acceptance:** existing login UX works; a seeded platform admin authenticates; harness proves cross-school 403/404 scaffolding runs.
- **Must not touch:** household routes/tables (still present, still passing their tests where unaffected).
- **Risk:** HIGH (auth refactor). Do it alone, nothing else in the slice.

### S2 — Household domain removal & rebrand
- **Goal:** delete household models/routes/services/frontend (§12 list) + drop their tables (migration) + prune i18n keys + "Class Hero Hub" branding/copy on shell + marketing pages; retarget dev/QA login to seed new personas.
- **User value:** clean product surface; no family features visible.
- **Files:** wide but mechanical — `routes/`, `services/`, `models/`, `main.py`, `frontend/src/routes/`, `messages.ts`, `.env.example` (`APP_NAME`, remove `POINTS_LABEL` env), `dev.py`.
- **Tests:** delete household test files; suite green; Playwright public-pages spec updated.
- **Acceptance:** app boots, login works, no household route resolves (404), i18n parity passes, no "Family Hero Hub" string in UI.
- **Must not touch:** `security.py`, CSRF, config validation, deploy files.
- **Risk:** MEDIUM (large but mechanical; main risk is over-deletion — keep `invite_tokens` extraction from `child_auth.py` here).

### S3 — Company admin panel v1
- **Goal:** platform admin creates schools, invites school admins (email token invite), lists schools with status + counts, suspend/reactivate.
- **DB:** `school_admin_invites` (or generic `staff_invites` with role) revision.
- **Backend:** `routes/platform.py`; invite issue/accept using `invite_tokens`; suspension enforcement in auth dependency (school-suspended → 403 for its members).
- **Frontend:** `/platform` list + create + detail; `/invite/[token]` accept page (shared later by teacher invites).
- **Tests:** create/list/suspend; invite lifecycle; suspended-school member blocked; non-platform-admin 403.
- **Acceptance:** end-to-end: create school → email link (log/console in dev) → admin accepts → lands in empty school shell.
- **Risk:** LOW-MEDIUM. Depends on S1, S2.

### S4 — School structure
- **Goal:** academic years, grade levels, class sections (bulk creator), subjects, subject groups; school settings page; setup-checklist home.
- **DB:** structure tables revision (§9).
- **Backend:** `routes/school.py` CRUD with `require_school_role('school_admin')`.
- **Frontend:** `/school` shell + checklist + settings + years + classes + subjects screens.
- **Tests:** CRUD, unique constraints (duplicate section label), cross-school, non-admin 403.
- **Acceptance:** admin creates "2026–2027", KG1–G12 grades, sections A/B, optional subjects; checklist reflects progress.
- **Risk:** MEDIUM (widest CRUD surface; keep UI plain). Depends on S3.

### S5 — Teachers & assignments
- **Goal:** invite teachers by email; accept → teacher membership; assign to sections (homeroom) and subject groups; teacher sees "My classes" stub.
- **DB:** `staff_assignments` revision.
- **Backend:** staff routes; `require_teacher_of(...)` scope guard (first real use).
- **Frontend:** `/school/teachers`; `/teach` shell with class cards.
- **Tests:** invite lifecycle; assignment CRUD; teacher sees only assigned classes; date-bounded close-and-reopen on reassignment.
- **Risk:** MEDIUM. Depends on S4.

### S6 — Students & enrolments
- **Goal:** student CRUD, homeroom enrolment, class move (close+open), subject-group enrolment, roster views (admin + teacher).
- **DB:** `students`, `enrolments` revision.
- **Tests:** CRUD, move preserves history, roster scope (teacher sees only own classes), cross-school.
- **Acceptance:** admin adds students to Grade 1A; teacher's class card shows roster.
- **Risk:** LOW-MEDIUM. Depends on S5.

### S7 — CSV import v1 (students)
- **Goal:** staged students-CSV pipeline per §24 (upload → validate → preview with per-row errors → commit-valid; idempotent re-import; auto-create grades/sections; error CSV download; template download).
- **DB:** `imports`, `import_rows` revision.
- **Backend:** `imports_service` + routes; UTF-8/BOM/Arabic handling.
- **Frontend:** `/school/imports` upload + preview table + commit.
- **Tests:** the §29 import suite (idempotency, move-not-duplicate, bad rows, encoding).
- **Risk:** HIGH (correctness-critical). Depends on S6. Guardian-email columns can land in S9.

### S8 — CSV import v2 (teachers) — *optional, may trail*
- **Goal:** teachers CSV reusing the S7 pipeline (kind='teachers'); creates invites.
- **Risk:** LOW-MEDIUM. Depends on S7, S5.

### S9 — Magic-link auth + guardian QR onboarding
- **Goal:** email magic-link login; guardian invites (per-student, two slots, QR + short code); printable letter view (EN/AR, print CSS); `/join` exchange; `guardian_links`; sibling "add a child"; revoke/reissue from student page.
- **DB:** `guardian_invites`, `guardian_links` revision.
- **Backend:** magic-link endpoints; `/api/join/exchange` (public, rate-limited — port child-link exchange + its tests); guardian membership auto-management.
- **Frontend:** `/join`, letter print view, guardian confirmation step (relationship picker), `/school/students/[id]` guardian panel.
- **Tests:** full invite lifecycle; **no student PII before auth**; two-guardian; sibling add; revoke ends access; rate limit.
- **Acceptance:** printed letter → scan → sign in with plain email → child linked and visible.
- **Risk:** MEDIUM (mechanism proven; magic link is the new part). Depends on S6.

### S10 — Parent home (mobile-first)
- **Goal:** `/home` guardian shell: child cards, child view tab scaffold, profile (language), bottom-tab nav, multi-school switcher.
- **Tests:** guardian sees only linked children; Playwright mobile-viewport smoke; AR/RTL render.
- **Risk:** LOW. Depends on S9.

### S11 — Announcements & class posts (text)
- **Goal:** `posts` (text, pin, audiences school/section/group); teacher composer in class view; school-admin school-wide composer; guardian feed per child + school.
- **Tests:** audience correctness (guardian of 1A doesn't see 1B), scope guards, pin ordering.
- **Risk:** LOW-MEDIUM. Depends on S10 (view) + S5 (author scope).

### S12 — Photos on posts
- **Goal:** media pipeline per §20 (validate → EXIF-strip re-encode → `./data/media/{school}` → authenticated serving + thumbnail); composer photo attach; `media_opt_out` flag on students + composer warning chip.
- **DB:** `media_objects`, `post_media` revision + student flag.
- **Tests:** EXIF removed (fixture with GPS data), MIME/size rejection, unauthorized fetch 403, opt-out warning logic.
- **Risk:** MEDIUM-HIGH (first upload path — security-sensitive; review this one yourself, don't rubber-stamp Codex). Depends on S11.

### S13 — Diary v1 (homework/tests/events/required items)
- **Goal:** `diary_items` CRUD (teacher: section/group/student audiences; admin: school); parent agenda view grouped by day; teacher week list.
- **Tests:** audience scoping, due-date ordering, student-specific item visible to right guardians only.
- **Risk:** MEDIUM. Depends on S10.

### S14 — Behaviour points v1
- **Goal:** `behaviour_categories` (school config UI + seeded defaults EN/AR) + `point_events` (award single/multi/class, note, subject context; undo-with-reason as reversal); parent per-child recognition view; teacher class log; per-school negative-points toggle.
- **Tests:** correction idempotency + concurrency (port PG pattern), scope (unassigned teacher 403), parent sees own child only, toggle hides negative categories.
- **Risk:** MEDIUM. Depends on S6 (+S10 for parent view).

### S15 — Messaging v1

**Superseded implementation definition:** the goal/DB/tests below are historical. The current
Messaging v1 is split into the independently testable slices in
[`docs/planning/2026-07-messaging-v1-architecture-plan.md`](planning/2026-07-messaging-v1-architecture-plan.md)
§22.

- **Goal:** (student × teacher) threads per §19; teacher inbox; guardian unified inbox + initiate; unread tracking; per-school replies toggle; admin threads.
- **DB:** `conversations`, `messages`, `message_reads` revision.
- **Tests:** governance suite (no guardian↔guardian path constructible, ex-teacher loses write at assignment end, both guardians see thread), unread counts, scope.
- **Risk:** HIGH (most privacy-sensitive surface). Depends on S9/S10.

### S16 — Notifications v1
- **Goal:** `notifications` + badges; email (immediate/digest/off prefs; message-immediate default; weekly points summary; AR email templates); dedupe keys.
- **Tests:** fan-out correctness, dedupe, prefs honored, locale rendering.
- **Risk:** MEDIUM. Depends on S11–S15 (event sources).

### S17 — Arabic/RTL completion pass
- **Goal:** full AR catalogue for new domain (native review), `dir="auto"` on user content, logical CSS properties audit, AR Playwright smoke, AR invite letters + emails polish.
- **Risk:** LOW (but schedule real native-speaker review time). Depends on all UI slices.

### S18 — Guardian access management
- **Goal:** school-admin dashboards for link status (per class: 0/1/2 guardians linked), bulk letter regeneration, revoke flows, guardian list per student.
- **Risk:** LOW. Depends on S9.

### S19 — Academic year rollover (post-pilot)
- **Goal:** wizard: create next year → map sections → bulk-promote enrolments (close+open) → carry/confirm staff assignments → archive old year; dry-run preview.
- **Risk:** HIGH (history correctness). Needed before year 2.

### S20 — Hardening for school #2 (post-pilot)
- **Goal:** PostgreSQL RLS policies on tenant tables + session-context plumbing; media to S3-compatible storage; durable job queue for notifications/imports if volumes demand; pen-test pass; per-tenant export.
- **Risk:** HIGH. Gate for scaling beyond pilot.

---

## 35. First five Codex prompts

Prepend to every Codex prompt (per the delegation policy):

> *Coding philosophy: write the minimum code that actually works. Reuse existing helpers/patterns in this repo before writing new ones; prefer stdlib and already-installed deps; no new dependencies unless stated. Never cut corners on validation, error handling, security, or tests. Follow existing code style (FastAPI deps, SQLAlchemy models, pytest patterns, svelte-i18n EN+AR parity).*

Model guidance: prompts 1, 2 and 5 → `gpt-5.5`; prompts 3 and 4 → `gpt-5.5` first time (they're wide), drop to `gpt-5.4-mini` only for follow-up fixes.

---

**Prompt 1 — S1a: identity/tenancy schema + fixtures (backend only, no auth wiring yet)**

> Task: Create the Class Hero Hub identity/tenancy foundation in `/opt/apps/class_hero_hub`. Read `backend/app/models.py`, `backend/app/database.py`, `alembic/versions/`, and `backend/tests/test_parent_auth_session.py` first to learn conventions.
> 1) Add new SQLAlchemy models in a new package `backend/app/models_school/` (do NOT modify existing `models.py`): `User` (id, email unique+indexed, name, google_sub unique nullable, locale default 'en', status default 'active', created_at, last_login_at), `School` (id, name, name_ar nullable, slug unique, timezone default 'Asia/Muscat', locale_default 'en', points_label default 'Points', status default 'pending_setup', suspended_at/suspended_by_user_id/suspend_reason, created_at), `Membership` (id, school_id FK, user_id FK, role string, status default 'active', created_by_user_id, created_at, revoked_at, revoked_by_user_id; UNIQUE(school_id,user_id,role)), `PlatformAdmin` (id, user_id FK unique, granted_by_user_id nullable, granted_at, revoked_at), `AuditLog` (id, school_id FK nullable, actor_user_id FK, action string, entity_type string, entity_id int nullable, detail JSON, created_at; append-only, no updates). Use the timestamp/status column idioms from the existing models.
> 2) Add one Alembic revision creating exactly these five tables (do not touch existing tables or revisions).
> 3) Add `backend/app/school_scope.py` with a helper `write_audit(db, actor, action, entity, detail, school_id=None)` and stubs `require_platform_admin`, `require_school_role` that raise NotImplementedError (wired in the next task).
> 4) Add `backend/tests/conftest_school.py` (or extend the existing conftest pattern) with a fixture that seeds two schools ("Alpha Academy", "Beta School") each with a school_admin user, a teacher user and memberships, plus one platform admin user. Add `backend/tests/test_identity_models.py` covering: unique email, unique (school,user,role), audit row write, and fixture integrity.
> Do NOT: modify any existing route, `auth.py`, `main.py`, frontend files, docker/Caddy/env files, or delete anything. Run `cd backend && python -m pytest tests -q` — all existing 207 tests plus yours must pass.

**Prompt 2 — S1b: auth generalisation (get_current_user + platform bootstrap + /api/me)**

> Task: Wire the new identity tables into auth. Read `backend/app/auth.py`, `backend/app/routes/authentication.py`, `backend/app/main.py`, `backend/app/models_school/`, `backend/app/school_scope.py`, and `backend/tests/test_parent_auth_session.py` first.
> 1) In the Google OAuth callback, additionally upsert a `User` row (email/google_sub/name, update last_login_at). Keep the existing ParentUser behaviour untouched and passing.
> 2) Add `get_current_user` in `auth.py`: resolves the JWT/cookie exactly like `get_current_parent` but returns the `User`; add settings key `PLATFORM_ADMIN_EMAILS` (default empty) to `database.py` Settings + `.env.example`; on `get_current_user`, if the user's email is in `PLATFORM_ADMIN_EMAILS` and no active `PlatformAdmin` row exists, create one (source: bootstrap) and write an audit log.
> 3) Implement `require_platform_admin` and `require_school_role(*roles)` in `school_scope.py` as FastAPI dependencies (school resolved from a path param `school_id` or `X-School-Id` header; membership must be active; suspended school → 403 with a clear detail message).
> 4) Add `GET /api/me/v2` returning `{user: {id,email,name,locale}, is_platform_admin, memberships: [{school_id, school_name, role}]}`. Leave `/api/me` as-is.
> 5) Tests in `backend/tests/test_user_auth.py`: cookie auth resolves user; bootstrap platform admin created once (idempotent); require_platform_admin 403 for normal user; require_school_role enforces role, active membership, wrong-school 403, suspended-school 403 — use the two-school fixture.
> Do NOT: remove or alter `get_current_parent` or any household route; no frontend changes; no changes to CSRF/session middleware. All tests must pass: `cd backend && python -m pytest tests -q`.

**Prompt 3 — S2a: remove household backend domain**

> Task: Remove the Family Hero Hub household domain from the backend now that identity v2 exists. Read `backend/app/main.py` router list, then delete: routes `children, ledger, redemptions, presets, rewards, family, child_devices, child_link, child_access, registration, calendar, child_calendar, school_items, allowance` and their service modules (`allowance_service, rewards_service, school_items_service, points_service, calendar_service`), `currencies.py`, `child_auth.py` (AFTER extracting — see step 2), the savings-maturity worker in `main.py`, and the corresponding household models in `models.py` (Family, FamilyInvite, Child, ChildDeviceInvite, ChildDeviceSession, ChildAllowanceSetting, CalendarEntry, CalendarCompletion, SchoolItem, SchoolItemCheck, WeeklyStreak, LedgerTransaction, RedemptionRequest, PetProgress, PresetBehaviour, Reward, RegistrationRequest, ApprovedParentEmail, and ParentUser last).
> 2) Before deleting `child_auth.py`, extract its generic token functions (generate_token, hash_token, TTL/cookie helpers, the issue/exchange/revoke shape, rate-limited exchange) into a new `backend/app/invite_tokens.py` with no child/family references; keep the `BoundedInMemoryRateLimiter` usage.
> 3) Add an Alembic revision dropping the household tables. 4) Update `routes/dev.py` QA login to mint a session for a seeded `User` (platform admin persona) instead of a ParentUser; keep the same token gating. 5) Update `routes/authentication.py` and `/api/me` to be User-based only (remove ParentUser upsert; `/api/me` may now serve the v2 payload). 6) Delete household test files; keep and adapt `test_security_hardening.py`, CSRF tests, and auth tests to the User model.
> Do NOT touch: `security.py`, `database.py` validation logic (except removing dead settings like POINTS_LABEL from Settings + `.env.example`), docker/Caddy files, frontend (separate task), `models_school/`.
> Acceptance: `cd backend && python -m pytest tests -q` green; `uvicorn` boots; `/api/health`, Google login, `/api/me`, and dev QA login work; no household route resolves.

**Prompt 4 — S2b: remove household frontend + rebrand shell**

> Task: Frontend counterpart of the household removal. Read `frontend/src/routes/+layout.svelte`, `frontend/src/lib/i18n/messages.ts`, `frontend/src/lib/api.ts`, and `scripts/check-i18n-parity.mjs` first.
> 1) Delete routes: `child`, `child-link`, `child-guide`, `allowance`, `redemptions`, `request-access`, `family-invite`, `parent-guide`, `calendar`, `redemptions`, and the `parent` dashboard page content (replace with a minimal authenticated placeholder that reads `/api/me` and says "No school role assigned yet" i18n'd). Keep: login, admin shell (empty for now), faq/contact/privacy/terms/safety-privacy as pages but with copy TODO markers.
> 2) Rebrand: app name "Class Hero Hub" everywhere user-visible (`app.name` etc. in messages.ts EN+AR: Arabic name: "كلاس هيرو هب" as placeholder pending review), update landing page hero copy to a short school-communication description (keep layout/components), footer description likewise.
> 3) Prune messages.ts: remove keys only used by deleted routes (verify by grep), keeping EN/AR parity — `npm run check:i18n` must pass.
> 4) Update Playwright: delete child/auth specs that target removed pages; keep public-pages spec passing against the new copy.
> Do NOT: change Tailwind config, design tokens, i18n plumbing (`lib/i18n/index.ts`), `submitGuard.ts`, or add new features. Acceptance: `npm run check`, `npm run check:i18n`, `npm run build` all pass; `npm run test:e2e:public` passes locally if the stack is up.

**Prompt 5 — S3: company admin panel v1**

> Task: Build the platform admin panel. Read `backend/app/school_scope.py`, `backend/app/invite_tokens.py`, `backend/app/mailer.py`, the old `FamilyInvite` pattern in git history if helpful, and `frontend/src/routes/admin/` for shell patterns.
> Backend: 1) New model `StaffInvite` (id, school_id FK, email, role — 'school_admin' for now, token_hash unique, invited_by_user_id, created_at, expires_at default 7 days, revoked_at, accepted_at, accepted_by_user_id) + Alembic revision. 2) `routes/platform.py` under `/api/platform`, all behind `require_platform_admin`: `POST /schools` (name, name_ar?, timezone, locale_default, admin_email → creates School pending_setup + StaffInvite + sends invite email via mailer with accept URL, logs audit), `GET /schools` (id, name, status, created_at, counts: memberships by role, students=0 for now, setup flags), `GET /schools/{id}`, `POST /schools/{id}/suspend` + `/reactivate` (reason required, audit), `POST /schools/{id}/invites` (resend/new admin invite), `DELETE /invites/{id}` (revoke). 3) Public `POST /api/invites/exchange` {token}: validates via invite_tokens (hashed lookup, expiry, single-use, rate-limited), requires an authenticated user, creates school_admin Membership, marks invite accepted, audit-logs. 4) Suspended-school 403 already enforced by require_school_role — add a test proving it end-to-end.
> Frontend: `/platform` route group behind is_platform_admin from `/api/me/v2`: schools table (name/status/counts/created), create-school modal, school detail page (invites list, resend/revoke, suspend/reactivate with reason). `/invite/[token]` page: if not logged in → login then return; on exchange success → redirect to a `/school` placeholder. All strings EN+AR.
> Tests (backend): full invite lifecycle (issue/exchange/expired/revoked/reused → 401-or-410 style errors), non-platform-admin 403 on every platform route, suspension blocks the school admin's membership, audit rows written. Use the two-school fixture.
> Do NOT: build any school-structure CRUD (next slice), billing, stats charts, impersonation. Acceptance: standard validation commands green; manual golden path works with the dev QA login as platform admin.

---

## 36. Self-audit

**Where this plan is weakest:**
1. **S1/S2 sequencing tension** — S1 adds new identity alongside the old, S2 deletes the old. During that window the codebase has two auth models. Kept deliberately (each slice stays testable) but do S2 immediately after S1; don't build features in the gap.
2. **Magic-link auth lands late (S9).** If the pilot school's parents are largely non-Gmail, pull it forward into S3-adjacent work. Cheap to reorder — it only depends on S1.
3. **In-request CSV commits and best-effort email** will eventually need a queue. Accepted consciously for pilot scale; S20 exists for the correction.
4. **Media on local disk** couples storage to the single VPS. Fine for a pilot; the `media_objects` abstraction is the escape hatch. Do not let a second school onboard with heavy photo use before S20.
5. **Diary without recurrence** may frustrate teachers with weekly PE-kit reminders — first candidate to pull forward from §31; the FHH recurrence engine makes it cheap.
6. **No pilot-school validation yet.** Before S4 is built, walk one real school's structure (grades, sections, subject teaching pattern, bilingual naming) through the §9 model on paper.
7. **RLS deferral** is a judgment call that trades absolute DB-level safety for slice velocity, backed by the two-school test harness. If you're uncomfortable, S20's RLS work can run any time after S6 — schema is ready for it.

**Where the family code may fight the school model:** the one-user-one-family assumption in any surviving helper (hunt for `family_id` after S2); SQLite-conditional code paths; i18n keys with household semantics reused for speed ("child" vs "student" — don't); the parent-launcher UI patterns tempting a "children-first" teacher UI (teachers think classes-first).

**Features you didn't mention that schools/teachers/parents will expect** (plan explicitly, mostly as §31 deferrals): attendance visibility (most-requested parent feature after messaging) · timetable view · report cards/term reports · message translation EN↔AR · "seen by X parents" acknowledgements · teacher absence/substitute handling (threads and classes need a cover path) · school branding (logo/colours on letters and app) · data export for the school (their data, they'll ask) · parent-teacher conference booking (Bloomz's wedge feature) · fee/payment reminders (common ask in private schools; firmly out of scope until core is solid) · staff-only notes on students (keep separate from parent-visible events — flagged in §22) · WhatsApp-style broadcast expectations (educate schools: announcements + notifications replace the class WhatsApp group — this is actually the core sales pitch in the GCC).

**Overbuilt risk check:** subject groups (mitigated: optional layer); staged imports (worth it — import errors are the #1 onboarding killer); per-student invite letters (worth it — the security model depends on them). **Underbuilt risk check:** messaging (no attachments may bite — parents photograph forms; add image attachments soon after pilot feedback); notifications (digest-only defaults may under-notify — watch pilot engagement).

---
*End of blueprint.*

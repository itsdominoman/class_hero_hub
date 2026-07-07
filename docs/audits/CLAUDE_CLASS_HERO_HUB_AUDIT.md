# Class Hero Hub — Strategic & Technical Audit

**Audit date:** 2026-06-16
**Auditor:** Claude (Opus 4.8), read-only engagement
**Subject repository:** `/opt/apps/class_hero_hub` (a clone of Family Hero Hub)
**Proof-of-concept URL:** https://class.familyherohub.com
**Status of this document:** Report only. No code, schema, configuration, secrets, or deployment was changed.

---

## Reading guide — evidence labelling

Throughout this report, claims are tagged so you can weigh them:

- **[FACT]** — Confirmed by direct inspection of this repository, or by a cited public source.
- **[INFERENCE]** — A reasonable conclusion drawn from evidence, not directly stated.
- **[RECOMMENDATION]** — A product or engineering proposal.
- **[OPINION]** — My own judgement call, offered bluntly and open to challenge.

External research is cited inline with links and collected in the Sources section (§ end). All codebase claims reference files by path.

A blunt framing up front: **this is a single-tenant household app with a school-shaped paint job on the proof-of-concept domain.** The data model has exactly one tenant type — the `Family` — and almost every monetisable school concept (multi-school isolation, rosters, staff roles, behaviour categories, messaging, feed, media, consent, CSV import) does not exist yet. The honest path to a ClassDojo competitor is **a new schema and new domain services**, reusing the *infrastructure and engineering discipline* of this repo rather than its *domain model*. That is the through-line of everything below.

---

## 1. Executive summary

**[FACT]** Class Hero Hub is currently Family Hero Hub with a renamed test hostname (`git log`: commit `5c63ea4 Configure Class Hero Hub test hostname`). The application code, data model, routes, and UI are unchanged household-app code: parents award points to their own children, children redeem rewards, manage allowance/savings, pack a "school bag", and a gamified dragon pet levels up.

**[FACT]** The tenant boundary in the entire system is the `Family` (`backend/app/models.py`). There is no `School`, no `Organisation`, no `Tenant`, no campus, no academic year, no class, no subject, no enrolment, no staff role table. Authorisation is "same `family_id`" plus a hard-coded super-admin email allowlist (`PARENT_EMAILS` env var, `backend/app/auth.py`).

**[FACT]** Entire product pillars required by the brief are **absent**: messaging, class/school feed, media/attachments, media consent, comment moderation, safeguarding, CSV import, notifications, object storage, reporting, real RBAC, and tenant isolation. There is no file upload path anywhere in the backend.

**[OPINION]** The engineering *quality* of what exists is genuinely good for a household app — careful ledger idempotency, partial unique indexes, CSRF double-submit, fail-closed config validation, 207 tests including PostgreSQL concurrency tests, pgBackRest backups. **Do not throw the engineering culture away.** But the *domain* is the wrong domain. Roughly 60–70% of the existing business logic (rewards, allowance, savings, jars, pet, streaks, school-bag) is household-specific and should be deleted, not adapted.

**[RECOMMENDATION]** Treat this as a **greenfield multi-tenant build on a reused platform**: keep the stack (FastAPI + SQLAlchemy + Alembic + PostgreSQL + SvelteKit + Docker + Caddy + pgBackRest), keep the auth/CSRF/rate-limit/config-validation scaffolding as reference, and design a new `school`-rooted schema with PostgreSQL Row-Level Security from commit one. Reuse the QR-onboarding pattern (it is the single most directly transferable feature) for parent invitations.

**The five things that must be designed correctly before any implementation begins** (detail in §15–§19, §53):
1. The tenant model and isolation strategy (RLS + `school_id` on every row).
2. The school-structure graph (school→campus→year→term→grade→class→subject→teaching group→assignments→enrolments→guardianship), including history retention across academic-year rollover.
3. The identity/role model (multi-role staff, no global admin-by-env-email, parent ≠ family).
4. The invitation/guardianship security model (no student PII before auth).
5. The behaviour-points domain, deliberately stripped of all economy mechanics (no rewards/allowance/savings/redemption).

---

## 2. Product vision

**[RECOMMENDATION]** Class Hero Hub is a **multi-school, multi-language, safeguarding-first K–12 engagement platform**: positive-behaviour recognition, controlled school↔home communication, a moderated class/school feed, calendar & assignments, and media with explicit consent — architected as SaaS with strict tenant isolation, English + Arabic (full RTL) from day one, and no country-specific hard-coding.

**[OPINION]** The sharpest available wedge against ClassDojo is **trust and governance, localised for the GCC/MENA and international-school market**. ClassDojo's most cited weaknesses are surveillance framing, public point display/shaming, weak consent, and US/English-centric data posture ([The Conversation](https://theconversation.com/classdojo-raises-concerns-about-childrens-rights-111033); [Manolev research summary, EducationHQ](https://educationhq.com/news/classdojo-harms-teachers-behaviour-management-approach-researcher-188825/)). A platform that is **Arabic-first, consent-first, no-public-leaderboard, school-governed, with data residency options** is a differentiated product, not a clone. Lead with governance, not gamification.

---

## 3. Current codebase summary

**[FACT] Stack.** Backend: FastAPI + SQLAlchemy + Alembic, PostgreSQL in production (SQLite legacy path still present for dev). Frontend: SvelteKit (Svelte 5 runes) + Tailwind 3, static adapter, client-side fetch only (no SSR data loading — `PLAN.md`). Deployment: Docker Compose (`backend`, `frontend`, `postgres`, `postgres_restore`), Caddy reverse proxy, pgBackRest WAL archiving.

**[FACT] Backend modules** (`backend/app/`): `models.py` (470 lines, 17 tables), `schemas.py` (673 lines, ~70 Pydantic models), `auth.py` (parent JWT/OAuth/CSRF), `child_auth.py` (QR device sessions), `security.py` (rate limiter, trusted-proxy middleware), `database.py` (config validation + settings), `mailer.py`, `main.py`. Routes: `admin, allowance, authentication, calendar, child_access, child_calendar, child_devices, child_link, children, dev, family, ledger, presets, redemptions, registration, rewards, school_items`. Services: `allowance_service, calendar_service, points_service, rewards_service, school_items_service, qa_seed`.

**[FACT] Data model (the entire tenancy story).** Tables: `families`, `parent_users`, `approved_parent_emails`, `children`, `family_invites`, `child_device_invites`, `child_device_sessions`, `child_allowance_settings`, `calendar_entries`, `calendar_task_completions`, `school_items`, `school_item_checks`, `weekly_streaks`, `ledger_transactions`, `redemption_requests`, `pet_progress`, `preset_behaviours`, `rewards`, `registration_requests`. **Tenant = `Family`.** Every domain row carries `family_id`; isolation is enforced only in application queries (e.g. `routes/family_scope.py: get_family_child_or_404` filters `Child.family_id == current_parent.family_id`).

**[FACT] Identity.** Parents authenticate **only** via Google OAuth (`authlib`, `routes/authentication.py`). There is no password, magic link, or non-Google option. Super-admin is whoever's email is in `PARENT_EMAILS` (`auth.is_admin` → `is_bootstrap_admin_email`). There is **no roles table**; "admin" is an env-var membership test. Children get device sessions via QR (`child_auth.py`) — a 30-day `child_session` cookie keyed to a SHA-256 token hash, rate-limited at exchange.

**[FACT] Quality signals.** 207 test functions across 24 test files, including PostgreSQL-specific concurrency and FK tests (`test_phase2_concurrency_pg.py`, `test_school_items_fk_pg.py`). Ledger has carefully engineered idempotency via partial unique indexes (`models.py` `uq_ledger_*`). Config validation fails closed on placeholder secrets, wildcard proxy trust, and missing production secrets (`database.py: validate_runtime_configuration`).

**[FACT] Tooling/i18n.** `svelte-i18n`, English + Arabic message catalogues (`frontend/src/lib/i18n/messages.ts`, 2,477 lines), RTL via `dir` attribute (`i18n/index.ts: localeDirection`), an i18n parity checker (`scripts/check-i18n-parity.mjs`).

---

## 4. Current deployment summary

**[FACT]** (from `docs/CURRENT_DEPLOYMENT.md`, `docker-compose.yml`):
- **US production:** `familyherohub.com`, Caddy, Docker Compose, PostgreSQL (cutover 2026-05-13), pgBackRest full+WAL backups with off-server mirror. Postgres is Compose-internal only; no public 5432.
- **Europe/France dev:** `dev.familyherohub.com`, same stack, PostgreSQL runtime, pgBackRest with restore rehearsal completed. Daily QA harness runs pytest + frontend build + Playwright + smoke.
- **Class PoC:** `class.familyherohub.com` — the renamed instance under audit.
- Caddy routes `/api/*` → `127.0.0.1:8000`, everything else → `127.0.0.1:5173`. Backend/frontend bound to localhost; Caddy terminates TLS.
- Backups: pgBackRest stanza `fhh`, `archive_mode=on`, off-server mirror, documented restore runbooks (`docs/operations/`).
- A Cloudflare Tunnel config exists but is documented as **not** the production method.

**[OPINION]** Deployment hygiene is a strength: real backups, restore rehearsals, internal-only DB, fail-closed config. **[RECOMMENDATION]** For multi-school SaaS this single-compose, single-VPS topology will not survive growth: no horizontal scaling, the rate limiter is in-process (see §41), no object storage, no queue/worker tier, no read replica. Plan for a managed Postgres (or HA pair), an object store, a job queue, and stateless app replicas behind a load balancer before onboarding more than a pilot.

---

## 5. Family Hero Hub features worth keeping

Categorisation legend: **Reuse** / **Reuse-with-small-changes** / **Major-redesign** / **Replace** / **Remove**.

| Capability | Verdict | Notes |
|---|---|---|
| Stack & build tooling (FastAPI/SQLAlchemy/Alembic/SvelteKit/Tailwind/Docker/Caddy/pgBackRest) | **Reuse** | Solid, modern, appropriate. Keep. |
| Config validation (`database.py: validate_runtime_configuration`) | **Reuse** | Fail-closed secret/proxy/origin checks are excellent. Extend, don't replace. |
| CSRF double-submit (`auth.validate_csrf_request`) | **Reuse-small** | Good pattern; broaden to all session types. |
| Trusted-proxy middleware (`security.py`) | **Reuse** | Correct handling of `X-Forwarded-*` behind Caddy. |
| QR device-onboarding flow (`child_auth.py`, `child-link/[token]`) | **Reuse-small** | The single most transferable feature → becomes **parent invitation** onboarding. Token hashing, single-use, expiry, revoke, rate-limit are all already right. |
| Ledger idempotency engineering (partial unique indexes, reversal/correction window) | **Reuse-pattern** | The *technique* is gold for point-event integrity & corrections; the *economy semantics* (jars/savings) go. |
| Invitation model (`family_invites`: token_hash, expiry, revoke, accept) | **Reuse-small** | Generalise to staff & guardian invites. |
| Soft-delete / status + audit columns pattern (revoked_by/at/reason, restored_by/at) | **Reuse-pattern** | Good instinct; formalise into a real audit-log table (see §17). |
| i18n catalogue + RTL + parity checker | **Reuse-small** | Architecture is right; content is household-flavoured (see §36). |
| Test discipline (207 tests, PG concurrency tests, Playwright) | **Reuse-culture** | Keep the bar. Most tests themselves will be rewritten with the domain. |
| Backup/restore runbooks & pgBackRest | **Reuse** | Mature; extend for multi-tenant export/restore. |
| Calendar engine (recurrence, occurrence expansion, completion) | **Major-redesign** | Concept reusable; must move from per-child/family to school/grade/class/group audiences. |

---

## 6. Family Hero Hub features to remove

**[FACT]** These are household-economy mechanics with no place in a school behaviour platform per the brief ("No rewards. No allowance. No savings. No jars. No household chores. No family-specific concepts."):

- **Rewards** (`Reward` model, `routes/rewards.py`, `rewards_service.py`, `/redemptions`) — **Remove.**
- **Redemptions / reward-request workflow** (`RedemptionRequest`, `routes/redemptions.py`) — **Remove.**
- **Allowance** (real-money: `ChildAllowanceSetting`, currency/minor-units/exponent, `routes/allowance.py`, `allowance_service.py`, `currencies.py`) — **Remove.** Converting behaviour points to money is explicitly out of scope and is a safeguarding/regulatory liability in schools.
- **Savings jar & maturity/bonus** (`JarType.savings`, `savings_deposit/withdrawal/maturity/bonus` transaction types, `mature_savings_deposits`, background sweep in `main.py`) — **Remove.**
- **Spending jar economy** (the dual-jar ledger concept) — **Remove**; replace with a non-economic behaviour-point event log.
- **Pet progression / dragon gamification** (`PetProgress`, `PetStage`, thresholds) — **Remove.** This is the kind of public/competitive gamification the brief warns against and that draws ClassDojo's strongest criticism.
- **Weekly streak bonus multiplier** (`WeeklyStreak`, `bonus_multiplier`) — **Remove** (or reconceive cautiously; see §24 opinion).
- **School Bag / school-prep packing** (`SchoolItem`, `SchoolItemCheck`, "pack for tomorrow") — **Remove** as a child-economy feature. (A "required items for an event/homework" concept survives in §33, but not this per-child weekday packing list.)
- **Child-facing dashboard as a kid login** (`/child/[id]`, child device sessions) — **Remove** the student-login concept for the initial release (brief: "Students do not need a personal login"). The QR mechanism is repurposed for parents.
- **Registration self-service for parents creating families** (`registration_requests`, "Join the Free Beta") — **Remove.** Teachers/parents must not create tenants; schools are onboarded (§21).

---

## 7. Family Hero Hub features requiring redesign

- **Tenancy** (`Family`) → **`School` organisation** with campus/year/term/grade/class/subject/group (§16). Major redesign, foundational.
- **Identity & roles** (Google-only parent + env-admin) → multi-provider auth + real RBAC with multi-role staff (§14, §18). Major redesign.
- **Calendar** (`CalendarEntry` per child/family) → audience-scoped events + homework/assignments with acknowledgement (§33). Major redesign.
- **Preset behaviours** (`PresetBehaviour`, parent-owned, parent-awards-points) → **school-managed behaviour categories** with positive/negative, configurable values, subject context (§24). Redesign ownership and scope.
- **Points ledger** (economy) → **behaviour point-event log** with corrections/audit but no balances-as-currency (§24). Redesign semantics, reuse integrity patterns.
- **Invitations** (`FamilyInvite`, `ChildDeviceInvite`) → **staff invites + guardian invites + QR access codes** (§19, §20). Redesign scope, reuse mechanism.
- **Admin** (`routes/admin.py`, env-allowlist) → **platform super-admin** vs **school admin** boundary (§28). Major redesign.

---

## 8. Current technical debt

**[FACT] / [OPINION]** Debt that will actively impede the school build:

1. **No tenant isolation at the database layer.** Isolation is application-query-only (`family_id == current_parent.family_id`). One missing filter = cross-tenant data leak. For a multi-school product holding children's data this is unacceptable; needs Postgres RLS (§15). **[FACT]** Confirmed: no `RLS`/`POLICY`/`tenant` anywhere in `backend`/`alembic`.
2. **Admin = env-var email list.** `is_admin` is `email in PARENT_EMAILS`. No DB-backed roles, no per-school admin, no scoping. Replace wholesale.
3. **Single-process in-memory rate limiter** (`security.py: BoundedInMemoryRateLimiter`). Resets on restart, not shared across replicas. Useless once you scale out; needs Redis or DB-backed limiting.
4. **Long-lived JWT, no rotation/refresh/revocation list.** `ACCESS_TOKEN_EXPIRE_MINUTES = 43200` (30 days) (`database.py`). Revocation relies on a DB status lookup each request, which works but the token itself can't be invalidated. No refresh-token rotation.
5. **No audit-log table.** "Audit" is ad-hoc columns (`revoked_by_parent_id`, etc.). A school platform needs a first-class immutable audit log (safeguarding/legal).
6. **No object storage / no uploads.** Entire media pillar is missing.
7. **Client-only data fetching** (no SSR loaders). Fine for an app shell; will complicate SEO for marketing/school-public pages and adds auth-token-in-browser exposure considerations.
8. **Background work is a bare asyncio loop** in the web process (`_savings_maturity_loop`). No durable queue, no retries, dies with the process. Inadequate for notifications/imports/media processing.
9. **Dual SQLite/Postgres code paths** (`ensure_runtime_schema`, `create_all` for SQLite). Carry-over legacy; drop SQLite for the school build to remove a whole class of "works on SQLite, breaks on PG" partial-index/`func` divergences.
10. **`/api/me` and auth assume one parent ↔ one family.** Parents can belong to only one `family_id`. Guardians with children in multiple schools break this immediately (§14).

---

## 9. ClassDojo current verified feature inventory

**[FACT]** (cited public sources, 2025–2026):

- **Behaviour points** with monster avatars; teachers award/subtract points for behaviours/skills; visual real-time feedback ([SoftwareAdvice](https://www.softwareadvice.com/classroom-management/classdojo-profile/); [The Conversation](https://theconversation.com/classdojo-raises-concerns-about-childrens-rights-111033)).
- **Class Story** — an Instagram-style class photo/video/text feed seen by students and connected parents ([KiwiBee guide](https://lemobee.com/en/blog/classdojo-for-teachers-guide)).
- **Messaging** between teachers and parents with **automatic translation into 30+ languages** ([GetApp](https://www.getapp.com/education-childcare-software/a/classdojo/)).
- **Student portfolios** — students/parents log in via QR scan; record video, journal entries, submit work as images ([KiwiBee students guide](https://lemobee.com/en/blog/classdojo-for-students-guide)).
- **Attendance & engagement tracking** ([SoftwareAdvice](https://www.softwareadvice.com/classroom-management/classdojo-profile/)).
- **Dojo Islands** — play-based learning/virtual world ([eLearning Industry](https://elearningindustry.com/press-releases/classdojo-for-districts-unveils-new-features-for-2025-26-school-year)).
- **ClassDojo Plus** — paid family subscription tier (since 2020) ([Capterra](https://capterra.com/p/124446/ClassDojo/)).
- **ClassDojo for Districts** (free) — automated rostering & SIS/ClassLink/SFTP sync (daily sync of students/staff/families), district messaging, IT admin/oversight ([PRNewswire](https://www.prnewswire.com/news-releases/classdojo-for-districts-unveils-new-features-for-202526-school-year-302510766.html)).
- **Sidekick** — AI assistant for lesson planning and admin/classroom workflows ([eLearning Industry](https://elearningindustry.com/press-releases/classdojo-for-districts-unveils-new-features-for-2025-26-school-year)).
- **Announced for 2026:** teacher-to-student messaging, attendance-based alerts via SIS, automated voice calls to households, integration with district social channels (Facebook/Instagram) ([eLearning Industry](https://elearningindustry.com/press-releases/classdojo-for-districts-unveils-new-features-for-2025-26-school-year)).
- **Scale claim (vendor-stated):** ~50M teachers/families, 180 countries, used in 95% of US K–8 schools ([EducationHQ](https://educationhq.com/news/classdojo-harms-teachers-behaviour-management-approach-researcher-188825/)).

**[FACT] Criticisms / risks** (academic & press): surveillance/"social-credit" framing and normalising student monitoring ([EducationHQ](https://educationhq.com/news/classdojo-harms-teachers-behaviour-management-approach-researcher-188825/); [EurekAlert](https://www.eurekalert.org/news-releases/732702)); compliance-over-learning and chilling effect ([The Conversation](https://theconversation.com/digitally-tracking-student-behaviour-in-the-classroom-encourages-compliance-not-learning-110181)); **public point display can shame/humiliate students** ([The Conversation](https://theconversation.com/classdojo-raises-concerns-about-childrens-rights-111033)); **inconsistent informed consent** and over-collection of data; data-protection concerns flagged by regulators ([LSE Parenting4DigitalFuture](https://blogs.lse.ac.uk/parenting4digitalfuture/2017/01/04/classdojo-poses-data-protection-concerns-for-parents/); [recent peer-reviewed analysis, Taylor & Francis 2025](https://www.tandfonline.com/doi/full/10.1080/17439884.2025.2553184)).

---

## 10. Competitor landscape

**[FACT]** (cited):

- **ClassDojo** — behaviour culture + parent messaging + class story; freemium + Plus + free Districts tier ([GetApp](https://www.getapp.com/education-childcare-software/a/classdojo/)).
- **Seesaw** — student-driven **portfolios** and academic output; activities, feedback, skill tracking; freemium. ClassDojo emphasises behaviour, Seesaw emphasises academic work ([Slashdot compare](https://slashdot.org/software/comparison/ClassDojo-vs-Seesaw/); [aiineducation](https://aiineducation.io/compare/classdojo-vs-seesaw)).
- **Bloomz** — broadest **ClassDojo replacement**: messaging + behaviour + class updates + conference scheduling + events; free for parents/teachers, premium for schools ([ClassPoint alternatives](https://www.classpoint.io/blog/classdojo-alternatives)).
- **Remind** — fast, private **messaging** at school/district scale; minimal feature surface beyond comms.
- **Google Classroom / Microsoft Teams for Education** — LMS/assignment + identity backbone (Google Workspace / Entra ID); **not** behaviour or family-engagement tools; relevant as integration targets and as the identity systems schools already run.
- **Behaviour systems (e.g. Hero/School Status, PBIS tools)** — discipline/PBIS tracking and analytics, often US-district-centric.

**[OPINION]** No incumbent owns **Arabic-first + safeguarding-first + multi-school governance for international/MENA schools**. ClassDojo and Bloomz are US-centric; Seesaw is portfolio-centric; Remind is comms-only. That gap is the wedge.

---

## 11. Feature comparison matrix

**[FACT]** for competitor columns (per §9–§10 sources); **CHH = recommended target** for Class Hero Hub.

| Capability | ClassDojo | Seesaw | Bloomz | Remind | CHH (target) |
|---|---|---|---|---|---|
| School setup / org onboarding | Yes (Districts) | Limited | Yes | District | **Yes — school-onboarded, no teacher self-create** |
| School-leader oversight | Yes (Districts) | Limited | Yes | Yes | **Yes — school admin + platform super-admin** |
| Teacher accounts | Yes | Yes | Yes | Yes | **Yes, multi-role** |
| Classes / rosters | Yes (SIS sync) | Yes | Yes | Yes | **Yes + CSV import + multi-subject/group** |
| Student profiles | Yes | Yes | Yes | Limited | **Yes (no student login in v1)** |
| Parent connection | Code/QR | QR | Code | Phone/email | **QR + typed code, expiring/revocable** |
| Behaviour points | Yes (public) | No | Yes | No | **Yes — private, no leaderboard** |
| Skills/behaviour categories | Yes | No | Yes | No | **Yes — school-managed, +/–, subject context** |
| Whole-school usage | Yes | Partial | Yes | Yes | **Yes** |
| Class feed/story | Yes | Yes | Yes | No | **Yes, moderated** |
| School feed/story | Yes (Districts) | No | Yes | Yes | **Yes, audience-scoped** |
| Messaging (teacher↔parent) | Yes | Yes | Yes | Yes | **Yes + quiet hours + safeguarding** |
| Parent-to-parent | No | No | Limited | No | **No (forbidden by brief)** |
| Translation | 30+ langs auto | Some | Some | Some | **EN/AR day 1, full RTL, extensible** |
| Events / calendar | Basic | Some | Yes | Reminders | **Yes + homework/assignments + acknowledgement** |
| Portfolios | Yes | **Yes (core)** | Some | No | **Defer (v2+)** |
| Attendance | Yes | No | Yes | No | **Defer (v2), integrate later** |
| Student login/access | Yes | Yes | Some | Limited | **No in v1 (parent is child-facing)** |
| Media consent | Weak/implicit | Weak | Weak | n/a | **Yes — explicit, per-child, per-type (differentiator)** |
| Notifications (push/email) | Yes | Yes | Yes | Yes (SMS) | **In-app + email + web push; quiet hours** |
| Reports | Yes | Yes | Yes | Limited | **Yes — behaviour & engagement, privacy-safe** |
| Moderation of parent comments | Limited | Limited | Limited | n/a | **Yes — approval-before-publish (differentiator)** |
| Privacy/data residency | US-centric | US-centric | US-centric | US-centric | **Region options (differentiator)** |
| AI assistant | Sidekick | Some | Some | Some | **Defer; later (translation/draft assist)** |
| Pricing | Free + Plus + free Districts | Freemium | Free + premium | Freemium | **Per-school SaaS (TBD)** |

---

## 12. Differentiation opportunities

**[RECOMMENDATION]** Differentiate on governance and locale, not on more gamification:

1. **Arabic-first + full RTL** as a first-class experience, not a translation afterthought. (CHH already has the i18n scaffolding; competitors auto-translate but aren't RTL-native.)
2. **Explicit, granular media consent** (per child, per use-type, expiring, revocable) with **teacher warnings before posting** — directly answers ClassDojo's consent criticism.
3. **Comment moderation by default** — parent comments require staff approval; structurally prevents parent-to-parent drift.
4. **No public leaderboards / no shaming** — points are private between school and the child's guardians. Directly counters the most-cited ClassDojo harm.
5. **Staff wellbeing controls** — quiet hours / communication windows enforced server-side; urgent/safeguarding override path.
6. **Strict tenant isolation + data residency options** — sellable to international schools, ministries, and privacy-sensitive markets (GCC, EU/UK GDPR).
7. **Safeguarding-grade audit & legal hold** — immutable logs, disclosure-ready exports.
8. **Honest behaviour model** — effort/improvement/concern framing, correction-with-reason, not a surveillance score.

---

## 13. Recommended Class Hero Hub scope

**[RECOMMENDATION]** MVP must-haves (pilot one school):
School onboarding; staff & role model; school structure (year/term/grade/class/subject/group); CSV import with dry-run; parent QR invitation & guardianship; behaviour points (private, school-managed categories, corrections, audit); teacher/parent messaging with quiet hours; class/school feed with moderated parent comments; media + consent; calendar + homework with acknowledgement; notifications (in-app + email); EN/AR + RTL; tenant isolation via RLS; audit log.

**Defer:** portfolios, attendance, native push, AI assist, analytics dashboards beyond basics, district/multi-campus federation reporting, calendar export, SIS integrations.

**Avoid (never build):** rewards/allowance/savings economy, pet/streak gamification, public leaderboards, parent-to-parent chat, student private messaging, student logins (v1).

---

## 14. Roles and permissions

**[RECOMMENDATION]** Replace the env-allowlist admin and the one-parent-one-family assumption with a DB-backed, school-scoped, multi-role model.

Roles (per brief): **Platform super-admin** (cross-tenant, tightly bounded), **School owner/admin**, **Senior leader / year coordinator / department coordinator** (scoped to grade(s)/department(s)), **Teacher**, **Teaching assistant**, **Parent/guardian**, **Student profile** (no login in v1).

Principles:
- A **person** can hold **multiple roles across multiple schools** (e.g. a teacher who is also a parent at another school). Membership is `(person, school, role, scope)` — not a single `family_id` on the user.
- **Scope-based permissions**: a teacher can act only on students in classes/groups they are assigned to (`teacher_assignments`). A year coordinator is scoped to their grade(s). Enforced at query time **and** by RLS predicates.
- **Parent↔child access** is via explicit `guardian_relationships`, school-controlled, never implied by surname or family.
- **Super-admin boundaries**: cross-tenant access must be explicit, logged, time-boxed, and ideally require break-glass + impersonation audit. No silent cross-school reads.

**[OPINION]** This is the second-most important design decision after tenancy. The current `is_admin = email in env` and `parent.family_id` design cannot be incrementally bent into this — design it fresh.

---

## 15. Multi-school architecture (non-negotiable)

**[FACT]** Today there is zero tenant isolation beyond application `WHERE family_id = ?`. No RLS, no tenant column convention, no cross-tenant guard tests.

**[RECOMMENDATION]** Pooled multi-tenancy (shared schema) with **defence in depth**:

1. **`school_id` on every tenant-owned row** (NOT NULL), part of composite indexes and unique constraints (e.g. `UNIQUE (school_id, external_ref)`).
2. **PostgreSQL Row-Level Security** on every tenant table. App sets `SET LOCAL app.current_school_id = :id` (and role/person context) per transaction; policies enforce `school_id = current_setting(...)`. This makes a forgotten `WHERE` clause a non-event instead of a breach.
3. **Application-layer scoping too** (belt and braces) via a tenant-aware session/dependency that injects `school_id`.
4. **Super-admin path** uses a separate role that can `SET app.bypass_rls` only on audited, explicit operations.
5. **Tenant-scoped roles/constraints/indexes** throughout; no global-unique business keys that cross tenants (emails are the one tricky exception — see §18).
6. **Cross-school access prevention tests** as a first-class test suite: every endpoint gets a "user from school A cannot touch school B" test.
7. **Lifecycle:** school **suspension** (read-only/blocked), **offboarding** (export then disable), **export** (full tenant data dump), **deletion** (hard delete + audit tombstone + backup expiry policy). Historical records and audit logs survive suspension; deletion honours legal-hold.
8. **Everything tenant-aware:** notifications, media keys (prefix by `school_id`), background jobs (carry tenant context), reporting (scoped), caching (key by tenant), backups/restore (support per-tenant restore).

**[OPINION] Risks of application-layer-only filtering:** with children's data and many schools, a single missing filter is a reportable data breach and a contract-ending event. **RLS is mandatory, not optional.** This is the single biggest architectural gap versus the brief.

---

## 16. School / class / subject model

**[RECOMMENDATION]** Model the brief's hierarchy explicitly and make **assignments and enrolments first-class, time-bounded, history-preserving** rows:

```
School ─< Campus (optional) ─< Grade/YearGroup
School ─< AcademicYear ─< Term/Semester
Grade ─< Class/Homeroom
School ─< Subject
(Class × Subject) ─> TeachingGroup        # the unit a teacher actually teaches
TeachingGroup ─< StaffAssignment           # teacher | assistant | substitute, date-bounded
TeachingGroup ─< StudentEnrolment          # student in group, date-bounded
Student ─< GuardianRelationship ─> Guardian
```

Key requirements satisfied:
- **One teacher → many subjects × many classes/grades** via many `StaffAssignment` rows (e.g. English to 3A/3B/4A/4C/5B/5D + Science to selected groups).
- **Multiple teachers per group**, **assistants**, **substitutes/cover** = assignment rows with a `role` and `is_cover` + validity window.
- **Reassignment & student movement** = closing one date-bounded assignment/enrolment and opening another; **history retained** (never hard-update the membership in place).
- **Academic-year rollover** = new `AcademicYear`/`Term` + new enrolments; prior years remain queryable (§23).

**[OPINION]** The temptation will be to put `class_id` directly on point events and messages. Resist. Point events/messages should reference the **teaching group / enrolment context at the time**, so historical reports remain correct after students move.

---

## 17. PostgreSQL model

**[RECOMMENDATION]** Production-grade entities. For each: *Purpose · Tenant ownership · Key relationships · Constraints · History · Indexing · Soft-delete · Audit.* All tenant tables carry `school_id NOT NULL` + RLS. Use `bigint`/UUID surrogate PKs; UUIDs for anything exposed in URLs/QR.

- **schools** — root tenant. Owns itself. Fields: name, slug, region/locale defaults, status (active/suspended/offboarded), data-residency tag. Soft-delete via status + `deleted_at`. Audited. Indexed by slug (global unique), status.
- **campuses** — optional sub-site. Tenant: school. FK school. History: rarely changes. Soft-delete.
- **academic_years / terms** — calendar spine. Tenant: school. Unique `(school_id, name)`, non-overlapping date checks. Immutable once closed. Indexed `(school_id, start_date)`.
- **grades (year groups)** — Tenant: school. Unique `(school_id, code)`.
- **classes (homerooms)** — Tenant: school. FK grade, academic_year. Unique `(school_id, academic_year_id, name)`.
- **subjects** — Tenant: school. Unique `(school_id, code)`.
- **teaching_groups** — the taught unit. Tenant: school. FK class, subject, academic_year. Indexed `(school_id, academic_year_id)`.
- **persons** — global identity (one row per human). **Not tenant-owned.** Holds auth identity (email unique global, optional). The bridge to tenants is `memberships`.
- **memberships** — `(person, school, role, scope)`. Tenant: school. Drives RBAC. Unique `(school_id, person_id, role, scope_ref)`. Audited (who granted/revoked). Soft-delete = `revoked_at`.
- **staff_assignments** — person↔teaching_group, role (teacher/assistant/substitute), `valid_from/valid_to`, `is_cover`. Tenant: school. **History-preserving** (never delete; close the window). Indexed `(school_id, teaching_group_id, valid_to)`.
- **students** — student profile (no login v1). Tenant: school. `external_ref` (SIS id) unique `(school_id, external_ref)`. Soft-delete. Audited.
- **enrolments** — student↔teaching_group/class, `valid_from/valid_to`, reason (promotion/transfer). Tenant: school. History-preserving. Indexed `(school_id, student_id, valid_to)`.
- **guardians** — guardian profile (person link optional until they accept invite). Tenant: school (a guardian record is per-school even if the human has children in several schools).
- **guardian_relationships** — guardian↔student, relationship type, consent flags, `is_primary`. Tenant: school. Multiple guardians/student and multiple students/guardian. Audited.
- **invitations** — staff & guardian invites. Tenant: school. `token_hash` (never store raw), `code` (typed fallback), `expires_at`, `revoked_at`, `accepted_at`, single-use. Indexed by `token_hash`. (Reuse FHH pattern.)
- **access_codes (QR)** — printable per-student guardian codes. Tenant: school. Hashed, expiring, revocable, regeneratable. Reveals no student PII pre-auth.
- **behaviour_categories** — school-managed; positive/negative; default points; subject context optional; active flag. Tenant: school. Audited.
- **point_events** — immutable behaviour event: student(s), category, points, teacher, teaching_group context, note, evidence ref, parent-visibility flag, occurred_at. Tenant: school. **Append-only**; corrections via linked reversal rows (reuse FHH ledger idempotency pattern). Indexed `(school_id, student_id, occurred_at)`.
- **point_event_corrections** — reversal/adjustment with reason + actor. Tenant: school. Unique partial index per source (reuse pattern).
- **audit_logs** — first-class immutable audit (actor, action, entity, before/after hash, ip, at). Tenant: school (+ platform-level for super-admin). Append-only; legal-hold aware. Indexed `(school_id, occurred_at)`, `(entity_type, entity_id)`.
- **conversations / conversation_participants / messages / message_attachments** — teacher↔parent & school↔parent only. Tenant: school. Participants constrained by assignment/guardianship. Messages append-only + soft-delete-for-moderation. Read receipts, retention policy, quiet-hours metadata. Indexed `(school_id, conversation_id, created_at)`.
- **posts / post_audiences / post_comments / moderation_states** — feed. Tenant: school. Audience = school/grade/class/group; scheduled/draft/pinned. Comments require approval (`pending/approved/rejected` + moderator + reason). Audited.
- **media_objects** — object-storage pointer (key, mime, size, checksum, EXIF-stripped flag, virus-scan status). Tenant: school (key prefixed by school). Soft-delete + retention. (See §42.)
- **media_consents** — per child, per type (internal/classroom/event/public-marketing), photo/video, granted/revoked/expires, evidence, annual-renewal. Tenant: school. Append-only history. Audited. **Differentiator.**
- **calendar_events / homework / projects / required_items** — audience-scoped (§33). Tenant: school. Recurrence, attachments/links, acknowledgement, completion. Indexed `(school_id, audience, start_at)`.
- **acknowledgements / completions** — guardian acknowledgement & where-appropriate completion. Tenant: school. Unique `(event_id, guardian_id)` / `(event_id, student_id)`.
- **notifications / notification_preferences / communication_hours** — see §35. Tenant: school (+ per-person prefs). Delivery status, retry, dedupe key.
- **imports / import_rows / import_errors** — CSV pipeline (§22). Tenant: school. Dry-run vs commit, idempotency key, per-row status, downloadable error report. Audited.
- **safeguarding_records** — flagged messages/incidents, restricted visibility, legal-hold. Tenant: school. Heavily audited, access-logged.
- **reports** — saved/generated report metadata. Tenant: school.

**[OPINION]** Two non-obvious calls worth making early: (1) **`persons` is global, `guardians`/`memberships` are tenant-scoped** — this is how you let one human be a parent in two schools without breaking RLS. (2) **Everything that feeds a report is append-only with corrections**, never destructive updates — safeguarding and trust depend on it.

---

## 18. Authentication

**[FACT]** Current: Google OAuth only for parents; long-lived JWT cookie; env-allowlist admin; QR sessions for children. **[RECOMMENDATION]** for schools:

- **Parents must NOT be forced into Google/Apple** (brief). Offer: **passwordless email magic link** (primary, lowest friction, no password storage), **password** (with strong hashing — argon2id), and **optional OAuth** (Google/Microsoft, useful where schools already use Workspace/365). Evaluate per §11 brief: magic link is best default for parents; password as fallback; OAuth optional.
- **Staff**: school-configurable — password + optional **SSO (Google Workspace / Microsoft Entra)**; **MFA required for admins/super-admin** (§40).
- **Tokens**: short-lived access token + **rotating refresh token** with server-side revocation (session table). Drop the 30-day bearer JWT.
- **Email uniqueness**: a person's email is globally unique (identity), but tenant access is via membership — so the same parent email can be invited by multiple schools.
- **Super-admin**: separate auth path, mandatory MFA, all actions audited, impersonation explicit & logged.

---

## 19. Parent invitation and QR onboarding

**[RECOMMENDATION]** (Directly reuse and generalise the FHH `child_auth` mechanism — it is already the right shape.)

- School issues a **per-student guardian invitation**: printed **QR code** + **typed fallback code**, **unique, expiring, revocable, regeneratable**.
- **No student details exposed before authentication** — the QR/code resolves to "you are being invited to connect to a student at School X"; the child's name appears only after the guardian authenticates and the school's policy permits.
- Flow: scan/enter code → authenticate (magic link/password/OAuth) → consent & onboarding (incl. **media-consent prompt on first login**, §32) → guardian_relationship created (school-controlled, possibly pending school approval).
- **Multiple guardians per student**, **multiple students per guardian** supported by the relationship table.
- Security: `token_hash` only (never raw), single-use where appropriate, rate-limited exchange, audit on issue/accept/revoke/regenerate. (FHH already does hashing, single-use, expiry, revoke, rate-limit in `child_auth.py` — port it.)

---

## 20. Teacher onboarding

**[RECOMMENDATION]** School admin invites staff (email invite, reuse invitation table). Teacher accepts → authenticates (password/SSO + MFA if elevated) → membership created with role(s). Admin assigns staff to teaching groups (UI or CSV, §22). Support assistants, substitutes/cover (date-bounded assignments), and reassignment without losing history. Teachers **cannot** create schools, classes outside their assignment, or other staff.

---

## 21. School admin onboarding

**[RECOMMENDATION]** Schools are **onboarded by the platform**, never self-created by teachers/parents (brief). Flow: platform super-admin (or a vetted sales/onboarding process) creates the `school` tenant + first **school owner** invite → owner accepts, configures campuses/years/terms/grades/subjects → bulk-imports staff/students/parents via CSV (§22) → configures behaviour categories, communication hours, consent policy, default language. Remove the FHH self-service "Join the Free Beta"/`registration_requests` path entirely.

---

## 22. CSV imports

**[FACT]** None exists today. **[RECOMMENDATION]** Build a robust import pipeline — this is table stakes for school onboarding and a frequent ClassDojo pain point versus SIS-synced districts.

- **Downloadable templates** per entity: teachers, assistants, students, parents/guardians, grades, classes, subjects, teaching groups, teacher assignments, student enrolments, parent-child links.
- **Two-phase**: **dry-run/preview** (validate, diff, show create/update/move counts, no writes) → **commit**.
- **Upsert by stable identifier** (`external_ref`/SIS id), not by name. Create-if-absent, update-if-present, **move** assignments/enrolments when changed (close old window, open new), **promote/transfer** students preserving history, **no duplicates**, **idempotent re-import** (import-level idempotency key + per-row hash).
- **Per-row validation** with **detailed, downloadable error reports**; **partial-failure handling** (commit valid rows, report failures — or all-or-nothing mode, configurable).
- **Audit logs** for every import (who, when, file checksum, row outcomes).
- **Academic-year-aware**: imports targeted at a specific year/term; rollover-safe (§23).
- Run as a **background job** (durable queue), not in the request thread.

---

## 23. Academic-year rollover

**[RECOMMENDATION]** Rollover is a first-class, auditable operation, not a data wipe:
- Create next `AcademicYear` + `Term`s.
- **Promote** students: new enrolments in next year's classes; previous enrolments closed (`valid_to` set), **not deleted**.
- Carry forward / re-confirm staff assignments; re-issue where structure changed.
- **Historical retention**: prior years' enrolments, point events, messages, posts, consents remain queryable and report-correct (because events reference the context-at-time, §16).
- **Consent renewal**: media consents flagged for **annual renewal** prompt guardians at year start (§32).
- Provide a **preview/dry-run** of the rollover and a reversible window before finalisation.

---

## 24. Behaviour points

**[FACT]** Current model is an economy (jars, savings, redemption, allowance, pet, streaks). **[RECOMMENDATION]** Replace with a **non-economic behaviour-recognition log**:

- **School-managed behaviour categories** (positive & negative), e.g. positives: excellent effort, reading a book, helping others, going above and beyond, strong project work, improvement, respect, teamwork, participation; negatives: missing homework, forgotten books, rudeness, disruption, poor behaviour, missing materials, repeated lateness.
- **Configurable point values** per category (school-set).
- Award to **individual / multiple students / whole class / whole group**, with **subject context**, **notes**, and **evidence** (media ref).
- **Parent-visibility rules** per category/event.
- **Undo + correction history + reason for corrections + full audit log** (reuse FHH ledger idempotency/reversal pattern — this is exactly what it's good for).
- **Reports** (per student/class/category/time), privacy-safe.
- **Safeguards against misuse**: rate/volume anomaly flags, admin oversight, no bulk-negative without reason.
- **No public humiliation / no leaderboards** that rank or shame students — points are private between school and the student's guardians.

**[OPINION]** Drop streak multipliers and any "score" that invites ranking. The brief's framing (effort/improvement/concern) is healthier and is your differentiation from ClassDojo's most-criticised behaviour mechanic. If you keep any aggregate, keep it **private and individual**, never comparative.

---

## 25. Parent dashboard

**[RECOMMENDATION]** Parents get the **main child-facing experience** (students don't log in v1). Per child: recent behaviour recognition (private), feed posts for their child's audiences, messages with teachers, calendar/homework with acknowledgement & completion, consent management, notification preferences & language. Multi-child, multi-school switching (a guardian may have children in different classes/schools). No economy, no rewards, no pet.

---

## 26. Teacher dashboard

**[RECOMMENDATION]** Scoped strictly to assigned teaching groups: roster view, award/correct behaviour points (individual/multi/group), post to class/group feed (with media + consent warnings), message parents (within communication hours; urgent override), set homework/events, moderate parent comments on own posts, see acknowledgements/completions. No access to students outside assignments (enforced by RLS + scope).

---

## 27. School-admin dashboard

**[RECOMMENDATION]** School configuration (campuses/years/terms/grades/classes/subjects/groups), staff & assignments, CSV import & rollover, behaviour categories, communication-hours & consent policy, moderation/safeguarding queue, school-wide feed & announcements, reports, audit-log access, school export. Bounded to their school only.

---

## 28. Platform-admin dashboard

**[RECOMMENDATION]** Super-admin: onboard/suspend/offboard schools, manage school owners, platform health, cross-tenant **only via audited, explicit, time-boxed** actions (break-glass), impersonation with full audit, billing/plan management. **Hard boundary:** no casual cross-school browsing; every cross-tenant read/write logged to platform audit. Replaces the FHH env-allowlist admin entirely.

---

## 29. Messaging

**[RECOMMENDATION]** Build per brief, governance-first:
- **Allowed**: teacher↔parent, school→parent, class/grade/subject-group announcements; **parents may initiate**.
- **Forbidden**: parent↔parent, family↔family, student private messaging, uncontrolled group chat. Enforce structurally (participants derived from assignment/guardianship; no parent-to-parent conversation type can exist).
- **Communication hours / quiet hours**: teachers receive parent messages only during configured windows, **except defined urgent/safeguarding cases** (override path with logging). Server-side enforced, per-school configurable. Protects **staff wellbeing**.
- Features: direct conversations, multiple guardians, attachments (photos/documents via object storage + scan + EXIF strip), read receipts, search, retention policy, **moderation/reporting/safeguarding review**, escalation, notifications, **audit access**, **tenant isolation**, **assignment-based access** (a teacher can only message parents of their students).

---

## 30. Class and school feed

**[RECOMMENDATION]** Audience-scoped story: **school / grade / class / subject-group** feeds. Content: photos, documents, announcements, celebrations, projects, homework reminders. Support **scheduled** + **draft** posts, **pinning**, **audience controls**, **moderation/reporting**, notifications, search, **archiving**, **translation-ready content**. Media must respect consent (§32) with **teacher warnings before posting** photos of children lacking consent.

---

## 31. Comment moderation

**[RECOMMENDATION]** Comments **optional per post**. Parent comments **require teacher/staff approval before publication** (`pending → approved/rejected` with moderator + reason + timestamp). Comments must **not** become parent-to-parent communication (replies are to staff/post, not visible as a parent-to-parent thread until approved, and never enable private parent contact). Full **moderation state + audit history**. **[OPINION]** This is a genuine differentiator — make approval-before-publish the default and unskippable.

---

## 32. Media consent

**[RECOMMENDATION]** **Differentiator — build it properly.** Prompt guardians on **first login**. Support: consent **per child**; **types** (internal school use / classroom use / school-event use / public marketing use); **photo** and **video** separately; **revocation**, **expiry**, **annual renewal**; **audit history** + **evidence**; **teacher warnings before posting** media of a child lacking consent; **group-photo handling** (block/blur/flag when any child in frame lacks consent); **country/region policy differences** (configurable per school/region, no hard-coding). This directly answers ClassDojo's consent criticism ([LSE](https://blogs.lse.ac.uk/parenting4digitalfuture/2017/01/04/classdojo-poses-data-protection-concerns-for-parents/)).

---

## 33. Calendar and assignments

**[RECOMMENDATION]** (Redesign FHH calendar engine; keep recurrence/occurrence logic.) Audience-scoped: **school/grade/class/subject-group/selected-student/individual-student** events; **homework, tests, projects, trips, deadlines**; **required items/books/equipment**; **attachments/links**; **recurring events**; **parent acknowledgement**; **completion tracking where appropriate**; **reminders**; **update/cancellation notices**; **calendar export later**. Maintain a **clear distinction between posts, announcements, homework, and events** (separate entity types, not one overloaded row).

---

## 34. Reporting

**[RECOMMENDATION]** Behaviour & engagement reports per student/class/category/time; participation in feed/messages; consent status; import outcomes; safeguarding/audit reports. **Privacy-safe** (no cross-student ranking exposed to parents), tenant-scoped, exportable. Defer heavy analytics/dashboards beyond basics to v2.

---

## 35. Notifications

**[FACT]** None today (no email-on-event, no push). **[RECOMMENDATION]** Channels: **in-app**, **email**, **web push / PWA** (native push later). Respect **quiet hours**, **parent preferences**, **teacher working hours**; **emergency announcements** bypass quiet hours (logged). Require **delivery status**, **retry**, **deduplication** (dedupe key per event×recipient×channel), **background queues** (durable, not the current asyncio loop), **per-language delivery** (render in recipient's language), **audit history**. **[OPINION]** Introduce a real job queue (e.g. Redis/RQ, Celery, or `pg`-backed) here — it's also what imports, media processing, and rollover need.

---

## 36. Internationalisation

**[FACT]** Current i18n: `svelte-i18n`, EN + AR catalogues (`messages.ts`, 2,477 lines), parity checker, RTL via `dir`. **Strengths**: real catalogue, AR present day one, RTL mechanism, parity tooling, deliberate "parent-entered content not translated" policy (`docs/LOCALISATION_NOTES.md`).

**Gaps to fix for schools:**
- **Hard-coded household wording** throughout AR/EN catalogues ("Family Hero Hub", family/child/reward/allowance/savings/school-bag terms) — must be rewritten for school domain (`messages.ts` `app.name`, `footer.description`, `language.help`, etc.).
- **No backend/email/notification localisation** — emails are English-only (`mailer.py`). School notifications must render per-recipient-language.
- **No CSV localisation** (templates/errors English-only).
- **No locale-aware academic calendars / number / date-time / pluralisation handling on the backend.** Frontend relies on catalogue strings; ensure ICU plural rules for AR (more than en's 2 forms).
- **Language resolution**: need **language per user**, **school default language**, **parent-selected language** with sensible fallback chain (user → school → platform default). Currently only a browser/localStorage toggle (`i18n/index.ts`).
- **Mixed-language content** (AR post in an EN UI) must render correctly with per-element `dir="auto"`.
- **No country-specific hard-coding** — today `Family.timezone` defaults to `Asia/Muscat` and allowance currency to `OMR` (`models.py`). For a multi-school platform, timezone/locale/region must be **per school**, not a global default.

---

## 37. Arabic and RTL

**[FACT]** RTL is implemented at the document level (`dir` on `<html>`, `localeDirection`). **[OPINION]** Document-level `dir` is necessary but not sufficient. **[RECOMMENDATION]**:
- Audit every component for **logical CSS properties** (`margin-inline-start` not `margin-left`), icon mirroring, and bidi-correct number/date rendering.
- **Mixed-direction content** (EN names in AR UI and vice versa) needs `dir="auto"` on user-content elements.
- **Accessibility under RTL** (§38): focus order, screen-reader language tagging (`lang` attr per content block).
- AR pluralisation/number formatting via Intl APIs, not string concatenation.
- Native Arabic review of all school-domain terms (the localisation notes already flag many AR terms "Needs native review").

---

## 38. Accessibility

**[RECOMMENDATION]** Target **WCAG 2.2 AA**. Keyboard navigation, focus management in modals (current app is modal-heavy per `PLAN.md`), ARIA labelling, colour-contrast, screen-reader support in **both** LTR and RTL, language tagging of content blocks, accessible forms/error reporting, reduced-motion. Schools (especially public/ministry buyers) increasingly require accessibility compliance — treat it as a sales requirement, not a nicety.

---

## 39. Safeguarding

**[RECOMMENDATION]** This is a child-data platform; safeguarding is core, not an add-on:
- **Safeguarding review queue** for flagged messages/comments/incidents; restricted-visibility `safeguarding_records`.
- **Moderation + reporting** on messages, comments, feed.
- **Legal hold** (suspend deletion/retention for records under investigation).
- **Immutable audit trails** with access logging (who viewed safeguarding data).
- **Escalation** paths and designated-safeguarding-lead roles.
- **Disclosure-ready export** of a child's full record.
- **No-shaming / no-public-points** design choices (also safeguarding-relevant).

---

## 40. Privacy and legal risks

**[FACT/RECOMMENDATION]** Children's data across jurisdictions → high regulatory load. Design for: **COPPA** (US under-13), **FERPA** (US student records), **GDPR / UK GDPR** (EU/UK), **Oman/GCC privacy regimes**, and **regional data residency**. Requirements: lawful basis & consent records, data-minimisation, retention schedules, right-to-export/erasure (school-mediated, since the school is typically controller), DPA/sub-processor management, breach-notification readiness, and **per-school/region data-residency options**.

**[OPINION] You need professional legal review before pilot, and certainly before a second country.** I can build the technical controls (consent, audit, residency tagging, export/delete), but the data-controller/processor split, lawful basis, and per-jurisdiction consent wording are legal decisions, not engineering ones. Do not skip this. Also: the current single-VPS, single-DB, EU/US topology already mixes regions — multi-school will force a residency decision early.

---

## 41. Security architecture

**[FACT]** Current strengths: CSRF double-submit (`auth.validate_csrf_request`), fail-closed config validation, trusted-proxy middleware, token hashing for child links, rate-limited exchange, secure cookies in production, no public DB port. Current weaknesses: env-allowlist admin, 30-day non-revocable JWT, **in-process rate limiter** (`security.py` — not multi-replica safe), no RLS, no MFA, no audit-log table, no file-upload security (because no uploads yet).

**[RECOMMENDATION]** For the school build:
- **RBAC + scope-based permissions + RLS** (§14, §15) — the spine.
- Teacher-assignment checks and parent-child relationship checks on **every** access.
- **MFA** for admins/super-admin; **passwordless/magic-link** + password + optional OAuth for parents (§18).
- **Invitation/QR security**: hashed, single-use, expiring, revocable, rate-limited (reuse FHH).
- CSRF on all session types; **secure, httpOnly, SameSite** cookies; short-lived access + rotating refresh tokens.
- **Distributed rate limiting & brute-force protection** (Redis/DB), not in-memory.
- **File-upload security** (§42): MIME validation, AV scan, EXIF strip, size/type quotas, signed URLs.
- **Message moderation + safeguarding access controls + legal holds + immutable audit**.
- Child-data privacy, consent enforcement, retention, export, deletion.
- A standing **cross-tenant access test suite**.

---

## 42. Media and file storage

**[FACT]** No media/upload capability exists; no object storage; Docker mounts a local `./data` volume only. **[RECOMMENDATION]** Use **S3-compatible object storage** (not local disk):
- **Tenant separation** via key prefix (`school_id/...`) + bucket policy.
- **Signed URLs** for upload/download (no public buckets).
- **Virus scanning** on upload (quarantine until clean).
- **MIME validation** (allowlist), reject mismatched content.
- **EXIF stripping + geolocation removal** (child-safety critical) before storage/serving.
- **Image resizing + thumbnails** (background job).
- **Quotas** per school; **retention** & **deletion** policies; **backups**; **CDN later**; **cost controls** (lifecycle rules, size caps).
- `media_objects` table tracks key, checksum, scan status, EXIF-stripped flag, consent linkage.

---

## 43. Performance and scaling

**[FACT]** Current: single Docker Compose, single Postgres, in-process background loop, in-memory rate limiter, client-only fetch. **[RECOMMENDATION]** for multi-school:
- **Stateless app replicas** behind a load balancer (move all in-process state — rate limits, background jobs — out).
- **Managed/HA PostgreSQL** + **read replica** for reporting; connection pooling (PgBouncer).
- **Durable job queue + workers** (imports, notifications, media, rollover, maturity-style sweeps).
- **Redis** for cache, rate limiting, sessions.
- **Object storage + CDN** for media.
- **Per-tenant indexing** (composite `(school_id, …)`) and partitioning candidates for high-volume tables (`point_events`, `messages`, `audit_logs`) as data grows.
- Caching keyed by tenant; careful cache-isolation to avoid cross-tenant bleed.

---

## 44. Testing strategy

**[FACT]** Strong existing culture: 207 tests, PG concurrency/FK tests, Playwright E2E, i18n parity, daily QA harness. **[RECOMMENDATION]** Carry the culture, expand coverage:
- **Tenant isolation tests** (first-class): every endpoint, "school A cannot touch school B", including RLS-enforced negatives.
- **RBAC/scope tests** per role × resource.
- **Permission boundary tests** (teacher outside assignment, parent without guardianship).
- **Import pipeline tests** (dry-run/commit/idempotency/partial-failure/error-report).
- **Concurrency tests** for point events & corrections (reuse the existing PG concurrency approach).
- **i18n/RTL tests** (parity + render-direction).
- **Consent enforcement tests** (media blocked without consent).
- **Messaging governance tests** (no parent-to-parent path exists).
- E2E across roles (admin/teacher/parent), EN + AR.
- **Drop SQLite from the test matrix** — test on PostgreSQL only to avoid partial-index/`func` divergence.

---

## 45. Migration from the current schema

**[OPINION] There is no meaningful data to migrate** — the only live data is household families/children/points/rewards, which have no school equivalent and are out of scope. **[RECOMMENDATION]**: **Do not migrate; start a fresh schema.** Reuse the FHH schema only as a *reference* for the patterns worth copying (ledger idempotency, invitation/token, soft-delete/audit columns). The PoC instance's data should be discarded for the school product. New Alembic history begins at the new `schools`-rooted baseline. Keep the old repo/branch archived for reference; do not try to evolve `families` into `schools` via migrations — the conceptual mismatch (one tenant vs many, parent-owned vs school-owned points, economy vs recognition) makes incremental migration more expensive and riskier than a clean baseline.

---

## 46. API redesign

**[RECOMMENDATION]**:
- Re-root all resources under **tenant context** (school resolved from membership/subdomain/header), with RLS-backed enforcement.
- Versioned API (`/api/v1`), consistent resource naming (schools, grades, classes, subjects, groups, students, guardians, staff, point-events, conversations, posts, events, homework, consents, imports, notifications, audit).
- Replace `parent.family_id` coupling with `(person, membership)` resolution.
- Server-side **scope guards** as reusable dependencies (assignment check, guardianship check, role check) — not ad-hoc per route.
- Consider **server-side data loading** (SvelteKit `load`) for authenticated pages to reduce token exposure and improve UX.
- Idempotency keys on write endpoints (point events, imports) — reuse FHH's idempotency discipline.

---

## 47. Frontend redesign

**[FACT]** Current UI is household-themed (parent launcher with children-first, child dragon dashboard, rewards/allowance/savings/school-bag modals — `PLAN.md`, `routes/`). **[RECOMMENDATION]**:
- New role-based shells: **platform-admin, school-admin, teacher, parent** (no student app in v1).
- Remove child dashboard, rewards, allowance, savings, redemptions, pet, school-bag routes/components.
- New surfaces: school config, roster/import, behaviour points, feed, messaging, calendar/homework, consent, moderation/safeguarding, reports, notifications.
- Keep: i18n/RTL architecture, Tailwind system, component discipline, API client pattern (`lib/api.ts`).
- Build **RTL-correct, accessible** components from the start (§37–§38).

---

## 48. Exact wording / routes / features to remove

**[FACT]** Concrete removal list (household-only):

*Backend models/tables:* `Reward`, `RedemptionRequest`, `RedemptionStatus`, `ChildAllowanceSetting`, `PetProgress`, `PetStage`, `WeeklyStreak`, `SchoolItem`, `SchoolItemCheck`, `JarType`, economy `TransactionType` members (`savings_*`, `redemption_*`), `RegistrationRequest`, `ApprovedParentEmail`, and the `Family`/`ParentUser.family_id`/`Child`-as-tenant shape.

*Backend routes/services:* `routes/rewards.py`, `routes/redemptions.py`, `routes/allowance.py`, `routes/school_items.py`, `routes/presets.py` (replace with behaviour-categories), `routes/registration.py`, `services/allowance_service.py`, `services/rewards_service.py`, `services/school_items_service.py`, `currencies.py`, the savings-maturity loop in `main.py`, child device/session login (`child_auth.py`, `routes/child_*`) as a *student* login.

*Frontend routes:* `/child/[id]`, `/allowance`, `/redemptions`, `/request-access`, `child-link/[token]`, `child-guide`, and reward/allowance/savings/pet/school-bag UI in `/parent`.

*Wording (i18n + marketing):* "Family Hero Hub", "family", "child"-as-account, "rewards", "redeem", "allowance", "savings/jars", "pet/dragon", "school bag/pack for tomorrow", "grownup/caregiver" as family roles, "Join the Free Beta". Replace with school-domain vocabulary (school, class, teacher, guardian, behaviour, recognition, announcement, homework). Update `docs/LOCALISATION_NOTES.md` term table wholesale.

*Concepts to eliminate:* parent-awards-points-to-own-child, family-as-tenant, sibling/household routines, home behaviours, family-only tenancy, env-allowlist admin, self-service tenant creation.

---

## 49. MVP

**[RECOMMENDATION]** MVP = enough to run **one pilot school well**: school onboarding + structure; staff/roles + assignments; CSV import (dry-run + commit); parent QR invitation + guardianship; behaviour points (private, categories, corrections, audit); teacher↔parent messaging with quiet hours; class/school feed with moderated parent comments; media + consent; calendar + homework with acknowledgement; in-app + email notifications; EN/AR + RTL; **RLS tenant isolation**; audit log. Explicitly **not** in MVP: portfolios, attendance, native push, AI, advanced analytics, SIS integration, multi-campus reporting.

---

## 50. Pilot

**[RECOMMENDATION]** One school, real staff/students/parents, with: full data export/delete tested; backup/restore rehearsed for the tenant; safeguarding/moderation workflows exercised; consent flow validated with real guardians; AR + RTL validated by native users; communication-hours and notification delivery validated; load tested at the school's real size. Define exit criteria (no cross-tenant leaks, no consent bypass, acceptable performance, positive teacher/parent feedback) before opening to a second school.

---

## 51. Production launch

**[RECOMMENDATION]** Gate multi-school GA on: RLS verified by isolation test suite + external pen test; legal review complete (§40); MFA for admins; distributed rate limiting; durable job queue; object storage with AV/EXIF; HA Postgres + backups + per-tenant restore proven; monitoring/alerting/audit dashboards; documented incident & breach-notification process; data-residency story for target regions.

---

## 52. Later roadmap

**[RECOMMENDATION]** Post-GA: portfolios (Seesaw-style, the obvious adjacency); attendance; native push; SIS/ClassLink/SFTP rostering integrations; calendar export (ICS); AI assist (translation, draft messages, post drafting — carefully, with human approval); analytics dashboards; multi-campus/district federation & reporting; Google Workspace / Microsoft 365 SSO integrations; offline/PWA enhancements.

---

## 53. Phase-by-phase implementation plan

Each phase: **Objective · Scope · Backend · Frontend · Database · Security · Tests · Dependencies · Risks · Acceptance · Complexity.** Phases 0–2 are the "design correctly before building" foundation and must not be rushed.

### Phase 0 — Foundations & design lock-in
- **Objective:** Lock the five must-get-right designs (tenancy, school graph, identity/roles, invitation/guardianship, behaviour model) before code.
- **Scope:** Architecture decision records; schema diagrams; RLS strategy; auth strategy; threat model; legal-requirements brief.
- **Backend:** New repo skeleton/branch; reuse config-validation, CSRF, proxy middleware as libraries.
- **Frontend:** New SvelteKit shell, i18n/RTL scaffolding retained.
- **Database:** New Alembic baseline plan (no migration from FHH); RLS conventions defined.
- **Security:** Threat model, data-classification, RLS policy templates, MFA/auth decisions.
- **Tests:** Test strategy incl. tenant-isolation harness design.
- **Dependencies:** None (start here).
- **Risks:** Under-designing tenancy/roles forces costly rework later.
- **Acceptance:** Signed-off ADRs for §14–§17; legal brief commissioned.
- **Complexity:** Medium (mostly design effort, high leverage).

### Phase 1 — Tenancy, identity, RBAC, RLS
- **Objective:** Multi-school skeleton with enforced isolation and roles.
- **Scope:** schools/campuses/persons/memberships; auth (magic link + password + optional OAuth); MFA for admins; RLS on all tenant tables.
- **Backend:** Tenant-aware DB session (`SET LOCAL app.current_school_id`); auth service; membership/role resolution; scope-guard dependencies; super-admin path.
- **Frontend:** Auth flows; school switcher; platform-admin + school-admin shells.
- **Database:** Baseline schema + RLS policies; session-context plumbing.
- **Security:** RLS, MFA, rotating refresh tokens, distributed rate limiting (Redis), audit-log table.
- **Tests:** Cross-tenant isolation suite (must pass), RBAC/scope tests, auth tests.
- **Dependencies:** Phase 0.
- **Risks:** RLS performance tuning; auth edge cases (multi-school person).
- **Acceptance:** A user in school A provably cannot read/write school B (incl. raw SQL via app role); admin MFA enforced.
- **Complexity:** High (foundational).

### Phase 2 — School structure & rollover
- **Objective:** Full school graph with history.
- **Scope:** academic years/terms/grades/classes/subjects/teaching groups; staff assignments; students; enrolments; guardians/relationships.
- **Backend:** CRUD + date-bounded assignment/enrolment logic; rollover engine.
- **Frontend:** School-admin config UIs; roster views.
- **Database:** Structure tables + history constraints + indexes.
- **Security:** Scope checks (teacher↔group, coordinator↔grade).
- **Tests:** Structure integrity; history retention across reassignment/move; rollover dry-run.
- **Dependencies:** Phase 1.
- **Risks:** Getting history/temporal model wrong → broken historical reports.
- **Acceptance:** Modelled examples from brief (one teacher across 3A/3B/4A/4C/5B/5D + Science) work; rollover preserves prior year.
- **Complexity:** High.

### Phase 3 — CSV import
- **Objective:** Onboard a school from spreadsheets safely.
- **Scope:** Templates + dry-run/commit + upsert/move + error reports + audit, for all brief entities.
- **Backend:** Import pipeline on durable job queue; idempotency; validation; error-report generation.
- **Frontend:** Upload, preview/diff, error download UIs.
- **Database:** imports/import_rows/import_errors.
- **Security:** Tenant-scoped imports; audit.
- **Tests:** Dry-run vs commit, idempotent re-import, partial-failure, move/promote, error reports.
- **Dependencies:** Phase 2; job queue (Phase 1/Phase 5 infra).
- **Risks:** Idempotency & "move vs duplicate" correctness.
- **Acceptance:** Re-importing the same file is a no-op; changed assignments move with history preserved; errors downloadable.
- **Complexity:** High.

### Phase 4 — Parent invitation & QR onboarding
- **Objective:** Secure guardian connection with no pre-auth PII.
- **Scope:** QR + typed code invites; guardianship; first-login consent prompt.
- **Backend:** Reuse/port FHH token mechanism; guardian onboarding; consent capture.
- **Frontend:** Invite-accept flow, consent prompt.
- **Database:** invitations/access_codes/guardian_relationships/media_consents.
- **Security:** Hashing, single-use, expiry, revoke, regenerate, rate-limit; no PII pre-auth.
- **Tests:** Invite lifecycle; PII-not-leaked-before-auth; multi-guardian/multi-child.
- **Dependencies:** Phase 1–2.
- **Risks:** Consent UX correctness; code distribution logistics.
- **Acceptance:** Guardian connects via QR/code; no student detail shown pre-auth; consent recorded.
- **Complexity:** Medium (mechanism largely reusable).

### Phase 5 — Behaviour points
- **Objective:** Private behaviour recognition with corrections & audit.
- **Scope:** Categories; individual/multi/class/group awards; subject context, notes, evidence; corrections; reports.
- **Backend:** Append-only point-event log + reversal/correction (reuse idempotency pattern); reporting queries.
- **Frontend:** Teacher award UI; parent/child view; school category config.
- **Database:** behaviour_categories/point_events/corrections.
- **Security:** Assignment-scoped; misuse safeguards; visibility rules; audit.
- **Tests:** Concurrency, correction integrity, scope, no-leaderboard, parent-visibility.
- **Dependencies:** Phase 2.
- **Risks:** Re-introducing economy/leaderboard semantics by habit.
- **Acceptance:** Awards/corrections audited; no public ranking; reports correct after student moves.
- **Complexity:** Medium.

### Phase 6 — Media, consent & object storage
- **Objective:** Safe media with explicit consent.
- **Scope:** Object storage; signed URLs; AV scan; EXIF strip; thumbnails; consent enforcement; teacher warnings.
- **Backend:** Upload service + scan/strip/resize jobs; consent checks.
- **Frontend:** Upload UI with consent warnings; consent management.
- **Database:** media_objects (extend media_consents from Phase 4).
- **Security:** MIME validation, AV, EXIF/geo strip, quotas, tenant key prefixing.
- **Tests:** Consent-blocked posting, EXIF stripped, scan quarantine, group-photo handling.
- **Dependencies:** Phase 4 (consent), job queue.
- **Risks:** EXIF/geo leakage if any path bypasses processing.
- **Acceptance:** No child media posted without consent; all media EXIF-stripped & scanned.
- **Complexity:** High.

### Phase 7 — Messaging
- **Objective:** Governed teacher↔parent + school→parent comms.
- **Scope:** Conversations, attachments, read receipts, search, quiet hours, urgent override, moderation/safeguarding, retention.
- **Backend:** Messaging service; communication-hours enforcement; safeguarding flags.
- **Frontend:** Inbox/threads; quiet-hours indicators; report/escalate.
- **Database:** conversations/participants/messages/attachments.
- **Security:** Assignment/guardianship-scoped; no parent-to-parent path; audit.
- **Tests:** Governance (no P2P), quiet hours + override, safeguarding, isolation.
- **Dependencies:** Phase 2, 6.
- **Risks:** Quiet-hours/urgent edge cases; moderation gaps.
- **Acceptance:** Parent↔parent impossible; quiet hours enforced server-side; urgent override logged.
- **Complexity:** High.

### Phase 8 — Feed & comment moderation
- **Objective:** Moderated, audience-scoped feeds.
- **Scope:** School/grade/class/group posts; scheduled/draft/pinned; parent comments approval-before-publish.
- **Backend:** Feed + moderation state machine; scheduling job.
- **Frontend:** Feed composer (with media/consent warnings), moderation queue.
- **Database:** posts/audiences/comments/moderation_states.
- **Security:** Audience scoping; moderation audit.
- **Tests:** Audience correctness, comment approval flow, no P2P drift.
- **Dependencies:** Phase 6, 7.
- **Risks:** Comment threads becoming parent-to-parent.
- **Acceptance:** Parent comments require approval; audience controls enforced.
- **Complexity:** Medium–High.

### Phase 9 — Calendar, homework & notifications
- **Objective:** Events/assignments with acknowledgement + delivery.
- **Scope:** Audience-scoped events/homework/projects/required-items; acknowledgement/completion; notifications (in-app/email/web push) with quiet hours, retry, dedupe, per-language.
- **Backend:** Calendar engine (redesigned); notification service on queue.
- **Frontend:** Calendar/homework UIs; notification prefs.
- **Database:** events/homework/required_items/acknowledgements; notifications/preferences/communication_hours.
- **Security:** Audience scoping; per-language delivery; audit.
- **Tests:** Recurrence, acknowledgement, notification dedupe/retry/quiet-hours, per-language render.
- **Dependencies:** Phase 2, 7.
- **Risks:** Notification storm / dedupe correctness.
- **Acceptance:** Reminders deliver in recipient language, respect quiet hours, dedupe.
- **Complexity:** High.

### Phase 10 — Reporting, safeguarding, hardening, pilot readiness
- **Objective:** Production-ready single-school pilot.
- **Scope:** Reports; safeguarding queue + legal hold; export/delete; pen test; accessibility; AR/RTL polish; HA/scale infra.
- **Backend:** Reporting; safeguarding; tenant export/delete.
- **Frontend:** Reports, safeguarding, accessibility/RTL pass.
- **Database:** reports/safeguarding_records; partitioning candidates.
- **Security:** External pen test, legal review sign-off, MFA, residency tagging.
- **Tests:** Full isolation/RBAC/consent/governance regression; a11y; AR E2E.
- **Dependencies:** All prior.
- **Risks:** Legal/compliance gaps surfacing late.
- **Acceptance:** Pilot exit criteria (§50) met.
- **Complexity:** High.

---

## 54. Risks

1. **[OPINION] Treating this as "rename + extend" instead of a domain rebuild** — the single biggest risk. The family tenant and economy will leak into the school product and create permanent confusion.
2. **Tenant-isolation failure** → child-data breach, contract loss, regulatory action. Mitigate with RLS + isolation test suite + pen test.
3. **Legal/compliance under-investment** (COPPA/FERPA/GDPR/UK GDPR/GCC + residency). Mitigate: legal review before pilot.
4. **Consent/media mishandling** (EXIF/geo leakage, posting without consent) — child-safety incident. Mitigate: Phase 6 controls, no bypass paths.
5. **Safeguarding/moderation gaps** — harm + liability. Mitigate: Phase 7–8 + audit.
6. **Scaling debt** (in-process limiter/queue, single DB) bites at second/third school. Mitigate: Phase 1/5 infra.
7. **Scope creep into portfolios/attendance/AI** before the governance core is solid. Mitigate: hold the §13 line.
8. **AR/RTL treated as translation, not native experience** — loses the differentiator. Mitigate: native review + RTL component discipline.
9. **Re-introducing gamification/leaderboards** out of habit → inherits ClassDojo's criticisms.

---

## 55. Open questions

1. **Target launch geographies** for pilot and first 12 months? (Drives residency, legal, locale priorities.)
2. **Data-controller model**: is the school always the controller and CHH the processor? (Drives export/delete/consent UX.)
3. **Identity preference**: how many schools already use Google Workspace / Microsoft 365 (affects SSO priority)?
4. **Pilot school size & structure** (campuses? bilingual? year structure?) — to validate the school graph against reality.
5. **Pricing model** (per-student? per-school? free tier?) — affects tenant lifecycle/billing design.
6. **SIS landscape** of target schools — do we need integration sooner than v2?
7. **Hosting/residency constraints** from the pilot school/ministry?
8. **Is "selected student / individual student" feed/event audience** a hard MVP requirement or deferrable?
9. **Retention periods** required by target jurisdictions (drives schema retention fields).
10. **Brand**: keep "Class Hero Hub" or is naming still open? (Affects i18n term lock.)

---

## 56. Recommended next action

**[RECOMMENDATION]** Do **Phase 0** now, and nothing downstream until it's signed off:

1. **Stop extending the family app.** Freeze the PoC; do not bend `Family` into `School`.
2. **Commission the legal/compliance brief** (§40) in parallel — it constrains the schema.
3. **Produce and sign off the five foundational designs** (§14 roles, §15 tenancy/RLS, §16 school graph, §17 schema, §19 invitation/guardianship), with the cross-tenant test strategy.
4. **Start a clean repository/branch** with a new Alembic baseline, reusing FHH's config-validation, CSRF, proxy-trust, invitation-token, and ledger-idempotency *patterns* as libraries — not its domain model.
5. **Validate the school graph against the real pilot school's structure** before writing CRUD.

**[OPINION]** The fastest path to a credible ClassDojo competitor is not to nurse this codebase forward — it is to **reuse its engineering discipline to build the right schema once.** The team clearly can build carefully (the ledger and config-validation prove it). Point that same care at the correct domain.

---

## Sources (external research)

- ClassDojo features/pricing — SoftwareAdvice: https://www.softwareadvice.com/classroom-management/classdojo-profile/
- ClassDojo features/reviews — GetApp: https://www.getapp.com/education-childcare-software/a/classdojo/
- ClassDojo teacher guide (Class Story, messaging) — KiwiBee/Lemobee: https://lemobee.com/en/blog/classdojo-for-teachers-guide
- ClassDojo students/portfolios (QR login) — KiwiBee/Lemobee: https://lemobee.com/en/blog/classdojo-for-students-guide
- ClassDojo pricing/alternatives — Capterra: https://capterra.com/p/124446/ClassDojo/
- ClassDojo for Districts 2025–26 (rostering, Sidekick AI, 2026 roadmap) — eLearning Industry: https://elearningindustry.com/press-releases/classdojo-for-districts-unveils-new-features-for-2025-26-school-year
- ClassDojo for Districts press release — PRNewswire: https://www.prnewswire.com/news-releases/classdojo-for-districts-unveils-new-features-for-202526-school-year-302510766.html
- Children's-rights / public-points shaming concerns — The Conversation: https://theconversation.com/classdojo-raises-concerns-about-childrens-rights-111033
- Surveillance / compliance-over-learning — The Conversation: https://theconversation.com/digitally-tracking-student-behaviour-in-the-classroom-encourages-compliance-not-learning-110181
- Behaviour-management critique (Manolev) — EducationHQ: https://educationhq.com/news/classdojo-harms-teachers-behaviour-management-approach-researcher-188825/
- Surveillance in schools — EurekAlert: https://www.eurekalert.org/news-releases/732702
- Data-protection concerns — LSE Parenting4DigitalFuture: https://blogs.lse.ac.uk/parenting4digitalfuture/2017/01/04/classdojo-poses-data-protection-concerns-for-parents/
- Peer-reviewed analysis (2025) — Taylor & Francis: https://www.tandfonline.com/doi/full/10.1080/17439884.2025.2553184
- ClassDojo vs Seesaw comparison — Slashdot: https://slashdot.org/software/comparison/ClassDojo-vs-Seesaw/
- ClassDojo vs Seesaw — AI in Education: https://aiineducation.io/compare/classdojo-vs-seesaw
- ClassDojo alternatives (Bloomz/Remind/Seesaw) — ClassPoint: https://www.classpoint.io/blog/classdojo-alternatives
- ClassDojo alternatives — G2: https://www.g2.com/products/classdojo/competitors/alternatives

*External market facts are current public sources as of June 2026; vendor-stated scale figures (e.g. ClassDojo's user counts) are claims by the vendor, not independently verified. Codebase facts are from direct inspection of `/opt/apps/class_hero_hub` on 2026-06-16.*

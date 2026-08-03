# CHH current pilot deployment

## 2026-08-03 direct CHH family-access removal

Class Hero Hub is now exclusively a staff workspace. The authenticated navigation
contains no Family destination for guardian-only or dual-role accounts, including
staff members who are also parents. Staff continue to see pupils only through the
teaching and school-administration workflows authorised for their staff role; their
own child's school information is available only through Family Hero Hub.

The obsolete CHH parent dashboard and guardian-code page no longer load child data.
Requests to `/parent` and `/join` are redirected to the bilingual public Family Hero
Hub explanation. The backend no longer mounts any direct `/api/guardian/*` or
`/api/join/guardian*` route, so a saved URL or custom client cannot bypass the
navigation change. The separate authenticated `/api/integrations/fhh/*` service
surface used by Family Hero Hub remains mounted and unchanged.

Validation passed 24 focused backend tests covering the removed public surface and
the retained FHH dashboard, messaging and survey integrations; 37 focused frontend
contract and presentation tests; 2,217-key English/Arabic parity; Svelte diagnostics
with zero errors and zero warnings; and the production frontend build. A focused
Playwright test confirmed that a mixed staff/guardian account has no Family link and
that `/parent` redirects to `/family-connection`. Live HTTPS checks returned 404 for
the removed guardian dashboard and join routes, 401 rather than 404 for the retained
protected FHH dashboard route, and `database=ok`, `migration=current`. The existing
signed-in Chrome workspace was reloaded and contained zero `/parent` navigation
links; its legacy parent URL redirected to “School updates for families.”

Only the backend and frontend were rebuilt and recreated. The backend changed from
container `f23aa4b53963` to `db11ff99aa23`; the frontend changed from
`046fa48792c1` to `6e2abf1e5921`. PostgreSQL `9653df2c5588`, messaging worker
`8919cebb3330`, and notification scheduler `2909345e8a68` retained their identities.
There is no schema migration, existing-data mutation, FHH deployment, worker,
scheduler, Capacitor, Android or APK change. A database backup was not required for
this route and presentation change. Source implementation commit: `1a864ae`.

## 2026-08-03 student-import avatar assignment release

Committing a staged student CSV import now assigns avatars for every successful,
active row whose recorded gender is `male` or `female`. Assignment runs once after
the complete student and enrolment batch is prepared, allowing the existing
class-aware service to use the correct gender pool, exclude retired artwork, and
avoid current-class collisions. Preview remains read-only. Blank, `other`, and
`unspecified` values remain unassigned, inactive/leaver rows are skipped, and a
later CSV gender correction replaces a wrong-pool avatar.

Avatar assignment uses `commit=False` inside the import transaction. Any assignment
failure therefore rolls back the students, enrolments, avatar writes, and import
status together; the import remains staged for correction or retry. No API response
shape or CSV template changed.

The combined student-import and avatar selection passed 61/61 tests both locally
and inside the deployed image, including immediate male/female assignment,
same-class uniqueness, retired-artwork exclusion, unknown-gender withholding,
gender correction, and deliberate assignment-failure rollback. The live
aggregate-only avatar audit remains a no-op across all 504 active demo students,
readiness reports `database=ok` and `migration=current`, and recent backend logs
contain no relevant error entry.

Only the backend was rebuilt and recreated, changing from container `d60b88ec573f`
to `f23aa4b53963`. The frontend `046fa48792c1`, PostgreSQL `9653df2c5588`,
messaging worker `8919cebb3330`, and notification scheduler `2909345e8a68`
retained their identities. There is no schema migration, existing-data mutation,
frontend, worker, scheduler, native, or APK change. A new database backup was not
required for this backend-only transactional change. Source implementation commit:
`fe52ba0`.

## 2026-08-03 complete demo avatar coverage follow-up

A full live audit found that the only two active students still missing avatars were
the remaining synthetic Nour records. The three other active students generated
with the same demo first name are all recorded female, which established the seed's
intended demo value without adding name-inference behaviour to the product. The two
remaining demo records were corrected from `unspecified` to `female` and received
girl-pool avatars 65 and 68 through the existing class-aware assignment service.

All 504 active demo students now have avatars. The final aggregate audit reports
zero missing avatars, retired assignments, wrong-gender-pool assignments,
assignments without a valid recorded gender, and duplicate avatar groups in current
active classes. A repeat dry run targeted and changed zero students. Both assigned
artworks were visually inspected.

Fresh pre-change encrypted incremental backups are
`20260801-221505F_20260803-131858I` locally and
`20260801-221522F_20260803-131904I` off-host; repository, WAL, and application
readiness checks passed. This was a guarded data-only correction. No source,
container, schema, migration, frontend, worker, scheduler, native, or APK changed;
backend container `d60b88ec573f` remained healthy and readiness reports
`database=ok` and `migration=current`.

## 2026-08-03 avatar 83 and 87 retirement follow-up

Avatar IDs `83` and `87` are now also retired from assignment, leaving 22
assignable girl avatars. Their artwork remains present and displayable for rollback
and stale clients; no asset was deleted. The first guarded live operation replaced
all 10 active assignments of avatar 83 and assigned four previously missing avatars
after an explicit manual correction of invalid or unspecified gender values on
unmistakable synthetic pilot records. Visual QA then caught that one random
replacement and existing assignments used the similarly prismatic avatar 87, so a
second guarded pass replaced all 13 active assignments of avatar 87. This was a
one-off data correction, not name-inference logic in the product. At that point two
records remained unspecified and avatarless; the complete-demo follow-up above
resolved their intended seed value and assigned them.

The completed state has zero retired assignments, zero wrong-gender-pool
assignments, zero assignments without a valid recorded gender, and zero duplicate
avatar groups in current active classes. A repeat dry run targeted and changed zero
students. The pre-change encrypted incremental backups are
`20260801-221505F_20260803-130323I` locally and
`20260801-221522F_20260803-130328I` off-host; repository, WAL and application
readiness checks passed.

Focused avatar coverage passed 3/3 locally and 3/3 inside the deployed backend
image. Both replacement assets return HTTP 200, readiness reports `database=ok`
and `migration=current`, and recent backend logs contain no relevant error entry.
Only the backend was rebuilt and recreated, first from `4e09017b0358` to
`85098ce32fd3` and then to final container `d60b88ec573f` after visual QA retired
avatar 87. The frontend `046fa48792c1`, PostgreSQL `9653df2c5588`,
messaging worker `8919cebb3330`, and notification scheduler `2909345e8a68`
retained their identities. There is no schema migration, frontend, asset, native,
or APK change. Source implementation commits: `890a5b5` and `1e57c4f`.

## 2026-08-03 gender-safe avatar assignment release

Avatar IDs `56`, `59`, `67`, `75`, `77`, `89`, and `90` are no longer
assignable. The artwork remains present and displayable for rollback and stale
clients; no source or runtime asset was deleted. The remaining assignable pools
contain 28 boy avatars and 24 girl avatars. Assignment uses only the school's
recorded `male` or `female` value, never a name-based guess, and now checks every
current classmate before choosing an avatar.

A fresh encrypted pgBackRest incremental backup completed to both local and
off-host repositories immediately before the data operation. Labels are
`20260801-221505F_20260803-123230I` locally and
`20260801-221522F_20260803-123239I` off-host. Disposable PostgreSQL copies proved
both the main backfill and final strict-gender clearing through dry run, apply,
and idempotent post-apply dry run; their temporary databases and worktrees were
then removed.

The live aggregate-only operation assigned 398 previously missing avatars and
replaced all 16 retired assignments: 232 female and 182 male students received
gender-pool-safe avatars. A final strict-gender pass cleared three legacy
assignments whose records lacked a valid `male` or `female` value. In total, 417
records changed. All six active records without valid recorded gender are now
intentionally avatarless until the school corrects them. The final state has zero
retired assignments, zero wrong-gender-pool assignments, zero assignments without
valid recorded gender, and zero duplicate avatar groups across current active
classes. A repeat live dry run targeted and changed zero students.

Focused tests passed 47/47 both locally and inside the deployed backend image.
The public root and retained avatar 56 asset return HTTP 200, recent backend logs
contain no traceback, exception, fatal, critical, or uncaught entry, and readiness
reports `database=ok` and `migration=current`. Only the backend was rebuilt and
recreated, changing from container `a14bcbf565eb` to final container
`4e09017b0358`. The frontend
`046fa48792c1`, PostgreSQL `9653df2c5588`, messaging worker `8919cebb3330`, and
notification scheduler `2909345e8a68` retained their identities. There is no
schema migration, frontend, worker, scheduler, asset, native, or APK change.

## 2026-08-03 capability-relationship guidance release

The Dom-only school-capability manager now explains every catalogue relationship
in both directions. A capability card states what it requires, while a capability
used by another feature states which features use it. For example, Behaviour and
points shows that it is used by Positive recognition, and Positive recognition
shows that it requires Behaviour and points.

Trying to turn off a capability that an enabled feature still uses now opens a
plain-language English or Arabic dialog naming the blocker and linking directly to
its card. The same treatment covers attempts to turn on a feature before its
required feature and availability dates that do not fit within the required
feature's dates. The manager never switches related capabilities off
automatically. Existing server validation remains the final protection and its
structured relationship response is retained by the frontend for the same friendly
handling if the page is stale.

Implementation commit `2ed2aa3` passed five focused relationship cases, the six
existing backend entitlement tests, English/Arabic parity at 2,217 keys, Svelte
diagnostics with zero errors or warnings and the production frontend build. Direct
rendered inspection covered English and Arabic/RTL desktop layouts and the Arabic
dialog at 390 x 844, with no horizontal overflow. The Review action closed the
dialog, scrolled to the named capability and focused its card.

Only the CHH frontend was rebuilt and recreated. The replacement container is
`046fa48792c1` with image `0d907e1c49a4`; it is healthy. The backend
`a14bcbf565eb`, PostgreSQL `9653df2c5588`, messaging worker `8919cebb3330` and
notification scheduler `2909345e8a68` retained their existing identities and were
not restarted. Public readiness reports `database=ok` and `migration=current`, the
frontend root returns HTTP 200, both new English and Arabic messages are present in
the deployed bundle, and recent frontend logs contain no error, fatal, critical,
uncaught or traceback entry. There is no database, migration, backend, worker,
native application or APK change.

## 2026-08-03 canonical school-entitlement release

CHH now has one canonical, fail-closed entitlement authority for optional school
capabilities. The catalogue covers homework/diary, notices/calendar,
behaviour/points, positive recognition, surveys/polls, school chats, chat photos,
voice notes, the Family Hero Hub connection, school-family updates, update photos,
reports/insights, safeguarding, and student/staff import-export. Foundation identity,
access, school structure, people/assignments, security/audit and read-only
entitlement visibility remain available to every school. Dependencies and effective
date windows are enforced at read time and mutation time. Safeguarding remains
independent from participant chat availability.

Entitlements determine what a school may use; the existing school-administrator
messaging, voice-note, receipt, contact-hours and points-notification controls remain
where they were and continue to determine what the school chooses to enable. When
the parent entitlement is unavailable, those controls stay visible but disabled,
their action APIs fail with the stable `capability_not_enabled` response, and their
stored values are not changed. Pre- and post-deployment row counts and full-row
fingerprints matched for `school_feature_controls`,
`school_feature_control_audit_events`, `school_messaging_policies` and
`school_points_notification_policies`.

Alembic revision `a1e2f3c4d5b6` adds canonical entitlement rows, optimistic
versions, append-only full-snapshot events and the stored platform authority flag.
The one existing pilot school was backfilled with all 14 optional capabilities as
enabled pilot grants, producing 14 initial events. Dom's verified active platform
account is the sole row with entitlement-management authority; runtime checks use
that database flag and never compare email addresses. New schools receive no
optional entitlement rows and therefore start foundation-only. A restored pilot
database passed upgrade, forced append-only rejection, downgrade to
`a0b1c2d3e4f5`, object/flag removal, and clean re-upgrade with identical counts.

Before the live migration, encrypted differential backups completed in both
repositories: local `20260801-221505F_20260803-094522D` and off-host
`20260801-221522F_20260803-094532D`. Both contained `11,235,248` repository bytes;
the subsequent backup health check and application readiness were `ok`.

Implementation commits `cf62681` and `22b0cba` were deployed on pilot `main`.
The second commit advances the readiness revision after the schema upgrade. The
backend, frontend, messaging production worker and notification scheduler were
rebuilt and recreated; PostgreSQL was not restarted. Their deployed container IDs
begin `a14bcbf5`, `9d569064`, `8919cebb` and `2909345e`; all are healthy. Public
`/` and `/api/health/ready` return HTTP 200, readiness reports
`database=ok`/`migration=current`, and recent affected-service logs contain no
fatal, traceback, critical or uncaught error. Live database verification reports
one school, 14 enabled entitlement rows, 14 append-only events, one authorised
manager and one school with the complete 14-capability pilot grant.

Focused entitlement, platform-authority, operational-preservation, feature,
foundation/auth/structure, messaging, worker and prerequisite suites passed,
alongside Python compilation, Svelte diagnostics with zero errors or warnings,
English/Arabic parity at 2,204 keys and the production frontend build. A small set
of unrelated legacy guardian-auth, invitation and dated notification-policy tests
was reproduced at the unchanged baseline and was not altered in this release.

The bundled Android frontend advances `com.classherohub.app` to code `16`, version
`1.14-school-entitlements-pilot`. The verified APK is
`class-hero-hub-school-entitlements-v1.14-code16-20260803.apk`, `96,509,761` bytes,
SHA-256
`913e22c84eab3c957e8dee9e04485248f08d668747c7db642e6319387550e18f`.
The remote build, Windows copy, Google Drive copy and installed RMX3997 base APK are
byte-identical. `adb install -r` preserved the original first-install time,
app-data inode, notification and microphone grants, and authenticated school
session. On-device checks at 360 CSS pixels found 14 entitlement cards, the existing
operational controls, no horizontal overflow or console error, and equivalent
Arabic RTL layout. Detailed Android evidence is in
`docs/implementation/CHH_ANDROID_APK_IMPLEMENTATION_LOG.md`. Release tag:
`chh-school-entitlements-pilot-code16-20260803`.

## 2026-08-03 final public editorial and hero-layout release

The English homepage hero now leads with `Help teachers. Keep families
informed.` and explains in direct language that Class Hero Hub brings homework,
behaviour, recognition, notices, chats, surveys and family updates together
alongside the systems a school already uses. The matching Arabic copy was
written for the same meaning in natural Modern Standard Arabic. The main family
section now leads with `School updates for families.` and states simply that
staff use Class Hero Hub while parents see the school updates shared with them in
Family Hero Hub.

Public marketing sentences that read like internal product or implementation
language were rewritten in plain English and natural Arabic. Examples now say
`Start with your class`, `Pick up where you left off`, `See whether messages have
arrived and been read`, `See what changed and when`, and `The tools teachers use
most are easy to find`. The existing teacher, communication and family-update
positioning is unchanged: CHH works alongside existing school systems, is not
presented as an MIS or SIS replacement, and setup, imports and reporting remain
secondary. Parents continue to use Family Hero Hub rather than signing in to
CHH.

The homepage hero spacing and desktop type breakpoint were tightened without
reducing the normal body or button text sizes. At 1366 x 768, the full English
headline, introduction and primary pilot button are visible without scrolling.
Rendered English and Arabic inspection also passed at 390 x 844 with no
horizontal overflow and correct RTL presentation.

Focused validation passed the six public-copy catalogue tests, Svelte diagnostics
with zero errors or warnings, the production frontend build, all 21 public-page
browser tests, the ten-case responsive route matrix covering all 16 public routes
in both languages at five widths, and all eight public 320-430 px visual-layout
checks. Live route probes returned HTTP 200 for the home, Product, How it works,
Schools, Family connection, Pilot, Privacy Policy and Terms pages. Direct live
inspection covered both homepage languages at 1366 x 768 and 390 x 844, plus the
Arabic family-connection page. The four authenticated dashboard cases in the
broader visual-layout file were not applicable because the local QA login token
was not supplied; authenticated routing and application code were not changed.

Implementation commit `20c328b` was deployed by rebuilding and recreating only
the CHH frontend. The replacement frontend container is `859bfff01dda` with image
ID `7cab51f720f3`; it is healthy. The backend (`c551b9d2c6da`), PostgreSQL
(`9653df2c5588`), messaging production worker (`bf724969582b`) and notification
scheduler (`52c145d59912`) retained their existing container identities and were
not restarted. Readiness reports `database=ok` and `migration=current`. The
Privacy Policy, Terms, effective dates, pilot-enquiry behaviour, routes,
authentication, product images, FHH, database, migrations and native application
are unchanged; no APK was built.

## 2026-08-03 everyday-workflow public positioning release

The CHH public website now presents Class Hero Hub as a practical workspace for
teachers, school communication, follow-up and family updates that complements the
systems a school already uses. The public copy does not position CHH as an MIS or
SIS replacement and makes no claim of live integration or synchronisation. A
capability check confirmed that administrators can enter supported student and
staff details manually or stage, review and apply CSV files; that supporting
setup appears after the human workflow story rather than leading it.

The homepage now uses the single positioning line `School life, clearly
connected.` and follows this order: the everyday teacher/staff problem and
benefit; classroom and communication workflows; the CHH-to-FHH family
connection; genuine product proof; leader visibility and follow-up; supporting
setup alongside existing systems; trust, bilingual support, FAQ and pilot call
to action. The teacher workspace image is the first product view and uses the
full content width so its class and action labels remain readable. The school
setup image follows as secondary evidence.

The Product overview now leads with teaching, contextual communication and
follow-up, with school setup last. How it works now starts from the class or
message in front of a staff member, carries the appropriate update to Family
Hero Hub and explains workspace setup last. For schools now leads with teachers,
then the wider school team, leaders/administrators and bilingual communities.
The FAQ explains in one concise answer how CHH works alongside existing systems
and truthfully describes reviewed CSV setup for supported student and staff
details. English phrasing was tightened throughout these surfaces, while the
matching Arabic copy was edited as natural Modern Standard Arabic rather than a
literal structural translation.

The visible highlights on both the Privacy Policy and Terms of Service now show
`Effective 3 August 2026` and `سارية من 3 أغسطس 2026`. The legal structure,
pilot enquiry form and mail delivery, staff authentication, role-aware Dashboard
routing, native startup, existing product images and FHH behaviour are unchanged.
There is no backend, database, migration, school-data, FHH, native or APK impact.

Focused validation passed the paired public-copy catalogue and positioning/date
tests, Svelte diagnostics with zero errors or warnings, the production frontend
build, 21 public-flow browser tests, the 160-combination English/Arabic public
route and responsive-width matrix, eight 320–430 px public layout checks and 24
authenticated navigation/language-switcher tests. Direct rendered inspection
covered the English hierarchy and product-proof order, the Arabic RTL homepage
and the visible Arabic Privacy Policy effective date.

Implementation commit `7a646df` was deployed by rebuilding and recreating only
the CHH frontend. The replacement frontend container is `a7a28c885229` with image
ID `710ba359190b`; it is healthy. The backend (`c551b9d2c6da`), PostgreSQL
(`9653df2c5588`), messaging production worker (`bf724969582b`) and notification
scheduler (`52c145d59912`) retained their existing container identities and were
not restarted. Readiness reports `database=ok` and `migration=current`, and the
home, Product, How it works, Schools, Privacy Policy and Terms routes return HTTP
200 over the deployed origin.

Post-deployment browser validation passed all 16 public routes in both languages
at 390 px, including RTL direction, accessible navigation, image loading and
horizontal containment. Direct live desktop inspection confirmed the English and
Arabic heroes, the homepage story and teacher-first proof order, and the visible
effective date on both legal pages in both languages. The wider live matrix used
the suite's 30-second per-case budget and timed out only during later
`networkidle` waits; the identical five-width matrix had already passed locally,
and the bounded live bilingual run passed with a realistic remote timeout.

## 2026-08-03 public website editorial and pilot-enquiry release

The CHH public website has been rewritten for school leaders, administrators and
teachers while retaining the established brand, responsive layouts, public route
map, English/Arabic switching, RTL behaviour, staff login, authenticated
Dashboard routing and Capacitor/native startup behaviour. The new copy leads with
the practical outcomes for a school: less switching, quicker teacher workflows,
clearer family updates and more useful follow-up. Repetitive implementation and
procurement-style checklists were consolidated into shorter page narratives.

The home page now includes two genuine CHH interface views captured from the
current product with a synthetic `Riverside Demonstration School`, synthetic staff
and synthetic class data. The static assets are
`frontend/static/product/school-overview.png` and
`frontend/static/product/teacher-workflow.png`; they contain no deployed school,
student, message, survey or safeguarding information.

The family explanation is intentionally simple: school staff work in Class Hero
Hub and parents see the school information shared for their linked child in Family
Hero Hub. The public website no longer describes integration internals, identifier
handling or the special case of a staff member who is also a parent. FHH source and
deployment are unchanged.

The pilot page now offers three steps—understand the school, show the relevant
product and agree the next step—plus a minimal enquiry form. `POST
/api/public/pilot-enquiries` validates and bounds name, school, role, country or
region, email and message fields, rejects line breaks in email-header fields, and
allows five submissions per client IP in ten minutes. It stores no enquiry in the
CHH database. The backend sends the message to the published CHH support address
using the existing SMTP service, sets the visitor address as `Reply-To`, records no
message content in application logs and returns success only after the configured
mail server accepts the email. Missing SMTP configuration or a delivery exception
returns HTTP 503; the page then keeps the direct
`support@classherohub.com` alternative visible. Existing `SMTP_HOST` and
`SMTP_FROM_EMAIL` settings are the only required delivery configuration.

The Privacy Policy and Terms of Service now provide plain-language pilot baselines
without public drafting notes, personal references or unsupported claims. They
cover the service, information and uses, school and service responsibilities,
authorised use, necessary providers, retention and security principles, requests,
pilot limitations and contact. They state neutrally that applicable law and a
signed school agreement may add local terms. Outstanding decisions for qualified
counsel are kept only in
`docs/planning/CHH_PILOT_LEGAL_COUNSEL_CHECKLIST.md`.

There is no database schema, migration, school-data, FHH, native or APK change.
The release was deployed to the CHH pilot host from commit `8c061911` by
rebuilding and recreating only the CHH backend and frontend. PostgreSQL was not
recreated, and the messaging-production worker and notification scheduler kept
their existing container identities.

Pre-deployment validation passed the public-copy catalogue tests, English/Arabic
parity at 2,153 keys, Svelte diagnostics with zero errors or warnings, the
production frontend build, eight focused enquiry/mailer tests, 20 public-flow
browser tests, the 10-case public route matrix covering 160 route/language/width
combinations, 17 authenticated role-navigation tests and seven authenticated
language-switcher tests. The rendered English and Arabic home, product-proof and
pilot-form surfaces were also inspected directly. Form success and failure were
tested with controlled mail transport substitutes; no unsolicited live enquiry
email was sent during pre-deployment validation.

Post-deployment readiness reported `database=ok` and `migration=current`; the
frontend, backend, PostgreSQL and both workers were healthy. The home page, pilot
page and both product images returned HTTP 200 over the public HTTPS route, while
an empty enquiry returned HTTP 422 without invoking mail delivery. All 54 live
Playwright cases passed, including the 160 route/language/width combinations,
public and login routes, native signed-out routing, mocked enquiry acceptance and
failure, and separate authenticated navigation/language checks. Direct live
inspection covered the English hero and product visuals plus the Arabic RTL pilot
form and legal routes. Fresh frontend/backend logs showed normal successful asset,
health and expected signed-out authentication responses, with no application
exception or traceback.

## 2026-08-02 bilingual public website pilot release

The CHH root now presents the complete Class Hero Hub public website rather than
the previous placeholder. Its positioning line is `School life, clearly
connected.` The public information architecture covers the home page, product
overview, how it works, schools, the Family Hero Hub connection, pilot enquiries,
FAQ, contact and support, administrator/teacher/family guides, safety and privacy,
the Privacy Policy, Terms of Service, and data/account requests. Every surface has
paired professional English and Arabic copy, document-level LTR/RTL switching,
responsive navigation and the shared support address
`support@classherohub.com`.

The website keeps the product boundary explicit. CHH is for authorised school
staff and school roles. Parents and guardians do not sign in to CHH; linked
homework, notices, updates, school points, calendar items, surveys and School
Chats appear in Family Hero Hub when the school enables the corresponding
feature. FHH continues to own family, household, child and device identity, and
family clients never call CHH directly. The coordinated FHH public-home wording
links to the CHH family-connection explanation without changing FHH application
behaviour.

Public routes use a dedicated marketing header, compact drawer and full
product/support/legal footer. Authenticated school routes retain the existing
role-aware application shell and staff login. The Capacitor/native root detection
and signed-out redirect to `/login` are preserved, so native users do not enter
the marketing website. Pilot calls to action make no pricing promise. The legal
pages deliberately identify the outstanding professional review of controller and
processor roles, jurisdiction, retention, subprocessors, transfer rights,
governing law, liability, service levels and commercial terms instead of inventing
them.

Focused validation passed Svelte check with zero errors or warnings, public-copy
shape and CHH/FHH boundary tests, English/Arabic parity at 2,153 catalogue keys,
the production static build and an 18-case Playwright public-route suite. The
browser suite covers all public routes, internal links, signed-out staff login,
English/Arabic switching, document language and direction, console/page errors,
horizontal containment and the native root bypass. Direct visual checks at 390,
768, 1024, 1280 and 1440 CSS pixels covered the hero, desktop and compact headers,
mobile drawer and footer; Arabic RTL was checked at 390 pixels. No database,
migration, backend, permission, integration protocol or native bundle changed.

CHH implementation commit `df7286d` and the coordinated FHH public-copy commit
`4d4d59c` were deployed by rebuilding and recreating only each system's frontend.
Both replacement frontend containers are healthy. The existing CHH and FHH
backends, PostgreSQL containers, notification/lifecycle workers and CHH messaging
worker/scheduler retained their prior container IDs and uptimes. All 16 CHH public
routes and the FHH home return HTTP 200; anonymous `/api/me` remains HTTP 401 on
both systems; and both readiness endpoints report `database=ok` and
`migration=current`. The 18-case public-route Playwright suite also passed against
the deployed CHH origin. A signed-in hosted check retained the role-aware
`/platform` workspace with no public marketing chrome, and the language preference
was restored to English after the RTL check.

## 2026-08-02 authenticated language switcher pilot release

The Arabic catalogue and RTL shell were already persistent, but the only visible
language control was on public/login surfaces. Once authenticated, administrators
and teachers could not change language without leaving their workflow. The global
layout now reuses the established language selector in both authenticated shells:
after the existing destinations and before Logout in the desktop navigation, and
at the top of the compact drawer before its destinations. The control uses a globe,
shows the native-script choices `English` and `العربية`, exposes a localised
accessible name and focus indicator, and uses no flags. Existing navigation order,
routes, query parameters, role gates and permission checks are unchanged.

The selector continues to use the existing `familyHeroHub.language` preference.
Changing it updates the document `lang` and `dir` immediately without navigation;
the current path, query context, selected tab and open drawer are retained. The
preference is not removed on logout, so it survives navigation, refresh, a later
authenticated browser tab and an Android force-stop/cold launch. English remains
LTR with its previous wording. Arabic remains RTL and continues to preserve
school-entered names and content exactly as supplied; no school data is translated
by this control.

Implementation commit `803ae5f` was deployed by rebuilding and recreating only the
pilot frontend. Public HTTP returned 200, readiness returned `database=ok` and
`migration=current`, and every Compose service remained healthy. The backend,
PostgreSQL, notification scheduler and messaging production worker were neither
rebuilt nor restarted. There is no schema, migration, data or configuration change.

Validation passed Svelte check with zero errors or warnings, English/Arabic parity
at 2,153 keys per locale, all 93 Node tests, the production frontend build and a
92-case serial Playwright matrix. The matrix covers the authenticated selector,
global navigation/state, School setup, administration, messaging, safeguarding,
recognition, mobile workspaces and native shell behaviour at 390, 768, 1024, 1280
and 1440 CSS pixels. A signed-in hosted Chrome check retained
`/school?tab=years&context=school-7` while switching both directions, confirmed
immediate `lang`/`dir` and content changes, refresh and fresh-tab persistence,
drawer retention, correct logical drawer edge and zero horizontal overflow. The
hosted console contained no error.

### Authenticated language switcher pilot APK

- Package `com.classherohub.app`; version code `15`; version name
  `1.13-authenticated-language-switcher-pilot`; min SDK 23 and compile/target SDK
  35.
- Artifact:
  `/opt/apps/class_hero_hub/tmp/class-hero-hub-authenticated-language-switcher-v1.13-code15-20260802.apk`;
  identical Windows and Drive copies at
  `C:\Users\Dom\Documents\CHH - FHH\class-hero-hub-authenticated-language-switcher-v1.13-code15-20260802.apk`
  and
  `G:\My Drive\CHH\Remote\class-hero-hub-authenticated-language-switcher-v1.13-code15-20260802.apk`.
- Size `96,323,953` bytes; SHA-256
  `0d21f315daf28fc35947f04073acd4a0ea54f720f481302ac0a824891b6e2afd`.
- Android Debug signer DN `C=US, O=Android, CN=Android Debug`; certificate SHA-256
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
  APK signature schemes v1 and v2 verify; v3/v4 are not used by this debug build.
- `testDebugUnitTest`, `lintDebug`, `assembleDebug` and
  `assembleDebugAndroidTest` passed on Temurin 21.0.11 and Android SDK/build tools
  35. Package/version, signer and source/local/Drive hashes passed. All 356
  production build files are byte-identical to their Capacitor bundle copies; the
  installed base APK pulled from the RMX3997 is byte-identical to the delivered
  file.

`adb install -r` upgraded code 14 in place. The original first-install timestamp
(`2026-07-18 22:47:59`), app-data inode (`9258`) and notification/microphone grants
were preserved. On the physical RMX3997, the authenticated Arabic choice survived
the upgrade, the drawer selector visibly switched Arabic to English and back
without closing or changing `https://localhost/school`, and the drawer moved to the
correct logical edge. Native Back closed the drawer while retaining the route.
Both English/LTR and Arabic/RTL survived separate force-stop/cold launches, restored
the authenticated School setup workspace, and measured `clientWidth=360` and
`scrollWidth=360`. No fatal application or WebView error was found. The device was
left authenticated in Arabic on School setup. No production environment was
touched. Release tag: `chh-authenticated-language-switcher-pilot-code15-20260802`.

## 2026-08-02 Arabic localisation audit pilot release

The CHH-wide Arabic audit found three localisation gaps that ordinary catalogue
parity could not detect. School setup checklist labels came from English backend
display strings and were rendered verbatim; survey administration kept much of its
system copy inline in English; and several school, class, subject, status, role and
result components displayed API values directly despite an active Arabic locale.
Unknown English backend error details could also pass through the shared API client.
The signed-in pilot audit additionally found date, time and report-number formatters
using the browser default locale, so Arabic pages could still show English month
names. Those formatters now select Arabic only in Arabic mode and retain the
previous browser-default formatting in English mode.

The release maps stable School setup checklist keys, invitation and plan result
values to paired catalogue entries, moves all survey composer/results system copy
and accessibility labels into the shared catalogue, and prevents English backend
error fallbacks from appearing in Arabic mode. Platform, School setup, Students and
Import & Export, Behaviour & points, Reports, Recognition, Surveys, Messages,
Safeguarding, System & compliance and teacher/class surfaces were checked for
literal visible text and physical-direction CSS. Shared controls now use logical
start/end positioning; arrows and chevrons mirror in RTL; and protected-message
photo navigation reverses its visual, keyboard and swipe directions in Arabic.
English rendering paths retain their previous wording and API values.

Arabic display prefers an existing `name_ar` for schools, branches, years, stages,
grades, classes, subjects and subject groups. If a school has not supplied an
Arabic value, CHH deliberately shows the exact school-entered name or code instead
of inventing a translation. Student, guardian, survey, announcement, message,
recognition and safeguarding content also remains user/school-entered data. The
controlled educational terms use `السنوات الدراسية`, `المراحل التعليمية`,
`الصفوف/المستويات الدراسية`, `الشعب` and `مجموعات المواد`; the survey workflow uses
`الاستجابات`, `معدل الاستجابة`, `وحدة الاستجابة` and `مقياس تقييم`.

Implementation commits `209655e` and `0e1e499` were deployed by rebuilding and
recreating only the pilot frontend. All services are healthy; loopback and public
frontend checks return HTTP 200 and readiness reports `database=ok` and
`migration=current`. The backend, PostgreSQL, scheduler and messaging production
worker were not rebuilt or restarted. There is no schema, migration, configuration,
route, permission or data change, so no database backup or rollback action was
required.

Validation passed 62 focused localisation, School setup, student, teacher, survey,
messaging, recognition and navigation tests; English/Arabic parity at 2,153 keys per
locale; Svelte check with zero errors or warnings; and the production static frontend
build. A final 84-case serial Playwright matrix passed navigation and URL state,
School setup, administration, messaging, safeguarding, recognition, survey/mobile
workspaces and native shell behaviour. Its English/Arabic checks cover 390, 768,
1024, 1280 and 1440 CSS pixels where applicable, Android Back order and horizontal
containment.

A signed-in hosted audit covered representative platform-administrator and
school-administrator routes at mobile, tablet and desktop widths in Arabic/RTL, plus
an English/LTR desktop control. Platform, School setup, Behaviour & points, Students,
Student Import & Export, Reports, Recognition, Surveys, Messages, System &
compliance and Safeguarding had no horizontal overflow or unexplained English system
labels. The current pilot account has no teacher membership, so the live `/teach`
check correctly showed the localised access boundary; the true teacher role and
class workflow are covered by the passed mocked-role browser matrix. The visible
`United International School` and restored guardian-survey title are intentional
school-entered data, not system-text fallbacks.

The bundled code-14 frontend and hosted build come from the same final application
source. Capacitor's copied public assets are byte-identical to the production build
counterparts apart from its expected bridge files, including an identical
`index.html` SHA-256 of
`ed059965f70525f5c2ddda6bedf037fb3af1446b26ca96aba196a116e93f0bd4`.

### Arabic localisation pilot APK

- Package `com.classherohub.app`; version code `14`; version name
  `1.12-arabic-localisation-pilot`; min SDK 23 and compile/target SDK 35.
- Artifact:
  `/opt/apps/class_hero_hub/tmp/class-hero-hub-arabic-localisation-v1.12-code14-20260802.apk`;
  identical Drive copy at
  `G:\My Drive\CHH\Remote\class-hero-hub-arabic-localisation-v1.12-code14-20260802.apk`.
- Size `96,323,858` bytes; SHA-256
  `2e82c67f4a9f3ac6dc9157959682490132725aad1ff717bd8ab009631e40ac3d`.
- Android Debug signer DN `C=US, O=Android, CN=Android Debug`; certificate SHA-256
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
  APK signature schemes v1 and v2 verify; v3/v4 are not used by this debug build.
- `testDebugUnitTest`, `lintDebug`, `assembleDebug` and
  `assembleDebugAndroidTest` passed on Temurin 21.0.11 and Android SDK/build tools
  35. ZIP integrity, package/version, signer and source/local/Drive hashes passed.

`adb install -r` upgraded the RMX3997 from code 13 without uninstalling. The original
first-install timestamp, app-data inode and notification/microphone grants were
preserved; the pulled installed base APK is byte-for-byte identical to the delivered
file. Physical Arabic/RTL verification covered launch into the authenticated School
setup workspace, the full drawer hierarchy, School setup, platform administration,
Behaviour & points, Students, Import & Export, Reports, Recognition, Surveys,
Messages, System & compliance, Safeguarding and the teacher access boundary. The
360-CSS-pixel WebView reported zero horizontal overflow on every checked route;
safe areas, RTL order, mirrored controls and drawer-first/native route Back behaviour
were correct, and a fresh-launch log contained no application/runtime or WebView
console error. The app was left authenticated in Arabic on School setup.

Physical English switching was intentionally not attempted because this authenticated
route exposes no language selector and logging out would discard the retained pilot
session. English mode is instead covered by the passed source, browser matrix and
signed-in hosted checks. No production environment was touched. Release tag:
`chh-arabic-localisation-pilot-code14-20260802`.

## 2026-08-02 compact School setup navigation

The compact School setup navigation no longer renders six large accordion groups
inline above the selected page. That duplication was the root cause of the
Android-like navigation failure: the global layout already owned a safe-area-aware
hamburger drawer and native Back handling, while the School setup page separately
owned an inline compact menu. The desktop sidebar also began at 1024 CSS pixels,
leaving tablet widths outside the compact application pattern.

At widths up to and including 1024 CSS pixels, the existing hamburger drawer now
contains the same six permission-aware School setup groups and destinations as the
desktop sidebar. The links retain their existing paths and `?tab=` URLs, expose one
purple `aria-current=page` state, close the drawer on selection and restore the
selected section at the top of the School setup workspace. The drawer mirrors to
the logical end edge in Arabic RTL, owns its safe-area-aware scroll region, and
contains no accordion elements. Native Back closes the drawer before the existing
School setup URL/history hierarchy. The grouped desktop sidebar remains unchanged
from 1280 CSS pixels.

Validation passed Svelte checking with zero errors/warnings, English/Arabic parity
at 2,007 keys per locale, 14 focused navigation/menu/URL-state source tests, and
the production frontend build. Fifteen containerised Playwright cases passed in
English and Arabic/RTL at 390, 768, 1024, 1280 and 1440 CSS pixels, including
open/close, one current item, destination selection, URL refresh, native Back,
safe content placement and zero horizontal overflow. A signed-in deployed Chrome
check at 390, 768 and 1024 CSS pixels confirmed the six-group drawer, selected
Academic years state, close-on-selection, preserved `/school?tab=years`, no inline
navigation and zero horizontal overflow.

Implementation commit `bb742c1` was deployed by rebuilding and recreating only the
CHH pilot frontend. Loopback and public `/school` checks returned HTTP 200,
readiness returned `database=ok,migration=current`, and all pilot services are
healthy. Backend, PostgreSQL, the notification scheduler and messaging production
worker retained their running containers. Configuration, schema and data were
unchanged; no backup or migration was needed.

The authorised in-place pilot APK keeps package `com.classherohub.app`, raises the
version to code `12` / name `1.10-school-setup-drawer`, and uses the exact installed
Android Debug certificate SHA-256
`e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
The build passed app unit tests, lint, debug APK assembly, test-APK assembly, ZIP
integrity, package/version inspection, v1/v2 signature verification and byte-level
Capacitor entry-point parity. `adb install -r` succeeded without uninstalling;
the original install timestamp, app-data inode, encrypted-preference file set,
notification permission and microphone permission were preserved. The installed
APK is byte-for-byte identical to the delivered build.

The delivered file is
`class-hero-hub-school-setup-drawer-v1.10-code12-20260802.apk`, size `96,318,038`
bytes, SHA-256
`c5bdd0c2d5034cb88ea5aa641f7879e305e44e156bccb77afe823b727444fe80`.
The verified source is `/opt/apps/class_hero_hub/tmp/`; the identical Windows copy
is in `G:\My Drive\CHH\Remote\`. After unlock, the app reopened directly into the
authenticated Teach workspace. The global drawer respected the physical status and
navigation insets, Android Back closed it first, and the 360 CSS pixel WebView
reported `scrollWidth=360` with zero horizontal overflow.

An authorised school-administrator OAuth session then completed the English
physical check. School setup showed no inline navigation; the drawer exposed all
six groups plus Students, Student Import & Export, Reports, Positive recognition
and System & compliance. Checklist and Academic years each showed the single
purple current state. Selecting Academic years closed the drawer, retained
`/school?tab=years` and put its form in the first viewport. The first Android Back
closed the reopened drawer while preserving that URL; the next Back returned to
the checklist hierarchy. The complete drawer remained inside the physical status
and navigation safe areas with internal scrolling and no horizontal clipping.

The visible language selector switched the physical login screen to Arabic with
correct RTL mirroring. A subsequent authorised administrator check exposed a
code-12 Back-state defect: after leaving the Academic years drawer item, the first
Back closed the drawer correctly and the next Back removed `?tab=years`, but the
Academic years content remained visible. The page was reading stale router state
after native history traversal. Commit `d50a370` now synchronises the selected
School setup content from the current browser URL during Back traversal, and
commit `4b48d87` strengthens the browser regression to require checklist content,
not only the checklist URL.

The corrective frontend was deployed and the focused source test, Svelte check,
2,007-key English/Arabic parity check, production build and 15-case responsive
Playwright matrix passed. Compose recreated the frontend and its backend dependency;
no backend source or configuration changed, and backend/frontend readiness returned
healthy with `database=ok,migration=current`. PostgreSQL, notification scheduler
and messaging production worker were unchanged.

Because the signed and delivered code-12 APK could not be safely overwritten, the
corrected in-place pilot is code `13` / name
`1.11-school-setup-drawer-back`. It retains package
`com.classherohub.app` and the same installed Android Debug certificate SHA-256
`e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
Android unit tests, lint, debug APK assembly, test-APK assembly, ZIP integrity,
package/version and v1/v2 signature checks passed. `adb install -r` succeeded; the
original install time, app-data inode and notification/microphone grants remained
unchanged. The first post-install launch required one administrator OAuth
re-authentication even though app data was retained; a subsequent forced cold start
restored that authenticated session normally.

The code-13 physical Arabic/RTL check used the authorised administrator account.
The drawer showed the grouped hierarchy and one purple current item, closed on
Academic years selection and kept content clear of status/navigation insets. The
first Back closed the reopened drawer and retained `/school?tab=years`; the next
Back restored both `/school` and checklist content. WebView inspection reported
`dir=rtl`, `lang=ar`, 360 CSS pixels for both viewport and document width, and zero
horizontal overflow. Login, OAuth return and the Arabic safe-area layout also
worked. No remaining drawer-specific English/Arabic difference was found.

The final file is
`class-hero-hub-school-setup-drawer-back-v1.11-code13-20260802.apk`, size
`96,318,009` bytes, SHA-256
`ab76f092f06252a7168225458a15a37e9ab3ec6b168a3cb0bb59fe742863408a`.
The server source, pulled installed APK and Drive copy are byte-for-byte identical.
The Drive path is
`G:\My Drive\CHH\Remote\class-hero-hub-school-setup-drawer-back-v1.11-code13-20260802.apk`.
The code-12 file remains retained as the superseded pilot artifact and was not
overwritten or relabelled.

## 2026-08-02 multi-school context pilot-scope assessment

Multi-school switching was assessed and intentionally not implemented. A read-only,
aggregate check of the live pilot found exactly one school, with no suspension, and
zero users holding active memberships across more than one school. The same-role
counts are also zero for school administrators and teachers, and there are no mixed
staff accounts spanning schools. This confirms the earlier audit decision in
`docs/audits/2026-07-07-post-s4-fable-checkpoint-audit.md` and
`docs/audits/2026-07-07-post-s5-teachers-assignments-audit.md`: the two-school test
harness protects tenancy, but switching UI does not pay for itself before a second
real pilot school exists.

The data model and `/api/me/v2` can represent multiple school memberships. Teach
already aggregates a teacher's active assignment cards, while Messages and Surveys
have their own membership selection. Core School setup, Students, Reports,
Recognition, System & compliance and related school-admin pages still resolve the
first active school-admin membership. That is unambiguous for the current one-school
pilot, but it must not become the multi-school design: before onboarding a second
pilot school or issuing any staff account an active membership in another school,
add an explicit shared school-context selection and remove silent first-membership
resolution across those pages.

Eighteen focused backend tests passed for cross-school School setup requests,
wrong-school role resolution, teacher dashboard/assignment scoping, platform-only
denial and deactivation boundaries. API readiness remains
`database=ok,migration=current`. Because the assessment showed no live multi-school
workflow, no runtime, URL, permission, localisation, configuration, schema or data
change was made. No build, service recreation, migration, backup or APK was needed;
all CHH pilot services retained their existing healthy containers. The assessment
is documented and tagged independently so the deferral and its activation condition
are explicit.

## 2026-08-02 recognition review usability

Recognition draft reviews now keep large and cutoff-tied shortlists inside a
bounded candidate list instead of extending the page by thousands of pixels.
Candidates render as compact rows with name, class, positive points, event count
and shared rank visible. Positive category detail, staff-only safeguard evidence,
recorded overrides and exclusion actions remain available in an expandable evidence
area; positive-only ranking, staff-only evidence boundaries and the existing audit
operations are unchanged.

The draft decision summary is presented before the candidate list on mobile and in
a sticky side panel from 1280 CSS pixels. It always shows the current selected
recipient, citation field and primary confirmation action. The selected row has a
consistent visible state in both LTR and RTL. The shortlist has contained scrolling,
stable scrollbar space and overscroll containment, while direct review URLs and the
existing Back hierarchy remain unchanged.

Validation passed eight focused Recognition source tests, English/Arabic parity at
2,007 keys each, Svelte checking with zero errors or warnings, and the affected
production frontend build. Ten containerised Playwright cases exercised 50-candidate
tied shortlists in English and Arabic/RTL at 390, 768, 1024, 1280 and 1440 CSS
pixels, including evidence expansion, last-row selection, enabled primary action,
sticky controls and zero horizontal overflow. The existing Recognition deep-link,
refresh and Back/Forward browser test also passed. Signed-in deployed-browser
verification opened a 90-candidate cutoff-tied pilot review and confirmed a 590px
bounded list containing 9,449px of rows, automatic internal scrolling, expandable
evidence and a visible sticky decision panel.

Implementation commit `263cd50` was deployed by recreating only the CHH pilot
frontend from the validated image. Loopback and public Recognition checks returned
HTTP 200, readiness returned `database=ok,migration=current`, and all pilot services
are healthy with no frontend startup errors. Backend, PostgreSQL, the notification
scheduler and messaging production worker retained their running containers.
Configuration, schema and data were unchanged; no backup, migration, native change
or APK was required. Physical Android Back, safe-area, touch-target and real-device
shortlist scrolling verification remain for Dom.

## 2026-08-02 URL and Back-state consistency

School setup tabs, Reports filters and open sections, Recognition review selection,
Student list/search/page/detail context, and Messages membership/inbox/conversation
context now use their existing route query strings. Refreshes and bookmarks restore
the same usable context. User-initiated context changes create browser history
entries, so browser Back/Forward follows the work a user performed instead of
silently replacing it; background refreshes continue to replace or preserve the
current entry without polluting history.

Page Back controls and the existing `chh:native-back` event share the same
hierarchy: close the current detail, review, report section or conversation first,
then return to the preserved list, overview or inbox. Direct deep links without a
prior in-app entry clear their local detail state safely rather than leaving the
application. Existing paths, school scoping, destinations and role/permission
checks are unchanged. No query value bypasses the existing school-scoped API.

Validation passed 41 focused navigation, messaging, recognition, reporting and
student source tests, English/Arabic parity at 2,002 keys each, and Svelte checking
with zero errors or warnings. The affected production frontend image built
successfully. Nineteen containerised Playwright checks passed, covering school-admin,
teacher and mixed-role flows, refresh, deep links, browser Back/Forward and native
Back. English and Arabic/RTL School setup checks passed at 390, 768, 1024, 1280 and
1440 CSS pixels with no horizontal overflow. Signed-in deployed-browser verification
confirmed a School setup tab deep link and a Reports open-section deep link, then
restored both contexts through browser Back and Forward.

Implementation commit `3989aab` was deployed by recreating only the CHH pilot
frontend from the validated image. Loopback checks for `/`, `/messages`, Reports,
Recognition and Students and public checks for `/` and `/messages` returned HTTP
200. API health returned `status=ok`, readiness returned
`database=ok,migration=current`, and all pilot services are healthy with no frontend
startup errors. Backend, PostgreSQL, the notification scheduler and messaging
production worker retained their running containers. Configuration, schema and data
were unchanged; no backup, migration, native change or APK was required. Physical
Android Back, safe-area, keyboard and real-device history verification remain for
Dom.

## 2026-08-02 mobile overlays and workspaces

The survey composer is now a bounded modal workspace with one internal scroll
region. The backdrop and target list no longer compete for vertical scrolling;
the header, visible English/Arabic Close control and actions remain fixed while
the form scrolls. The dialog exposes `role=dialog`, `aria-modal` and a labelled
title, focuses Close on opening, restores focus to Create survey on closing, and
locks background/main-page scrolling. Its height follows the existing native
visual-viewport variable and all four existing safe-area insets.

Escape and the existing `chh:native-back` event close the composer. When a text
field is focused while the native keyboard is open, the first Back dismisses the
keyboard without closing the composer; a subsequent Back closes it. The hosted
Messages route no longer renders the global site footer, so its independently
scrolling workspace cannot reveal unrelated footer content. Existing survey and
messaging URLs, role/permission checks and backend behaviour are unchanged.

Validation passed 26 focused navigation, messaging and survey presentation tests,
English/Arabic parity at 2,002 keys each, and Svelte checking with zero errors or
warnings. The affected production frontend image built successfully. Nine
containerised Playwright checks passed in English and Arabic/RTL at 390 and 768 CSS
pixels, covering one survey scroll owner, dialog bounds, visible Close, focus
restoration, Escape, keyboard-first native Back, zero horizontal overflow and the
footer-free Messages workspace. Signed-in deployed-browser verification confirmed
the labelled survey dialog and Close action and confirmed that Messages exposes no
global footer.

Implementation commit `0cdb7f8` was deployed by rebuilding and recreating only the
CHH pilot frontend. Loopback and public `/` and `/messages` checks returned HTTP
200, API health returned `status=ok`, readiness returned
`database=ok,migration=current`, and the frontend is healthy with clean startup
logs. Backend, PostgreSQL, the notification scheduler and messaging production
worker retained their running containers. Configuration, schema and data were
unchanged; no backup, migration, native change or APK was required. Physical
Android keyboard, native Back, safe-area and real-device overlay/workspace
verification remain for Dom.

## 2026-08-01 permission-aware destinations

The school-admin and teacher global destinations were checked against their
existing role and permission gates. Messages already hides its navigation item
when the membership API is unavailable and provides an explicit direct-URL state;
Surveys does the same through its school-admin availability probe. School setup,
Teach, Reports and System & compliance remain actionable under their existing role
checks. Safeguarding was the confirmed dead end: its non-sensitive availability
probe previously treated any active safeguarding grant as enough to show the menu,
including moderation or export grants that provide no landing-page action.

Safeguarding availability now returns true only when the exact active school
membership has either `messaging.safeguarding_review` or
`messaging.manage_safeguarding_permissions`. A membership with neither permission
does not receive desktop or mobile navigation; a direct URL shows a clear English
or Arabic unavailable state without restricted labels, counts or disabled actions.
Review-only access shows only Message reviews, manage-only access shows only
Permission management, and memberships with both permissions see both. A
manage-only user opening the review URL receives review-specific unavailable copy.
Mixed-role accounts select the first membership with a usable safeguarding entry
permission rather than an unrelated membership. Existing URLs and every protected
backend permission check remain unchanged; adjunct moderation, export, internal-note
export and legal-hold permissions retain their existing enforcement inside an
authorised workflow.

Validation passed all nine focused safeguarding backend tests in the rebuilt image,
seven focused frontend source tests, English/Arabic parity at 2,002 keys each,
Svelte checking with zero errors and warnings, and the affected backend and frontend
production builds. Thirty Playwright navigation and safeguarding checks passed for
no access, review-only, manage-only, full and mixed-role combinations, followed by
the focused manage-only direct-route assertion. The matrix covered platform-admin,
school-admin, teacher and mixed-role navigation plus English and Arabic/RTL at 390,
768, 1024, 1280 and 1440 CSS pixels. Signed-in deployed-browser verification
confirmed hidden navigation and the explicit no-access state in English desktop and
Arabic/RTL at 390 CSS pixels, with zero horizontal overflow and no console warnings
or errors.

Implementation commit `d47d093` was deployed by rebuilding and recreating only the
CHH pilot backend and frontend. Both services are healthy; loopback and public
frontend checks returned HTTP 200 and readiness returned
`database=ok,migration=current`. PostgreSQL, the notification scheduler and the
messaging production worker retained their running containers. Configuration,
schema and data were unchanged; no backup, migration, native change or APK was
required. Physical Android Back, safe-area and real-device compact-menu/touch
verification remain for Dom.

## 2026-08-01 School setup menu grouping

The School setup workspace now uses one ordered menu definition for desktop and
mobile. The six workflow groups are School structure (Checklist, School settings,
Branches/campuses, Academic years, Education stages & terminology, Grade/year
levels, Sections); Teaching setup (Classes & rosters, Staff & teaching assignments,
Subjects, Default subjects, Subject groups); Students (Student records, Student
Import & Export); Communication (Notices, School calendar); Behaviour & insights
(Behaviour & points, Reports, Positive recognition); and System (System &
compliance). Existing URLs, destinations, school-administrator access checks and
backend behaviour are unchanged.

The canonical Students and Student Import & Export destinations remain links from
School setup. Reports remains in global navigation, while Reports, Positive
recognition and System & compliance are labelled contextual shortcuts within the
School setup hierarchy. Behaviour & points also has a contextual Reports shortcut
beside its existing page action. Ordinary items now share one neutral type and
weight treatment, with one consistent purple active state and
`aria-current="page"`. At widths below 1024 CSS pixels the same definition renders
as six compact, keyboard-accessible group accordions; the group containing the
current tab opens automatically. English and Arabic labels and shortcut wording are
kept in parity, including RTL layout.

Validation passed ten focused navigation/menu source tests, English/Arabic parity
at 2,001 keys each, Svelte checking with zero errors and warnings, the affected
container production build, and 18 Playwright role/layout checks. The browser
matrix covered school-admin and mixed-role School setup visibility and English and
Arabic/RTL containment at 390, 768, 1024, 1280 and 1440 CSS pixels. It also verified
the six groups and workflow order, preserved URLs, three labelled contextual
shortcuts, exactly one active item, mobile accordion behaviour and zero horizontal
overflow. Platform-admin and teacher visibility remained covered by the shared
global-navigation checks. Signed-in deployed-browser verification confirmed the
same six-group English desktop hierarchy, exactly one current item, the three
shortcut destinations, the automatically opened current mobile group, and zero
overflow in English and Arabic/RTL at 390 CSS pixels.

Implementation commit `00adc26` was deployed by rebuilding and recreating only the
CHH pilot frontend. Loopback and public frontend checks returned HTTP 200, readiness
returned `database=ok,migration=current`, and the frontend is healthy with no recent
errors. Backend, PostgreSQL, the notification scheduler, the messaging production
worker, FHH, configuration, schema and data were unchanged. No database backup,
migration, native change or APK was required. Physical Android Back, safe-area and
real-device accordion/touch verification remain for Dom.

## 2026-08-01 student lookup and list-state slice

The Students workspace now loads a bounded 25-record page instead of the entire
school roster. Administrators can move between pages with labelled Previous/Next
controls and a visible result range. The school-scoped API supports opt-in `page`
and `page_size` parameters with a maximum page size of 100; callers that omit both
parameters retain the existing array response, preserving the Reports workspace and
other established consumers.

Student search now treats each whitespace-separated part as a required term that
may match first name, last name, preferred name or external reference. This allows
complete names such as `Adnan Al Balushi` to match across stored name fields without
changing tenancy or school-administrator permission checks. Search input is capped
at 100 characters.

Search, class-section filter and page state are stored in the existing
`/school/students` query string. Opening a student adds the existing `student`
parameter without removing list state; returning to the list restores the same
results. Reloading a student deep link fetches that school-scoped student directly,
so it remains valid when the record is not on the currently loaded page. Invalid or
archived class-section parameters are cleared instead of being sent to the API.
English and Arabic copy covers the persistence note, result range and accessible
pagination labels.

Validation passed all 32 student/enrolment backend tests, eight focused student
administration presentation tests, English/Arabic parity at 1,991 keys each, Svelte
checking with zero errors and warnings, the source and container frontend production
builds, and three focused tests inside the rebuilt backend image. Signed-in deployed
browser checks confirmed complete-name search, URL-backed filter and page reloads,
student-detail reload/return, exactly 25 visible records per full page, and no
horizontal overflow in English and Arabic/RTL at 390, 768, 1024, 1280 and 1440 CSS
pixels. Browser console checks returned no warnings or errors.

Implementation commit `50c04f1` was deployed by rebuilding and recreating only the
CHH pilot backend and frontend. Loopback and public frontend checks returned HTTP
200, readiness returned `database=ok,migration=current`, and both services are
healthy with clean startup logs. PostgreSQL, the notification scheduler and the
messaging production worker retained their running containers. Configuration,
schema and data were unchanged; no backup, migration, native change or APK was
required. Physical Android Back, safe-area and real-device touch/menu verification
remain for Dom.

## 2026-08-01 global navigation consistency

The CHH pilot now builds desktop and compact global navigation from one ordered,
role-filtered definition: Family, Platform admin, School setup, Teach, Messages,
Surveys, Reports, System & compliance, Safeguarding, then Logout. Existing URLs,
membership availability checks and permission visibility are unchanged. The four
ambiguous labels have matching English and Arabic wording: **Platform admin**,
**School setup**, **Reports** and **System & compliance**.

Every recognised workspace route now exposes one visible `aria-current="page"`
state. Reports, Surveys, Safeguarding and the System & compliance routes, including
Recognition, Governance and Operations, take precedence over the general School
setup route. Current links use the shared purple active treatment and retain a
visible keyboard-focus outline. The horizontal navigation now starts at the `xl`
breakpoint; 1024px and narrower layouts use the bounded compact menu instead of
compressing the brand and links.

Focused validation passed four route/order/translation tests, English/Arabic parity
at 1,986 keys each, Svelte checking with zero errors and warnings, the local and
container production builds, and 14 Playwright role/layout checks. Those browser
checks covered platform-admin, school-admin, teacher and mixed-role visibility plus
English and Arabic/RTL containment at 390, 768, 1024, 1280 and 1440 CSS pixels.
Signed-in deployed-browser verification confirmed the new labels and order, exactly
one active item on School setup, Reports, Surveys, System & compliance and
Safeguarding, and a non-overlapping 1024px compact header with zero horizontal
overflow.

Implementation commit `46e2921` was deployed by rebuilding and recreating only the
CHH pilot frontend. Loopback and public frontend checks returned HTTP 200, API health
returned `status=ok`, and the frontend is healthy with clean startup logs. Backend,
PostgreSQL, the notification scheduler, the messaging production worker, FHH,
configuration, schema and data were unchanged. No database backup, migration,
native change or APK was required. Physical Android Back, safe-area and real-device
menu verification remain for Dom.

## 2026-08-01 recognition review and configuration lifecycle

Physical-test investigation found that the apparent one-point threshold failure was
caused by configuration selection and timing, not shortlist filtering. All three
retained drafts freeze `minimum_positive_points = 1`; the current configuration was
later edited to 2. Every retained candidate meets the minimum in its own immutable
review snapshot. The staff page now shows the selected configuration's scope,
inclusive review period, minimum positive points, target size and safeguard state
beside **Generate shortlist**, and repeats the frozen minimum, scope and target on
every review card. Configuration option labels include these criteria so similarly
named entries remain distinguishable.

Generation now serialises on the selected configuration and returns the existing
unconfirmed draft for the same configuration and exact inclusive period instead of
creating another. The frontend opens that draft and de-duplicates it locally. Staff
can explicitly open any review; draft, archived, confirmed and revoked/corrected
cards have separate treatments and the selected review remains highlighted. An
administrator may discard only an unconfirmed draft, with confirmation and a
3–500-character reason. This changes its state to archived, removes it from the
default list and records `recognition.review.archived`; archived history remains
available separately. Confirmed awards cannot be discarded and remain
correction/revocation-only.

Configurations now have explicit edit, deactivate and archive actions. Inactive and
archived configurations are excluded from generation server-side and in the UI.
Archiving requires confirmation and a reason, preserves every existing review
snapshot, and records `recognition.config.archived`. Archived history is available
separately and an archived scope may receive a replacement configuration. Creating
an active configuration with a case-, spacing- or punctuation-equivalent active
name requires an explicit warning confirmation.

Alembic head is `a0b1c2d3e4f5`. The migration adds nullable archive actor/time/reason
fields and lifecycle checks to recognition configurations and reviews, permits
`archived` only for never-confirmed reviews, and replaces the configuration scope
constraint with a partial unique index covering non-archived configurations. It
does not rewrite existing configurations, reviews, candidates, behaviour events or
audit records. Downgrade is intended only before archive/replacement use; after
such use it fails closed on the restored constraints instead of deleting history.

Migration safety note: the first disposable rehearsal overrode `DATABASE_URL`, but
the compose service retained its separate `MIGRATION_DATABASE_URL`; the additive
upgrade therefore reached the pilot before the planned fresh differential. The
migration guard refused the attempted downgrade. No application service was using
the new fields and the migration rewrote no rows. Verified same-day pre-change
recovery points at `f9a0b1c2d3e4` remain available as local
`20260728-182651F_20260801-134906D` and off-host
`20260725-221530F_20260801-134918D`. Immediate post-upgrade AES-256-CBC
differentials completed as local `20260728-182651F_20260801-144429D` and off-host
`20260725-221530F_20260801-144438D`; both repositories and WAL passed `check`.
The corrected disposable run explicitly isolated both database variables and
passed full upgrade, downgrade to `f9a0b1c2d3e4`, re-upgrade and model compilation.

Validation passed 14 recognition/readiness tests in the rebuilt backend image,
seven frontend management/accessibility/privacy checks, parity at 1,986 English
and Arabic keys, Svelte check with zero errors and warnings, and local plus image
production builds. Signed-in deployed-browser verification confirmed the selected
configuration displays minimum 2 while all three retained cards display their
frozen minimum 1; repeat generation opened an existing draft, focused the decision
section and left the database review count at three. Keyboard Enter opened the
correct older review, exactly one selected card was shown, reasoned discard controls
stayed disabled without a reason, and Arabic switched the page to `lang=ar` and
`dir=rtl` with matching open/discard actions. Only backend and frontend were
recreated; PostgreSQL and both workers retained their lifecycles. All five services
are healthy and readiness reports `database=ok,migration=current`.

## 2026-08-01 recognition eligibility safeguard and review actions

The CHH pilot recognition workflow now supports a school-configurable, disabled-by-
default staff eligibility safeguard. When enabled, it counts only unreversed
needs-work events inside the same inclusive school-local review period and marks a
student **Not eligible under current criteria** only when the count is greater than
the configured maximum. The school may restrict counting to selected active
needs-work categories; selecting none counts all such categories. Positive points
and positive event count remain the only shortlist and rank inputs.

Administrators can see the frozen counted total and category-count evidence on the
staff review, but no event note is copied. An override requires a reason and is
audited separately from the automatic safeguard exclusion. Certificates and the
existing positive award output contain no needs-work totals, categories, evidence
or override data. There is still no public recognition endpoint or FHH/notification
publication path.

Awaiting-decision cards now include a clear **Review shortlist** action, native
keyboard activation, pointer/hover/focus treatment, selected-card styling, and
scroll/focus the matching decision section. Repeat activation focuses the existing
review without opening a duplicate. Confirmed and revoked/corrected cards use
separate readable treatments and view actions.

Alembic head is `f9a0b1c2d3e4`. The additive migration adds two defaulted settings
columns, one optional category association table, and defaulted candidate snapshot
and audited-override columns. Existing recognition configuration remains disabled
for the safeguard and no behaviour, student, enrolment, certificate or audit row
was rewritten. A disposable PostgreSQL database passed full upgrade, one-revision
downgrade, re-upgrade and application smoke. The backend readiness revision was
updated to the same head.

Fresh pre-migration AES-256-CBC differential backups and repository/WAL/readiness
checks passed:

- local: `20260728-182651F_20260801-134906D`;
- off-host: `20260725-221530F_20260801-134918D`;
- repository bytes: `7,338,944` in each repository.

Focused validation passed 11 recognition/readiness tests inside the rebuilt backend
image, five frontend recognition presentation/accessibility/privacy tests, i18n
parity at 1,959 English and 1,959 Arabic keys, Svelte check with zero errors and
zero warnings, and local plus host production frontend builds. Only the CHH backend
and frontend were rebuilt/recreated. PostgreSQL and both workers retained their
lifecycles; all five containers are healthy and readiness reports
`database=ok,migration=current`. FHH, native code and Android/APK artefacts were
untouched.

## 2026-07-31 positive student recognition

The CHH pilot now has an administrator-only Positive recognition area linked from
Administration. It supports audited Star of the Week configuration, transparent
positive-evidence shortlist review, recorded candidate exclusion, explicit recipient
confirmation, history-preserving revocation/correction and a browser-printable
English/Arabic certificate. It has no public display endpoint and sends no parent,
FHH or push notification.

Alembic head is `e8f9a0b1c2d3`. The migration adds four initially empty recognition
tables plus school/scope/period constraints and indexes; existing behaviour events,
students, enrolments and audit rows are unchanged. Pre-migration encrypted
differentials are `20260728-182651F_20260731-172632D` locally and
`20260725-221530F_20260731-172637D` off-host. Upgrade/downgrade/re-upgrade passed on
a disposable PostgreSQL database.

## 2026-07-31 MIS import history and exports

The CHH pilot school administration Students area now provides school-scoped,
paginated student import history and stored row outcomes; streamed UTF-8 reports
for all rows, conflicts, errors and committed changes; and current active
student, guardian-contact, class-enrolment and populated annual-update exports.
Only school administrators may use these routes. Result tables omit guardian
contact values, while correction reports and authorised contact exports contain
only the school-held fields required for their stated purpose. Every CSV applies
spreadsheet-formula neutralisation and every history/report/export access is
audited without contact values. The importer reverses only that exact export
escape so safe stable IDs and international `+` phone values can be re-imported.

Alembic revision `e7f8a9b0c3d4` expands only the import status constraint so
future decoding/parsing/planning failures can be retained as failed history.
There was no data rewrite. The migration passed an isolated PostgreSQL
upgrade/downgrade/re-upgrade and application smoke. Pre-migration encrypted
differentials are `20260728-182651F_20260731-075648D` locally and
`20260725-221530F_20260731-075655D` off-host.

Validation passed 55 focused student-import tests and four migration-guard tests
against both edited source and the rebuilt image. Svelte reported zero
errors/warnings, English/Arabic parity passed at 1,796 keys each, and the
production frontend build passed. Only the CHH backend and frontend were
rebuilt/recreated. Public frontend and readiness returned HTTP 200 with
`database=ok` and `migration=current`; affected-service logs contained no
errors. PostgreSQL and both workers retained their service lifecycle. FHH,
native code and Android/APK artefacts were untouched.

## 2026-07-29 authentication admission control

CHH pilot now treats Google OAuth and magic links as identity proof, not
authorisation. A normal browser or Android session requires an active platform
administrator, active school administrator/teacher membership at a non-suspended
school, or active guardian link to an active student at a non-suspended school.
Access-token resolution and refresh repeat that check. Unknown bare identities are
not created and receive the privacy-safe rejection
`This account is not authorised for Class Hero Hub.`

Valid staff and guardian invitations remain explicit onboarding authorities.
OAuth/native/magic authentication entered from `/invite/<token>` or
`/join?c=<code>` may create an exact-invite-scoped pending session. Only the invite
hash, kind and expiry are stored in `user_refresh_sessions`; the raw code is not
stored. Ordinary authenticated routes reject that pending session, which is promoted
only after the matching membership or guardian link commits. This preserves pending
deep links and Android account-picker recovery without opening general admission.
Alembic revision `a4e5f6b7c8d9` adds only the three nullable pending-admission columns
and their completeness check.

Before inventory or deletion, fresh AES-256-CBC pgBackRest differentials completed
and passed repository, WAL and application-readiness checks at
`2026-07-29T00:05:37+04:00`:

- local repository: `20260728-182651F_20260728-200445D`;
- off-host SFTP repository: `20260725-221530F_20260728-200511D`;
- repository bytes: `7,156,672` in each repository.

The first backup attempt failed closed because files from the prior manual full
backup were owned by root. Ownership was corrected only inside the dedicated
pgBackRest repository to PostgreSQL uid/gid `999:999`, zero root-owned repository
paths were verified, and both fresh differentials then completed. No database row
was changed during that repair.

The dry-run inventory found four unauthorised identities: three planned removals and
one preserved documented S9 API-smoke identity. The guarded transaction locked and
rechecked all candidates, removed the required
`google-admin@familyherohub.com`, `test@familyherohub.com` and
`parent@familyherohub.com` users plus their five refresh sessions, and preserved
`s9.guardian.qa@myeduzone.org` inactive because append-only audit evidence references
it. Memberships (`77`), guardian links (`3`), platform admins (`2`), schools (`1`),
students (`502`), push registrations (`2`) and magic-link rows (`14`) were unchanged;
post-checks found zero orphaned refresh sessions or push registrations. The final
mode-600 report is:

- `/opt/apps/class_hero_hub/tmp/chh-unauthorised-account-report-2026-07-28.csv`
- SHA-256:
  `9499769f3d122002e326754273a3b1f97ebfe3a5964a3272a9e45d40f16c086a`

Repeatable inventory is dry-run by default:

```bash
docker compose run --rm --no-deps \
  -v /opt/apps/class_hero_hub:/repo -w /repo/backend backend \
  python scripts/chh_unauthorised_accounts.py \
  --report /repo/tmp/chh-unauthorised-accounts.csv
```

Deletion additionally requires the existing dry-run report, explicit confirmation
and `--pilot-target class.familyherohub.com`; it fails closed if the candidate set
changed or any user gained an entitlement. It is not an automatic or scheduled
delete.

Validation passed 127 focused authentication, admission cleanup, guardian,
platform-admin, security, migration-guard and operational-health tests. The built
backend image independently passed the 56 most directly affected auth/admission
tests. Svelte check reported zero errors/warnings, the frontend production build
passed, and a disposable PostgreSQL database passed full upgrade, one-revision
downgrade, re-upgrade and application smoke. Public pilot checks returned HTTP 200
for the frontend and readiness (`database=ok`, `migration=current`). A live
enumeration-safe magic-link request for a removed identity returned the generic
response while creating neither a user nor magic-link row.

Only the CHH pilot backend and frontend were rebuilt/recreated. PostgreSQL,
notification scheduler and messaging worker retained their uptime. The native
Google bridge now carries the exact pending invite/deep-link return path, so the
updated web assets were synchronised into Capacitor and a fresh development APK
passed `testDebugUnitTest`, `lintDebug` and `assembleDebug`:

- file: `class-hero-hub-admission-control-dev-20260729.apk`;
- package/version: `com.classherohub.app`, code `10`, name
  `1.8-surveys-polls`;
- size/SHA-256: `96,334,794` bytes,
  `6f98268fb43db1c0c970d538a82d64dd4fb8f261919c39c15c97abfd3af5fd6b`;
- server: `/opt/apps/class_hero_hub/tmp/`;
- Windows delivery: `G:\My Drive\CHH\Remote\`.

The server and Windows copies have identical SHA-256. CHH production and all FHH
environments were unchanged.

## 2026-07-28 AUTH-001 revocable sessions

CHH development/pilot now uses revocable, per-browser/device staff sessions. Access
JWTs last 15 minutes. A rotating refresh session has a 30-day idle lifetime and a
180-day absolute lifetime; only HMAC hashes of the current and immediately previous
refresh credentials and safe device metadata are stored. A 10-second previous-token
grace handles concurrent renewal, after which reuse revokes that session chain.
Logout revokes only the current session; `POST /api/auth/logout-all` revokes every
session for the user. Disabled or deleted users cannot access or refresh.

The browser stores access and refresh credentials only in Secure, HttpOnly,
SameSite=Lax cookies. Android stores both in encrypted native storage and silently
renews on startup and one eligible HTTP 401. Google login, account switching and
pending authenticated routes retain their existing user flow. Invitation codes,
school memberships and staff identities were not changed.

Alembic revision `a001c7e9d4f2` adds `user_auth_sessions` without rewriting any user,
school or membership row. Existing legacy access JWTs are accepted only through
`2026-08-04T23:59:59Z`; updated clients exchange them silently for a revocable
session, while older clients require one ordinary Google sign-in after that date.
The pre-migration pgBackRest full backup is `20260728-182651F`.

Focused validation passed 39 backend authentication, CSRF, QA-login and operational
health tests; Svelte check reported zero errors/warnings; the frontend production
build and three push/deep-link preservation tests passed. A disposable PostgreSQL
database passed clean upgrade, last-revision downgrade and re-upgrade. Fresh
`testDebugUnitTest`, `lintDebug` and `assembleDebug` Android gates passed.

Only the development backend and frontend were rebuilt/recreated. PostgreSQL, the
notification scheduler and messaging worker retained their prior uptime. Public
frontend and readiness returned HTTP 200, the database and migration checks reported
`ok`/`current`, and recent affected-service logs contained no application errors.
Production was not changed.

Development APK:

- File: `class-hero-hub-auth001-revocable-sessions-dev-20260728.apk`
- Package/version: `com.classherohub.app`, code `10`, name
  `1.8-surveys-polls`
- Size/SHA-256: `96,337,874` bytes,
  `8c842eaf32064b83cf1adaf26c96b3b329013e5b3ccfcc900726c3d27eb6eb0d`
- Server: `/opt/apps/class_hero_hub/tmp/`
- Windows delivery: `G:\My Drive\CHH\Remote\`

## 2026-07-27 production School Chats, surveys and destination gating

Production School Chats and linked-parent surveys are enabled with a dedicated
production messaging-assertion secret. CHH selects the assertion verifier from each
link's stored `integration_environment`: development uses
`FHH_MESSAGING_ASSERTION_SECRET`, while production additionally requires
`FHH_PRODUCTION_MESSAGING_ENABLED=true` and
`FHH_PRODUCTION_MESSAGING_ASSERTION_SECRET`. The production value matches only FHH
production's `CHH_MESSAGING_ASSERTION_SECRET`; it is distinct from the development
assertion secret and both integration service bearers. Values remain untracked and
service-scoped. The validated SHA-256 prefixes were `b3f93946a13c` for production
and `032a0a6e7b01` for development.

The notification scheduler now refuses only protected `school_chat` and `survey`
destinations when their matching runtime assertion configuration is unavailable.
It cancels undispatched rows with
`school_chat_destination_unavailable` or `survey_destination_unavailable` before
any bridge call. Points, homework, notice, calendar and update categories retain
their existing eligibility and dispatch paths.

Pre-change encrypted pgBackRest differentials are
`20260725-221505F_20260727-174315D` locally and
`20260725-221530F_20260727-174320D` off-host. Both repositories, WAL and readiness
passed the documented check. Mode-600 rollback copies are
`.env.pre-runtime-parity-20260727-2147`,
`.env.push.pre-runtime-parity-20260727-2147`, and
`.env.integration.production.pre-runtime-parity-20260727-2147`. The pre-change
application image tags are `class_hero_hub-backend:rollback-0708fa8` and
`class_hero_hub-notification_scheduler:rollback-0708fa8`. Rollback restores those
files, reverts the two source commits and recreates only `backend` and
`notification_scheduler`; it must not replay historical dead or cancelled rows.

Focused candidate and deployed-image validation passed 79 tests with the one
previously documented, unrelated policy-reconciliation test deselected. A fresh
staff-to-family chat row was accepted by the production bridge, ingested once by
FHH, produced one delivery and received one Firebase provider reference. A fresh
survey reminder produced one accepted production delivery for the eligible
installation; an already-ineligible linked recipient was safely cancelled by FHH.
Dom physically confirmed receipt of the production chat and survey notifications
and that each tap opened its correct protected School Chat or survey destination.
Production inbox, conversation/history, send, delivery/read acknowledgement,
photo upload/thumbnail/full retrieval, voice upload/playback, survey list/open and
survey submission all passed through FHH. Queue and worker health remained normal.
Only CHH `backend` and `notification_scheduler` were rebuilt/recreated. There was no
schema, frontend, native or APK change.

## 2026-07-27 environment-bound production notification validation

The first real production FHH invite was consumed successfully. FHH production has
exactly one active school connection for the linked child, CHH has exactly one link
created from that production invite, and the production APK loaded the protected
dashboard through FHH with CHH HTTP 200. CHH also retains the older development link
for the same school student; those two authority rows are now explicitly labelled
`development` and `production`.

Alembic revision `f8a9b0c1d2e3` adds the required `integration_environment` to
`fhh_links`. Redemption records the environment selected by the matched,
source-bound service credential. Notification dispatch uses that field to select
the matching development or production URL, bearer, HMAC secret and timeout from
one worker without copying credentials between environments. Both bridge URLs are
literal private-mesh endpoints with their existing exact path, allowlist, timestamp,
nonce/replay and redirect protections.

The pre-migration CHH recovery points are encrypted local differential
`20260725-221505F_20260727-105713D` and off-host differential
`20260725-221530F_20260727-105717D`; pgBackRest verified both repositories, WAL and
application readiness. The production bridge overlay rollback copy is
`.env.push.production.pre-environment-routing-20260727-1502` (SHA-256
`87b570aba3d8e8575c0291516d653702df93558fa71c9a8c164dc0a3834922f4`).
Rollback restores that file, downgrades one Alembic revision, reverts the matching
source commit, and recreates only `backend` and `notification_scheduler`.

A controlled update produced one row per environment and both reached the correct
bridge. Production FHH ingested its update once but cancelled it with
`no_active_devices`: the new connection's guardian messaging identity roster was
missing, so the event had zero eligible recipients. That event was not retried.
After a fresh verified FHH production backup and normal one-row roster
reconciliation, the connection has one active identity link and one completed
lifecycle event.

A fresh controlled Immediate `+1` positive points event then created exactly one CHH
row for each environment. Both were bridge-accepted. Production FHH has exactly one
matching points event, one recipient, one installation and one delivery; its worker
recorded Firebase provider acceptance and one opaque provider reference with no
error. Recent CHH/FHH actionable notification backlog is zero and all relevant
worker heartbeats are healthy. The notification appeared exactly once on the
registered production Android installation. Tapping it opened the linked child's
protected school Points destination, completing physical end-to-end acceptance.

The additive migration passed upgrade/downgrade/re-upgrade on disposable PostgreSQL.
Focused integration, security and dispatch validation passed 77 relevant tests; the
unchanged policy-reconciliation assertion remains the one previously documented
failure. Only CHH `backend` and `notification_scheduler` were rebuilt/recreated.
There was no frontend/native change or APK rebuild.

## 2026-07-27 production FHH school-link and notification enablement

The CHH pilot now accepts the FHH production server on the exact private source
`10.250.50.2/32`. The backend loads the untracked, mode-600
`.env.integration.production` after `.env`; its dedicated production service bearer
is separate from the existing development bearer and messaging assertion secret.
CHH binds the development pair to `10.250.50.1/32` and the production bearer to
`10.250.50.2/32`, so enabling production does not replace or authorize reuse of the
development credential. Production FHH has no messaging assertion secret because
production School Chats remain disabled.
FHH production calls `https://class.familyherohub.com` with that hostname mapped to
`10.250.50.5` inside only its backend and lifecycle-worker containers. TLS hostname
and certificate verification therefore remain intact while school-link and protected
school-data traffic stays on the private mesh. FHH production school messaging
remains disabled.

The notification scheduler continues to load CHH's existing `.env.push`, then the
untracked production bridge overlay `.env.push.production`. The overlay selects only
`http://10.250.50.2:8000/api/integrations/chh/school-message-notifications`, which
also appears exactly in `FHH_NOTIFICATION_APPROVED_PRIVATE_HTTP_ENDPOINTS`, and uses
the dedicated production bearer/HMAC pair and five-second timeout. The former
inactive overlay key names `FHH_NOTIFICATION_API_URL` and
`FHH_NOTIFICATION_HTTP_TIMEOUT_SECONDS` were corrected to the actual runtime names
`FHH_NOTIFICATION_BRIDGE_URL` and `FHH_NOTIFICATION_TIMEOUT_SECONDS`. Redirects,
timestamp skew, nonce replay protection, canonical body signing and FHH's exact
`10.250.50.5/32` source allowlist remain enforced.

Pre-change recovery evidence is the fresh encrypted local/off-host CHH differential
backup pair `20260725-221505F_20260727-100853D` and
`20260725-221530F_20260727-100857D`; the subsequent pgBackRest health check verified
both repositories, WAL archiving and application readiness. Runtime configuration
rollback copies are `.env.pre-production-school-link-20260727-1012` and
`.env.push.production.pre-production-school-link-20260727-1012`. To roll back,
restore those exact mode-600 files, revert the matching Compose/documentation commit,
and recreate only `backend` and `notification_scheduler`; do not reset notification
rows or retry dead rows.

Candidate and restarted production profiles passed fail-fast validation. A live
non-ingesting school-link probe arrived from `10.250.50.2` and returned 404 for a
deliberately nonexistent code, proving private routing, bearer authentication and
source allowlisting. A live signed empty notification probe arrived at FHH from
`10.250.50.5` and returned the expected authenticated 422. It created no FHH event
or delivery, and CHH link/outbox aggregates were unchanged. The CHH backend and
notification scheduler alone were recreated and are healthy; PostgreSQL, frontend,
Caddy and the production worker retained their uptime.

Focused CHH integration/security validation passed 52 tests. A wider unchanged
notification file passed 60 tests and retained one unrelated policy-reconciliation
failure (`cancelled` versus the test's expected `pending`); no code in that path
changed and the live queue aggregate remained unchanged.

An initial single-slot configuration briefly replaced the development service bearer
and caused FHH development requests from `10.250.50.1` to return 401. The final
source-bound dual-credential implementation corrected that regression. Live
non-ingesting probes from both FHH environments now reach the same CHH route using
different bearers and exact `/32` allowlists; neither bearer is accepted from the
other environment's source. The affected development FHH connection was verified
against CHH with its retained link credential, returned the complete dashboard
contract, and was restored to active/synchronised state without changing its three
active guardian identities or completed lifecycle events.

The earlier blocker was resolved by creating an FHH invite rather than the separate
guardian invite. The production APK consumed it, loaded protected school data and
the controlled points notification reached Firebase once. It then appeared once on
the registered production Android installation and its tap opened the protected
school Points destination. There was no frontend/native or APK change.

## 2026-07-27 CHH-to-FHH private bridge routing restoration

CHH development/pilot now sends school-notification events to the exact FHH
development mesh endpoint:
`http://10.250.50.1:8000/api/integrations/chh/school-message-notifications`.
The scheduler consumes this target from `.env.push`; the separate production
reciprocal configuration uses the corresponding `10.250.50.2` endpoint.
Each HTTP endpoint must also appear exactly in
`FHH_NOTIFICATION_APPROVED_PRIVATE_HTTP_ENDPOINTS`. Public HTTP, unapproved private
HTTP, hostnames, credentials, query strings, fragments, alternate routes and
redirects remain rejected. Bearer/HMAC authentication, canonical signing, timestamp
skew, UUID nonce/replay protection, the FHH `10.250.50.5/32` source allowlist and
the five-second timeout are unchanged.

The regression was caused by the former public HTTPS target: FHH observed CHH's
public egress source instead of mesh source `10.250.50.5` and rejected these ten
rows with `fhh_bridge_http_403`:

| Outbox | Event | Category | 2026-07-27 disposition |
|---:|---|---|---|
| 56 | `439b2030-216a-40d6-ac3f-891274164f01` | points | Remains dead; revalidate before any future retry |
| 57 | `8ed07bb2-7e0e-4e19-8243-8587c21d7999` | chat | Remains dead; revalidate before any future retry |
| 58 | `768a7908-5fe4-4bf3-9b1f-eeab095d28f0` | update | Remains dead; revalidate before any future retry |
| 59 | `6bd57a7c-20a5-4b02-b2f6-1eba0e834442` | homework | Remains dead; revalidate before any future retry |
| 61 | `20526112-be24-4689-9a6b-61bb68b8efd8` | chat | Remains dead; revalidate before any future retry |
| 64 | `1d6ca7ce-313e-44cf-ae72-aba365697e59` | chat | Remains dead; revalidate before any future retry |
| 65 | `3e5551e8-d60d-40a9-b070-9ba8122d7dcb` | homework | Selectively retried; provider accepted |
| 66 | `dff16e2a-0aa1-4420-8985-41e6b97fec3b` | chat | Remains dead; revalidate before any future retry |
| 67 | `22e5a8ed-be7d-4804-af70-229876c953a6` | chat | Remains dead; revalidate before any future retry |
| 68 | `44531a99-e5c4-4a47-a9cf-d99c8107a4a6` | update | Selectively retried; provider accepted |

The two audited retries were performed only after current eligibility was checked.
Both were ingested once by FHH and accepted by Firebase for both active development
installations. A fresh Immediate points event
`a14e6382-68a5-4480-be67-f1a9124a7127` (CHH outbox 69) followed the normal creation
path and reached the same provider-accepted state without duplication. Do not
bulk-retry the remaining rows; use the audited operator action and revalidate each
row immediately before an explicitly approved selective retry.

Only the notification scheduler was rebuilt/recreated. There was no schema,
migration, Android/native or APK change.

## OPS-HEALTH-001 operational readiness

`GET /api/health` is the lightweight process-liveness contract and remains
compatible with existing consumers: HTTP 200 and `{"status":"ok"}` without a
database query. `GET /api/health/ready` is the dependency-aware readiness contract. It
uses a separate one-connection pool with two-second connection, pool and statement
limits, checks `SELECT 1`, and requires the database Alembic revision to equal the
shipped head (`e7f8a9b0c1d2`). Database failure returns HTTP 503 `unavailable`;
revision drift returns HTTP 503 `degraded`. Responses contain no exception,
connection or credential details. Update `EXPECTED_MIGRATION_REVISION` in
`backend/app/operational_health.py` whenever a later migration becomes head.

The platform-admin-only `GET /api/platform/operations/status` projection exposes
aggregate operational state:

- production and notification worker heartbeat ages, stale after 120 seconds;
- operations-job and notification queue state counts, dead-letter presence and
  ready backlog age, stale after 300 seconds;
- the existing pgBackRest health-marker backup age (30-hour limit) and marker age
  (26-hour limit);
- existing scheduled-job marker failures and staleness (30 hours for normal jobs,
  eight days for weekly jobs and 35 days for restore rehearsals);
- data-volume disk use, warning at 80% and critical at 90%; and
- current/expected migration revisions and low-cardinality alert codes.

Only `tmp/backup-status` and `tmp/scheduled-status` are mounted read-only into the
backend. Queue payloads, messages, school/family identifiers, backup labels and
secrets are not returned. Docker health checks use readiness for the backend,
heartbeat freshness for enabled workers, and the static root for the frontend.
The pgBackRest health job now verifies `/api/health/ready`; `/api/health` must not be
changed into a dependency check. This pilot has status surfacing but no external
paging or alert delivery.

## CHH-DEPLOY-001 production security profile

The public pilot at `https://class.familyherohub.com` runs with the production
runtime security profile even though it remains the current pilot host. The required
non-secret environment settings are:

```dotenv
APP_ENV=production
DEV_AUTH_ENABLED=false
QA_LOGIN_ENABLED=false
QA_CHILD_LOGIN_ENABLED=false
CORS_ORIGINS=https://class.familyherohub.com,https://localhost
FHH_NOTIFICATION_BRIDGE_URL=http://10.250.50.1:8000/api/integrations/chh/school-message-notifications
FHH_NOTIFICATION_APPROVED_PRIVATE_HTTP_ENDPOINTS=http://10.250.50.1:8000/api/integrations/chh/school-message-notifications
```

`https://localhost` is the exact origin of the bundled Capacitor Android WebView.
The shell calls the public CHH API with a bearer token and therefore requires CORS;
HTTP localhost, development ports, wildcards and other origins are not permitted in
production. Production startup also requires non-placeholder JWT, session and Google
OAuth secrets, HTTPS public/API/callback URLs, and a bounded trusted-proxy allowlist.
It fails closed if development/QA authentication is enabled or the CORS set differs.
The notification scheduler loads `.env.push` after `.env`; any bridge URL override in
that file is environment-specific. The development/pilot target is the exact
WireGuard endpoint shown above; the production counterpart is
`http://10.250.50.2:8000/api/integrations/chh/school-message-notifications` and must
appear only in production configuration.

Plain HTTP is accepted only when the complete URL is also present in
`FHH_NOTIFICATION_APPROVED_PRIVATE_HTTP_ENDPOINTS`, uses an eligible literal private
IP address and has the exact notification ingestion path. Public HTTP, hostnames,
credentials, parameters, query strings, fragments and alternate routes fail startup
validation. Redirects are never followed and every 3xx response is terminal. HTTPS
targets remain valid, but the CHH-to-FHH notification bridge intentionally uses the
private mesh so FHH sees the strictly allowlisted CHH source `10.250.50.5`.

The public development HTTPS target caused the July 2026 regression: FHH observed
CHH's public egress address instead of `10.250.50.5` and rejected ten outbox rows with
`fhh_bridge_http_403`. The verified read-only evidence and exact candidate row
identifiers are in
`tmp/chh-fhh-push-notification-readonly-investigation-2026-07-27.md`. Recovery must
use the audited operator retry, revalidate eligibility immediately, start with one
homework row and one update row, and expand only after end-to-end provider and device
confirmation. Never bulk-retry unrelated dead rows.

This routing correction is server-side only. It requires rebuilding/recreating the
notification scheduler that consumes `.env.push`; it does not require an Android
change or APK rebuild.

The tracked `Caddyfile.example` is the CHH baseline for the live CHH site block. It
adds HSTS, MIME-sniffing protection, frame denial, strict-origin referrer handling and
a conservative permissions policy while preserving automatic HTTP-to-HTTPS redirect.
A strict Content-Security-Policy is intentionally deferred until the current Svelte
build, Google authentication, protected images/downloads and Capacitor shell have been
tested against a candidate policy.

For deployment, back up the live `.env` and `/etc/caddy/Caddyfile`, validate the
candidate Caddy configuration, recreate only CHH services that consume `.env`, and
reload Caddy only after validation succeeds. Live secrets remain outside Git.

## S26o Messaging v1 production hardening

Messaging Slice 13 is deployed to CHH development. United International School has
an explicit versioned System Owner record for Dominique Brown; first-admin bootstrap,
owner-only transfer and platform recovery are audited. School-scoped versioned
retention, legal holds, verified archive custody, asynchronous verified evidence
exports, durable leased operations jobs, reason-audited replay/cancel, low-cardinality
metrics and a protected school/platform operations projection are active.

- Database revision: `f0a1b2c3d4e6`. The migration round-tripped on fresh and
  restored disposable PostgreSQL databases and both restored apps returned healthy.
- Pre-change custom dump:
  `backups/slice13/chh-pre-slice13-20260721.dump`, 1,059,687 bytes, SHA-256
  `b6d357a943c941c80d8d76a8447ada00eb0fb8a0795793ea33f3bae3f85efe1e`.
  Full pgBackRest label: `20260721-062749F`.
- Protected media/archive/export snapshot:
  `backups/slice13/chh-protected-media-slice13-20260721.tar`, 2,068,480 bytes,
  SHA-256 `b9cdddee2284e8dc2f3b41ed965ace02e6c78c146c2689a633e05cd7147fcd98`.
  A disposable restore verified 20 files / 2,032,388 bytes by size and SHA-256.
- Default pilot policy retains messages, photo/voice and receipts for 2,557 days;
  safeguard/export audit metadata for 3,650 days; notifications for 365 days; and
  temporary export artifacts for 30 minutes. Media becomes archive-eligible at 365
  days and hot deletion occurs only after verified copy. These are technical
  defaults pending school policy/legal approval.
- The live-development retention preview completed successfully with zero eligible
  recent records. The operations projection reported no dead jobs/notifications,
  fresh worker heartbeat, 2.5% database-pool use, current backup marker and 76.09%
  archive-volume use (below the 80% alert threshold).
- Representative scale: 1,000 students, 2,000 guardians, 75 staff, 6,000
  conversations, 120,000 messages, 48,000 receipts, 12,000 media rows and 6,000
  notification jobs. All bounded query p95s were below 41 ms. See
  `docs/testing/MESSAGING_SCALE_RESULTS_2026-07-21.md`.
- Deployed-image validation passed 459 backend tests with 2 skips; Svelte check and
  production web build passed. Public/loopback health, ordinary messaging,
  governance, operations and safeguarding routes passed their live boundaries. The
  dedicated production worker and notification scheduler are running; PostgreSQL
  was not restarted or recreated.
- Source tag after final verification:
  `chh-s26o-messaging-production-hardening-2026-07-21`.

### Development production-hardening APK

- Server: `/opt/apps/class_hero_hub/tmp/class-hero-hub-production-hardening-dev.apk`
- Google Drive: `G:\My Drive\CHH\Remote\class-hero-hub-production-hardening-dev.apk`
- Package `com.classherohub.app`; version code/name
  `5`/`1.3-production-hardening`; min SDK 23; compile/target SDK 35; API
  `https://class.familyherohub.com/api`.
- Size: 96,179,832 bytes; SHA-256:
  `dce28027349e64d06b9c2cb6933e5319e2ad0a6e5a28ab1a8a6c1d94b73f3768`.
- Android debug signer certificate SHA-256:
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
- Server and Drive copies are byte-identical. Endpoint/package, v1/v2 signature,
  `testDebugUnitTest`, `lintDebug` and `assembleDebug` checks passed after Capacitor
  synchronized the final web assets.

## S26n safeguarding UI mop-up

The focused safeguarding administrator UI is deployed to CHH development. The former
combined page is now a compact landing page, a metadata-only conversation search, a
dedicated no-composer active review route and a separately gated permission page.
Mobile cards and controls are bounded at 320, 360, 390 and 430 CSS pixels; advanced
filters collapse without hiding active state; Android Back closes focused overlays;
and the same workflow is localized in English and Arabic RTL.

- Routes: `/school/safeguarding`, `/school/safeguarding/message-reviews`,
  `/school/safeguarding/message-reviews/{session}` and
  `/school/safeguarding/permissions`.
- The backend change is additive only: the already-authorized school context exposes
  active branch/class/grade display metadata, result/staff projections expose safe
  display roles and branch names, and review justification now requires at least 15
  meaningful characters. Permissions, review expiry, audit, protected media,
  moderation, tombstones, internal-note privacy and export controls are unchanged.
- Current-image validation passed: safeguarding backend **8/8**; ordinary text,
  administrator receipts, review receipt neutrality and push-direction coverage
  **9/9**; CHH presentation contracts **3/3**; focused Chromium UI **9/9**;
  `svelte-check` 0 errors/0 warnings; EN/AR parity **1,502/1,502**; production web
  build passed. The unchanged FHH neutral safeguarding projection passed **1/1**.
- Public and loopback CHH health returned 200; all three safeguarding frontend routes
  and ordinary `/messages` returned 200; unauthenticated safeguarding API access
  returned 401. FHH health and `/school-messages` returned 200.
- Only CHH backend and frontend were rebuilt/recreated. PostgreSQL retained container
  `c4bec565ceae` and its 2026-06-16 start time. The notification scheduler retained
  container `ffb8c9436a65` and its 2026-07-20 start time. Production and FHH source were
  not changed.
- Source tag: `chh-s26n-safeguarding-ui-mopup-2026-07-21` after final verification.

### Development safeguarding UI APK

- Server: `/opt/apps/class_hero_hub/tmp/class-hero-hub-safeguarding-ui-dev.apk`
- Google Drive: `G:\My Drive\CHH\Remote\class-hero-hub-safeguarding-ui-dev.apk`
- Package `com.classherohub.app`; version code/name `4`/`1.2-safeguarding`; min SDK
  23; compile/target SDK 35; API `https://class.familyherohub.com/api`.
- Size: 96,172,284 bytes; SHA-256:
  `490ec6b7a4f48feddb8c150a4c819b7fa21ee887a81a78ff6cf4bd2a36f17eb7`.
- Android debug signer certificate SHA-256:
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
- Server and Drive copies are byte-identical. Endpoint/package inspection, v1/v2
  signature verification, `testDebugUnitTest`, `lintDebug` and `assembleDebug` passed
  after the final web assets were synchronized into Capacitor.

## S26m Messaging v1 safeguarding administration

Messaging Slice 12 is deployed to CHH development. Explicit school-scoped grants,
reason-gated 5–60 minute review sessions, a separate no-composer evidence projection,
protected photo/voice review, audited restriction/closure, flags, append-only notes,
evidence-preserving tombstones and protected internal ZIP export are active. Review
does not add a participant, advance Delivered/Read, clear unread counts or enqueue
push. Dom's one active United International School admin membership has the five
explicit pilot permissions; school-admin role alone grants nothing.

- Database revision: `e0f1a2b3c4d5` from `d9e0f1a2b3c4`.
- Pre-migration custom dump:
  `/opt/apps/class_hero_hub/backups/chh-before-s26m-safeguarding-20260720.dump`,
  1,001,727 bytes, SHA-256
  `9ec4dd34374cef925102d4f5980decba76013fcb9ab2ba265acbcf995c8bea33`.
- pgBackRest full label `20260720-202322F`: source size 52,920,684 bytes,
  repository size 6,661,292 bytes. `pgbackrest check` and WAL archive passed after
  correcting repository ownership to the PostgreSQL OS account; PostgreSQL was not
  restarted.
- A restored disposable PostgreSQL database passed upgrade, downgrade to
  `d9e0f1a2b3c4`, re-upgrade, object checks and both append-only trigger checks, then
  was removed.
- Internal exports are capped at 5,000 messages, 500 media and 100 MiB, expire in 30
  minutes, allow three downloads and are removed by the bounded cleanup command.
- FHH receives only neutral participant state; internal reasons, reviewers, notes,
  flags and audit evidence remain CHH-only.
- Focused validation passed: safeguarding backend 8/8; existing named-admin,
  dual-role, FHH receipt, protected photo/voice and notification-direction nodes;
  CHH Svelte check 0 errors/0 warnings; and EN/AR parity 1,368/1,368.
- The authenticated deployed-route check reviewed 25 retained messages, five photos
  and five voice notes, generated/downloaded and verified one evidence ZIP and every
  manifest file hash, then removed the expired temporary artifact. Participant rows,
  Delivered/Read cursors, unread inputs, message/conversation state and notification
  outbox were byte-for-byte logically unchanged; nine safeguarding audit events were
  added. Public and loopback health returned 200. Only backend/frontend were
  recreated; PostgreSQL and the notification scheduler retained their uptime.
- Source tag: `chh-s26m-messaging-safeguarding-2026-07-20` after final deployment
  verification. Production was not touched.

### Development safeguarding APK

- Server: `/opt/apps/class_hero_hub/tmp/class-hero-hub-safeguarding-dev.apk`
- Google Drive: `G:\My Drive\CHH\Remote\class-hero-hub-safeguarding-dev.apk`
- Package `com.classherohub.app`; version code/name `3`/`1.1-push`; min SDK 23,
  compile/target SDK 35; API `https://class.familyherohub.com/api`.
- Size: 96,140,375 bytes; SHA-256:
  `4bcf3be6b52c569be475b6d51e46a538e1a9014528385026600e2acb481d3183`.
- Android debug signer certificate SHA-256:
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
- Server and Drive copies are byte-identical. The fixed endpoint, package, v1/v2
  signature, `testDebugUnitTest`, `lintDebug` and `assembleDebug` checks passed after
  final web assets were synchronized into Capacitor.

Complete message/media retention, legal hold, archival and participant-safe export
policy remain Slice 13. See `MESSAGING_SAFEGUARDING.md` for operations.

## S26l school-message Android push - final physical acceptance

Messaging v1 Slice 11 is complete on CHH development at runtime commit `0c5c643`.
Dom physically confirmed on 2026-07-20 that CHH receives real push while closed,
that FHH-to-CHH notifications reach staff only, and that a notification tap opens
the correct School Chat. The final notification-direction correction was server-side;
no replacement APK was required for acceptance.

- Post-acceptance database correlation for messages `71` and `73` (FHH parent
  authored) shows exactly one `chh_user` staff target each, no sender/self target,
  and no FHH bridge event at either message timestamp.
- Messages `70` and `72` (staff authored) show exactly one `fhh_link` target each.
  Their matching FHH events reached `provider_accepted`; authorised family devices
  received the notification normally.
- The direction correction therefore prevents family-authored messages from
  notifying any FHH household member while preserving staff-reply delivery.
- CHH and FHH loopback/public `/api/health` returned HTTP 200. CHH backend,
  frontend, scheduler and PostgreSQL services are healthy; the notification evidence
  is retained in the durable outbox/delivery tables.
- Final source tag: `chh-s26l-android-push-notifications-2026-07-20`.

**Status date:** 2026-07-20

**Environment:** CHH development, `https://class.familyherohub.com`

**Source checkpoint:** `main`, `0c5c643` plus this completion record. Production was
not touched.

## S26k named-administrator receipt mop-up

Messaging v1 Slice 9 administrator receipts are corrected on CHH development. The
old aggregate query treated every `school_admin_membership` access grant as though it
were safeguarding review. That grant is also the ordinary authorization source for
both named sides of a staff-direct thread and for a named primary administrator in a
student/guardian thread. Aggregation now accepts staff evidence only for memberships
structurally named by the conversation; a nonparticipant safeguarding reviewer still
owns no participant cursor and cannot affect visible receipts.

- Admin-to-teacher, teacher-to-admin, admin-to-FHH-parent and FHH-parent-to-admin
  Sent/Delivered/Read progression passes through the normal participant routes. Live
  read-only inspection confirms the existing named admin/teacher and named
  admin/FHH rows aggregate as Read without exposing message bodies or family data.
- Dual-role teacher/administrator accounts persist the selected membership in the
  message URL. Each request and acknowledgement remains bound to that exact
  membership/participant; switching roles clears the selected thread, and tests prove
  cursors, aggregates and participant rows do not cross-contaminate or duplicate.
- Safeguarding-only review remains outside the normal inbox/thread/acknowledgement
  routes. The focused gate proves denial for a nonparticipant admin, no participant or
  receipt creation, no cursor movement, immutable audit-only evidence, and defensive
  aggregate exclusion. This release does not add a safeguarding review UI/session.
- The focused current-image backend gate passed 50 tests. Current-source browser
  receipt-only polling and dual-role switching passed 2/2; focused receipt, actor,
  tick and policy source tests passed; Svelte checking passed with 0 errors/warnings;
  EN/AR parity remains 1,274/1,274; the production frontend build passed. Real
  attached photo and voice-note tests advance through Delivered and Read, and the
  signed FHH integration is covered in both directions.
- Only CHH backend and frontend were rebuilt/recreated. Public `/`, `/api/health` and
  `/messages` returned HTTP 200 and affected-service logs were clean. PostgreSQL and
  the Slice 10 `notification_scheduler` were not recreated: their container IDs stayed
  `c4bec565ceae` and `e578f39ef6c2`. No schema, migration or production action was
  required.
- Slice 10 is unchanged after deployment: messaging and scheduler remain enabled;
  poll/batch/lease/recheck are 15/50/60/300 seconds; retry is 30-3,600 seconds with 10
  attempts; the school remains `Asia/Muscat`, policy version 4, receipts/contact hours
  enabled, `delay_notifications_only`, staff opt-in/teacher urgent disabled, Sunday-
  Thursday 07:30-15:00, Friday/Saturday closed; the outbox remains empty.

### Development administrator-receipt APK

- Server: `/opt/apps/class_hero_hub/tmp/class-hero-hub-admin-receipts-dev.apk`
- Google Drive: `G:\My Drive\CHH\Remote\class-hero-hub-admin-receipts-dev.apk`
- Package `com.classherohub.app`; version code/name `1`/`1.0`; min SDK 23,
  compile/target SDK 35; API `https://class.familyherohub.com/api`.
- Size: 95,986,665 bytes; SHA-256:
  `f4ab4cf8f58f4a3e28aca49a80c57d06571f24435abe5d424803f57596310902`.
- Android debug signer certificate SHA-256:
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
- Server/build/Drive copies are byte-identical. ZIP, endpoint, package, v1/v2
  signature, `testDebugUnitTest`, `lintDebug` and `assembleDebug` checks passed after
  the final web assets were synchronized.

**Status date:** 2026-07-20

**Environment:** CHH development, `https://class.familyherohub.com`

**Source checkpoint:** `main`, tag
`chh-s26k-admin-receipt-mopup-2026-07-20`

## S26j Messaging v1 contact-hours/outbox checkpoint

Messaging v1 Slice 10 is deployed on CHH development. Parent messages still commit
and appear to staff immediately; only the new per-recipient notification foundation
is held outside configured school contact hours. No push, email, or other provider
delivery is implemented in this slice.

- United International School uses `Asia/Muscat`, Sunday-Thursday 07:30-15:00,
  Friday/Saturday closed, and policy version `4`. Contact hours are enabled in the
  fixed `delay_notifications_only` mode. Teacher urgent marking and personal staff
  out-of-hours opt-in are disabled. The initialization is append-only audited.
- Alembic head is `c8d9e0f1a2b3`. Pre-migration pgBackRest full backup
  `20260720-062615F` completed successfully. The repository's existing pgBackRest
  stanza requires the explicit `--pg1-user=classhero` override for backup commands.
- The separate `notification_scheduler` service is enabled and running. It performs
  policy re-evaluation and crash-safe leasing only; Slice 11 will own provider
  dispatch. The outbox contained zero rows immediately after rollout, as expected
  before a new post-deployment message.
- CHH backend, frontend, and notification scheduler were built/recreated without
  restarting or recreating PostgreSQL. Public `/api/health`, `/messages`, and `/`
  returned HTTP 200; startup and scheduler logs contained no application error.
- Validation passed 429 backend tests with 2 skips, a fresh PostgreSQL upgrade,
  downgrade/re-upgrade, JSONB and concurrent `SKIP LOCKED` checks, a production web
  build, Svelte checking with 0 errors/0 warnings, and EN/AR parity at 1,274 keys.
  Focused source/UI assertions for Slice 10 pass; three documented legacy regex or
  safe-bottom assertions remain stale and unrelated to this slice.

### Development contact-hours APK

- Server: `/opt/apps/class_hero_hub/tmp/class-hero-hub-contact-hours-dev.apk`
- Google Drive: `G:\My Drive\CHH\Remote\class-hero-hub-contact-hours-dev.apk`
- Package: `com.classherohub.app`; version code `1`, version name `1.0`; min SDK 23,
  compile/target SDK 35; native API `https://class.familyherohub.com/api`.
- Size: 95,954,195 bytes; SHA-256:
  `6dee024626863e0bef33e761f6c7a378a97d6bccfaa22c588bdc0085ba6f01ba`.
- Android debug signer certificate SHA-256:
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
- Server and Drive copies are byte-identical. Endpoint, package, v1/v2 signature,
  `testDebugUnitTest`, `lintDebug`, and `assembleDebug` checks passed after the final
  web assets were synchronized. Physical-device execution of the Slice 10 smoke
  matrix remains required.

**Status date:** 2026-07-20

**Environment:** CHH development, `https://class.familyherohub.com`

**Source checkpoint:** `main`, tag
`chh-s26j-messaging-contact-hours-2026-07-20`

## S26i Messaging v1 delivery/read receipts checkpoint

Messaging v1 Slice 9 is deployed to the CHH development stack. Outgoing message
bubbles now show one gray tick for sent, two gray ticks after at least one eligible
ordinary participant's client renders and acknowledges the message, and two blue
ticks after at least one eligible ordinary participant views it. No recipient
identities, counts, all-read state, or safeguarding-admin activity are exposed.

- CHH remains the authoritative message, access-history, policy, receipt-event, and
  aggregate source. FHH remains a credential-hiding proxy; no receipt persistence was
  added there.
- Delivery and read visibility are independent, versioned school controls. United
  International School is enabled for both in development at policy version `3`;
  the existing immutable policy audit records the change. Defaults remain delivery
  on and read off for other/new policy rows.
- Receipt aggregation uses one bounded set query for the page/delta candidate set.
  A representative 50-message history increases from 27 to 28 SELECTs, independent
  of message and participant count. Historical eligibility is evaluated at receipt
  event time, so valid evidence survives later revocation and late joiners do not
  inherit earlier messages.
- Only the CHH backend/frontend and FHH backend/frontend services were rebuilt and
  recreated. The CHH and FHH PostgreSQL containers were not restarted or recreated.
  No migration or database backup was needed because existing receipt events,
  access grants, policy rows, and polling cursors are reused.
- Loopback and public API health checks returned HTTP 200 with `status=ok`; CHH
  `/messages` and FHH `/school-messages` returned HTTP 200 after deployment.
- Focused validation covers sent/delivered/read transitions, all four policy states,
  event-time eligibility and revocation, late joiners, safeguarding-admin exclusion,
  sender exclusion, closed-world FHH proxy sanitization, text/photo/voice parity,
  receipt-only polling without row remounts, state monotonicity, narrow layout, and
  EN/AR accessible ticks. Receipt-specific Playwright flows passed in both apps.

### Development receipt APK

- Server: `/opt/apps/class_hero_hub/tmp/class-hero-hub-message-receipts-dev.apk`
- Google Drive: `G:\My Drive\CHH\Remote\class-hero-hub-message-receipts-dev.apk`
- Package: `com.classherohub.app`; version code `1`, version name `1.0`; min SDK 23,
  compile/target SDK 35.
- Native API: `https://class.familyherohub.com/api`.
- Size: 95,807,045 bytes.
- SHA-256: `5dc8fbcab2cff03e0941543d08664afaae2177c6f8381b7f57f37d6b11021124`.
- Android debug signer certificate SHA-256:
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
- Server and Drive copies are byte-for-byte identical. APK package, endpoint, and
  signature checks passed. App-scoped `testDebugUnitTest`, `lintDebug`, and
  `assembleDebug` passed after the final web assets were synchronized into Capacitor.

**Status date:** 2026-07-18
**Environment:** CHH development, `https://class.familyherohub.com`
**Source checkpoint:** `main`, S25q protected voice-note release tag
`chh-s25q-messaging-voice-notes-2026-07-18`
**Messaging status:** development pilot enabled only for United International School;
production remains disabled and unchanged.

## S25q deployed scope

S25q adds CHH-authoritative protected voice notes for staff and the FHH parent
integration. CHH validates a bounded memory-only raw upload, probes and normalizes it
with ffmpeg to mono AAC-LC in M4A/ISO BMFF, and stores only the randomized protected
result. Raw uploads are limited to 8 MiB; normalized notes are limited to 3 MiB and
600 ms through 180 seconds. Staged rows expire after 24 hours, attachment is
idempotent and conversation scoped, and playback repeats current authorization. FHH
remains a bounded, no-persistence proxy.

The CHH backend and frontend images/services were rebuilt and recreated at deployed
application commit `8c56408`. PostgreSQL was migrated in place but was not restarted
or recreated. No production service, database, configuration, DNS, or artifact was
changed.

- Pre-migration pgBackRest full backup: `20260718-180149F`.
- Alembic: `b7c8d9e0f1a2` is current head. A disposable PostgreSQL database passed a
  clean full upgrade, downgrade to `f5a6b7c8d9e0`, and re-upgrade before the deliberate
  development migration.
- Default-off school control: exactly one enabled row, United International School
  (`school_id=1`), control version `2`; zero other schools enabled. The acknowledgement
  produced one immutable feature-control audit event.
- Public API health, frontend root and `/messages`: HTTP 200. Protected staff voice
  playback and school feature-control endpoints return HTTP 401 without credentials.
- A real FHH-to-CHH development upload produced `audio/mp4`, AAC/MP4, duration 1,000 ms
  and 9,350 normalized bytes through the safe proxy allowlist. No staged smoke row is
  left in the database.
- Affected services are running and their latest 20-minute backend/frontend logs have
  no traceback, uncaught exception or error. PostgreSQL remains healthy.
- Focused CHH validation: 44 backend voice/messaging tests, 12 frontend voice/messaging
  tests, production web build, and EN/AR parity at 1,215 keys passed.

## Previous S25n deployed scope

S25n implements Messaging v1 Slice 8 only: CHH-authoritative protected photo
messages for staff and the FHH parent integration. Messages may contain text, one to
five photos, or both. CHH owns staged/attached media rows and randomized protected
derivatives; raw uploads are bounded in memory and are never persisted. FHH remains a
credential-hiding, no-persistence proxy.

The CHH backend and frontend images/services were rebuilt and recreated. PostgreSQL
was not restarted or recreated. No production service, database, configuration, DNS,
or artifact was changed.

- Pre-deploy pgBackRest full backup: `20260718-111653F`.
- Alembic: upgraded `e4f5a6b7c8d9` to `f5a6b7c8d9e0` (`message_media`); current
  revision is head.
- CHH flag: `MESSAGING_ENABLED=true`.
- Enabled school policy: United International School only (`pending_setup`).
- Loopback frontend root and `/messages`: HTTP 200.
- Direct API health: HTTP 200 with `{"status":"ok"}`; affected services have clean
  startup logs.
- Authenticated compatibility smoke: messaging inbox HTTP 200 (1 item), existing text
  history HTTP 200 (10-item page), protected update thumbnail HTTP 200 (`image/jpeg`,
  25,216 bytes).
- New-image backend suite: 15 passed; protected update-photo regression: 6 passed.
- Frontend: Svelte check 0 errors/0 warnings, production build passed, focused contracts
  9 passed, Android-sized Playwright 7 passed, EN/AR parity 1,165 keys each.
- Query fixture: 24 inbox, 17 unread and 26 50-message-history SELECTs; the single
  Slice 8 media query is page-batched rather than per message/photo.

## Development voice-note APK

- Server: `/opt/apps/class_hero_hub/tmp/class-hero-hub-voice-notes-dev.apk`
- Google Drive: `G:\My Drive\CHH\Remote\class-hero-hub-voice-notes-dev.apk`
- Package: `com.classherohub.app`
- Version: code `1`, name `1.0`; compile SDK 35.
- Native API: `https://class.familyherohub.com/api`
- Size: 95,893,704 bytes.
- SHA-256: `b2fd998690250ac3167a6265b3bd4c0f6a2356d997d336ce6669294b545e324c`.
- Signing: Android debug certificate; signer certificate SHA-256
  `e9506dfc7f53388bb6cc5c8fefdd16804f740745167b602efb725e173033060b`.
- Server and Google Drive copies have identical byte size and SHA-256. Package and
  packaged-asset inspection confirm the application ID and fixed CHH native API above.
- Fresh, app-scoped `testDebugUnitTest`, `lintDebug`, and `assembleDebug` passed after
  the S25q web assets were synchronized into Capacitor.

## Operational boundaries

The source/test default remains disabled; development enablement is an explicit
school acknowledgement and is not production authorization. Staged voice and photo
media expire after 24 hours. Opportunistic bounded cleanup and the dry-run-first
operator cleanup command are not a final retention worker.

Transcription, waveform generation, final retention/deletion automation, compliance
export, receipt presentation, contact-hours scheduling, school-message push,
safeguarding administration and video/office attachments remain later work or
explicit non-goals.

Physical-device verification remains required for microphone grant/denial recovery,
hold/lock/cancel gestures, calls/alarms, backgrounding, speaker/Bluetooth/headset audio
routes, network retry, gesture and three-button navigation, native Back and EN/AR RTL.
Use the S25q rows in `docs/testing/CHH_ANDROID_APK_SMOKE_TEST.md` before widening the
pilot.

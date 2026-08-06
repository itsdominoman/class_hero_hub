# CHH/FHH pre-CEO-demo result

Status: locally complete; release and live demo identities require deployment authorisation
Started: 2026-08-06  
Push/deployment authorisation: none

## Baselines

| System | Baseline commit | Local tag |
|---|---|---|
| CHH | `37f5201bc56abdc04929925281ee95a12a0b313a` | `pre-ceo-demo-baseline-2026-08-06` |
| FHH development | `85616ee0fcc255ca7198d26447e1a7911724a28c` | `pre-ceo-demo-baseline-2026-08-06` |

Both baselines were clean, on the required branch and equal to their origin tracking branch after fetch.

## Checkpoints

This ordered list is updated after each completed implementation checkpoint.

| Order | Repository | Commit | Purpose | Focused validation | Limitation/follow-up |
|---:|---|---|---|---|---|
| 1 | CHH | `e329142` | Audit current pre-demo state and define role/report scope | Repository/runtime/schema inspection | Implementation findings remain tracked below |
| 2 | CHH | `a953e42` | Permit active staff to discover and message active staff in the same school | 2 focused backend authorisation tests and 19 messaging presentation tests passed | Full local messaging file also requires guardian-router configuration and media binaries not present in the Windows harness |
| 3 | FHH development | `fc0637c` | Replace the two-option language selector with the requested opposite-language action | Focused Vitest passed; later full FHH checks passed with explicit development public env values | Physical shell switch remains in the final device checklist |
| 4 | CHH | `1a2395b` | Apply the same language-selector behaviour across CHH navigation contexts | Focused presentation test and Svelte check passed with 0 errors/warnings | Physical mobile-shell switch remains for final device smoke testing |
| 5 | FHH development | `02d6965` | Align the parent School dashboard with the student design while preserving guardian-only areas | 197 unit tests, Svelte check, i18n parity and 4 Chromium desktop/mobile/Android-shell scenarios passed | Physical Android Back, WebView and touch testing remains in the device smoke checklist |
| 6 | CHH | `7ef053e` | Checkpoint immediately before school-role, department and permission-schema work | Clean source checkpoint plus fresh verified PostgreSQL custom-format backup | No migration was applied |
| 7 | CHH | `8f28ec8` | Add Principal, Deputy Principal, HOD and Support Staff roles; dated department assignments; scoped reporting; communication oversight; and same-school staff messaging | 16 focused backend tests, 19 messaging presentation tests, Svelte check and 2,233-key English/Arabic parity passed; Alembic upgrade/downgrade SQL validated offline | Source only: migration and demo-role assignments are not deployed; physical workflow checks remain |
| 8 | CHH | `5297384` | Persist a one-time, versioned staff conversation-visibility and safeguarding acknowledgement | 5 role/messaging backend tests, 19 messaging presentation tests, Svelte check, 2,236-key language parity, compileall and offline migration upgrade/downgrade SQL passed | Source only: revision `f0e1d2c3b4a5` is not applied; physical mobile-shell flow remains |
| 9 | FHH development | `bdda9d4` | Persist the matching one-time parent school-messaging acknowledgement | All 23 school-messaging proxy tests, Svelte check, 1,571-key language parity, compileall and offline migration upgrade/downgrade SQL passed | Source only: revision `d2e3f4a5b6c7` is not applied; physical Android-shell flow remains |
| 10 | CHH | `329051b` | Publish the canonical messaging-warning version through the authenticated private FHH integration | Focused service-authentication and no-store response test passed | Source only; depends on controlled CHH/FHH rollout order |
| 11 | FHH development | `35964c4` | Source the warning version from authoritative CHH while retaining FHH-owned parent acknowledgement identity | Focused parent versioning/user-scope test passed | Source only; a CHH outage intentionally prevents accepting an unverified policy version |
| 12 | CHH | `9ce5619` | Remove infrastructure telemetry and operations controls from school routes/navigation while retaining platform-admin monitoring APIs | 3 production-hardening backend tests, 19 messaging presentation tests, Svelte check and language parity passed | Platform monitoring remains API-backed; no school-facing operations page remains |
| 13 | CHH | `95614ec` | Add reusable debounced teacher search, school-first server scope, Arabic/identity/assignment/department matching, natural education-aware setup ordering and stronger desktop/mobile navigation hierarchy | 63 focused backend tests, Svelte check with 0 errors/warnings, 2,244-key English/Arabic parity and 18 navigation/state presentation tests passed | Source only; physical keyboard, RTL and long-roster browser checks remain |
| 14 | CHH | `3217d2c` | Add a dry-run-first, manifest-only seeded-content cleanup with dependency/file handling, audit evidence and retained tombstones that prevent accidental reseeding | All 19 realistic demo-seeder/cleanup tests and compileall passed, including manual-content preservation and repeat cleanup | Utility is source-only; authoritative dry-run and any deletion remain pending the explicit pre-operation checkpoint |
| 15 | CHH | `b9c57e2` | Checkpoint immediately before seeded-content deletion with the authoritative zero-ambiguity dry-run, guarded production invocation, verified point-in-time backup and cleanup report | 3 focused cleanup/guard tests passed; backup catalogue and SHA-256 verified | No deletion had occurred at this checkpoint |
| 16 | CHH | `1856f00` | Record the completed manifest-only seeded-content cleanup and post-operation evidence | Zero-repeat dry-run, 1,041 tombstones, one audit event, preserved table counts, container health and affected logs verified | Recovery requires restoring the recorded pre-operation dump; no service restart occurred |
| 17 | CHH | `cc50980` | Add explicit teacher-to-family assignment-scope regression coverage across homeroom, subject, multi-class, cross-branch cover, expired, unrelated and cross-school targets plus direct conversation/message manipulation | 4 focused staff-side messaging tests passed | Guardian-route companion tests remain unavailable in the local Windows harness because those routers are disabled there; existing authoritative integration coverage is retained |
| 18 | CHH | `bf9967a` | Add shared school certificate logo/accent branding, extend positive-recognition management to Principal and Deputy Principal, and keep recognition in the Behaviour & recognition workspace | 10 focused backend tests, Svelte check with 0 errors/warnings, 8 recognition presentation tests, 2,257-key English/Arabic parity and guarded PostgreSQL upgrade/downgrade SQL passed | Source only: revision `c6d7e8f9a0b1` is not applied; physical EN/AR browser print/PDF output remains in the final checklist |
| 19 | CHH | `b40d221` | Add permission-scoped behaviour PDF/CSV exports and immutable report/certificate sharing through existing School Messages | 55 focused backend tests, bounded inbox/history query regression, compileall, Svelte check with 0 errors/warnings, 2,274-key EN/AR parity, visual PDF QA and guarded PostgreSQL upgrade/downgrade SQL passed | Source only: revision `c7d8e9f0a1b2` is not applied; backend PDFs deliberately do not fetch remote logo URLs across an SSRF boundary |
| 20 | FHH development | `cc15c95` | Receive protected staff-generated report/certificate documents through the exact-child School Chats proxy | 24 proxy tests, 197 frontend unit tests, Svelte check with 0 errors/warnings and 1,574-key EN/AR parity passed | Source only; physical parent Android download remains in the final device checklist |
| 21 | FHH development | `434a91a` | Align family and child profiles to the shared CHH avatar catalogue with deterministic legacy mapping | Focused backend and frontend catalogue coverage plus the later full FHH gates passed | Source only; no family record was rewritten and no APK was built |
| 22 | CHH | `5c64802` | Restore deterministic backend coverage while preserving the production CHH/FHH guardian boundary | Full CHH backend collection passed: 621 tests with 19 explicit environment skips | FFmpeg-dependent audio processing remains for the Linux/container gate |
| 23 | FHH development | `413e960` | Harden deterministic parent/child browser acceptance coverage | 74/74 Chromium cases, 200 unit tests, Svelte 0/0, 1,574-key EN/AR parity and production build passed | Test-harness only; this did not deploy or change the live browser header |
| 24 | CHH | `caac5ac` | Align browser fixtures with hardened role, entitlement, acknowledgement and native-shell contracts; fail messaging closed when no candidate membership is authorised | Svelte 0/0; 16/17 bounded messaging/mobile cases passed together, with the sole cold-start timeout passing immediately in isolation | Deliberately stopped short of another full browser matrix; release-device checks remain in the runbook |

## Backups and migrations

- No migration has been applied. One explicitly scoped CHH data mutation removed 1,041 manifest-proven seeded content rows after a verified backup and dry-run; all manual/unproven content was preserved and 1,041 seed manifests remain as reseed-blocking tombstones.
- Before the role/department schema work, CHH PostgreSQL backup `/opt/apps/class_hero_hub/backups/pre-ceo-demo/chh-pre-role-expansion-20260806T115820Z.dump` was created on the pilot server: 1,390,354 bytes; SHA-256 `fcda2c0fa2d4296f9332e25aa6be93c6fbe897e9b412270965bbc5c5840d17be`; `pg_restore --list` verified the catalogue.
- Alembic revision `b3c4d5e6f7a8` was validated with offline upgrade and downgrade SQL. Applying it remains a separately authorised deployment step.
- Before the FHH acknowledgement-schema work, development dump `/opt/apps/family-hero-hub/backups/pre-ceo-demo/fhh-dev-pre-messaging-ack-20260806T124500Z.dump` was created: 195,871 bytes; SHA-256 `cbf1d4e7aeb42e321ef69571f25c14424837aff7faec2876301fc28b055107e1`; its `pg_restore --list` catalogue was verified inside the healthy PostgreSQL container.
- Immediately before the planned CHH manifest-only content cleanup, custom-format dump `/opt/apps/class_hero_hub/backups/pre-ceo-demo/chh-pre-seed-cleanup-20260806T132931Z.dump` was created: 1,390,351 bytes; SHA-256 `0666777ebcf3bb3df41db81a48d0174120666522b8e87cd59a9030de754dafd6`; `pg_restore --list` verified the catalogue. The authoritative dry-run found 1,041 unambiguous manifest-proven rows and preserved every unmanifested survey, conversation, message and content row.
- The normal FHH pgBackRest command was attempted first and failed before backup because the existing encrypted local `backup.info` could not be decoded and repository `2` was rejected. The fallback dump above is valid; repairing pgBackRest is an operations follow-up and was not mixed into this product task.
- Acknowledgement revisions `f0e1d2c3b4a5` (CHH) and `d2e3f4a5b6c7` (FHH) were validated with offline upgrade and downgrade SQL. Neither has been applied.
- Certificate-branding revision `c6d7e8f9a0b1` was validated with guarded PostgreSQL upgrade and downgrade SQL. It has not been applied.
- Generated-message-document revision `c7d8e9f0a1b2` was validated against PostgreSQL with guarded offline upgrade and downgrade SQL. It has not been applied.

## Runtime/deployment impact

- No service was rebuilt or restarted.
- CHH source through `7ef053e` and FHH development source through `02d6965` are present in their authoritative server worktrees without rebuilding or restarting services. Later checkpoints remain local.
- No deployment, push, APK build or Android package change occurred.
- The guarded manifest-only cleanup ran as a temporary operator command against CHH, then its temporary files were removed. Post-operation CHH readiness and all containers remained healthy.

## Validation completed so far

- Both repository branches, HEADs, remotes, tracking states and clean worktrees verified.
- Both database Alembic revisions and table inventories inspected.
- CHH/FHH relevant services verified healthy.
- UIS entitlement, feature-control and messaging-policy state inspected.
- Jason Green's active UIS teacher membership and three active teaching assignments verified.
- Seed manifest namespaces/entity counts inspected without reading private content.
- Manifest-only seeded-content cleanup removed 166 announcements, 208 calendar events, 512 homework/diary items and 155 update posts; its retained tombstones, audit event, preserved counts and zero-repeat dry-run were verified.
- Same-school staff messaging, shared CHH/FHH language selection, FHH parent/student School dashboard boundaries, leadership/HOD reporting scope, department administration, audited communication-oversight scope, scoped teacher search, cross-school search isolation, natural setup ordering, responsive school-menu hierarchy and leadership-managed school certificate branding have focused automated coverage.
- Filter-preserving behaviour PDF/CSV exports, CSV formula neutralisation, staged-document transaction safety, exact-generator attachment scope, idempotent retry, participant-scoped document download, FHH exact-child proxying and retention disposal now have focused automated coverage. English/Arabic behaviour reports and certificates were rendered to page images and visually inspected for clipping, hierarchy and RTL layout.
- FHH's bounded browser gate passed 74/74 across authenticated parent/child, linked-school, Android-shell, Arabic/RTL, messaging, surveys and visual-width cases. CHH's full backend collection passed 621 tests with 19 explicit environment skips; the final changed CHH messaging/mobile browser surfaces were checked narrowly rather than repeating the entire matrix.

## Deployment and physical-device handoff

- The implementation and local evidence are complete enough for handoff. No push, deployment, migration or APK build was authorised or performed.
- Leadership/HOD demo identities and the deterministic linked demo family cannot be made usable on the live demo until the paired CHH/FHH source and migrations are released in a controlled window.
- Physical Android/WebView, download, keyboard, touch and final EN/AR device checks remain release gates, not unfinished local implementation.
- The authorised release order, demo journeys, rollback points and known live-browser risks are recorded in `CEO_DEMO_RUNBOOK.md`.

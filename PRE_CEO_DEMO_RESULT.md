# CHH/FHH pre-CEO-demo result

Status: active  
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

## Backups and migrations

- No migration, deletion or database mutation has occurred during the audit.
- Before the role/department schema work, CHH PostgreSQL backup `/opt/apps/class_hero_hub/backups/pre-ceo-demo/chh-pre-role-expansion-20260806T115820Z.dump` was created on the pilot server: 1,390,354 bytes; SHA-256 `fcda2c0fa2d4296f9332e25aa6be93c6fbe897e9b412270965bbc5c5840d17be`; `pg_restore --list` verified the catalogue.
- Alembic revision `b3c4d5e6f7a8` was validated with offline upgrade and downgrade SQL. Applying it remains a separately authorised deployment step.
- Before the FHH acknowledgement-schema work, development dump `/opt/apps/family-hero-hub/backups/pre-ceo-demo/fhh-dev-pre-messaging-ack-20260806T124500Z.dump` was created: 195,871 bytes; SHA-256 `cbf1d4e7aeb42e321ef69571f25c14424837aff7faec2876301fc28b055107e1`; its `pg_restore --list` catalogue was verified inside the healthy PostgreSQL container.
- Immediately before the planned CHH manifest-only content cleanup, custom-format dump `/opt/apps/class_hero_hub/backups/pre-ceo-demo/chh-pre-seed-cleanup-20260806T132931Z.dump` was created: 1,390,351 bytes; SHA-256 `0666777ebcf3bb3df41db81a48d0174120666522b8e87cd59a9030de754dafd6`; `pg_restore --list` verified the catalogue. The authoritative dry-run found 1,041 unambiguous manifest-proven rows and preserved every unmanifested survey, conversation, message and content row.
- The normal FHH pgBackRest command was attempted first and failed before backup because the existing encrypted local `backup.info` could not be decoded and repository `2` was rejected. The fallback dump above is valid; repairing pgBackRest is an operations follow-up and was not mixed into this product task.
- Acknowledgement revisions `f0e1d2c3b4a5` (CHH) and `d2e3f4a5b6c7` (FHH) were validated with offline upgrade and downgrade SQL. Neither has been applied.

## Runtime/deployment impact

- No service was rebuilt or restarted.
- CHH source through `7ef053e` and FHH development source through `02d6965` are present in their authoritative server worktrees without rebuilding or restarting services. Later checkpoints remain local.
- No deployment, push, APK build or Android package change occurred.

## Validation completed so far

- Both repository branches, HEADs, remotes, tracking states and clean worktrees verified.
- Both database Alembic revisions and table inventories inspected.
- CHH/FHH relevant services verified healthy.
- UIS entitlement, feature-control and messaging-policy state inspected.
- Jason Green's active UIS teacher membership and three active teaching assignments verified.
- Seed manifest namespaces/entity counts inspected without reading private content.
- Same-school staff messaging, shared CHH/FHH language selection, FHH parent/student School dashboard boundaries, leadership/HOD reporting scope, department administration, audited communication-oversight scope, scoped teacher search, cross-school search isolation, natural setup ordering and responsive school-menu hierarchy have focused automated coverage.

## Remaining work

Remaining Priority 0-3 implementation, backups, cleanup, broader test suites, manual browser/mobile/RTL checks, demo relationship completion, runbook and final tags remain active.

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

## Backups and migrations

- No migration, deletion or database mutation occurred during the audit.
- A fresh verified backup is required immediately before the first migration or seeded-data deletion.

## Runtime/deployment impact

- No service was rebuilt or restarted.
- CHH checkpoints through `a953e42` were transferred to the pilot server worktree without rebuilding or restarting services; later checkpoints remain local pending the next controlled transfer.
- No deployment, push, APK build or Android package change occurred.

## Validation completed so far

- Both repository branches, HEADs, remotes, tracking states and clean worktrees verified.
- Both database Alembic revisions and table inventories inspected.
- CHH/FHH relevant services verified healthy.
- UIS entitlement, feature-control and messaging-policy state inspected.
- Jason Green's active UIS teacher membership and three active teaching assignments verified.
- Seed manifest namespaces/entity counts inspected without reading private content.
- Same-school staff messaging, shared CHH/FHH language selection and FHH parent/student School dashboard boundaries have focused automated coverage.

## Remaining work

Remaining Priority 0-3 implementation, backups, cleanup, broader test suites, manual browser/mobile/RTL checks, demo relationship completion, runbook and final tags remain active.

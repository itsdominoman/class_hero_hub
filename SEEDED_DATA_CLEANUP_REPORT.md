# Seeded data cleanup report

Status: applied and post-operation verification complete  
Target: CHH pilot/public, United International School (`united-international-school`)  
Cleanup version: `manifest-content-cleanup-v1`  
Dry-run date: 2026-08-06

## Safety boundary

The cleanup selects a row only when its `demo_seed_records` manifest has an allowed entity type, the expected model/table name, a live model ID and the exact target school ID. It does not match on titles, message text, dates, authors or other content signatures. Model mismatches, missing IDs and missing targets are reported as ambiguous and are never deleted.

The manifest record is retained as a cleanup tombstone after deletion so the deterministic seeder cannot recreate retired content. Related reads, completions, attachments and update photos are planned explicitly. Files are removed only after the database transaction commits and only when their resolved path remains under the configured upload root.

Default cleanup scope is limited to manifest-proven notices, calendar events, homework/diary items, family updates and seeded update photos. Behaviour events are intentionally retained for the management-reporting demonstration. Surveys, conversations and messages have no seed-manifest provenance and are never selected.

## Verified pre-operation backup

- File: `/opt/apps/class_hero_hub/backups/pre-ceo-demo/chh-pre-seed-cleanup-20260806T132931Z.dump`
- Format: PostgreSQL custom format
- Size: 1,390,351 bytes
- SHA-256: `0666777ebcf3bb3df41db81a48d0174120666522b8e87cd59a9030de754dafd6`
- Verification: `pg_restore --list` completed successfully in the CHH PostgreSQL container.

## Authoritative dry-run

| Data type | Manifest-proven rows proposed | Rows preserved outside selection | Ambiguous rows |
|---|---:|---:|---:|
| Notices/announcements | 166 | 21 | 0 |
| Calendar events | 208 | 4 | 0 |
| Homework/diary items | 512 | 18 | 0 |
| Family updates | 155 | 33 | 0 |
| Update photos | 0 | 47 | 0 |
| **Total** | **1,041** | **123** | **0** |

The proposed rows span three deterministic namespaces: `s22-demo-v1` (31), `s22c-showcase-v1` (390) and `s22d-management-v1` (620).

No dependent records were found in the selected set: zero announcement attachments/reads, homework attachments/completions and child update photos. The apply path still handles and reports these dependencies if the state changes before execution.

## Explicitly preserved or excluded

- 10,138 manifest-proven behaviour events are retained to support the CEO management-reporting walkthrough.
- 10 surveys are preserved because no survey manifest proves they are seeded.
- 11 conversations and 132 messages are preserved because no messaging manifest proves they are seeded.
- All 123 unselected content rows and all 47 update photos are preserved; no title/content inference is used to classify them.
- Manually created items therefore remain untouched even when their wording resembles demo content.

## Apply result

The cleanup was applied once through the guarded operator command after the verified backup and pre-operation Git checkpoint.

| Data type | Deleted | Post-operation rows preserved |
|---|---:|---:|
| Notices/announcements | 166 | 21 |
| Calendar events | 208 | 4 |
| Homework/diary items | 512 | 18 |
| Family updates | 155 | 33 |
| Update photos | 0 | 47 |
| **Total** | **1,041** | **123** |

Post-operation verification established:

- all 1,041 selected manifests now carry the retained `removed` cleanup tombstone;
- a second dry-run proposed zero deletions and reported all 1,041 rows as already removed;
- exactly one `demo_seed.content_cleanup` audit event records the operation;
- all 10 surveys, 11 conversations and 132 messages remain present;
- 10,334 behaviour events remain present, including all 10,138 manifest-proven reporting events;
- there were no attachment, read, completion, photo or file dependencies to remove;
- all CHH containers remained healthy and the affected backend log contained readiness `200` entries with no cleanup error or traceback;
- no service was rebuilt or restarted;
- the temporary operator scripts were removed from both the host and running container after verification.

Recovery is possible by restoring the verified pre-operation custom-format dump. No manually created row was selected by this cleanup, and the backup is required to recover the intentionally deleted seeded rows.

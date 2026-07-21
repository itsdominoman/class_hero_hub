# Messaging v1 Slice 13 scale results

Measured on 2026-07-21 against a disposable PostgreSQL database at Alembic
`f0a1b2c3d4e6`. The tool refuses protected database names and requires the
`chh_scale_` prefix. It was removed after the run.

## Representative school

| Record | Count |
|---|---:|
| Students | 1,000 |
| Guardians | 2,000 |
| Staff | 75 |
| Conversations across three branch labels | 6,000 |
| Messages | 120,000 |
| Receipt events | 48,000 |
| Photo rows | 6,000 |
| Voice-note rows | 6,000 |
| Notification jobs | 6,000 |
| Safeguarding audit events | 600 |

Database size was 107,641,879 bytes. Modelled protected media was 3,599,940,000
bytes. Seed time was 17.865 seconds. Media bytes are realistic metadata assumptions;
the scale tool deliberately does not create protected files.

## Query latency

Thirty warm samples were taken for each bounded query.

| Query | Rows | p50 ms | p95 ms | max ms |
|---|---:|---:|---:|---:|
| Inbox listing | 3 | 3.148 | 4.908 | 7.614 |
| Message pagination | 20 | 0.847 | 2.031 | 2.565 |
| Receipt aggregation | 4 | 1.976 | 4.342 | 4.720 |
| Notification targeting | 100 | 1.502 | 3.155 | 4.813 |
| Safeguarding search | 50 | 11.280 | 14.114 | 15.117 |
| Safeguarding review projection | 20 | 4.705 | 12.110 | 13.212 |
| Export manifest selection | 20 | 2.041 | 6.764 | 8.323 |
| Retention preview candidates | 1 | 36.329 | 40.266 | 42.355 |
| Archive selection | 100 | 1.025 | 2.309 | 2.946 |
| Worker claim selection | 100 | 6.732 | 8.077 | 8.806 |
| Operations status counts | 4 | 6.978 | 8.550 | 10.478 |

No measured query exceeded 50 ms, so Slice 13 added no speculative index beyond
the migration's job, policy, hold, archive and governance indexes. The claim probe
shows that selecting a bounded 100-row batch is not the database bottleneck; it is
not an end-to-end provider throughput claim. Notification backlog-clearing rate is
provider, policy and recipient dependent and must be observed during the pilot.

## Growth interpretation

At this mix, 120,000 messages occupy about 108 MB of PostgreSQL and imply about
3.60 GB of protected media. A linear planning envelope is therefore roughly
0.9 GB of database and 30 GB of protected media per million messages, before
backups, WAL, indexes changing with production data, archive redundancy and export
artifacts. A school generating 120,000 messages per year should initially budget at
least 0.11 GB database and 3.6 GB media per year, plus headroom. Verified archive
copying temporarily needs both hot and archive copies. Capacity must be recalibrated
from pilot telemetry rather than treated as a guarantee.

## Functional and failure evidence

The deployed-image suites cover concurrent/idempotent messaging, monotonic receipts,
contact-hours release, notification direction, token invalidation, bridge retries,
lease recovery, owner transfer, legal-hold exclusion, asynchronous export custody,
media failures and safeguard isolation. CHH passed 459 tests with 2 skips and FHH
passed 359 tests. A live-development retention preview completed successfully with
zero eligible recent records. External FCM saturation, multi-hour backlog clearing,
and production cold-object-store throughput were not simulated and remain pilot
observations.

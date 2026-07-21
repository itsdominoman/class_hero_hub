# Messaging v1 development pilot readiness assessment

Status values are **Ready**, **Ready with conditions**, **Blocked**, **Requires school policy**, and **Requires legal review**. This is not a claim of legal compliance.

| Area | Status | Evidence / condition |
|---|---|---|
| Core text/photo/voice/receipts | Ready | Deployed-image regression suites and development route/health smokes passed. |
| School/FHH authorization isolation | Ready | CHH remains authority; FHH proxy receives no legal-hold or safeguarding detail. |
| System Owner governance | Ready with conditions | Explicit owner, transfer and recovery implemented; school must name and train owner/backup. |
| Safeguarding and evidence custody | Ready with conditions | Reason-gated review, async verified exports, bounded downloads; school case procedure required. |
| Retention and legal hold | Requires school policy | Conservative defaults and preview controls exist; school must approve values/process. |
| Local legal/regulatory basis | Requires legal review | Oman/school requirements were not invented or certified by this project. |
| Archive | Ready with conditions | Verified local development adapter; production cold/object storage and encrypted off-host custody still required. |
| Workers/replay | Ready | Durable leases, recovery, dead state and bounded reason-audited operations. |
| Monitoring/alerts | Ready with conditions | Protected health/thresholds exist; external monitor/page integration is required before production. |
| Database/storage capacity | Ready with conditions | Representative 120,000-message scale run stayed below 41 ms p95; pilot telemetry must recalibrate growth assumptions. |
| Backup | Ready with conditions | pgBackRest healthy in dev; repository encryption/off-host policy required for production. |
| Restore | Ready with conditions | Fresh and restored database round trips, restored app starts and a 20-file protected-media restore passed; repeat periodically. |
| Migration safety | Ready | Explicit validation URL/prefix; protected downgrades fail closed without exact emergency override. |
| Security | Ready with conditions | Credential-bearing commands were redacted and the exposed development database credential was rotated; the old invalid value remains in immutable historical commits. |
| Staff training | Ready with conditions | Guides/manuals/storyboards supplied; attendance and supervised practice required. |
| Parent communication | Requires school policy | School must approve School Chats, privacy, hours, emergency and support notice. |
| Incident/support process | Ready with conditions | Runbook exists; named on-call/escalation owners and rehearsal required. |
| Android deployment | Ready with conditions | Version-code 5 development APK passed endpoint/package/signature/hash/Drive equality. No Play Store publication. |
| iOS/APNs | Blocked | Explicitly outside Slice 13; iOS push is not available for this pilot. |
| Rollback | Ready with conditions | Forward-fix preferred; deployment backup and exact restore/pause criteria required. |

## United International School one-school pilot gate

- [x] Existing correct administrator identified for explicit System Owner migration without duplicate grants.
- [ ] Dominique Brown confirms acceptance as System Owner and a backup active administrator is nominated.
- [ ] School approves contact hours, urgent use, replies/receipts and parent notice.
- [ ] Safeguarding lead approves named reviewers/managers/exporters/legal-hold managers.
- [ ] School policy and legal reviewers approve retention and preservation settings.
- [x] Development backup, disposable restore, migration round trip, scaled performance and failure tests pass.
- [x] Development public/loopback health, workers, operations, ordinary messaging, School Chats, push direction and safeguard/export regression smoke pass.
- [x] Android development APK metadata/signature/hash/Drive equality pass.
- [ ] Teachers, safeguarding team, System Owner and pilot parents complete training.
- [ ] Launch cohort, support hours, incident contacts, success metrics, pause and rollback decisions signed off.

Pilot classification: **Ready with conditions**. Technical rehearsal/deployment gates
passed. Named-owner acceptance, a backup administrator, policy/legal decisions,
training, support ownership and signed launch/pause criteria remain with the school
and authorised advisers.

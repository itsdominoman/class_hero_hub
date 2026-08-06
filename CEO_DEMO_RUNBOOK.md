# CHH/FHH CEO demo runbook

Prepared: 2026-08-06

Current authority: CHH pilot and FHH development deployment/UAT only; no FHH
production promotion or APK publication
Detailed evidence: `PRE_CEO_DEMO_RESULT.md`

## Release decision

The paired implementation now serves CHH pilot and FHH development. Health and
migration gates passed. It is ready for bounded user acceptance, but the project
is not complete until the role identities/relationships are provisioned and the
full physical journey passes.

The following remaining actions require explicit user input or authorisation:

1. Select the real invitation identities for Principal, Deputy Principal and HOD.
2. Provision those identities and the demo family relationships through supported UI.
3. Promote any accepted work to FHH production or publish a new APK.

## Frozen source checkpoints

- CHH pilot source: `931eef68cd9566c9f7eed8d97a9474d4006f11ed`.
- FHH development source: `97003047bb5d06a58d50658056b98aef15ce33be`.
- Original baselines: CHH `37f5201` and FHH `85616ee`, both tagged `pre-ceo-demo-baseline-2026-08-06` locally.
- Final completion tags have not been created because UAT is incomplete.

## Completed deployment gates

1. Intended histories were reviewed and fresh verified backups were taken.
2. CHH migrations reached `d8e9f0a1b2c3`; readiness reports current.
3. FHH development migrations reached `d3e4f5a6b7c8`; readiness reports current.
4. CHH was deployed before the dependent FHH development work.
5. Both public development homes/readiness endpoints return HTTP 200 and all
   relevant containers are healthy.
6. FHH production and the Play Store release were not changed.

## Demo identity provisioning

Provision identities only through the normal application/administrative paths after the migrations are live. Do not add hard-coded email, title or permission exceptions.

- Preserve Jason Green's existing UIS teacher membership and its verified active assignments.
- Create one deterministic FHH parent and linked child relationship through the supported invitation/link flow; verify exact-child access and absence of sibling/guardian leakage.
- Create or assign one Principal, one Deputy Principal and one HOD membership. Give the HOD an explicit active department assignment and ensure the department's staff assignments are current.
- Keep platform administration, school setup ownership and leadership/reporting capabilities separate.
- Store credentials in the approved secret/password channel, never in this repository or runbook.

## Suggested demo journey

1. **FHH parent:** sign in, open the linked child's School workspace, switch EN/AR, review a school update and open School Chats.
2. **CHH teacher:** show assignment-scoped students, use search, open the existing family conversation and demonstrate the versioned safeguarding acknowledgement.
3. **Principal/deputy:** open the management report view, show school-wide trends and Communication Oversight without platform infrastructure access.
4. **HOD:** show the same report/oversight surfaces constrained to the assigned department.
5. **Recognition:** confirm a positive-recognition award and show school logo/accent branding in EN and AR.
6. **Export/share:** export the filtered behaviour report as CSV/PDF, stage it into the existing conversation, then download it as the exact linked FHH parent.
7. **Safety close:** show that revoked, expired, unrelated and cross-school identities fail closed while authorised history remains intact.

## Post-deployment acceptance

- CHH and FHH readiness endpoints and workers are healthy.
- Database revisions match the reviewed heads.
- Parent, child, teacher, Principal, Deputy and HOD routes resolve to the intended landing pages and scopes.
- Direct URL and API manipulation fail closed for unrelated school, student, conversation and generated-document identifiers.
- English and Arabic direction, mobile header, Android Back, keyboard resize and protected download work on a physical device.
- No school role can access infrastructure telemetry or platform operations.

## Known live-browser risk outside this local release proof

A live FHH mobile-browser screenshot supplied after the audit showed the full Surveys Hub and School Chats controls crowded into the global header, colliding with the logo/title and duplicating School Chats on the dashboard. The reporter also observed that a parent without a linked school child could see the Survey entry.

Treat this as a separate Priority 0 release check:

- Hide school Survey navigation unless an active linked child/school relationship authorises it.
- Reject the direct Survey route and API with no metadata disclosure when that relationship is absent.
- Restore a bounded mobile-web header without changing the intended APK navigation.
- Keep School Chats in the approved information architecture and avoid duplicate entry points.

The older browser harness did not include the reporter's exact unlinked-parent
state. Reproduce this in FHH development during UAT; if it remains present, it is
a development blocker and must be fixed before production promotion.

## Rollback

- Stop the rollout if migrations, health checks, exact-child scope or private CHH/FHH authentication fail.
- Prefer restoring the verified pre-release database backup and redeploying the previously recorded server commits over improvising live data repairs.
- Retain the local baseline tags and the backup paths/checksums in `PRE_CEO_DEMO_RESULT.md`.
- Do not reverse the already completed manifest-proven seed cleanup without restoring its recorded pre-operation CHH dump; that operation is separately documented and recoverable only from the verified backup.

# CHH/FHH CEO demo runbook

Prepared: 2026-08-06

Current authority: local source and validation only; no push, deployment, migration or APK build
Detailed evidence: `PRE_CEO_DEMO_RESULT.md`

## Release decision

The local CHH and FHH development implementations are ready for a controlled release review. They are not the code currently serving the live demo environments. Do not present leadership/HOD identities, certificate branding, generated-document sharing or the aligned avatar experience as live until the deployment and post-deployment gates below pass.

The following actions require explicit authorisation:

1. Push the local CHH `main` and FHH `develop` checkpoints.
2. Take fresh release-window backups and verify their catalogues/checksums.
3. Apply the pending CHH and FHH migrations.
4. Rebuild/restart the paired services in the controlled order.
5. Provision or change live demo identities and relationships.

## Frozen source checkpoints

- CHH local source: `caac5ac` plus the documentation checkpoint containing this runbook.
- FHH development local source: `413e960`.
- Original baselines: CHH `37f5201` and FHH `85616ee`, both tagged `pre-ceo-demo-baseline-2026-08-06` locally.
- No current checkpoint has been pushed or deployed by this audit.

## Pre-release gates

1. Review both worktree histories and confirm only the intended checkpoints will be released.
2. Confirm the existing verified backups listed in `PRE_CEO_DEMO_RESULT.md`, then take fresh release-window backups before applying migrations.
3. Confirm CHH migration history reaches the role/department, messaging acknowledgement, certificate-branding and generated-document revisions without a branch conflict.
4. Confirm FHH migration history reaches the parent acknowledgement revision without a branch conflict.
5. Deploy CHH before enabling dependent FHH behaviour, because CHH owns the authoritative messaging policy, school scope and protected document endpoints.
6. Deploy FHH development after CHH health and private integration authentication pass.
7. Do not deploy this work to FHH production as part of this runbook.

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

The local browser harness passing does not prove this live issue is fixed; current audit changes were not deployed and the reported unlinked-parent state was not part of the final local fixture.

## Rollback

- Stop the rollout if migrations, health checks, exact-child scope or private CHH/FHH authentication fail.
- Prefer restoring the verified pre-release database backup and redeploying the previously recorded server commits over improvising live data repairs.
- Retain the local baseline tags and the backup paths/checksums in `PRE_CEO_DEMO_RESULT.md`.
- Do not reverse the already completed manifest-proven seed cleanup without restoring its recorded pre-operation CHH dump; that operation is separately documented and recoverable only from the verified backup.

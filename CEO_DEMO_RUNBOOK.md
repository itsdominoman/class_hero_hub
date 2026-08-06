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

- CHH pilot source: `ea8507523c8b6dfc397f88b84289e8aedc95b186`.
- FHH development source: `d0121b7014f7442560ddea15ded278f04187118f`.
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

## Observed development acceptance

The following checks were observed against the deployed development systems on
2026-08-07:

- The user accepted the FHH development mobile header: the logo/title render
  correctly, only Logout remains in the global header, and Surveys/School Chats
  do not crowd or duplicate the header.
- The user accepted the unlinked-parent boundary: an unlinked parent has no
  Survey card and cannot use the direct Surveys destination.
- The user accepted the CHH Subject Groups result for `G12B`: nine expected
  groups are shown.
- CHH exact numeric student search was verified live after deployment: query
  `1` returns only student ID `1` (`Showing 1–1 of 1 students`).
- CHH and FHH development link counts reconcile at one active development link;
  both lifecycle and notification workers report healthy with no current error.

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

## Final UAT gates before production promotion

Run these in order so failures remain easy to isolate and no broad retest is
needed:

1. **Device-only regression:** open the existing production Google Play app and
   confirm its pre-CHH functions still load and save normally. No messaging entry
   is expected in that old production build.
2. **FHH linked parent:** on development, open the linked child's School workspace
   in EN and AR, then verify notices, Survey eligibility and School Chats. Repeat
   the header, Android Back and keyboard behaviour in the development Android shell.
3. **CHH narrow layout:** on the pilot site, switch EN/AR on School Setup, Students
   and Reports; confirm the menu hierarchy, search keyboard, empty state and RTL
   layout at phone width.
4. **Approved identities:** supply/select the Principal, Deputy Principal and HOD
   invitation identities, then create the department and dated HOD/Jason
   assignments through the supported Staff & Departments UI.
5. **Role and denial matrix:** verify Principal/Deputy school scope, HOD department
   scope, teacher assignment scope, unauthorised direct identifiers, unrelated
   departments and cross-school denial.
6. **State-changing messaging journey:** with the approved demo accounts, accept
   the safeguarding warning once, reload to prove persistence, send one staff
   message/attachment, generate one report/certificate, share it to the exact linked
   parent and verify protected download. Confirm no acknowledgement re-prompt for
   the unchanged policy version.
7. **Promotion decision:** review the resulting evidence and only then promote the
   accepted FHH development commit to production/build a release APK. Production is
   not part of the current authority.

## Resolved development release check

The reported FHH mobile-header collision, duplicated School Chats destination
and unlinked-parent Survey exposure were fixed in development at `d0121b7`.
Focused automated checks passed and the user physically accepted the mobile
header and unlinked-parent behaviour on 2026-08-07. The Android shell and a
linked-parent EN/AR pass remain part of final UAT before production promotion.

## Rollback

- Stop the rollout if migrations, health checks, exact-child scope or private CHH/FHH authentication fail.
- Prefer restoring the verified pre-release database backup and redeploying the previously recorded server commits over improvising live data repairs.
- Retain the local baseline tags and the backup paths/checksums in `PRE_CEO_DEMO_RESULT.md`.
- Do not reverse the already completed manifest-proven seed cleanup without restoring its recorded pre-operation CHH dump; that operation is separately documented and recoverable only from the verified backup.

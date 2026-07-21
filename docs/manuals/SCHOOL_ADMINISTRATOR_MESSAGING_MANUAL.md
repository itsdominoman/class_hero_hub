# School administrator messaging manual

## Account and staff governance

The first active school administrator becomes the explicit **System Owner**. Additional administrators do not inherit ownership. The owner can invite teachers/admins, assign explicit roles and safeguarding permissions, approve retention jobs, and transfer ownership with confirmation and a reason. Former owners keep only their other assigned roles/grants. If the owner is inactive, a platform administrator must use the audited emergency recovery flow.

Keep staff memberships current. Transfer ownership before deactivating the owner. Remove obsolete roles and grants rather than sharing accounts. Dual-role staff must use the correct membership context.

## School policy controls

- Contact hours delay eligible notifications only.
- Read-receipt visibility and urgent marking follow the versioned messaging policy.
- Retention has a separate versioned policy with an effective date.
- Run and review a retention preview before execution; confirm the exact preview hash.
- Legal-hold reasons are confidential and belong only in the protected hold workflow.

Use **School > Governance** for owner state and **School > Operations** for school-scoped health. These pages do not reveal cross-school metrics, tokens, message bodies, internal notes, credentials, or legal-hold reasons.

## Monthly checks

Review the active owner, administrators, safeguarding grants, dead jobs, worker heartbeat, oldest backlog, archive disk usage, backup marker, and retention policy. Escalate any dead-letter count, stale worker, failed export, archive hash mismatch, backup older than the runbook threshold, or unexplained access denial burst.

Arabic publication needs: formally agree the terms for System Owner, administrator, legal hold, retention, safeguarding, and chain of custody.

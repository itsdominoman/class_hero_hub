# Retention and legal-hold policy guide

## Default pilot baseline

These defaults are conservative technical settings, not legal advice: message/photo/voice/receipts 2,557 days; notification history 365 days; safeguarding audit, moderation, internal notes, reviews and export metadata 3,650 days; export artifact 30 minutes; revoked device registrations 90 days; replay assertions 30 days; operations jobs 365 days; operational logs 90 days. Eligible media moves from hot storage after 365 days and the hot source is deleted only after a verified archive copy. Schools must align values with local policy, contracts, regulator expectations, litigation/preservation duties, and applicable law.

Policies are school-scoped, append-only versions with effective dates, acknowledgement, actor, and reason. A new policy does not silently dispose content. The System Owner requests a dry-run; CHH reports candidate counts/bytes and a preview SHA-256. Execution requires the same active policy, completed preview ID, and exact hash. Batches recheck legal holds and active safeguarding review/export state.

## Legal holds

A permitted user can hold a conversation, selected message, or student-linked history with a reason, start date, optional review date, and optional case reference. Placement and release events are append-only. A release requires a new reason. Hold reasons never enter ordinary participant or FHH projections. Holds override destructive retention for covered message evidence and related records; policy owners should preserve external case authority separately.

## Approval checklist

- school policy owner and System Owner identified;
- retention values and effective date reviewed;
- legal counsel/privacy/safeguarding review obtained where required;
- backup/restore rehearsal current;
- preview reviewed for unexpected counts/bytes;
- active holds/reviews/exports checked;
- exact preview hash confirmed;
- operations and incident contacts ready;
- post-run counts, failures and sample evidence verified.

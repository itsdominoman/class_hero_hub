# CHH school feature entitlements

The `school_entitlements` table is the canonical authority for optional Class Hero Hub capabilities. A missing, disabled, not-yet-effective or expired row means the capability is unavailable. New schools therefore begin with foundation administration only; the migration backfills every school that already exists at deployment with every optional capability enabled as a `pilot` grant so the pilot loses no working feature.

Foundation capabilities are identity and access, school structure, people and assignments, security and auditing, and read-only entitlement visibility. Optional capabilities are:

- homework and diary;
- notices and calendar;
- behaviour and points, with positive recognition dependent on it;
- surveys and polls;
- school chats, with chat photos and voice notes dependent on it;
- Family Hero Hub connection, with school-family updates dependent on it and update photos dependent on those updates;
- reports and insights;
- safeguarding; and
- student/staff import and export.

Dependencies are fail-closed at read time as well as when a grant is changed. Safeguarding is deliberately independent from participant chat availability so authorised historical safety review is not coupled to ordinary messaging. The Family Hero Hub proxy requires both the family connection and the relevant content capability. Family notification, point-summary, messaging notification and messaging production workers revalidate current entitlements before work or delivery. Protected photo and voice downloads repeat their corresponding media entitlement checks.

Only an active `platform_admins` row with `manage_school_entitlements=true` may use the platform entitlement API and editor. The bootstrap migration assigns that stored authority only to Dom's existing verified, non-revoked platform account. Runtime authorisation never compares an email address. School administrators have a read-only view with source and effective dates; internal notes and actor details remain platform-only.

Every change uses optimistic `entitlement_version` concurrency, validates dependency and date-window containment, updates the canonical row in a transaction, appends a full `school_entitlement_events` snapshot, and writes the ordinary audit log. Event rows are append-only. No entitlement mutation is exposed to school staff or FHH.

Operationally, distinguish these layers:

1. the entitlement decides whether a school owns a capability;
2. an operational policy or compliance switch may further restrict an owned capability; and
3. role, assignment, guardian-link and safeguarding permissions decide who may act within it.

Changing an operational switch cannot grant an unentitled capability. Existing school-administrator messaging, voice-note and related operational controls remain in their established locations. Their saved values remain readable but the controls are visibly disabled, and write APIs return the stable `capability_not_enabled` error while the required entitlement is unavailable. Entitlement changes never rewrite or default these operational rows; once a capability is restored, the preserved school choice governs it again.

Disabling an entitlement removes ordinary feature navigation and action controls, suppresses protected feature data, family payload categories and worker delivery, and does not delete historical records or operational configuration. Use the Dom-only platform school page for entitlement changes; do not edit entitlement rows manually.

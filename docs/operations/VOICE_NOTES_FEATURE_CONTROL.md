# Voice notes: Compliance / Feature Controls

Voice notes are default-off per school even when Messaging v1 is globally enabled.
Only an active `school_admin` may change the control. Enabling requires the current
disclosure version `voice-notes-2026-07-v1`, an explicit acknowledgement and the
expected control version, preventing stale concurrent updates. Disabling is immediate.

The enabling administrator confirms that the school has completed its own review of:

- applicable law and school policy;
- guardian notice/consent where required;
- acceptable-use rules for staff, guardians and students;
- safeguarding, moderation, escalation and incident handling;
- retention, deletion, access/export and backup handling; and
- accessibility and an alternative channel for people who cannot use audio.

CHH provides technical controls and protected delivery; the school remains responsible
for the lawful and appropriate use of recordings. The UI states this shared
responsibility and blocks enablement until acknowledged.

Every effective change writes an immutable event containing school, feature, prior and
new state/version, disclosure version, acknowledgement flag, acknowledging user and
membership, timestamp and safe request context. PostgreSQL rejects update/delete of
these events. The ordinary school audit log also records the control change. Secrets,
audio content and storage paths are never audit fields.

Operational rules:

1. Confirm the exact school and a real active school-admin membership.
2. Review the disclosure with that administrator; never enable by copying another
   school's row.
3. Enable through the versioned control API/UI so both audit records are created.
4. Verify only the approved school is enabled. Absence of a row means disabled.
5. To halt new voice notes, disable the switch. Existing notes remain available only
   to currently authorized conversation participants so records are not stranded.
6. A disclosure revision requires a new disclosure constant and re-acknowledgement
   design; do not rewrite historical events.

The 2026-07-18 development pilot authorizes only United International School. All
other development schools and every production school remain off.


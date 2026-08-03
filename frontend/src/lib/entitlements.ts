import type { SessionMembership } from '$lib/roleRouting';

export const OPTIONAL_CAPABILITIES = [
  'homework_diary',
  'notices_calendar',
  'behaviour_points',
  'positive_recognition',
  'surveys_polls',
  'school_chats',
  'chat_photos',
  'voice_notes',
  'family_connection',
  'school_family_updates',
  'update_photos',
  'reports_insights',
  'safeguarding',
  'student_staff_import_export'
] as const;

export type CapabilityKey = (typeof OPTIONAL_CAPABILITIES)[number];
export type EntitlementSource = 'pilot' | 'trial' | 'paid' | 'complimentary';

export type SchoolEntitlement = {
  capability: CapabilityKey;
  enabled: boolean;
  effective_enabled: boolean;
  source: EntitlementSource | null;
  effective_from: string | null;
  expires_on: string | null;
  dependencies: CapabilityKey[];
  entitlement_version: number | null;
  internal_note?: string | null;
  last_changed_at?: string | null;
  last_actor?: { id: number; name: string; email: string } | null;
};

export type SchoolEntitlementPayload = {
  school: { id: number; name: string; name_ar?: string | null };
  foundation: string[];
  entitlements: SchoolEntitlement[];
};

export function entitlementStatus(entitlement: SchoolEntitlement): 'enabled' | 'disabled' | 'scheduled' | 'expired' {
  if (entitlement.effective_enabled) return 'enabled';
  if (!entitlement.enabled) return 'disabled';
  const today = new Date().toISOString().slice(0, 10);
  if (entitlement.effective_from && entitlement.effective_from > today) return 'scheduled';
  return 'expired';
}

export function membershipHasCapability(
  membership: Pick<SessionMembership, 'capabilities'> | null | undefined,
  capability: CapabilityKey
): boolean {
  return Boolean(membership?.capabilities?.includes(capability));
}

export function anyMembershipHasCapability(
  memberships: SessionMembership[] | null | undefined,
  capability: CapabilityKey,
  role?: string
): boolean {
  return Boolean(memberships?.some(
    (membership) => (!role || membership.role === role) && membershipHasCapability(membership, capability)
  ));
}

export function capabilityForRoute(pathname: string, search: string): CapabilityKey | null {
  if (pathname.startsWith('/messages')) return 'school_chats';
  if (pathname.startsWith('/school/surveys')) return 'surveys_polls';
  if (pathname.startsWith('/school/reports')) return 'reports_insights';
  if (pathname.startsWith('/school/recognition')) return 'positive_recognition';
  if (pathname.startsWith('/school/safeguarding')) return 'safeguarding';
  if (pathname.startsWith('/school/students/data')) return 'student_staff_import_export';
  if (pathname.startsWith('/parent')) return 'family_connection';
  if (pathname === '/school') {
    const tab = new URLSearchParams(search).get('tab');
    if (tab === 'announcements' || tab === 'calendar') return 'notices_calendar';
    if (tab === 'behaviour') return 'behaviour_points';
  }
  return null;
}

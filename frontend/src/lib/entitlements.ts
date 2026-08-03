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

export type EntitlementRelationshipBlock = {
  reason: 'enabled_dependents' | 'missing_dependencies' | 'dependency_window';
  capability: CapabilityKey;
  related: CapabilityKey[];
};

export function isCapabilityKey(value: unknown): value is CapabilityKey {
  return typeof value === 'string' && OPTIONAL_CAPABILITIES.includes(value as CapabilityKey);
}

export function capabilityDependents(
  entitlements: SchoolEntitlement[],
  capability: CapabilityKey
): CapabilityKey[] {
  return entitlements
    .filter((entitlement) => entitlement.dependencies.includes(capability))
    .map((entitlement) => entitlement.capability);
}

function windowContains(parent: SchoolEntitlement, child: SchoolEntitlement): boolean {
  if (!parent.effective_from || !child.effective_from) return true;
  if (parent.effective_from > child.effective_from) return false;
  if (!child.expires_on) return !parent.expires_on;
  return !parent.expires_on || parent.expires_on >= child.expires_on;
}

export function entitlementRelationshipBlock(
  entitlements: SchoolEntitlement[],
  draft: SchoolEntitlement
): EntitlementRelationshipBlock | null {
  const byCapability = new Map(entitlements.map((entitlement) => [entitlement.capability, entitlement]));
  byCapability.set(draft.capability, draft);

  if (!draft.enabled) {
    const enabledDependents = capabilityDependents(entitlements, draft.capability).filter(
      (capability) => byCapability.get(capability)?.enabled
    );
    return enabledDependents.length
      ? { reason: 'enabled_dependents', capability: draft.capability, related: enabledDependents }
      : null;
  }

  const missingDependencies = draft.dependencies.filter(
    (capability) => !byCapability.get(capability)?.enabled
  );
  if (missingDependencies.length) {
    return { reason: 'missing_dependencies', capability: draft.capability, related: missingDependencies };
  }

  const invalidDependencies = draft.dependencies.filter((capability) => {
    const dependency = byCapability.get(capability);
    return Boolean(dependency && !windowContains(dependency, draft));
  });
  if (invalidDependencies.length) {
    return { reason: 'dependency_window', capability: draft.capability, related: invalidDependencies };
  }

  for (const dependentKey of capabilityDependents(entitlements, draft.capability)) {
    const dependent = byCapability.get(dependentKey);
    if (dependent?.enabled && !windowContains(draft, dependent)) {
      return { reason: 'dependency_window', capability: dependentKey, related: [draft.capability] };
    }
  }

  return null;
}

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
  if (pathname === '/school') {
    const tab = new URLSearchParams(search).get('tab');
    if (tab === 'announcements' || tab === 'calendar') return 'notices_calendar';
    if (tab === 'behaviour') return 'behaviour_points';
  }
  return null;
}

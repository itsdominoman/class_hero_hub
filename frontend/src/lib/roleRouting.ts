export type SessionMembership = {
  membership_id: number;
  role: string;
  school_id: number;
  school_name: string;
  capabilities: string[];
};

export type SessionUser = {
  is_platform_admin?: boolean;
  can_manage_school_entitlements?: boolean;
  memberships?: SessionMembership[];
};

export function hasRole(user: SessionUser | null | undefined, role: string): boolean {
  return Boolean(user?.memberships?.some((membership) => membership.role === role));
}

// Class Hero Hub is a staff workspace. Family access is provided only through
// Family Hero Hub, so a guardian-only legacy account is sent to the public
// family-connection explanation instead of a CHH parent dashboard.
export function defaultLandingPath(user: SessionUser | null | undefined): string {
  if (!user) return '/login';
  if (hasRole(user, 'teacher')) return '/teach';
  if (hasRole(user, 'school_admin')) return '/school';
  if (user.is_platform_admin) return '/platform';
  return '/family-connection';
}

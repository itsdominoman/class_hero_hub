export type SessionMembership = {
  membership_id: number;
  role: string;
  school_id: number;
  school_name: string;
};

export type SessionUser = {
  is_platform_admin?: boolean;
  memberships?: SessionMembership[];
};

export function hasRole(user: SessionUser | null | undefined, role: string): boolean {
  return Boolean(user?.memberships?.some((membership) => membership.role === role));
}

// Priority mirrors pre-S10 behaviour: staff roles keep landing on their own
// workspace by default; only a guardian-only (or role-less) account lands on
// the guardian dashboard. Multi-role accounts still get an explicit Family
// nav link even though this isn't their default landing page.
export function defaultLandingPath(user: SessionUser | null | undefined): string {
  if (!user) return '/login';
  if (hasRole(user, 'teacher')) return '/teach';
  if (hasRole(user, 'school_admin')) return '/school';
  if (user.is_platform_admin) return '/platform';
  return '/parent';
}

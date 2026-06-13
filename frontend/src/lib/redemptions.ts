// Shared ordering for reward (redemption) requests.
//
// Pending requests come first, most-recently-requested on top, so a parent
// always sees what still needs a decision. Resolved requests (approved /
// rejected) follow, most-recently-reviewed on top (falling back to when they
// were created if a review timestamp is missing).

export type RedemptionLike = {
  status?: string;
  created_at?: string | null;
  reviewed_at?: string | null;
};

function time(value?: string | null): number {
  if (!value) return 0;
  const ms = new Date(value).getTime();
  return Number.isNaN(ms) ? 0 : ms;
}

function resolvedTime(request: RedemptionLike): number {
  // Prefer the review time for resolved items; fall back to creation time.
  return time(request.reviewed_at) || time(request.created_at);
}

export function sortRedemptions<T extends RedemptionLike>(requests: T[]): T[] {
  return [...requests].sort((a, b) => {
    const aPending = a.status === 'pending';
    const bPending = b.status === 'pending';
    if (aPending !== bPending) return aPending ? -1 : 1;
    if (aPending) {
      // Both pending: newest request first.
      return time(b.created_at) - time(a.created_at);
    }
    // Both resolved: most recently reviewed first.
    return resolvedTime(b) - resolvedTime(a);
  });
}

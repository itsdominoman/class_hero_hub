import { safeguardingApi } from "./api";
import type { SafeguardingContext, SafeguardingMembership } from "./types";
import type { SessionUser } from "$lib/roleRouting";

export type EligibleSafeguardingMembership = {
  membership: SafeguardingMembership;
  context: SafeguardingContext;
};

export async function findEligibleSafeguardingMemberships(
  user: SessionUser,
): Promise<EligibleSafeguardingMembership[]> {
  const candidates = (user.memberships || []).filter(
    (row) =>
      Number.isInteger(row.membership_id) && Number.isInteger(row.school_id),
  );
  const eligible: EligibleSafeguardingMembership[] = [];
  for (const candidate of candidates) {
    try {
      const availability = await safeguardingApi.availability(candidate);
      if (!availability.available) continue;
      eligible.push({
        membership: candidate,
        context: await safeguardingApi.context(candidate),
      });
    } catch {
      // Denied membership contexts intentionally disappear from safeguarding navigation.
    }
  }
  return eligible;
}

export function requestedMembershipId(url: URL): number | null {
  const value = Number(url.searchParams.get("membership"));
  return Number.isInteger(value) && value > 0 ? value : null;
}

export function membershipHref(
  path: string,
  membership: SafeguardingMembership,
): string {
  const query = new URLSearchParams({
    membership: String(membership.membership_id),
  });
  return `${path}?${query}`;
}

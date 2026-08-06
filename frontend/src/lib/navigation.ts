export const GLOBAL_NAVIGATION_ORDER = [
  "platform",
  "school",
  "teach",
  "messages",
  "surveys",
  "reports",
  "system",
  "safeguarding",
  "dashboard",
] as const;

export type GlobalNavigationItemId = (typeof GLOBAL_NAVIGATION_ORDER)[number];

function matchesPath(pathname: string, route: string) {
  return pathname === route || pathname.startsWith(`${route}/`);
}

export function activeNavigationItem(
  pathname: string,
): GlobalNavigationItemId | null {
  if (matchesPath(pathname, "/school/reports")) return "reports";
  if (matchesPath(pathname, "/school/surveys")) return "surveys";
  if (matchesPath(pathname, "/school/safeguarding")) return "safeguarding";
  if (
    [
      "/school/administration",
      "/school/governance",
    ].some((route) => matchesPath(pathname, route))
  )
    return "system";
  if (matchesPath(pathname, "/messages")) return "messages";
  if (matchesPath(pathname, "/teach")) return "teach";
  if (matchesPath(pathname, "/platform")) return "platform";
  if (matchesPath(pathname, "/school")) return "school";
  return null;
}

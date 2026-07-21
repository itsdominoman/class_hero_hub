export const SAFEGUARDING_PERMISSIONS = [
  "messaging.safeguarding_review",
  "messaging.moderate",
  "messaging.export_evidence",
  "messaging.export_internal_notes",
  "messaging.manage_safeguarding_permissions",
  "messaging.manage_legal_holds",
] as const;

export type SafeguardingPermission = (typeof SAFEGUARDING_PERMISSIONS)[number];

const permissionKeys: Record<string, string> = {
  "messaging.safeguarding_review": "review",
  "messaging.moderate": "moderate",
  "messaging.export_evidence": "exportEvidence",
  "messaging.export_internal_notes": "exportNotes",
  "messaging.manage_safeguarding_permissions": "manage",
  "messaging.manage_legal_holds": "legalHolds",
};

const roleKeys: Record<string, string> = {
  teacher: "teacher",
  staff: "staff",
  school_admin: "schoolAdmin",
  chh_guardian: "guardian",
  fhh_parent: "guardian",
  guardian: "guardian",
};

const conversationKeys: Record<string, string> = {
  student_staff: "studentStaff",
  guardian_direct: "familySchool",
  staff_direct: "staffConversation",
};

export function permissionLabelKey(value: string): string {
  return `safeguarding.permissionLabels.${permissionKeys[value] ?? "unknown"}`;
}

export function permissionDescriptionKey(value: string): string {
  return `safeguarding.permissionDescriptions.${permissionKeys[value] ?? "unknown"}`;
}

export function roleLabelKey(value: string | null | undefined): string {
  return `safeguarding.roles.${roleKeys[value ?? ""] ?? "staff"}`;
}

export function conversationKindLabelKey(value: string): string {
  return `safeguarding.conversationKinds.${conversationKeys[value] ?? "other"}`;
}

export function stateLabelKey(value: string | null | undefined): string {
  const normalized = value === "archived" ? "closed" : value || "active";
  return `safeguarding.states.${normalized}`;
}

export function messageTypeLabelKey(value: string): string {
  return `safeguarding.messageTypes.${value}`;
}

export function directionLabelKey(value: string): string {
  return `safeguarding.directions.${value}`;
}

export function restrictionLabelKey(value: string): string {
  return `safeguarding.restrictions.${value}`;
}

export function severityLabelKey(value: string): string {
  return `safeguarding.severities.${value}`;
}

export function flagStatusLabelKey(value: string): string {
  return `safeguarding.flagStatuses.${value}`;
}

export function accessSummaryKey(permissions: readonly string[]): string {
  if (
    SAFEGUARDING_PERMISSIONS.every((permission) =>
      permissions.includes(permission),
    )
  ) {
    return "safeguarding.accessLevels.full";
  }
  if (permissions.includes("messaging.manage_safeguarding_permissions")) {
    return "safeguarding.accessLevels.manager";
  }
  if (permissions.includes("messaging.moderate"))
    return "safeguarding.accessLevels.reviewModerate";
  if (permissions.includes("messaging.safeguarding_review"))
    return "safeguarding.accessLevels.review";
  return "safeguarding.accessLevels.limited";
}

export function normalizeJustification(value: string): string {
  return (value || "").trim().replace(/\s+/g, " ");
}

export function isMeaningfulJustification(
  value: string,
  minimum = 15,
): boolean {
  const normalized = normalizeJustification(value);
  const meaningful = Array.from(normalized).filter((character) =>
    /[\p{L}\p{N}]/u.test(character),
  );
  return (
    normalized.length >= minimum &&
    meaningful.length >= 8 &&
    new Set(meaningful.map((character) => character.toLocaleLowerCase()))
      .size >= 3
  );
}

export function friendlyTechnicalLabel(value: unknown): string {
  return String(value ?? "")
    .replace(/^safeguarding[._]/, "")
    .replace(/[._-]+/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

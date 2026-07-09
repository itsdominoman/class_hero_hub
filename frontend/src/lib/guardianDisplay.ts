export type GuardianDisplaySource = {
  slot?: number | null;
  name?: string | null;
  relationship?: string | null;
  display_name?: string | null;
  user_name?: string | null;
};

export function guardianDisplayName(source: GuardianDisplaySource, fallback: string): string {
  const primary = source.name || source.display_name || source.user_name || fallback;
  return [primary, source.relationship].filter(Boolean).join(' · ');
}

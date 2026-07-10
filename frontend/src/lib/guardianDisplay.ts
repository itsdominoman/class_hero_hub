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

// Initials remain the safe fallback when an assigned avatar is missing or
// its static asset cannot be loaded.
export function initialsFromStudentName(student: { first_name?: string | null; last_name?: string | null }): string {
  const parts = [student.first_name, student.last_name].filter(Boolean).map((part) => (part as string)[0]);
  return (parts.join('').toUpperCase() || '?').slice(0, 2);
}

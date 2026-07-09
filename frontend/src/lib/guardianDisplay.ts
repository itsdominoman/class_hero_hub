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

// TODO(S10+): initials are a placeholder avatar. Replace with the real
// non-human hero avatar system when it lands; keep this the single place
// student avatar initials are derived so the swap only touches one file.
export function initialsFromStudentName(student: { first_name?: string | null; last_name?: string | null }): string {
  const parts = [student.first_name, student.last_name].filter(Boolean).map((part) => (part as string)[0]);
  return (parts.join('').toUpperCase() || '?').slice(0, 2);
}

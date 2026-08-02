export type TeacherClassAssignment = {
  id: number;
  role: string;
  school: { name: string; name_ar?: string | null };
  class_section?: { name?: string | null; name_ar?: string | null; code?: string | null } | null;
  subject_group?: { name?: string | null; name_ar?: string | null; code?: string | null } | null;
  branch?: { name?: string | null; name_ar?: string | null } | null;
  grade_level?: { name?: string | null; name_ar?: string | null } | null;
  subject?: { name?: string | null; name_ar?: string | null } | null;
};

export type SubjectPalette = {
  background: string;
  border: string;
  accent: string;
};

export type TeacherClassGroup<T extends TeacherClassAssignment> = {
  key: string;
  label: string;
  homeroom: boolean;
  palette: SubjectPalette;
  assignments: T[];
};

type AcademicKey = {
  stage: number;
  grade: number;
  section: string;
  fallback: string;
};

const namedPalettes: Record<string, SubjectPalette> = {
  homeroom: { background: '#fff1ed', border: '#fdc9bb', accent: '#d95d43' },
  arabic: { background: '#fff8e6', border: '#f1d99a', accent: '#a66a00' },
  english: { background: '#eef6ff', border: '#bfdcff', accent: '#2878b9' },
  maths: { background: '#f5f0ff', border: '#d8c5ff', accent: '#7852ba' },
  science: { background: '#eef9f1', border: '#bde5c8', accent: '#2d8050' },
  pe: { background: '#fff3e8', border: '#f5cfaa', accent: '#c56720' },
  ict: { background: '#eafafa', border: '#afe2e4', accent: '#167b83' }
};

const neutralPalettes: SubjectPalette[] = [
  { background: '#f5f7fa', border: '#d7dde5', accent: '#5f6d7c' },
  { background: '#f4f7f2', border: '#d1ddcb', accent: '#607558' },
  { background: '#faf5f1', border: '#e5d4c7', accent: '#856957' },
  { background: '#f7f4f8', border: '#ddd2e1', accent: '#76617d' }
];

function normalized(value?: string | null) {
  return (value || '').normalize('NFKC').trim().replace(/\s+/g, ' ');
}

function localizedName(value: { name?: string | null; name_ar?: string | null } | null | undefined, locale: string) {
  return normalized(locale === 'ar' && value?.name_ar ? value.name_ar : value?.name);
}

function normalizedDigits(value: string) {
  return value
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)));
}

function collator(locale: string) {
  return new Intl.Collator(locale || 'en', { numeric: true, sensitivity: 'base' });
}

function parseAcademicValue(value?: string | null) {
  const label = normalizedDigits(normalized(value));
  if (!label) return null;

  const kg = label.match(/(?:^|\s)(?:kg|kindergarten|روضة|الروضة)\s*[-_/ ]?\s*(\d{1,2})(?:\s*[-_/ ]?\s*([a-z]))?(?:\b|$)/i);
  if (kg) return { stage: 0, grade: Number(kg[1]), section: (kg[2] || '').toUpperCase() };

  const grade = label.match(/(?:^|\s)(?:grade|year|g|الصف)\s*[-_/ ]?\s*(\d{1,2})(?:\s*[-_/ ]?\s*([a-z]))?(?:\b|$)/i);
  if (grade) return { stage: 1, grade: Number(grade[1]), section: (grade[2] || '').toUpperCase() };

  const bare = label.match(/^(\d{1,2})(?:\s*[-_/ ]?\s*([a-z]))?$/i);
  if (bare) return { stage: 1, grade: Number(bare[1]), section: (bare[2] || '').toUpperCase() };
  return null;
}

function sectionValue(value?: string | null) {
  const label = normalized(value);
  if (!label) return '';
  const parsed = parseAcademicValue(label);
  if (parsed?.section) return parsed.section;
  const withoutPrefix = label.replace(/^(?:class|section|الشعبة)\s*[-:]*\s*/i, '');
  if (/^[a-z]$/i.test(withoutPrefix)) return withoutPrefix.toUpperCase();
  if (parsed) return '';
  return withoutPrefix;
}

function academicKey(card: TeacherClassAssignment): AcademicKey {
  const candidates = [
    card.grade_level?.name,
    card.class_section?.name,
    card.class_section?.code,
    card.subject_group?.code,
    card.subject_group?.name
  ];
  const parsed = candidates.map(parseAcademicValue).find(Boolean);
  const sectionCandidates = [
    card.class_section?.name,
    card.class_section?.code,
    parsed?.section,
    card.subject_group?.code,
    card.subject_group?.name
  ];
  const section = sectionCandidates.map(sectionValue).find(Boolean) || '';
  return {
    stage: parsed?.stage ?? 2,
    grade: parsed?.grade ?? Number.MAX_SAFE_INTEGER,
    section,
    fallback: normalized(candidates.find(Boolean))
  };
}

function compareSection(left: string, right: string, locale: string) {
  const priority = (value: string) => {
    const upper = value.toUpperCase();
    if (upper === 'A') return 0;
    if (upper === 'B') return 1;
    if (upper === 'C') return 2;
    if (value) return 3;
    return 4;
  };
  return priority(left) - priority(right) || collator(locale).compare(left, right);
}

export function compareTeacherClasses(
  left: TeacherClassAssignment,
  right: TeacherClassAssignment,
  locale = 'en'
) {
  const leftKey = academicKey(left);
  const rightKey = academicKey(right);
  return (
    leftKey.stage - rightKey.stage ||
    leftKey.grade - rightKey.grade ||
    compareSection(leftKey.section, rightKey.section, locale) ||
    collator(locale).compare(localizedName(left.branch, locale), localizedName(right.branch, locale)) ||
    collator(locale).compare(localizedName(left.school, locale), localizedName(right.school, locale)) ||
    collator(locale).compare(leftKey.fallback, rightKey.fallback) ||
    left.id - right.id
  );
}

function stripAcademicContext(value: string) {
  const academic = '(?:(?:kg|kindergarten|grade|year|g|روضة|الروضة|الصف)\\s*[-_/ ]?\\s*\\d{1,2}(?:\\s*[-_/ ]?\\s*[a-z])?|\\d{1,2}[a-z]?)';
  return value
    .replace(new RegExp(`^${academic}\\s*[-·:|/]*\\s*`, 'i'), '')
    .replace(new RegExp(`\\s*[-·:|/]*\\s*${academic}$`, 'i'), '')
    .trim();
}

export function subjectLabel(
  card: TeacherClassAssignment,
  homeroomLabel: string,
  subjectFallback: string,
  locale = 'en'
) {
  if (card.role === 'homeroom') return homeroomLabel;
  const explicitSubject = localizedName(card.subject, locale);
  if (explicitSubject) return explicitSubject;
  const groupLabel = localizedName(card.subject_group, locale) || normalized(card.subject_group?.code);
  return stripAcademicContext(groupLabel) || groupLabel || subjectFallback;
}

export function classLabel(card: TeacherClassAssignment, locale = 'en') {
  const localizedClass = locale === 'ar'
    ? localizedName(card.class_section, locale) || localizedName(card.subject_group, locale)
    : '';
  if (localizedClass) return localizedClass;
  const key = academicKey(card);
  if (key.stage < 2) {
    const grade = `${key.stage === 0 ? 'KG' : 'G'}${key.grade}`;
    if (!key.section) return grade;
    return /^[A-C]$/i.test(key.section) ? `${grade}${key.section.toUpperCase()}` : `${grade} · ${key.section}`;
  }
  return normalized(
    card.class_section?.name ||
      card.class_section?.code ||
      card.subject_group?.name ||
      card.subject_group?.code
  );
}

function paletteName(subject: string) {
  const value = normalized(subject).toLocaleLowerCase();
  if (/^(arabic|العربية|اللغة العربية)$/.test(value)) return 'arabic';
  if (/^(english|الإنجليزية|اللغة الإنجليزية)$/.test(value)) return 'english';
  if (/^(math|maths|mathematics|الرياضيات)$/.test(value)) return 'maths';
  if (/^(science|العلوم)$/.test(value)) return 'science';
  if (/^(pe|p\.e\.|physical education|sport|sports|التربية البدنية|رياضة)$/.test(value)) return 'pe';
  if (/^(ict|computing|computer science|information technology|الحاسوب|تكنولوجيا المعلومات)$/.test(value)) return 'ict';
  return '';
}

export function subjectPalette(subject: string, homeroom = false) {
  if (homeroom) return namedPalettes.homeroom;
  const name = paletteName(subject);
  if (name) return namedPalettes[name];
  const hash = Array.from(normalized(subject)).reduce((value, character) => ((value * 31) + character.codePointAt(0)!) >>> 0, 7);
  return neutralPalettes[hash % neutralPalettes.length];
}

export function groupTeacherClasses<T extends TeacherClassAssignment>(
  assignments: T[],
  locale: string,
  homeroomLabel: string,
  subjectFallback: string
): TeacherClassGroup<T>[] {
  const groups = new Map<string, TeacherClassGroup<T>>();
  for (const assignment of assignments) {
    const homeroom = assignment.role === 'homeroom';
    const label = subjectLabel(assignment, homeroomLabel, subjectFallback, locale);
    const key = homeroom ? '__homeroom__' : normalized(label).toLocaleLowerCase(locale || 'en');
    const existing = groups.get(key);
    if (existing) existing.assignments.push(assignment);
    else groups.set(key, { key, label, homeroom, palette: subjectPalette(label, homeroom), assignments: [assignment] });
  }

  const languageCollator = collator(locale);
  return Array.from(groups.values())
    .sort((left, right) => Number(right.homeroom) - Number(left.homeroom) || languageCollator.compare(left.label, right.label))
    .map((group) => ({ ...group, assignments: [...group.assignments].sort((left, right) => compareTeacherClasses(left, right, locale)) }));
}

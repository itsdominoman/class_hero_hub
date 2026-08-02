import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { ar, en } from '../src/lib/i18n/messages.ts';

const read = (relative) => readFileSync(new URL(`../${relative}`, import.meta.url), 'utf8');
const school = read('src/routes/school/+page.svelte');
const api = read('src/lib/api.ts');

test('school checklist and backend result values use stable translation keys', () => {
  assert.match(school, /function checklistLabel/);
  assert.match(school, /school\.checklistItems\.\$\{item\.key\}/);
  assert.match(school, /<h2 class="font-bold text-slate-900">\{checklistLabel\(item\)\}<\/h2>/);
  assert.doesNotMatch(school, /<h2 class="font-bold text-slate-900">\{item\.label\}<\/h2>/);
  assert.match(school, /systemValue\('school\.sendStatuses', invite\.send_status\)/);
  assert.match(school, /systemValue\('school\.resultStatuses', item\.status\)/);
  assert.match(school, /function resultReason/);
  assert.equal(ar.school.checklistItems.settings, 'إعدادات المدرسة');
  assert.equal(ar.school.checklistItems.grade_levels, 'الصفوف/المستويات الدراسية');
  assert.equal(en.school.checklistItems.settings, 'School settings');
});

test('Arabic API errors cannot expose an English backend fallback', () => {
  assert.match(api, /function localizedApiError/);
  assert.match(api, /get\(locale\) === 'ar'/);
  assert.match(api, /get\(_\)\('common\.requestFailed'\)/);
  assert.equal(ar.common.requestFailed, 'تعذر إكمال الطلب. يُرجى المحاولة مرة أخرى.');
});

test('school-owned statuses and bilingual records are locale aware', () => {
  const rows = read('src/lib/components/school/RowsTable.svelte');
  const select = read('src/lib/components/school/SelectInput.svelte');
  assert.match(rows, /function statusLabel/);
  assert.match(rows, /\$locale === 'ar' \? \$_\(`school\.\$\{status\}`\) : status/);
  assert.match(select, /\$locale === 'ar' && row\.name_ar/);
  assert.match(school, /function localizedRowName/);
  assert.equal(ar.school.active, 'نشط');
  assert.equal(ar.school.inactive, 'غير نشط');
  assert.equal(ar.school.archived, 'مؤرشف');
});

test('directional controls use RTL-aware icons and logical positioning', () => {
  const paths = [
    'src/routes/school/administration/+page.svelte',
    'src/routes/school/recognition/+page.svelte',
    'src/routes/school/reports/+page.svelte',
    'src/routes/school/students/+page.svelte',
    'src/routes/teach/+page.svelte',
    'src/routes/teach/assignments/[id]/+page.svelte',
    'src/lib/components/messaging/ProtectedPhotoViewer.svelte'
  ];
  for (const path of paths) assert.match(read(path), /rtl:(?:-scale-x-100|rotate-180)/, path);
  const viewer = read('src/lib/components/messaging/ProtectedPhotoViewer.svelte');
  assert.match(viewer, /absolute start-3/);
  assert.match(viewer, /absolute end-3/);
  assert.match(viewer, /event\.key === 'ArrowLeft'.*\$locale === 'ar'/);
});

test('Arabic catalogue does not expose development TODO markers', () => {
  const arabicValues = [];
  const walk = (value) => {
    if (typeof value === 'string') arabicValues.push(value);
    else if (value && typeof value === 'object') Object.values(value).forEach(walk);
  };
  walk(ar);
  assert.equal(arabicValues.some((value) => value.includes('TODO')), false);
});

test('system dates, times and report numbers follow the active Arabic locale', () => {
  const localeAwareFiles = [
    'src/routes/platform/+page.svelte',
    'src/routes/platform/[id]/+page.svelte',
    'src/routes/parent/+page.svelte',
    'src/routes/school/+page.svelte',
    'src/routes/school/reports/+page.svelte',
    'src/routes/school/students/+page.svelte',
    'src/routes/teach/+page.svelte',
    'src/routes/teach/assignments/[id]/+page.svelte',
    'src/lib/components/messaging/InboxList.svelte',
    'src/lib/components/messaging/ConversationPane.svelte'
  ];
  for (const path of localeAwareFiles) {
    const source = read(path);
    assert.doesNotMatch(source, /Intl\.(?:DateTime|Number)Format\(undefined/, path);
    assert.doesNotMatch(source, /\.toLocale(?:Date)?String\(\)/, path);
  }
  assert.match(read('src/routes/platform/+page.svelte'), /\$locale === 'ar' \? 'ar' : undefined/);
  assert.match(read('src/routes/school/reports/+page.svelte'), /new Intl\.NumberFormat\(\$locale === 'ar'/);
  assert.equal(en.school.recordCount, '{count} records');
  assert.equal(ar.school.recordCount, 'عدد السجلات: {count}');
});

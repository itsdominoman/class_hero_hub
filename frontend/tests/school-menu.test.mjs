import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { en, ar } from '../src/lib/i18n/messages.ts';
import { SCHOOL_MENU_GROUPS, SCHOOL_TABS } from '../src/lib/schoolMenu.ts';

const schoolSource = readFileSync(new URL('../src/routes/school/+page.svelte', import.meta.url), 'utf8');

test('School setup uses the agreed workflow groups and item order', () => {
  assert.deepEqual(
    SCHOOL_MENU_GROUPS.map((group) => group.key),
    ['structure', 'teaching', 'students', 'communication', 'behaviour', 'system']
  );
  assert.deepEqual(
    SCHOOL_MENU_GROUPS.map((group) =>
      group.items.map((item) => (item.type === 'tab' ? item.key : item.href))
    ),
    [
      ['checklist', 'settings', 'branches', 'years', 'stages', 'levels', 'sections'],
      ['rosters', 'teachers', 'subjects', 'defaults', 'groups'],
      ['/school/students', '/school/students/data'],
      ['announcements', 'calendar'],
      ['behaviour', '/school/reports', '/school/recognition'],
      ['/school/administration']
    ]
  );
});

test('existing School setup tabs and destinations retain their behaviour', () => {
  assert.deepEqual(
    SCHOOL_TABS.map((tab) => tab.key),
    [
      'checklist',
      'settings',
      'branches',
      'years',
      'stages',
      'levels',
      'sections',
      'rosters',
      'teachers',
      'subjects',
      'defaults',
      'groups',
      'announcements',
      'calendar',
      'behaviour'
    ]
  );
  assert.match(schoolSource, /SCHOOL_TABS\.some\(\(tab\) => tab\.key === requestedTab\)/);
  assert.match(schoolSource, /onclick=\{\(\) => selectTab\(item\.key\)\}/);
});

test('ordinary items share one treatment while active state and shortcuts are explicit', () => {
  const shortcuts = SCHOOL_MENU_GROUPS.flatMap((group) => group.items).filter(
    (item) => item.type === 'shortcut'
  );
  assert.deepEqual(
    shortcuts.map((item) => item.href),
    ['/school/reports', '/school/recognition', '/school/administration']
  );
  assert.equal((schoolSource.match(/schoolMenuItemClass\(/g) || []).length, 5);
  assert.equal((schoolSource.match(/aria-current=/g) || []).length, 2);
  assert.match(schoolSource, /border-hero\/30 bg-hero\/10 text-hero/);
  assert.doesNotMatch(schoolSource, /whitespace-nowrap rounded-lg border border-sky-200/);
  assert.doesNotMatch(schoolSource, /whitespace-nowrap rounded-lg border border-hero/);
});

test('Reports remains a contextual shortcut inside Behaviour & points', () => {
  assert.match(schoolSource, /activeTab === 'behaviour'/);
  assert.match(schoolSource, /href="\/school\/reports" class="btn-secondary/);
  assert.match(schoolSource, /school\.menu\.openReports/);
});

test('mobile accordions and desktop grouped navigation use the same definition', () => {
  assert.equal((schoolSource.match(/\{#each SCHOOL_MENU_GROUPS as group\}/g) || []).length, 2);
  assert.match(schoolSource, /<details[^>]+open=\{isSchoolMenuGroupActive\(group\)\}/);
  assert.match(schoolSource, /class="lg:hidden" aria-label=/);
  assert.match(schoolSource, /class="hidden rounded-xl[^\n]+lg:block" aria-label=/);
});

test('English and Arabic menu labels describe the hierarchy consistently', () => {
  assert.deepEqual(Object.keys(en.school.menu.groups), Object.keys(ar.school.menu.groups));
  assert.deepEqual(Object.values(en.school.menu.groups), [
    'School structure',
    'Teaching setup',
    'Students',
    'Communication',
    'Behaviour & insights',
    'System'
  ]);
  assert.equal(en.school.tabs.settings, 'School settings');
  assert.equal(en.school.tabs.teachers, 'Staff & teaching assignments');
  assert.equal(en.school.tabs.students, 'Student records');
  assert.equal(ar.school.menu.shortcut, 'اختصار');
  assert.equal(ar.school.menu.positiveRecognition, 'التقدير الإيجابي');
});

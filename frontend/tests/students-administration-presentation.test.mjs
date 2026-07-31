import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const adminSource = readFileSync(
  new URL('../src/routes/school/students/+page.svelte', import.meta.url),
  'utf8'
);
const dataSource = readFileSync(
  new URL('../src/routes/school/students/data/+page.svelte', import.meta.url),
  'utf8'
);
const schoolSource = readFileSync(new URL('../src/routes/school/+page.svelte', import.meta.url), 'utf8');
const messagesSource = readFileSync(new URL('../src/lib/i18n/messages.ts', import.meta.url), 'utf8');

test('student editing and student data operations are separate routes', () => {
  assert.match(schoolSource, /href="\/school\/students"/);
  assert.match(schoolSource, /href="\/school\/students\/data"/);
  assert.doesNotMatch(schoolSource, /\{ key: 'students', label: 'school\.tabs\.students' \}/);
  assert.match(adminSource, /href="\/school\/students\/data"/);
  assert.match(dataSource, /href="\/school\/students"/);
  assert.doesNotMatch(adminSource, /\/students\/imports/);
});

test('complete student creation captures placement and optional guardians atomically', () => {
  assert.match(adminSource, /api\.post\(\s*'\/school\/students\/complete'/);
  assert.match(adminSource, /class_section_id: Number\(addSectionId\)/);
  assert.match(adminSource, /guardians: populatedGuardians\.map\(guardianPayload\)/);
  assert.match(adminSource, /studentIdRequired/);
  assert.match(adminSource, /guardianNameRequired/);
  assert.match(adminSource, /emailTestInvalid/);
  assert.match(messagesSource, /\.test addresses are not accepted/);
});

test('student detail exposes distinct data, guardian, placement and access concerns', () => {
  for (const tab of ['details', 'guardians', 'placement', 'access', 'fhh', 'history']) {
    assert.match(messagesSource, new RegExp(`${tab}:`));
  }
  assert.match(adminSource, /user_email/);
  assert.match(adminSource, /link_status/);
  assert.match(adminSource, /link_history/);
  assert.match(adminSource, /<details class="mt-5/);
  assert.doesNotMatch(adminSource, /opaque|household|device_token|invite_token/);
});

test('search clears explicitly and naturally resets when the route is recreated', () => {
  assert.match(adminSource, /let search = \$state\(''\)/);
  assert.match(adminSource, /async function clearSearch\(\)/);
  assert.match(adminSource, /search = ''/);
  assert.match(adminSource, /sectionFilter = ''/);
});

test('history stays compact while detailed rows remain downloadable', () => {
  assert.match(dataSource, /page_size=1/);
  assert.match(dataSource, /reports\/\$\{reportType\}\.csv/);
  assert.match(dataSource, /export-history\?page=/);
  assert.doesNotMatch(dataSource, /selectedImport\.rows/);
  assert.match(dataSource, /fixed bottom-4 end-4/);
});

test('English and Arabic copy use the school-system guardian ID label', () => {
  assert.match(messagesSource, /Guardian ID from school system \(optional\)/);
  assert.match(messagesSource, /معرّف ولي الأمر من نظام المدرسة \(اختياري\)/);
  assert.equal((messagesSource.match(/studentAdmin: \{/g) || []).length, 2);
  assert.equal((messagesSource.match(/studentData: \{/g) || []).length, 2);
});

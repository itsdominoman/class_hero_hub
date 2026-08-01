import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');
const school = read('src/routes/school/+page.svelte');
const reports = read('src/routes/school/reports/+page.svelte');
const recognition = read('src/routes/school/recognition/+page.svelte');
const students = read('src/routes/school/students/+page.svelte');
const messages = read('src/routes/messages/+page.svelte');

test('School setup tab state supports refresh, history and native Back', () => {
  assert.match(school, /url\.searchParams\.set\('tab', activeTab\)/);
  assert.match(school, /chhSchoolTabEntry/);
  assert.match(school, /window\.addEventListener\('popstate', onPopState\)/);
  assert.match(school, /window\.addEventListener\('chh:native-back', onNativeBack\)/);
});

test('Reports stores filters, sections, event pages and matrix controls in the URL', () => {
  for (const key of [
    'date_from',
    'category_type',
    'grade_level_id',
    'class_section_id',
    'student_id',
    'section',
    'events_offset',
    'row_dimension',
    'column_dimension',
    'order_by'
  ]) {
    assert.match(reports, new RegExp(`['"]${key}['"]`));
  }
  assert.match(reports, /chhReportContextEntry/);
  assert.match(reports, /restoreReportsFromHistory/);
  assert.match(reports, /window\.addEventListener\('popstate', onPopState\)/);
  assert.match(reports, /window\.addEventListener\('chh:native-back', onNativeBack\)/);
});

test('Recognition review selection is deep-linkable and returns to the review list', () => {
  assert.match(recognition, /searchParams\.set\('review', String\(reviewId\)\)/);
  assert.match(recognition, /chhRecognitionReviewEntry/);
  assert.match(recognition, /function backToReviews/);
  assert.match(recognition, /window\.addEventListener\('popstate', onPopState\)/);
  assert.match(recognition, /window\.addEventListener\('chh:native-back', onNativeBack\)/);
});

test('Student list/detail and message inbox/thread states create restorable history entries', () => {
  assert.match(students, /chhStudentDetailEntry/);
  assert.match(students, /restoreStudentUrl/);
  assert.match(students, /historyMode: 'push'/);
  assert.match(students, /window\.addEventListener\('popstate', onPopState\)/);
  assert.match(students, /window\.addEventListener\('chh:native-back', onNativeBack\)/);

  assert.match(messages, /chhMessageConversationEntry/);
  assert.match(messages, /historyMode: 'push'/);
  assert.match(messages, /window\.addEventListener\('popstate', onPopState\)/);
  assert.match(messages, /window\.addEventListener\('chh:native-back', onNativeBack\)/);
});

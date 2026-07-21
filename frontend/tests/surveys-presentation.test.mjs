import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

test('survey editor presents audience, privacy, response-unit, timezone and preview controls', () => {
  const source = read('src/routes/school/surveys/+page.svelte');
  assert.match(source, /schoolLocalToIso/);
  assert.match(source, /Selected linked families/);
  assert.match(source, /Anonymous responses/);
  assert.match(source, /One per household/);
  assert.match(source, /Push notification/);
  assert.match(source, /Notices-feed link/);
  assert.match(source, /previewOpen/);
  assert.match(source, /const \{ reminder_enabled, reminder_at, \.\.\.surveyForm \} = form/);
  assert.match(source, /\.\.\.surveyForm/);
  assert.match(source, /dir=\{ar \?/);
  assert.match(source, /rtl/);
  assert.match(source, /ltr/);
});

test('survey results expose lifecycle, response metrics, reminder and safe CSV actions', () => {
  const source = read('src/routes/school/surveys/[id]/+page.svelte');
  for (const label of ['Publish', 'Close', 'Reopen', 'Archive', 'Send reminder', 'Export CSV']) {
    assert.match(source, new RegExp(label));
  }
  assert.match(source, /Response rate/);
  assert.match(source, /Comments \/ free text/);
  assert.match(source, /survey\.response_mode/);
  assert.match(source, /dir=\{ar \?/);
  assert.match(source, /rtl/);
  assert.match(source, /ltr/);
});

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

test('survey composer is a single-scroll accessible mobile dialog', () => {
  const source = read('src/routes/school/surveys/+page.svelte');
  assert.match(source, /role="dialog"/);
  assert.match(source, /aria-modal="true"/);
  assert.match(source, /aria-labelledby="survey-composer-title"/);
  assert.match(source, /data-testid="survey-composer-close"/);
  assert.match(source, /close: "Close"/);
  assert.match(source, /close: "إغلاق"/);
  assert.match(source, /event\.key === "Escape"/);
  assert.match(source, /chh:native-back/);
  assert.match(source, /native-keyboard-open/);
  assert.match(source, /survey-composer-open/);
  assert.match(source, /data-testid="survey-composer-scroll"/);
  assert.doesNotMatch(source, /max-h-48 overflow-y-auto/);
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

test('closed survey reopen collects a future closing time in an accessible modal', () => {
  const source = read('src/routes/school/surveys/[id]/+page.svelte');
  assert.match(source, /onclick=\{openReopen\}/);
  assert.match(source, /type="datetime-local"/);
  assert.match(source, /role="dialog"/);
  assert.match(source, /aria-modal="true"/);
  assert.match(source, /closes_at: closesAt/);
  assert.match(source, /Choose a future closing time before reopening/);
  assert.match(source, /event\.key === "Escape"/);
});

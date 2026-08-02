import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';
import { ar, en } from '../src/lib/i18n/messages.ts';

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

test('survey editor presents audience, privacy, response-unit, timezone and preview controls', () => {
  const source = read('src/routes/school/surveys/+page.svelte');
  assert.match(source, /schoolLocalToIso/);
  assert.match(source, /surveyManagement\.audiences\.selected_families/);
  assert.match(source, /surveyManagement\.anonymousResponses/);
  assert.match(source, /surveyManagement\.responseModes\.household/);
  assert.match(source, /surveyManagement\.pushNotification/);
  assert.match(source, /surveyManagement\.noticesFeed/);
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
  assert.match(source, /surveyManagement\.close/);
  assert.match(source, /event\.key === "Escape"/);
  assert.match(source, /chh:native-back/);
  assert.match(source, /native-keyboard-open/);
  assert.match(source, /survey-composer-open/);
  assert.match(source, /data-testid="survey-composer-scroll"/);
  assert.doesNotMatch(source, /max-h-48 overflow-y-auto/);
});

test('survey results expose lifecycle, response metrics, reminder and safe CSV actions', () => {
  const source = read('src/routes/school/surveys/[id]/+page.svelte');
  for (const key of ['publish', 'close', 'reopen', 'archive', 'sendReminder', 'exportCsv']) {
    assert.match(source, new RegExp(`surveyManagement\\.${key}`));
  }
  assert.match(source, /surveyManagement\.responseRate/);
  assert.match(source, /surveyManagement\.comments/);
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
  assert.match(source, /surveyManagement\.futureClosingTime/);
  assert.match(source, /event\.key === "Escape"/);
});

test('survey system copy is catalogue-backed with professional Arabic terminology', () => {
  assert.equal(en.surveyManagement.audiences.whole_school, 'Whole school');
  assert.equal(ar.surveyManagement.audiences.whole_school, 'المدرسة بأكملها');
  assert.equal(ar.surveyManagement.responseModes.guardian, 'استجابة واحدة لكل ولي أمر');
  assert.equal(ar.surveyManagement.types.rating, 'مقياس تقييم');
  assert.equal(ar.surveyManagement.responseRate, 'معدل الاستجابة');
  for (const path of [
    'Archived', 'Eligible', 'Responses', 'Survey title', 'Question',
    'Anonymous responses', 'Push notification', 'Saving…'
  ]) {
    assert.doesNotMatch(read('src/routes/school/surveys/+page.svelte'), new RegExp(`>${path}<`));
  }
});

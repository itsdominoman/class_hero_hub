import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const source = readFileSync(new URL('../src/routes/school/recognition/+page.svelte', import.meta.url), 'utf8');
const administration = readFileSync(new URL('../src/routes/school/administration/+page.svelte', import.meta.url), 'utf8');
const messages = readFileSync(new URL('../src/lib/i18n/messages.ts', import.meta.url), 'utf8');

test('recognition is an administrator-led positive-only workflow', () => {
  assert.match(administration, /href="\/school\/recognition"/);
  assert.match(source, /\/school\/recognition\/options/);
  assert.match(source, /\/school\/recognition\/reviews/);
  assert.match(source, /noAutomaticWinner/);
  assert.match(source, /positiveOnlyHelp/);
  assert.doesNotMatch(source, /needs_work|negative leaderboard|worst student/i);
});

test('shortlist requires explicit selection and supports recorded exclusion and correction', () => {
  assert.match(source, /type="radio" name="recipient"/);
  assert.match(source, /candidates\/\$\{candidate\.id\}\/exclude/);
  assert.match(source, /\/confirm/);
  assert.match(source, /\/revoke/);
  assert.match(source, /revocationReason\.trim\(\)\.length < 3/);
});

test('confirmed award renders a browser-printable certificate without publication', () => {
  assert.match(source, /currentReview\?\.status === 'confirmed'/);
  assert.match(source, /window\.print\(\)/);
  assert.match(source, /@media print/);
  assert.match(source, /@page \{ size: A4 landscape/);
  assert.match(source, /notPublished/);
  assert.doesNotMatch(source, /api\.post\([^\n]*(publish|notification)/i);
});

test('English and Arabic recognition copy remains paired', () => {
  assert.equal((messages.match(/recognitionPage: \{/g) || []).length, 2);
  assert.match(messages, /Positive recognition/);
  assert.match(messages, /التقدير الإيجابي/);
  assert.match(messages, /لا يُستخدم السلوك السلبي ولا يظهر هنا أبداً/);
});

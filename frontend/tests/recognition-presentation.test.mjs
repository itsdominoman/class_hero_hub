import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const source = readFileSync(new URL('../src/routes/school/recognition/+page.svelte', import.meta.url), 'utf8');
const administration = readFileSync(new URL('../src/routes/school/administration/+page.svelte', import.meta.url), 'utf8');
const messages = readFileSync(new URL('../src/lib/i18n/messages.ts', import.meta.url), 'utf8');

test('recognition keeps positive ranking and adds a staff-only eligibility safeguard', () => {
  assert.match(administration, /href="\/school\/recognition"/);
  assert.match(source, /\/school\/recognition\/options/);
  assert.match(source, /\/school\/recognition\/reviews/);
  assert.match(source, /noAutomaticWinner/);
  assert.match(source, /positiveOnlyHelp/);
  assert.match(source, /needs_work_safeguard_enabled/);
  assert.match(source, /maximum_needs_work_events/);
  assert.match(source, /needs_work_category_ids/);
  assert.match(source, /override-safeguard/);
  assert.doesNotMatch(source, /negative leaderboard|worst student|bad student/i);
});

test('review cards expose an actionable keyboard button and focus the selected decision section', () => {
  assert.match(source, /recognitionPage\.openReview/);
  assert.match(source, /<article class=\{`review-card/);
  assert.match(source, /<button type="button" class="review-card-action/);
  assert.match(source, /aria-pressed=\{currentReview\?\.id === review\.id\}/);
  assert.match(source, /cursor: pointer/);
  assert.match(source, /\.review-card button:hover/);
  assert.match(source, /\.review-card button:focus-visible/);
  assert.match(source, /decisionSection\?\.scrollIntoView/);
  assert.match(source, /decisionSection\?\.focus/);
  assert.match(source, /bind:this=\{decisionSection\} tabindex="-1"/);
  assert.match(source, /if \(currentReview\?\.id === reviewId && !forceReload\)/);
});

test('draft and configuration lifecycle controls preserve history and avoid duplicate cards', () => {
  assert.match(source, /was_existing_draft/);
  assert.match(source, /reviews\.filter\(\(row\) => row\.id !== review\.id\)/);
  assert.match(source, /existingDraftOpened/);
  assert.match(source, /reviews\/\$\{currentReview\.id\}\/archive/);
  assert.match(source, /discardReason\.trim\(\)\.length < 3/);
  assert.match(source, /confirmDiscardReview/);
  assert.match(source, /configs\/\$\{config\.id\}\/archive/);
  assert.match(source, /configArchiveReason\.trim\(\)\.length < 3/);
  assert.match(source, /row\.status === 'active' && !row\.archived_at/);
  assert.match(source, /include_archived=true/);
  assert.match(source, /similarConfigWarning/);
});

test('generation shows the selected frozen criteria and excludes inactive or archived configurations', () => {
  assert.match(source, /selectedConfig\(\)/);
  assert.match(source, /config\.minimum_positive_points/);
  assert.match(source, /config\.shortlist_size/);
  assert.match(source, /config\.needs_work_safeguard_enabled/);
  assert.match(source, /configOptionLabel\(config\)/);
  assert.match(source, /configStatus\.\$\{config\.status\}/);
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
  const certificate = source.slice(source.indexOf('{#if currentReview?.status'), source.indexOf('<style>'));
  assert.doesNotMatch(certificate, /safeguard_counted_total|safeguard_category_totals|countedNeedsWork/);
});

test('English and Arabic recognition copy remains paired', () => {
  assert.equal((messages.match(/recognitionPage: \{/g) || []).length, 2);
  assert.match(messages, /Positive recognition/);
  assert.match(messages, /التقدير الإيجابي/);
  assert.match(messages, /غير مؤهل وفق المعايير الحالية/);
});

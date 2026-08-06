import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const selector = readFileSync(
  new URL('../src/lib/components/LanguageSelector.svelte', import.meta.url),
  'utf8'
);

test('language control shows only the opposite language and switches in place', () => {
  assert.match(selector, /\$locale === 'ar' \? 'en' : 'ar'/);
  assert.match(selector, /\$locale === 'ar' \? 'English' : 'العربية'/);
  assert.match(selector, /<Globe2[^>]*data-testid="language-globe"/);
  assert.match(selector, /setLanguage\(nextLocale\)/);
  assert.doesNotMatch(selector, /<select/);
  assert.doesNotMatch(selector, /goto\(/);
});

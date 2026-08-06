import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (relative) => readFileSync(new URL(`../${relative}`, import.meta.url), 'utf8');
const sharedSearch = read('src/lib/components/EntitySearch.svelte');
const school = read('src/routes/school/+page.svelte');
const studentRecords = read('src/routes/school/students/+page.svelte');
const reports = read('src/routes/school/reports/+page.svelte');
const surveys = read('src/routes/school/surveys/+page.svelte');

test('shared entity search is debounced, keyboard-native and allows exact numeric identifiers immediately', () => {
  assert.match(sharedSearch, /type="search"/);
  assert.match(sharedSearch, /debounceMs = 250/);
  assert.match(sharedSearch, /!\/\^\\d\+\$\/\.test\(query\)/);
  assert.match(sharedSearch, /query\.length < minCharacters/);
  assert.match(sharedSearch, /aria-describedby=\{helpId\}/);
});

test('subject-group tables and roster selection share the long-list search pattern', () => {
  assert.match(school, /id="subject-group-search"/);
  assert.match(school, /id="subject-group-roster-search"/);
  assert.match(school, /filteredGroupRows\(groupSearchQuery\)/);
  assert.match(school, /rows=\{groupRosterOptions\(\)\}/);
  for (const field of ['row.code', 'row.name_ar', 'yearName', 'subjectName', 'groupPolicyLabel']) {
    assert.match(school, new RegExp(field.replace(/[().]/g, '\\$&')));
  }
});

test('class roster selection supports the same bilingual and identifier search pattern', () => {
  assert.match(school, /id="class-roster-search"/);
  assert.match(school, /function rosterSectionOptions/);
  assert.match(school, /row\.name_ar/);
  assert.match(school, /yearName\(row\.academic_year_id\)/);
  assert.match(school, /levelName\(row\.grade_level_id\)/);
  assert.match(school, /rows=\{rosterSectionOptions\(\)\}/);
});

test('report staff filtering searches only the permission-scoped staff context', () => {
  assert.match(reports, /id="report-teacher-search"/);
  assert.match(reports, /teachers\.filter/);
  assert.match(reports, /String\(teacher\.id\) === query/);
  assert.match(reports, /\{#each visibleTeachers as teacher\}/);
});

test('student records use the shared debounced server-search control', () => {
  assert.match(studentRecords, /id="student-record-search"/);
  assert.match(studentRecords, /onquery=\{\(query\) => \{ search = query; void applyFilters\(\); \}\}/);
  assert.match(studentRecords, /school\.studentAdmin\.searchPatternHelp/);
});

test('survey recipient search filters the server-scoped audience context without losing selected ids', () => {
  assert.match(surveys, /id="survey-target-search"/);
  assert.match(surveys, /filteredTargetRows/);
  assert.match(surveys, /row\.label_ar/);
  assert.match(surveys, /checked=\{form\.target_ids\.includes\(row\.id\)\}/);
  assert.match(surveys, /surveyManagement\.noMatchingTargets/);
});

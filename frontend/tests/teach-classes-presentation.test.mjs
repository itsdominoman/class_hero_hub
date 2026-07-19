import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  classLabel,
  compareTeacherClasses,
  groupTeacherClasses,
  subjectPalette
} from '../src/routes/teach/teachClassPresentation.ts';

const pageSource = readFileSync(new URL('../src/routes/teach/+page.svelte', import.meta.url), 'utf8');

function assignment(id, subject, grade, section, branch = 'Al Khoud', role = 'subject_teacher') {
  return {
    id,
    role,
    school: { name: 'CHH School' },
    grade_level: { name: grade },
    class_section: { name: section },
    subject_group: { name: `${grade}${section} ${subject}` },
    subject: { name: subject },
    branch: { name: branch }
  };
}

test('groups Homeroom first and other subjects alphabetically', () => {
  const input = [
    assignment(1, 'Science', 'G6', ''),
    assignment(2, 'Maths', 'G10', ''),
    assignment(3, 'English', 'G2', 'B'),
    assignment(4, 'Arabic', 'KG2', ''),
    assignment(5, 'Homeroom', 'G2', 'A', 'Al Khoud', 'homeroom'),
    assignment(6, 'ICT', 'G1', '')
  ];
  const groups = groupTeacherClasses(input, 'en', 'Homeroom', 'Subject');
  assert.deepEqual(groups.map((group) => group.label), ['Homeroom', 'Arabic', 'English', 'ICT', 'Maths', 'Science']);
});

test('uses KG-to-G12 academic ordering, A-B-C sections, then branch', () => {
  const input = [
    assignment(10, 'English', 'G10', ''),
    assignment(9, 'English', 'G2', 'Blue'),
    assignment(8, 'English', 'G2', 'C'),
    assignment(7, 'English', 'G2', 'A', 'Barka'),
    assignment(6, 'English', 'G2', 'B'),
    assignment(5, 'English', 'G2', 'A', 'Al Khoud'),
    assignment(4, 'English', 'G1', ''),
    assignment(3, 'English', 'KG2', ''),
    assignment(2, 'English', 'KG1', '')
  ];
  const sorted = [...input].sort((left, right) => compareTeacherClasses(left, right, 'en'));
  assert.deepEqual(sorted.map((row) => row.id), [2, 3, 4, 5, 7, 6, 8, 9, 10]);
  assert.deepEqual(sorted.map(classLabel), ['KG1', 'KG2', 'G1', 'G2A', 'G2A', 'G2B', 'G2C', 'G2 · Blue', 'G10']);
});

test('unknown subject colours are deterministic neutral pastels', () => {
  assert.deepEqual(subjectPalette('Robotics'), subjectPalette('Robotics'));
  assert.notDeepEqual(subjectPalette('Robotics'), subjectPalette('English'));
});

test('mobile source fixes the compact controls and gives scroll ownership to the grouped class list', () => {
  assert.match(pageSource, /data-testid="teach-fixed-panel"/);
  assert.match(pageSource, /data-testid="teach-utility-actions"[^>]*grid-cols-3/);
  assert.match(pageSource, /data-testid="teach-class-list"[^>]*overflow-y-auto/);
  assert.doesNotMatch(pageSource, /data-testid="teach-subject-heading"[^>]*\bsticky\b/);
  assert.match(pageSource, /aria-label=\{\$_\('teach\.announcements\.utilityLabel'\)\}/);
  assert.match(pageSource, /data-testid="teach-class-card"/);
  assert.match(pageSource, /href=\{`\/teach\/assignments\/\$\{card\.id\}`\}/);
  assert.match(pageSource, /data-testid="teach-class-list"[^>]*\bpb-4\b[^>]*\bmd:pb-0\b/);
  assert.doesNotMatch(pageSource, /data-testid="teach-class-card"[^>]*btn-hero/);
});

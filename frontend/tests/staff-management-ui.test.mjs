import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { en, ar } from '../src/lib/i18n/messages.ts';

const source = readFileSync(new URL('../src/routes/school/staff/+page.svelte', import.meta.url), 'utf8');

test('staff management exposes every requested non-administrator staff role', () => {
  for (const role of ['principal', 'deputy_principal', 'head_of_department', 'support_staff', 'teacher']) {
    assert.match(source, new RegExp(`['"]${role}['"]`));
    assert.equal(typeof en.staffManagement.roles[role], 'string');
    assert.equal(typeof ar.staffManagement.roles[role], 'string');
  }
});

test('staff management uses school-scoped role and department APIs', () => {
  assert.match(source, /'X-School-Id'/);
  assert.match(source, /'X-Membership-Id'/);
  assert.match(source, /\/school\/staff\$\{params\.size/);
  assert.match(source, /'\/school\/staff\/invites'/);
  assert.match(source, /'\/school\/departments'/);
  assert.match(source, /\/school\/departments\/\$\{assignmentDepartmentId\}\/assignments/);
  assert.match(source, /\/school\/department-assignments\/\$\{row\.id\}\/close/);
});

test('HOD selection is constrained to explicit HOD memberships and dated assignments', () => {
  assert.match(source, /row\.role === 'head_of_department'/);
  assert.match(source, /valid_from: assignmentValidFrom/);
  assert.match(source, /valid_to: assignmentValidTo \|\| null/);
  assert.match(source, /responsibility: assignmentResponsibility/);
});

test('staff search is debounced and permits immediate exact numeric identifiers', () => {
  assert.match(source, /term\.length === 1 && !\/\^\\d\+\$\//);
  assert.match(source, /setTimeout\(async \(\) =>/);
  assert.match(source, /}, 300\)/);
});

import assert from 'node:assert/strict';
import { rosterPathForAssignment } from '../src/lib/teachRoster.js';

assert.equal(
  rosterPathForAssignment({
    target_type: 'subject_group',
    school: { id: 1 },
    class_section: { id: 2 },
    subject_group: { id: 9 }
  }),
  '/teach/schools/1/subject-groups/9/roster'
);

assert.equal(
  rosterPathForAssignment({
    target_type: 'class_section',
    school: { id: 1 },
    class_section: { id: 2 },
    subject_group: null
  }),
  '/teach/schools/1/sections/2/roster'
);

console.log('teach roster path checks passed');

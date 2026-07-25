import assert from 'node:assert/strict';
import test from 'node:test';

import {
  awardRequest,
  behaviourAwardFingerprint
} from '../src/lib/behaviourAwardIdempotency.ts';

const basePayload = {
  school_id: 7,
  student_ids: [41, 12],
  category_id: 3,
  note: 'Good teamwork',
  context_type: 'class',
  class_section_id: 9
};

test('reordered students and note whitespace reuse the original idempotency key', () => {
  let created = 0;
  const createKey = () => `key-${++created}`;
  const first = awardRequest(basePayload, null, createKey);
  const retry = awardRequest({
    category_id: 3,
    class_section_id: 9,
    context_type: 'class',
    note: '  Good teamwork  ',
    student_ids: [12, 41],
    school_id: 7
  }, first, createKey);

  assert.equal(retry.key, first.key);
  assert.equal(created, 1);
  assert.equal(
    behaviourAwardFingerprint({ ...basePayload, note: '   ' }),
    behaviourAwardFingerprint({ ...basePayload, note: null })
  );
});

test('a materially changed award receives a new idempotency key', () => {
  let created = 0;
  const createKey = () => `key-${++created}`;
  const first = awardRequest(basePayload, null, createKey);
  const changed = awardRequest({ ...basePayload, category_id: 4 }, first, createKey);

  assert.notEqual(changed.key, first.key);
  assert.equal(created, 2);
});

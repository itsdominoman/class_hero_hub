import assert from 'node:assert/strict';
import test from 'node:test';

import {
  conversationSubtitle,
  conversationTitle,
  filterConversations
} from '../src/lib/messaging/presentation.ts';
import { highestServerSequence, mergeIncomingMessages } from '../src/lib/messaging/state.ts';
import { chooseNativeBackAction } from '../src/lib/native/back-policy.ts';

const baseConversation = {
  id: '00000000-0000-0000-0000-000000000001',
  kind: 'student_staff',
  status: 'active',
  read_only: false,
  student: {
    id: 11,
    display_name: 'Mariam Al Harthy',
    name_ar: 'مريم الحارثية',
    class_label: 'KG1A',
    class_label_ar: 'الروضة الأولى أ',
    grade_label: 'KG1',
    grade_label_ar: 'الروضة الأولى'
  },
  context: { label: 'Class 4A', label_ar: 'الصف ٤ أ' },
  participants: ['Aisha Al Balushi'],
  last_message: {
    id: '00000000-0000-0000-0000-000000000002',
    sequence: 3,
    sender_display_name: 'Aisha Al Balushi',
    body: 'Please review the homework',
    state: 'active',
    created_at: '2026-07-16T08:00:00Z'
  },
  last_message_at: '2026-07-16T08:00:00Z',
  unread_count: 2,
  capabilities: {
    can_send: true,
    can_close: false,
    delivery_receipts_visible: false,
    read_receipts_visible: false
  }
};

test('conversation presentation preserves explicit student and participant context', () => {
  assert.equal(conversationTitle(baseConversation), 'Mariam Al Harthy · KG1A');
  assert.equal(conversationTitle(baseConversation, true), 'Mariam Al Harthy · الروضة الأولى أ');
  assert.equal(conversationSubtitle(baseConversation), 'Aisha Al Balushi');
});

test('incremental refresh merges monotonically without dropping optimistic drafts', () => {
  const optimistic = {
    id: 'local:stable-client-id',
    client_message_id: 'stable-client-id',
    sequence: Number.MAX_SAFE_INTEGER,
    sender_display_name: 'Teacher One',
    sender_is_self: true,
    body: 'Unsent draft-owned retry',
    state: 'active',
    urgent: false,
    created_at: '2026-07-17T09:00:00Z',
    local_state: 'failed'
  };
  const current = [
    {
      ...baseConversation.last_message,
      sender_is_self: false,
      urgent: false
    },
    optimistic
  ];
  const incoming = {
    id: '00000000-0000-0000-0000-000000000004',
    sequence: 4,
    sender_display_name: 'Dom Brown',
    sender_kind: 'chh_guardian',
    sender_relationship: 'father',
    sender_is_self: false,
    body: 'New parent reply',
    state: 'active',
    urgent: false,
    created_at: '2026-07-17T09:01:00Z'
  };
  const merged = mergeIncomingMessages(current, [incoming]);
  assert.deepEqual(merged.map((row) => row.id), [baseConversation.last_message.id, incoming.id, optimistic.id]);
  assert.equal(merged.at(-1).body, 'Unsent draft-owned retry');
  assert.equal(highestServerSequence(merged), 4);

  const stale = mergeIncomingMessages(merged, [current[0]]);
  assert.deepEqual(stale.map((row) => row.id), merged.map((row) => row.id));
  assert.equal(stale.some((row) => row.body === 'New parent reply'), true);
});

test('inbox filtering supports Arabic mixed-direction content and unread status', () => {
  assert.deepEqual(filterConversations([baseConversation], 'مريم', 'all'), [baseConversation]);
  assert.deepEqual(filterConversations([baseConversation], 'homework', 'unread'), [baseConversation]);
  assert.deepEqual(filterConversations([baseConversation], '', 'closed'), []);
});

test('staff-direct conversations fall back to participant identity', () => {
  const direct = {
    ...baseConversation,
    kind: 'staff_direct',
    student: null,
    participants: ['School Administrator'],
    context: { label: null, label_ar: null },
    unread_count: 0
  };
  assert.equal(conversationTitle(direct), 'School Administrator');
  assert.equal(conversationSubtitle(direct), 'School Administrator');
  assert.deepEqual(filterConversations([direct], '', 'active'), [direct]);
});

test('native Back policy avoids accidental exit and preserves non-root fallback', () => {
  const roots = ['/', '/login', '/school', '/teach', '/parent'];
  assert.equal(chooseNativeBackAction('/messages', roots, true, false), 'history');
  assert.equal(chooseNativeBackAction('/messages', roots, false, false), 'fallback');
  assert.equal(chooseNativeBackAction('/teach', roots, false, false), 'arm-exit');
  assert.equal(chooseNativeBackAction('/teach', roots, false, true), 'exit');
});

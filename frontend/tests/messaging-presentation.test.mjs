import assert from 'node:assert/strict';
import test from 'node:test';

import {
  conversationSubtitle,
  conversationTitle,
  filterConversations
} from '../src/lib/messaging/presentation.ts';

const baseConversation = {
  id: '00000000-0000-0000-0000-000000000001',
  kind: 'student_staff',
  status: 'active',
  read_only: false,
  student: { id: 11, display_name: 'Mariam Al Harthy', name_ar: 'مريم الحارثية' },
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
  assert.equal(conversationTitle(baseConversation), 'Mariam Al Harthy');
  assert.equal(conversationSubtitle(baseConversation), 'Aisha Al Balushi · Class 4A');
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

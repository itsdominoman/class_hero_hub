import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  activeGuardianCount,
  conversationSubtitle,
  conversationTitle,
  filterConversations,
  staffContextLabel
} from '../src/lib/messaging/presentation.ts';
import { highestServerSequence, mergeIncomingMessages } from '../src/lib/messaging/state.ts';
import { chooseNativeBackAction } from '../src/lib/native/back-policy.ts';

const composerSource = readFileSync(new URL('../src/lib/components/messaging/MessageComposer.svelte', import.meta.url), 'utf8');
const photoSource = readFileSync(new URL('../src/lib/components/messaging/ProtectedMessagePhoto.svelte', import.meta.url), 'utf8');
const viewerSource = readFileSync(new URL('../src/lib/components/messaging/ProtectedPhotoViewer.svelte', import.meta.url), 'utf8');
const pageSource = readFileSync(new URL('../src/routes/messages/+page.svelte', import.meta.url), 'utf8');
const apiSource = readFileSync(new URL('../src/lib/messaging/api.ts', import.meta.url), 'utf8');

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

test('compact conversation context uses staff assignment and active guardian count', () => {
  assert.equal(staffContextLabel(
    { relationship: 'homeroom_teacher', subjects: [] },
    false,
    { administration: 'Administration', homeroom: 'Homeroom', teacher: 'Teacher', staff: 'Staff' }
  ), 'Homeroom');
  assert.equal(staffContextLabel(
    {
      relationship: 'subject_teacher',
      subjects: [{ name: 'Maths', name_ar: 'الرياضيات' }, { name: 'Science', name_ar: 'العلوم' }]
    },
    true,
    { administration: 'الإدارة', homeroom: 'الفصل', teacher: 'المعلم', staff: 'الموظف' }
  ), 'الرياضيات, العلوم');
  assert.equal(activeGuardianCount({
    ...baseConversation,
    participant_details: [
      { kind: 'staff', side: 'staff', display_name: 'Teacher One', active: true },
      { kind: 'chh_guardian', side: 'guardian', display_name: 'Aisha', active: true },
      { kind: 'chh_guardian', side: 'guardian', display_name: 'Fatma', active: true },
      { kind: 'chh_guardian', side: 'guardian', display_name: 'Former guardian', active: false }
    ],
    shared_guardian_visibility: true,
    safeguarding_disclosure: true
  }), 2);
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

test('photo composer supports gallery, Android camera, five-photo limit, and independent retry', () => {
  assert.match(composerSource, /type="file"[^>]+multiple/);
  assert.match(composerSource, /capture="environment"/);
  assert.match(composerSource, /photos\.length >= 5/g);
  assert.match(composerSource, /onretryphoto\(photo\)/);
  assert.match(composerSource, /!draft\.trim\(\) && !photos\.some/);
  assert.match(pageSource, /const available = Math\.max\(0, 5 - selectedPhotos\.length\)/);
  assert.match(pageSource, /files\.slice\(0, available\)/);
  assert.match(pageSource, /staged_media_ids: stagedMediaIds/);
});

test('compact composer integrates media controls and reserves the empty action for future voice notes', () => {
  assert.match(composerSource, /rounded-\[1\.4rem\]/);
  assert.match(composerSource, /min-h-11 max-h-32/);
  assert.match(composerSource, /grid h-10 w-10/g);
  assert.match(composerSource, /pb-\[calc\(0\.5rem\+var\(--safe-bottom\)\)\]/);
  assert.match(composerSource, /\{#if draft\.trim\(\) \|\| photos\.length\}/);
  assert.match(composerSource, /data-testid="message-voice-placeholder"/);
  assert.match(composerSource, /voiceNotesUnavailable/);
  assert.match(composerSource, /<Mic size=\{19\}/);
  assert.match(composerSource, /data-testid="message-send"/);
  assert.match(composerSource, /<SendHorizontal size=\{19\}/);
  assert.doesNotMatch(composerSource, /h-12 w-12/);
});

test('protected photo delivery never renders a stable media URL and cleans blob URLs', () => {
  assert.match(apiSource, /api\.download\(/);
  assert.match(apiSource, /\/media\/\$\{mediaId\}\/\$\{variant\}/);
  assert.doesNotMatch(photoSource, /storage_key|direct_url|public_url/);
  assert.match(photoSource, /URL\.createObjectURL\(blob\)/);
  assert.match(photoSource, /URL\.revokeObjectURL\(objectUrl\)/);
  assert.match(photoSource, /onclick=\{fetchPhoto\}/);
});

test('full-screen viewer provides protected fetch retry, gestures, navigation, and native Back', () => {
  assert.match(viewerSource, /touch-action:none/);
  assert.match(viewerSource, /pointers\.size === 2/);
  assert.match(viewerSource, /Math\.abs\(dx\) > 56/);
  assert.match(viewerSource, /event\.key === 'ArrowLeft'/);
  assert.match(viewerSource, /event\.key === 'Escape'/);
  assert.match(viewerSource, /chh:native-back/);
  assert.match(viewerSource, /onclick=\{fetchFull\}/);
  assert.match(viewerSource, /URL\.revokeObjectURL\(objectUrl\)/);
});

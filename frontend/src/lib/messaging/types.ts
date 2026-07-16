import type { SessionMembership } from '$lib/roleRouting';

export type MessagingMembership = SessionMembership & {
  role: 'teacher' | 'school_admin';
};

export type MessagingStudent = {
  id: number;
  display_name: string;
  name_ar?: string | null;
};

export type MessagingCapabilities = {
  can_send: boolean;
  can_close: boolean;
  delivery_receipts_visible: boolean;
  read_receipts_visible: boolean;
};

export type InboxMessage = {
  id: string;
  sequence: number;
  sender_display_name: string;
  body: string | null;
  state: string;
  created_at: string;
};

export type ConversationSummary = {
  id: string;
  kind: 'student_staff' | 'staff_direct' | 'guardian_direct';
  status: string;
  read_only: boolean;
  student: MessagingStudent | null;
  context: { label?: string | null; label_ar?: string | null };
  participants: string[];
  last_message: InboxMessage | null;
  last_message_at: string | null;
  unread_count: number;
  capabilities: MessagingCapabilities;
};

export type ParticipantDetail = {
  kind: string;
  side: 'staff' | 'guardian';
  display_name: string;
  active: boolean;
};

export type ConversationDetail = ConversationSummary & {
  participant_details: ParticipantDetail[];
  shared_guardian_visibility: boolean;
  safeguarding_disclosure: boolean;
};

export type MessageItem = {
  id: string;
  sequence: number;
  sender_display_name: string;
  sender_is_self: boolean;
  body: string | null;
  state: string;
  urgent: boolean;
  created_at: string;
};

export type OptimisticMessage = MessageItem & {
  client_message_id?: string;
  local_state?: 'sending' | 'failed';
  error?: string;
};

export type InboxPage = {
  items: ConversationSummary[];
  next_cursor: string | null;
};

export type MessagePage = {
  items: MessageItem[];
  next_cursor: string | null;
};

export type RecipientStudent = {
  student_id: number;
  display_name: string;
  name_ar?: string | null;
  guardian_names: string[];
};

export type RecipientStaff = {
  membership_id: number;
  display_name: string;
  name_ar?: string | null;
  role: 'teacher' | 'school_admin';
};

export type RecipientResults = {
  students: RecipientStudent[];
  staff: RecipientStaff[];
};

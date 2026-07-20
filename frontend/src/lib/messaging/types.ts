import type { SessionMembership } from '$lib/roleRouting';

export type MessagingMembership = SessionMembership & {
  role: 'teacher' | 'school_admin';
};

export type StaffNotificationPreference = {
  allowed_by_school: boolean;
  stored_out_of_hours_notifications_enabled: boolean;
  effective_out_of_hours_notifications_enabled: boolean;
  preference_version: number;
};

export type MessagingStudent = {
  id: number;
  display_name: string;
  name_ar?: string | null;
  class_label?: string | null;
  class_label_ar?: string | null;
  grade_label?: string | null;
  grade_label_ar?: string | null;
};

export type StaffContext = {
  relationship: 'school_administration' | 'homeroom_teacher' | 'subject_teacher' | 'school_staff';
  subjects: Array<{ name?: string | null; name_ar?: string | null }>;
};

export type MessagingCapabilities = {
  can_send: boolean;
  can_close: boolean;
  can_mark_urgent: boolean;
  delivery_receipts_visible: boolean;
  read_receipts_visible: boolean;
  voice_notes_enabled: boolean;
};

export type InboxMessage = {
  id: string;
  sequence: number;
  sender_display_name: string;
  sender_kind?: string | null;
  sender_relationship?: string | null;
  message_type: 'standard' | 'voice_note';
  body: string | null;
  photo_count: number;
  voice_note: MessageVoiceNote | null;
  state: string;
  created_at: string;
};

export type ConversationSummary = {
  id: string;
  kind: 'student_staff' | 'staff_direct' | 'guardian_direct';
  status: string;
  participant_state: 'active' | 'read_only' | 'closed';
  read_only: boolean;
  student: MessagingStudent | null;
  context: { label?: string | null; label_ar?: string | null };
  staff_context?: StaffContext | null;
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
  relationship?: string | null;
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
  sender_kind?: string | null;
  sender_relationship?: string | null;
  sender_is_self: boolean;
  message_type: 'standard' | 'voice_note';
  body: string | null;
  photos: MessagePhoto[];
  voice_note: MessageVoiceNote | null;
  state: string;
  urgent: boolean;
  created_at: string;
  receipt?: MessageReceipt;
};

export type MessageReceipt = {
  delivery_visible: boolean;
  read_visible: boolean;
  delivered: boolean;
  read: boolean;
  state: 'sent' | 'delivered' | 'read';
  policy_version: number;
};

export type MessageReceiptUpdate = {
  id: string;
  sequence: number;
  receipt: MessageReceipt;
};

export type MessagePhoto = {
  id: string;
  sort_order: number;
  content_type: 'image/jpeg' | 'image/webp' | null;
  full_bytes: number;
  thumbnail_bytes: number;
  width: number;
  height: number;
  thumbnail_width: number;
  thumbnail_height: number;
  thumbnail_available: boolean;
  full_available: boolean;
};

export type MessageVoiceNote = {
  id: string;
  content_type: 'audio/mp4';
  size_bytes: number;
  duration_ms: number;
  codec: 'aac';
  container: 'mp4';
  available: boolean;
  transcription: { available: false; state: 'not_requested' };
};

export type SelectedMessagePhoto = {
  client_upload_id: string;
  file: File;
  preview_url: string;
  state: 'selected' | 'uploading' | 'ready' | 'failed';
  staged_id?: string;
  error?: string;
};

export type OptimisticMessage = MessageItem & {
  client_message_id?: string;
  staged_media_ids?: string[];
  local_photo_urls?: string[];
  staged_voice_id?: string;
  voice_upload_id?: string;
  voice_blob?: Blob;
  local_voice_url?: string;
  voice_duration_ms?: number;
  local_state?: 'sending' | 'failed';
  error?: string;
};

export type InboxPage = {
  items: ConversationSummary[];
  next_cursor: string | null;
};

export type MessagePage = {
  items: MessageItem[];
  receipt_updates: MessageReceiptUpdate[];
  next_cursor: string | null;
  latest_sequence: number;
};

export type RecipientStudent = {
  student_id: number;
  display_name: string;
  name_ar?: string | null;
  guardian_names: string[];
  guardian_details?: Array<{ display_name: string; relationship?: string | null }>;
  conversation_id?: string | null;
  class_label?: string | null;
  class_label_ar?: string | null;
  grade_label?: string | null;
  grade_label_ar?: string | null;
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

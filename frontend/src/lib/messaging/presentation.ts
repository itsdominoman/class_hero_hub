import type { ConversationSummary, MessagingStudent } from './types';

export function studentAcademicLabel(
  student: Pick<MessagingStudent, 'class_label' | 'class_label_ar' | 'grade_label' | 'grade_label_ar'> | null,
  arabic = false
): string {
  if (!student) return '';
  return (
    (arabic ? student.class_label_ar : student.class_label) ||
    (arabic ? student.grade_label_ar : student.grade_label) ||
    student.class_label ||
    student.grade_label ||
    ''
  ).trim();
}

export function conversationTitle(conversation: ConversationSummary, arabic = false): string {
  if (conversation.student?.display_name) {
    const academic = studentAcademicLabel(conversation.student, arabic);
    return [conversation.student.display_name, academic].filter(Boolean).join(' · ');
  }
  return conversation.participants.join(', ') || 'Conversation';
}

export function conversationSubtitle(conversation: ConversationSummary, arabic = false): string {
  const context = (arabic ? conversation.context.label_ar : conversation.context.label)?.trim();
  const participants = conversation.participants.join(', ');
  return [participants, conversation.student ? '' : context].filter(Boolean).join(' · ');
}

export function filterConversations(
  conversations: ConversationSummary[],
  query: string,
  status: 'all' | 'unread' | 'active' | 'closed'
): ConversationSummary[] {
  const needle = query.trim().toLocaleLowerCase();
  return conversations.filter((conversation) => {
    const statusMatches =
      status === 'all' ||
      (status === 'unread' && conversation.unread_count > 0) ||
      (status === 'active' && !conversation.read_only) ||
      (status === 'closed' && conversation.read_only);
    if (!statusMatches) return false;
    if (!needle) return true;
    const haystack = [
      conversation.student?.display_name,
      conversation.student?.name_ar,
      conversation.student?.class_label,
      conversation.student?.class_label_ar,
      conversation.student?.grade_label,
      conversation.student?.grade_label_ar,
      conversation.context.label,
      conversation.context.label_ar,
      ...conversation.participants,
      conversation.last_message?.sender_display_name,
      conversation.last_message?.body
    ]
      .filter(Boolean)
      .join(' ')
      .toLocaleLowerCase();
    return haystack.includes(needle);
  });
}

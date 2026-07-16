import type { ConversationSummary } from './types';

export function conversationTitle(conversation: ConversationSummary): string {
  if (conversation.student?.display_name) return conversation.student.display_name;
  return conversation.participants.join(', ') || 'Conversation';
}

export function conversationSubtitle(conversation: ConversationSummary): string {
  const context = conversation.context.label?.trim();
  const participants = conversation.participants.join(', ');
  return [participants, context].filter(Boolean).join(' · ');
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

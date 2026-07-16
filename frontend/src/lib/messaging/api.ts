import { api } from '$lib/api';
import type {
  ConversationDetail,
  InboxPage,
  MessageItem,
  MessagePage,
  MessagingMembership,
  RecipientResults
} from './types';

function contextHeaders(membership: MessagingMembership): HeadersInit {
  return {
    'X-School-Id': String(membership.school_id),
    'X-Membership-Id': String(membership.membership_id)
  };
}

function queryPath(path: string, values: Record<string, string | boolean | number | null | undefined>) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== null && value !== undefined && value !== '') {
      params.set(key, String(value));
    }
  }
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

export function errorStatus(error: unknown): number | undefined {
  return (error as Error & { status?: number })?.status;
}

export const messagingApi = {
  inbox(
    membership: MessagingMembership,
    options: { cursor?: string | null; unreadOnly?: boolean; limit?: number } = {}
  ): Promise<InboxPage> {
    return api.get(
      queryPath('/messaging/inbox', {
        cursor: options.cursor,
        unread_only: options.unreadOnly || undefined,
        limit: options.limit ?? 50
      }),
      { headers: contextHeaders(membership) }
    );
  },

  unreadCount(membership: MessagingMembership): Promise<{ total: number; conversations: number }> {
    return api.get('/messaging/unread-count', { headers: contextHeaders(membership) });
  },

  recipients(membership: MessagingMembership, q = ''): Promise<RecipientResults> {
    return api.get(queryPath('/messaging/recipients', { q }), {
      headers: contextHeaders(membership)
    });
  },

  createStudentConversation(membership: MessagingMembership, studentId: number) {
    return api.post(
      '/messaging/conversations',
      { kind: 'student_staff', student_id: studentId },
      { headers: contextHeaders(membership) }
    ) as Promise<{ conversation_id: string; status: string }>;
  },

  createStaffConversation(membership: MessagingMembership, otherMembershipId: number) {
    return api.post(
      '/messaging/conversations',
      { kind: 'staff_direct', other_staff_membership_id: otherMembershipId },
      { headers: contextHeaders(membership) }
    ) as Promise<{ conversation_id: string; status: string }>;
  },

  detail(membership: MessagingMembership, conversationId: string): Promise<ConversationDetail> {
    return api.get(`/messaging/conversations/${conversationId}`, {
      headers: contextHeaders(membership)
    });
  },

  messages(
    membership: MessagingMembership,
    conversationId: string,
    cursor?: string | null
  ): Promise<MessagePage> {
    return api.get(
      queryPath(`/messaging/conversations/${conversationId}/messages`, {
        cursor,
        limit: 75
      }),
      { headers: contextHeaders(membership) }
    );
  },

  send(
    membership: MessagingMembership,
    conversationId: string,
    clientMessageId: string,
    body: string
  ): Promise<MessageItem & { duplicate: boolean }> {
    return api.post(
      `/messaging/conversations/${conversationId}/messages`,
      { client_message_id: clientMessageId, body, urgent: false },
      { headers: contextHeaders(membership) }
    ) as Promise<MessageItem & { duplicate: boolean }>;
  },

  acknowledgeRead(
    membership: MessagingMembership,
    conversationId: string,
    throughSequence: number
  ) {
    return api.post(
      `/messaging/conversations/${conversationId}/acknowledgements`,
      {
        event_type: 'read',
        through_sequence: throughSequence,
        client_ack_id: crypto.randomUUID(),
        occurred_at: new Date().toISOString()
      },
      { headers: contextHeaders(membership) }
    );
  }
};

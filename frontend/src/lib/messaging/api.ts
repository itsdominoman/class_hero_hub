import { api } from '$lib/api';
import type {
  ConversationDetail,
  InboxPage,
  MessageItem,
  MessagePage,
  MessagingMembership,
  RecipientResults
} from './types';

function contextHeaders(membership: MessagingMembership): Record<string, string> {
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
    options: { cursor?: string | null; afterSequence?: number; limit?: number } = {}
  ): Promise<MessagePage> {
    return api.get(
      queryPath(`/messaging/conversations/${conversationId}/messages`, {
        cursor: options.cursor,
        after_sequence: options.afterSequence,
        limit: options.limit ?? 75
      }),
      { headers: contextHeaders(membership) }
    );
  },

  send(
    membership: MessagingMembership,
    conversationId: string,
    clientMessageId: string,
    body: string | null,
    stagedMediaIds: string[] = [],
    stagedVoiceId: string | null = null
  ): Promise<MessageItem & { duplicate: boolean }> {
    return api.post(
      `/messaging/conversations/${conversationId}/messages`,
      { client_message_id: clientMessageId, body, staged_media_ids: stagedMediaIds, staged_voice_id: stagedVoiceId, urgent: false },
      { headers: contextHeaders(membership) }
    ) as Promise<MessageItem & { duplicate: boolean }>;
  },

  uploadPhoto(
    membership: MessagingMembership,
    conversationId: string,
    uploadId: string,
    file: File
  ): Promise<{ id: string; state: string; duplicate: boolean }> {
    const data = new FormData();
    data.append('file', file, file.name || 'photo');
    return api.upload(`/messaging/conversations/${conversationId}/media`, data, {
      headers: { ...contextHeaders(membership), 'X-Upload-Id': uploadId }
    }) as Promise<{ id: string; state: string; duplicate: boolean }>;
  },

  uploadVoice(
    membership: MessagingMembership,
    conversationId: string,
    uploadId: string,
    blob: Blob
  ): Promise<{ id: string; state: string; duration_ms: number; duplicate: boolean }> {
    const data = new FormData();
    data.append('file', blob, blob.type.includes('mp4') ? 'voice-note.m4a' : 'voice-note.webm');
    return api.upload(`/messaging/conversations/${conversationId}/voice-media`, data, {
      headers: { ...contextHeaders(membership), 'X-Upload-Id': uploadId }
    }) as Promise<{ id: string; state: string; duration_ms: number; duplicate: boolean }>;
  },

  photo(
    membership: MessagingMembership,
    conversationId: string,
    mediaId: string,
    variant: 'thumbnail' | 'full'
  ): Promise<Blob> {
    return api.download(
      `/messaging/conversations/${conversationId}/media/${mediaId}/${variant}`,
      { headers: contextHeaders(membership), cache: 'no-store' }
    );
  },

  voice(
    membership: MessagingMembership,
    conversationId: string,
    mediaId: string
  ): Promise<Blob> {
    return api.download(
      `/messaging/conversations/${conversationId}/voice-media/${mediaId}`,
      { headers: contextHeaders(membership), cache: 'no-store' }
    );
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

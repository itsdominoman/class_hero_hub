import { api } from '$lib/api';
import type {
  SafeguardingContext,
  SafeguardingMembership,
  SafeguardingPermissionsResponse,
  SafeguardingReview,
  SafeguardingSearchItem
} from './types';

function headers(membership: SafeguardingMembership): Record<string, string> {
  return {
    'X-School-Id': String(membership.school_id),
    'X-Membership-Id': String(membership.membership_id)
  };
}

function query(path: string, values: Record<string, string | number | boolean | null | undefined>) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== null && value !== undefined && value !== '') params.set(key, String(value));
  }
  const suffix = params.toString();
  return suffix ? `${path}?${suffix}` : path;
}

export const safeguardingApi = {
  availability(membership: SafeguardingMembership): Promise<{ available: boolean }> {
    return api.get('/safeguarding/availability', { headers: headers(membership) });
  },
  context(membership: SafeguardingMembership): Promise<SafeguardingContext> {
    return api.get('/safeguarding/context', { headers: headers(membership) });
  },
  search(
    membership: SafeguardingMembership,
    filters: Record<string, string | number | boolean | null | undefined>
  ): Promise<{ items: SafeguardingSearchItem[] }> {
    return api.get(query('/safeguarding/conversations', filters), { headers: headers(membership) });
  },
  startReview(
    membership: SafeguardingMembership,
    body: {
      conversation_id: string;
      reason_category: string;
      justification: string;
      acknowledgement: boolean;
      ttl_minutes?: number;
    }
  ): Promise<{ review_session_id: string; conversation_id: string; expires_at: string }> {
    return api.post('/safeguarding/reviews', body, { headers: headers(membership) });
  },
  review(membership: SafeguardingMembership, sessionId: string): Promise<SafeguardingReview> {
    return api.get(`/safeguarding/reviews/${sessionId}`, { headers: headers(membership) });
  },
  endReview(membership: SafeguardingMembership, sessionId: string) {
    return api.post(`/safeguarding/reviews/${sessionId}/end`, {}, { headers: headers(membership) });
  },
  photo(membership: SafeguardingMembership, sessionId: string, mediaId: string, variant: 'thumbnail' | 'full') {
    return api.download(`/safeguarding/reviews/${sessionId}/media/${mediaId}/${variant}`, {
      headers: headers(membership), cache: 'no-store'
    });
  },
  voice(membership: SafeguardingMembership, sessionId: string, mediaId: string) {
    return api.download(`/safeguarding/reviews/${sessionId}/voice-media/${mediaId}`, {
      headers: headers(membership), cache: 'no-store'
    });
  },
  restriction(membership: SafeguardingMembership, sessionId: string, body: Record<string, unknown>) {
    return api.post(`/safeguarding/reviews/${sessionId}/restriction`, body, { headers: headers(membership) });
  },
  removeRestriction(membership: SafeguardingMembership, sessionId: string, body: Record<string, unknown>) {
    return api.post(`/safeguarding/reviews/${sessionId}/restriction/remove`, body, { headers: headers(membership) });
  },
  close(membership: SafeguardingMembership, sessionId: string, body: Record<string, unknown>) {
    return api.post(`/safeguarding/reviews/${sessionId}/close`, body, { headers: headers(membership) });
  },
  reopen(membership: SafeguardingMembership, sessionId: string, body: Record<string, unknown>) {
    return api.post(`/safeguarding/reviews/${sessionId}/reopen`, body, { headers: headers(membership) });
  },
  tombstone(membership: SafeguardingMembership, sessionId: string, messageId: string, body: Record<string, unknown>) {
    return api.post(`/safeguarding/reviews/${sessionId}/messages/${messageId}/tombstone`, body, { headers: headers(membership) });
  },
  restore(membership: SafeguardingMembership, sessionId: string, messageId: string, body: Record<string, unknown>) {
    return api.post(`/safeguarding/reviews/${sessionId}/messages/${messageId}/restore`, body, { headers: headers(membership) });
  },
  addNote(membership: SafeguardingMembership, sessionId: string, body: string) {
    return api.post(`/safeguarding/reviews/${sessionId}/notes`, { body }, { headers: headers(membership) });
  },
  addFlag(membership: SafeguardingMembership, sessionId: string, body: Record<string, unknown>) {
    return api.post(`/safeguarding/reviews/${sessionId}/flags`, body, { headers: headers(membership) });
  },
  updateFlag(membership: SafeguardingMembership, sessionId: string, flagId: string, body: Record<string, unknown>) {
    return api.post(`/safeguarding/reviews/${sessionId}/flags/${flagId}/status`, body, { headers: headers(membership) });
  },
  export(membership: SafeguardingMembership, sessionId: string, body: Record<string, unknown>) {
    return api.post(`/safeguarding/reviews/${sessionId}/exports`, body, { headers: headers(membership) });
  },
  downloadExport(membership: SafeguardingMembership, exportId: string) {
    return api.download(`/safeguarding/exports/${exportId}/download`, { headers: headers(membership), cache: 'no-store' });
  },
  permissions(membership: SafeguardingMembership): Promise<SafeguardingPermissionsResponse> {
    return api.get('/safeguarding/permissions', { headers: headers(membership) });
  },
  grantPermission(membership: SafeguardingMembership, body: Record<string, unknown>) {
    return api.post('/safeguarding/permissions', body, { headers: headers(membership) });
  },
  revokePermission(membership: SafeguardingMembership, grantId: string, reason: string) {
    return api.post(`/safeguarding/permissions/${grantId}/revoke`, { reason }, { headers: headers(membership) });
  }
};

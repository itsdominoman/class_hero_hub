import type { SessionMembership } from "$lib/roleRouting";

export type SafeguardingMembership = SessionMembership;

export type SafeguardingNamedOption = {
  id: number;
  name: string;
  name_ar?: string | null;
};

export type SafeguardingSchoolContext = {
  class_section: SafeguardingNamedOption;
  grade_level: SafeguardingNamedOption;
  branch: SafeguardingNamedOption;
};

export type SafeguardingContext = {
  school: { id: number; name: string; timezone: string };
  reviewer: {
    user_id: number;
    membership_id: number;
    name: string;
    role: string;
  };
  permissions: string[];
  review_ttl_minutes: number;
  audit_notice: true;
  filters: {
    branches: SafeguardingNamedOption[];
    grade_levels: SafeguardingNamedOption[];
    class_sections: Array<
      SafeguardingNamedOption & { branch_id: number; grade_level_id: number }
    >;
  };
};

export type SafeguardingSearchItem = {
  conversation_id: string;
  reference: string;
  kind: string;
  status: string;
  participant_state: "active" | "read_only" | "closed";
  restricted: boolean;
  flag_count: number;
  student: { id: number; display_name: string; name_ar?: string | null } | null;
  school_context: SafeguardingSchoolContext | null;
  participants: Array<{
    display_name: string;
    kind: string;
    role?: string | null;
    side: string;
  }>;
  branch_id: number | null;
  branch: SafeguardingNamedOption | null;
  last_activity_at: string;
};

export type SafeguardingPhoto = {
  id: string;
  sort_order: number;
  content_type: string | null;
  full_bytes: number;
  thumbnail_bytes: number;
  thumbnail_available: boolean;
  full_available: boolean;
};

export type SafeguardingVoice = {
  id: string;
  content_type: "audio/mp4";
  size_bytes: number;
  duration_ms: number;
  codec: "aac";
  container: "mp4";
  available: boolean;
  transcription: { available: false; state: "not_requested" };
};

export type SafeguardingReview = {
  mode: "safeguarding_review";
  review: {
    id: string;
    reason_category: string;
    justification: string;
    started_at: string;
    expires_at: string;
    audited: true;
  };
  reviewer: {
    user_id: number;
    membership_id: number;
    name: string;
    role: string;
  };
  school: { id: number; name: string; timezone: string };
  permissions: string[];
  conversation: {
    id: string;
    reference: string;
    kind: string;
    status: string;
    restriction_type: string | null;
    reopening_requires_approval: boolean;
    created_at: string;
    last_message_sequence: number;
    student: {
      id: number;
      display_name: string;
      name_ar?: string | null;
    } | null;
    school_context: SafeguardingSchoolContext | null;
    branch: SafeguardingNamedOption | null;
    participants: Array<{
      reference: string;
      display_name: string;
      kind: string;
      role?: string | null;
      side: string;
      joined_at: string;
      left_at: string | null;
      receipt_cursor: { delivered_sequence: number; read_sequence: number };
    }>;
  };
  messages: Array<{
    id: string;
    sequence: number;
    sender_display_name: string;
    sender_kind: string | null;
    sender_role?: string | null;
    sender_side: string | null;
    message_type: "standard" | "voice_note";
    body: string | null;
    state: string;
    urgent: boolean;
    created_at: string;
    photos: SafeguardingPhoto[];
    voice_note: SafeguardingVoice | null;
    flags: Array<{
      id: string;
      category: string;
      severity: string;
      status: string;
    }>;
  }>;
  next_after_sequence: number | null;
  receipt_evidence: Array<Record<string, unknown>>;
  conversation_flags: Array<{
    id: string;
    message_id: string | null;
    category: string;
    severity: string;
    status: string;
    internal_note: string | null;
    assigned_membership_id: number | null;
    created_at: string;
    resolution_note: string | null;
  }>;
  internal_notes: Array<{
    id: string;
    body: string;
    author_membership_id: number;
    correction_of_note_id: string | null;
    created_at: string;
  }>;
  moderation_history: Array<Record<string, unknown>>;
  audit_history: Array<Record<string, unknown>>;
  exports: Array<{
    id: string;
    mode: string;
    state: string;
    size_bytes: number | null;
    artifact_sha256: string | null;
    manifest_sha256: string | null;
    expires_at: string;
    download_count: number;
    max_downloads: number;
  }>;
  capabilities: {
    can_moderate: boolean;
    can_export: boolean;
    has_composer: false;
  };
};

export type SafeguardingPermissionsResponse = {
  available_permissions: string[];
  memberships: Array<{
    membership_id: number;
    name: string;
    role: string;
    active: boolean;
    branch: SafeguardingNamedOption | null;
    permissions: Array<{ id: string; permission: string; granted_at: string }>;
  }>;
};

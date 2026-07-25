export type BehaviourAwardPayload = {
  school_id: number;
  student_ids: number[];
  category_id: number;
  note?: string | null;
  context_type?: string;
  class_section_id?: number | null;
  subject_group_id?: number | null;
  duty_context?: string | null;
};

export type PendingAwardRequest = { fingerprint: string; key: string };

export function behaviourAwardFingerprint(payload: BehaviourAwardPayload): string {
  const note = payload.note?.trim() || null;
  return JSON.stringify({
    school_id: payload.school_id,
    student_ids: [...new Set(payload.student_ids)].sort((left, right) => left - right),
    category_id: payload.category_id,
    note,
    context_type: payload.context_type ?? 'general',
    class_section_id: payload.class_section_id ?? null,
    subject_group_id: payload.subject_group_id ?? null,
    duty_context: payload.duty_context ?? null
  });
}

export function awardRequest(
  payload: BehaviourAwardPayload,
  previous: PendingAwardRequest | null,
  createKey: () => string = () => crypto.randomUUID()
): PendingAwardRequest {
  const fingerprint = behaviourAwardFingerprint(payload);
  return previous?.fingerprint === fingerprint
    ? previous
    : { fingerprint, key: createKey() };
}

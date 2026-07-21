#!/usr/bin/env python3
"""Seed and measure a deterministic, disposable Messaging v1 school dataset.

The target must be an otherwise empty database named with the configured
`chh_scale_` prefix. Media rows model realistic derivative sizes but deliberately
do not create protected files; file custody is exercised by separate tests.
"""
from __future__ import annotations

import json
import os
import statistics
import time
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.migration_guard import is_protected, parse_target


STUDENTS = 1_000
GUARDIANS = 2_000
STAFF = 75
CONVERSATIONS = 6_000
MESSAGES_PER_CONVERSATION = 20


def _timed(connection, sql: str, parameters: dict, repeats: int = 30) -> dict:
    values = []
    rows = 0
    for _ in range(repeats):
        started = time.perf_counter()
        result = connection.execute(text(sql), parameters)
        rows = len(result.fetchall())
        values.append((time.perf_counter() - started) * 1000)
    ordered = sorted(values)
    return {
        "rows": rows,
        "samples": repeats,
        "p50_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[max(int(len(ordered) * 0.95) - 1, 0)], 3),
        "max_ms": round(max(ordered), 3),
    }


def main() -> int:
    url = os.getenv("MESSAGING_SCALE_DATABASE_URL", "")
    database_name = os.getenv("MESSAGING_SCALE_DATABASE", "")
    if not url and database_name:
        source_url = os.getenv("DATABASE_URL", "")
        if not source_url:
            raise SystemExit("DATABASE_URL is required when MESSAGING_SCALE_DATABASE is used")
        url = make_url(source_url).set(database=database_name).render_as_string(hide_password=False)
    if not url:
        raise SystemExit("MESSAGING_SCALE_DATABASE_URL or MESSAGING_SCALE_DATABASE is required")
    target = parse_target(url, source="environment:MESSAGING_SCALE_DATABASE_URL")
    prefix = os.getenv("MESSAGING_SCALE_DATABASE_PREFIX", "chh_scale_")
    if is_protected(target) or not target.database.startswith(prefix):
        raise SystemExit(f"Refusing scale target {target.label}; database must start with {prefix!r} and be unprotected")
    engine = create_engine(url, pool_pre_ping=True)
    started = time.perf_counter()
    with engine.begin() as connection:
        existing = connection.execute(text("SELECT count(*) FROM schools")).scalar_one()
        if existing:
            raise SystemExit("Scale target must not contain schools")
        school_id = connection.execute(text("""
            INSERT INTO schools (messaging_remote_ref, name, slug, timezone, locale_default, status)
            VALUES (md5('scale-school')::uuid, 'Representative Scale School', 'scale-school', 'Asia/Muscat', 'en', 'active')
            RETURNING id
        """)).scalar_one()
        connection.execute(text("""
            INSERT INTO users (email, name, locale, status)
            SELECT 'scale-staff-' || g || '@example.invalid',
                   'Staff ' || g || CASE WHEN g % 7 = 0 THEN ' - SEN Team' WHEN g % 5 = 0 THEN ' - Arabic' ELSE '' END,
                   CASE WHEN g % 4 = 0 THEN 'ar' ELSE 'en' END, 'active'
            FROM generate_series(1, :staff) g
        """), {"staff": STAFF})
        connection.execute(text("""
            INSERT INTO users (email, name, locale, status)
            SELECT 'scale-guardian-' || g || '@example.invalid', 'Guardian ' || g,
                   CASE WHEN g % 3 = 0 THEN 'ar' ELSE 'en' END, 'active'
            FROM generate_series(1, :guardians) g
        """), {"guardians": GUARDIANS})
        connection.execute(text("""
            INSERT INTO memberships (school_id, user_id, role, status)
            SELECT :school, id, CASE WHEN email LIKE 'scale-staff-1@%' THEN 'school_admin' ELSE 'teacher' END, 'active'
            FROM users WHERE email LIKE 'scale-staff-%@example.invalid'
        """), {"school": school_id})
        connection.execute(text("""
            INSERT INTO students (school_id, external_ref, first_name, last_name, preferred_name, status)
            SELECT :school, 'S-' || lpad(g::text, 5, '0'), 'Student', g::text,
                   CASE WHEN g % 6 = 0 THEN 'Learner ' || g ELSE NULL END, 'active'
            FROM generate_series(1, :students) g
        """), {"school": school_id, "students": STUDENTS})
        connection.execute(text("""
            INSERT INTO conversations (
                public_id, school_id, kind, student_id, primary_staff_membership_id,
                internal_guardian_user_id, context_label, context_label_ar, status,
                last_message_sequence, last_message_at, created_at, closed_at, closed_reason
            )
            SELECT md5('scale-conversation-' || g)::uuid, :school, 'guardian_direct',
                   (SELECT id FROM students WHERE school_id=:school ORDER BY id OFFSET ((g-1) % :students) LIMIT 1),
                   (SELECT id FROM memberships WHERE school_id=:school ORDER BY id OFFSET ((g-1) % :staff) LIMIT 1),
                   (SELECT id FROM users WHERE email LIKE 'scale-guardian-%@example.invalid' ORDER BY id OFFSET ((g-1) % :guardians) LIMIT 1),
                   'Branch ' || (1 + (g % 3)) || ' · Grade ' || (1 + (g % 12)),
                   'الفرع ' || (1 + (g % 3)) || ' · الصف ' || (1 + (g % 12)),
                   'archived', :messages,
                   now() - ((g % 1095) || ' days')::interval,
                   now() - ((g % 1095 + 30) || ' days')::interval,
                   now() - ((g % 1095) || ' days')::interval, 'scale_closed'
            FROM generate_series(1, :conversations) g
        """), {
            "school": school_id, "students": STUDENTS, "staff": STAFF,
            "guardians": GUARDIANS, "messages": MESSAGES_PER_CONVERSATION,
            "conversations": CONVERSATIONS,
        })
        connection.execute(text("""
            WITH numbered AS (SELECT id, primary_staff_membership_id, internal_guardian_user_id, row_number() OVER (ORDER BY id) n FROM conversations WHERE school_id=:school)
            INSERT INTO conversation_participants (conversation_id, participant_kind, user_id, membership_id, side, display_name_snapshot, joined_at)
            SELECT n.id, 'staff', m.user_id, m.id, 'staff', 'School staff ' || n.n, now() - interval '3 years'
            FROM numbered n JOIN memberships m ON m.id=n.primary_staff_membership_id
        """), {"school": school_id})
        connection.execute(text("""
            WITH numbered AS (SELECT id, internal_guardian_user_id, row_number() OVER (ORDER BY id) n FROM conversations WHERE school_id=:school)
            INSERT INTO conversation_participants (conversation_id, participant_kind, user_id, side, display_name_snapshot, joined_at)
            SELECT n.id, 'chh_guardian', n.internal_guardian_user_id, 'guardian', 'Family contact ' || n.n, now() - interval '3 years'
            FROM numbered n
        """), {"school": school_id})
        connection.execute(text("""
            INSERT INTO messages (
                public_id, school_id, conversation_id, sequence, sender_participant_id,
                sender_display_name_snapshot, client_message_id, message_type, body, state, urgent, created_at
            )
            SELECT md5('scale-message-' || c.id || '-' || s)::uuid, :school, c.id, s,
                   CASE WHEN s % 2 = 1 THEN staff.id ELSE guardian.id END,
                   CASE WHEN s % 2 = 1 THEN staff.display_name_snapshot ELSE guardian.display_name_snapshot END,
                   md5('scale-client-' || c.id || '-' || s)::uuid,
                   CASE WHEN s % 20 = 0 THEN 'voice_note' ELSE 'standard' END,
                   CASE WHEN s % 20 = 0 THEN NULL
                        WHEN s % 9 = 0 THEN 'Follow-up ' || s || ': please review the attached class update.'
                        WHEN s % 5 = 0 THEN 'Thank you. We have received this school message.'
                        ELSE 'School conversation update ' || s || ' for reference.' END,
                   'active',
                   (s % 41 = 0), c.created_at + (s || ' hours')::interval
            FROM conversations c
            JOIN conversation_participants staff ON staff.conversation_id=c.id AND staff.side='staff'
            JOIN conversation_participants guardian ON guardian.conversation_id=c.id AND guardian.side='guardian'
            CROSS JOIN generate_series(1, :messages) s
            WHERE c.school_id=:school
        """), {"school": school_id, "messages": MESSAGES_PER_CONVERSATION})
        connection.execute(text("""
            INSERT INTO message_receipt_events (conversation_id, participant_id, event_type, through_sequence, client_ack_id, device_session_ref, occurred_at, recorded_at)
            SELECT c.id, p.id, kind.event_type, kind.seq,
                   md5('scale-receipt-' || c.id || '-' || p.id || '-' || kind.event_type || '-' || kind.seq)::uuid,
                   'scale-device-' || (p.id % 200), c.last_message_at, c.last_message_at
            FROM conversations c JOIN conversation_participants p ON p.conversation_id=c.id
            CROSS JOIN (VALUES ('delivered', 10), ('delivered', 20), ('read', 5), ('read', 15)) kind(event_type, seq)
            WHERE c.school_id=:school
        """), {"school": school_id})
        connection.execute(text("""
            INSERT INTO messaging_audit_events (event_id, school_id, actor_kind, event_type, conversation_id, detail, occurred_at)
            SELECT md5('scale-audit-' || c.id)::uuid, :school, 'system', 'safeguarding.scale_review', c.id,
                   jsonb_build_object('reason_category', 'scale_validation'), c.last_message_at
            FROM conversations c WHERE c.school_id=:school AND c.id % 10 = 0
        """), {"school": school_id})
        connection.execute(text("""
            INSERT INTO message_media (
                public_id, client_upload_id, school_id, conversation_id, message_id, uploaded_by_participant_id,
                sort_order, state, storage_backend, content_type, full_bytes, thumbnail_bytes, width, height,
                thumbnail_width, thumbnail_height, source_checksum_sha256, checksum_sha256,
                original_filename_safe, metadata_stripped, created_at, attached_at, expires_at,
                archive_full_storage_key, archive_thumbnail_storage_key, archive_full_sha256,
                archive_thumbnail_sha256, archived_at, archive_verified_at, hot_deleted_at
            )
            SELECT md5('scale-photo-' || m.id)::uuid, md5('scale-upload-photo-' || m.id)::uuid,
                   :school, m.conversation_id, m.id, m.sender_participant_id, 0, 'archived', 'local', 'image/jpeg',
                   350000 + (m.id % 50000), 25000 + (m.id % 5000), 1280, 960, 320, 240,
                   repeat('a',64), repeat('b',64), 'class-update.jpg', true, m.created_at, m.created_at,
                   m.created_at + interval '1 day', 'scale/photo/' || m.id || '-full', 'scale/photo/' || m.id || '-thumb',
                   repeat('b',64), repeat('c',64), m.created_at + interval '1 year', m.created_at + interval '1 year', m.created_at + interval '1 year'
            FROM messages m WHERE m.school_id=:school AND m.sequence = 10
        """), {"school": school_id})
        connection.execute(text("""
            INSERT INTO message_voice_media (
                public_id, client_upload_id, school_id, conversation_id, message_id, uploaded_by_participant_id,
                state, storage_backend, content_type, size_bytes, duration_ms, codec, container,
                source_checksum_sha256, checksum_sha256, metadata_stripped, transcription_state,
                created_at, attached_at, expires_at, archive_storage_key, archive_sha256,
                archived_at, archive_verified_at, hot_deleted_at
            )
            SELECT md5('scale-voice-' || m.id)::uuid, md5('scale-upload-voice-' || m.id)::uuid,
                   :school, m.conversation_id, m.id, m.sender_participant_id, 'archived', 'local', 'audio/mp4',
                   180000 + (m.id % 40000), 12000 + (m.id % 20000), 'aac', 'mp4', repeat('d',64), repeat('e',64),
                   true, 'not_requested', m.created_at, m.created_at, m.created_at + interval '1 day',
                   'scale/voice/' || m.id || '.m4a', repeat('e',64), m.created_at + interval '1 year',
                   m.created_at + interval '1 year', m.created_at + interval '1 year'
            FROM messages m WHERE m.school_id=:school AND m.sequence = 20
        """), {"school": school_id})
        connection.execute(text("""
            INSERT INTO notification_outbox (
                event_id, school_id, message_id, recipient_kind, recipient_user_id,
                recipient_participant_id, channel, template_key, template_args,
                deep_link, policy_version, state, eligible_at, scheduler_check_at,
                attempt_count, next_attempt_at, dedupe_key, created_at
            )
            SELECT md5('scale-notification-' || m.id)::uuid, :school, m.id,
                   'chh_user', staff.user_id, staff.id, 'push',
                   'messaging.staff_to_family', jsonb_build_object('conversation_id', m.conversation_id),
                   '/messages/' || c.public_id, 1,
                   CASE WHEN m.conversation_id % 4 = 0 THEN 'pending'
                        WHEN m.conversation_id % 4 = 1 THEN 'held'
                        WHEN m.conversation_id % 4 = 2 THEN 'failed' ELSE 'dead' END,
                   now() - interval '5 minutes', now() - interval '5 minutes', 1,
                   now() - interval '1 minute', 'scale-notification-' || m.id, m.created_at
            FROM messages m
            JOIN conversations c ON c.id=m.conversation_id
            JOIN conversation_participants staff ON staff.conversation_id=c.id AND staff.side='staff'
            WHERE m.school_id=:school AND m.sequence=20
        """), {"school": school_id})
        connection.execute(text("ANALYZE"))

    seed_seconds = time.perf_counter() - started
    with engine.connect() as connection:
        representative_conversation = connection.execute(text("SELECT id FROM conversations WHERE school_id=:school ORDER BY id OFFSET 3000 LIMIT 1"), {"school": school_id}).scalar_one()
        representative_guardian = connection.execute(text("SELECT internal_guardian_user_id FROM conversations WHERE id=:id"), {"id": representative_conversation}).scalar_one()
        probes = {
            "inbox_listing": ("SELECT id, public_id, status, last_message_at FROM conversations WHERE school_id=:school AND internal_guardian_user_id=:guardian ORDER BY last_message_at DESC, id DESC LIMIT 50", {"school": school_id, "guardian": representative_guardian}),
            "message_pagination": ("SELECT id, public_id, sequence, sender_participant_id, message_type, state, created_at FROM messages WHERE conversation_id=:conversation AND sequence < 21 ORDER BY sequence DESC LIMIT 50", {"conversation": representative_conversation}),
            "receipt_aggregation": ("SELECT participant_id, event_type, max(through_sequence) FROM message_receipt_events WHERE conversation_id=:conversation GROUP BY participant_id, event_type", {"conversation": representative_conversation}),
            "notification_targeting": ("SELECT o.id, o.state FROM notification_outbox o JOIN users u ON u.id=o.recipient_user_id JOIN memberships m ON m.user_id=u.id AND m.school_id=o.school_id WHERE o.school_id=:school AND u.status='active' AND m.status='active' ORDER BY o.id LIMIT 100", {"school": school_id}),
            "safeguarding_search": ("SELECT c.id, c.public_id, c.status, c.last_message_at FROM conversations c JOIN students s ON s.id=c.student_id WHERE c.school_id=:school AND (s.first_name ILIKE :term OR s.last_name ILIKE :term) ORDER BY c.last_message_at DESC LIMIT 50", {"school": school_id, "term": "%Student%"}),
            "safeguarding_review_projection": ("SELECT m.id, m.sequence, m.message_type, m.state, p.side, p.display_name_snapshot FROM messages m JOIN conversation_participants p ON p.id=m.sender_participant_id WHERE m.conversation_id=:conversation ORDER BY m.sequence LIMIT 100", {"conversation": representative_conversation}),
            "export_manifest_selection": ("SELECT m.id, m.public_id, m.sequence, pm.id AS photo_id, vm.id AS voice_id FROM messages m LEFT JOIN message_media pm ON pm.message_id=m.id LEFT JOIN message_voice_media vm ON vm.message_id=m.id WHERE m.conversation_id=:conversation ORDER BY m.sequence LIMIT 100", {"conversation": representative_conversation}),
            "retention_preview_candidates": ("SELECT count(*), coalesce(sum(length(m.body)),0) FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE m.school_id=:school AND c.status <> 'active' AND m.created_at < now() - interval '2 years' AND m.retention_disposed_at IS NULL", {"school": school_id}),
            "archive_selection": ("SELECT id, full_bytes, thumbnail_bytes FROM message_media WHERE school_id=:school AND state IN ('attached','archived') AND created_at < now() - interval '365 days' ORDER BY id LIMIT 100", {"school": school_id}),
            "worker_claim_selection": ("SELECT id FROM notification_outbox WHERE state IN ('pending','failed') AND next_attempt_at <= now() ORDER BY next_attempt_at,id FOR UPDATE SKIP LOCKED LIMIT 100", {}),
            "operations_counts": ("SELECT state, count(*) FROM notification_outbox WHERE school_id=:school GROUP BY state", {"school": school_id}),
        }
        results = {name: _timed(connection, sql, params) for name, (sql, params) in probes.items()}
        counts = dict(connection.execute(text("""
            SELECT 'students', count(*) FROM students WHERE school_id=:school UNION ALL
            SELECT 'staff', count(*) FROM memberships WHERE school_id=:school UNION ALL
            SELECT 'guardians', count(*) FROM users WHERE email LIKE 'scale-guardian-%@example.invalid' UNION ALL
            SELECT 'conversations', count(*) FROM conversations WHERE school_id=:school UNION ALL
            SELECT 'messages', count(*) FROM messages WHERE school_id=:school UNION ALL
            SELECT 'receipts', count(*) FROM message_receipt_events r JOIN conversations c ON c.id=r.conversation_id WHERE c.school_id=:school UNION ALL
            SELECT 'photos', count(*) FROM message_media WHERE school_id=:school UNION ALL
            SELECT 'voice_notes', count(*) FROM message_voice_media WHERE school_id=:school UNION ALL
            SELECT 'notification_jobs', count(*) FROM notification_outbox WHERE school_id=:school UNION ALL
            SELECT 'safeguarding_audits', count(*) FROM messaging_audit_events WHERE school_id=:school
        """), {"school": school_id}).all())
        database_size = connection.execute(text("SELECT pg_database_size(current_database())")).scalar_one()
        assumed_media_bytes = connection.execute(text("SELECT coalesce(sum(full_bytes + thumbnail_bytes),0) FROM message_media WHERE school_id=:school"), {"school": school_id}).scalar_one()
        assumed_media_bytes += connection.execute(text("SELECT coalesce(sum(size_bytes),0) FROM message_voice_media WHERE school_id=:school"), {"school": school_id}).scalar_one()
    print(json.dumps({
        "target": target.label,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed_seconds": round(seed_seconds, 3),
        "counts": {key: int(value) for key, value in counts.items()},
        "database_bytes": int(database_size),
        "assumed_protected_media_bytes": int(assumed_media_bytes),
        "probes": results,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

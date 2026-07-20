import hashlib
import json
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import UUID, uuid4

import pytest

from app import message_media_service, message_voice_service, safeguarding_service
from app.models_school import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageReceiptEvent,
    MessagingAuditEvent,
    MessagingEvidenceExport,
    MessagingModerationAction,
    MessagingPermissionGrant,
    NotificationOutbox,
    SafeguardingFlag,
    SafeguardingInternalNote,
    SafeguardingReviewSession,
)
from app.safeguarding_service import cleanup_expired_safeguarding_state
from test_messaging_api import (
    _create_teacher_thread,
    _headers,
    _jpeg_bytes,
    _school_world,
    _voice_tone_bytes,
    client,
    db,
)


REVIEW = "messaging.safeguarding_review"
MODERATE = "messaging.moderate"
EXPORT = "messaging.export_evidence"
EXPORT_NOTES = "messaging.export_internal_notes"
MANAGE = "messaging.manage_safeguarding_permissions"


def _grant(db, world, membership, *permissions):
    rows = []
    for permission in permissions:
        row = MessagingPermissionGrant(
            school_id=world["school"].id,
            membership_id=membership.id,
            permission=permission,
            granted_by_membership_id=membership.id,
            grant_reason="Authorised test assignment",
        )
        db.add(row)
        rows.append(row)
    db.commit()
    return rows


def _staff_headers(world, membership=None):
    membership = membership or world["admin"]
    user = next(user for user in world["users"].values() if user.id == membership.user_id)
    return _headers(user, world["school"], membership)


def _send_text(client, world, conversation_id, body="Evidence message"):
    response = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=_headers(world["users"]["teacher"], world["school"], world["teacher"]),
        json={"client_message_id": str(uuid4()), "body": body},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _start_review(client, world, conversation_id, *, headers=None, justification="Reported concern requires an authorised review"):
    response = client.post(
        "/api/safeguarding/reviews",
        headers=headers or _staff_headers(world),
        json={
            "conversation_id": conversation_id,
            "reason_category": "reported_concern",
            "justification": justification,
            "acknowledgement": True,
            "ttl_minutes": 30,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["review_session_id"]


def _review(client, world, session_id, *, headers=None):
    response = client.get(
        f"/api/safeguarding/reviews/{session_id}",
        headers=headers or _staff_headers(world),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _moderation(reason="Audited safeguarding intervention required"):
    return {
        "reason_category": "safeguarding_investigation",
        "confidential_reason": reason,
        "participant_safe_reason": "This conversation is currently read-only.",
    }


def test_authorisation_metadata_search_and_review_have_no_participant_receipt_unread_or_push_side_effects(db, client):
    world = _school_world(db, "safeguarding-review")
    other = _school_world(db, "safeguarding-other")
    conversation_id = _create_teacher_thread(client, world)
    sent = _send_text(client, world, conversation_id, "Sensitive evidence phrase")
    admin_headers = _staff_headers(world)
    teacher_headers = _staff_headers(world, world["teacher"])

    assert client.get("/api/safeguarding/availability", headers=teacher_headers).json() == {"available": False}
    assert client.get("/api/safeguarding/conversations", headers=teacher_headers).status_code == 403
    assert client.get("/api/safeguarding/conversations", headers=admin_headers).status_code == 403

    _grant(db, world, world["admin"], REVIEW)
    assert client.get("/api/safeguarding/availability", headers=admin_headers).json() == {"available": True}
    search = client.get(
        "/api/safeguarding/conversations?student=Student&participant_role=staff&class_grade=KG1",
        headers=admin_headers,
    )
    assert search.status_code == 200, search.text
    assert search.json()["items"][0]["conversation_id"] == conversation_id
    assert "Sensitive evidence phrase" not in search.text
    reference = search.json()["items"][0]["reference"]
    by_reference = client.get(
        f"/api/safeguarding/conversations?reference={reference}", headers=admin_headers
    )
    assert [row["conversation_id"] for row in by_reference.json()["items"]] == [conversation_id]

    cross_school_headers = {
        **admin_headers,
        "X-School-Id": str(other["school"].id),
        "X-Membership-Id": str(world["admin"].id),
    }
    assert client.get("/api/safeguarding/conversations", headers=cross_school_headers).status_code == 403
    assert client.get("/api/safeguarding/conversations", headers={**admin_headers, "X-School-Id": "999999"}).status_code == 403

    conversation = db.query(Conversation).filter(Conversation.public_id == UUID(conversation_id)).one()
    participant_rows = db.query(ConversationParticipant).filter_by(conversation_id=conversation.id).all()
    participant_ids = [row.id for row in participant_rows]
    participant_membership_ids = {row.membership_id for row in participant_rows if row.membership_id is not None}
    receipt_snapshot = db.query(MessageReceiptEvent).filter_by(conversation_id=conversation.id).count()
    push_snapshot = db.query(NotificationOutbox).filter_by(message_id=db.query(Message).filter_by(public_id=UUID(sent["id"])).one().id).count()
    unread_snapshot = client.get(
        "/api/guardian/messaging/unread-count",
        headers=_headers(world["users"]["guardian"], world["school"]),
    ).json()["total"]

    invalid = client.post(
        "/api/safeguarding/reviews",
        headers=admin_headers,
        json={
            "conversation_id": conversation_id,
            "reason_category": "reported_concern",
            "justification": "aaaaaaa",
            "acknowledgement": True,
        },
    )
    assert invalid.status_code == 422
    missing_ack = client.post(
        "/api/safeguarding/reviews",
        headers=admin_headers,
        json={
            "conversation_id": conversation_id,
            "reason_category": "reported_concern",
            "justification": "Meaningful authorised justification",
            "acknowledgement": False,
        },
    )
    assert missing_ack.status_code == 422

    session_id = _start_review(client, world, conversation_id)
    detail = _review(client, world, session_id)
    assert detail["mode"] == "safeguarding_review"
    assert detail["capabilities"]["has_composer"] is False
    assert detail["messages"][0]["body"] == "Sensitive evidence phrase"
    assert world["admin"].id not in participant_membership_ids
    assert [row.id for row in db.query(ConversationParticipant).filter_by(conversation_id=conversation.id).all()] == participant_ids
    assert db.query(MessageReceiptEvent).filter_by(conversation_id=conversation.id).count() == receipt_snapshot
    assert db.query(NotificationOutbox).filter_by(message_id=db.query(Message).filter_by(public_id=UUID(sent["id"])).one().id).count() == push_snapshot
    assert client.get(
        "/api/guardian/messaging/unread-count",
        headers=_headers(world["users"]["guardian"], world["school"]),
    ).json()["total"] == unread_snapshot
    assert db.query(MessagingAuditEvent).filter_by(event_type="safeguarding.conversation_opened").count() == 1


def test_review_expiry_revocation_conversation_scope_and_inactive_access(db, client):
    world = _school_world(db, "safeguarding-session")
    first_id = _create_teacher_thread(client, world)
    first = _send_text(client, world, first_id, "First conversation evidence")
    second = Conversation(
        school_id=world["school"].id,
        kind="student_staff",
        student_id=world["student"].id,
        primary_staff_membership_id=world["teacher"].id,
        status="archived",
    )
    db.add(second)
    db.flush()
    teacher_participant = db.query(ConversationParticipant).filter_by(
        conversation_id=db.query(Conversation).filter_by(public_id=UUID(first_id)).one().id,
        membership_id=world["teacher"].id,
    ).one()
    db.add(ConversationParticipant(
        conversation_id=second.id,
        participant_kind="staff",
        side="staff",
        user_id=world["users"]["teacher"].id,
        membership_id=world["teacher"].id,
        display_name_snapshot=teacher_participant.display_name_snapshot,
    ))
    db.commit()
    _grant(db, world, world["admin"], REVIEW, MANAGE)
    headers = _staff_headers(world)

    session_id = _start_review(client, world, first_id)
    session = db.query(SafeguardingReviewSession).filter_by(public_id=UUID(session_id)).one()
    session.started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert client.get(f"/api/safeguarding/reviews/{session_id}", headers=headers).status_code == 410
    db.refresh(session)
    assert session.end_reason == "expired"

    scoped_session = _start_review(client, world, first_id)
    assert client.post(
        f"/api/safeguarding/reviews/{scoped_session}/messages/{uuid4()}/tombstone",
        headers=headers,
        json=_moderation(),
    ).status_code == 404
    malformed = client.get("/api/safeguarding/reviews/not-a-uuid", headers=headers)
    assert malformed.status_code == 422
    revoked = client.post(
        f"/api/safeguarding/reviews/{scoped_session}/revoke",
        headers=headers,
        json={"reason": "Access no longer needed"},
    )
    assert revoked.status_code == 200, revoked.text
    assert client.get(f"/api/safeguarding/reviews/{scoped_session}", headers=headers).status_code == 410
    assert db.query(MessagingAuditEvent).filter_by(event_type="safeguarding.review_revoked").count() == 1

    world["admin"].status = "suspended"
    db.commit()
    assert client.get("/api/safeguarding/context", headers=headers).status_code == 403


def test_restrictions_close_reopen_flags_notes_and_tombstones_are_audited_and_internal(db, client, monkeypatch, tmp_path):
    monkeypatch.setattr(message_media_service, "MESSAGE_MEDIA_ROOT", tmp_path / "media")
    world = _school_world(db, "safeguarding-moderation")
    conversation_id = _create_teacher_thread(client, world)
    teacher_headers = _headers(world["users"]["teacher"], world["school"], world["teacher"])
    guardian_headers = _headers(world["users"]["guardian"], world["school"])
    uploaded = client.post(
        f"/api/messaging/conversations/{conversation_id}/media",
        headers={**teacher_headers, "X-Upload-Id": str(uuid4())},
        files={"file": ("evidence.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert uploaded.status_code == 201, uploaded.text
    media_id = uploaded.json()["id"]
    sent = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=teacher_headers,
        json={"client_message_id": str(uuid4()), "body": "Original retained text", "staged_media_ids": [media_id]},
    )
    assert sent.status_code == 200, sent.text
    message_id = sent.json()["id"]
    _grant(db, world, world["admin"], REVIEW, MODERATE)
    headers = _staff_headers(world)
    session_id = _start_review(client, world, conversation_id)

    restriction = client.post(
        f"/api/safeguarding/reviews/{session_id}/restriction",
        headers=headers,
        json={**_moderation(), "restriction_type": "family_replies", "reopening_requires_approval": True},
    )
    assert restriction.status_code == 200, restriction.text
    guardian_inbox = client.get("/api/guardian/messaging/inbox", headers=guardian_headers).json()["items"][0]
    teacher_inbox = client.get("/api/messaging/inbox", headers=teacher_headers).json()["items"][0]
    assert guardian_inbox["participant_state"] == "read_only" and guardian_inbox["read_only"] is True
    assert teacher_inbox["participant_state"] == "active" and teacher_inbox["read_only"] is False
    denied_reply = client.post(
        f"/api/guardian/messaging/conversations/{conversation_id}/messages",
        headers=guardian_headers,
        json={"client_message_id": str(uuid4()), "body": "Must be denied"},
    )
    assert denied_reply.status_code == 409
    assert _send_text(client, world, conversation_id, "Staff side remains available")["sequence"] == 2

    note_text = "Internal note that must never leave safeguarding"
    assert client.post(
        f"/api/safeguarding/reviews/{session_id}/notes",
        headers=headers,
        json={"body": note_text},
    ).status_code == 200
    assert client.post(
        f"/api/safeguarding/reviews/{session_id}/flags",
        headers=headers,
        json={"message_id": message_id, "category": "follow_up", "severity": "high", "internal_note": "Internal flag evidence"},
    ).status_code == 200
    ordinary = client.get(
        f"/api/guardian/messaging/conversations/{conversation_id}/messages", headers=guardian_headers
    )
    assert note_text not in ordinary.text
    assert "Internal flag evidence" not in ordinary.text
    assert world["users"]["admin"].name not in ordinary.text

    tombstone = client.post(
        f"/api/safeguarding/reviews/{session_id}/messages/{message_id}/tombstone",
        headers=headers,
        json=_moderation("Message removal is required for participant safety"),
    )
    assert tombstone.status_code == 200, tombstone.text
    ordinary_after = client.get(
        f"/api/guardian/messaging/conversations/{conversation_id}/messages", headers=guardian_headers
    ).json()["items"][0]
    assert ordinary_after["body"] is None and ordinary_after["photos"] == [] and ordinary_after["state"] == "tombstoned"
    assert client.get(
        f"/api/guardian/messaging/conversations/{conversation_id}/media/{media_id}/full",
        headers=guardian_headers,
    ).status_code == 404
    protected_review = _review(client, world, session_id)
    reviewed_message = next(row for row in protected_review["messages"] if row["id"] == message_id)
    assert reviewed_message["body"] == "Original retained text"
    assert reviewed_message["photos"][0]["id"] == media_id
    assert client.get(
        f"/api/safeguarding/reviews/{session_id}/media/{media_id}/full", headers=headers
    ).status_code == 200

    assert client.post(
        f"/api/safeguarding/reviews/{session_id}/messages/{message_id}/restore",
        headers=headers,
        json=_moderation("Evidence restoration was formally authorised"),
    ).status_code == 200
    assert client.post(
        f"/api/safeguarding/reviews/{session_id}/close",
        headers=headers,
        json={**_moderation(), "reopening_requires_approval": True},
    ).status_code == 200
    assert client.get("/api/guardian/messaging/inbox", headers=guardian_headers).json()["items"][0]["participant_state"] == "closed"
    assert client.post(
        f"/api/safeguarding/reviews/{session_id}/reopen",
        headers=headers,
        json={**_moderation("Reopening was approved after safeguarding review"), "remove_existing_restriction": True},
    ).status_code == 200
    actions = [row.action for row in db.query(MessagingModerationAction).order_by(MessagingModerationAction.id).all()]
    assert actions == ["restrict", "tombstone", "restore", "close", "reopen"]
    assert db.query(SafeguardingInternalNote).one().body == note_text
    assert db.query(SafeguardingFlag).one().internal_note == "Internal flag evidence"
    audit_types = {row.event_type for row in db.query(MessagingAuditEvent).all()}
    assert {"safeguarding.restrict", "safeguarding.tombstone", "safeguarding.restore", "safeguarding.close", "safeguarding.reopen", "safeguarding.internal_note_added", "safeguarding.flagged"} <= audit_types


def test_permission_management_is_school_scoped_audited_and_revocable(db, client):
    world = _school_world(db, "safeguarding-permissions")
    other = _school_world(db, "safeguarding-permissions-other")
    _grant(db, world, world["admin"], MANAGE)
    headers = _staff_headers(world)
    granted = client.post(
        "/api/safeguarding/permissions",
        headers=headers,
        json={"membership_id": world["teacher"].id, "permission": REVIEW, "reason": "Designated safeguarding reviewer"},
    )
    assert granted.status_code == 200, granted.text
    assert client.get("/api/safeguarding/context", headers=_staff_headers(world, world["teacher"])).status_code == 200
    assert client.post(
        "/api/safeguarding/permissions",
        headers=headers,
        json={"membership_id": other["teacher"].id, "permission": REVIEW, "reason": "Cross school attempt"},
    ).status_code == 404
    revoked = client.post(
        f"/api/safeguarding/permissions/{granted.json()['id']}/revoke",
        headers=headers,
        json={"reason": "Assignment ended"},
    )
    assert revoked.status_code == 200
    assert client.get("/api/safeguarding/context", headers=_staff_headers(world, world["teacher"])).status_code == 403
    assert {row.event_type for row in db.query(MessagingAuditEvent).all()} >= {
        "safeguarding.permission_granted", "safeguarding.permission_revoked"
    }


def test_voice_evidence_uses_review_authorisation_and_survives_participant_tombstone(db, client, monkeypatch, tmp_path):
    media_root = tmp_path / "protected-message-media"
    monkeypatch.setattr(message_media_service, "MESSAGE_MEDIA_ROOT", media_root)
    monkeypatch.setattr(message_voice_service, "MESSAGE_MEDIA_ROOT", media_root)
    world = _school_world(db, "safeguarding-voice")
    conversation_id = _create_teacher_thread(client, world)
    admin_headers = _headers(world["users"]["admin"], world["school"], world["admin"])
    teacher_headers = _headers(world["users"]["teacher"], world["school"], world["teacher"])
    guardian_headers = _headers(world["users"]["guardian"], world["school"])
    controls = client.get("/api/school/feature-controls", headers=admin_headers).json()["voice_notes"]
    enabled = client.put(
        "/api/school/feature-controls/voice-notes",
        headers=admin_headers,
        json={
            "enabled": True,
            "expected_control_version": controls["control_version"],
            "disclosure_version": controls["disclosure_version"],
            "acknowledged": True,
        },
    )
    assert enabled.status_code == 200, enabled.text
    uploaded = client.post(
        f"/api/messaging/conversations/{conversation_id}/voice-media",
        headers={**teacher_headers, "X-Upload-Id": str(uuid4())},
        files={"file": ("voice.wav", _voice_tone_bytes(tmp_path), "audio/wav")},
    )
    assert uploaded.status_code == 201, uploaded.text
    media_id = uploaded.json()["id"]
    sent = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=teacher_headers,
        json={"client_message_id": str(uuid4()), "body": None, "staged_voice_id": media_id},
    )
    assert sent.status_code == 200, sent.text
    message_id = sent.json()["id"]
    _grant(db, world, world["admin"], REVIEW, MODERATE)
    session_id = _start_review(client, world, conversation_id)
    detail = _review(client, world, session_id)
    assert detail["messages"][0]["voice_note"]["id"] == media_id
    review_voice_url = f"/api/safeguarding/reviews/{session_id}/voice-media/{media_id}"
    voice = client.get(review_voice_url, headers=admin_headers)
    assert voice.status_code == 200 and voice.headers["content-type"].startswith("audio/mp4")
    assert client.post(
        f"/api/safeguarding/reviews/{session_id}/messages/{message_id}/tombstone",
        headers=admin_headers,
        json=_moderation("Voice evidence removed from ordinary participant access"),
    ).status_code == 200
    assert client.get(
        f"/api/guardian/messaging/conversations/{conversation_id}/voice-media/{media_id}",
        headers=guardian_headers,
    ).status_code == 404
    assert client.get(review_voice_url, headers=admin_headers).status_code == 200
    assert db.query(MessagingAuditEvent).filter_by(event_type="safeguarding.media_accessed").count() == 2


def test_internal_evidence_export_hashes_timestamps_media_note_permission_download_limit_expiry_and_cleanup(db, client, monkeypatch, tmp_path):
    media_root = tmp_path / "message-media"
    export_root = tmp_path / "safeguarding-exports"
    monkeypatch.setattr(message_media_service, "MESSAGE_MEDIA_ROOT", media_root)
    monkeypatch.setattr(safeguarding_service, "EXPORT_ROOT", export_root)
    world = _school_world(db, "safeguarding-export")
    conversation_id = _create_teacher_thread(client, world)
    teacher_headers = _headers(world["users"]["teacher"], world["school"], world["teacher"])
    uploaded = client.post(
        f"/api/messaging/conversations/{conversation_id}/media",
        headers={**teacher_headers, "X-Upload-Id": str(uuid4())},
        files={"file": ("evidence.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert uploaded.status_code == 201
    media_id = uploaded.json()["id"]
    sent = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=teacher_headers,
        json={"client_message_id": str(uuid4()), "body": "Exported text", "staged_media_ids": [media_id]},
    )
    assert sent.status_code == 200
    _grant(db, world, world["admin"], REVIEW, MODERATE)
    headers = _staff_headers(world)
    session_id = _start_review(client, world, conversation_id)
    assert client.post(
        f"/api/safeguarding/reviews/{session_id}/notes", headers=headers,
        json={"body": "Highly restricted internal export note"},
    ).status_code == 200
    export_body = {
        "export_mode": "internal",
        "reason_category": "legal_regulatory_request",
        "justification": "Authorised evidence package for formal investigation",
        "include_internal_notes": False,
    }
    assert client.post(f"/api/safeguarding/reviews/{session_id}/exports", headers=headers, json=export_body).status_code == 403
    _grant(db, world, world["admin"], EXPORT)
    without_notes = client.post(
        f"/api/safeguarding/reviews/{session_id}/exports", headers=headers, json=export_body
    )
    assert without_notes.status_code == 200, without_notes.text
    assert client.post(
        f"/api/safeguarding/reviews/{session_id}/exports", headers=headers,
        json={**export_body, "include_internal_notes": True},
    ).status_code == 403
    _grant(db, world, world["admin"], EXPORT_NOTES)
    created = client.post(
        f"/api/safeguarding/reviews/{session_id}/exports", headers=headers,
        json={**export_body, "include_internal_notes": True},
    )
    assert created.status_code == 200, created.text
    export_id = created.json()["id"]
    artifact = export_root / f"{export_id}.zip"
    assert artifact.is_file()
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == created.json()["artifact_sha256"]
    with zipfile.ZipFile(artifact) as package:
        assert set(package.namelist()) >= {"manifest.json", "transcript.html"}
        manifest = json.loads(package.read("manifest.json"))
        integrity = manifest.pop("integrity")
        canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        assert hashlib.sha256(canonical).hexdigest() == integrity["canonical_payload_sha256"] == created.json()["manifest_sha256"]
        assert manifest["privacy_mode"] == "internal"
        assert manifest["internal_notes"][0]["body"] == "Highly restricted internal export note"
        assert manifest["messages"][0]["created_at_utc"].endswith("+00:00")
        assert manifest["messages"][0]["created_at_school_local"].endswith("+04:00")
        for file_entry in manifest["files"]:
            assert hashlib.sha256(package.read(file_entry["file"])).hexdigest() == file_entry["sha256"]
        assert all(not name.startswith("/") and ".." not in name.split("/") for name in package.namelist())
        assert "/app/" not in package.read("manifest.json").decode()

    first_download = client.get(f"/api/safeguarding/exports/{export_id}/download", headers=headers)
    assert first_download.status_code == 200
    assert first_download.headers["content-type"] == "application/zip"
    row = db.query(MessagingEvidenceExport).filter_by(public_id=UUID(export_id)).one()
    assert row.download_count == 1
    assert db.query(MessagingAuditEvent).filter_by(event_type="safeguarding.export_downloaded").count() == 1
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert client.get(f"/api/safeguarding/exports/{export_id}/download", headers=headers).status_code == 410
    cleanup = cleanup_expired_safeguarding_state(db)
    assert cleanup["expired_exports"] >= 1 and cleanup["deleted_files"] >= 1
    assert not artifact.exists()


def test_search_and_export_rate_and_size_limits_fail_closed(db, client, monkeypatch, tmp_path):
    monkeypatch.setattr(safeguarding_service, "EXPORT_ROOT", tmp_path / "exports")
    world = _school_world(db, "safeguarding-limits")
    conversation_id = _create_teacher_thread(client, world)
    _send_text(client, world, conversation_id, "Bounded evidence")
    _grant(db, world, world["admin"], REVIEW, EXPORT)
    headers = _staff_headers(world)
    for _ in range(30):
        db.add(MessagingAuditEvent(
            school_id=world["school"].id,
            actor_kind="safeguarding_admin",
            actor_user_id=world["users"]["admin"].id,
            actor_membership_id=world["admin"].id,
            event_type="safeguarding.search",
            detail={},
            occurred_at=datetime.now(timezone.utc),
        ))
    db.commit()
    limited = client.get("/api/safeguarding/conversations", headers=headers)
    assert limited.status_code == 429 and limited.headers["retry-after"] == "60"

    session_id = _start_review(client, world, conversation_id)
    monkeypatch.setattr(safeguarding_service, "MAX_EXPORT_BYTES", 32)
    too_large = client.post(
        f"/api/safeguarding/reviews/{session_id}/exports",
        headers=headers,
        json={
            "export_mode": "internal",
            "reason_category": "legal_regulatory_request",
            "justification": "Authorised bounded export validation",
            "include_internal_notes": False,
        },
    )
    assert too_large.status_code == 422
    assert db.query(MessagingEvidenceExport).filter_by(state="failed").count() == 1


def test_safeguarding_frontend_is_a_separate_projection_without_composer():
    Path = __import__("pathlib").Path
    candidates = [
        Path("/frontend/src/routes/school/safeguarding/message-reviews/+page.svelte"),
        Path(__file__).parents[2] / "frontend/src/routes/school/safeguarding/message-reviews/+page.svelte",
    ]
    route_path = next((path for path in candidates if path.is_file()), None)
    assert route_path is not None, "Safeguarding frontend route was not mounted for verification"
    route = route_path.read_text(encoding="utf-8")
    assert "safeguardingApi.review" in route
    assert "participant delivery" not in route.casefold()
    assert "ComposeDialog" not in route
    assert "sendMessage" not in route
    assert "acknowledgeDelivery" not in route
    assert "acknowledgeRead" not in route
    assert 'data-testid="safeguarding-review-workspace"' in route

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import text

from app import messaging_production
from app.legal_hold_service import place_hold, release_hold
from app.messaging_production import enqueue_job, process_one_job
from app.models_school import (
    Conversation,
    Membership,
    Message,
    MessagingLegalHoldEvent,
    MessagingOperationsJob,
    MessagingPermissionGrant,
    MessagingRetentionPolicy,
    SchoolSystemOwner,
)
from app.safeguarding_service import resolve_actor
from app.school_governance import bootstrap_system_owner
from test_messaging_api import Session, _create_teacher_thread, _headers, _school_world, client, db


LEGAL_HOLD = "messaging.manage_legal_holds"


def _owner_world(db, suffix: str):
    world = _school_world(db, suffix)
    bootstrap_system_owner(
        db,
        school=world["school"],
        membership=world["admin"],
        actor_user_id=world["users"]["admin"].id,
    )
    return world


def _owner_headers(world):
    return _headers(world["users"]["admin"], world["school"], world["admin"])


def test_system_owner_is_explicit_transfer_is_confirmed_and_non_owner_is_denied(db, client):
    world = _owner_world(db, "production-owner")
    second = Membership(
        school_id=world["school"].id,
        user_id=world["users"]["teacher"].id,
        role="school_admin",
        status="active",
        created_by_user_id=world["users"]["admin"].id,
    )
    db.add(second)
    db.commit()
    summary = client.get("/api/school/governance", headers=_owner_headers(world))
    assert summary.status_code == 200
    assert summary.json()["owner"]["membership_id"] == world["admin"].id

    mismatch = client.post(
        "/api/school/governance/transfer",
        headers=_owner_headers(world),
        json={"target_membership_id": second.id, "confirmation_membership_id": world["admin"].id, "reason": "Approved responsibility transfer"},
    )
    assert mismatch.status_code == 409
    transferred = client.post(
        "/api/school/governance/transfer",
        headers=_owner_headers(world),
        json={"target_membership_id": second.id, "confirmation_membership_id": second.id, "reason": "Approved responsibility transfer"},
    )
    assert transferred.status_code == 200
    assert db.query(SchoolSystemOwner).filter_by(school_id=world["school"].id).one().membership_id == second.id
    denied = client.post(
        "/api/school/operations/retention/preview",
        headers=_owner_headers(world),
        json={"reason": "Former owner should not retain authority"},
    )
    assert denied.status_code == 403
    advanced_denied = client.get("/api/school/operations/advanced", headers=_owner_headers(world))
    assert advanced_denied.status_code == 403


def test_legal_hold_excludes_retention_preview_then_release_is_append_only(db, client):
    world = _owner_world(db, "production-hold")
    conversation_public_id = _create_teacher_thread(client, world)
    sent = client.post(
        f"/api/messaging/conversations/{conversation_public_id}/messages",
        headers=_headers(world["users"]["teacher"], world["school"], world["teacher"]),
        json={"client_message_id": str(uuid4()), "body": "Preserved legal evidence"},
    )
    assert sent.status_code == 200
    conversation = db.query(Conversation).filter_by(public_id=UUID(conversation_public_id)).one()
    message = db.query(Message).filter_by(public_id=UUID(sent.json()["id"])).one()
    conversation.status = "archived"
    db.commit()
    db.execute(text("UPDATE messages SET created_at = :old WHERE id = :id"), {
        "old": datetime.now(timezone.utc) - timedelta(days=3), "id": message.id
    })
    policy = db.query(MessagingRetentionPolicy).filter_by(school_id=world["school"].id).one()
    policy.rules = {**policy.rules, "message_days": 1}
    db.add(MessagingPermissionGrant(
        school_id=world["school"].id,
        membership_id=world["admin"].id,
        permission=LEGAL_HOLD,
        granted_by_membership_id=world["admin"].id,
        grant_reason="Authorised legal hold manager",
    )) if not db.query(MessagingPermissionGrant).filter_by(
        school_id=world["school"].id, membership_id=world["admin"].id, permission=LEGAL_HOLD
    ).first() else None
    db.commit()
    actor = resolve_actor(
        db,
        user=world["users"]["admin"],
        school_id=world["school"].id,
        membership_id=world["admin"].id,
    )
    hold = place_hold(
        db,
        actor=actor,
        scope_type="message",
        target_ref=str(message.public_id),
        reason="Formal preservation request received",
        case_reference="CASE-001",
        review_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    preview = enqueue_job(
        db,
        school_id=world["school"].id,
        membership_id=world["admin"].id,
        job_type="retention_preview",
        reason="Verify legal hold exclusion before disposal",
        policy_id=policy.id,
        dry_run=True,
    )
    process_one_job(Session, worker_id="test-retention-worker")
    db.refresh(preview)
    assert preview.progress["messages"] == 0
    assert preview.progress["held_messages_excluded"] == 1

    release_hold(db, actor=actor, public_id=hold.public_id, reason="Preservation instruction formally withdrawn")
    assert [row.action for row in db.query(MessagingLegalHoldEvent).filter_by(hold_id=hold.id).order_by(MessagingLegalHoldEvent.id)] == ["placed", "released"]
    second = enqueue_job(
        db,
        school_id=world["school"].id,
        membership_id=world["admin"].id,
        job_type="retention_preview",
        reason="Verify released hold changes the preview",
        policy_id=policy.id,
        dry_run=True,
    )
    process_one_job(Session, worker_id="test-retention-worker")
    db.refresh(second)
    assert second.progress["messages"] == 1


def test_expired_lease_is_recovered_and_operations_health_contains_no_payload_content(db, client, tmp_path, monkeypatch):
    world = _owner_world(db, "production-lease")
    monkeypatch.setattr(messaging_production, "MESSAGE_MEDIA_ARCHIVE_ROOT", tmp_path)
    policy = db.query(MessagingRetentionPolicy).filter_by(school_id=world["school"].id).one()
    job = enqueue_job(
        db,
        school_id=world["school"].id,
        membership_id=world["admin"].id,
        job_type="retention_preview",
        reason="Recover an abandoned production worker lease",
        policy_id=policy.id,
        dry_run=True,
    )
    job.state = "leased"
    job.lease_owner = "dead-worker"
    job.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    process_one_job(Session, worker_id="replacement-worker")
    db.refresh(job)
    assert job.state == "succeeded"
    summary = client.get("/api/school/operations", headers=_owner_headers(world))
    assert summary.status_code == 200
    assert "Preserved legal evidence" not in summary.text
    assert set(summary.json()) == {"health"}
    heartbeat = summary.json()["health"]["worker_heartbeats"][0]
    assert heartbeat["recovered_leases_total"] >= 1
    advanced = client.get("/api/school/operations/advanced", headers=_owner_headers(world))
    assert advanced.status_code == 200
    assert advanced.json()["jobs"][0]["id"] == str(job.public_id)
    assert advanced.json()["active_retention_policy"]["version"] == policy.policy_version

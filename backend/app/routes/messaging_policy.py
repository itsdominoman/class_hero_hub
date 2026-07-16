from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db, settings
from ..models_school import Membership, SchoolMessagingPolicy
from ..schemas import SchoolMessagingPolicyResponse, SchoolMessagingPolicyUpdate
from ..school_scope import require_school_role, write_audit


router = APIRouter(dependencies=[Depends(require_school_role("school_admin"))])


def _default_policy(school_id: int) -> SchoolMessagingPolicy:
    return SchoolMessagingPolicy(school_id=school_id)


def _payload(policy: SchoolMessagingPolicy) -> dict:
    global_enabled = bool(settings.MESSAGING_ENABLED)
    return {
        "school_id": policy.school_id,
        "global_enabled": global_enabled,
        "effective_enabled": global_enabled and bool(policy.enabled),
        "enabled": bool(policy.enabled),
        "guardian_replies_enabled": bool(policy.guardian_replies_enabled),
        "delivery_receipts_visible": bool(policy.delivery_receipts_visible),
        "read_receipts_visible": bool(policy.read_receipts_visible),
        "allow_staff_out_of_hours_opt_in": bool(policy.allow_staff_out_of_hours_opt_in),
        "teachers_may_mark_urgent": bool(policy.teachers_may_mark_urgent),
        "notification_preview_mode": policy.notification_preview_mode,
        "retention_days": policy.retention_days,
        "email_mode": policy.email_mode,
        "policy_version": policy.policy_version,
        "created_at": policy.created_at,
        "updated_at": policy.updated_at,
    }


@router.get("/messaging-policy", response_model=SchoolMessagingPolicyResponse)
def get_messaging_policy(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    policy = db.query(SchoolMessagingPolicy).filter(SchoolMessagingPolicy.school_id == membership.school_id).first()
    if policy is None:
        # The migration and school-creation path create rows proactively. This
        # fail-closed fallback supports databases restored from older snapshots.
        policy = _default_policy(membership.school_id)
        db.add(policy)
        db.commit()
        db.refresh(policy)
    return _payload(policy)


@router.put("/messaging-policy", response_model=SchoolMessagingPolicyResponse)
def update_messaging_policy(
    payload: SchoolMessagingPolicyUpdate,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    policy = (
        db.query(SchoolMessagingPolicy)
        .filter(SchoolMessagingPolicy.school_id == membership.school_id)
        .with_for_update()
        .first()
    )
    if policy is None:
        policy = _default_policy(membership.school_id)
        db.add(policy)
        db.flush()
    if policy.policy_version != payload.expected_policy_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "messaging_policy_version_conflict", "current_version": policy.policy_version},
        )

    before = _payload(policy)
    for field in (
        "enabled",
        "guardian_replies_enabled",
        "delivery_receipts_visible",
        "read_receipts_visible",
        "allow_staff_out_of_hours_opt_in",
        "teachers_may_mark_urgent",
        "notification_preview_mode",
        "retention_days",
        "email_mode",
    ):
        setattr(policy, field, getattr(payload, field))
    policy.policy_version += 1
    policy.updated_by_membership_id = membership.id
    db.flush()
    after = _payload(policy)
    write_audit(
        db,
        membership.user_id,
        "messaging.policy.updated",
        ("school_messaging_policies", policy.school_id),
        {
            "previous_policy_version": before["policy_version"],
            "policy_version": after["policy_version"],
            "changed_fields": sorted(
                key
                for key in after
                if key in before
                and key not in {"created_at", "updated_at", "effective_enabled", "global_enabled"}
                and key != "policy_version"
                and before[key] != after[key]
            ),
            "effective_enabled": after["effective_enabled"],
        },
        school_id=membership.school_id,
    )
    db.commit()
    db.refresh(policy)
    return _payload(policy)

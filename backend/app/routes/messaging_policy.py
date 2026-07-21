from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db, settings
from ..models_school import (
    Membership,
    NotificationOutbox,
    School,
    SchoolContactException,
    SchoolContactWindow,
    SchoolMessagingPolicy,
    SchoolPointsNotificationPolicy,
)
from ..schemas import (
    NotificationOutboxStatusResponse,
    SchoolContactHoursResponse,
    SchoolContactHoursUpdate,
    SchoolMessagingPolicyResponse,
    SchoolMessagingPolicyUpdate,
    SchoolPointsNotificationPolicyResponse,
    SchoolPointsNotificationPolicyUpdate,
)
from ..school_scope import require_school_role, write_audit
from ..family_notifications import cancel_undispatched_immediate_points


router = APIRouter(dependencies=[Depends(require_school_role("school_admin"))])
UTC = timezone.utc


def _default_policy(school_id: int) -> SchoolMessagingPolicy:
    return SchoolMessagingPolicy(school_id=school_id)


def _default_points_policy(school_id: int) -> SchoolPointsNotificationPolicy:
    return SchoolPointsNotificationPolicy(school_id=school_id)


def _points_payload(school: School, policy: SchoolPointsNotificationPolicy) -> dict:
    return {
        "school_id": school.id,
        "school_timezone": school.timezone,
        "mode": policy.mode,
        "daily_enabled": bool(policy.daily_enabled),
        "weekly_enabled": bool(policy.weekly_enabled),
        "monthly_enabled": bool(policy.monthly_enabled),
        "week_starts_on": policy.week_starts_on,
        "week_ends_on": policy.week_ends_on,
        "weekly_summary_day": policy.weekly_summary_day,
        "daily_summary_time": policy.daily_summary_time,
        "weekly_summary_time": policy.weekly_summary_time,
        "monthly_summary_time": policy.monthly_summary_time,
        "policy_version": policy.policy_version,
        "created_at": policy.created_at,
        "updated_at": policy.updated_at,
    }


def _points_audit_payload(payload: dict) -> dict:
    return {
        key: (value.isoformat() if hasattr(value, "isoformat") else value)
        for key, value in payload.items()
        if key not in {"created_at", "updated_at"}
    }


@router.get("/points-notification-policy", response_model=SchoolPointsNotificationPolicyResponse)
def get_points_notification_policy(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school = db.query(School).filter(School.id == membership.school_id).first()
    if school is None:
        raise HTTPException(status_code=404, detail="School not found")
    policy = db.query(SchoolPointsNotificationPolicy).filter(
        SchoolPointsNotificationPolicy.school_id == membership.school_id
    ).first()
    if policy is None:
        policy = _default_points_policy(membership.school_id)
        db.add(policy)
        db.commit()
        db.refresh(policy)
    return _points_payload(school, policy)


@router.put("/points-notification-policy", response_model=SchoolPointsNotificationPolicyResponse)
def update_points_notification_policy(
    payload: SchoolPointsNotificationPolicyUpdate,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school = db.query(School).filter(School.id == membership.school_id).with_for_update().first()
    if school is None:
        raise HTTPException(status_code=404, detail="School not found")
    try:
        ZoneInfo(payload.school_timezone)
    except ZoneInfoNotFoundError:
        raise HTTPException(status_code=422, detail="School timezone must be a valid IANA timezone")
    policy = db.query(SchoolPointsNotificationPolicy).filter(
        SchoolPointsNotificationPolicy.school_id == membership.school_id
    ).with_for_update().first()
    if policy is None:
        policy = _default_points_policy(membership.school_id)
        db.add(policy)
        db.flush()
    if policy.policy_version != payload.expected_policy_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "points_notification_policy_version_conflict", "current_version": policy.policy_version},
        )
    before = _points_payload(school, policy)
    for field in (
        "mode", "daily_enabled", "weekly_enabled", "monthly_enabled",
        "week_starts_on", "week_ends_on", "weekly_summary_day",
        "daily_summary_time", "weekly_summary_time", "monthly_summary_time",
    ):
        setattr(policy, field, getattr(payload, field))
    school.timezone = payload.school_timezone
    policy.policy_version += 1
    policy.updated_by_membership_id = membership.id
    now = datetime.now(UTC)
    if policy.mode != "immediate":
        cancel_undispatched_immediate_points(db, school_id=school.id, now=now)
    db.flush()
    after = _points_payload(school, policy)
    write_audit(
        db,
        membership.user_id,
        "behaviour.points_notification_policy.updated",
        ("school_points_notification_policies", school.id),
        {"previous": _points_audit_payload(before), "current": _points_audit_payload(after)},
        school_id=school.id,
    )
    db.commit()
    db.refresh(policy)
    return _points_payload(school, policy)


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
        "contact_hours_enabled": bool(policy.contact_hours_enabled),
        "notification_delay_mode": policy.notification_delay_mode,
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


def _contact_hours_payload(
    db: Session,
    *,
    school: School,
    policy: SchoolMessagingPolicy,
) -> dict:
    windows = (
        db.query(SchoolContactWindow)
        .filter(SchoolContactWindow.school_id == school.id)
        .order_by(SchoolContactWindow.weekday)
        .all()
    )
    exceptions = (
        db.query(SchoolContactException)
        .filter(SchoolContactException.school_id == school.id)
        .order_by(SchoolContactException.local_date)
        .all()
    )
    return {
        "school_id": school.id,
        "school_timezone": school.timezone,
        "policy_version": policy.policy_version,
        "enabled": bool(policy.contact_hours_enabled),
        "notification_delay_mode": policy.notification_delay_mode,
        "allow_staff_out_of_hours_opt_in": bool(policy.allow_staff_out_of_hours_opt_in),
        "teachers_may_mark_urgent": bool(policy.teachers_may_mark_urgent),
        "weekly_windows": [
            {
                "weekday": row.weekday,
                "start_local": row.start_local.isoformat(timespec="minutes"),
                "end_local": row.end_local.isoformat(timespec="minutes"),
            }
            for row in windows
        ],
        "exceptions": [
            {
                "local_date": row.local_date.isoformat(),
                "kind": row.kind,
                "start_local": (
                    row.start_local.isoformat(timespec="minutes")
                    if row.start_local is not None
                    else None
                ),
                "end_local": (
                    row.end_local.isoformat(timespec="minutes")
                    if row.end_local is not None
                    else None
                ),
                "label": row.label,
                "label_ar": row.label_ar,
            }
            for row in exceptions
        ],
    }


@router.get("/messaging-contact-hours", response_model=SchoolContactHoursResponse)
def get_messaging_contact_hours(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school = db.query(School).filter(School.id == membership.school_id).first()
    policy = (
        db.query(SchoolMessagingPolicy)
        .filter(SchoolMessagingPolicy.school_id == membership.school_id)
        .first()
    )
    if school is None:
        raise HTTPException(status_code=404, detail="School not found")
    if policy is None:
        policy = _default_policy(membership.school_id)
        db.add(policy)
        db.commit()
        db.refresh(policy)
    return _contact_hours_payload(db, school=school, policy=policy)


@router.put("/messaging-contact-hours", response_model=SchoolContactHoursResponse)
def update_messaging_contact_hours(
    payload: SchoolContactHoursUpdate,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school = db.query(School).filter(School.id == membership.school_id).first()
    policy = (
        db.query(SchoolMessagingPolicy)
        .filter(SchoolMessagingPolicy.school_id == membership.school_id)
        .with_for_update()
        .first()
    )
    if school is None:
        raise HTTPException(status_code=404, detail="School not found")
    if policy is None:
        policy = _default_policy(membership.school_id)
        db.add(policy)
        db.flush()
    if policy.policy_version != payload.expected_policy_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "messaging_policy_version_conflict",
                "current_version": policy.policy_version,
            },
        )

    before = _contact_hours_payload(db, school=school, policy=policy)
    db.query(SchoolContactException).filter(
        SchoolContactException.school_id == school.id
    ).delete(synchronize_session=False)
    db.query(SchoolContactWindow).filter(
        SchoolContactWindow.school_id == school.id
    ).delete(synchronize_session=False)
    for window in payload.weekly_windows:
        db.add(
            SchoolContactWindow(
                school_id=school.id,
                weekday=window.weekday,
                start_local=window.start_local,
                end_local=window.end_local,
            )
        )
    for exception in payload.exceptions:
        db.add(
            SchoolContactException(
                school_id=school.id,
                local_date=exception.local_date,
                kind=exception.kind,
                start_local=exception.start_local,
                end_local=exception.end_local,
                label=exception.label,
                label_ar=exception.label_ar,
                created_by_membership_id=membership.id,
            )
        )
    policy.contact_hours_enabled = payload.enabled
    policy.notification_delay_mode = payload.notification_delay_mode
    policy.allow_staff_out_of_hours_opt_in = payload.allow_staff_out_of_hours_opt_in
    policy.teachers_may_mark_urgent = payload.teachers_may_mark_urgent
    policy.policy_version += 1
    policy.updated_by_membership_id = membership.id
    db.flush()
    after = _contact_hours_payload(db, school=school, policy=policy)
    write_audit(
        db,
        membership.user_id,
        "messaging.contact_hours.updated",
        ("school_messaging_policies", school.id),
        {
            "previous": before,
            "current": after,
        },
        school_id=school.id,
    )
    db.commit()
    return after


@router.get("/messaging-notification-outbox", response_model=NotificationOutboxStatusResponse)
def get_messaging_notification_outbox_status(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    state_counts = (
        db.query(NotificationOutbox.state, func.count(NotificationOutbox.id))
        .filter(NotificationOutbox.school_id == membership.school_id)
        .group_by(NotificationOutbox.state)
        .all()
    )
    oldest_held_at, next_eligible_at = (
        db.query(
            func.min(NotificationOutbox.created_at),
            func.min(NotificationOutbox.eligible_at),
        )
        .filter(
            NotificationOutbox.school_id == membership.school_id,
            NotificationOutbox.state == "held",
        )
        .one()
    )
    return {
        "counts": {state: count for state, count in state_counts},
        "oldest_held_at": oldest_held_at,
        "next_eligible_at": next_eligible_at,
    }


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

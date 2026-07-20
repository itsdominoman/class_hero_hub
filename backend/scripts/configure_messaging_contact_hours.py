"""Apply an explicitly confirmed school's initial Messaging v1 contact hours.

This is deliberately school-specific and idempotent. It never enables messaging
itself, never changes the school's timezone, and records every material policy
change in the append-only school audit log.
"""

from __future__ import annotations

import argparse
from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.database import SessionLocal
from app.models_school import (
    Membership,
    School,
    SchoolContactWindow,
    SchoolMessagingPolicy,
)
from app.school_scope import write_audit


WEEKLY_WINDOWS = {
    weekday: (time(7, 30), time(15, 0))
    for weekday in (1, 2, 3, 4, 7)
}


def _serialized_windows(rows: list[SchoolContactWindow]) -> list[dict[str, object]]:
    return [
        {
            "weekday": row.weekday,
            "start_local": row.start_local.isoformat(timespec="minutes"),
            "end_local": row.end_local.isoformat(timespec="minutes"),
        }
        for row in sorted(rows, key=lambda value: value.weekday)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--school-slug", required=True)
    parser.add_argument(
        "--confirm",
        required=True,
        help="Must exactly match --school-slug so another school cannot be changed accidentally.",
    )
    args = parser.parse_args()
    if args.confirm != args.school_slug:
        raise SystemExit("Confirmation must exactly match the school slug")

    db = SessionLocal()
    try:
        school = db.query(School).filter(School.slug == args.school_slug).one_or_none()
        if school is None:
            raise SystemExit("School not found")
        try:
            ZoneInfo(school.timezone)
        except ZoneInfoNotFoundError as exc:
            raise SystemExit("School timezone is not a valid IANA timezone") from exc

        admin = (
            db.query(Membership)
            .filter(
                Membership.school_id == school.id,
                Membership.role == "school_admin",
                Membership.status == "active",
                Membership.revoked_at.is_(None),
            )
            .order_by(Membership.id)
            .first()
        )
        if admin is None:
            raise SystemExit("An active school administrator is required for audited setup")

        policy = (
            db.query(SchoolMessagingPolicy)
            .filter(SchoolMessagingPolicy.school_id == school.id)
            .with_for_update()
            .one_or_none()
        )
        if policy is None:
            policy = SchoolMessagingPolicy(school_id=school.id)
            db.add(policy)
            db.flush()
        existing_windows = (
            db.query(SchoolContactWindow)
            .filter(SchoolContactWindow.school_id == school.id)
            .order_by(SchoolContactWindow.weekday)
            .all()
        )
        expected_windows = [
            {
                "weekday": weekday,
                "start_local": start_local.isoformat(timespec="minutes"),
                "end_local": end_local.isoformat(timespec="minutes"),
            }
            for weekday, (start_local, end_local) in sorted(WEEKLY_WINDOWS.items())
        ]
        before = {
            "enabled": bool(policy.contact_hours_enabled),
            "notification_delay_mode": policy.notification_delay_mode,
            "allow_staff_out_of_hours_opt_in": bool(policy.allow_staff_out_of_hours_opt_in),
            "teachers_may_mark_urgent": bool(policy.teachers_may_mark_urgent),
            "weekly_windows": _serialized_windows(existing_windows),
            "policy_version": policy.policy_version,
            "school_timezone": school.timezone,
        }
        already_configured = (
            before["enabled"] is True
            and before["notification_delay_mode"] == "delay_notifications_only"
            and before["allow_staff_out_of_hours_opt_in"] is False
            and before["teachers_may_mark_urgent"] is False
            and before["weekly_windows"] == expected_windows
        )
        if already_configured:
            print(
                f"Contact hours already configured for {school.slug} "
                f"({school.timezone}), policy version {policy.policy_version}."
            )
            db.rollback()
            return

        db.query(SchoolContactWindow).filter(
            SchoolContactWindow.school_id == school.id
        ).delete(synchronize_session=False)
        for weekday, (start_local, end_local) in WEEKLY_WINDOWS.items():
            db.add(
                SchoolContactWindow(
                    school_id=school.id,
                    weekday=weekday,
                    start_local=start_local,
                    end_local=end_local,
                )
            )
        policy.contact_hours_enabled = True
        policy.notification_delay_mode = "delay_notifications_only"
        policy.allow_staff_out_of_hours_opt_in = False
        policy.teachers_may_mark_urgent = False
        policy.policy_version += 1
        policy.updated_by_membership_id = admin.id
        db.flush()
        after = {
            **before,
            "enabled": True,
            "notification_delay_mode": "delay_notifications_only",
            "allow_staff_out_of_hours_opt_in": False,
            "teachers_may_mark_urgent": False,
            "weekly_windows": expected_windows,
            "policy_version": policy.policy_version,
        }
        write_audit(
            db,
            admin.user_id,
            "messaging.contact_hours.initialized",
            ("school_messaging_policies", school.id),
            {"previous": before, "current": after, "source": "deployment_script"},
            school_id=school.id,
        )
        db.commit()
        print(
            f"Configured contact hours for {school.slug} ({school.timezone}), "
            f"policy version {policy.policy_version}."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

"""School- and interval-scoped department authority helpers."""

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from .models_school import Department, Membership, StaffDepartmentAssignment


def _today() -> date:
    return datetime.now(timezone.utc).date()


def active_head_department_ids(
    db: Session,
    *,
    school_id: int,
    membership_id: int,
    today: date | None = None,
) -> frozenset[int]:
    today = today or _today()
    return frozenset(
        row[0]
        for row in db.query(StaffDepartmentAssignment.department_id)
        .join(Department, Department.id == StaffDepartmentAssignment.department_id)
        .filter(
            StaffDepartmentAssignment.school_id == school_id,
            StaffDepartmentAssignment.membership_id == membership_id,
            StaffDepartmentAssignment.responsibility == "head",
            StaffDepartmentAssignment.valid_from <= today,
            (
                StaffDepartmentAssignment.valid_to.is_(None)
                | (StaffDepartmentAssignment.valid_to > today)
            ),
            Department.school_id == school_id,
            Department.status == "active",
        )
        .all()
    )

def active_department_membership_ids(
    db: Session,
    *,
    school_id: int,
    department_ids: frozenset[int] | set[int],
    today: date | None = None,
) -> frozenset[int]:
    if not department_ids:
        return frozenset()
    today = today or _today()
    return frozenset(
        row[0]
        for row in db.query(StaffDepartmentAssignment.membership_id)
        .join(Membership, Membership.id == StaffDepartmentAssignment.membership_id)
        .join(Department, Department.id == StaffDepartmentAssignment.department_id)
        .filter(
            StaffDepartmentAssignment.school_id == school_id,
            StaffDepartmentAssignment.department_id.in_(department_ids),
            StaffDepartmentAssignment.valid_from <= today,
            (
                StaffDepartmentAssignment.valid_to.is_(None)
                | (StaffDepartmentAssignment.valid_to > today)
            ),
            Membership.school_id == school_id,
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            Department.school_id == school_id,
            Department.status == "active",
        )
        .all()
    )

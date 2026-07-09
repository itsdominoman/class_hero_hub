from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import auth, invite_tokens
from ..database import get_db
from ..models_school import AcademicYear, BranchCampus, ClassSection, GradeLevel, Membership, School, StaffAssignment, Subject, SubjectGroup, User
from ..rosters import roster_payload
from ..school_scope import open_interval_expression, require_teacher_of

router = APIRouter()


def _row_ref(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "code": getattr(row, "code", None),
        "name": getattr(row, "name", None),
        "name_ar": getattr(row, "name_ar", None),
        "status": getattr(row, "status", None),
    }


def _assignment_card(db: Session, assignment: StaffAssignment, school: School) -> dict[str, Any]:
    section = None
    group = None
    branch = None
    year = None
    level = None
    subject = None

    if assignment.class_section_id is not None:
        section = db.query(ClassSection).filter(ClassSection.id == assignment.class_section_id).first()
        if section:
            branch = db.query(BranchCampus).filter(BranchCampus.id == section.branch_campus_id).first()
            year = db.query(AcademicYear).filter(AcademicYear.id == section.academic_year_id).first()
            level = db.query(GradeLevel).filter(GradeLevel.id == section.grade_level_id).first()

    if assignment.subject_group_id is not None:
        group = db.query(SubjectGroup).filter(SubjectGroup.id == assignment.subject_group_id).first()
        if group:
            subject = db.query(Subject).filter(Subject.id == group.subject_id).first()
            year = db.query(AcademicYear).filter(AcademicYear.id == group.academic_year_id).first()
            if group.class_section_id is not None:
                section = db.query(ClassSection).filter(ClassSection.id == group.class_section_id).first()
                if section:
                    branch = db.query(BranchCampus).filter(BranchCampus.id == section.branch_campus_id).first()
                    level = db.query(GradeLevel).filter(GradeLevel.id == section.grade_level_id).first()
            elif group.grade_level_id is not None:
                level = db.query(GradeLevel).filter(GradeLevel.id == group.grade_level_id).first()

    return {
        "id": assignment.id,
        "role": assignment.role,
        "target_type": "subject_group" if assignment.subject_group_id is not None else "class_section",
        "valid_from": assignment.valid_from,
        "valid_to": assignment.valid_to,
        "school": {"id": school.id, "name": school.name, "name_ar": school.name_ar},
        "class_section": _row_ref(section),
        "subject_group": _row_ref(group),
        "branch": _row_ref(branch),
        "academic_year": _row_ref(year),
        "grade_level": _row_ref(level),
        "subject": _row_ref(subject),
    }


def _roster_payload(db: Session, school_id: int, *, class_section_id: int | None = None, subject_group_id: int | None = None) -> dict[str, Any]:
    if class_section_id is not None:
        section = db.query(ClassSection).filter(ClassSection.id == class_section_id, ClassSection.school_id == school_id).first()
        if not section:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roster target not found")
    else:
        group = db.query(SubjectGroup).filter(SubjectGroup.id == subject_group_id, SubjectGroup.school_id == school_id).first()
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roster target not found")
    return roster_payload(db, school_id, class_section_id=class_section_id, subject_group_id=subject_group_id, today=invite_tokens.now_utc().date())


@router.get("/dashboard")
def teacher_dashboard(
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    teacher_memberships = (
        db.query(Membership, School)
        .join(School, Membership.school_id == School.id)
        .filter(
            Membership.user_id == current_user.id,
            Membership.role == "teacher",
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            School.status != "suspended",
        )
        .all()
    )
    if not teacher_memberships:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher access required")

    today = invite_tokens.now_utc().date()
    cards = []
    for membership, school in teacher_memberships:
        assignments = (
            db.query(StaffAssignment)
            .filter(
                StaffAssignment.school_id == school.id,
                StaffAssignment.membership_id == membership.id,
                *open_interval_expression(StaffAssignment, today),
            )
            .order_by(StaffAssignment.role.asc(), StaffAssignment.id.asc())
            .all()
        )
        cards.extend(_assignment_card(db, assignment, school) for assignment in assignments)

    return {"assignments": cards}


@router.get(
    "/schools/{school_id}/sections/{class_section_id}/roster",
    dependencies=[Depends(require_teacher_of(class_section_param="class_section_id"))],
)
def section_roster(school_id: int, class_section_id: int, db: Session = Depends(get_db)):
    return _roster_payload(db, school_id, class_section_id=class_section_id)


@router.get(
    "/schools/{school_id}/subject-groups/{subject_group_id}/roster",
    dependencies=[Depends(require_teacher_of(subject_group_param="subject_group_id"))],
)
def subject_group_roster(school_id: int, subject_group_id: int, db: Session = Depends(get_db)):
    return _roster_payload(db, school_id, subject_group_id=subject_group_id)

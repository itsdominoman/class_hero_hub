from __future__ import annotations

from datetime import date
from typing import Any, Type

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import auth, invite_tokens
from ..database import get_db
from ..models_school import (
    AcademicYear,
    BranchCampus,
    ClassSection,
    EducationStage,
    Enrolment,
    GradeLevel,
    Membership,
    School,
    StaffAssignment,
    StaffInvite,
    Student,
    Subject,
    SubjectGroup,
    User,
)
from ..rosters import bulk_subject_groups_for_students, current_subject_groups_for_student, roster_payload
from .platform import _invite_payload, _issue_staff_invite
from ..school_scope import is_open_interval, open_interval_expression, require_school_role, write_audit

router = APIRouter(dependencies=[Depends(require_school_role("school_admin"))])


class SettingsUpdate(BaseModel):
    grade_level_label: str = Field(default="Grade", min_length=1, max_length=40)


class StructureBase(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    name_ar: str | None = Field(default=None, max_length=200)
    sort_order: int = 0
    status: str = Field(default="active", max_length=40)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"active", "inactive"}:
            raise ValueError("status must be active or inactive")
        return value


class BranchCampusRequest(StructureBase):
    pass


class EducationStageRequest(StructureBase):
    pass


class AcademicYearRequest(StructureBase):
    is_current: bool = False
    start_date: date | None = None
    end_date: date | None = None


class GradeLevelRequest(StructureBase):
    education_stage_id: int | None = None


class ClassSectionRequest(StructureBase):
    branch_campus_id: int | None = None
    academic_year_id: int
    grade_level_id: int


class SubjectRequest(StructureBase):
    pass


class SubjectGroupRequest(StructureBase):
    academic_year_id: int
    class_section_id: int | None = None
    grade_level_id: int | None = None
    subject_id: int
    enrolment_policy: str = "explicit_only"

    @field_validator("enrolment_policy")
    @classmethod
    def validate_enrolment_policy(cls, value: str) -> str:
        if value not in {"explicit_only", "default_for_section", "default_for_grade"}:
            raise ValueError("enrolment_policy must be explicit_only, default_for_section, or default_for_grade")
        return value


class SubjectGroupBulkRequest(BaseModel):
    academic_year_id: int
    grade_level_id: int
    subject_id: int
    class_section_ids: list[int] = Field(min_length=1)
    enrolment_policy: str = "default_for_section"

    @field_validator("enrolment_policy")
    @classmethod
    def validate_enrolment_policy(cls, value: str) -> str:
        if value not in {"explicit_only", "default_for_section", "default_for_grade"}:
            raise ValueError("enrolment_policy must be explicit_only, default_for_section, or default_for_grade")
        return value


class TeacherInviteRequest(BaseModel):
    email: EmailStr


class AssignmentRequest(BaseModel):
    role: str = Field(min_length=1, max_length=40)
    class_section_id: int | None = None
    subject_group_id: int | None = None
    valid_from: date | None = None


class CloseAssignmentRequest(BaseModel):
    valid_to: date | None = None


class StudentRequest(BaseModel):
    external_ref: str | None = Field(default=None, max_length=120)
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    preferred_name: str | None = Field(default=None, max_length=120)
    name_ar: str | None = Field(default=None, max_length=240)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=40)
    status: str = Field(default="active", max_length=40)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"active", "inactive"}:
            raise ValueError("status must be active or inactive")
        return value

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        if cleaned not in {"male", "female", "other", "unspecified"}:
            raise ValueError("gender must be male, female, other, unspecified, or blank")
        return cleaned


class EnrolmentRequest(BaseModel):
    class_section_id: int | None = None
    subject_group_id: int | None = None
    valid_from: date | None = None
    kind: str = "member"

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        if value not in {"member", "excluded"}:
            raise ValueError("kind must be member or excluded")
        return value


class CloseEnrolmentRequest(BaseModel):
    valid_to: date | None = None


class MoveSectionRequest(BaseModel):
    class_section_id: int
    valid_from: date | None = None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_payload(payload: StructureBase) -> dict[str, Any]:
    return {
        "code": payload.code.strip(),
        "name": payload.name.strip(),
        "name_ar": _clean_text(payload.name_ar),
        "sort_order": payload.sort_order,
        "status": payload.status,
    }


def _school_id(membership: Membership) -> int:
    return int(membership.school_id)


def _school(db: Session, school_id: int) -> School:
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")
    return school


def _default_branch(db: Session, school_id: int) -> BranchCampus:
    branch = (
        db.query(BranchCampus)
        .filter(BranchCampus.school_id == school_id, BranchCampus.status != "archived")
        .order_by(BranchCampus.sort_order.asc(), BranchCampus.id.asc())
        .first()
    )
    if branch:
        return branch

    branch = db.query(BranchCampus).filter(BranchCampus.school_id == school_id, BranchCampus.code == "MAIN").first()
    if branch:
        branch.status = "active"
        branch.name = branch.name or "Main Branch"
        db.commit()
        db.refresh(branch)
        return branch

    branch = BranchCampus(
        school_id=school_id,
        code="MAIN",
        name="Main Branch",
        name_ar=None,
        sort_order=0,
        status="active",
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


def _get_owned(db: Session, model: Type[Any], school_id: int, row_id: int):
    row = db.query(model).filter(model.id == row_id, model.school_id == school_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return row


def _ensure_owned(
    db: Session,
    model: Type[Any],
    school_id: int,
    row_id: int | None,
    label: str,
    *,
    current_id: int | None = None,
):
    if row_id is None:
        return None
    row = db.query(model).filter(model.id == row_id, model.school_id == school_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {label}")
    # Archived parents cannot be picked for new relationships, but an existing
    # child may keep referencing one it was already linked to (historical validity).
    if row.status == "archived" and row_id != current_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Archived {label} cannot be selected")
    return row


def _commit_or_conflict(db: Session, detail: str = "Duplicate record") -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _payload(row: Any) -> dict[str, Any]:
    data = {
        "id": row.id,
        "school_id": row.school_id,
        "code": row.code,
        "name": row.name,
        "name_ar": row.name_ar,
        "sort_order": row.sort_order,
        "status": row.status,
        "created_at": row.created_at,
    }
    for field in ("education_stage_id", "branch_campus_id", "academic_year_id", "grade_level_id", "class_section_id", "subject_id", "enrolment_policy", "is_current", "start_date", "end_date"):
        if hasattr(row, field):
            data[field] = getattr(row, field)
    return data


def _list_rows(db: Session, model: Type[Any], school_id: int, *, include_archived: bool = False):
    query = db.query(model).filter(model.school_id == school_id)
    if not include_archived:
        query = query.filter(model.status != "archived")
    rows = query.order_by(model.sort_order.asc(), model.id.asc()).all()
    return [_payload(row) for row in rows]


# Natural-key columns beyond (school_id, code) that scope uniqueness for the
# parent-bearing entities. Everything else is keyed on (school_id, code) alone.
# Note: grade levels are keyed on code only — education_stage_id is not part of
# their natural key even though it is stored via `extra`.
_EXTRA_KEY_COLUMNS: dict[Type[Any], tuple[str, ...]] = {
    ClassSection: ("branch_campus_id", "academic_year_id", "grade_level_id"),
    SubjectGroup: ("academic_year_id", "class_section_id", "grade_level_id", "subject_id"),
}


def _find_by_natural_key(db: Session, model: Type[Any], school_id: int, code: str, extra: dict[str, Any]):
    filters = [model.school_id == school_id, model.code == code]
    for column in _EXTRA_KEY_COLUMNS.get(model, ()):
        value = extra[column]
        if value is None:
            filters.append(getattr(model, column).is_(None))
        else:
            filters.append(getattr(model, column) == value)
    return db.query(model).filter(*filters).first()


def _ensure_no_update_duplicate(db: Session, row: Any, cleaned: dict[str, Any], extra: dict[str, Any]) -> None:
    model = row.__class__
    existing = _find_by_natural_key(db, model, row.school_id, cleaned["code"], extra)
    if existing is not None and existing.id != row.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This value is already used by another record.")


def _active_duplicate_detail(existing_status: str) -> str:
    if existing_status == "inactive":
        return "This value is already used by an inactive record. Edit or reactivate that record instead."
    return "An active record with this code already exists."


def _compact_code(value: str | None) -> str:
    return "".join(ch for ch in (value or "").upper() if ch.isalnum())


def _subject_group_defaults(
    *,
    subject: Subject,
    section: ClassSection | None = None,
    grade_level: GradeLevel | None = None,
) -> dict[str, str]:
    subject_code = _compact_code(subject.code)
    if not subject_code:
        subject_code = _compact_code(subject.name)

    if section is not None:
        level_code = _compact_code(getattr(grade_level, "code", None))
        section_code = _compact_code(section.code)
        context_code = f"{level_code}{section_code}" if level_code else section_code
        context_name = section.name
    elif grade_level is not None:
        context_code = _compact_code(grade_level.code)
        context_name = grade_level.name
    else:
        raise ValueError("Subject group context required")

    return {
        "code": f"{context_code}-{subject_code}",
        "name": f"{context_name} {subject.name}".strip(),
    }


def _restore_row(db: Session, row: Any, cleaned: dict[str, Any], extra: dict[str, Any]) -> Any:
    # Reactivate the archived row in place and refresh its editable fields from
    # the submitted form so the recreated record reflects what the admin typed.
    for key, value in cleaned.items():
        setattr(row, key, value)
    for key, value in extra.items():
        setattr(row, key, value)
    if row.status == "archived":
        row.status = "active"
    _commit_or_conflict(db, "This value is already used by another record.")
    db.refresh(row)
    return row


def _create_row(
    db: Session,
    model: Type[Any],
    school_id: int,
    payload: StructureBase,
    *,
    extra: dict[str, Any] | None = None,
) -> tuple[Any, bool]:
    """Create a record, restoring an archived one that shares its natural key.

    Returns (row, restored) where `restored` is True when an archived record was
    reactivated in place instead of a new row being inserted.
    """
    extra = extra or {}
    cleaned = _clean_payload(payload)
    existing = _find_by_natural_key(db, model, school_id, cleaned["code"], extra)
    if existing is not None:
        if existing.status == "archived":
            return _restore_row(db, existing, cleaned, extra), True
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_active_duplicate_detail(existing.status))
    row = model(school_id=school_id, **cleaned, **extra)
    db.add(row)
    _commit_or_conflict(db, "This value is already used by another record.")
    db.refresh(row)
    return row, False


def _create_response(
    db: Session,
    membership: Membership,
    model: Type[Any],
    payload: StructureBase,
    *,
    entity: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    school_id = _school_id(membership)
    row, restored = _create_row(db, model, school_id, payload, extra=extra)
    if restored:
        write_audit(
            db,
            membership.user_id,
            f"school.{entity}.restored",
            row,
            {"code": row.code, "status": row.status},
            school_id=school_id,
        )
        db.commit()
    return {**_payload(row), "restored": restored}


def _update_row(db: Session, row: Any, payload: StructureBase, *, extra: dict[str, Any] | None = None):
    extra = extra or {}
    cleaned = _clean_payload(payload)
    _ensure_no_update_duplicate(db, row, cleaned, extra)
    for key, value in cleaned.items():
        setattr(row, key, value)
    for key, value in extra.items():
        setattr(row, key, value)
    _commit_or_conflict(db)
    db.refresh(row)
    return row


def _archive_row(db: Session, row: Any):
    row.status = "archived"
    db.commit()


def _today() -> date:
    return invite_tokens.now_utc().date()


def _is_open_assignment(row: StaffAssignment, today: date | None = None) -> bool:
    return is_open_interval(row, today or _today())


def _validate_valid_from(value: date | None, label: str = "valid_from") -> date:
    valid_from = value or _today()
    if valid_from != _today():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} must be today")
    return valid_from


def _validate_close_date(valid_from: date, valid_to: date | None) -> date:
    close_date = valid_to or _today()
    if close_date < valid_from:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="valid_to must be on or after valid_from")
    if close_date != _today():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="valid_to must be today")
    return close_date


def _user_payload(user: User | None) -> dict[str, Any]:
    return {
        "id": getattr(user, "id", None),
        "email": getattr(user, "email", None),
        "name": getattr(user, "name", None),
    }


def _teacher_membership_or_404(db: Session, school_id: int, membership_id: int, *, require_active: bool = True) -> Membership:
    membership = (
        db.query(Membership)
        .filter(
            Membership.id == membership_id,
            Membership.school_id == school_id,
            Membership.role == "teacher",
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher membership not found")
    if require_active and (membership.status != "active" or membership.revoked_at is not None):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Teacher membership is not active")
    return membership


def _ensure_active_target(row: Any, label: str) -> Any:
    if row.status == "archived":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Archived {label} cannot be assigned")
    if row.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Inactive {label} cannot be assigned")
    return row


def _assignment_payload(db: Session, row: StaffAssignment) -> dict[str, Any]:
    return _assignment_payloads_bulk(db, [row])[0]


def _assignment_payloads_bulk(db: Session, rows: list[StaffAssignment]) -> list[dict[str, Any]]:
    """Build assignment payloads for many rows with a fixed number of batch queries."""
    section_ids = {row.class_section_id for row in rows if row.class_section_id is not None}
    group_ids = {row.subject_group_id for row in rows if row.subject_group_id is not None}
    sections_by_id = {s.id: _payload(s) for s in (db.query(ClassSection).filter(ClassSection.id.in_(section_ids)).all() if section_ids else [])}
    groups_by_id = {g.id: _payload(g) for g in (db.query(SubjectGroup).filter(SubjectGroup.id.in_(group_ids)).all() if group_ids else [])}
    return [
        {
            "id": row.id,
            "school_id": row.school_id,
            "membership_id": row.membership_id,
            "role": row.role,
            "class_section_id": row.class_section_id,
            "subject_group_id": row.subject_group_id,
            "valid_from": row.valid_from,
            "valid_to": row.valid_to,
            "created_by_user_id": row.created_by_user_id,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "class_section": sections_by_id.get(row.class_section_id),
            "subject_group": groups_by_id.get(row.subject_group_id),
            "is_open": _is_open_assignment(row),
        }
        for row in rows
    ]


def _open_assignments_query(db: Session, school_id: int, today: date | None = None):
    today = today or _today()
    return db.query(StaffAssignment).filter(
        StaffAssignment.school_id == school_id,
        *open_interval_expression(StaffAssignment, today),
    )


def _close_assignment_row(row: StaffAssignment, valid_to: date | None = None) -> None:
    close_date = _validate_close_date(row.valid_from, valid_to)
    if row.valid_to is None or row.valid_to > close_date:
        row.valid_to = close_date


def _student_display_name(row: Student) -> str:
    return " ".join(part for part in [row.preferred_name or row.first_name, row.last_name] if part).strip()


def _student_payload(row: Student, *, current_class_section: dict[str, Any] | None = None, current_subject_groups: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "id": row.id,
        "school_id": row.school_id,
        "external_ref": row.external_ref,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "preferred_name": row.preferred_name,
        "display_name": _student_display_name(row),
        "name_ar": row.name_ar,
        "date_of_birth": row.date_of_birth,
        "gender": row.gender,
        "status": row.status,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "current_class_section": current_class_section,
        "current_subject_groups": current_subject_groups or [],
    }


def _clean_student_payload(payload: StudentRequest) -> dict[str, Any]:
    return {
        "external_ref": _clean_text(payload.external_ref),
        "first_name": payload.first_name.strip(),
        "last_name": payload.last_name.strip(),
        "preferred_name": _clean_text(payload.preferred_name),
        "name_ar": _clean_text(payload.name_ar),
        "date_of_birth": payload.date_of_birth,
        "gender": payload.gender,
        "status": payload.status,
    }


def _current_student_context(db: Session, school_id: int, student_id: int) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    open_rows = (
        db.query(Enrolment)
        .filter(Enrolment.school_id == school_id, Enrolment.student_id == student_id, *open_interval_expression(Enrolment, _today()))
        .order_by(Enrolment.id.asc())
        .all()
    )
    class_section = None
    subject_groups = []
    for row in open_rows:
        if row.class_section_id is not None:
            section = db.query(ClassSection).filter(ClassSection.id == row.class_section_id).first()
            class_section = _payload(section) if section else None
    subject_groups = current_subject_groups_for_student(db, school_id, student_id, _today())
    return class_section, subject_groups


def _student_with_context(db: Session, row: Student) -> dict[str, Any]:
    class_section, subject_groups = _current_student_context(db, row.school_id, row.id)
    return _student_payload(row, current_class_section=class_section, current_subject_groups=subject_groups)


def _students_with_context_bulk(db: Session, school_id: int, rows: list[Student]) -> list[dict[str, Any]]:
    today = _today()
    subject_groups_by_student = bulk_subject_groups_for_students(db, school_id, today)

    student_ids = [row.id for row in rows]
    section_id_by_student: dict[int, int] = {}
    if student_ids:
        section_enrolments = (
            db.query(Enrolment)
            .filter(
                Enrolment.school_id == school_id,
                Enrolment.student_id.in_(student_ids),
                Enrolment.class_section_id.is_not(None),
                *open_interval_expression(Enrolment, today),
            )
            .order_by(Enrolment.id.asc())
            .all()
        )
        for enrolment in section_enrolments:
            section_id_by_student[enrolment.student_id] = enrolment.class_section_id
    section_ids = set(section_id_by_student.values())
    sections_by_id = {s.id: _payload(s) for s in (db.query(ClassSection).filter(ClassSection.id.in_(section_ids)).all() if section_ids else [])}

    payloads = []
    for row in rows:
        class_section = sections_by_id.get(section_id_by_student.get(row.id))
        payloads.append(_student_payload(row, current_class_section=class_section, current_subject_groups=subject_groups_by_student.get(row.id, [])))
    return payloads


def _enrolment_payload(db: Session, row: Enrolment) -> dict[str, Any]:
    section = db.query(ClassSection).filter(ClassSection.id == row.class_section_id).first() if row.class_section_id is not None else None
    group = db.query(SubjectGroup).filter(SubjectGroup.id == row.subject_group_id).first() if row.subject_group_id is not None else None
    student = db.query(Student).filter(Student.id == row.student_id).first()
    return {
        "id": row.id,
        "school_id": row.school_id,
        "student_id": row.student_id,
        "class_section_id": row.class_section_id,
        "subject_group_id": row.subject_group_id,
        "kind": row.kind,
        "valid_from": row.valid_from,
        "valid_to": row.valid_to,
        "created_by_user_id": row.created_by_user_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "class_section": _payload(section) if section else None,
        "subject_group": _payload(group) if group else None,
        "student": _student_payload(student) if student else None,
        "is_open": is_open_interval(row, _today()),
    }


def _open_enrolments_query(db: Session, school_id: int, today: date | None = None):
    today = today or _today()
    return db.query(Enrolment).filter(Enrolment.school_id == school_id, *open_interval_expression(Enrolment, today))


def _ensure_active_enrolment_target(db: Session, school_id: int, *, class_section_id: int | None, subject_group_id: int | None) -> tuple[int | None, int | None]:
    if (class_section_id is None and subject_group_id is None) or (class_section_id is not None and subject_group_id is not None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exactly one enrolment target is required")
    if class_section_id is not None:
        section = _ensure_active_target(_ensure_owned(db, ClassSection, school_id, class_section_id, "class_section_id"), "class_section")
        return section.id, None
    group = _ensure_active_target(_ensure_owned(db, SubjectGroup, school_id, subject_group_id, "subject_group_id"), "subject_group")
    if group.class_section_id is not None:
        parent = _ensure_owned(db, ClassSection, school_id, group.class_section_id, "class_section_id")
        _ensure_active_target(parent, "parent class_section")
    return None, group.id


def _validate_enrolment_kind(db: Session, school_id: int, *, class_section_id: int | None, subject_group_id: int | None, kind: str) -> None:
    if kind == "member":
        return
    if class_section_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Excluded enrolments are only valid for subject groups")
    group = _get_owned(db, SubjectGroup, school_id, subject_group_id)
    if group.enrolment_policy not in {"default_for_section", "default_for_grade"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Excluded enrolments require a default subject-group policy")


def _create_enrolment_row(
    db: Session,
    *,
    school_id: int,
    student: Student,
    class_section_id: int | None,
    subject_group_id: int | None,
    valid_from: date,
    created_by_user_id: int,
    kind: str = "member",
    skip_class_open_check: bool = False,
) -> Enrolment:
    if student.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive or archived students cannot receive new enrolments")
    _validate_enrolment_kind(db, school_id, class_section_id=class_section_id, subject_group_id=subject_group_id, kind=kind)
    if class_section_id is not None and not skip_class_open_check:
        existing_section = _open_enrolments_query(db, school_id).filter(Enrolment.student_id == student.id, Enrolment.class_section_id.is_not(None)).first()
        if existing_section is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student already has an open class-section enrolment")
    if subject_group_id is not None:
        duplicate_group = (
            _open_enrolments_query(db, school_id)
            .filter(Enrolment.student_id == student.id, Enrolment.subject_group_id == subject_group_id, Enrolment.kind == kind)
            .first()
        )
        if duplicate_group is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student already has this open subject-group enrolment")
        opposite_kind = "excluded" if kind == "member" else "member"
        opposite_group = (
            _open_enrolments_query(db, school_id)
            .filter(Enrolment.student_id == student.id, Enrolment.subject_group_id == subject_group_id, Enrolment.kind == opposite_kind)
            .first()
        )
        if opposite_group is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Close the other open subject-group enrolment first")
    row = Enrolment(
        school_id=school_id,
        student_id=student.id,
        class_section_id=class_section_id,
        subject_group_id=subject_group_id,
        kind=kind,
        valid_from=valid_from,
        valid_to=None,
        created_by_user_id=created_by_user_id,
    )
    db.add(row)
    db.flush()
    return row


def _close_enrolment_row(row: Enrolment, valid_to: date | None = None) -> None:
    close_date = _validate_close_date(row.valid_from, valid_to)
    if row.valid_to is None or row.valid_to > close_date:
        row.valid_to = close_date


def _roster_payload(db: Session, school_id: int, *, class_section_id: int | None = None, subject_group_id: int | None = None) -> dict[str, Any]:
    if class_section_id is not None:
        _get_owned(db, ClassSection, school_id, class_section_id)
    else:
        _get_owned(db, SubjectGroup, school_id, subject_group_id)
    return roster_payload(db, school_id, class_section_id=class_section_id, subject_group_id=subject_group_id, today=_today())


def _student_history_reasons(db: Session, school_id: int, student_id: int) -> list[str]:
    reasons: list[str] = []
    if db.query(Enrolment.id).filter(Enrolment.school_id == school_id, Enrolment.student_id == student_id).first():
        reasons.append("enrolments")
    return reasons


def _teacher_ref_payloads_bulk(db: Session, assignments: list[StaffAssignment]) -> dict[int, dict[str, Any]]:
    """Map assignment.id -> teacher ref payload for many assignments with a fixed number of batch queries."""
    membership_ids = {a.membership_id for a in assignments}
    memberships_by_id = {m.id: m for m in (db.query(Membership).filter(Membership.id.in_(membership_ids)).all() if membership_ids else [])}
    user_ids = {m.user_id for m in memberships_by_id.values()}
    users_by_id = {u.id: u for u in (db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else [])}
    result: dict[int, dict[str, Any]] = {}
    for assignment in assignments:
        membership = memberships_by_id.get(assignment.membership_id)
        user = users_by_id.get(membership.user_id) if membership else None
        if membership is None or user is None:
            continue
        result[assignment.id] = {
            "assignment_id": assignment.id,
            "membership_id": membership.id,
            "valid_from": assignment.valid_from,
            "user": _user_payload(user),
        }
    return result


def _class_roster_setup_payload(db: Session, school_id: int, class_section_id: int) -> dict[str, Any]:
    section = _get_owned(db, ClassSection, school_id, class_section_id)
    branch = db.query(BranchCampus).filter(BranchCampus.id == section.branch_campus_id, BranchCampus.school_id == school_id).first() if section.branch_campus_id else None
    year = db.query(AcademicYear).filter(AcademicYear.id == section.academic_year_id, AcademicYear.school_id == school_id).first()
    level = db.query(GradeLevel).filter(GradeLevel.id == section.grade_level_id, GradeLevel.school_id == school_id).first()
    roster = _roster_payload(db, school_id, class_section_id=section.id)
    homeroom_assignment = (
        _open_assignments_query(db, school_id)
        .filter(StaffAssignment.role == "homeroom", StaffAssignment.class_section_id == section.id)
        .order_by(StaffAssignment.id.asc())
        .first()
    )
    subject_group_rows = (
        db.query(SubjectGroup)
        .filter(SubjectGroup.school_id == school_id, SubjectGroup.class_section_id == section.id, SubjectGroup.status != "archived")
        .order_by(SubjectGroup.sort_order.asc(), SubjectGroup.id.asc())
        .all()
    )
    group_ids = [row.id for row in subject_group_rows]
    subject_ids = [row.subject_id for row in subject_group_rows if row.subject_id is not None]
    subjects_by_id = {
        row.id: row
        for row in db.query(Subject).filter(Subject.school_id == school_id, Subject.id.in_(subject_ids)).all()
    } if subject_ids else {}
    assignments_by_group: dict[int, StaffAssignment] = {}
    if group_ids:
        for assignment in (
            _open_assignments_query(db, school_id)
            .filter(StaffAssignment.role == "subject", StaffAssignment.subject_group_id.in_(group_ids))
            .order_by(StaffAssignment.id.asc())
            .all()
        ):
            assignments_by_group.setdefault(assignment.subject_group_id, assignment)
    teacher_refs_by_assignment_id = _teacher_ref_payloads_bulk(
        db, ([homeroom_assignment] if homeroom_assignment else []) + list(assignments_by_group.values())
    )
    return {
        "class_section": _payload(section),
        "branch": _payload(branch) if branch else None,
        "academic_year": _payload(year) if year else None,
        "grade_level": _payload(level) if level else None,
        "students": roster["students"],
        "homeroom_teacher": teacher_refs_by_assignment_id.get(homeroom_assignment.id) if homeroom_assignment else None,
        "subject_groups": [
            {
                "subject_group": _payload(group),
                "subject": _payload(subjects_by_id.get(group.subject_id)) if group.subject_id is not None else None,
                "teacher": (
                    teacher_refs_by_assignment_id.get(assignments_by_group[group.id].id)
                    if group.id in assignments_by_group
                    else None
                ),
            }
            for group in subject_group_rows
        ],
    }


def _assignment_counts(db: Session, school_id: int) -> dict[int, int]:
    counts: dict[int, int] = {}
    for row in _open_assignments_query(db, school_id).all():
        counts[row.membership_id] = counts.get(row.membership_id, 0) + 1
    return counts


def _checklist_item(key: str, label: str, complete: bool, count: int, required: bool = True) -> dict[str, Any]:
    return {"key": key, "label": label, "complete": complete, "count": count, "required": required}


@router.get("/settings")
def get_settings(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school = _school(db, _school_id(membership))
    return {
        "school_id": school.id,
        "grade_level_label": school.grade_level_label or "Grade",
    }


@router.put("/settings")
def update_settings(
    payload: SettingsUpdate,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school = _school(db, _school_id(membership))
    school.grade_level_label = payload.grade_level_label.strip() or "Grade"
    db.commit()
    db.refresh(school)
    write_audit(db, membership.user_id, "school.settings.updated", school, {"grade_level_label": school.grade_level_label}, school_id=school.id)
    db.commit()
    return {"school_id": school.id, "grade_level_label": school.grade_level_label}


@router.get("/setup-checklist")
def setup_checklist(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    _default_branch(db, school_id)
    counts = {
        "branches": db.query(BranchCampus).filter(BranchCampus.school_id == school_id, BranchCampus.status != "archived").count(),
        "education_stages": db.query(EducationStage).filter(EducationStage.school_id == school_id, EducationStage.status != "archived").count(),
        "academic_years": db.query(AcademicYear).filter(AcademicYear.school_id == school_id, AcademicYear.status != "archived").count(),
        "grade_levels": db.query(GradeLevel).filter(GradeLevel.school_id == school_id, GradeLevel.status != "archived").count(),
        "class_sections": db.query(ClassSection).filter(ClassSection.school_id == school_id, ClassSection.status != "archived").count(),
        "subjects": db.query(Subject).filter(Subject.school_id == school_id, Subject.status != "archived").count(),
        "subject_groups": db.query(SubjectGroup).filter(SubjectGroup.school_id == school_id, SubjectGroup.status != "archived").count(),
    }
    items = [
        _checklist_item("settings", "School settings", True, 1),
        _checklist_item("branches", "Branches/campuses", counts["branches"] > 0, counts["branches"]),
        _checklist_item("academic_years", "Academic years", counts["academic_years"] > 0, counts["academic_years"]),
        _checklist_item("education_stages", "Education stages", counts["education_stages"] > 0, counts["education_stages"], required=False),
        _checklist_item("grade_levels", "Grade/year levels", counts["grade_levels"] > 0, counts["grade_levels"]),
        _checklist_item("class_sections", "Class sections/homerooms", counts["class_sections"] > 0, counts["class_sections"]),
        _checklist_item("subjects", "Subjects", counts["subjects"] > 0, counts["subjects"], required=False),
        _checklist_item("subject_groups", "Subject groups", counts["subject_groups"] > 0, counts["subject_groups"], required=False),
    ]
    required = [item for item in items if item["required"]]
    return {
        "school_id": school_id,
        "complete": all(item["complete"] for item in required),
        "items": items,
        "counts": counts,
    }


@router.get("/branches")
def list_branches(include_archived: bool = False, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    _default_branch(db, school_id)
    return _list_rows(db, BranchCampus, school_id, include_archived=include_archived)


@router.post("/branches", status_code=status.HTTP_201_CREATED)
def create_branch(payload: BranchCampusRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    return _create_response(db, membership, BranchCampus, payload, entity="branch")


@router.put("/branches/{row_id}")
def update_branch(row_id: int, payload: BranchCampusRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    row = _get_owned(db, BranchCampus, _school_id(membership), row_id)
    return _payload(_update_row(db, row, payload))


@router.delete("/branches/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_branch(row_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    _archive_row(db, _get_owned(db, BranchCampus, _school_id(membership), row_id))


@router.get("/education-stages")
def list_education_stages(include_archived: bool = False, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    return _list_rows(db, EducationStage, _school_id(membership), include_archived=include_archived)


@router.post("/education-stages", status_code=status.HTTP_201_CREATED)
def create_education_stage(payload: EducationStageRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    return _create_response(db, membership, EducationStage, payload, entity="education_stage")


@router.put("/education-stages/{row_id}")
def update_education_stage(row_id: int, payload: EducationStageRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    return _payload(_update_row(db, _get_owned(db, EducationStage, _school_id(membership), row_id), payload))


@router.delete("/education-stages/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_education_stage(row_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    _archive_row(db, _get_owned(db, EducationStage, _school_id(membership), row_id))


@router.get("/academic-years")
def list_academic_years(include_archived: bool = False, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    return _list_rows(db, AcademicYear, _school_id(membership), include_archived=include_archived)


def _academic_year_extra(db: Session, school_id: int, payload: AcademicYearRequest, current: Any = None) -> dict[str, Any]:
    if payload.start_date and payload.end_date and payload.end_date < payload.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date must be on or after start_date")
    if payload.is_current:
        existing = (
            db.query(AcademicYear)
            .filter(
                AcademicYear.school_id == school_id,
                AcademicYear.is_current.is_(True),
                AcademicYear.status != "archived",
            )
            .first()
        )
        if existing is not None and existing.id != getattr(current, "id", None):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only one academic year can be current")
    return {
        "is_current": payload.is_current,
        "start_date": payload.start_date,
        "end_date": payload.end_date,
    }


@router.post("/academic-years", status_code=status.HTTP_201_CREATED)
def create_academic_year(payload: AcademicYearRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    return _create_response(db, membership, AcademicYear, payload, entity="academic_year", extra=_academic_year_extra(db, school_id, payload))


@router.put("/academic-years/{row_id}")
def update_academic_year(row_id: int, payload: AcademicYearRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    row = _get_owned(db, AcademicYear, school_id, row_id)
    return _payload(_update_row(db, row, payload, extra=_academic_year_extra(db, school_id, payload, row)))


@router.delete("/academic-years/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_academic_year(row_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    row = _get_owned(db, AcademicYear, _school_id(membership), row_id)
    row.is_current = False
    _archive_row(db, row)


@router.get("/grade-levels")
def list_grade_levels(include_archived: bool = False, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    return _list_rows(db, GradeLevel, _school_id(membership), include_archived=include_archived)


@router.post("/grade-levels", status_code=status.HTTP_201_CREATED)
def create_grade_level(payload: GradeLevelRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    _ensure_owned(db, EducationStage, school_id, payload.education_stage_id, "education_stage_id")
    return _create_response(db, membership, GradeLevel, payload, entity="grade_level", extra={"education_stage_id": payload.education_stage_id})


@router.put("/grade-levels/{row_id}")
def update_grade_level(row_id: int, payload: GradeLevelRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    row = _get_owned(db, GradeLevel, school_id, row_id)
    _ensure_owned(db, EducationStage, school_id, payload.education_stage_id, "education_stage_id", current_id=row.education_stage_id)
    return _payload(_update_row(db, row, payload, extra={"education_stage_id": payload.education_stage_id}))


@router.delete("/grade-levels/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_grade_level(row_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    _archive_row(db, _get_owned(db, GradeLevel, _school_id(membership), row_id))


@router.get("/class-sections")
def list_class_sections(include_archived: bool = False, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    return _list_rows(db, ClassSection, _school_id(membership), include_archived=include_archived)


def _class_section_extra(db: Session, school_id: int, payload: ClassSectionRequest, current: Any = None) -> dict[str, Any]:
    branch_id = payload.branch_campus_id or _default_branch(db, school_id).id
    _ensure_owned(db, BranchCampus, school_id, branch_id, "branch_campus_id", current_id=getattr(current, "branch_campus_id", None))
    _ensure_owned(db, AcademicYear, school_id, payload.academic_year_id, "academic_year_id", current_id=getattr(current, "academic_year_id", None))
    _ensure_owned(db, GradeLevel, school_id, payload.grade_level_id, "grade_level_id", current_id=getattr(current, "grade_level_id", None))
    return {
        "branch_campus_id": branch_id,
        "academic_year_id": payload.academic_year_id,
        "grade_level_id": payload.grade_level_id,
    }


@router.post("/class-sections", status_code=status.HTTP_201_CREATED)
def create_class_section(payload: ClassSectionRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    return _create_response(db, membership, ClassSection, payload, entity="class_section", extra=_class_section_extra(db, school_id, payload))


@router.put("/class-sections/{row_id}")
def update_class_section(row_id: int, payload: ClassSectionRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    row = _get_owned(db, ClassSection, school_id, row_id)
    return _payload(_update_row(db, row, payload, extra=_class_section_extra(db, school_id, payload, row)))


@router.delete("/class-sections/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_class_section(row_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    _archive_row(db, _get_owned(db, ClassSection, _school_id(membership), row_id))


@router.get("/subjects")
def list_subjects(include_archived: bool = False, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    return _list_rows(db, Subject, _school_id(membership), include_archived=include_archived)


@router.post("/subjects", status_code=status.HTTP_201_CREATED)
def create_subject(payload: SubjectRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    return _create_response(db, membership, Subject, payload, entity="subject")


@router.put("/subjects/{row_id}")
def update_subject(row_id: int, payload: SubjectRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    return _payload(_update_row(db, _get_owned(db, Subject, _school_id(membership), row_id), payload))


@router.delete("/subjects/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_subject(row_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    _archive_row(db, _get_owned(db, Subject, _school_id(membership), row_id))


@router.get("/subject-groups")
def list_subject_groups(include_archived: bool = False, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    return _list_rows(db, SubjectGroup, _school_id(membership), include_archived=include_archived)


def _subject_group_extra(db: Session, school_id: int, payload: SubjectGroupRequest, current: Any = None) -> dict[str, Any]:
    if payload.class_section_id is None and payload.grade_level_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="class_section_id or grade_level_id is required")
    if payload.enrolment_policy == "default_for_section" and payload.class_section_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="default_for_section requires class_section_id")
    if payload.enrolment_policy == "default_for_grade" and payload.grade_level_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="default_for_grade requires grade_level_id")
    _ensure_owned(db, AcademicYear, school_id, payload.academic_year_id, "academic_year_id", current_id=getattr(current, "academic_year_id", None))
    section = _ensure_owned(db, ClassSection, school_id, payload.class_section_id, "class_section_id", current_id=getattr(current, "class_section_id", None))
    _ensure_owned(db, GradeLevel, school_id, payload.grade_level_id, "grade_level_id", current_id=getattr(current, "grade_level_id", None))
    _ensure_owned(db, Subject, school_id, payload.subject_id, "subject_id", current_id=getattr(current, "subject_id", None))
    if section is not None and section.academic_year_id != payload.academic_year_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="class_section_id must belong to academic_year_id")
    if section is not None and payload.grade_level_id is not None and section.grade_level_id != payload.grade_level_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="grade_level_id must match class_section_id")
    return {
        "academic_year_id": payload.academic_year_id,
        "class_section_id": payload.class_section_id,
        "grade_level_id": payload.grade_level_id,
        "subject_id": payload.subject_id,
        "enrolment_policy": payload.enrolment_policy,
    }


@router.post("/subject-groups", status_code=status.HTTP_201_CREATED)
def create_subject_group(payload: SubjectGroupRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    return _create_response(db, membership, SubjectGroup, payload, entity="subject_group", extra=_subject_group_extra(db, school_id, payload))


@router.post("/subject-groups/bulk-section")
def bulk_create_section_subject_groups(
    payload: SubjectGroupBulkRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    year = _ensure_owned(db, AcademicYear, school_id, payload.academic_year_id, "academic_year_id")
    grade_level = _ensure_owned(db, GradeLevel, school_id, payload.grade_level_id, "grade_level_id")
    subject = _ensure_owned(db, Subject, school_id, payload.subject_id, "subject_id")
    if payload.enrolment_policy == "default_for_grade":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bulk section groups cannot use default_for_grade")
    for label, row in (("academic_year", year), ("grade_level", grade_level), ("subject", subject)):
        if row.status == "archived":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Archived {label} cannot be selected")
        if row.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Inactive {label} cannot be selected")

    results: list[dict[str, Any]] = []
    created = 0
    restored = 0
    skipped = 0
    failed = 0

    seen_section_ids: set[int] = set()
    for section_id in payload.class_section_ids:
        if section_id in seen_section_ids:
            continue
        seen_section_ids.add(section_id)
        result: dict[str, Any] = {"class_section_id": section_id, "status": "failed"}
        section = db.query(ClassSection).filter(ClassSection.id == section_id, ClassSection.school_id == school_id).first()
        if section is None:
            result["reason"] = "Class section not found"
            failed += 1
            results.append(result)
            continue
        result["class_section"] = _payload(section)
        if section.status == "archived":
            result["reason"] = "Archived class section cannot be selected"
            failed += 1
            results.append(result)
            continue
        if section.status != "active":
            result["reason"] = "Inactive class section cannot be selected"
            failed += 1
            results.append(result)
            continue
        if section.academic_year_id != payload.academic_year_id:
            result["reason"] = "Class section does not belong to the selected academic year"
            failed += 1
            results.append(result)
            continue
        if section.grade_level_id != payload.grade_level_id:
            result["reason"] = "Class section does not belong to the selected grade/year level"
            failed += 1
            results.append(result)
            continue

        defaults = _subject_group_defaults(subject=subject, section=section, grade_level=grade_level)
        extra = {
            "academic_year_id": payload.academic_year_id,
            "class_section_id": section.id,
            "grade_level_id": None,
            "subject_id": subject.id,
            "enrolment_policy": payload.enrolment_policy,
        }
        existing = _find_by_natural_key(db, SubjectGroup, school_id, defaults["code"], extra)
        if existing is not None and existing.status != "archived":
            result.update(
                {
                    "status": "skipped",
                    "reason": _active_duplicate_detail(existing.status),
                    "subject_group": _payload(existing),
                }
            )
            skipped += 1
            results.append(result)
            continue

        request = SubjectGroupRequest(
            code=defaults["code"],
            name=defaults["name"],
            name_ar=None,
            sort_order=section.sort_order,
            status="active",
            academic_year_id=payload.academic_year_id,
            class_section_id=section.id,
            grade_level_id=None,
            subject_id=subject.id,
            enrolment_policy=payload.enrolment_policy,
        )
        row, was_restored = _create_row(db, SubjectGroup, school_id, request, extra=extra)
        result.update(
            {
                "status": "restored" if was_restored else "created",
                "reason": None,
                "subject_group": _payload(row),
            }
        )
        if was_restored:
            restored += 1
            write_audit(
                db,
                membership.user_id,
                "school.subject_group.restored",
                row,
                {"code": row.code, "status": row.status, "source": "bulk_section"},
                school_id=school_id,
            )
        else:
            created += 1
        results.append(result)

    if created or restored:
        write_audit(
            db,
            membership.user_id,
            "school.subject_group.bulk_created",
            ("subject_groups", None),
            {
                "academic_year_id": payload.academic_year_id,
                "grade_level_id": payload.grade_level_id,
                "subject_id": payload.subject_id,
                "created": created,
                "restored": restored,
                "skipped": skipped,
                "failed": failed,
            },
            school_id=school_id,
        )
    db.commit()
    return {
        "created": created,
        "restored": restored,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }


@router.put("/subject-groups/{row_id}")
def update_subject_group(row_id: int, payload: SubjectGroupRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    row = _get_owned(db, SubjectGroup, school_id, row_id)
    return _payload(_update_row(db, row, payload, extra=_subject_group_extra(db, school_id, payload, row)))


@router.delete("/subject-groups/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_subject_group(row_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    _archive_row(db, _get_owned(db, SubjectGroup, _school_id(membership), row_id))


@router.get("/teachers")
def list_teachers(include_deactivated: bool = False, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    counts = _assignment_counts(db, school_id)
    teacher_query = (
        db.query(Membership, User)
        .join(User, Membership.user_id == User.id)
        .filter(
            Membership.school_id == school_id,
            Membership.role == "teacher",
        )
    )
    if not include_deactivated:
        teacher_query = teacher_query.filter(Membership.status == "active", Membership.revoked_at.is_(None))
    teacher_rows = teacher_query.order_by(User.email.asc(), Membership.id.asc()).all()
    pending_invites = (
        db.query(StaffInvite)
        .filter(
            StaffInvite.school_id == school_id,
            StaffInvite.role == "teacher",
            StaffInvite.revoked_at.is_(None),
            StaffInvite.accepted_at.is_(None),
        )
        .order_by(StaffInvite.created_at.desc(), StaffInvite.id.desc())
        .all()
    )
    return {
        "teachers": [
            {
                "membership_id": teacher_membership.id,
                "school_id": teacher_membership.school_id,
                "status": teacher_membership.status,
                "created_at": teacher_membership.created_at,
                "revoked_at": teacher_membership.revoked_at,
                "assignment_count": counts.get(teacher_membership.id, 0),
                "user": _user_payload(user),
            }
            for teacher_membership, user in teacher_rows
        ],
        "pending_invites": [_invite_payload(invite) for invite in pending_invites if _invite_payload(invite)["status"] == "pending"],
    }


@router.get("/teachers/invites")
def list_teacher_invites(membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    invites = (
        db.query(StaffInvite)
        .filter(StaffInvite.school_id == school_id, StaffInvite.role == "teacher")
        .order_by(StaffInvite.created_at.desc(), StaffInvite.id.desc())
        .all()
    )
    return [_invite_payload(invite) for invite in invites]


@router.post("/teachers/invites", status_code=status.HTTP_201_CREATED)
def create_teacher_invite(
    payload: TeacherInviteRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    normalized_email = auth.normalize_email(str(payload.email))
    invited_user = db.query(User).filter(User.email == normalized_email).first()
    if invited_user is not None:
        existing_membership = (
            db.query(Membership)
            .filter(
                Membership.school_id == school_id,
                Membership.user_id == invited_user.id,
                Membership.role == "teacher",
                Membership.status == "active",
                Membership.revoked_at.is_(None),
            )
            .first()
        )
        if existing_membership is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Teacher already has an active membership")

    actor = db.query(User).filter(User.id == membership.user_id).first()
    staff_invite, _raw_token, warning = _issue_staff_invite(db, _school(db, school_id), normalized_email, actor, role="teacher")
    write_audit(
        db,
        membership.user_id,
        "school.teacher_invite.created",
        staff_invite,
        {"email": staff_invite.email, "role": staff_invite.role},
        school_id=school_id,
    )
    db.commit()
    response = _invite_payload(staff_invite)
    if warning:
        response["warning"] = warning
    return response


@router.delete("/teachers/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_teacher_invite(
    invite_id: int,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    staff_invite = (
        db.query(StaffInvite)
        .filter(StaffInvite.id == invite_id, StaffInvite.school_id == school_id, StaffInvite.role == "teacher")
        .first()
    )
    if not staff_invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    if staff_invite.accepted_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invite already accepted")
    if staff_invite.revoked_at is None:
        staff_invite.revoked_at = invite_tokens.now_utc()
        write_audit(
            db,
            membership.user_id,
            "school.teacher_invite.revoked",
            staff_invite,
            {"email": staff_invite.email, "role": staff_invite.role},
            school_id=school_id,
        )
        db.commit()


@router.get("/teachers/assignments")
def list_all_teacher_assignments(
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    teacher_memberships = (
        db.query(Membership.id)
        .filter(
            Membership.school_id == school_id,
            Membership.role == "teacher",
            Membership.status == "active",
            Membership.revoked_at.is_(None),
        )
        .all()
    )
    teacher_membership_ids = [row.id for row in teacher_memberships]
    if not teacher_membership_ids:
        return {}

    assignments_by_teacher: dict[int, list[dict[str, Any]]] = {membership_id: [] for membership_id in teacher_membership_ids}
    assignments = (
        db.query(StaffAssignment)
        .filter(
            StaffAssignment.school_id == school_id,
            StaffAssignment.membership_id.in_(teacher_membership_ids),
        )
        .order_by(StaffAssignment.membership_id.asc(), StaffAssignment.valid_from.desc(), StaffAssignment.id.desc())
        .all()
    )
    for payload in _assignment_payloads_bulk(db, assignments):
        assignments_by_teacher.setdefault(payload["membership_id"], []).append(payload)
    return assignments_by_teacher


@router.get("/teachers/{teacher_membership_id}/assignments")
def list_teacher_assignments(
    teacher_membership_id: int,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    _teacher_membership_or_404(db, school_id, teacher_membership_id, require_active=False)
    assignments = (
        db.query(StaffAssignment)
        .filter(StaffAssignment.school_id == school_id, StaffAssignment.membership_id == teacher_membership_id)
        .order_by(StaffAssignment.valid_from.desc(), StaffAssignment.id.desc())
        .all()
    )
    return _assignment_payloads_bulk(db, assignments)


@router.post("/teachers/{teacher_membership_id}/assignments", status_code=status.HTTP_201_CREATED)
def create_teacher_assignment(
    teacher_membership_id: int,
    payload: AssignmentRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    teacher_membership = _teacher_membership_or_404(db, school_id, teacher_membership_id)
    valid_from = _validate_valid_from(payload.valid_from)
    role = payload.role.strip()
    if role not in {"homeroom", "subject"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported assignment role")
    if role == "homeroom" and (payload.class_section_id is None or payload.subject_group_id is not None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Homeroom assignments require class_section_id only")
    if role == "subject" and (payload.subject_group_id is None or payload.class_section_id is not None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject assignments require subject_group_id only")

    target_section_id = None
    target_group_id = None
    if role == "homeroom":
        section = _ensure_active_target(_ensure_owned(db, ClassSection, school_id, payload.class_section_id, "class_section_id"), "class_section")
        target_section_id = section.id
        existing_homeroom = (
            _open_assignments_query(db, school_id)
            .filter(StaffAssignment.role == "homeroom", StaffAssignment.class_section_id == target_section_id)
            .first()
        )
        if existing_homeroom is not None and existing_homeroom.membership_id != teacher_membership.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Class section already has an open homeroom teacher")
    else:
        group = _ensure_active_target(_ensure_owned(db, SubjectGroup, school_id, payload.subject_group_id, "subject_group_id"), "subject_group")
        if group.class_section_id is not None:
            parent = _ensure_owned(db, ClassSection, school_id, group.class_section_id, "class_section_id")
            _ensure_active_target(parent, "parent class_section")
        target_group_id = group.id

    duplicate = (
        _open_assignments_query(db, school_id)
        .filter(
            StaffAssignment.membership_id == teacher_membership.id,
            StaffAssignment.role == role,
            StaffAssignment.class_section_id == target_section_id if target_section_id is not None else StaffAssignment.class_section_id.is_(None),
            StaffAssignment.subject_group_id == target_group_id if target_group_id is not None else StaffAssignment.subject_group_id.is_(None),
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Teacher already has this open assignment")

    # Homeroom is singular for a teacher in this slice. Subject assignments may
    # be multiple concurrent groups, so they are closed explicitly.
    prior_rows = []
    if role == "homeroom":
        prior_rows = _open_assignments_query(db, school_id).filter(
            StaffAssignment.membership_id == teacher_membership.id,
            StaffAssignment.role == role,
        ).all()
    close_date = valid_from
    for prior in prior_rows:
        _close_assignment_row(prior, close_date)

    assignment = StaffAssignment(
        school_id=school_id,
        membership_id=teacher_membership.id,
        class_section_id=target_section_id,
        subject_group_id=target_group_id,
        role=role,
        valid_from=valid_from,
        valid_to=None,
        created_by_user_id=membership.user_id,
    )
    db.add(assignment)
    db.flush()
    write_audit(
        db,
        membership.user_id,
        "school.staff_assignment.created",
        assignment,
        {
            "membership_id": teacher_membership.id,
            "role": role,
            "class_section_id": target_section_id,
            "subject_group_id": target_group_id,
            "closed_previous_ids": [row.id for row in prior_rows],
        },
        school_id=school_id,
    )
    db.commit()
    db.refresh(assignment)
    return _assignment_payload(db, assignment)


@router.delete("/assignments/{assignment_id}")
def close_teacher_assignment(
    assignment_id: int,
    payload: CloseAssignmentRequest | None = None,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    assignment = db.query(StaffAssignment).filter(StaffAssignment.id == assignment_id, StaffAssignment.school_id == school_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    _close_assignment_row(assignment, payload.valid_to if payload else None)
    write_audit(
        db,
        membership.user_id,
        "school.staff_assignment.closed",
        assignment,
        {"membership_id": assignment.membership_id, "valid_to": str(assignment.valid_to)},
        school_id=school_id,
    )
    db.commit()
    db.refresh(assignment)
    return _assignment_payload(db, assignment)


@router.post("/teachers/{teacher_membership_id}/deactivate")
def deactivate_teacher(
    teacher_membership_id: int,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    teacher_membership = _teacher_membership_or_404(db, school_id, teacher_membership_id)
    teacher_membership.status = "revoked"
    teacher_membership.revoked_at = invite_tokens.now_utc()
    teacher_membership.revoked_by_user_id = membership.user_id
    teacher_user = db.query(User).filter(User.id == teacher_membership.user_id).first()
    revoked_invites = []
    if teacher_user is not None:
        pending_invites = (
            db.query(StaffInvite)
            .filter(
                StaffInvite.school_id == school_id,
                StaffInvite.email == teacher_user.email,
                StaffInvite.role == "teacher",
                StaffInvite.revoked_at.is_(None),
                StaffInvite.accepted_at.is_(None),
            )
            .all()
        )
        for invite in pending_invites:
            invite.revoked_at = teacher_membership.revoked_at
            revoked_invites.append(invite.id)
    open_assignments = _open_assignments_query(db, school_id).filter(StaffAssignment.membership_id == teacher_membership.id).all()
    for assignment in open_assignments:
        _close_assignment_row(assignment)
    write_audit(
        db,
        membership.user_id,
        "school.teacher_membership.deactivated",
        teacher_membership,
        {"closed_assignment_ids": [assignment.id for assignment in open_assignments], "revoked_invite_ids": revoked_invites},
        school_id=school_id,
    )
    db.commit()
    return {
        "membership_id": teacher_membership.id,
        "status": teacher_membership.status,
        "closed_assignments": len(open_assignments),
        "revoked_invites": len(revoked_invites),
    }


@router.get("/students")
def list_students(
    include_archived: bool = False,
    class_section_id: int | None = None,
    search: str | None = None,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    query = db.query(Student).filter(Student.school_id == school_id)
    if not include_archived:
        query = query.filter(Student.status != "archived")
    if search:
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            (Student.first_name.ilike(term))
            | (Student.last_name.ilike(term))
            | (Student.preferred_name.ilike(term))
            | (Student.external_ref.ilike(term))
        )
    if class_section_id is not None:
        _get_owned(db, ClassSection, school_id, class_section_id)
        student_ids = select(Enrolment.student_id).where(
            Enrolment.school_id == school_id,
            Enrolment.class_section_id == class_section_id,
            Enrolment.kind == "member",
            *open_interval_expression(Enrolment, _today()),
        )
        query = query.filter(Student.id.in_(student_ids))
    rows = query.order_by(Student.last_name.asc(), Student.first_name.asc(), Student.id.asc()).all()
    return _students_with_context_bulk(db, school_id, rows)


@router.post("/students", status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    cleaned = _clean_student_payload(payload)
    external_ref = cleaned["external_ref"]
    if external_ref:
        existing = db.query(Student).filter(Student.school_id == school_id, Student.external_ref == external_ref).first()
        if existing is not None:
            if existing.status == "archived":
                for key, value in cleaned.items():
                    setattr(existing, key, value)
                existing.status = "active"
                write_audit(db, membership.user_id, "school.student.restored", existing, {"external_ref": external_ref}, school_id=school_id)
                db.commit()
                db.refresh(existing)
                return {**_student_with_context(db, existing), "restored": True}
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student external_ref is already used by a visible student")
    row = Student(school_id=school_id, **cleaned)
    db.add(row)
    db.flush()
    write_audit(db, membership.user_id, "school.student.created", row, {"external_ref": external_ref}, school_id=school_id)
    db.commit()
    db.refresh(row)
    return {**_student_with_context(db, row), "restored": False}


@router.get("/students/{student_id}")
def get_student(student_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    return _student_with_context(db, _get_owned(db, Student, _school_id(membership), student_id))


@router.put("/students/{student_id}")
def update_student(student_id: int, payload: StudentRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    row = _get_owned(db, Student, school_id, student_id)
    cleaned = _clean_student_payload(payload)
    external_ref = cleaned["external_ref"]
    if external_ref:
        existing = db.query(Student).filter(Student.school_id == school_id, Student.external_ref == external_ref).first()
        if existing is not None and existing.id != row.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student external_ref is already used by another student")
    for key, value in cleaned.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _student_with_context(db, row)


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_student(student_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    row = _get_owned(db, Student, _school_id(membership), student_id)
    row.status = "archived"
    write_audit(db, membership.user_id, "school.student.archived", row, {"external_ref": row.external_ref}, school_id=row.school_id)
    db.commit()


@router.delete("/students/{student_id}/remove-mistake", status_code=status.HTTP_204_NO_CONTENT)
def remove_student_mistake(student_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    row = _get_owned(db, Student, school_id, student_id)
    history_reasons = _student_history_reasons(db, school_id, student_id)
    if history_reasons:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This student has history. Archive instead.",
        )
    write_audit(
        db,
        membership.user_id,
        "school.student.removed_mistake",
        ("students", row.id),
        {"external_ref": row.external_ref, "display_name": _student_display_name(row), "history_reasons": history_reasons},
        school_id=school_id,
    )
    db.delete(row)
    db.commit()


@router.get("/students/{student_id}/enrolments")
def list_student_enrolments(
    student_id: int,
    include_closed: bool = True,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    _get_owned(db, Student, school_id, student_id)
    query = db.query(Enrolment).filter(Enrolment.school_id == school_id, Enrolment.student_id == student_id)
    if not include_closed:
        query = query.filter(*open_interval_expression(Enrolment, _today()))
    rows = query.order_by(Enrolment.valid_from.desc(), Enrolment.id.desc()).all()
    return [_enrolment_payload(db, row) for row in rows]


@router.post("/students/{student_id}/enrolments", status_code=status.HTTP_201_CREATED)
def add_student_enrolment(
    student_id: int,
    payload: EnrolmentRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    student = _get_owned(db, Student, school_id, student_id)
    valid_from = _validate_valid_from(payload.valid_from)
    class_section_id, subject_group_id = _ensure_active_enrolment_target(
        db,
        school_id,
        class_section_id=payload.class_section_id,
        subject_group_id=payload.subject_group_id,
    )
    row = _create_enrolment_row(
        db,
        school_id=school_id,
        student=student,
        class_section_id=class_section_id,
        subject_group_id=subject_group_id,
        valid_from=valid_from,
        created_by_user_id=membership.user_id,
        kind=payload.kind,
    )
    write_audit(
        db,
        membership.user_id,
        "school.enrolment.created",
        row,
        {"student_id": student.id, "class_section_id": class_section_id, "subject_group_id": subject_group_id, "kind": payload.kind},
        school_id=school_id,
    )
    db.commit()
    db.refresh(row)
    return _enrolment_payload(db, row)


@router.delete("/enrolments/{enrolment_id}")
def close_enrolment(
    enrolment_id: int,
    payload: CloseEnrolmentRequest | None = None,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    row = db.query(Enrolment).filter(Enrolment.id == enrolment_id, Enrolment.school_id == school_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrolment not found")
    _close_enrolment_row(row, payload.valid_to if payload else None)
    write_audit(db, membership.user_id, "school.enrolment.closed", row, {"student_id": row.student_id, "valid_to": str(row.valid_to)}, school_id=school_id)
    db.commit()
    db.refresh(row)
    return _enrolment_payload(db, row)


@router.post("/students/{student_id}/move-section", status_code=status.HTTP_201_CREATED)
def move_student_section(
    student_id: int,
    payload: MoveSectionRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    student = _get_owned(db, Student, school_id, student_id)
    valid_from = _validate_valid_from(payload.valid_from)
    class_section_id, _ = _ensure_active_enrolment_target(db, school_id, class_section_id=payload.class_section_id, subject_group_id=None)
    open_sections = _open_enrolments_query(db, school_id).filter(Enrolment.student_id == student.id, Enrolment.class_section_id.is_not(None)).all()
    if any(row.class_section_id == class_section_id for row in open_sections):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student is already enrolled in this class section")
    for row in open_sections:
        _close_enrolment_row(row, valid_from)
    new_row = _create_enrolment_row(
        db,
        school_id=school_id,
        student=student,
        class_section_id=class_section_id,
        subject_group_id=None,
        valid_from=valid_from,
        created_by_user_id=membership.user_id,
        kind="member",
        skip_class_open_check=True,
    )
    write_audit(
        db,
        membership.user_id,
        "school.enrolment.moved",
        new_row,
        {"student_id": student.id, "closed_enrolment_ids": [row.id for row in open_sections], "class_section_id": class_section_id},
        school_id=school_id,
    )
    db.commit()
    db.refresh(new_row)
    return {"new_enrolment": _enrolment_payload(db, new_row), "closed_enrolment_ids": [row.id for row in open_sections]}


@router.get("/class-sections/{class_section_id}/students")
def list_active_students_by_class_section(
    class_section_id: int,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    return _roster_payload(db, _school_id(membership), class_section_id=class_section_id)


@router.get("/class-sections/{class_section_id}/roster")
def get_class_section_roster_setup(
    class_section_id: int,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    return _class_roster_setup_payload(db, _school_id(membership), class_section_id)


@router.get("/subject-groups/{subject_group_id}/students")
def list_active_students_by_subject_group(
    subject_group_id: int,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    return _roster_payload(db, _school_id(membership), subject_group_id=subject_group_id)

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Type

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import auth, invite_tokens
from ..database import get_db, settings
from ..imports_service import (
    CSV_COLUMNS,
    TEACHER_CSV_COLUMNS,
    ImportUploadError,
    decode_csv_bytes,
    existing_guardian_contacts_by_student,
    generate_template_csv,
    open_section_enrolments_by_student,
    parse_csv_rows,
    plan_student_import_rows,
    plan_teacher_import_rows,
    summarize_plans,
)
from ..models_school import (
    AcademicYear,
    BranchCampus,
    ClassSection,
    DefaultSubjectTemplate,
    EducationStage,
    Enrolment,
    FhhLinkInvite,
    GradeLevel,
    GuardianInvite,
    GuardianLink,
    Import,
    ImportRow,
    Membership,
    School,
    StaffAssignment,
    StaffInvite,
    Student,
    StudentGuardianContact,
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


class DefaultSubjectTemplateRequest(BaseModel):
    education_stage_id: int | None = None
    grade_level_id: int | None = None
    subject_id: int
    sort_order: int = 0
    status: str = Field(default="active", max_length=40)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"active", "inactive"}:
            raise ValueError("status must be active or inactive")
        return value


class DefaultSubjectTemplateApplyRequest(BaseModel):
    academic_year_id: int
    branch_campus_id: int | None = None
    education_stage_id: int | None = None
    grade_level_id: int | None = None


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


class GuardianInviteCreateRequest(BaseModel):
    contact_id: int | None = None
    slot: int | None = None
    relationship: str | None = None
    guardian_name: str | None = Field(default=None, max_length=200)
    guardian_email: EmailStr | None = None

    @field_validator("slot")
    @classmethod
    def validate_slot(cls, value: int | None) -> int | None:
        if value is not None and value not in {1, 2}:
            raise ValueError("slot must be 1 or 2")
        return value

    @field_validator("relationship")
    @classmethod
    def validate_relationship(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if cleaned not in {"mother", "father", "guardian", "other"}:
            raise ValueError("relationship must be mother, father, guardian, or other")
        return cleaned


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


def _guardian_relationship_label(value: str | None) -> str | None:
    return value if value in {"mother", "father", "guardian", "other"} else None


def _guardian_invite_status(row: GuardianInvite) -> str:
    now = invite_tokens.now_utc()
    if row.claimed_at is not None:
        return "claimed"
    if row.revoked_at is not None:
        return "revoked"
    expires_at = invite_tokens.as_utc_aware(row.expires_at)
    if expires_at is None or expires_at <= now:
        return "expired"
    return "active"


def _guardian_contact_payload(row: StudentGuardianContact) -> dict[str, Any]:
    return {
        "id": row.id,
        "slot": row.slot,
        "name": row.name,
        "email": row.email,
        "relationship": row.relationship,
        "status": row.status,
    }


def _guardian_invite_payload(row: GuardianInvite) -> dict[str, Any]:
    return {
        "id": row.id,
        "student_id": row.student_id,
        "student_guardian_contact_id": row.student_guardian_contact_id,
        "slot": row.slot,
        "relationship": row.relationship,
        "guardian_name": row.guardian_name,
        "display_code_last4": row.display_code_last4,
        "status": _guardian_invite_status(row),
        "expires_at": row.expires_at,
        "created_at": row.created_at,
        "revoked_at": row.revoked_at,
        "claimed_at": row.claimed_at,
        "claimed_by_user_id": row.claimed_by_user_id,
    }


def _guardian_link_payload(row: GuardianLink, user: User | None = None) -> dict[str, Any]:
    return {
        "id": row.id,
        "student_id": row.student_id,
        "user_id": row.user_id,
        "relationship": row.relationship,
        "display_name": row.display_name or getattr(user, "name", None),
        "user_name": getattr(user, "name", None),
        "user_email": getattr(user, "email", None),
        "email_matched_contact": row.email_matched_contact,
        "status": row.status,
        "created_at": row.created_at,
        "revoked_at": row.revoked_at,
    }


def _guardian_join_url(display_code: str) -> str:
    return f"{settings.PUBLIC_APP_URL.rstrip('/')}/join?c={display_code}"


def _active_live_invite_query(db: Session, school_id: int, student_id: int, slot: int | None):
    query = db.query(GuardianInvite).filter(
        GuardianInvite.school_id == school_id,
        GuardianInvite.student_id == student_id,
        GuardianInvite.revoked_at.is_(None),
        GuardianInvite.claimed_at.is_(None),
        GuardianInvite.expires_at > invite_tokens.now_utc(),
    )
    return query.filter(GuardianInvite.slot == slot) if slot is not None else query.filter(GuardianInvite.slot.is_(None))


def _ensure_guardian_membership(db: Session, school_id: int, user_id: int, created_by_user_id: int | None) -> Membership:
    membership = (
        db.query(Membership)
        .filter(Membership.school_id == school_id, Membership.user_id == user_id, Membership.role == "guardian")
        .first()
    )
    if membership:
        membership.status = "active"
        membership.revoked_at = None
        membership.revoked_by_user_id = None
        return membership
    membership = Membership(
        school_id=school_id,
        user_id=user_id,
        role="guardian",
        status="active",
        created_by_user_id=created_by_user_id,
    )
    db.add(membership)
    db.flush()
    return membership


def _revoke_guardian_membership_if_last_link(db: Session, school_id: int, user_id: int, revoked_by_user_id: int, *, exclude_link_id: int | None = None) -> None:
    query = db.query(GuardianLink.id).filter(
        GuardianLink.school_id == school_id,
        GuardianLink.user_id == user_id,
        GuardianLink.status == "active",
        GuardianLink.revoked_at.is_(None),
    )
    if exclude_link_id is not None:
        query = query.filter(GuardianLink.id != exclude_link_id)
    still_active = (
        query.first()
    )
    if still_active:
        return
    membership = (
        db.query(Membership)
        .filter(Membership.school_id == school_id, Membership.user_id == user_id, Membership.role == "guardian")
        .first()
    )
    if membership and membership.status == "active":
        membership.status = "revoked"
        membership.revoked_at = invite_tokens.now_utc()
        membership.revoked_by_user_id = revoked_by_user_id


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


def _default_subject_template_payload(row: DefaultSubjectTemplate) -> dict[str, Any]:
    return {
        "id": row.id,
        "school_id": row.school_id,
        "education_stage_id": row.education_stage_id,
        "grade_level_id": row.grade_level_id,
        "subject_id": row.subject_id,
        "status": row.status,
        "sort_order": row.sort_order,
        "created_by_user_id": row.created_by_user_id,
        "created_at": row.created_at,
    }


def _default_subject_templates_payload_bulk(db: Session, rows: list[DefaultSubjectTemplate]) -> list[dict[str, Any]]:
    subject_ids = {row.subject_id for row in rows}
    stage_ids = {row.education_stage_id for row in rows if row.education_stage_id is not None}
    grade_ids = {row.grade_level_id for row in rows if row.grade_level_id is not None}
    subjects_by_id = {s.id: _payload(s) for s in (db.query(Subject).filter(Subject.id.in_(subject_ids)).all() if subject_ids else [])}
    stages_by_id = {s.id: _payload(s) for s in (db.query(EducationStage).filter(EducationStage.id.in_(stage_ids)).all() if stage_ids else [])}
    grades_by_id = {g.id: _payload(g) for g in (db.query(GradeLevel).filter(GradeLevel.id.in_(grade_ids)).all() if grade_ids else [])}
    return [
        {
            **_default_subject_template_payload(row),
            "subject": subjects_by_id.get(row.subject_id),
            "education_stage": stages_by_id.get(row.education_stage_id),
            "grade_level": grades_by_id.get(row.grade_level_id),
        }
        for row in rows
    ]


def _validate_template_scope(payload: DefaultSubjectTemplateRequest) -> None:
    if (payload.education_stage_id is None) == (payload.grade_level_id is None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exactly one of education_stage_id or grade_level_id is required")


def _find_default_subject_template(
    db: Session,
    school_id: int,
    education_stage_id: int | None,
    grade_level_id: int | None,
    subject_id: int,
) -> DefaultSubjectTemplate | None:
    # Nullable-column unique constraints do not dedupe NULLs in SQL, so the
    # stage/grade natural key must be matched explicitly with .is_(None).
    filters = [DefaultSubjectTemplate.school_id == school_id, DefaultSubjectTemplate.subject_id == subject_id]
    filters.append(
        DefaultSubjectTemplate.education_stage_id.is_(None)
        if education_stage_id is None
        else DefaultSubjectTemplate.education_stage_id == education_stage_id
    )
    filters.append(
        DefaultSubjectTemplate.grade_level_id.is_(None)
        if grade_level_id is None
        else DefaultSubjectTemplate.grade_level_id == grade_level_id
    )
    return db.query(DefaultSubjectTemplate).filter(*filters).first()


@router.get("/default-subject-templates")
def list_default_subject_templates(
    include_archived: bool = False,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    query = db.query(DefaultSubjectTemplate).filter(DefaultSubjectTemplate.school_id == school_id)
    if not include_archived:
        query = query.filter(DefaultSubjectTemplate.status != "archived")
    rows = query.order_by(DefaultSubjectTemplate.sort_order.asc(), DefaultSubjectTemplate.id.asc()).all()
    return _default_subject_templates_payload_bulk(db, rows)


@router.post("/default-subject-templates", status_code=status.HTTP_201_CREATED)
def create_default_subject_template(
    payload: DefaultSubjectTemplateRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    _validate_template_scope(payload)
    _ensure_owned(db, EducationStage, school_id, payload.education_stage_id, "education_stage_id")
    _ensure_owned(db, GradeLevel, school_id, payload.grade_level_id, "grade_level_id")
    _ensure_owned(db, Subject, school_id, payload.subject_id, "subject_id")

    existing = _find_default_subject_template(db, school_id, payload.education_stage_id, payload.grade_level_id, payload.subject_id)
    if existing is not None:
        if existing.status != "archived":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_active_duplicate_detail(existing.status))
        existing.sort_order = payload.sort_order
        existing.status = "active"
        _commit_or_conflict(db, "This value is already used by another record.")
        db.refresh(existing)
        write_audit(
            db,
            membership.user_id,
            "school.default_subject_template.restored",
            existing,
            {"education_stage_id": existing.education_stage_id, "grade_level_id": existing.grade_level_id, "subject_id": existing.subject_id},
            school_id=school_id,
        )
        db.commit()
        return {**_default_subject_template_payload(existing), "restored": True}

    row = DefaultSubjectTemplate(
        school_id=school_id,
        education_stage_id=payload.education_stage_id,
        grade_level_id=payload.grade_level_id,
        subject_id=payload.subject_id,
        sort_order=payload.sort_order,
        status=payload.status,
        created_by_user_id=membership.user_id,
    )
    db.add(row)
    _commit_or_conflict(db, "This value is already used by another record.")
    db.refresh(row)
    return {**_default_subject_template_payload(row), "restored": False}


@router.put("/default-subject-templates/{row_id}")
def update_default_subject_template(
    row_id: int,
    payload: DefaultSubjectTemplateRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    row = _get_owned(db, DefaultSubjectTemplate, school_id, row_id)
    _validate_template_scope(payload)
    _ensure_owned(db, EducationStage, school_id, payload.education_stage_id, "education_stage_id", current_id=row.education_stage_id)
    _ensure_owned(db, GradeLevel, school_id, payload.grade_level_id, "grade_level_id", current_id=row.grade_level_id)
    _ensure_owned(db, Subject, school_id, payload.subject_id, "subject_id", current_id=row.subject_id)

    duplicate = _find_default_subject_template(db, school_id, payload.education_stage_id, payload.grade_level_id, payload.subject_id)
    if duplicate is not None and duplicate.id != row.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This value is already used by another record.")

    row.education_stage_id = payload.education_stage_id
    row.grade_level_id = payload.grade_level_id
    row.subject_id = payload.subject_id
    row.sort_order = payload.sort_order
    row.status = payload.status
    _commit_or_conflict(db)
    db.refresh(row)
    return _default_subject_template_payload(row)


@router.delete("/default-subject-templates/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_default_subject_template(
    row_id: int,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    _archive_row(db, _get_owned(db, DefaultSubjectTemplate, _school_id(membership), row_id))


def _plan_default_subject_template_application(
    db: Session,
    school_id: int,
    payload: DefaultSubjectTemplateApplyRequest,
) -> list[dict[str, Any]]:
    """Batched plan for preview/apply: a fixed number of queries regardless of section/subject count."""
    _ensure_owned(db, AcademicYear, school_id, payload.academic_year_id, "academic_year_id")
    _ensure_owned(db, BranchCampus, school_id, payload.branch_campus_id, "branch_campus_id")
    _ensure_owned(db, EducationStage, school_id, payload.education_stage_id, "education_stage_id")
    _ensure_owned(db, GradeLevel, school_id, payload.grade_level_id, "grade_level_id")

    sections_query = db.query(ClassSection).filter(
        ClassSection.school_id == school_id,
        ClassSection.academic_year_id == payload.academic_year_id,
        ClassSection.status == "active",
    )
    if payload.branch_campus_id is not None:
        sections_query = sections_query.filter(ClassSection.branch_campus_id == payload.branch_campus_id)
    if payload.grade_level_id is not None:
        sections_query = sections_query.filter(ClassSection.grade_level_id == payload.grade_level_id)
    if payload.education_stage_id is not None:
        stage_grade_ids = select(GradeLevel.id).where(
            GradeLevel.school_id == school_id, GradeLevel.education_stage_id == payload.education_stage_id
        )
        sections_query = sections_query.filter(ClassSection.grade_level_id.in_(stage_grade_ids))
    sections = sections_query.order_by(ClassSection.sort_order.asc(), ClassSection.id.asc()).all()
    if not sections:
        return []

    grade_ids = {section.grade_level_id for section in sections}
    grades_by_id = {g.id: g for g in db.query(GradeLevel).filter(GradeLevel.id.in_(grade_ids)).all()} if grade_ids else {}

    templates = (
        db.query(DefaultSubjectTemplate)
        .filter(DefaultSubjectTemplate.school_id == school_id, DefaultSubjectTemplate.status == "active")
        .order_by(DefaultSubjectTemplate.sort_order.asc(), DefaultSubjectTemplate.id.asc())
        .all()
    )
    stage_template_subject_ids: dict[int, list[int]] = {}
    grade_template_subject_ids: dict[int, list[int]] = {}
    for template in templates:
        if template.education_stage_id is not None:
            stage_template_subject_ids.setdefault(template.education_stage_id, []).append(template.subject_id)
        else:
            grade_template_subject_ids.setdefault(template.grade_level_id, []).append(template.subject_id)

    subject_ids = {sid for ids in stage_template_subject_ids.values() for sid in ids} | {
        sid for ids in grade_template_subject_ids.values() for sid in ids
    }
    subjects_by_id = {s.id: s for s in db.query(Subject).filter(Subject.id.in_(subject_ids)).all()} if subject_ids else {}

    section_subject_pairs: list[tuple[ClassSection, int]] = []
    for section in sections:
        grade = grades_by_id.get(section.grade_level_id)
        stage_id = grade.education_stage_id if grade is not None else None
        seen: set[int] = set()
        ordered_subject_ids: list[int] = []
        for sid in (stage_template_subject_ids.get(stage_id, []) if stage_id is not None else []):
            if sid not in seen:
                seen.add(sid)
                ordered_subject_ids.append(sid)
        for sid in grade_template_subject_ids.get(section.grade_level_id, []):
            if sid not in seen:
                seen.add(sid)
                ordered_subject_ids.append(sid)
        for sid in ordered_subject_ids:
            section_subject_pairs.append((section, sid))

    section_ids = {section.id for section, _ in section_subject_pairs}
    existing_groups = (
        db.query(SubjectGroup)
        .filter(
            SubjectGroup.school_id == school_id,
            SubjectGroup.academic_year_id == payload.academic_year_id,
            SubjectGroup.class_section_id.in_(section_ids),
        )
        .all()
        if section_ids
        else []
    )

    plan: list[dict[str, Any]] = []
    for section, subject_id in section_subject_pairs:
        subject = subjects_by_id.get(subject_id)
        if subject is None:
            plan.append({"section": section, "subject_id": subject_id, "action": "fail", "reason": "Subject not found"})
            continue
        if subject.status == "archived":
            plan.append({"section": section, "subject": subject, "action": "fail", "reason": "Subject is archived"})
            continue
        grade = grades_by_id.get(section.grade_level_id)
        defaults = _subject_group_defaults(subject=subject, section=section, grade_level=grade)
        code = defaults["code"]
        existing = next(
            (g for g in existing_groups if g.class_section_id == section.id and g.subject_id == subject_id and g.code == code),
            None,
        )
        if existing is None:
            action = "create"
        elif existing.status == "archived":
            action = "restore"
        else:
            action = "skip"
        plan.append(
            {
                "section": section,
                "subject": subject,
                "code": code,
                "name": defaults["name"],
                "action": action,
                "existing_group": existing,
                "reason": _active_duplicate_detail(existing.status) if action == "skip" else None,
            }
        )
    return plan


def _default_subject_template_plan_row(item: dict[str, Any]) -> dict[str, Any]:
    section = item.get("section")
    subject = item.get("subject")
    return {
        "class_section_id": section.id if section is not None else None,
        "class_section": _payload(section) if section is not None else None,
        "subject_id": subject.id if subject is not None else item.get("subject_id"),
        "subject": _payload(subject) if subject is not None else None,
        "code": item.get("code"),
        "name": item.get("name"),
    }


_PLAN_PREVIEW_LABELS = {"create": "would_create", "restore": "would_restore", "skip": "skipped_existing", "fail": "failed"}


@router.post("/default-subject-templates/preview")
def preview_default_subject_templates(
    payload: DefaultSubjectTemplateApplyRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    plan = _plan_default_subject_template_application(db, _school_id(membership), payload)
    counts = {label: 0 for label in _PLAN_PREVIEW_LABELS.values()}
    results = []
    for item in plan:
        label = _PLAN_PREVIEW_LABELS[item["action"]]
        counts[label] += 1
        row = _default_subject_template_plan_row(item)
        row["status"] = label
        row["reason"] = item.get("reason")
        results.append(row)
    return {**counts, "results": results}


@router.post("/default-subject-templates/apply")
def apply_default_subject_templates(
    payload: DefaultSubjectTemplateApplyRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    plan = _plan_default_subject_template_application(db, school_id, payload)

    created = restored = skipped = failed = 0
    results = []
    for item in plan:
        row = _default_subject_template_plan_row(item)
        if item["action"] == "create":
            section = item["section"]
            group = SubjectGroup(
                school_id=school_id,
                academic_year_id=payload.academic_year_id,
                class_section_id=section.id,
                grade_level_id=None,
                subject_id=item["subject"].id,
                code=item["code"],
                name=item["name"],
                name_ar=None,
                sort_order=section.sort_order,
                status="active",
                enrolment_policy="default_for_section",
            )
            db.add(group)
            db.flush()
            created += 1
            row["status"] = "created"
            row["reason"] = None
            row["subject_group"] = _payload(group)
        elif item["action"] == "restore":
            group = item["existing_group"]
            group.name = item["name"]
            group.enrolment_policy = "default_for_section"
            group.status = "active"
            db.flush()
            restored += 1
            write_audit(
                db,
                membership.user_id,
                "school.subject_group.restored",
                group,
                {"code": group.code, "status": group.status, "source": "default_subject_template"},
                school_id=school_id,
            )
            row["status"] = "restored"
            row["reason"] = None
            row["subject_group"] = _payload(group)
        elif item["action"] == "skip":
            skipped += 1
            row["status"] = "skipped_existing"
            row["reason"] = item.get("reason")
            row["subject_group"] = _payload(item["existing_group"])
        else:
            failed += 1
            row["status"] = "failed"
            row["reason"] = item.get("reason")
        results.append(row)

    if created or restored:
        write_audit(
            db,
            membership.user_id,
            "school.default_subject_template.applied",
            ("subject_groups", None),
            {
                "academic_year_id": payload.academic_year_id,
                "branch_campus_id": payload.branch_campus_id,
                "education_stage_id": payload.education_stage_id,
                "grade_level_id": payload.grade_level_id,
                "created": created,
                "restored": restored,
                "skipped": skipped,
                "failed": failed,
            },
            school_id=school_id,
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Apply conflicted with a concurrent change. Re-run preview and try again.")

    return {"created": created, "restored": restored, "skipped": skipped, "failed": failed, "results": results}


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


def _import_summary_payload(imp: Import) -> dict[str, Any]:
    return {
        "id": imp.id,
        "school_id": imp.school_id,
        "kind": imp.kind,
        "filename": imp.filename,
        "status": imp.status,
        "summary": imp.summary,
        "created_at": imp.created_at,
        "committed_at": imp.committed_at,
    }


def _import_row_payload(row: ImportRow) -> dict[str, Any]:
    csv_row = row.raw or {}
    return {
        "id": row.id,
        "row_number": row.row_number,
        "student_id": csv_row.get("student_id") or None,
        "first_name": csv_row.get("first_name") or None,
        "last_name": csv_row.get("last_name") or None,
        "grade": csv_row.get("grade") or None,
        "section": csv_row.get("section") or None,
        "branch": csv_row.get("branch") or None,
        "guardian1_name": csv_row.get("guardian1_name") or None,
        "guardian1_email": csv_row.get("guardian1_email") or None,
        "guardian1_relationship": csv_row.get("guardian1_relationship") or None,
        "guardian2_name": csv_row.get("guardian2_name") or None,
        "guardian2_email": csv_row.get("guardian2_email") or None,
        "guardian2_relationship": csv_row.get("guardian2_relationship") or None,
        "action": row.action,
        "errors": row.errors or [],
        "warnings": row.warnings or [],
        "applied_entity_id": row.applied_entity_id,
    }


def _import_detail_payload(db: Session, imp: Import, row_payload_fn=_import_row_payload) -> dict[str, Any]:
    rows = db.query(ImportRow).filter(ImportRow.import_id == imp.id).order_by(ImportRow.row_number.asc()).all()
    return {**_import_summary_payload(imp), "rows": [row_payload_fn(row) for row in rows]}


@router.get("/students/import-template")
def download_student_import_template(membership: Membership = Depends(require_school_role("school_admin"))):
    csv_text = generate_template_csv(CSV_COLUMNS)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=student_import_template.csv"},
    )


@router.post("/students/imports", status_code=status.HTTP_201_CREATED)
async def upload_student_import(
    file: UploadFile = File(...),
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    content = await file.read()
    try:
        text = decode_csv_bytes(content)
        raw_rows = parse_csv_rows(text, CSV_COLUMNS)
        if not raw_rows:
            raise ImportUploadError("CSV has no data rows")
        plans = plan_student_import_rows(db, school_id, raw_rows, today=_today())
    except ImportUploadError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    summary = summarize_plans(plans)
    imp = Import(
        school_id=school_id,
        kind="students",
        filename=file.filename,
        status="staged",
        uploaded_by_user_id=membership.user_id,
        summary=summary,
    )
    db.add(imp)
    db.flush()
    for plan in plans:
        db.add(
            ImportRow(
                import_id=imp.id,
                row_number=plan.row_number,
                raw=plan.csv,
                action=plan.action,
                errors=plan.errors or None,
                warnings=plan.warnings or None,
            )
        )
    write_audit(db, membership.user_id, "school.import.staged", imp, {"filename": file.filename, "summary": summary}, school_id=school_id)
    db.commit()
    db.refresh(imp)
    return _import_detail_payload(db, imp)


@router.get("/students/imports/{import_id}")
def get_student_import(import_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    imp = _get_owned(db, Import, _school_id(membership), import_id)
    return _import_detail_payload(db, imp)


@router.post("/students/imports/{import_id}/commit")
def commit_student_import(import_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    imp = _get_owned(db, Import, school_id, import_id)
    if imp.status != "staged":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only staged imports can be committed")

    rows = db.query(ImportRow).filter(ImportRow.import_id == imp.id).order_by(ImportRow.row_number.asc()).all()
    raw_rows = [row.raw for row in rows]
    today = _today()
    try:
        plans = plan_student_import_rows(db, school_id, raw_rows, today=today)
    except ImportUploadError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    student_ids = [plan.student_id for plan in plans if plan.student_id is not None]
    students_by_id = {
        s.id: s
        for s in (
            db.query(Student).filter(Student.school_id == school_id, Student.id.in_(student_ids)).all()
            if student_ids
            else []
        )
    }
    open_section_by_student = open_section_enrolments_by_student(db, school_id, student_ids, today)
    existing_guardian_contacts = existing_guardian_contacts_by_student(db, school_id, student_ids)

    for plan, row in zip(plans, rows):
        row.action = plan.action
        row.errors = plan.errors or None
        row.warnings = plan.warnings or None

        if plan.action == "error":
            continue

        if plan.action == "create":
            student = Student(school_id=school_id, status="active", **plan.cleaned)
            db.add(student)
            db.flush()
        else:
            student = students_by_id[plan.student_id]
            for key, value in plan.cleaned.items():
                setattr(student, key, value)
            if plan.action == "restore":
                student.status = "active"

        row.applied_entity_id = student.id

        # A direct Enrolment insert (not _create_enrolment_row) is intentional
        # here: the batched open_section_by_student/students_by_id lookups
        # above already establish everything that helper would otherwise
        # re-check per row (active target, no duplicate open enrolment), and
        # re-running those as per-row queries would break the "no per-row
        # query in a list/bulk endpoint" rule (see BACKEND_PERFORMANCE.md).
        # _close_enrolment_row is pure (no query), so it's reused as-is.
        if plan.action != "skip":
            current_enrolment = open_section_by_student.get(student.id)
            if current_enrolment is None or current_enrolment.class_section_id != plan.class_section_id:
                if current_enrolment is not None:
                    _close_enrolment_row(current_enrolment, today)
                db.add(
                    Enrolment(
                        school_id=school_id,
                        student_id=student.id,
                        class_section_id=plan.class_section_id,
                        kind="member",
                        valid_from=today,
                        created_by_user_id=membership.user_id,
                    )
                )

        # Guardian contacts are draft-only prep records (never contacted, no
        # login, no guardian_link) and are upserted regardless of the
        # student row's own action — a guardian-only edit on an otherwise
        # unchanged student must still land, not be skipped along with the
        # student "skip" action.
        for contact in plan.guardian_contacts:
            key = (student.id, contact["slot"])
            existing_contact = existing_guardian_contacts.get(key)
            if existing_contact is not None:
                if existing_contact.status != "draft":
                    # S9 (or an admin) has already acted on this contact;
                    # a re-import must not clobber that decision.
                    continue
                existing_contact.name = contact["name"]
                existing_contact.email = contact["email"]
                existing_contact.relationship = contact["relationship"]
                existing_contact.source_import_id = imp.id
            else:
                db.add(
                    StudentGuardianContact(
                        school_id=school_id,
                        student_id=student.id,
                        slot=contact["slot"],
                        name=contact["name"],
                        email=contact["email"],
                        relationship=contact["relationship"],
                        source_import_id=imp.id,
                        status="draft",
                    )
                )

    summary = summarize_plans(plans)
    imp.status = "committed"
    imp.committed_at = invite_tokens.now_utc()
    imp.summary = summary
    write_audit(db, membership.user_id, "school.import.committed", imp, {"summary": summary}, school_id=school_id)
    db.commit()
    db.refresh(imp)
    return _import_detail_payload(db, imp)


@router.post("/students/imports/{import_id}/discard")
def discard_student_import(import_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    imp = _get_owned(db, Import, school_id, import_id)
    if imp.status != "staged":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only staged imports can be discarded")
    imp.status = "discarded"
    write_audit(db, membership.user_id, "school.import.discarded", imp, {}, school_id=school_id)
    db.commit()
    db.refresh(imp)
    return _import_summary_payload(imp)


def _teacher_import_row_payload(row: ImportRow) -> dict[str, Any]:
    csv_row = row.raw or {}
    return {
        "id": row.id,
        "row_number": row.row_number,
        "email": csv_row.get("email") or None,
        "first_name": csv_row.get("first_name") or None,
        "last_name": csv_row.get("last_name") or None,
        "name_ar": csv_row.get("name_ar") or None,
        "action": row.action,
        "errors": row.errors or [],
        "warnings": row.warnings or [],
        "applied_entity_id": row.applied_entity_id,
    }


@router.get("/teachers/import-template")
def download_teacher_import_template(membership: Membership = Depends(require_school_role("school_admin"))):
    csv_text = generate_template_csv(TEACHER_CSV_COLUMNS)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=teacher_import_template.csv"},
    )


@router.post("/teachers/imports", status_code=status.HTTP_201_CREATED)
async def upload_teacher_import(
    file: UploadFile = File(...),
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    content = await file.read()
    try:
        text = decode_csv_bytes(content)
        raw_rows = parse_csv_rows(text, TEACHER_CSV_COLUMNS)
        if not raw_rows:
            raise ImportUploadError("CSV has no data rows")
        plans = plan_teacher_import_rows(db, school_id, raw_rows)
    except ImportUploadError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    summary = summarize_plans(plans)
    imp = Import(
        school_id=school_id,
        kind="teachers",
        filename=file.filename,
        status="staged",
        uploaded_by_user_id=membership.user_id,
        summary=summary,
    )
    db.add(imp)
    db.flush()
    for plan in plans:
        db.add(
            ImportRow(
                import_id=imp.id,
                row_number=plan.row_number,
                raw=plan.csv,
                action=plan.action,
                errors=plan.errors or None,
                warnings=plan.warnings or None,
            )
        )
    write_audit(db, membership.user_id, "school.teacher_import.staged", imp, {"filename": file.filename, "summary": summary}, school_id=school_id)
    db.commit()
    db.refresh(imp)
    return _import_detail_payload(db, imp, _teacher_import_row_payload)


@router.get("/teachers/imports/{import_id}")
def get_teacher_import(import_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    imp = _get_owned(db, Import, _school_id(membership), import_id)
    return _import_detail_payload(db, imp, _teacher_import_row_payload)


@router.post("/teachers/imports/{import_id}/commit")
def commit_teacher_import(import_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    imp = _get_owned(db, Import, school_id, import_id)
    if imp.status != "staged":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only staged imports can be committed")

    rows = db.query(ImportRow).filter(ImportRow.import_id == imp.id).order_by(ImportRow.row_number.asc()).all()
    raw_rows = [row.raw for row in rows]
    try:
        plans = plan_teacher_import_rows(db, school_id, raw_rows)
    except ImportUploadError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    user_ids = [plan.user_id for plan in plans if plan.user_id is not None]
    users_by_id = {
        u.id: u for u in (db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else [])
    }
    membership_ids = [plan.membership_id for plan in plans if plan.membership_id is not None]
    memberships_by_id = {
        m.id: m
        for m in (
            db.query(Membership).filter(Membership.school_id == school_id, Membership.id.in_(membership_ids)).all()
            if membership_ids
            else []
        )
    }

    for plan, row in zip(plans, rows):
        row.action = plan.action
        row.errors = plan.errors or None
        row.warnings = plan.warnings or None

        if plan.action == "error":
            continue

        if plan.action == "create":
            user = users_by_id.get(plan.user_id) if plan.user_id is not None else None
            if user is None:
                user = User(
                    email=auth.normalize_email(plan.csv["email"]),
                    name=f"{plan.cleaned['first_name']} {plan.cleaned['last_name']}".strip(),
                    name_ar=plan.cleaned["name_ar"],
                    status="active",
                )
                db.add(user)
                db.flush()
            teacher_membership = Membership(
                school_id=school_id,
                user_id=user.id,
                role="teacher",
                status="active",
                created_by_user_id=membership.user_id,
            )
            db.add(teacher_membership)
            db.flush()
            row.applied_entity_id = teacher_membership.id
        elif plan.action == "update":
            user = users_by_id[plan.user_id]
            if not user.name:
                user.name = f"{plan.cleaned['first_name']} {plan.cleaned['last_name']}".strip()
            if not user.name_ar and plan.cleaned["name_ar"]:
                user.name_ar = plan.cleaned["name_ar"]
            row.applied_entity_id = memberships_by_id[plan.membership_id].id
        else:
            row.applied_entity_id = plan.membership_id

    summary = summarize_plans(plans)
    imp.status = "committed"
    imp.committed_at = invite_tokens.now_utc()
    imp.summary = summary
    write_audit(db, membership.user_id, "school.teacher_import.committed", imp, {"summary": summary}, school_id=school_id)
    db.commit()
    db.refresh(imp)
    return _import_detail_payload(db, imp, _teacher_import_row_payload)


@router.post("/teachers/imports/{import_id}/discard")
def discard_teacher_import(import_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    imp = _get_owned(db, Import, school_id, import_id)
    if imp.status != "staged":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only staged imports can be discarded")
    imp.status = "discarded"
    write_audit(db, membership.user_id, "school.teacher_import.discarded", imp, {}, school_id=school_id)
    db.commit()
    db.refresh(imp)
    return _import_summary_payload(imp)


@router.get("/students/{student_id}/guardian-invites")
def list_student_guardians(student_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    student = _get_owned(db, Student, school_id, student_id)
    contacts = (
        db.query(StudentGuardianContact)
        .filter(StudentGuardianContact.school_id == school_id, StudentGuardianContact.student_id == student.id)
        .order_by(StudentGuardianContact.slot.asc())
        .all()
    )
    invites = (
        db.query(GuardianInvite)
        .filter(GuardianInvite.school_id == school_id, GuardianInvite.student_id == student.id)
        .order_by(GuardianInvite.created_at.desc(), GuardianInvite.id.desc())
        .all()
    )
    links = (
        db.query(GuardianLink)
        .filter(GuardianLink.school_id == school_id, GuardianLink.student_id == student.id)
        .order_by(GuardianLink.created_at.desc(), GuardianLink.id.desc())
        .all()
    )
    user_ids = {link.user_id for link in links}
    users_by_id = {u.id: u for u in (db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else [])}
    return {
        "student": _student_with_context(db, student),
        "contacts": [_guardian_contact_payload(contact) for contact in contacts],
        "invites": [_guardian_invite_payload(invite) for invite in invites],
        "links": [_guardian_link_payload(link, users_by_id.get(link.user_id)) for link in links],
    }


@router.post("/students/{student_id}/guardian-invites", status_code=status.HTTP_201_CREATED)
def create_guardian_invite(
    student_id: int,
    payload: GuardianInviteCreateRequest,
    membership: Membership = Depends(require_school_role("school_admin")),
    db: Session = Depends(get_db),
):
    school_id = _school_id(membership)
    student = _get_owned(db, Student, school_id, student_id)
    if student.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Guardian invites require an active student")

    contact = None
    if payload.contact_id is not None:
        contact = (
            db.query(StudentGuardianContact)
            .filter(
                StudentGuardianContact.id == payload.contact_id,
                StudentGuardianContact.school_id == school_id,
                StudentGuardianContact.student_id == student.id,
            )
            .first()
        )
        if not contact:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid guardian contact")
        if contact.status == "ignored":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ignored guardian contacts cannot receive invites")
        slot = contact.slot
        relationship = _guardian_relationship_label(payload.relationship) or contact.relationship
        guardian_name = _clean_text(payload.guardian_name) or contact.name
        guardian_email = auth.normalize_email(str(payload.guardian_email)) if payload.guardian_email else contact.email
    else:
        slot = payload.slot
        if slot is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="slot or contact_id is required")
        relationship = _guardian_relationship_label(payload.relationship)
        guardian_name = _clean_text(payload.guardian_name)
        guardian_email = auth.normalize_email(str(payload.guardian_email)) if payload.guardian_email else None

    if _active_live_invite_query(db, school_id, student.id, slot).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An active invite already exists for this guardian slot. Revoke it before generating another.")

    raw_code = invite_tokens.generate_short_code()
    display_code = invite_tokens.display_short_code(raw_code)
    invite = GuardianInvite(
        school_id=school_id,
        student_id=student.id,
        student_guardian_contact_id=contact.id if contact else None,
        slot=slot,
        token_hash=invite_tokens.hash_token(invite_tokens.normalize_short_code(raw_code)),
        display_code_last4=raw_code[-4:],
        relationship=relationship,
        guardian_name=guardian_name,
        guardian_email=guardian_email,
        expires_at=invite_tokens.now_utc() + invite_tokens.GUARDIAN_INVITE_TTL,
        created_by_user_id=membership.user_id,
    )
    db.add(invite)
    db.flush()
    write_audit(
        db,
        membership.user_id,
        "school.guardian_invite.created",
        invite,
        {"student_id": student.id, "slot": slot, "contact_id": contact.id if contact else None},
        school_id=school_id,
    )
    db.commit()
    db.refresh(invite)
    return {**_guardian_invite_payload(invite), "code": display_code, "join_url": _guardian_join_url(display_code)}


@router.post("/guardian-invites/{invite_id}/revoke")
def revoke_guardian_invite(invite_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    invite = db.query(GuardianInvite).filter(GuardianInvite.id == invite_id, GuardianInvite.school_id == school_id).first()
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardian invite not found")
    if invite.claimed_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Claimed invites cannot be revoked")
    if invite.revoked_at is None:
        invite.revoked_at = invite_tokens.now_utc()
        invite.revoked_by_user_id = membership.user_id
        write_audit(db, membership.user_id, "school.guardian_invite.revoked", invite, {"student_id": invite.student_id}, school_id=school_id)
        db.commit()
        db.refresh(invite)
    return _guardian_invite_payload(invite)


def _fhh_invite_payload(row: FhhLinkInvite) -> dict[str, Any]:
    return {
        "id": row.id,
        "student_id": row.student_id,
        "display_code_last4": row.display_code_last4,
        "expires_at": row.expires_at,
        "consumed_at": row.consumed_at,
        "revoked_at": row.revoked_at,
        "created_at": row.created_at,
    }


@router.get("/students/{student_id}/fhh-invites")
def list_fhh_invites(student_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    student = _get_owned(db, Student, school_id, student_id)
    rows = db.query(FhhLinkInvite).filter(
        FhhLinkInvite.school_id == school_id, FhhLinkInvite.student_id == student.id
    ).order_by(FhhLinkInvite.created_at.desc(), FhhLinkInvite.id.desc()).all()
    return {"student": _student_with_context(db, student), "invites": [_fhh_invite_payload(row) for row in rows]}


@router.post("/students/{student_id}/fhh-invites", status_code=status.HTTP_201_CREATED)
def create_fhh_invite(student_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    student = _get_owned(db, Student, school_id, student_id)
    if student.status != "active":
        raise HTTPException(status_code=400, detail="FHH invites require an active student")
    raw_code = invite_tokens.generate_short_code()
    normalized = invite_tokens.normalize_short_code(raw_code)
    row = FhhLinkInvite(
        school_id=school_id, student_id=student.id,
        token_hash=invite_tokens.hash_token(normalized), display_code_last4=normalized[-4:],
        expires_at=invite_tokens.now_utc() + timedelta(hours=72),
        created_by_user_id=membership.user_id,
    )
    db.add(row); db.flush()
    write_audit(db, membership.user_id, "school.fhh_invite.created", row, {"student_id": student.id}, school_id=school_id)
    db.commit(); db.refresh(row)
    return {**_fhh_invite_payload(row), "code": invite_tokens.display_short_code(raw_code)}


@router.post("/fhh-invites/{invite_id}/revoke")
def revoke_fhh_invite(invite_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    row = db.query(FhhLinkInvite).filter(FhhLinkInvite.id == invite_id, FhhLinkInvite.school_id == school_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="FHH invite not found")
    if row.consumed_at is not None:
        raise HTTPException(status_code=409, detail="Consumed invites cannot be revoked")
    if row.revoked_at is None:
        row.revoked_at = invite_tokens.now_utc(); row.revoked_by_user_id = membership.user_id
        write_audit(db, membership.user_id, "school.fhh_invite.revoked", row, {"student_id": row.student_id}, school_id=school_id)
        db.commit(); db.refresh(row)
    return _fhh_invite_payload(row)


@router.post("/guardian-contacts/{contact_id}/ignore")
def ignore_guardian_contact(contact_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    contact = db.query(StudentGuardianContact).filter(StudentGuardianContact.id == contact_id, StudentGuardianContact.school_id == school_id).first()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardian contact not found")
    if contact.status == "linked":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Linked guardian contacts cannot be ignored")
    contact.status = "ignored"
    revoked_ids = []
    for invite in (
        db.query(GuardianInvite)
        .filter(
            GuardianInvite.school_id == school_id,
            GuardianInvite.student_guardian_contact_id == contact.id,
            GuardianInvite.revoked_at.is_(None),
            GuardianInvite.claimed_at.is_(None),
        )
        .all()
    ):
        invite.revoked_at = invite_tokens.now_utc()
        invite.revoked_by_user_id = membership.user_id
        revoked_ids.append(invite.id)
    write_audit(db, membership.user_id, "school.guardian_contact.ignored", contact, {"revoked_invite_ids": revoked_ids}, school_id=school_id)
    db.commit()
    db.refresh(contact)
    return _guardian_contact_payload(contact)


@router.post("/guardian-links/{link_id}/revoke")
def revoke_guardian_link(link_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    link = db.query(GuardianLink).filter(GuardianLink.id == link_id, GuardianLink.school_id == school_id).first()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardian link not found")
    if link.status == "active":
        link.status = "revoked"
        link.revoked_at = invite_tokens.now_utc()
        link.revoked_by_user_id = membership.user_id
        _revoke_guardian_membership_if_last_link(db, school_id, link.user_id, membership.user_id, exclude_link_id=link.id)
        write_audit(db, membership.user_id, "school.guardian_link.revoked", link, {"student_id": link.student_id}, school_id=school_id)
        db.commit()
        db.refresh(link)
    user = db.query(User).filter(User.id == link.user_id).first()
    return _guardian_link_payload(link, user)


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

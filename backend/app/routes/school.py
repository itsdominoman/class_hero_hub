from __future__ import annotations

from typing import Any, Type

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models_school import (
    AcademicYear,
    BranchCampus,
    ClassSection,
    EducationStage,
    GradeLevel,
    Membership,
    School,
    Subject,
    SubjectGroup,
)
from ..school_scope import require_school_role, write_audit

router = APIRouter(dependencies=[Depends(require_school_role("school_admin"))])


class SettingsUpdate(BaseModel):
    grade_level_label: str = Field(default="Grade", min_length=1, max_length=40)


class StructureBase(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    name_ar: str | None = Field(default=None, max_length=200)
    sort_order: int = 0
    status: str = Field(default="active", max_length=40)


class BranchCampusRequest(StructureBase):
    pass


class EducationStageRequest(StructureBase):
    pass


class AcademicYearRequest(StructureBase):
    pass


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
    class_section_id: int
    subject_id: int


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
        "status": payload.status.strip() or "active",
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
    for field in ("education_stage_id", "branch_campus_id", "academic_year_id", "grade_level_id", "class_section_id", "subject_id"):
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
    SubjectGroup: ("academic_year_id", "class_section_id", "subject_id"),
}


def _find_by_natural_key(db: Session, model: Type[Any], school_id: int, code: str, extra: dict[str, Any]):
    filters = [model.school_id == school_id, model.code == code]
    for column in _EXTRA_KEY_COLUMNS.get(model, ()):
        filters.append(getattr(model, column) == extra[column])
    return db.query(model).filter(*filters).first()


def _active_duplicate_detail(existing_status: str) -> str:
    if existing_status == "inactive":
        return "This value is already used by an inactive record. Edit or reactivate that record instead."
    return "An active record with this code already exists."


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
    return {**_payload(row), "restored": restored}


def _update_row(db: Session, row: Any, payload: StructureBase, *, extra: dict[str, Any] | None = None):
    for key, value in _clean_payload(payload).items():
        setattr(row, key, value)
    for key, value in (extra or {}).items():
        setattr(row, key, value)
    _commit_or_conflict(db)
    db.refresh(row)
    return row


def _archive_row(db: Session, row: Any):
    row.status = "archived"
    db.commit()


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


@router.post("/academic-years", status_code=status.HTTP_201_CREATED)
def create_academic_year(payload: AcademicYearRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    return _create_response(db, membership, AcademicYear, payload, entity="academic_year")


@router.put("/academic-years/{row_id}")
def update_academic_year(row_id: int, payload: AcademicYearRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    return _payload(_update_row(db, _get_owned(db, AcademicYear, _school_id(membership), row_id), payload))


@router.delete("/academic-years/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_academic_year(row_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    _archive_row(db, _get_owned(db, AcademicYear, _school_id(membership), row_id))


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
    _ensure_owned(db, AcademicYear, school_id, payload.academic_year_id, "academic_year_id", current_id=getattr(current, "academic_year_id", None))
    section = _ensure_owned(db, ClassSection, school_id, payload.class_section_id, "class_section_id", current_id=getattr(current, "class_section_id", None))
    _ensure_owned(db, Subject, school_id, payload.subject_id, "subject_id", current_id=getattr(current, "subject_id", None))
    if section.academic_year_id != payload.academic_year_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="class_section_id must belong to academic_year_id")
    return {
        "academic_year_id": payload.academic_year_id,
        "class_section_id": payload.class_section_id,
        "subject_id": payload.subject_id,
    }


@router.post("/subject-groups", status_code=status.HTTP_201_CREATED)
def create_subject_group(payload: SubjectGroupRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    return _create_response(db, membership, SubjectGroup, payload, entity="subject_group", extra=_subject_group_extra(db, school_id, payload))


@router.put("/subject-groups/{row_id}")
def update_subject_group(row_id: int, payload: SubjectGroupRequest, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    school_id = _school_id(membership)
    row = _get_owned(db, SubjectGroup, school_id, row_id)
    return _payload(_update_row(db, row, payload, extra=_subject_group_extra(db, school_id, payload, row)))


@router.delete("/subject-groups/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_subject_group(row_id: int, membership: Membership = Depends(require_school_role("school_admin")), db: Session = Depends(get_db)):
    _archive_row(db, _get_owned(db, SubjectGroup, _school_id(membership), row_id))

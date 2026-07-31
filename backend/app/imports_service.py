from __future__ import annotations

import csv
import io
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from unicodedata import name as unicode_name

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth import normalize_email
from .models_school import AcademicYear, BranchCampus, ClassSection, Enrolment, GradeLevel, Membership, Student, StudentGuardianContact, User
from .school_scope import open_interval_expression

CSV_COLUMNS = [
    "student_id",
    "first_name",
    "last_name",
    "preferred_name",
    "name_ar",
    "dob",
    "gender",
    "branch",
    "grade",
    "section",
    "student_status",
    "guardian1_name",
    "guardian1_id",
    "guardian1_email",
    "guardian1_phone",
    "guardian1_relationship",
    "guardian2_name",
    "guardian2_id",
    "guardian2_email",
    "guardian2_phone",
    "guardian2_relationship",
]

OPTIONAL_STUDENT_CSV_COLUMNS = {
    "student_status",
    "guardian1_id",
    "guardian1_phone",
    "guardian2_id",
    "guardian2_phone",
}

TEACHER_CSV_COLUMNS = ["email", "first_name", "last_name", "name_ar"]

GENDER_VALUES = {"male", "female", "other", "unspecified"}

GUARDIAN_RELATIONSHIP_VALUES = {"mother", "father", "guardian", "other"}

STUDENT_IMPORT_MODES = {"normal", "annual"}

ANNUAL_STUDENT_STATUS_VALUES = {"active", "leaver", "inactive"}

MIXED_NAME_AR_WARNING = (
    "name_ar contains both Arabic and Latin letters; review that it is the complete "
    "Arabic-script student name."
)

_ROW_ACTIONS = {
    "create",
    "update",
    "move",
    "restore",
    "reactivate",
    "leaver",
    "inactive",
    "skip",
    "conflict",
    "error",
}


class ImportUploadError(ValueError):
    """Raised for whole-file problems (encoding, headers, missing current year)."""


def normalize_student_external_ref(value: str | None) -> str | None:
    """Return the stable identity form while leaving stored display casing alone."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned.lower() if cleaned else None


def normalize_guardian_external_ref(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned.lower() if cleaned else None


def has_mixed_arabic_latin_letters(value: str | None) -> bool:
    """Return true only when both scripts contain letters.

    Spaces, digits and punctuation are deliberately ignored so normal Arabic
    name forms remain valid and mixed-script names can be reviewed rather than
    rejected or rewritten.
    """
    has_arabic = False
    has_latin = False
    for character in value or "":
        if not character.isalpha():
            continue
        character_name = unicode_name(character, "")
        has_arabic = has_arabic or "ARABIC" in character_name
        has_latin = has_latin or "LATIN" in character_name
        if has_arabic and has_latin:
            return True
    return False


def normalize_guardian_phone(value: str | None) -> tuple[str | None, str | None]:
    """Validate a usable phone value and return display + comparison forms."""
    if value is None or not value.strip():
        return None, None
    display = value.strip()
    compact = "".join(ch for ch in display if ch not in " -().")
    if compact.startswith("00"):
        compact = f"+{compact[2:]}"
    if compact.startswith("+"):
        digits = compact[1:]
        normalized = compact
    else:
        digits = compact
        normalized = compact
    if not digits.isdigit() or not 7 <= len(digits) <= 15:
        raise ValueError("must contain 7 to 15 digits and may start with + or 00")
    return display, normalized


def generate_template_csv(columns: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    return buffer.getvalue()


def decode_csv_bytes(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    try:
        return content.decode("cp1256")
    except UnicodeDecodeError:
        raise ImportUploadError("Could not read this file. Save it as UTF-8 or Windows-1256 CSV and try again.")


def _restore_exported_csv_cell(value: str | None) -> str:
    text = (value or "").strip()
    if text.startswith("'"):
        escaped = text[1:].lstrip()
        if escaped and escaped[0] in "=+-@":
            return escaped.strip()
    return text


def parse_csv_rows(
    text: str,
    columns: list[str],
    *,
    optional_columns: set[str] | None = None,
) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    # Header matching is case/whitespace-insensitive (a common Excel-resave
    # quirk), but DictReader keys rows by the *original* header spelling, so
    # row values must be looked up through this original-name map rather than
    # by the lowercase column name directly.
    original_by_lower = {(name or "").strip().lower(): name for name in (reader.fieldnames or [])}
    optional_columns = optional_columns or set()
    missing = [
        column
        for column in columns
        if column not in original_by_lower and column not in optional_columns
    ]
    if missing:
        raise ImportUploadError(f"CSV is missing required columns: {', '.join(missing)}")
    rows: list[dict[str, str]] = []
    for raw_row in reader:
        rows.append(
            {
                column: _restore_exported_csv_cell(
                    (raw_row.get(original_by_lower[column]) or "") if column in original_by_lower else ""
                )
                for column in columns
            }
        )
    return rows


@dataclass
class RowPlan:
    row_number: int
    csv: dict[str, str]
    action: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    student_id: int | None = None
    class_section_id: int | None = None
    current_enrolment_id: int | None = None
    student_status: str | None = None
    cleaned: dict[str, Any] | None = None
    guardian_contacts: list[dict[str, Any]] = field(default_factory=list)


def _validate_guardian_slot(
    row: dict[str, str], slot: int
) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    """Parse+validate one guardian slot's columns. Never raises/errors the row:

    guardian data is prep-only for a future workflow (S9), so bad or
    incomplete guardian data is surfaced as a preview warning and either
    left blank or staged as-is, never blocks student create/update.
    """
    warnings: list[str] = []
    errors: list[str] = []
    external_ref = row[f"guardian{slot}_id"] or None
    name = row[f"guardian{slot}_name"] or None
    email = row[f"guardian{slot}_email"] or None
    phone_raw = row[f"guardian{slot}_phone"] or None
    relationship_raw = (row[f"guardian{slot}_relationship"] or "").strip().lower()

    if not external_ref and not name and not email and not phone_raw and not relationship_raw:
        return None, warnings, errors

    if email:
        try:
            email = normalize_email(validate_email(email, check_deliverability=False).normalized)
        except EmailNotValidError:
            errors.append(f"guardian{slot}_email is not a valid email")
    if email and not name:
        warnings.append(f"guardian{slot}_name is missing; add a name before this guardian can be invited later")

    phone = None
    phone_normalized = None
    if phone_raw:
        try:
            phone, phone_normalized = normalize_guardian_phone(phone_raw)
        except ValueError as exc:
            errors.append(f"guardian{slot}_phone {exc}")

    relationship: str | None = None
    if relationship_raw:
        if relationship_raw not in GUARDIAN_RELATIONSHIP_VALUES:
            warnings.append(
                f"guardian{slot}_relationship must be one of {', '.join(sorted(GUARDIAN_RELATIONSHIP_VALUES))}; left blank"
            )
        else:
            relationship = relationship_raw

    warnings.append(f"Guardian {slot} will be saved as a draft contact only; no invite or message is sent.")
    provided_fields = [
        field
        for field, value in (
            ("external_ref", external_ref),
            ("name", name),
            ("email", email),
            ("phone", phone),
            ("phone_normalized", phone_normalized),
            ("relationship", relationship),
        )
        if value is not None
    ]
    return {
        "slot": slot,
        "external_ref": external_ref,
        "name": name,
        "email": email,
        "phone": phone,
        "phone_normalized": phone_normalized,
        "relationship": relationship,
        "provided_fields": provided_fields,
    }, warnings, errors


def existing_guardian_contacts_by_student(
    db: Session, school_id: int, student_ids: list[int]
) -> dict[tuple[int, int | str], StudentGuardianContact]:
    """One batched lookup of every (student, slot) draft guardian contact.

    Shared shape with open_section_enrolments_by_student: keyed for O(1)
    per-row lookup in the commit loop instead of a per-row query.
    """
    if not student_ids:
        return {}
    rows = (
        db.query(StudentGuardianContact)
        .filter(StudentGuardianContact.school_id == school_id, StudentGuardianContact.student_id.in_(student_ids))
        .all()
    )
    indexed: dict[tuple[int, int | str], StudentGuardianContact] = {}
    for row in rows:
        if row.slot is not None:
            indexed[(row.student_id, row.slot)] = row
        normalized_ref = normalize_guardian_external_ref(row.external_ref)
        if normalized_ref:
            indexed[(row.student_id, f"ref:{normalized_ref}")] = row
    return indexed


def open_section_enrolments_by_student(
    db: Session,
    school_id: int,
    student_ids: list[int],
    today: date,
    *,
    lock_rows: bool = False,
) -> dict[int, Enrolment]:
    """One batched lookup of each student's current open class-section enrolment.

    Shared by the plan (to decide create/update/move/restore/skip) and the
    commit route (to apply it), so the definition of "currently enrolled
    section" can't drift between preview and commit.
    """
    if not student_ids:
        return {}
    query = (
        db.query(Enrolment)
        .filter(
            Enrolment.school_id == school_id,
            Enrolment.student_id.in_(student_ids),
            Enrolment.class_section_id.is_not(None),
            Enrolment.kind == "member",
            *open_interval_expression(Enrolment, today),
        )
    )
    if lock_rows:
        query = query.with_for_update()
    rows = query.all()
    return {row.student_id: row for row in rows}


def class_section_enrolments_by_student(
    db: Session,
    school_id: int,
    student_ids: list[int],
    *,
    lock_rows: bool = False,
) -> dict[int, list[Enrolment]]:
    if not student_ids:
        return {}
    query = (
        db.query(Enrolment)
        .filter(
            Enrolment.school_id == school_id,
            Enrolment.student_id.in_(student_ids),
            Enrolment.class_section_id.is_not(None),
            Enrolment.kind == "member",
        )
        .order_by(Enrolment.student_id.asc(), Enrolment.valid_from.asc(), Enrolment.id.asc())
    )
    if lock_rows:
        query = query.with_for_update()
    indexed: dict[int, list[Enrolment]] = {}
    for row in query.all():
        indexed.setdefault(row.student_id, []).append(row)
    return indexed


def plan_student_import_rows(
    db: Session,
    school_id: int,
    raw_rows: list[dict[str, str]],
    *,
    today: date | None = None,
    mode: str = "normal",
    academic_year_id: int | None = None,
    effective_date: date | None = None,
    lock_rows: bool = False,
) -> list[RowPlan]:
    today = today or date.today()
    mode = (mode or "normal").strip().lower()
    if mode not in STUDENT_IMPORT_MODES:
        raise ImportUploadError("Import mode must be 'normal' or 'annual'.")

    if mode == "annual":
        if academic_year_id is None:
            raise ImportUploadError("Annual Update requires a destination academic year.")
        year = (
            db.query(AcademicYear)
            .filter(
                AcademicYear.id == academic_year_id,
                AcademicYear.school_id == school_id,
                AcademicYear.status != "archived",
            )
            .first()
        )
        if not year:
            raise ImportUploadError("The selected destination academic year is not available for this school.")
        effective_date = effective_date or year.start_date
        if effective_date is None:
            raise ImportUploadError("Annual Update requires an effective date because the selected academic year has no start date.")
        if year.start_date is not None and effective_date < year.start_date:
            raise ImportUploadError("The effective date cannot be earlier than the selected academic year's start date.")
        if year.end_date is not None and effective_date > year.end_date:
            raise ImportUploadError("The effective date cannot be later than the selected academic year's end date.")
    else:
        year = (
            db.query(AcademicYear)
            .filter(
                AcademicYear.school_id == school_id,
                AcademicYear.is_current.is_(True),
                AcademicYear.status != "archived",
            )
            .first()
        )
        effective_date = today
    if not year:
        raise ImportUploadError("No current academic year is set for this school. Set a current academic year before importing students.")

    branches = db.query(BranchCampus).filter(BranchCampus.school_id == school_id, BranchCampus.status != "archived").all()
    branch_by_code = {b.code.strip().upper(): b for b in branches}
    active_branches = [b for b in branches if b.status == "active"]

    grade_levels = db.query(GradeLevel).filter(GradeLevel.school_id == school_id, GradeLevel.status != "archived").all()
    grade_by_code = {g.code.strip().upper(): g for g in grade_levels}

    sections = (
        db.query(ClassSection)
        .filter(ClassSection.school_id == school_id, ClassSection.academic_year_id == year.id, ClassSection.status == "active")
        .all()
    )
    section_by_key = {(s.branch_campus_id, s.grade_level_id, s.code.strip().upper()): s for s in sections}

    normalized_refs = [normalize_student_external_ref(row["student_id"]) for row in raw_rows]
    ref_counts = Counter(ref for ref in normalized_refs if ref)

    non_blank_refs = {ref for ref in normalized_refs if ref}
    if non_blank_refs:
        student_query = db.query(Student).filter(
            Student.school_id == school_id,
            func.lower(func.trim(Student.external_ref)).in_(non_blank_refs),
        )
        if lock_rows:
            student_query = student_query.with_for_update()
        existing_students = student_query.all()
    else:
        existing_students = []
    students_by_ref: dict[str, list[Student]] = {}
    for student in existing_students:
        normalized = normalize_student_external_ref(student.external_ref)
        if normalized is not None:
            students_by_ref.setdefault(normalized, []).append(student)

    student_ids = [s.id for s in existing_students]
    open_section_by_student = (
        open_section_enrolments_by_student(
            db,
            school_id,
            student_ids,
            today,
            lock_rows=lock_rows,
        )
        if mode == "normal"
        else {}
    )
    class_enrolments_by_student = (
        class_section_enrolments_by_student(
            db,
            school_id,
            student_ids,
            lock_rows=lock_rows,
        )
        if mode == "annual"
        else {}
    )
    guardian_contacts_by_student = existing_guardian_contacts_by_student(db, school_id, student_ids)

    plans: list[RowPlan] = []
    for idx, row in enumerate(raw_rows, start=1):
        errors: list[str] = []
        warnings: list[str] = []

        external_ref = row["student_id"].strip() or None
        normalized_ref = normalize_student_external_ref(external_ref)
        first_name = row["first_name"]
        last_name = row["last_name"]
        preferred_name = row["preferred_name"] or None
        name_ar = row["name_ar"] or None
        if has_mixed_arabic_latin_letters(name_ar):
            warnings.append(MIXED_NAME_AR_WARNING)
        dob_raw = row["dob"]
        gender_raw = row["gender"].lower()
        branch_raw = row["branch"]
        grade_raw = row["grade"]
        section_raw = row["section"]
        student_status_raw = row.get("student_status", "").strip().lower()

        conflicts: list[str] = []
        if normalized_ref is None:
            errors.append("student_id is required")
        elif ref_counts[normalized_ref] > 1:
            conflicts.append("Duplicate normalised student_id in file")

        if not first_name:
            errors.append("first_name is required")
        if not last_name:
            errors.append("last_name is required")

        dob: date | None = None
        if dob_raw:
            try:
                dob = date.fromisoformat(dob_raw)
            except ValueError:
                errors.append("dob must be in YYYY-MM-DD format")

        gender: str | None = None
        if gender_raw:
            if gender_raw not in GENDER_VALUES:
                errors.append(f"gender must be one of {', '.join(sorted(GENDER_VALUES))}")
            else:
                gender = gender_raw

        imported_status = "active"
        if mode == "annual":
            if not student_status_raw:
                conflicts.append("student_status is required in Annual Update mode")
                imported_status = None
            elif student_status_raw not in ANNUAL_STUDENT_STATUS_VALUES:
                conflicts.append(
                    f"student_status must be one of {', '.join(sorted(ANNUAL_STUDENT_STATUS_VALUES))}"
                )
                imported_status = None
            else:
                imported_status = student_status_raw
        elif student_status_raw and student_status_raw != "active":
            errors.append("student_status values leaver/inactive require Annual Update mode")

        placement_required = mode == "normal" or imported_status == "active"
        placement_supplied = bool(branch_raw or grade_raw or section_raw)
        validate_placement = placement_required or placement_supplied
        structure_issues: list[str] = []
        branch = None
        if validate_placement:
            if branch_raw:
                branch = branch_by_code.get(branch_raw.upper())
                if branch is None:
                    structure_issues.append(f"Unknown branch '{branch_raw}'")
            elif len(active_branches) == 1:
                branch = active_branches[0]
            elif not active_branches:
                structure_issues.append("branch is required (this school has no active branch)")
            else:
                structure_issues.append("branch is required (this school has more than one branch)")

        grade = None
        if validate_placement:
            if not grade_raw:
                structure_issues.append("grade is required")
            else:
                grade = grade_by_code.get(grade_raw.upper())
                if grade is None:
                    structure_issues.append(f"Unknown grade '{grade_raw}'")

        section = None
        if validate_placement:
            if not section_raw:
                structure_issues.append("section is required")
            elif branch is not None and grade is not None:
                section = section_by_key.get((branch.id, grade.id, section_raw.upper()))
                if section is None:
                    structure_issues.append(
                        f"Unknown section '{section_raw}' for branch '{branch.code}' / grade '{grade.code}'"
                    )

        if mode == "annual":
            conflicts.extend(structure_issues)
        else:
            errors.extend(structure_issues)

        guardian_contacts: list[dict[str, Any]] = []
        for slot in (1, 2):
            contact, slot_warnings, slot_errors = _validate_guardian_slot(row, slot)
            warnings.extend(slot_warnings)
            errors.extend(slot_errors)
            if contact:
                guardian_contacts.append(contact)
        guardian_refs = [
            normalize_guardian_external_ref(contact["external_ref"])
            for contact in guardian_contacts
            if contact["external_ref"]
        ]
        if len(guardian_refs) != len(set(guardian_refs)):
            conflicts.append("Duplicate normalised guardian contact ID in row")

        if errors:
            plans.append(RowPlan(idx, row, "error", errors, warnings, guardian_contacts=guardian_contacts))
            continue

        matching_students = students_by_ref.get(normalized_ref, []) if normalized_ref else []
        if len(matching_students) > 1:
            conflicts.append("Ambiguous existing student identity")

        if conflicts:
            plans.append(RowPlan(idx, row, "conflict", conflicts, warnings, guardian_contacts=guardian_contacts))
            continue

        existing = matching_students[0] if matching_students else None
        cleaned = {
            "external_ref": external_ref,
            "first_name": first_name,
            "last_name": last_name,
            "preferred_name": preferred_name if preferred_name is not None or existing is None else existing.preferred_name,
            "name_ar": name_ar if name_ar is not None or existing is None else existing.name_ar,
            "date_of_birth": dob if dob_raw or existing is None else existing.date_of_birth,
            "gender": gender if gender_raw or existing is None else existing.gender,
        }

        if existing is None:
            plans.append(
                RowPlan(
                    idx,
                    row,
                    "create" if imported_status == "active" else imported_status,
                    errors,
                    warnings,
                    student_id=None,
                    class_section_id=section.id if section else None,
                    student_status=imported_status,
                    cleaned=cleaned,
                    guardian_contacts=guardian_contacts,
                )
            )
            continue

        changed_guardian_contacts: list[dict[str, Any]] = []
        guardian_conflicts: list[str] = []
        for contact in guardian_contacts:
            normalized_guardian_ref = normalize_guardian_external_ref(contact["external_ref"])
            contact_key: tuple[int, int | str] = (
                (existing.id, f"ref:{normalized_guardian_ref}")
                if normalized_guardian_ref
                else (existing.id, contact["slot"])
            )
            stored = guardian_contacts_by_student.get(contact_key)
            if stored is None and normalized_guardian_ref:
                stored = guardian_contacts_by_student.get((existing.id, contact["slot"]))
            contact["existing_contact_id"] = stored.id if stored is not None else None
            provided_fields = contact["provided_fields"]
            changed_fields = [
                field
                for field in provided_fields
                if stored is None or getattr(stored, field) != contact[field]
            ]
            if not changed_fields:
                continue
            if stored is not None and stored.status != "draft":
                guardian_conflicts.append(
                    f"Guardian {contact['slot']} contact is {stored.status} and cannot be overwritten by import"
                )
                continue
            contact["changed_fields"] = changed_fields
            changed_guardian_contacts.append(contact)

        if guardian_conflicts:
            plans.append(
                RowPlan(
                    idx,
                    row,
                    "conflict",
                    guardian_conflicts,
                    warnings,
                    student_id=existing.id,
                    class_section_id=section.id if section else None,
                    student_status=imported_status,
                    cleaned=cleaned,
                    guardian_contacts=[],
                )
            )
            continue

        fields_changed = any(getattr(existing, key) != value for key, value in cleaned.items())

        if mode == "annual":
            enrolments = class_enrolments_by_student.get(existing.id, [])
            active_at_effective = [
                enrolment
                for enrolment in enrolments
                if enrolment.valid_from <= effective_date
                and (enrolment.valid_to is None or enrolment.valid_to > effective_date)
            ]
            future_enrolments = [
                enrolment for enrolment in enrolments if enrolment.valid_from > effective_date
            ]
            boundary_conflicts: list[str] = []
            if len(active_at_effective) > 1:
                boundary_conflicts.append("Overlapping class enrolments exist at the effective date")
            if future_enrolments:
                boundary_conflicts.append(
                    "The effective date is earlier than an incompatible existing enrolment boundary"
                )
            current_enrolment = active_at_effective[0] if len(active_at_effective) == 1 else None
            current_section_id = current_enrolment.class_section_id if current_enrolment else None
            target_section_id = section.id if section else None

            if (
                imported_status == "active"
                and current_enrolment is not None
                and current_section_id != target_section_id
                and current_enrolment.valid_from == effective_date
            ):
                boundary_conflicts.append(
                    "The existing class enrolment starts on the effective date and cannot be replaced at that boundary"
                )
            if (
                existing.status in {"inactive", "leaver", "archived"}
                and imported_status != "active"
                and target_section_id is not None
                and current_section_id != target_section_id
            ):
                boundary_conflicts.append(
                    "An inactive or leaver student cannot move without explicit active reactivation"
                )

            if boundary_conflicts:
                plans.append(
                    RowPlan(
                        idx,
                        row,
                        "conflict",
                        boundary_conflicts,
                        warnings,
                        student_id=existing.id,
                        class_section_id=target_section_id,
                        current_enrolment_id=current_enrolment.id if current_enrolment else None,
                        student_status=imported_status,
                        cleaned=cleaned,
                        guardian_contacts=[],
                    )
                )
                continue

            if imported_status == "active":
                if existing.status != "active":
                    action = "reactivate"
                elif current_section_id != target_section_id:
                    action = "move"
                elif fields_changed or changed_guardian_contacts:
                    action = "update"
                else:
                    action = "skip"
            elif (
                existing.status == imported_status
                and current_enrolment is None
                and not fields_changed
                and not changed_guardian_contacts
            ):
                action = "skip"
            else:
                action = imported_status

            plans.append(
                RowPlan(
                    idx,
                    row,
                    action,
                    errors,
                    warnings,
                    student_id=existing.id,
                    class_section_id=target_section_id,
                    current_enrolment_id=current_enrolment.id if current_enrolment else None,
                    student_status=imported_status,
                    cleaned=cleaned,
                    guardian_contacts=changed_guardian_contacts,
                )
            )
            continue

        current_enrolment = open_section_by_student.get(existing.id)
        current_section_id = current_enrolment.class_section_id if current_enrolment else None
        if existing.status == "archived":
            action = "restore"
        elif current_section_id != section.id:
            action = "move"
        elif fields_changed or changed_guardian_contacts:
            action = "update"
        else:
            action = "skip"

        plans.append(
            RowPlan(
                idx, row, action, errors, warnings,
                student_id=existing.id,
                class_section_id=section.id,
                current_enrolment_id=current_enrolment.id if current_enrolment else None,
                student_status="active",
                cleaned=cleaned,
                guardian_contacts=changed_guardian_contacts,
            )
        )

    return plans


def summarize_plans(plans: list[RowPlan]) -> dict[str, int]:
    counts = {action: 0 for action in _ROW_ACTIONS}
    for plan in plans:
        counts[plan.action] += 1
    counts["total"] = len(plans)
    return counts


@dataclass
class TeacherRowPlan:
    row_number: int
    csv: dict[str, str]
    action: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    user_id: int | None = None
    membership_id: int | None = None
    cleaned: dict[str, Any] | None = None


def plan_teacher_import_rows(db: Session, school_id: int, raw_rows: list[dict[str, str]]) -> list[TeacherRowPlan]:
    """Batched planner for staged teacher CSV rows.

    Identity is email only (global, unlike Student.external_ref). Commit
    creates/reuses a User by email and ensures an active teacher Membership
    for this school -- never sends an invite email, never touches
    StaffInvite/MagicLoginToken. A Membership row already exists uniquely
    per (school, user, role), so a previously revoked teacher is left alone
    (skip + warning) rather than silently reactivated by re-import.
    """
    emails = [normalize_email(row["email"]) for row in raw_rows if row["email"] and "@" in row["email"]]
    email_counts = Counter(emails)

    # Compare case-insensitively: normalize_email lowercases the CSV side,
    # but User.email is a plain unique-index String column, not guaranteed
    # lowercase at rest for every historical row -- an exact-match lookup
    # here would misclassify a mixed-case existing user as "create" and
    # violate the no-duplicate-user idempotency guarantee.
    existing_users = db.query(User).filter(func.lower(User.email).in_(emails)).all() if emails else []
    user_by_email = {u.email.lower(): u for u in existing_users}

    user_ids = [u.id for u in existing_users]
    existing_memberships = (
        db.query(Membership)
        .filter(Membership.school_id == school_id, Membership.role == "teacher", Membership.user_id.in_(user_ids))
        .all()
        if user_ids
        else []
    )
    membership_by_user_id = {m.user_id: m for m in existing_memberships}

    plans: list[TeacherRowPlan] = []
    for idx, row in enumerate(raw_rows, start=1):
        errors: list[str] = []
        warnings: list[str] = []

        email_raw = row["email"]
        first_name = row["first_name"]
        last_name = row["last_name"]
        name_ar = row["name_ar"] or None

        email: str | None = None
        if not email_raw:
            errors.append("email is required")
        elif "@" not in email_raw:
            errors.append("email is not a valid email address")
        else:
            email = normalize_email(email_raw)
            if email_counts[email] > 1:
                errors.append("Duplicate email in file")

        if not first_name:
            errors.append("first_name is required")
        if not last_name:
            errors.append("last_name is required")

        if errors:
            plans.append(TeacherRowPlan(idx, row, "error", errors, warnings))
            continue

        cleaned = {"first_name": first_name, "last_name": last_name, "name_ar": name_ar}
        existing_user = user_by_email.get(email)
        existing_membership = membership_by_user_id.get(existing_user.id) if existing_user else None

        if existing_membership is not None and existing_membership.status == "active" and existing_membership.revoked_at is None:
            full_name = f"{first_name} {last_name}".strip()
            fills_blank_name = bool(full_name) and not existing_user.name
            fills_blank_name_ar = bool(name_ar) and not existing_user.name_ar
            action = "update" if (fills_blank_name or fills_blank_name_ar) else "skip"
            plans.append(
                TeacherRowPlan(
                    idx, row, action, errors, warnings,
                    user_id=existing_user.id, membership_id=existing_membership.id, cleaned=cleaned,
                )
            )
            continue

        if existing_membership is not None:
            warnings.append("This person was previously removed as a teacher at this school. Re-activate them from the Teachers tab, not via import.")
            plans.append(
                TeacherRowPlan(
                    idx, row, "skip", errors, warnings,
                    user_id=existing_user.id, membership_id=existing_membership.id, cleaned=cleaned,
                )
            )
            continue

        plans.append(
            TeacherRowPlan(
                idx, row, "create", errors, warnings,
                user_id=existing_user.id if existing_user else None, cleaned=cleaned,
            )
        )

    return plans

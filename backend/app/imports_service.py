from __future__ import annotations

import csv
import io
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Any

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
    "guardian1_name",
    "guardian1_email",
    "guardian1_relationship",
    "guardian2_name",
    "guardian2_email",
    "guardian2_relationship",
]

TEACHER_CSV_COLUMNS = ["email", "first_name", "last_name", "name_ar"]

GENDER_VALUES = {"male", "female", "other", "unspecified"}

GUARDIAN_RELATIONSHIP_VALUES = {"mother", "father", "guardian", "other"}

_ROW_ACTIONS = {"create", "update", "move", "restore", "skip", "error"}


class ImportUploadError(ValueError):
    """Raised for whole-file problems (encoding, headers, missing current year)."""


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


def parse_csv_rows(text: str, columns: list[str]) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    # Header matching is case/whitespace-insensitive (a common Excel-resave
    # quirk), but DictReader keys rows by the *original* header spelling, so
    # row values must be looked up through this original-name map rather than
    # by the lowercase column name directly.
    original_by_lower = {(name or "").strip().lower(): name for name in (reader.fieldnames or [])}
    missing = [column for column in columns if column not in original_by_lower]
    if missing:
        raise ImportUploadError(f"CSV is missing required columns: {', '.join(missing)}")
    rows: list[dict[str, str]] = []
    for raw_row in reader:
        rows.append({column: (raw_row.get(original_by_lower[column]) or "").strip() for column in columns})
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
    cleaned: dict[str, Any] | None = None
    guardian_contacts: list[dict[str, Any]] = field(default_factory=list)


def _validate_guardian_slot(row: dict[str, str], slot: int) -> tuple[dict[str, Any] | None, list[str]]:
    """Parse+validate one guardian slot's columns. Never raises/errors the row:

    guardian data is prep-only for a future workflow (S9), so bad or
    incomplete guardian data is surfaced as a preview warning and either
    left blank or staged as-is, never blocks student create/update.
    """
    warnings: list[str] = []
    name = row[f"guardian{slot}_name"] or None
    email = row[f"guardian{slot}_email"] or None
    relationship_raw = (row[f"guardian{slot}_relationship"] or "").strip().lower()

    if not name and not email and not relationship_raw:
        return None, warnings

    if email and "@" not in email:
        warnings.append(f"guardian{slot}_email does not look like a valid email")
    if email and not name:
        warnings.append(f"guardian{slot}_name is missing; add a name before this guardian can be invited later")

    relationship: str | None = None
    if relationship_raw:
        if relationship_raw not in GUARDIAN_RELATIONSHIP_VALUES:
            warnings.append(
                f"guardian{slot}_relationship must be one of {', '.join(sorted(GUARDIAN_RELATIONSHIP_VALUES))}; left blank"
            )
        else:
            relationship = relationship_raw

    warnings.append(f"Guardian {slot} will be saved as a draft contact only; no invite or message is sent.")
    return {"slot": slot, "name": name, "email": email, "relationship": relationship}, warnings


def existing_guardian_contacts_by_student(
    db: Session, school_id: int, student_ids: list[int]
) -> dict[tuple[int, int], StudentGuardianContact]:
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
    return {(row.student_id, row.slot): row for row in rows}


def open_section_enrolments_by_student(db: Session, school_id: int, student_ids: list[int], today: date) -> dict[int, Enrolment]:
    """One batched lookup of each student's current open class-section enrolment.

    Shared by the plan (to decide create/update/move/restore/skip) and the
    commit route (to apply it), so the definition of "currently enrolled
    section" can't drift between preview and commit.
    """
    if not student_ids:
        return {}
    rows = (
        db.query(Enrolment)
        .filter(
            Enrolment.school_id == school_id,
            Enrolment.student_id.in_(student_ids),
            Enrolment.class_section_id.is_not(None),
            Enrolment.kind == "member",
            *open_interval_expression(Enrolment, today),
        )
        .all()
    )
    return {row.student_id: row for row in rows}


def plan_student_import_rows(db: Session, school_id: int, raw_rows: list[dict[str, str]], *, today: date | None = None) -> list[RowPlan]:
    today = today or date.today()

    year = (
        db.query(AcademicYear)
        .filter(AcademicYear.school_id == school_id, AcademicYear.is_current.is_(True), AcademicYear.status != "archived")
        .first()
    )
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

    external_refs = [row["student_id"] for row in raw_rows]
    ref_counts = Counter(ref for ref in external_refs if ref)

    non_blank_refs = {ref for ref in external_refs if ref}
    existing_students = (
        db.query(Student).filter(Student.school_id == school_id, Student.external_ref.in_(non_blank_refs)).all()
        if non_blank_refs
        else []
    )
    student_by_ref = {s.external_ref: s for s in existing_students}

    student_ids = [s.id for s in existing_students]
    open_section_by_student = open_section_enrolments_by_student(db, school_id, student_ids, today)

    plans: list[RowPlan] = []
    for idx, row in enumerate(raw_rows, start=1):
        errors: list[str] = []
        warnings: list[str] = []

        external_ref = row["student_id"] or None
        first_name = row["first_name"]
        last_name = row["last_name"]
        preferred_name = row["preferred_name"] or None
        name_ar = row["name_ar"] or None
        dob_raw = row["dob"]
        gender_raw = row["gender"].lower()
        branch_raw = row["branch"]
        grade_raw = row["grade"]
        section_raw = row["section"]

        if external_ref and ref_counts[external_ref] > 1:
            errors.append("Duplicate student_id in file")

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

        branch = None
        if branch_raw:
            branch = branch_by_code.get(branch_raw.upper())
            if branch is None:
                errors.append(f"Unknown branch '{branch_raw}'")
        elif len(active_branches) == 1:
            branch = active_branches[0]
        elif not active_branches:
            errors.append("branch is required (this school has no active branch)")
        else:
            errors.append("branch is required (this school has more than one branch)")

        grade = None
        if not grade_raw:
            errors.append("grade is required")
        else:
            grade = grade_by_code.get(grade_raw.upper())
            if grade is None:
                errors.append(f"Unknown grade '{grade_raw}'")

        section = None
        if not section_raw:
            errors.append("section is required")
        elif branch is not None and grade is not None:
            section = section_by_key.get((branch.id, grade.id, section_raw.upper()))
            if section is None:
                errors.append(f"Unknown section '{section_raw}' for branch '{branch.code}' / grade '{grade.code}'")

        guardian_contacts: list[dict[str, Any]] = []
        for slot in (1, 2):
            contact, slot_warnings = _validate_guardian_slot(row, slot)
            warnings.extend(slot_warnings)
            if contact:
                guardian_contacts.append(contact)

        if errors:
            plans.append(RowPlan(idx, row, "error", errors, warnings, guardian_contacts=guardian_contacts))
            continue

        cleaned = {
            "external_ref": external_ref,
            "first_name": first_name,
            "last_name": last_name,
            "preferred_name": preferred_name,
            "name_ar": name_ar,
            "date_of_birth": dob,
            "gender": gender,
        }

        existing = student_by_ref.get(external_ref) if external_ref else None
        if existing is None:
            plans.append(
                RowPlan(
                    idx, row, "create", errors, warnings,
                    student_id=None, class_section_id=section.id, cleaned=cleaned,
                    guardian_contacts=guardian_contacts,
                )
            )
            continue

        current_enrolment = open_section_by_student.get(existing.id)
        current_section_id = current_enrolment.class_section_id if current_enrolment else None
        fields_changed = any(getattr(existing, key) != value for key, value in cleaned.items())

        if existing.status == "archived":
            action = "restore"
        elif current_section_id != section.id:
            action = "move"
        elif fields_changed:
            action = "update"
        else:
            action = "skip"

        plans.append(
            RowPlan(
                idx, row, action, errors, warnings,
                student_id=existing.id, class_section_id=section.id, cleaned=cleaned,
                guardian_contacts=guardian_contacts,
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

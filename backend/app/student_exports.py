from __future__ import annotations

import csv
import io
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Iterator, Sequence

from sqlalchemy import and_, case, desc
from sqlalchemy.orm import Query, Session

from .imports_service import CSV_COLUMNS
from .models_school import (
    AcademicYear,
    BranchCampus,
    ClassSection,
    Enrolment,
    GradeLevel,
    ImportRow,
    Student,
    StudentGuardianContact,
)
from .school_scope import open_interval_expression


IMPORT_REPORT_TYPES = {"all", "conflicts", "errors", "committed"}
IMPORT_CHANGE_ACTIONS = {
    "create",
    "update",
    "move",
    "restore",
    "reactivate",
    "leaver",
    "inactive",
}
EXPORT_ROW_LIMIT = 100_000
CSV_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True)
class AnnualGuardianContact:
    name: str | None
    external_ref: str | None
    email: str | None
    phone: str | None
    relationship: str | None


STUDENT_ROSTER_COLUMNS = [
    "student_id",
    "first_name",
    "last_name",
    "preferred_name",
    "name_ar",
    "dob",
    "gender",
    "branch",
    "academic_year",
    "grade",
    "section",
    "student_status",
]

GUARDIAN_CONTACT_COLUMNS = [
    "student_id",
    "student_first_name",
    "student_last_name",
    "student_status",
    "guardian_contact_id",
    "guardian_name",
    "relationship",
    "email",
    "phone",
    "is_primary",
    "is_emergency",
    "contact_active",
    "contact_status",
    "source",
]

CLASS_ENROLMENT_COLUMNS = [
    "student_id",
    "student_first_name",
    "student_last_name",
    "student_status",
    "branch",
    "academic_year",
    "grade",
    "section",
    "valid_from",
    "valid_to",
]

IMPORT_REPORT_COLUMNS = [
    "row_number",
    "outcome",
    "reason",
    "affected_student_id",
    *CSV_COLUMNS,
]


def csv_safe_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, (date,)):
        text = value.isoformat()
    else:
        text = str(value)
    stripped = text.lstrip()
    if stripped and (stripped[0] in "=+-@" or text[0] in "\t\r\n"):
        return f"'{text}"
    return text


def stream_utf8_csv(columns: Sequence[str], rows: Iterable[Sequence[Any]]) -> Iterator[str]:
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(columns)
    for values in rows:
        writer.writerow([csv_safe_cell(value) for value in values])
        if buffer.tell() >= CSV_CHUNK_BYTES:
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)
    if buffer.tell():
        yield buffer.getvalue()


def import_row_reason(row: ImportRow) -> str:
    messages = list(row.errors or [])
    if not messages:
        messages = list(row.warnings or [])
    return "; ".join(str(message) for message in messages)


def import_report_query(
    db: Session,
    import_id: int,
    report_type: str,
) -> Query:
    query = (
        db.query(ImportRow)
        .filter(ImportRow.import_id == import_id)
        .order_by(ImportRow.row_number.asc(), ImportRow.id.asc())
    )
    if report_type == "conflicts":
        query = query.filter(ImportRow.action == "conflict")
    elif report_type == "errors":
        query = query.filter(ImportRow.action == "error")
    elif report_type == "committed":
        query = query.filter(
            ImportRow.action.in_(IMPORT_CHANGE_ACTIONS),
            ImportRow.applied_entity_id.is_not(None),
        )
    return query


def import_report_rows(query: Query) -> Iterator[list[Any]]:
    for row in query.yield_per(500):
        raw = row.raw or {}
        yield [
            row.row_number,
            row.action,
            import_row_reason(row),
            row.applied_entity_id,
            *(raw.get(column) for column in CSV_COLUMNS),
        ]


def current_student_placement_query(
    db: Session,
    school_id: int,
    as_of: date,
    *,
    active_students_only: bool,
) -> Query:
    query = (
        db.query(
            Student,
            Enrolment,
            ClassSection,
            BranchCampus,
            GradeLevel,
            AcademicYear,
        )
        .outerjoin(
            Enrolment,
            and_(
                Enrolment.school_id == school_id,
                Enrolment.student_id == Student.id,
                Enrolment.class_section_id.is_not(None),
                Enrolment.kind == "member",
                *open_interval_expression(Enrolment, as_of),
            ),
        )
        .outerjoin(
            ClassSection,
            and_(
                ClassSection.id == Enrolment.class_section_id,
                ClassSection.school_id == school_id,
            ),
        )
        .outerjoin(
            BranchCampus,
            and_(
                BranchCampus.id == ClassSection.branch_campus_id,
                BranchCampus.school_id == school_id,
            ),
        )
        .outerjoin(
            GradeLevel,
            and_(
                GradeLevel.id == ClassSection.grade_level_id,
                GradeLevel.school_id == school_id,
            ),
        )
        .outerjoin(
            AcademicYear,
            and_(
                AcademicYear.id == ClassSection.academic_year_id,
                AcademicYear.school_id == school_id,
            ),
        )
        .filter(
            Student.school_id == school_id,
            Student.status != "archived",
        )
        .order_by(Student.id.asc(), Enrolment.id.asc())
    )
    if active_students_only:
        query = query.filter(Student.status == "active")
    return query


def student_roster_rows(query: Query) -> Iterator[list[Any]]:
    for student, _enrolment, section, branch, grade, year in query.yield_per(500):
        yield [
            student.external_ref,
            student.first_name,
            student.last_name,
            student.preferred_name,
            student.name_ar,
            student.date_of_birth,
            student.gender,
            branch.code if branch else None,
            year.code if year else None,
            grade.code if grade else None,
            section.code if section else None,
            student.status,
        ]


def current_class_enrolment_rows(query: Query) -> Iterator[list[Any]]:
    for student, enrolment, section, branch, grade, year in query.yield_per(500):
        if enrolment is None:
            continue
        yield [
            student.external_ref,
            student.first_name,
            student.last_name,
            student.status,
            branch.code if branch else None,
            year.code if year else None,
            grade.code if grade else None,
            section.code if section else None,
            enrolment.valid_from,
            enrolment.valid_to,
        ]


def guardian_contact_query(db: Session, school_id: int) -> Query:
    return (
        db.query(StudentGuardianContact, Student)
        .join(
            Student,
            and_(
                Student.id == StudentGuardianContact.student_id,
                Student.school_id == school_id,
            ),
        )
        .filter(
            StudentGuardianContact.school_id == school_id,
            Student.status != "archived",
        )
        .order_by(Student.id.asc(), StudentGuardianContact.id.asc())
    )


def guardian_contact_rows(query: Query) -> Iterator[list[Any]]:
    for contact, student in query.yield_per(500):
        yield [
            student.external_ref,
            student.first_name,
            student.last_name,
            student.status,
            contact.external_ref,
            contact.name,
            contact.relationship,
            contact.email,
            contact.phone,
            contact.is_primary,
            contact.is_emergency,
            contact.is_active,
            contact.status,
            contact.source,
        ]


def guardian_contacts_for_annual_export(
    db: Session,
    school_id: int,
) -> dict[int, list[AnnualGuardianContact]]:
    contacts = (
        db.query(StudentGuardianContact)
        .filter(StudentGuardianContact.school_id == school_id)
        .order_by(
            StudentGuardianContact.student_id.asc(),
            desc(StudentGuardianContact.is_active),
            desc(StudentGuardianContact.is_primary),
            case((StudentGuardianContact.slot.is_(None), 1), else_=0).asc(),
            StudentGuardianContact.slot.asc(),
            StudentGuardianContact.id.asc(),
        )
        .limit(EXPORT_ROW_LIMIT + 1)
        .all()
    )
    if len(contacts) > EXPORT_ROW_LIMIT:
        raise ValueError("Guardian contact export exceeds the supported row limit")
    grouped: dict[int, list[AnnualGuardianContact]] = defaultdict(list)
    for contact in contacts:
        if len(grouped[contact.student_id]) < 2:
            grouped[contact.student_id].append(
                AnnualGuardianContact(
                    name=contact.name,
                    external_ref=contact.external_ref,
                    email=contact.email,
                    phone=contact.phone,
                    relationship=contact.relationship,
                )
            )
    return grouped


def annual_update_rows(
    placement_query: Query,
    contacts_by_student: dict[int, list[AnnualGuardianContact]],
) -> Iterator[list[Any]]:
    for student, _enrolment, section, branch, grade, _year in placement_query.yield_per(500):
        contacts = contacts_by_student.get(student.id, [])
        contact1 = contacts[0] if contacts else None
        contact2 = contacts[1] if len(contacts) > 1 else None
        yield [
            student.external_ref,
            student.first_name,
            student.last_name,
            student.preferred_name,
            student.name_ar,
            student.date_of_birth,
            student.gender,
            branch.code if branch else None,
            grade.code if grade else None,
            section.code if section else None,
            student.status,
            contact1.name if contact1 else None,
            contact1.external_ref if contact1 else None,
            contact1.email if contact1 else None,
            contact1.phone if contact1 else None,
            contact1.relationship if contact1 else None,
            contact2.name if contact2 else None,
            contact2.external_ref if contact2 else None,
            contact2.email if contact2 else None,
            contact2.phone if contact2 else None,
            contact2.relationship if contact2 else None,
        ]

"""Backfill believable teacher assignment coverage for the UIS demo.

Dry-run by default; pass --apply to commit. Idempotent: safe to re-run.

Scope:
  - Uses existing active teacher memberships and demo teacher CSV metadata.
  - Creates missing homeroom/subject StaffAssignment rows only.
  - Does not create students, change enrolments, or close/delete history.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
APP_IMPORT_ROOT = BACKEND if (BACKEND / "app").exists() else ROOT
if str(APP_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_IMPORT_ROOT))

from app.database import SessionLocal
from app.models_school import (
    ClassSection,
    EducationStage,
    GradeLevel,
    Membership,
    School,
    StaffAssignment,
    Subject,
    SubjectGroup,
    User,
)
from app.school_scope import open_interval_expression


SCHOOL_SLUG = "united-international-school"
TARGET_BRANCH_CODE = "ALK"
TEACHERS_CSV = ROOT / "tmp" / "imports" / "demo_teachers_80.csv"
NAMED_DEMO_TEACHER_EMAILS = {"dom@myeduzone.org"}
NAMED_DEMO_TEACHER_TARGETS = [
    ("G6", "A", "ENG"),
    ("G6", "A", "MAT"),
    ("G6", "A", "SCI"),
]

TEACHER_ROLE_MAP = {
    "teacher": "teacher",
    "subject_lead": "teacher",
    "head_of_year": "teacher",
    "teaching_assistant": "teacher",
}

SUBJECT_ALIASES = {
    "ARB": "AR",
    "AR": "AR",
    "ENG": "ENG",
    "MAT": "MAT",
    "SCI": "SCI",
    "BIO": "SCI",
    "PHY": "SCI",
    "SOC": "SOC",
    "GP": "SOC",
    "ICT": "ICT",
    "PE": "PE",
    "ART": "ART",
    "TAJ": "TAJ",
    "IC": "TAJ",
}

DEPARTMENT_SUBJECTS = {
    "Arabic": {"AR"},
    "Arabic and Islamic": {"AR", "TAJ"},
    "Arts": {"ART"},
    "Early Years": {"ENG", "AR", "MAT", "SCI", "SOC"},
    "English": {"ENG"},
    "Humanities": {"SOC"},
    "ICT": {"ICT"},
    "Mathematics": {"MAT"},
    "Physical Education": {"PE"},
    "Science": {"SCI"},
}

PRIMARY_HOMEROOM_SUBJECTS = {"ENG", "MAT", "SCI", "SOC"}
EARLY_YEARS_HOMEROOM_SUBJECTS = {"ENG", "MAT", "SCI", "SOC"}
SPECIALIST_SUBJECTS = {"AR", "TAJ", "ICT", "PE", "ART"}


@dataclass(frozen=True)
class TeacherProfile:
    membership_id: int
    user_id: int
    email: str
    name: str
    csv_role: str
    department: str
    subjects: frozenset[str]
    homeroom_code: str


@dataclass(frozen=True)
class GroupContext:
    group: SubjectGroup
    subject: Subject
    section: ClassSection | None
    grade: GradeLevel | None
    stage: EducationStage | None


@dataclass
class Coverage:
    active_teachers: int
    active_default_groups: int
    active_sections: int
    groups_without_teacher: int
    teachers_without_assignments: int
    homeroom_gaps: int
    gap_by_subject_stage: Counter[tuple[str, str, str]]
    groups_by_subject_grade_section: Counter[tuple[str, str, str, str]]
    homeroom_gap_names: list[str]
    unassigned_teacher_names: list[str]


@dataclass
class PlanResult:
    teacher_memberships_created: int = 0
    homeroom_created: int = 0
    subject_created: int = 0
    named_demo_subject_created: int = 0
    skipped_groups: list[str] | None = None
    skipped_teachers: list[str] | None = None
    projected_groups_without_teacher: int = 0
    projected_teachers_without_assignments: int = 0
    projected_homeroom_gaps: int = 0


def read_csv_profiles() -> dict[str, dict[str, str]]:
    with TEACHERS_CSV.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {
        row["teacher_email"].strip().lower(): row
        for row in rows
        if row["branch_code"].strip() == TARGET_BRANCH_CODE and row["role"].strip() in TEACHER_ROLE_MAP
    }


def clean_code(value: str | None) -> str:
    return (value or "").strip().upper()


def compact_code(value: str | None) -> str:
    return "".join(ch for ch in clean_code(value) if ch.isalnum())


def section_key(grade_code: str | None, section_code: str | None) -> str:
    return f"{clean_code(grade_code)}{clean_code(section_code)}"


def normalize_subjects(*codes: str | None) -> set[str]:
    subjects: set[str] = set()
    for code in codes:
        normalized = SUBJECT_ALIASES.get(clean_code(code))
        if normalized:
            subjects.add(normalized)
    return subjects


def csv_profile_for_membership(membership: Membership, user: User, csv_rows: dict[str, dict[str, str]]) -> TeacherProfile:
    row = csv_rows.get((user.email or "").lower(), {})
    department = row.get("department", "").strip()
    subjects = normalize_subjects(row.get("primary_subject_code"), row.get("secondary_subject_code"))
    subjects.update(DEPARTMENT_SUBJECTS.get(department, set()))
    return TeacherProfile(
        membership_id=membership.id,
        user_id=user.id,
        email=user.email,
        name=user.name or user.email,
        csv_role=row.get("role", "teacher").strip() or "teacher",
        department=department,
        subjects=frozenset(subjects),
        homeroom_code=clean_code(row.get("homeroom_class_section_code")),
    )


def most_common_existing_valid_from(db, school_id: int) -> date:
    values = [row[0] for row in db.query(StaffAssignment.valid_from).filter(StaffAssignment.school_id == school_id).all() if row[0]]
    if not values:
        return date.today()
    return Counter(values).most_common(1)[0][0]


def load_world(db):
    school = db.query(School).filter(School.slug == SCHOOL_SLUG).one()
    csv_rows = read_csv_profiles()
    teachers = [
        csv_profile_for_membership(membership, user, csv_rows)
        for membership, user in (
            db.query(Membership, User)
            .join(User, User.id == Membership.user_id)
            .filter(Membership.school_id == school.id, Membership.role == "teacher", Membership.status == "active", User.status == "active")
            .order_by(User.name, User.email)
            .all()
        )
    ]
    groups = [
        GroupContext(group, subject, section, grade, stage)
        for group, subject, section, grade, stage in (
            db.query(SubjectGroup, Subject, ClassSection, GradeLevel, EducationStage)
            .join(Subject, Subject.id == SubjectGroup.subject_id)
            .outerjoin(ClassSection, ClassSection.id == SubjectGroup.class_section_id)
            .outerjoin(GradeLevel, GradeLevel.id == ClassSection.grade_level_id)
            .outerjoin(EducationStage, EducationStage.id == GradeLevel.education_stage_id)
            .filter(
                SubjectGroup.school_id == school.id,
                SubjectGroup.status == "active",
                SubjectGroup.enrolment_policy == "default_for_section",
                ClassSection.status == "active",
            )
            .order_by(GradeLevel.sort_order, ClassSection.sort_order, Subject.sort_order, Subject.code)
            .all()
        )
    ]
    sections = (
        db.query(ClassSection, GradeLevel, EducationStage)
        .join(GradeLevel, GradeLevel.id == ClassSection.grade_level_id)
        .outerjoin(EducationStage, EducationStage.id == GradeLevel.education_stage_id)
        .filter(ClassSection.school_id == school.id, ClassSection.status == "active")
        .order_by(GradeLevel.sort_order, ClassSection.sort_order)
        .all()
    )
    assignments = (
        db.query(StaffAssignment)
        .filter(StaffAssignment.school_id == school.id, *open_interval_expression(StaffAssignment))
        .all()
    )
    return school, teachers, groups, sections, assignments


def ensure_named_demo_teacher_profiles(db, school: School, *, apply: bool) -> tuple[list[TeacherProfile], int, list[str]]:
    profiles: list[TeacherProfile] = []
    created = 0
    exceptions: list[str] = []
    for email in sorted(NAMED_DEMO_TEACHER_EMAILS):
        user = db.query(User).filter(User.email == email, User.status == "active").first()
        if user is None:
            exceptions.append(f"{email}: existing active user not found")
            continue

        membership = (
            db.query(Membership)
            .filter(
                Membership.school_id == school.id,
                Membership.user_id == user.id,
                Membership.role == "teacher",
                Membership.status == "active",
                Membership.revoked_at.is_(None),
            )
            .first()
        )
        if membership is None:
            inactive_teacher_membership = (
                db.query(Membership)
                .filter(Membership.school_id == school.id, Membership.user_id == user.id, Membership.role == "teacher")
                .first()
            )
            if inactive_teacher_membership is not None:
                exceptions.append(f"{email}: inactive teacher membership exists; not reactivating history")
                continue

            existing_membership = (
                db.query(Membership)
                .filter(Membership.school_id == school.id, Membership.user_id == user.id, Membership.status == "active")
                .first()
            )
            created += 1
            if apply:
                membership = Membership(
                    school_id=school.id,
                    branch_campus_id=existing_membership.branch_campus_id if existing_membership else None,
                    user_id=user.id,
                    role="teacher",
                    status="active",
                )
                db.add(membership)
                db.flush()
            else:
                membership = Membership(
                    id=-1000 - created,
                    school_id=school.id,
                    branch_campus_id=existing_membership.branch_campus_id if existing_membership else None,
                    user_id=user.id,
                    role="teacher",
                    status="active",
                )

        profiles.append(
            TeacherProfile(
                membership_id=membership.id,
                user_id=user.id,
                email=user.email,
                name=user.name or user.email,
                csv_role="teacher",
                department="Demo",
                subjects=frozenset({"ENG", "MAT", "SCI"}),
                homeroom_code="",
            )
        )
    return profiles, created, exceptions


def assignment_sets(assignments: list[StaffAssignment]):
    teacher_ids = {row.membership_id for row in assignments}
    group_ids = {row.subject_group_id for row in assignments if row.subject_group_id is not None}
    section_ids = {row.class_section_id for row in assignments if row.role == "homeroom" and row.class_section_id is not None}
    exact = {
        (row.membership_id, row.role, row.class_section_id, row.subject_group_id)
        for row in assignments
    }
    return teacher_ids, group_ids, section_ids, exact


def coverage_snapshot(db) -> Coverage:
    school, teachers, groups, sections, assignments = load_world(db)
    teacher_ids, group_ids, section_ids, _exact = assignment_sets(assignments)
    unassigned_groups = [ctx for ctx in groups if ctx.group.id not in group_ids]
    unassigned_teachers = [teacher for teacher in teachers if teacher.membership_id not in teacher_ids]
    homeroom_gaps = [(section, grade, stage) for section, grade, stage in sections if section.id not in section_ids]

    return Coverage(
        active_teachers=len(teachers),
        active_default_groups=len(groups),
        active_sections=len(sections),
        groups_without_teacher=len(unassigned_groups),
        teachers_without_assignments=len(unassigned_teachers),
        homeroom_gaps=len(homeroom_gaps),
        gap_by_subject_stage=Counter(
            (
                ctx.subject.code,
                ctx.stage.code if ctx.stage else "(no stage)",
                ctx.grade.code if ctx.grade else "(no grade)",
            )
            for ctx in unassigned_groups
        ),
        groups_by_subject_grade_section=Counter(
            (
                ctx.subject.code,
                ctx.stage.code if ctx.stage else "(no stage)",
                ctx.grade.code if ctx.grade else "(no grade)",
                ctx.section.code if ctx.section else "(no section)",
            )
            for ctx in groups
        ),
        homeroom_gap_names=[f"{grade.code}{section.code} {section.name}" for section, grade, _stage in homeroom_gaps],
        unassigned_teacher_names=[f"{teacher.name} <{teacher.email}>" for teacher in unassigned_teachers],
    )


def print_coverage(label: str, coverage: Coverage) -> None:
    print(f"\n--- {label} ---")
    print(f"active teachers: {coverage.active_teachers}")
    print(f"active sections: {coverage.active_sections}")
    print(f"active default/core subject groups: {coverage.active_default_groups}")
    print(f"subject groups with no active teacher assignment: {coverage.groups_without_teacher}")
    print(f"teachers with no active assignments: {coverage.teachers_without_assignments}")
    print(f"sections with no homeroom teacher: {coverage.homeroom_gaps}")
    print("active subject groups by subject/stage/grade/section:")
    for (subject, stage, grade, section), count in sorted(coverage.groups_by_subject_grade_section.items()):
        print(f"  {subject}/{stage}/{grade}/{section}: {count}")
    print("obvious gaps by subject/stage/grade:")
    if coverage.gap_by_subject_stage:
        for (subject, stage, grade), count in sorted(coverage.gap_by_subject_stage.items()):
            print(f"  {subject}/{stage}/{grade}: {count}")
    else:
        print("  none")
    if coverage.homeroom_gap_names:
        print("homeroom exceptions:")
        for name in coverage.homeroom_gap_names:
            print(f"  {name}")
    if coverage.unassigned_teacher_names:
        print("teachers without assignments:")
        for name in coverage.unassigned_teacher_names:
            print(f"  {name}")


def grade_number(grade_code: str | None) -> int | None:
    code = clean_code(grade_code)
    if code.startswith("KG"):
        return 0
    if code.startswith("G") and code[1:].isdigit():
        return int(code[1:])
    return None


def is_primary_or_early(grade_code: str | None) -> bool:
    number = grade_number(grade_code)
    return number is not None and number <= 5


def subject_candidate_score(
    teacher: TeacherProfile,
    ctx: GroupContext,
    *,
    load: Counter[int],
    subject_load: Counter[tuple[int, str]],
    homeroom_by_section: dict[int, int],
    no_assignment: set[int],
) -> tuple[int, int, int, str]:
    subject = ctx.subject.code
    grade_code = ctx.grade.code if ctx.grade else ""
    section_id = ctx.section.id if ctx.section else None
    score = 0

    if subject in teacher.subjects:
        score += 80
    if teacher.csv_role == "subject_lead" and subject in teacher.subjects:
        score += 20
    if teacher.csv_role == "teaching_assistant":
        score -= 25
    if teacher.csv_role == "head_of_year":
        score += 5
    if teacher.membership_id in no_assignment:
        score += 15

    if section_id and homeroom_by_section.get(section_id) == teacher.membership_id:
        if is_primary_or_early(grade_code) and subject in (EARLY_YEARS_HOMEROOM_SUBJECTS if grade_code.startswith("KG") else PRIMARY_HOMEROOM_SUBJECTS):
            score += 55
        elif subject in SPECIALIST_SUBJECTS:
            score -= 15

    if not is_primary_or_early(grade_code) and subject not in teacher.subjects:
        score -= 40

    score -= load[teacher.membership_id] * 4
    score -= subject_load[(teacher.membership_id, subject)] * 8
    return (score, -load[teacher.membership_id], -subject_load[(teacher.membership_id, subject)], teacher.name)


def choose_teacher(
    teachers: list[TeacherProfile],
    ctx: GroupContext,
    *,
    load: Counter[int],
    subject_load: Counter[tuple[int, str]],
    homeroom_by_section: dict[int, int],
    no_assignment: set[int],
) -> TeacherProfile | None:
    if not teachers:
        return None
    return max(
        teachers,
        key=lambda teacher: subject_candidate_score(
            teacher,
            ctx,
            load=load,
            subject_load=subject_load,
            homeroom_by_section=homeroom_by_section,
            no_assignment=no_assignment,
        ),
    )


def choose_homeroom_teacher(
    teachers: list[TeacherProfile],
    section: ClassSection,
    grade: GradeLevel,
    *,
    load: Counter[int],
    no_assignment: set[int],
) -> TeacherProfile | None:
    key = section_key(grade.code, section.code)
    candidates = [teacher for teacher in teachers if compact_code(teacher.homeroom_code) == key]
    if not candidates:
        candidates = [
            teacher
            for teacher in teachers
            if teacher.csv_role in {"teacher", "head_of_year"} and ("ENG" in teacher.subjects or teacher.department == "Early Years")
        ]
    if not candidates:
        candidates = teachers
    return min(candidates, key=lambda teacher: (load[teacher.membership_id], teacher.membership_id not in no_assignment, teacher.name))


def plan_and_maybe_apply(db, *, apply: bool) -> PlanResult:
    school, teachers, groups, sections, assignments = load_world(db)
    valid_from = most_common_existing_valid_from(db, school.id)
    teacher_ids, group_ids, section_ids, exact = assignment_sets(assignments)
    load = Counter(row.membership_id for row in assignments)
    subject_load = Counter()
    for row in assignments:
        if row.subject_group_id:
            ctx = next((candidate for candidate in groups if candidate.group.id == row.subject_group_id), None)
            if ctx:
                subject_load[(row.membership_id, ctx.subject.code)] += 1

    homeroom_by_section = {
        row.class_section_id: row.membership_id
        for row in assignments
        if row.role == "homeroom" and row.class_section_id is not None
    }
    no_assignment = {teacher.membership_id for teacher in teachers if teacher.membership_id not in teacher_ids}
    result = PlanResult(skipped_groups=[], skipped_teachers=[])
    named_profiles, named_memberships_created, named_exceptions = ensure_named_demo_teacher_profiles(db, school, apply=apply)
    result.teacher_memberships_created = named_memberships_created
    result.skipped_teachers.extend(named_exceptions)
    for profile in named_profiles:
        if profile.membership_id not in {teacher.membership_id for teacher in teachers}:
            teachers.append(profile)
            no_assignment.add(profile.membership_id)

    for section, grade, _stage in sections:
        if section.id in section_ids:
            continue
        teacher = choose_homeroom_teacher(teachers, section, grade, load=load, no_assignment=no_assignment)
        if teacher is None:
            result.skipped_teachers.append(f"No teacher available for homeroom {grade.code}{section.code}")
            continue
        key = (teacher.membership_id, "homeroom", section.id, None)
        if key in exact:
            continue
        result.homeroom_created += 1
        exact.add(key)
        section_ids.add(section.id)
        homeroom_by_section[section.id] = teacher.membership_id
        load[teacher.membership_id] += 1
        no_assignment.discard(teacher.membership_id)
        if apply:
            db.add(
                StaffAssignment(
                    school_id=school.id,
                    membership_id=teacher.membership_id,
                    class_section_id=section.id,
                    role="homeroom",
                    valid_from=valid_from,
                )
            )

    for ctx in groups:
        if ctx.group.id in group_ids:
            continue
        teacher = choose_teacher(
            teachers,
            ctx,
            load=load,
            subject_load=subject_load,
            homeroom_by_section=homeroom_by_section,
            no_assignment=no_assignment,
        )
        if teacher is None:
            result.skipped_groups.append(ctx.group.code)
            continue
        key = (teacher.membership_id, "subject", None, ctx.group.id)
        if key in exact:
            continue
        result.subject_created += 1
        exact.add(key)
        group_ids.add(ctx.group.id)
        load[teacher.membership_id] += 1
        subject_load[(teacher.membership_id, ctx.subject.code)] += 1
        no_assignment.discard(teacher.membership_id)
        if apply:
            db.add(
                StaffAssignment(
                    school_id=school.id,
                    membership_id=teacher.membership_id,
                    subject_group_id=ctx.group.id,
                    role="subject",
                    valid_from=valid_from,
                )
            )

    groups_by_target = {
        (ctx.grade.code if ctx.grade else "", ctx.section.code if ctx.section else "", ctx.subject.code): ctx
        for ctx in groups
    }
    for profile in named_profiles:
        for target in NAMED_DEMO_TEACHER_TARGETS:
            ctx = groups_by_target.get(target)
            if ctx is None:
                result.skipped_groups.append("-".join(target))
                continue
            key = (profile.membership_id, "subject", None, ctx.group.id)
            if key in exact:
                continue
            result.named_demo_subject_created += 1
            exact.add(key)
            group_ids.add(ctx.group.id)
            load[profile.membership_id] += 1
            subject_load[(profile.membership_id, ctx.subject.code)] += 1
            no_assignment.discard(profile.membership_id)
            if apply:
                db.add(
                    StaffAssignment(
                        school_id=school.id,
                        membership_id=profile.membership_id,
                        subject_group_id=ctx.group.id,
                        role="subject",
                        valid_from=valid_from,
                    )
                )

    result.projected_groups_without_teacher = len(groups) - len(group_ids)
    result.projected_teachers_without_assignments = len([teacher for teacher in teachers if load[teacher.membership_id] == 0])
    result.projected_homeroom_gaps = len(sections) - len(section_ids)
    if apply:
        db.flush()
    return result


def print_plan(result: PlanResult, *, apply: bool) -> None:
    print("\n--- PLAN ---")
    print(f"mode: {'APPLY' if apply else 'DRY RUN'}")
    print(f"teacher memberships to create: {result.teacher_memberships_created}")
    print(f"homeroom assignments to create: {result.homeroom_created}")
    print(f"subject assignments to create: {result.subject_created}")
    print(f"named demo account subject assignments to create: {result.named_demo_subject_created}")
    print("projected after coverage:")
    print(f"  subject groups with no active teacher assignment: {result.projected_groups_without_teacher}")
    print(f"  teachers with no active assignments: {result.projected_teachers_without_assignments}")
    print(f"  sections with no homeroom teacher: {result.projected_homeroom_gaps}")
    if result.skipped_groups:
        print("subject groups intentionally unassigned:")
        for code in result.skipped_groups:
            print(f"  {code}")
    if result.skipped_teachers:
        print("teacher assignment exceptions:")
        for note in result.skipped_teachers:
            print(f"  {note}")


def run(*, apply: bool) -> None:
    db = SessionLocal()
    try:
        before = coverage_snapshot(db)
        print_coverage("BEFORE", before)
        result = plan_and_maybe_apply(db, apply=apply)
        print_plan(result, apply=apply)
        after = coverage_snapshot(db)
        print_coverage("AFTER (uncommitted)" if not apply else "AFTER", after)
        if apply:
            db.commit()
            print("\nAPPLIED (committed).")
        else:
            db.rollback()
            print("\nDRY RUN (rolled back, no changes committed). Re-run with --apply to commit.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit changes (default: dry run).")
    args = parser.parse_args()
    run(apply=args.apply)


if __name__ == "__main__":
    main()

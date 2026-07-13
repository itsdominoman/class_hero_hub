"""Seed realistic demo activity for United International School.

Dry-run by default. Writes only with --apply and the required development guards.
The script is intentionally deterministic and manifest-backed so it can be
re-run without creating duplicate junk.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from itertools import cycle
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
APP_IMPORT_ROOT = ROOT if (ROOT / "app").exists() else ROOT.parent
if str(APP_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_IMPORT_ROOT))

from app.database import SessionLocal
from app.models_school import (
    AcademicYear,
    Announcement,
    BehaviourCategory,
    BehaviourEvent,
    BranchCampus,
    CalendarEvent,
    ClassSection,
    DemoSeedRecord,
    Enrolment,
    GradeLevel,
    HomeworkItem,
    Membership,
    School,
    StaffAssignment,
    Student,
    Subject,
    SubjectGroup,
    UpdatePhoto,
    UpdatePost,
    User,
    GuardianLink,
    FhhLink,
)

TARGET_SCHOOL_NAME = "United International School"
DEFAULT_SCHOOL_SLUG = "united-international-school"
SEED_NAMESPACE = "s22-demo-v1"
SHOWCASE_SEED_NAMESPACE = "s22c-showcase-v1"
MANAGEMENT_SEED_NAMESPACE = "s22d-management-v1"
SCALE_DEMO = "demo"
SCALE_SHOWCASE = "showcase"
SCALE_MANAGEMENT = "management"
LOCAL_ASSET_MANIFEST_CANDIDATES = (
    ROOT / "docs" / "demo-assets" / "manifest.json",
    ROOT / "backend" / "demo-assets" / "manifest.json",
)

PERSONA_ENGLISH = "english_support_in_maths"
PERSONA_DUTY = "duty_break_hallway"
PERSONA_MATHS = "maths_strong_organisation"

PERSONA_SECTION_PREFERENCES = {
    PERSONA_ENGLISH: ["G1 A", "G1 B", "G2 A", "KG1 A"],
    PERSONA_DUTY: ["G4 B", "G4 A", "G5 B", "G5 A"],
    PERSONA_MATHS: ["G10 B", "G10 A", "G11 B", "G11 A"],
}

SUBJECT_PRIORITY = ("ENG", "MAT", "SCI")
DUTY_CONTEXTS = ("break", "hallway", "playground", "lunch", "assembly")
DUTY_LABELS = {
    "break": "Break",
    "hallway": "Hallway",
    "playground": "Playground",
    "lunch": "Lunch",
    "assembly": "Assembly",
}


@dataclass(frozen=True)
class World:
    school: School
    academic_year: AcademicYear
    branches: list[BranchCampus]
    grade_levels: list[GradeLevel]
    sections: list[ClassSection]
    subjects: list[Subject]
    subject_groups: list[SubjectGroup]
    teacher_memberships: list[Membership]
    teacher_users: dict[int, User]
    students: list[Student]
    active_student_ids: set[int]
    linked_student_ids: set[int]
    behaviour_categories: list[BehaviourCategory]


@dataclass(frozen=True)
class PersonaSelection:
    key: str
    student_id: int
    student_name: str
    class_section_id: int
    class_section_code: str
    grade_code: str


@dataclass(frozen=True)
class SeedTask:
    entity_type: str
    entity_key: str
    model_name: str
    payload: dict


@dataclass
class RunSummary:
    mode: str
    scale: str
    school_slug: str
    school_name: str
    as_of: date
    personas: dict[str, PersonaSelection]
    counts: Counter
    skipped_photos_reason: str | None


class SeedError(RuntimeError):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit changes; default is dry-run.")
    parser.add_argument("--as-of", dest="as_of", default=None, help="Anchor date for deterministic output (YYYY-MM-DD).")
    parser.add_argument("--school-slug", dest="school_slug", default=DEFAULT_SCHOOL_SLUG, help="Target school slug.")
    parser.add_argument("--scale", choices=(SCALE_DEMO, SCALE_SHOWCASE, SCALE_MANAGEMENT), default=SCALE_DEMO, help="Seed size/profile.")
    return parser.parse_args(argv)


def normalized_name(value: str | None) -> str:
    return (value or "").strip().casefold()


def parse_as_of(value: str | None) -> date:
    if not value:
        return date.today()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SeedError(f"Invalid --as-of value {value!r}; expected YYYY-MM-DD") from exc


def fail(message: str) -> None:
    raise SeedError(message)


def require_write_guards(args: argparse.Namespace) -> None:
    if not args.apply:
        return
    if os.getenv("APP_ENV") != "development":
        fail("Writes require APP_ENV=development")
    if os.getenv("DEMO_SEED_CONFIRM") != DEFAULT_SCHOOL_SLUG:
        fail("Writes require DEMO_SEED_CONFIRM=united-international-school")


def load_world(db, school_slug: str) -> World:
    schools_by_slug = db.query(School).filter(School.slug == school_slug).all()
    schools_by_name = db.query(School).filter(School.name == TARGET_SCHOOL_NAME).all()
    if len(schools_by_slug) != 1:
        fail(f"Expected exactly one school with slug {school_slug!r}, found {len(schools_by_slug)}")
    if len(schools_by_name) != 1:
        fail(f"Expected exactly one school named {TARGET_SCHOOL_NAME!r}, found {len(schools_by_name)}")

    school = schools_by_slug[0]
    name_match = schools_by_name[0]
    if school.id != name_match.id:
        fail("School slug/name mismatch for the target demo school")
    if normalized_name(school.name) != normalized_name(TARGET_SCHOOL_NAME) or school.slug != DEFAULT_SCHOOL_SLUG:
        fail("Target school slug/name mismatch")
    if school.suspended_at is not None or normalized_name(school.status) == "suspended":
        fail("Target school is suspended")

    academic_years = (
        db.query(AcademicYear)
        .filter(AcademicYear.school_id == school.id, AcademicYear.is_current.is_(True))
        .order_by(AcademicYear.sort_order, AcademicYear.id)
        .all()
    )
    if len(academic_years) != 1:
        fail(f"Expected exactly one current academic year, found {len(academic_years)}")
    academic_year = academic_years[0]

    branches = (
        db.query(BranchCampus)
        .filter(BranchCampus.school_id == school.id)
        .order_by(BranchCampus.sort_order, BranchCampus.code)
        .all()
    )
    grade_levels = (
        db.query(GradeLevel)
        .filter(GradeLevel.school_id == school.id)
        .order_by(GradeLevel.sort_order, GradeLevel.code)
        .all()
    )
    sections = (
        db.query(ClassSection)
        .filter(ClassSection.school_id == school.id, ClassSection.status == "active")
        .order_by(ClassSection.id)
        .all()
    )
    subjects = (
        db.query(Subject)
        .filter(Subject.school_id == school.id, Subject.status == "active")
        .order_by(Subject.sort_order, Subject.code)
        .all()
    )
    subject_groups = (
        db.query(SubjectGroup)
        .filter(SubjectGroup.school_id == school.id, SubjectGroup.status == "active")
        .order_by(SubjectGroup.id)
        .all()
    )
    teacher_memberships = (
        db.query(Membership)
        .join(User, User.id == Membership.user_id)
        .filter(
            Membership.school_id == school.id,
            Membership.role == "teacher",
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            User.status == "active",
        )
        .order_by(User.name, User.email)
        .all()
    )
    teacher_users = {
        membership.user_id: db.query(User).filter(User.id == membership.user_id).one()
        for membership in teacher_memberships
    }
    students = (
        db.query(Student)
        .filter(Student.school_id == school.id, Student.status == "active")
        .order_by(Student.id)
        .all()
    )
    active_student_ids = {student.id for student in students}
    linked_student_ids = {
        student_id
        for (student_id,) in (
            db.query(GuardianLink.student_id)
            .filter(GuardianLink.school_id == school.id, GuardianLink.status == "active")
            .distinct()
            .all()
        )
    } | {
        student_id
        for (student_id,) in (
            db.query(FhhLink.student_id)
            .filter(FhhLink.school_id == school.id, FhhLink.status == "active")
            .distinct()
            .all()
        )
    }
    behaviour_categories = (
        db.query(BehaviourCategory)
        .filter(BehaviourCategory.school_id == school.id)
        .order_by(BehaviourCategory.type, BehaviourCategory.sort_order, BehaviourCategory.label)
        .all()
    )

    if len(sections) < 4:
        fail("Not enough active sections to build a realistic demo dataset")
    if len(subjects) < 3:
        fail("Not enough active subjects to build a realistic demo dataset")
    if len(teacher_memberships) < 3:
        fail("Not enough active teachers to build a realistic demo dataset")
    if len(students) < 12:
        fail("Not enough active students to build a realistic demo dataset")

    missing_subjects = [code for code in SUBJECT_PRIORITY if not any(subject.code == code for subject in subjects)]
    if missing_subjects:
        fail(f"Missing required subjects: {', '.join(missing_subjects)}")

    return World(
        school=school,
        academic_year=academic_year,
        branches=branches,
        grade_levels=grade_levels,
        sections=sections,
        subjects=subjects,
        subject_groups=subject_groups,
        teacher_memberships=teacher_memberships,
        teacher_users=teacher_users,
        students=students,
        active_student_ids=active_student_ids,
        linked_student_ids=linked_student_ids,
        behaviour_categories=behaviour_categories,
    )


def section_by_code(world: World) -> dict[str, ClassSection]:
    grades = {grade.id: grade.code for grade in world.grade_levels}
    return {f"{grades.get(section.grade_level_id, '')} {section.code}".strip(): section for section in world.sections}


def subject_by_code(world: World) -> dict[str, Subject]:
    return {subject.code: subject for subject in world.subjects}


def grade_code_map(world: World) -> dict[int, str]:
    return {grade.id: grade.code for grade in world.grade_levels}


def group_index(world: World) -> dict[tuple[int, str], SubjectGroup]:
    index: dict[tuple[int, str], SubjectGroup] = {}
    for group in world.subject_groups:
        subject = next((item for item in world.subjects if item.id == group.subject_id), None)
        if subject is not None:
            index[(group.class_section_id or 0, subject.code)] = group
    return index


def class_section_for_student(db, student_id: int) -> tuple[int | None, str | None, str | None]:
    row = (
        db.query(ClassSection.id, ClassSection.code, GradeLevel.code)
        .join(Enrolment, Enrolment.class_section_id == ClassSection.id)
        .join(GradeLevel, GradeLevel.id == ClassSection.grade_level_id)
        .filter(Enrolment.student_id == student_id, Enrolment.kind == "member", Enrolment.valid_to.is_(None), ClassSection.status == "active")
        .order_by(ClassSection.id.desc())
        .first()
    )
    if row is None:
        return None, None, None
    return row[0], row[1], row[2]


def student_name(student: Student) -> str:
    return f"{student.first_name} {student.last_name}".strip()


def is_bob(student: Student) -> bool:
    return normalized_name(student.first_name) == "bob" and normalized_name(student.last_name) == "smith"


def select_persona_student(world: World, db, persona_key: str) -> PersonaSelection:
    preferences = PERSONA_SECTION_PREFERENCES[persona_key]
    grades = grade_code_map(world)
    for section_label in preferences:
        try:
            grade_code, section_code = section_label.split(" ", 1)
        except ValueError:
            continue
        section = next(
            (item for item in world.sections if grades.get(item.grade_level_id) == grade_code and item.code == section_code),
            None,
        )
        if section is None:
            continue
        candidates = (
            db.query(Student)
            .join(Enrolment, Enrolment.student_id == Student.id)
            .filter(
                Student.school_id == world.school.id,
                Student.status == "active",
                Enrolment.class_section_id == section.id,
                Enrolment.kind == "member",
                Enrolment.valid_to.is_(None),
            )
            .order_by(Student.id)
            .all()
        )
        for student in candidates:
            if student.id in world.linked_student_ids or is_bob(student):
                continue
            return PersonaSelection(
                key=persona_key,
                student_id=student.id,
                student_name=student_name(student),
                class_section_id=section.id,
                class_section_code=f"{grades.get(section.grade_level_id, '')} {section.code}".strip(),
                grade_code=grades.get(section.grade_level_id, ""),
            )
    fail(f"Could not resolve a deterministic persona for {persona_key}")


def select_personas(world: World, db) -> dict[str, PersonaSelection]:
    selections = {
        PERSONA_ENGLISH: select_persona_student(world, db, PERSONA_ENGLISH),
        PERSONA_DUTY: select_persona_student(world, db, PERSONA_DUTY),
        PERSONA_MATHS: select_persona_student(world, db, PERSONA_MATHS),
    }
    ids = [selection.student_id for selection in selections.values()]
    if len(set(ids)) != len(ids):
        fail("Persona selection unexpectedly resolved to the same student twice")
    return selections


def locate_student_section(db, student_id: int) -> tuple[int | None, str | None, str | None]:
    return class_section_for_student(db, student_id)


def resolve_bob_for_showcase(world: World, db) -> tuple[Student, PersonaSelection]:
    bob = next((student for student in world.students if is_bob(student)), None)
    if bob is None:
        fail("Could not resolve Bob Smith for showcase seeding")

    class_section_id, class_code, grade_code = locate_student_section(db, bob.id)
    if class_section_id is None or class_code is None or grade_code is None:
        fail("Bob Smith is not enrolled in an active class section")
    if f"{grade_code} {class_code}".strip() != "KG1 A":
        fail(f"Bob Smith must be in KG1 A for showcase seeding, found {grade_code} {class_code}")

    return bob, PersonaSelection(
        key="bob_showcase",
        student_id=bob.id,
        student_name=student_name(bob),
        class_section_id=class_section_id,
        class_section_code=f"{grade_code} {class_code}".strip(),
        grade_code=grade_code,
    )


def teacher_assignments_for_world(db, school_id: int) -> dict[str, list[tuple[Membership, User, StaffAssignment | None]]]:
    rows = (
        db.query(Membership, User, StaffAssignment)
        .join(User, User.id == Membership.user_id)
        .outerjoin(
            StaffAssignment,
            (StaffAssignment.membership_id == Membership.id)
            & (StaffAssignment.school_id == school_id)
            & (StaffAssignment.valid_to.is_(None))
        )
        .filter(
            Membership.school_id == school_id,
            Membership.role == "teacher",
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            User.status == "active",
        )
        .order_by(User.name, User.email, StaffAssignment.id)
        .all()
    )
    by_teacher: dict[int, list[StaffAssignment]] = defaultdict(list)
    teacher_membership_by_user: dict[int, Membership] = {}
    teacher_user_by_id: dict[int, User] = {}
    for membership, user, assignment in rows:
        teacher_membership_by_user[user.id] = membership
        teacher_user_by_id[user.id] = user
        if assignment is not None:
            by_teacher[user.id].append(assignment)
    return {
        "assignments": by_teacher,
        "membership_by_user": teacher_membership_by_user,
        "user_by_id": teacher_user_by_id,
    }


def teacher_pool(world: World, db) -> list[dict]:
    assignments = teacher_assignments_for_world(db, world.school.id)
    pool: list[dict] = []
    for user_id, user in sorted(assignments["user_by_id"].items(), key=lambda item: (item[1].name or item[1].email or "", item[1].email or "")):
        membership = assignments["membership_by_user"][user_id]
        teacher_assignments = assignments["assignments"].get(user_id, [])
        pool.append({"user": user, "membership": membership, "assignments": teacher_assignments})
    if not pool:
        fail("No active teachers with assignments were available")
    return pool


def teacher_for_target(pool: list[dict], class_section_id: int | None = None, subject_group_id: int | None = None) -> User:
    if class_section_id is not None:
        for entry in pool:
            if any(assignment.class_section_id == class_section_id for assignment in entry["assignments"]):
                return entry["user"]
    if subject_group_id is not None:
        for entry in pool:
            if any(assignment.subject_group_id == subject_group_id for assignment in entry["assignments"]):
                return entry["user"]
    return pool[0]["user"]


def pick_category(world: World, category_type: str, preferred_labels: Iterable[str]) -> BehaviourCategory:
    for label in preferred_labels:
        for category in world.behaviour_categories:
            if category.type == category_type and category.label == label and category.active:
                return category
    for category in world.behaviour_categories:
        if category.type == category_type and category.active:
            return category
    fail(f"No active {category_type} behaviour categories available")


def section_students(db, section_id: int, world: World) -> list[Student]:
    rows = (
        db.query(Student)
        .join(Enrolment, Enrolment.student_id == Student.id)
        .filter(
            Student.school_id == world.school.id,
            Student.status == "active",
            Enrolment.class_section_id == section_id,
            Enrolment.kind == "member",
            Enrolment.valid_to.is_(None),
        )
        .order_by(Student.id)
        .all()
    )
    return [student for student in rows if student.id not in world.linked_student_ids and not is_bob(student)]


def pick_student_from_section(db, world: World, section_id: int, offset: int = 0) -> Student:
    students = section_students(db, section_id, world)
    if not students:
        fail(f"No eligible students available in section {section_id}")
    return students[offset % len(students)]


def subject_group_for_section_and_code(world: World, section_id: int, subject_code: str) -> SubjectGroup | None:
    for group in world.subject_groups:
        if group.class_section_id == section_id:
            subject = next((item for item in world.subjects if item.id == group.subject_id), None)
            if subject is not None and subject.code == subject_code:
                return group
    for group in world.subject_groups:
        subject = next((item for item in world.subjects if item.id == group.subject_id), None)
        if subject is not None and subject.code == subject_code:
            return group
    return None


def make_time(as_of: date, days_offset: int, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(as_of + timedelta(days=days_offset), time(hour=hour, minute=minute), tzinfo=timezone.utc)


def clamp_points(category: BehaviourCategory) -> int:
    return category.points_value


def event_blueprint(
    *,
    key: str,
    student_id: int,
    actor_user_id: int,
    category: BehaviourCategory,
    points_delta: int,
    note: str,
    created_at: datetime,
    context_type: str,
    class_section_id: int | None = None,
    subject_group_id: int | None = None,
    duty_context: str | None = None,
) -> SeedTask:
    return SeedTask(
        entity_type="behaviour_event",
        entity_key=key,
        model_name="behaviour_events",
        payload={
            "student_id": student_id,
            "actor_user_id": actor_user_id,
            "category_id": category.id,
            "points_delta": points_delta,
            "note": note,
            "created_at": created_at,
            "source": "teacher",
            "context_type": context_type,
            "class_section_id": class_section_id,
            "subject_group_id": subject_group_id,
            "duty_context": duty_context,
        },
    )


def build_behaviour_tasks(world: World, db, personas: dict[str, PersonaSelection], pool: list[dict], as_of: date) -> list[SeedTask]:
    section_index = section_by_code(world)
    grade_codes = grade_code_map(world)
    subject_index = subject_by_code(world)
    group_lookup = group_index(world)

    english_persona = personas[PERSONA_ENGLISH]
    duty_persona = personas[PERSONA_DUTY]
    maths_persona = personas[PERSONA_MATHS]

    english_section = section_index.get(english_persona.class_section_code)
    duty_section = section_index.get(duty_persona.class_section_code)
    maths_section = section_index.get(maths_persona.class_section_code)
    if english_section is None or duty_section is None or maths_section is None:
        fail("Persona sections could not be resolved")

    english_group = subject_group_for_section_and_code(world, english_section.id, "ENG")
    maths_group = subject_group_for_section_and_code(world, maths_section.id, "MAT")
    science_group = subject_group_for_section_and_code(world, maths_section.id, "SCI") or subject_group_for_section_and_code(world, english_section.id, "SCI")
    if english_group is None or maths_group is None or science_group is None:
        fail("Required subject groups for English/Maths/Science could not be resolved")

    positive = pick_category(
        world,
        "positive",
        ("Good work", "Great effort", "Participation", "Listening well", "Kindness", "Responsible behaviour", "Leadership", "Above and beyond"),
    )
    positive_two = pick_category(
        world,
        "positive",
        ("Safe play", "Helping others", "Teamwork", "Improvement", "Respectful behaviour", "Helping at break", "Good sportsmanship"),
    )
    needs_work = pick_category(
        world,
        "needs_work",
        ("Homework incomplete", "Forgot equipment", "Not following instructions", "Off-task", "Wandering halls", "Late for class", "Unsafe play"),
    )
    needs_work_two = pick_category(
        world,
        "needs_work",
        ("Disrespect", "Running indoors", "Out of bounds", "Leaving area without permission", "Not listening", "Unsafe behaviour"),
    )

    tasks: list[SeedTask] = []
    teacher_cycle = cycle(pool)

    def next_teacher(class_section_id: int | None = None, subject_group_id: int | None = None) -> User:
        chosen = teacher_for_target(pool, class_section_id=class_section_id, subject_group_id=subject_group_id)
        if chosen is not None:
            return chosen
        return next(teacher_cycle)["user"]

    # Persona 1: English strong, Maths support.
    english_events = [
        ("subject", 0, english_persona.student_id, english_group.class_section_id, english_group.id, None, positive, 1, "Strong reading response"),
        ("subject", 1, english_persona.student_id, english_group.class_section_id, english_group.id, None, positive_two, 1, "Excellent comprehension"),
        ("subject", 2, english_persona.student_id, english_group.class_section_id, english_group.id, None, positive, 1, "Helpful discussion"),
        ("subject", 3, english_persona.student_id, english_group.class_section_id, english_group.id, None, positive_two, 1, "Clear paragraph"),
        ("subject", 4, english_persona.student_id, english_group.class_section_id, english_group.id, None, positive, 1, "Reading confidence"),
        ("subject", 5, english_persona.student_id, maths_group.class_section_id, maths_group.id, None, needs_work, -1, "Needs maths scaffolding"),
        ("subject", 6, english_persona.student_id, maths_group.class_section_id, maths_group.id, None, needs_work_two, -1, "Maths workbook incomplete"),
        ("subject", 7, english_persona.student_id, maths_group.class_section_id, maths_group.id, None, needs_work, -1, "Extra practice needed"),
        ("subject", 8, english_persona.student_id, science_group.class_section_id, science_group.id, None, positive, 1, "Careful science explanation"),
        ("class", 9, english_persona.student_id, english_section.id, None, None, positive_two, 1, "Ready for learning"),
    ]
    for idx, (_, day_offset, student_id, class_section_id, subject_group_id, duty_context, category, points_delta, note) in enumerate(english_events):
        teacher = next_teacher(class_section_id=class_section_id, subject_group_id=subject_group_id)
        created_at = make_time(as_of, -48 + day_offset * 3, 9 + (idx % 3), 10 * (idx % 4))
        tasks.append(
            event_blueprint(
                key=f"{PERSONA_ENGLISH}:{idx}",
                student_id=student_id,
                actor_user_id=teacher.id,
                category=category,
                points_delta=points_delta,
                note=note,
                created_at=created_at,
                context_type="subject" if subject_group_id is not None else "class",
                class_section_id=class_section_id if subject_group_id is None else None,
                subject_group_id=subject_group_id,
                duty_context=duty_context,
            )
        )

    # Persona 2: good in class, loses points in break/hallway.
    duty_events = [
        ("class", 0, duty_persona.student_id, duty_section.id, None, None, positive, 1, "Settle quickly"),
        ("class", 1, duty_persona.student_id, duty_section.id, None, None, positive_two, 1, "Worked well independently"),
        ("class", 2, duty_persona.student_id, duty_section.id, None, None, positive, 1, "Helpful in group work"),
        ("duty", 3, duty_persona.student_id, None, None, "break", needs_work, -1, "Reminder at break"),
        ("duty", 4, duty_persona.student_id, None, None, "hallway", needs_work_two, -1, "Hallway reminder"),
        ("duty", 5, duty_persona.student_id, None, None, "playground", needs_work, -1, "Playground conduct"),
        ("duty", 6, duty_persona.student_id, None, None, "hallway", needs_work_two, -1, "Returned after reminder"),
        ("duty", 7, duty_persona.student_id, None, None, "break", needs_work, -1, "Line up reminder"),
        ("class", 8, duty_persona.student_id, duty_section.id, None, None, positive_two, 1, "Back on task"),
        ("duty", 9, duty_persona.student_id, None, None, "assembly", positive, 1, "Assembly readiness"),
    ]
    for idx, (_, day_offset, student_id, class_section_id, subject_group_id, duty_context, category, points_delta, note) in enumerate(duty_events, start=10):
        teacher = next_teacher(class_section_id=class_section_id or duty_section.id, subject_group_id=subject_group_id)
        tasks.append(
            event_blueprint(
                key=f"{PERSONA_DUTY}:{idx}",
                student_id=student_id,
                actor_user_id=teacher.id,
                category=category,
                points_delta=points_delta,
                note=note,
                created_at=make_time(as_of, -42 + day_offset * 2, 10 + (idx % 2), 5 * (idx % 6)),
                context_type="duty" if duty_context else "class",
                class_section_id=class_section_id if duty_context is None else None,
                subject_group_id=subject_group_id,
                duty_context=duty_context,
            )
        )

    # Persona 3: strong in Maths, weaker on organisation.
    maths_events = [
        ("subject", 0, maths_persona.student_id, maths_group.class_section_id, maths_group.id, None, positive, 1, "Sharp number work"),
        ("subject", 1, maths_persona.student_id, maths_group.class_section_id, maths_group.id, None, positive_two, 1, "Quick recall"),
        ("subject", 2, maths_persona.student_id, maths_group.class_section_id, maths_group.id, None, positive, 1, "Maths confidence"),
        ("subject", 3, maths_persona.student_id, maths_group.class_section_id, maths_group.id, None, positive_two, 1, "Problem solving"),
        ("subject", 4, maths_persona.student_id, science_group.class_section_id, science_group.id, None, positive, 1, "Good science follow-up"),
        ("class", 5, maths_persona.student_id, maths_section.id, None, None, needs_work, -1, "Homework incomplete"),
        ("class", 6, maths_persona.student_id, maths_section.id, None, None, needs_work_two, -1, "Forgot equipment"),
        ("class", 7, maths_persona.student_id, maths_section.id, None, None, needs_work, -1, "Organisation reminder"),
        ("duty", 8, maths_persona.student_id, None, None, "hallway", needs_work_two, -1, "Late to line up"),
        ("general", 9, maths_persona.student_id, None, None, None, positive, 1, "Responsible reflection"),
    ]
    for idx, (_, day_offset, student_id, class_section_id, subject_group_id, duty_context, category, points_delta, note) in enumerate(maths_events, start=20):
        teacher = next_teacher(class_section_id=class_section_id or maths_section.id, subject_group_id=subject_group_id)
        tasks.append(
            event_blueprint(
                key=f"{PERSONA_MATHS}:{idx}",
                student_id=student_id,
                actor_user_id=teacher.id,
                category=category,
                points_delta=points_delta,
                note=note,
                created_at=make_time(as_of, -36 + day_offset * 2, 8 + (idx % 4), 15 * (idx % 3)),
                context_type="general" if duty_context is None and class_section_id is None and subject_group_id is None else ("duty" if duty_context else ("subject" if subject_group_id else "class")),
                class_section_id=class_section_id if duty_context is None and subject_group_id is None and class_section_id is not None else None,
                subject_group_id=subject_group_id,
                duty_context=duty_context,
            )
        )

    # Class positive / needs-work sections.
    positive_class = next((section for section in world.sections if grade_codes.get(section.grade_level_id) == "G1" and section.code == "A"), None)
    needs_work_class = next((section for section in world.sections if grade_codes.get(section.grade_level_id) == "G4" and section.code == "B"), None)
    if positive_class is None or needs_work_class is None:
        fail("Required anchor sections G1 A and G4 B were not available")

    positive_students = [student for student in section_students(db, positive_class.id, world)]
    needs_work_students = [student for student in section_students(db, needs_work_class.id, world)]
    if not positive_students or not needs_work_students:
        fail("Anchor sections did not have any eligible students")

    positive_templates = [
        ("class", positive_class.id, None, positive, "Ready to learn"),
        ("class", positive_class.id, None, positive_two, "Excellent collaboration"),
        ("subject", positive_class.id, "ENG", positive, "Reading progress"),
        ("subject", positive_class.id, "SCI", positive_two, "Science curiosity"),
        ("duty", None, None, positive, "safe play"),
    ]
    needs_work_templates = [
        ("class", needs_work_class.id, None, needs_work, "Needs reminder"),
        ("class", needs_work_class.id, None, needs_work_two, "Behaviour reminder"),
        ("subject", needs_work_class.id, "MAT", needs_work, "Maths incomplete"),
        ("duty", None, None, needs_work_two, "hallway reminder"),
        ("duty", None, None, needs_work, "break reminder"),
    ]

    for idx in range(20):
        student = positive_students[idx % len(positive_students)]
        template = positive_templates[idx % len(positive_templates)]
        context_type, section_id, subject_code, category, note = template
        if context_type == "subject":
            group = subject_group_for_section_and_code(world, section_id, subject_code or "ENG")
            if group is None:
                continue
            teacher = next_teacher(class_section_id=group.class_section_id, subject_group_id=group.id)
            tasks.append(
                event_blueprint(
                    key=f"anchor-positive:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=note,
                    created_at=make_time(as_of, -28 + idx, 11, 0),
                    context_type="subject",
                    subject_group_id=group.id,
                )
            )
        elif context_type == "duty":
            teacher = next_teacher(class_section_id=positive_class.id)
            duty_context = DUTY_CONTEXTS[idx % len(DUTY_CONTEXTS)]
            duty_category = pick_category(world, "positive", ("Safe play", "Helping at break", "Good sportsmanship", "Kindness", "Teamwork"))
            tasks.append(
                event_blueprint(
                    key=f"anchor-positive-duty:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=duty_category,
                    points_delta=duty_category.points_value,
                    note=f"Positive {DUTY_LABELS[duty_context].lower()} behaviour",
                    created_at=make_time(as_of, -24 + idx, 13, 20),
                    context_type="duty",
                    duty_context=duty_context,
                )
            )
        else:
            teacher = next_teacher(class_section_id=positive_class.id)
            tasks.append(
                event_blueprint(
                    key=f"anchor-positive-class:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=note,
                    created_at=make_time(as_of, -30 + idx, 8, 45),
                    context_type="class",
                    class_section_id=positive_class.id,
                )
            )

    for idx in range(20):
        student = needs_work_students[idx % len(needs_work_students)]
        template = needs_work_templates[idx % len(needs_work_templates)]
        context_type, section_id, subject_code, category, note = template
        if context_type == "subject":
            group = subject_group_for_section_and_code(world, section_id, subject_code or "MAT")
            if group is None:
                continue
            teacher = next_teacher(class_section_id=group.class_section_id, subject_group_id=group.id)
            tasks.append(
                event_blueprint(
                    key=f"anchor-needs:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=note,
                    created_at=make_time(as_of, -22 + idx, 12, 5),
                    context_type="subject",
                    subject_group_id=group.id,
                )
            )
        elif context_type == "duty":
            teacher = next_teacher(class_section_id=needs_work_class.id)
            duty_context = DUTY_CONTEXTS[(idx + 2) % len(DUTY_CONTEXTS)]
            duty_category = pick_category(world, "needs_work", ("Wandering halls", "Out of bounds", "Unsafe play", "Running indoors", "Leaving area without permission", "Not listening"))
            tasks.append(
                event_blueprint(
                    key=f"anchor-needs-duty:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=duty_category,
                    points_delta=duty_category.points_value,
                    note=f"Reminder at {DUTY_LABELS[duty_context].lower()}",
                    created_at=make_time(as_of, -18 + idx, 13, 40),
                    context_type="duty",
                    duty_context=duty_context,
                )
            )
        else:
            teacher = next_teacher(class_section_id=needs_work_class.id)
            tasks.append(
                event_blueprint(
                    key=f"anchor-needs-class:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=note,
                    created_at=make_time(as_of, -20 + idx, 9, 25),
                    context_type="class",
                    class_section_id=needs_work_class.id,
                )
            )

    # Wider school mix.
    eligible_students = [student for student in world.students if student.id not in world.linked_student_ids and not is_bob(student)]
    subject_codes = ["ENG", "MAT", "SCI"]
    for idx in range(68):
        student = eligible_students[idx % len(eligible_students)]
        class_section_id, class_code, grade_code = class_section_for_student(db, student.id)
        if class_section_id is None:
            continue
        subject_code = subject_codes[idx % len(subject_codes)]
        mode = idx % 4
        if mode == 0:
            group = subject_group_for_section_and_code(world, class_section_id, subject_code)
            if group is None:
                continue
            category = positive if idx % 2 == 0 else positive_two
            teacher = next_teacher(class_section_id=group.class_section_id, subject_group_id=group.id)
            tasks.append(
                event_blueprint(
                    key=f"mix-subject:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=f"{subject_code} progress",
                    created_at=make_time(as_of, -34 + idx, 10 + (idx % 3), 30),
                    context_type="subject",
                    subject_group_id=group.id,
                )
            )
        elif mode == 1:
            category = needs_work if idx % 3 else needs_work_two
            teacher = next_teacher(class_section_id=class_section_id)
            tasks.append(
                event_blueprint(
                    key=f"mix-class:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=f"Class reminder for {class_code}",
                    created_at=make_time(as_of, -32 + idx, 8 + (idx % 4), 5),
                    context_type="class",
                    class_section_id=class_section_id,
                )
            )
        elif mode == 2:
            duty_context = DUTY_CONTEXTS[idx % len(DUTY_CONTEXTS)]
            category = positive if idx % 2 == 0 else needs_work
            if category.points_value < 0:
                category = pick_category(world, "needs_work", ("Wandering halls", "Out of bounds", "Unsafe play", "Running indoors", "Leaving area without permission"))
            else:
                category = pick_category(world, "positive", ("Safe play", "Helping at break", "Teamwork", "Kindness", "Leadership"))
            teacher = next_teacher(class_section_id=class_section_id)
            tasks.append(
                event_blueprint(
                    key=f"mix-duty:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=f"{DUTY_LABELS[duty_context]} duty",
                    created_at=make_time(as_of, -30 + idx, 13, 10),
                    context_type="duty",
                    duty_context=duty_context,
                )
            )
        else:
            category = positive if idx % 2 == 0 else needs_work
            teacher = next_teacher(class_section_id=class_section_id)
            tasks.append(
                event_blueprint(
                    key=f"mix-general:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=f"General school pattern {idx:02d}",
                    created_at=make_time(as_of, -26 + idx, 7 + (idx % 5), 50),
                    context_type="general",
                )
            )

    return tasks


def build_showcase_behaviour_tasks(
    world: World,
    db,
    personas: dict[str, PersonaSelection],
    pool: list[dict],
    as_of: date,
) -> list[SeedTask]:
    bob, bob_selection = resolve_bob_for_showcase(world, db)
    section_index = section_by_code(world)
    subject_index = subject_by_code(world)
    group_lookup = group_index(world)
    grade_codes = grade_code_map(world)

    kg1_section = section_index.get("KG1 A")
    if kg1_section is None:
        fail("KG1 A section is required for showcase seeding")

    candidate_codes = ["ENG", "MAT", "SCI", "ARA", "ICT", "PE"]
    available_subject_codes = [code for code in candidate_codes if code in subject_index]
    if not available_subject_codes:
        fail("No usable subjects were available for showcase seeding")

    positive_categories = [category for category in world.behaviour_categories if category.type == "positive" and category.active]
    needs_work_categories = [category for category in world.behaviour_categories if category.type == "needs_work" and category.active]
    if not positive_categories or not needs_work_categories:
        fail("Behaviour categories were not available for showcase seeding")

    tasks: list[SeedTask] = []
    teacher_cycle = cycle(pool)
    active_students = [student for student in world.students if student.status == "active" and student.id not in world.linked_student_ids]
    active_students.sort(key=lambda student: (student.id != bob.id, student.id))
    class_sections = list(world.sections)
    class_sections.sort(key=lambda section: (grade_codes.get(section.grade_level_id, ""), section.code, section.id))

    def next_teacher(class_section_id: int | None = None, subject_group_id: int | None = None) -> User:
        chosen = teacher_for_target(pool, class_section_id=class_section_id, subject_group_id=subject_group_id)
        if chosen is not None:
            return chosen
        return next(teacher_cycle)["user"]

    def choose_category(idx: int, positive: bool) -> BehaviourCategory:
        categories = positive_categories if positive else needs_work_categories
        return categories[idx % len(categories)]

    # Bob gets a handful of realistic, visible entries in KG1 A without flood.
    bob_patterns = [
        ("class", None, None, "Settled into KG1 A routines", True, 1, 0, 8, 30),
        ("subject", kg1_section.id, "ENG", "Reading time participation", True, 1, 3, 9, 5),
        ("subject", kg1_section.id, "MAT", "Counting support", True, 1, 6, 10, 10),
        ("duty", None, None, "Breakfast line reminder", False, -1, 9, 2, 10),
        ("duty", None, None, "Playground boundary reminder", False, -1, 12, 5, 20),
        ("class", None, None, "Quick reset after reminder", True, 1, 15, 8, 45),
        ("subject", kg1_section.id, "SCI", "Careful observation", True, 1, 18, 9, 15),
        ("duty", None, None, "Assembly listening", True, 1, 21, 13, 0),
    ]
    for idx, (context_type, class_section_id, subject_code, note, positive, _points_delta, day_offset, hour, minute) in enumerate(bob_patterns):
        category = choose_category(idx, positive)
        subject_group_id = None
        duty_context = None
        if context_type == "subject" and subject_code is not None:
            subject_group = subject_group_for_section_and_code(world, kg1_section.id, subject_code)
            if subject_group is None:
                fail(f"Could not resolve KG1 A subject group for {subject_code}")
            subject_group_id = subject_group.id
        elif context_type == "duty":
            duty_context = DUTY_CONTEXTS[idx % len(DUTY_CONTEXTS)]
        teacher = next_teacher(class_section_id=kg1_section.id if context_type != "subject" else class_section_id, subject_group_id=subject_group_id)
        tasks.append(
            event_blueprint(
                key=f"bob:{idx}",
                student_id=bob.id,
                actor_user_id=teacher.id,
                category=category,
                points_delta=category.points_value,
                note=note,
                created_at=make_time(as_of, -28 + day_offset, hour, minute),
                context_type=context_type if context_type != "class" else "class",
                class_section_id=kg1_section.id if context_type == "class" else None,
                subject_group_id=subject_group_id,
                duty_context=duty_context,
            )
        )

    # KG1 A visible content for parents and management reports.
    kg1_students = [
        student
        for student in active_students
        if locate_student_section(db, student.id)[0] == kg1_section.id
    ]
    if not kg1_students:
        fail("KG1 A did not have any active students for showcase seeding")

    for idx in range(10):
        teacher = next_teacher(class_section_id=kg1_section.id)
        student = kg1_students[idx % len(kg1_students)]
        category = choose_category(idx, positive=(idx % 2 == 0))
        tasks.append(
            event_blueprint(
                key=f"kg1-class:{idx}",
                student_id=student.id,
                actor_user_id=teacher.id,
                category=category,
                points_delta=category.points_value,
                note="KG1 A classroom routine snapshot" if idx % 2 == 0 else "KG1 A reminder",
                created_at=make_time(as_of, -26 + idx, 8, 20 + idx),
                context_type="class",
                class_section_id=kg1_section.id,
            )
        )

    for idx in range(10):
        subject_code = available_subject_codes[idx % len(available_subject_codes)]
        subject_group = subject_group_for_section_and_code(world, kg1_section.id, subject_code)
        if subject_group is None:
            continue
        teacher = next_teacher(class_section_id=kg1_section.id, subject_group_id=subject_group.id)
        student = kg1_students[idx % len(kg1_students)]
        category = choose_category(idx, positive=True)
        tasks.append(
            event_blueprint(
                key=f"kg1-subject:{idx}",
                student_id=student.id,
                actor_user_id=teacher.id,
                category=category,
                points_delta=category.points_value,
                note=f"KG1 A {subject_code} learning moment",
                created_at=make_time(as_of, -24 + idx, 9, 5 + idx),
                context_type="subject",
                subject_group_id=subject_group.id,
            )
        )

    for idx in range(12):
        teacher = next_teacher(class_section_id=kg1_section.id)
        student = kg1_students[idx % len(kg1_students)]
        duty_context = DUTY_CONTEXTS[idx % len(DUTY_CONTEXTS)]
        positive = idx % 3 != 1
        category = choose_category(idx, positive=positive)
        tasks.append(
            event_blueprint(
                key=f"kg1-duty:{idx}",
                student_id=student.id,
                actor_user_id=teacher.id,
                category=category,
                points_delta=category.points_value,
                note=f"KG1 A {DUTY_LABELS[duty_context].lower()} note",
                created_at=make_time(as_of, -20 + idx, 12, 10 + idx),
                context_type="duty",
                duty_context=duty_context,
            )
        )

    # Broad reporting-scale coverage across classes, subjects, teachers, and students.
    subject_group_cache: list[SubjectGroup] = []
    for section in class_sections:
        for code in available_subject_codes:
            group = subject_group_for_section_and_code(world, section.id, code)
            if group is not None:
                subject_group_cache.append(group)
    if not subject_group_cache:
        fail("No subject groups were available for showcase seeding")

    broad_students = [student for student in active_students if student.id != bob.id]
    if not broad_students:
        fail("Not enough students available for showcase seeding")

    context_cycle = ("class", "subject", "duty", "general")
    duty_cycle = cycle(DUTY_CONTEXTS)
    for idx in range(2000 - len(tasks)):
        student = broad_students[idx % len(broad_students)]
        section_id, class_code, _grade_code = class_section_for_student(db, student.id)
        if section_id is None:
            continue
        mode = context_cycle[idx % len(context_cycle)]
        positive = idx % 5 != 3
        category = choose_category(idx, positive=positive)
        days_offset = -42 + (idx % 36)
        hour = 8 + (idx % 5)
        minute = (idx * 7) % 60
        if mode == "subject":
            subject_group = subject_group_cache[idx % len(subject_group_cache)]
            teacher = next_teacher(class_section_id=subject_group.class_section_id, subject_group_id=subject_group.id)
            subject_code = next((subject.code for subject in world.subjects if subject.id == subject_group.subject_id), "SUB")
            tasks.append(
                event_blueprint(
                    key=f"showcase-subject:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=f"{subject_code} reporting snapshot {idx:03d}",
                    created_at=make_time(as_of, days_offset, hour, minute),
                    context_type="subject",
                    subject_group_id=subject_group.id,
                )
            )
        elif mode == "class":
            teacher = next_teacher(class_section_id=section_id)
            tasks.append(
                event_blueprint(
                    key=f"showcase-class:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=f"Class report pattern {class_code or section_id}",
                    created_at=make_time(as_of, days_offset, hour, minute),
                    context_type="class",
                    class_section_id=section_id,
                )
            )
        elif mode == "duty":
            teacher = next_teacher(class_section_id=section_id)
            duty_context = next(duty_cycle)
            tasks.append(
                event_blueprint(
                    key=f"showcase-duty:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=f"{DUTY_LABELS[duty_context]} duty report",
                    created_at=make_time(as_of, days_offset, hour, minute),
                    context_type="duty",
                    duty_context=duty_context,
                )
            )
        else:
            teacher = next_teacher(class_section_id=section_id)
            tasks.append(
                event_blueprint(
                    key=f"showcase-general:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=f"General reporting trend {idx:03d}",
                    created_at=make_time(as_of, days_offset, hour, minute),
                    context_type="general",
                )
            )

    if len(tasks) != 2000:
        fail(f"Showcase behaviour task count mismatch: expected 2000, got {len(tasks)}")
    return tasks


def maybe_load_photo_assets() -> tuple[list[dict], str | None]:
    for candidate in LOCAL_ASSET_MANIFEST_CANDIDATES:
        if candidate.exists():
            try:
                assets = json.loads(candidate.read_text())
            except json.JSONDecodeError as exc:
                raise SeedError(f"Invalid local asset manifest: {candidate}") from exc
            if not isinstance(assets, list):
                raise SeedError(f"Asset manifest must be a list: {candidate}")
            return assets, None
    return [], "No reviewed local photo asset manifest was found; update photos were skipped."


def build_homework_tasks(world: World, personas: dict[str, PersonaSelection], as_of: date) -> list[SeedTask]:
    section_index = section_by_code(world)
    tasks: list[SeedTask] = []
    english_section = section_index.get(personas[PERSONA_ENGLISH].class_section_code)
    duty_section = section_index.get(personas[PERSONA_DUTY].class_section_code)
    maths_section = section_index.get(personas[PERSONA_MATHS].class_section_code)
    if english_section is None or duty_section is None or maths_section is None:
        fail("Persona sections could not be resolved for homework seeding")

    homework_specs = [
        ("homework", "class_section", english_section.id, None, "G1 A reading practice", -5, "Read the short story and answer five questions."),
        ("homework", "subject_group", None, subject_group_for_section_and_code(world, english_section.id, "ENG"), "English vocabulary check", -2, "Learn the vocabulary list and bring the notebook."),
        ("homework", "subject_group", None, subject_group_for_section_and_code(world, english_section.id, "SCI"), "Science observation log", 3, "Observe and note the experiment changes."),
        ("homework", "class_section", duty_section.id, None, "G4 B class practice", 2, "Complete the practice sheet and return it tomorrow."),
        ("homework", "subject_group", None, subject_group_for_section_and_code(world, duty_section.id, "ENG"), "Reading fluency", 6, "Read aloud with a family member."),
        ("homework", "subject_group", None, subject_group_for_section_and_code(world, maths_section.id, "MAT"), "Maths review set", 1, "Complete the mixed practice set."),
        ("homework", "subject_group", None, subject_group_for_section_and_code(world, maths_section.id, "SCI"), "Science revision", 4, "Revise the unit notes and bring questions."),
        ("homework", "class_section", maths_section.id, None, "Organisation checklist", 8, "Pack equipment and finish the checklist."),
        ("homework", "subject_group", None, subject_group_for_section_and_code(world, english_section.id, "MAT"), "Cross-curricular maths", 10, "Use the workbook to practise problem solving."),
        ("homework", "subject_group", None, subject_group_for_section_and_code(world, duty_section.id, "SCI"), "Science reflection", 12, "Write three sentences about the lesson."),
        ("homework", "class_section", english_section.id, None, "Reading reminder", 13, "Bring the reading folder and planner."),
        ("homework", "subject_group", None, subject_group_for_section_and_code(world, maths_section.id, "ENG"), "English response", 14, "Write a short response to the prompt."),
    ]
    for idx, (_, audience_type, class_section_id, subject_group, title, day_offset, body) in enumerate(homework_specs):
        if subject_group is None and audience_type == "subject_group":
            continue
        tasks.append(
            SeedTask(
                entity_type="homework_item",
                entity_key=f"homework:{idx}",
                model_name="homework_items",
                payload={
                    "item_type": "homework",
                    "title": title,
                    "body": body,
                    "audience_type": audience_type,
                    "class_section_id": class_section_id if audience_type == "class_section" else None,
                    "subject_group_id": subject_group.id if audience_type == "subject_group" and subject_group is not None else None,
                    "due_at": make_time(as_of, day_offset, 14, 0),
                    "status": "active",
                    "resource_links": [],
                    "author_user_id": world.teacher_memberships[0].user_id,
                },
            )
        )
    return tasks


def build_showcase_homework_tasks(world: World, personas: dict[str, PersonaSelection], as_of: date) -> list[SeedTask]:
    section_index = section_by_code(world)
    kg1_section = section_index.get("KG1 A")
    if kg1_section is None:
        fail("KG1 A section is required for showcase homework seeding")

    subject_codes = [code for code in ("ENG", "MAT", "SCI", "ARA", "ICT", "PE") if any(subject.code == code for subject in world.subjects)]
    if not subject_codes:
        fail("No usable subjects were available for showcase homework seeding")
    kg1_subject_groups = [group for code in subject_codes if (group := subject_group_for_section_and_code(world, kg1_section.id, code)) is not None]
    if not kg1_subject_groups:
        fail("KG1 A subject groups are required for showcase homework seeding")

    tasks: list[SeedTask] = []
    teacher_id = world.teacher_memberships[0].user_id

    # KG1 A gets repeated parent-visible homework across subjects.
    for idx in range(24):
        if idx % 2 == 0:
            tasks.append(
                SeedTask(
                    entity_type="homework_item",
                    entity_key=f"showcase-kg1-class:{idx}",
                    model_name="homework_items",
                    payload={
                        "item_type": "homework",
                        "title": f"KG1 A family task {idx + 1}",
                        "body": "Read the prompt with your child and return a short note.",
                        "audience_type": "class_section",
                        "class_section_id": kg1_section.id,
                        "subject_group_id": None,
                        "due_at": make_time(as_of, -3 + idx, 14, 0),
                        "status": "active",
                        "resource_links": [],
                        "author_user_id": teacher_id,
                    },
                )
            )
        else:
            subject_code = subject_codes[idx % len(subject_codes)]
            subject_group = subject_group_for_section_and_code(world, kg1_section.id, subject_code)
            if subject_group is None:
                continue
            tasks.append(
                SeedTask(
                    entity_type="homework_item",
                    entity_key=f"showcase-kg1-subject:{idx}",
                    model_name="homework_items",
                    payload={
                        "item_type": "homework",
                        "title": f"KG1 A {subject_code} practice {idx + 1}",
                        "body": "Complete the activity sheet and bring it back tomorrow.",
                        "audience_type": "subject_group",
                        "class_section_id": None,
                        "subject_group_id": subject_group.id,
                        "due_at": make_time(as_of, -2 + idx, 14, 0),
                        "status": "active",
                        "resource_links": [],
                        "author_user_id": teacher_id,
                    },
                )
            )

    section_cycle = cycle(sorted(world.sections, key=lambda section: section.id))
    student_cycle = cycle([student for student in world.students if student.status == "active" and student.id not in world.linked_student_ids])
    while len(tasks) < 200:
        student = next(student_cycle)
        section = next(section_cycle)
        subject_code = subject_codes[len(tasks) % len(subject_codes)]
        audience_type = "class_section" if len(tasks) % 3 else "subject_group"
        subject_group = subject_group_for_section_and_code(world, section.id, subject_code)
        if audience_type == "subject_group" and subject_group is None:
            audience_type = "class_section"
        tasks.append(
            SeedTask(
                entity_type="homework_item",
                entity_key=f"showcase-homework:{len(tasks)}",
                model_name="homework_items",
                payload={
                    "item_type": "homework",
                    "title": f"Reporting homework {len(tasks):03d}",
                    "body": f"Support task for {student_name(student)} in {section.name}.",
                    "audience_type": audience_type,
                    "class_section_id": section.id if audience_type == "class_section" else None,
                    "subject_group_id": subject_group.id if audience_type == "subject_group" and subject_group is not None else None,
                    "due_at": make_time(as_of, -14 + (len(tasks) % 30), 15, (len(tasks) * 3) % 60),
                    "status": "active",
                    "resource_links": [],
                    "author_user_id": teacher_id,
                },
            )
        )

    if len(tasks) != 200:
        fail(f"Showcase homework task count mismatch: expected 200, got {len(tasks)}")
    return tasks


def build_announcement_tasks(world: World, personas: dict[str, PersonaSelection], as_of: date) -> list[SeedTask]:
    section_index = section_by_code(world)
    english_section = section_index.get(personas[PERSONA_ENGLISH].class_section_code)
    duty_section = section_index.get(personas[PERSONA_DUTY].class_section_code)
    maths_section = section_index.get(personas[PERSONA_MATHS].class_section_code)
    if english_section is None or duty_section is None or maths_section is None:
        fail("Persona sections could not be resolved for announcement seeding")

    subject_english = subject_group_for_section_and_code(world, english_section.id, "ENG")
    subject_maths = subject_group_for_section_and_code(world, maths_section.id, "MAT")
    subject_science = subject_group_for_section_and_code(world, maths_section.id, "SCI") or subject_group_for_section_and_code(world, english_section.id, "SCI")
    if subject_english is None or subject_maths is None or subject_science is None:
        fail("Could not resolve required announcement subject groups")

    teacher_id = world.teacher_memberships[0].user_id
    specs = [
        ("school", None, None, "Welcome to the demo week", "A short school-wide note for the seeded UIS demo data."),
        ("class_section", english_section.id, None, "G1 A reading focus", "Reading support and classroom routines for the week."),
        ("class_section", duty_section.id, None, "G4 B expectations", "A reminder about class routines and transitions."),
        ("subject_group", None, subject_english.id, "English speaking task", "Practice the speaking task before the lesson."),
        ("subject_group", None, subject_maths.id, "Maths strategy update", "Bring the strategy sheet and check the examples."),
        ("subject_group", None, subject_science.id, "Science lab notice", "Lab safety reminder and materials list."),
    ]
    tasks: list[SeedTask] = []
    for idx, (audience_type, class_section_id, subject_group_id, title, body) in enumerate(specs):
        tasks.append(
            SeedTask(
                entity_type="announcement",
                entity_key=f"announcement:{idx}",
                model_name="announcements",
                payload={
                    "author_user_id": teacher_id,
                    "title": title,
                    "body": body,
                    "audience_type": audience_type,
                    "class_section_id": class_section_id,
                    "subject_group_id": subject_group_id,
                    "status": "published",
                    "created_at": make_time(as_of, -14 + idx * 2, 8, 30),
                },
            )
        )
    return tasks


def build_showcase_announcement_tasks(world: World, personas: dict[str, PersonaSelection], as_of: date) -> list[SeedTask]:
    section_index = section_by_code(world)
    kg1_section = section_index.get("KG1 A")
    if kg1_section is None:
        fail("KG1 A section is required for showcase announcements")

    subject_codes = [code for code in ("ENG", "MAT", "SCI", "ARA", "ICT", "PE") if any(subject.code == code for subject in world.subjects)]
    if not subject_codes:
        fail("No usable subjects were available for showcase announcements")
    kg1_subject_groups = [group for code in subject_codes if (group := subject_group_for_section_and_code(world, kg1_section.id, code)) is not None]
    if not kg1_subject_groups:
        fail("KG1 A subject groups are required for showcase announcements")

    teacher_id = world.teacher_memberships[0].user_id
    tasks: list[SeedTask] = []

    for idx in range(12):
        if idx % 2 == 0:
            tasks.append(
                SeedTask(
                    entity_type="announcement",
                    entity_key=f"showcase-kg1-class:{idx}",
                    model_name="announcements",
                    payload={
                        "author_user_id": teacher_id,
                        "title": f"KG1 A family update {idx + 1}",
                        "body": "A short parent-visible note for KG1 A families.",
                        "audience_type": "class_section",
                        "class_section_id": kg1_section.id,
                        "subject_group_id": None,
                        "status": "published",
                        "created_at": make_time(as_of, -9 + idx, 7, 30),
                    },
                )
            )
        else:
            subject_group = kg1_subject_groups[idx % len(kg1_subject_groups)]
            tasks.append(
                SeedTask(
                    entity_type="announcement",
                    entity_key=f"showcase-kg1-subject:{idx}",
                    model_name="announcements",
                    payload={
                        "author_user_id": teacher_id,
                        "title": f"KG1 A {subject_group.id} subject note {idx + 1}",
                        "body": "A simple note to keep the parent feed useful and current.",
                        "audience_type": "subject_group",
                        "class_section_id": None,
                        "subject_group_id": subject_group.id,
                        "status": "published",
                        "created_at": make_time(as_of, -8 + idx, 8, 15),
                    },
                )
            )

    section_cycle = cycle(sorted(world.sections, key=lambda section: section.id))
    subject_cycle = cycle(subject_codes)
    while len(tasks) < 60:
        section = next(section_cycle)
        subject_code = next(subject_cycle)
        audience_type = "class_section" if len(tasks) % 4 else "subject_group"
        subject_group = subject_group_for_section_and_code(world, section.id, subject_code)
        if audience_type == "subject_group" and subject_group is None:
            audience_type = "class_section"
        tasks.append(
            SeedTask(
                entity_type="announcement",
                entity_key=f"showcase-announcement:{len(tasks)}",
                model_name="announcements",
                payload={
                    "author_user_id": teacher_id,
                    "title": f"School note {len(tasks):03d}",
                    "body": f"Reporting announcement for {section.name} with {subject_code} context.",
                    "audience_type": audience_type,
                    "class_section_id": section.id if audience_type == "class_section" else None,
                    "subject_group_id": subject_group.id if audience_type == "subject_group" and subject_group is not None else None,
                    "status": "published",
                    "created_at": make_time(as_of, -18 + (len(tasks) % 28), 9, (len(tasks) * 2) % 60),
                },
            )
        )

    if len(tasks) != 60:
        fail(f"Showcase announcement task count mismatch: expected 60, got {len(tasks)}")
    return tasks


def build_update_tasks(world: World, personas: dict[str, PersonaSelection], as_of: date) -> list[SeedTask]:
    section_index = section_by_code(world)
    english_section = section_index.get(personas[PERSONA_ENGLISH].class_section_code)
    duty_section = section_index.get(personas[PERSONA_DUTY].class_section_code)
    maths_section = section_index.get(personas[PERSONA_MATHS].class_section_code)
    if english_section is None or duty_section is None or maths_section is None:
        fail("Persona sections could not be resolved for updates")

    subject_english = subject_group_for_section_and_code(world, english_section.id, "ENG")
    subject_maths = subject_group_for_section_and_code(world, maths_section.id, "MAT")
    if subject_english is None or subject_maths is None:
        fail("Could not resolve required update subject groups")

    teacher_id = world.teacher_memberships[0].user_id
    specs = [
        ("class_section", english_section.id, None, "G1 A classroom update", "A quick note from the classroom after a busy lesson."),
        ("class_section", duty_section.id, None, "G4 B class photo update", "A classroom update for the week with a safe placeholder photo if available."),
        ("subject_group", None, subject_english.id, "English group update", "A short subject update for the English group."),
        ("subject_group", None, subject_maths.id, "Maths group update", "A short subject update for the Maths group."),
        ("class_section", maths_section.id, None, "Upper school update", "A general update for the upper school class."),
    ]
    tasks: list[SeedTask] = []
    for idx, (audience_type, class_section_id, subject_group_id, title, body) in enumerate(specs):
        tasks.append(
            SeedTask(
                entity_type="update_post",
                entity_key=f"update:{idx}",
                model_name="update_posts",
                payload={
                    "author_user_id": teacher_id,
                    "body": body,
                    "audience_type": audience_type,
                    "class_section_id": class_section_id,
                    "subject_group_id": subject_group_id,
                    "status": "active",
                    "created_at": make_time(as_of, -10 + idx, 9, 15),
                },
            )
        )
    return tasks


def build_showcase_update_tasks(world: World, personas: dict[str, PersonaSelection], as_of: date) -> list[SeedTask]:
    section_index = section_by_code(world)
    kg1_section = section_index.get("KG1 A")
    if kg1_section is None:
        fail("KG1 A section is required for showcase updates")

    subject_codes = [code for code in ("ENG", "MAT", "SCI", "ARA", "ICT", "PE") if any(subject.code == code for subject in world.subjects)]
    if not subject_codes:
        fail("No usable subjects were available for showcase updates")
    kg1_subject_groups = [group for code in subject_codes if (group := subject_group_for_section_and_code(world, kg1_section.id, code)) is not None]
    if not kg1_subject_groups:
        fail("KG1 A subject groups are required for showcase updates")

    teacher_id = world.teacher_memberships[0].user_id
    tasks: list[SeedTask] = []

    for idx in range(12):
        if idx % 2 == 0:
            tasks.append(
                SeedTask(
                    entity_type="update_post",
                    entity_key=f"showcase-kg1-class:{idx}",
                    model_name="update_posts",
                    payload={
                        "author_user_id": teacher_id,
                        "body": f"KG1 A parent update {idx + 1} with a useful classroom snapshot.",
                        "audience_type": "class_section",
                        "class_section_id": kg1_section.id,
                        "subject_group_id": None,
                        "status": "active",
                        "created_at": make_time(as_of, -7 + idx, 8, 10),
                    },
                )
            )
        else:
            subject_group = kg1_subject_groups[idx % len(kg1_subject_groups)]
            tasks.append(
                SeedTask(
                    entity_type="update_post",
                    entity_key=f"showcase-kg1-subject:{idx}",
                    model_name="update_posts",
                    payload={
                        "author_user_id": teacher_id,
                        "body": f"KG1 A {subject_group.id} subject update for parents.",
                        "audience_type": "subject_group",
                        "class_section_id": None,
                        "subject_group_id": subject_group.id,
                        "status": "active",
                        "created_at": make_time(as_of, -6 + idx, 8, 40),
                    },
                )
            )

    section_cycle = cycle(sorted(world.sections, key=lambda section: section.id))
    subject_cycle = cycle(subject_codes)
    while len(tasks) < 50:
        section = next(section_cycle)
        subject_code = next(subject_cycle)
        subject_group = subject_group_for_section_and_code(world, section.id, subject_code)
        audience_type = "class_section" if len(tasks) % 3 else "subject_group"
        if audience_type == "subject_group" and subject_group is None:
            audience_type = "class_section"
        tasks.append(
            SeedTask(
                entity_type="update_post",
                entity_key=f"showcase-update:{len(tasks)}",
                model_name="update_posts",
                payload={
                    "author_user_id": teacher_id,
                    "body": f"Reporting update {len(tasks):03d} for {section.name}.",
                    "audience_type": audience_type,
                    "class_section_id": section.id if audience_type == "class_section" else None,
                    "subject_group_id": subject_group.id if audience_type == "subject_group" and subject_group is not None else None,
                    "status": "active",
                    "created_at": make_time(as_of, -16 + (len(tasks) % 24), 9, (len(tasks) * 3) % 60),
                },
            )
        )

    if len(tasks) != 50:
        fail(f"Showcase update task count mismatch: expected 50, got {len(tasks)}")
    return tasks


def build_calendar_tasks(world: World, personas: dict[str, PersonaSelection], as_of: date) -> list[SeedTask]:
    section_index = section_by_code(world)
    english_section = section_index.get(personas[PERSONA_ENGLISH].class_section_code)
    duty_section = section_index.get(personas[PERSONA_DUTY].class_section_code)
    maths_section = section_index.get(personas[PERSONA_MATHS].class_section_code)
    if english_section is None or duty_section is None or maths_section is None:
        fail("Persona sections could not be resolved for calendar seeding")

    subject_english = subject_group_for_section_and_code(world, english_section.id, "ENG")
    subject_maths = subject_group_for_section_and_code(world, maths_section.id, "MAT")
    subject_science = subject_group_for_section_and_code(world, maths_section.id, "SCI") or subject_group_for_section_and_code(world, english_section.id, "SCI")
    if subject_english is None or subject_maths is None or subject_science is None:
        fail("Could not resolve required calendar subject groups")

    teacher_id = world.teacher_memberships[0].user_id
    specs = [
        ("school", None, None, "School test window", "A school-wide assessment block.", "test", 3, True),
        ("class_section", english_section.id, None, "Reading trip reminder", "Bring the reading folder for the trip.", "trip", 7, True),
        ("class_section", duty_section.id, None, "Assembly reminder", "Whole-class assembly in the hall.", "reminder", 10, True),
        ("subject_group", None, subject_english.id, "English class event", "A planned English lesson event.", "event", 12, False),
        ("subject_group", None, subject_maths.id, "Maths test", "Maths class test revision session.", "test", 16, True),
        ("school", None, None, "Civvies day", "School civvies day notice.", "civvies", 20, True),
        ("class_section", maths_section.id, None, "Charity reminder", "Bring the approved donation item.", "charity", 24, True),
        ("subject_group", None, subject_science.id, "Science trip", "Science subject trip preparation.", "trip", 28, True),
    ]
    tasks: list[SeedTask] = []
    for idx, (audience_type, class_section_id, subject_group_id, title, body, event_type, day_offset, all_day) in enumerate(specs):
        start = make_time(as_of, day_offset, 8 + (idx % 4), 0)
        end = start + timedelta(hours=1 if not all_day else 2)
        tasks.append(
            SeedTask(
                entity_type="calendar_event",
                entity_key=f"calendar:{idx}",
                model_name="calendar_events",
                payload={
                    "author_user_id": teacher_id,
                    "title": title,
                    "body": body,
                    "event_type": event_type,
                    "audience_type": audience_type,
                    "class_section_id": class_section_id,
                    "subject_group_id": subject_group_id,
                    "starts_at": start,
                    "ends_at": end,
                    "all_day": all_day,
                    "status": "active",
                    "created_at": make_time(as_of, -2 + idx, 7, 45),
                },
            )
        )
    return tasks


def build_showcase_calendar_tasks(world: World, personas: dict[str, PersonaSelection], as_of: date) -> list[SeedTask]:
    section_index = section_by_code(world)
    kg1_section = section_index.get("KG1 A")
    if kg1_section is None:
        fail("KG1 A section is required for showcase calendar seeding")

    subject_codes = [code for code in ("ENG", "MAT", "SCI", "ARA", "ICT", "PE") if any(subject.code == code for subject in world.subjects)]
    if not subject_codes:
        fail("No usable subjects were available for showcase calendar seeding")
    kg1_subject_groups = [group for code in subject_codes if (group := subject_group_for_section_and_code(world, kg1_section.id, code)) is not None]
    if not kg1_subject_groups:
        fail("KG1 A subject groups are required for showcase calendar seeding")

    teacher_id = world.teacher_memberships[0].user_id
    tasks: list[SeedTask] = []

    for idx in range(12):
        if idx % 2 == 0:
            tasks.append(
                SeedTask(
                    entity_type="calendar_event",
                    entity_key=f"showcase-kg1-class:{idx}",
                    model_name="calendar_events",
                    payload={
                        "author_user_id": teacher_id,
                        "title": f"KG1 A planned event {idx + 1}",
                        "body": "A parent-visible KG1 A calendar item.",
                        "event_type": "reminder" if idx % 4 else "event",
                        "audience_type": "class_section",
                        "class_section_id": kg1_section.id,
                        "subject_group_id": None,
                        "starts_at": make_time(as_of, -5 + idx, 8, 0),
                        "ends_at": make_time(as_of, -5 + idx, 9, 0),
                        "all_day": False,
                        "status": "active",
                        "created_at": make_time(as_of, -12 + idx, 7, 45),
                    },
                )
            )
        else:
            subject_group = kg1_subject_groups[idx % len(kg1_subject_groups)]
            tasks.append(
                SeedTask(
                    entity_type="calendar_event",
                    entity_key=f"showcase-kg1-subject:{idx}",
                    model_name="calendar_events",
                    payload={
                        "author_user_id": teacher_id,
                        "title": f"KG1 A subject event {idx + 1}",
                        "body": "A calendar reminder for KG1 A families.",
                        "event_type": "test" if idx % 3 else "trip",
                        "audience_type": "subject_group",
                        "class_section_id": None,
                        "subject_group_id": subject_group.id,
                        "starts_at": make_time(as_of, 2 + idx, 10, 30),
                        "ends_at": make_time(as_of, 2 + idx, 11, 30),
                        "all_day": False,
                        "status": "active",
                        "created_at": make_time(as_of, -11 + idx, 7, 30),
                    },
                )
            )

    section_cycle = cycle(sorted(world.sections, key=lambda section: section.id))
    subject_cycle = cycle(subject_codes)
    event_types = cycle(["event", "test", "reminder", "trip", "civvies", "charity"])
    while len(tasks) < 80:
        section = next(section_cycle)
        subject_code = next(subject_cycle)
        subject_group = subject_group_for_section_and_code(world, section.id, subject_code)
        audience_type = "school" if len(tasks) % 5 == 0 else ("class_section" if len(tasks) % 2 else "subject_group")
        if audience_type == "subject_group" and subject_group is None:
            audience_type = "class_section"
        event_type = next(event_types)
        starts_at = make_time(as_of, -20 + (len(tasks) % 45), 8 + (len(tasks) % 4), 0)
        if len(tasks) % 7 == 0:
            starts_at = make_time(as_of, 5 + (len(tasks) % 18), 9, 30)
        tasks.append(
            SeedTask(
                entity_type="calendar_event",
                entity_key=f"showcase-calendar:{len(tasks)}",
                model_name="calendar_events",
                payload={
                    "author_user_id": teacher_id,
                    "title": f"Reporting calendar item {len(tasks):03d}",
                    "body": f"Calendar report item for {section.name}.",
                    "event_type": event_type,
                    "audience_type": audience_type,
                    "class_section_id": section.id if audience_type == "class_section" else None,
                    "subject_group_id": subject_group.id if audience_type == "subject_group" and subject_group is not None else None,
                    "starts_at": starts_at,
                    "ends_at": starts_at + timedelta(hours=1),
                    "all_day": len(tasks) % 6 == 0,
                    "status": "active",
                    "created_at": make_time(as_of, -18 + (len(tasks) % 26), 7, (len(tasks) * 2) % 60),
                },
            )
        )

    if len(tasks) != 80:
        fail(f"Showcase calendar task count mismatch: expected 80, got {len(tasks)}")
    return tasks


def build_management_behaviour_tasks(
    world: World,
    db,
    personas: dict[str, PersonaSelection],
    pool: list[dict],
    as_of: date,
) -> list[SeedTask]:
    bob, _ = resolve_bob_for_showcase(world, db)
    section_index = section_by_code(world)
    subject_codes = [code for code in ("ENG", "MAT", "SCI", "ARA", "ICT", "PE") if any(subject.code == code for subject in world.subjects)]
    if not subject_codes:
        fail("No usable subjects were available for management seeding")

    kg1_section = section_index.get("KG1 A")
    if kg1_section is None:
        fail("KG1 A section is required for management seeding")

    positive_categories = [category for category in world.behaviour_categories if category.type == "positive" and category.active]
    needs_work_categories = [category for category in world.behaviour_categories if category.type == "needs_work" and category.active]
    if not positive_categories or not needs_work_categories:
        fail("Behaviour categories were not available for management seeding")

    tasks: list[SeedTask] = []
    teacher_cycle = cycle(pool)
    active_students = [student for student in world.students if student.status == "active" and student.id not in world.linked_student_ids]
    active_students.sort(key=lambda student: (student.id != bob.id, student.id))
    if len(active_students) < 450:
        fail("Management seeding requires at least 450 active students in the demo dataset")

    grades = grade_code_map(world)
    section_lookup = {section.id: section for section in world.sections}
    student_section_map = {
        student.id: class_section_for_student(db, student.id)[0]
        for student in active_students
    }
    section_groups: dict[int, list[SubjectGroup]] = defaultdict(list)
    for group in world.subject_groups:
        section_groups[group.class_section_id].append(group)
    for groups in section_groups.values():
        groups.sort(key=lambda group: group.id)

    section_order = [section for section in world.sections if section.status == "active"]
    section_order.sort(key=lambda section: (grades.get(section.grade_level_id, ""), section.code, section.id))

    def next_teacher(class_section_id: int | None = None, subject_group_id: int | None = None) -> User:
        chosen = teacher_for_target(pool, class_section_id=class_section_id, subject_group_id=subject_group_id)
        if chosen is not None:
            return chosen
        return next(teacher_cycle)["user"]

    def category_for(idx: int, positive: bool) -> BehaviourCategory:
        categories = positive_categories if positive else needs_work_categories
        return categories[idx % len(categories)]

    def student_section(student_id: int) -> ClassSection:
        section_id = student_section_map.get(student_id)
        section = section_lookup.get(section_id) if section_id is not None else None
        if section is None:
            fail(f"Could not resolve section for student_id={student_id}")
        return section

    # Bob gets visible but limited coverage.
    bob_subject_groups = [group for group in section_groups.get(kg1_section.id, []) if next((sub for sub in world.subjects if sub.id == group.subject_id), None) is not None]
    if not bob_subject_groups:
        fail("KG1 A subject groups are required for management seeding")
    bob_specs = [
        ("class", kg1_section.id, None, None, category_for(0, True), "KG1 A routine check-in"),
        ("subject", None, bob_subject_groups[0].id, None, category_for(1, True), "KG1 A reading support"),
        ("subject", None, bob_subject_groups[1 % len(bob_subject_groups)].id, None, category_for(2, False), "KG1 A phonics reminder"),
        ("duty", None, None, "break", category_for(3, False), "Break reminder for KG1 A"),
        ("duty", None, None, "playground", category_for(4, True), "Playground safe play"),
        ("class", kg1_section.id, None, None, category_for(5, True), "Back on task in KG1 A"),
        ("subject", None, bob_subject_groups[2 % len(bob_subject_groups)].id, None, category_for(6, True), "KG1 A maths counting"),
        ("duty", None, None, "hallway", category_for(7, False), "Hallway reset"),
        ("subject", None, bob_subject_groups[3 % len(bob_subject_groups)].id, None, category_for(8, True), "KG1 A science observation"),
        ("class", kg1_section.id, None, None, category_for(9, True), "KG1 A positive routine"),
        ("duty", None, None, "assembly", category_for(10, True), "Assembly listening"),
        ("general", None, None, None, category_for(11, True), "General reflection"),
    ]
    for idx, (context_type, class_section_id, subject_group_id, duty_context, category, note) in enumerate(bob_specs):
        teacher = next_teacher(class_section_id=class_section_id or kg1_section.id, subject_group_id=subject_group_id)
        tasks.append(
            event_blueprint(
                key=f"mg-bob:{idx}",
                student_id=bob.id,
                actor_user_id=teacher.id,
                category=category,
                points_delta=category.points_value,
                note=note,
                created_at=make_time(as_of, -54 + idx * 3, 8 + (idx % 4), (idx * 5) % 60),
                context_type="general" if context_type == "general" else context_type,
                class_section_id=class_section_id if context_type == "class" else None,
                subject_group_id=subject_group_id,
                duty_context=duty_context,
            )
        )

    # Extra KG1 A visibility for parent/phone demos.
    kg1_students = [student for student in active_students if student_section(student.id).id == kg1_section.id]
    if len(kg1_students) < 4:
        fail("KG1 A needs several active students for management seeding")

    kg1_subject_cycle = cycle(bob_subject_groups)
    kg1_duty_cycle = cycle(DUTY_CONTEXTS)
    kg1_teacher_cycle = cycle(pool)
    for idx in range(24):
        student = kg1_students[idx % len(kg1_students)]
        if idx < 8:
            teacher = next_teacher(class_section_id=kg1_section.id)
            category = category_for(idx, positive=(idx % 3 != 1))
            tasks.append(
                event_blueprint(
                    key=f"mg-kg1-class:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note="KG1 A classroom routine snapshot" if idx % 2 == 0 else "KG1 A reminder",
                    created_at=make_time(as_of, -48 + idx * 2, 8, 15 + idx),
                    context_type="class",
                    class_section_id=kg1_section.id,
                )
            )
        elif idx < 16:
            group = next(kg1_subject_cycle)
            subject = next((item for item in world.subjects if item.id == group.subject_id), None)
            teacher = next_teacher(class_section_id=kg1_section.id, subject_group_id=group.id)
            category = category_for(idx, positive=True)
            tasks.append(
                event_blueprint(
                    key=f"mg-kg1-subject:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=f"KG1 A {subject.code if subject else 'SUB'} parent update",
                    created_at=make_time(as_of, -46 + idx * 2, 9, 5 + idx),
                    context_type="subject",
                    subject_group_id=group.id,
                )
            )
        else:
            teacher = next_teacher(class_section_id=kg1_section.id)
            duty_context = next(kg1_duty_cycle)
            category = category_for(idx, positive=(idx % 4 != 1))
            tasks.append(
                event_blueprint(
                    key=f"mg-kg1-duty:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=f"KG1 A {DUTY_LABELS[duty_context].lower()} note",
                    created_at=make_time(as_of, -44 + idx * 2, 12, 10 + idx),
                    context_type="duty",
                    duty_context=duty_context,
                )
            )

    eligible_students = [student for student in active_students if student.id != bob.id]
    subject_group_cache: dict[tuple[int, str], SubjectGroup] = {}
    for section in section_order:
        for code in subject_codes:
            group = subject_group_for_section_and_code(world, section.id, code)
            if group is not None:
                subject_group_cache[(section.id, code)] = group
    if not subject_group_cache:
        fail("No subject groups were available for management seeding")

    mode_cycle = ("class", "subject", "duty", "general")
    duty_cycle = cycle(DUTY_CONTEXTS)
    for idx in range(8000 - len(tasks)):
        student = eligible_students[idx % len(eligible_students)]
        section = student_section(student.id)
        mode = mode_cycle[idx % len(mode_cycle)]
        positive = (idx % 7) not in {3, 5}
        category = category_for(idx, positive=positive)
        days_offset = -56 + (idx % 70)
        hour = 7 + (idx % 6)
        minute = (idx * 7) % 60
        if mode == "subject":
            subject_code = subject_codes[idx % len(subject_codes)]
            group = subject_group_cache.get((section.id, subject_code))
            if group is None:
                group = next(iter(subject_group_cache.values()))
            teacher = next_teacher(class_section_id=group.class_section_id, subject_group_id=group.id)
            subject = next((item for item in world.subjects if item.id == group.subject_id), None)
            tasks.append(
                event_blueprint(
                    key=f"mg-subject:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=f"{subject.code if subject else 'SUB'} report {idx:04d}",
                    created_at=make_time(as_of, days_offset, hour, minute),
                    context_type="subject",
                    subject_group_id=group.id,
                )
            )
        elif mode == "class":
            teacher = next_teacher(class_section_id=section.id)
            tasks.append(
                event_blueprint(
                    key=f"mg-class:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=f"Class report for {section.name}",
                    created_at=make_time(as_of, days_offset, hour, minute),
                    context_type="class",
                    class_section_id=section.id,
                )
            )
        elif mode == "duty":
            teacher = next_teacher(class_section_id=section.id)
            duty_context = next(duty_cycle)
            tasks.append(
                event_blueprint(
                    key=f"mg-duty:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=f"{DUTY_LABELS[duty_context]} duty report",
                    created_at=make_time(as_of, days_offset, hour, minute),
                    context_type="duty",
                    duty_context=duty_context,
                )
            )
        else:
            teacher = next_teacher(class_section_id=section.id)
            tasks.append(
                event_blueprint(
                    key=f"mg-general:{idx}",
                    student_id=student.id,
                    actor_user_id=teacher.id,
                    category=category,
                    points_delta=category.points_value,
                    note=f"General trend report {idx:04d}",
                    created_at=make_time(as_of, days_offset, hour, minute),
                    context_type="general",
                )
            )

    if len(tasks) != 8000:
        fail(f"Management behaviour task count mismatch: expected 8000, got {len(tasks)}")
    return tasks


def build_management_homework_tasks(world: World, as_of: date) -> list[SeedTask]:
    section_index = section_by_code(world)
    kg1_section = section_index.get("KG1 A")
    if kg1_section is None:
        fail("KG1 A section is required for management homework seeding")
    subject_codes = [code for code in ("ENG", "MAT", "SCI", "ARA", "ICT", "PE") if any(subject.code == code for subject in world.subjects)]
    if not subject_codes:
        fail("No usable subjects were available for management homework seeding")
    kg1_groups = [group for code in subject_codes if (group := subject_group_for_section_and_code(world, kg1_section.id, code)) is not None]
    if not kg1_groups:
        fail("KG1 A subject groups are required for management homework seeding")

    teacher_id = world.teacher_memberships[0].user_id
    tasks: list[SeedTask] = []
    for idx in range(20):
        if idx % 2 == 0:
            tasks.append(
                SeedTask(
                    entity_type="homework_item",
                    entity_key=f"mg-kg1-homework:{idx}",
                    model_name="homework_items",
                    payload={
                        "item_type": "homework",
                        "title": f"KG1 A family task {idx + 1}",
                        "body": "Read the prompt with your child and return a short note.",
                        "audience_type": "class_section",
                        "class_section_id": kg1_section.id,
                        "subject_group_id": None,
                        "due_at": make_time(as_of, -14 + idx, 14, 0),
                        "status": "active",
                        "resource_links": [],
                        "author_user_id": teacher_id,
                    },
                )
            )
        else:
            group = kg1_groups[idx % len(kg1_groups)]
            subject = next((item for item in world.subjects if item.id == group.subject_id), None)
            tasks.append(
                SeedTask(
                    entity_type="homework_item",
                    entity_key=f"mg-kg1-subject-homework:{idx}",
                    model_name="homework_items",
                    payload={
                        "item_type": "homework",
                        "title": f"KG1 A {subject.code if subject else 'SUB'} practice {idx + 1}",
                        "body": "Complete the activity and bring it back tomorrow.",
                        "audience_type": "subject_group",
                        "class_section_id": None,
                        "subject_group_id": group.id,
                        "due_at": make_time(as_of, -12 + idx, 14, 0),
                        "status": "active",
                        "resource_links": [],
                        "author_user_id": teacher_id,
                    },
                )
            )

    section_cycle = cycle(section for section in world.sections if section.status == "active")
    subject_cycle = cycle(subject_codes)
    student_cycle = cycle(student for student in world.students if student.status == "active" and student.id not in world.linked_student_ids)
    while len(tasks) < 300:
        section = next(section_cycle)
        subject_code = next(subject_cycle)
        student = next(student_cycle)
        audience_type = "class_section" if len(tasks) % 3 else "subject_group"
        group = subject_group_for_section_and_code(world, section.id, subject_code)
        if audience_type == "subject_group" and group is None:
            audience_type = "class_section"
        tasks.append(
            SeedTask(
                entity_type="homework_item",
                entity_key=f"mg-homework:{len(tasks)}",
                model_name="homework_items",
                payload={
                    "item_type": "homework",
                    "title": f"Management homework {len(tasks):03d}",
                    "body": f"Support task for {student_name(student)} in {section.name}.",
                    "audience_type": audience_type,
                    "class_section_id": section.id if audience_type == "class_section" else None,
                    "subject_group_id": group.id if audience_type == "subject_group" and group is not None else None,
                    "due_at": make_time(as_of, -20 + (len(tasks) % 40), 15, (len(tasks) * 3) % 60),
                    "status": "active",
                    "resource_links": [],
                    "author_user_id": teacher_id,
                },
            )
        )

    if len(tasks) != 300:
        fail(f"Management homework task count mismatch: expected 300, got {len(tasks)}")
    return tasks


def build_management_announcement_tasks(world: World, as_of: date) -> list[SeedTask]:
    section_index = section_by_code(world)
    kg1_section = section_index.get("KG1 A")
    if kg1_section is None:
        fail("KG1 A section is required for management announcements")
    subject_codes = [code for code in ("ENG", "MAT", "SCI", "ARA", "ICT", "PE") if any(subject.code == code for subject in world.subjects)]
    if not subject_codes:
        fail("No usable subjects were available for management announcements")
    kg1_groups = [group for code in subject_codes if (group := subject_group_for_section_and_code(world, kg1_section.id, code)) is not None]
    if not kg1_groups:
        fail("KG1 A subject groups are required for management announcements")

    teacher_id = world.teacher_memberships[0].user_id
    tasks: list[SeedTask] = []
    for idx in range(15):
        if idx % 2 == 0:
            tasks.append(
                SeedTask(
                    entity_type="announcement",
                    entity_key=f"mg-kg1-announcement:{idx}",
                    model_name="announcements",
                    payload={
                        "author_user_id": teacher_id,
                        "title": f"KG1 A family update {idx + 1}",
                        "body": "A short parent-visible note for KG1 A families.",
                        "audience_type": "class_section",
                        "class_section_id": kg1_section.id,
                        "subject_group_id": None,
                        "status": "published",
                        "created_at": make_time(as_of, -10 + idx, 7, 30),
                    },
                )
            )
        else:
            group = kg1_groups[idx % len(kg1_groups)]
            subject = next((item for item in world.subjects if item.id == group.subject_id), None)
            tasks.append(
                SeedTask(
                    entity_type="announcement",
                    entity_key=f"mg-kg1-subject-announcement:{idx}",
                    model_name="announcements",
                    payload={
                        "author_user_id": teacher_id,
                        "title": f"KG1 A {subject.code if subject else 'SUB'} note {idx + 1}",
                        "body": "A simple note to keep the parent feed useful and current.",
                        "audience_type": "subject_group",
                        "class_section_id": None,
                        "subject_group_id": group.id,
                        "status": "published",
                        "created_at": make_time(as_of, -9 + idx, 8, 15),
                    },
                )
            )

    section_cycle = cycle(section for section in world.sections if section.status == "active")
    subject_cycle = cycle(subject_codes)
    while len(tasks) < 100:
        section = next(section_cycle)
        subject_code = next(subject_cycle)
        group = subject_group_for_section_and_code(world, section.id, subject_code)
        audience_type = "class_section" if len(tasks) % 4 else "subject_group"
        if audience_type == "subject_group" and group is None:
            audience_type = "class_section"
        tasks.append(
            SeedTask(
                entity_type="announcement",
                entity_key=f"mg-announcement:{len(tasks)}",
                model_name="announcements",
                payload={
                    "author_user_id": teacher_id,
                    "title": f"Management note {len(tasks):03d}",
                    "body": f"Reporting announcement for {section.name} with {subject_code} context.",
                    "audience_type": audience_type,
                    "class_section_id": section.id if audience_type == "class_section" else None,
                    "subject_group_id": group.id if audience_type == "subject_group" and group is not None else None,
                    "status": "published",
                    "created_at": make_time(as_of, -18 + (len(tasks) % 35), 9, (len(tasks) * 2) % 60),
                },
            )
        )

    if len(tasks) != 100:
        fail(f"Management announcement task count mismatch: expected 100, got {len(tasks)}")
    return tasks


def build_management_update_tasks(world: World, as_of: date) -> list[SeedTask]:
    section_index = section_by_code(world)
    kg1_section = section_index.get("KG1 A")
    if kg1_section is None:
        fail("KG1 A section is required for management updates")
    subject_codes = [code for code in ("ENG", "MAT", "SCI", "ARA", "ICT", "PE") if any(subject.code == code for subject in world.subjects)]
    if not subject_codes:
        fail("No usable subjects were available for management updates")
    kg1_groups = [group for code in subject_codes if (group := subject_group_for_section_and_code(world, kg1_section.id, code)) is not None]
    if not kg1_groups:
        fail("KG1 A subject groups are required for management updates")

    teacher_id = world.teacher_memberships[0].user_id
    tasks: list[SeedTask] = []
    for idx in range(20):
        if idx % 2 == 0:
            tasks.append(
                SeedTask(
                    entity_type="update_post",
                    entity_key=f"mg-kg1-update:{idx}",
                    model_name="update_posts",
                    payload={
                        "author_user_id": teacher_id,
                        "body": f"KG1 A parent update {idx + 1} with a useful classroom snapshot.",
                        "audience_type": "class_section",
                        "class_section_id": kg1_section.id,
                        "subject_group_id": None,
                        "status": "active",
                        "created_at": make_time(as_of, -8 + idx, 8, 10),
                    },
                )
            )
        else:
            group = kg1_groups[idx % len(kg1_groups)]
            subject = next((item for item in world.subjects if item.id == group.subject_id), None)
            tasks.append(
                SeedTask(
                    entity_type="update_post",
                    entity_key=f"mg-kg1-subject-update:{idx}",
                    model_name="update_posts",
                    payload={
                        "author_user_id": teacher_id,
                        "body": f"KG1 A {subject.code if subject else 'SUB'} subject update for parents.",
                        "audience_type": "subject_group",
                        "class_section_id": None,
                        "subject_group_id": group.id,
                        "status": "active",
                        "created_at": make_time(as_of, -7 + idx, 8, 40),
                    },
                )
            )

    section_cycle = cycle(section for section in world.sections if section.status == "active")
    subject_cycle = cycle(subject_codes)
    while len(tasks) < 100:
        section = next(section_cycle)
        subject_code = next(subject_cycle)
        group = subject_group_for_section_and_code(world, section.id, subject_code)
        audience_type = "class_section" if len(tasks) % 3 else "subject_group"
        if audience_type == "subject_group" and group is None:
            audience_type = "class_section"
        tasks.append(
            SeedTask(
                entity_type="update_post",
                entity_key=f"mg-update:{len(tasks)}",
                model_name="update_posts",
                payload={
                    "author_user_id": teacher_id,
                    "body": f"Management update {len(tasks):03d} for {section.name}.",
                    "audience_type": audience_type,
                    "class_section_id": section.id if audience_type == "class_section" else None,
                    "subject_group_id": group.id if audience_type == "subject_group" and group is not None else None,
                    "status": "active",
                    "created_at": make_time(as_of, -16 + (len(tasks) % 32), 9, (len(tasks) * 3) % 60),
                },
            )
        )

    if len(tasks) != 100:
        fail(f"Management update task count mismatch: expected 100, got {len(tasks)}")
    return tasks


def build_management_calendar_tasks(world: World, as_of: date) -> list[SeedTask]:
    section_index = section_by_code(world)
    kg1_section = section_index.get("KG1 A")
    if kg1_section is None:
        fail("KG1 A section is required for management calendar events")
    subject_codes = [code for code in ("ENG", "MAT", "SCI", "ARA", "ICT", "PE") if any(subject.code == code for subject in world.subjects)]
    if not subject_codes:
        fail("No usable subjects were available for management calendar events")
    kg1_groups = [group for code in subject_codes if (group := subject_group_for_section_and_code(world, kg1_section.id, code)) is not None]
    if not kg1_groups:
        fail("KG1 A subject groups are required for management calendar events")

    teacher_id = world.teacher_memberships[0].user_id
    tasks: list[SeedTask] = []
    for idx in range(20):
        if idx % 2 == 0:
            tasks.append(
                SeedTask(
                    entity_type="calendar_event",
                    entity_key=f"mg-kg1-calendar:{idx}",
                    model_name="calendar_events",
                    payload={
                        "author_user_id": teacher_id,
                        "title": f"KG1 A planned event {idx + 1}",
                        "body": "A parent-visible KG1 A calendar item.",
                        "event_type": "reminder" if idx % 4 else "event",
                        "audience_type": "class_section",
                        "class_section_id": kg1_section.id,
                        "subject_group_id": None,
                        "starts_at": make_time(as_of, -6 + idx, 8, 0),
                        "ends_at": make_time(as_of, -6 + idx, 9, 0),
                        "all_day": False,
                        "status": "active",
                        "created_at": make_time(as_of, -12 + idx, 7, 45),
                    },
                )
            )
        else:
            group = kg1_groups[idx % len(kg1_groups)]
            subject = next((item for item in world.subjects if item.id == group.subject_id), None)
            tasks.append(
                SeedTask(
                    entity_type="calendar_event",
                    entity_key=f"mg-kg1-subject-calendar:{idx}",
                    model_name="calendar_events",
                    payload={
                        "author_user_id": teacher_id,
                        "title": f"KG1 A {subject.code if subject else 'SUB'} event {idx + 1}",
                        "body": "A calendar reminder for KG1 A families.",
                        "event_type": "test" if idx % 3 else "trip",
                        "audience_type": "subject_group",
                        "class_section_id": None,
                        "subject_group_id": group.id,
                        "starts_at": make_time(as_of, 2 + idx, 10, 30),
                        "ends_at": make_time(as_of, 2 + idx, 11, 30),
                        "all_day": False,
                        "status": "active",
                        "created_at": make_time(as_of, -11 + idx, 7, 30),
                    },
                )
            )

    section_cycle = cycle(section for section in world.sections if section.status == "active")
    subject_cycle = cycle(subject_codes)
    event_types = cycle(["event", "test", "reminder", "trip", "civvies", "charity"])
    while len(tasks) < 120:
        section = next(section_cycle)
        subject_code = next(subject_cycle)
        group = subject_group_for_section_and_code(world, section.id, subject_code)
        audience_type = "school" if len(tasks) % 5 == 0 else ("class_section" if len(tasks) % 2 else "subject_group")
        if audience_type == "subject_group" and group is None:
            audience_type = "class_section"
        event_type = next(event_types)
        starts_at = make_time(as_of, -24 + (len(tasks) % 60), 8 + (len(tasks) % 4), 0)
        if len(tasks) % 7 == 0:
            starts_at = make_time(as_of, 5 + (len(tasks) % 18), 9, 30)
        tasks.append(
            SeedTask(
                entity_type="calendar_event",
                entity_key=f"mg-calendar:{len(tasks)}",
                model_name="calendar_events",
                payload={
                    "author_user_id": teacher_id,
                    "title": f"Management calendar item {len(tasks):03d}",
                    "body": f"Calendar report item for {section.name}.",
                    "event_type": event_type,
                    "audience_type": audience_type,
                    "class_section_id": section.id if audience_type == "class_section" else None,
                    "subject_group_id": group.id if audience_type == "subject_group" and group is not None else None,
                    "starts_at": starts_at,
                    "ends_at": starts_at + timedelta(hours=1),
                    "all_day": len(tasks) % 6 == 0,
                    "status": "active",
                    "created_at": make_time(as_of, -18 + (len(tasks) % 30), 7, (len(tasks) * 2) % 60),
                },
            )
        )

    if len(tasks) != 120:
        fail(f"Management calendar task count mismatch: expected 120, got {len(tasks)}")
    return tasks


def load_manifest_assets() -> tuple[list[dict], str | None]:
    return maybe_load_photo_assets()


def build_photo_tasks(world: World, updates: list[UpdatePost], assets: list[dict], as_of: date) -> list[SeedTask]:
    if not assets:
        return []
    teacher_id = world.teacher_memberships[0].user_id
    tasks: list[SeedTask] = []
    for idx, update in enumerate(updates[: min(5, len(assets))]):
        asset = assets[idx]
        storage_key = asset.get("storage_key")
        original_filename = asset.get("original_filename")
        content_type = asset.get("content_type")
        size_bytes = asset.get("size_bytes")
        if not all([storage_key, original_filename, content_type, size_bytes]):
            continue
        tasks.append(
            SeedTask(
                entity_type="update_photo",
                entity_key=f"photo:{idx}",
                model_name="update_photos",
                payload={
                    "post_id": update.id,
                    "school_id": world.school.id,
                    "uploaded_by_user_id": teacher_id,
                    "original_filename": original_filename,
                    "storage_key": storage_key,
                    "content_type": content_type,
                    "size_bytes": int(size_bytes),
                    "created_at": make_time(as_of, idx, 9, 5),
                },
            )
        )
    return tasks


def manifest_row(db, *, seed_namespace: str, entity_type: str, entity_key: str) -> DemoSeedRecord | None:
    return (
        db.query(DemoSeedRecord)
        .filter(
            DemoSeedRecord.seed_namespace == seed_namespace,
            DemoSeedRecord.entity_type == entity_type,
            DemoSeedRecord.entity_key == entity_key,
        )
        .one_or_none()
    )


def persist_task(
    db,
    task: SeedTask,
    *,
    apply: bool,
    counts: Counter,
    school_id: int | None = None,
    seed_namespace: str = SEED_NAMESPACE,
) -> int | None:
    existing = manifest_row(db, seed_namespace=seed_namespace, entity_type=task.entity_type, entity_key=task.entity_key)
    if existing is not None and existing.model_id is not None:
        counts["already_present"] += 1
        return existing.model_id

    model_map = {
        "behaviour_events": BehaviourEvent,
        "homework_items": HomeworkItem,
        "announcements": Announcement,
        "update_posts": UpdatePost,
        "update_photos": UpdatePhoto,
        "calendar_events": CalendarEvent,
    }
    model_cls = model_map[task.model_name]
    payload = dict(task.payload)
    if school_id is not None and "school_id" not in payload:
        payload["school_id"] = school_id
    obj = model_cls(**payload)
    db.add(obj)
    db.flush()
    counts["created"] += 1

    manifest_payload = {
        "task": task.entity_type,
        "key": task.entity_key,
        "payload": {
            key: (value.isoformat() if isinstance(value, datetime) else value)
            for key, value in task.payload.items()
            if key not in {"created_at"}
        },
    }
    if apply:
        if existing is None:
            existing = DemoSeedRecord(
                seed_namespace=seed_namespace,
                entity_type=task.entity_type,
                entity_key=task.entity_key,
                model_name=task.model_name,
                model_id=obj.id,
                metadata_json=manifest_payload,
            )
            db.add(existing)
        else:
            existing.model_name = task.model_name
            existing.model_id = obj.id
            existing.metadata_json = manifest_payload
    return obj.id


def seed_namespace_for_scale(scale: str) -> str:
    if scale == SCALE_DEMO:
        return SEED_NAMESPACE
    if scale == SCALE_SHOWCASE:
        return SHOWCASE_SEED_NAMESPACE
    if scale == SCALE_MANAGEMENT:
        return MANAGEMENT_SEED_NAMESPACE
    fail(f"Unsupported scale {scale!r}")


def seed_school(db, *, school_slug: str, as_of: date, apply: bool, scale: str = SCALE_DEMO) -> RunSummary:
    world = load_world(db, school_slug)
    personas = select_personas(world, db)
    pool = teacher_pool(world, db)
    seed_namespace = seed_namespace_for_scale(scale)
    counts: Counter = Counter()
    skipped_photos_reason = None

    try:
        if scale == SCALE_SHOWCASE:
            behaviour_tasks = build_showcase_behaviour_tasks(world, db, personas, pool, as_of)
            homework_tasks = build_showcase_homework_tasks(world, personas, as_of)
            announcement_tasks = build_showcase_announcement_tasks(world, personas, as_of)
            update_tasks = build_showcase_update_tasks(world, personas, as_of)
            calendar_tasks = build_showcase_calendar_tasks(world, personas, as_of)
        elif scale == SCALE_MANAGEMENT:
            behaviour_tasks = build_management_behaviour_tasks(world, db, personas, pool, as_of)
            homework_tasks = build_management_homework_tasks(world, as_of)
            announcement_tasks = build_management_announcement_tasks(world, as_of)
            update_tasks = build_management_update_tasks(world, as_of)
            calendar_tasks = build_management_calendar_tasks(world, as_of)
        else:
            behaviour_tasks = build_behaviour_tasks(world, db, personas, pool, as_of)
            homework_tasks = build_homework_tasks(world, personas, as_of)
            announcement_tasks = build_announcement_tasks(world, personas, as_of)
            update_tasks = build_update_tasks(world, personas, as_of)
            calendar_tasks = build_calendar_tasks(world, personas, as_of)

        asset_manifest, skipped_photos_reason = load_manifest_assets()
        if not asset_manifest:
            counts["skipped_photos"] += len(update_tasks)
        elif len(asset_manifest) < len(update_tasks):
            counts["skipped_photos"] += len(update_tasks) - len(asset_manifest)

        # Seed in a stable order so dependencies are available for later rows.
        persisted_updates: list[UpdatePost] = []
        for task in behaviour_tasks + homework_tasks + announcement_tasks:
            persist_task(db, task, apply=apply, counts=counts, school_id=world.school.id, seed_namespace=seed_namespace)
        for task in update_tasks:
            update_id = persist_task(db, task, apply=apply, counts=counts, school_id=world.school.id, seed_namespace=seed_namespace)
            if update_id is not None:
                persisted_updates.append(UpdatePost(id=update_id))
        if asset_manifest:
            photo_tasks = build_photo_tasks(world, persisted_updates, asset_manifest, as_of)
            for task in photo_tasks:
                persist_task(db, task, apply=apply, counts=counts, school_id=world.school.id, seed_namespace=seed_namespace)
        for task in calendar_tasks:
            persist_task(db, task, apply=apply, counts=counts, school_id=world.school.id, seed_namespace=seed_namespace)

        db.flush()
        if apply:
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()
        raise

    return RunSummary(
        mode="apply" if apply else "dry-run",
        scale=scale,
        school_slug=world.school.slug,
        school_name=world.school.name,
        as_of=as_of,
        personas=personas,
        counts=counts,
        skipped_photos_reason=skipped_photos_reason,
    )


def print_summary(summary: RunSummary) -> None:
    print(f"Mode: {summary.mode}")
    print(f"Scale: {summary.scale}")
    print(f"Target school: {summary.school_name} ({summary.school_slug})")
    print(f"As-of date: {summary.as_of.isoformat()}")
    print("Persona mapping:")
    for label, selection in summary.personas.items():
        print(
            f"  - {label}: {selection.student_name} [student_id={selection.student_id}] "
            f"in {selection.class_section_code}"
        )
    print(f"Would create / created: {summary.counts['created']}")
    print(f"Already present: {summary.counts['already_present']}")
    print(f"Skipped photos: {summary.counts['skipped_photos']}")
    if summary.skipped_photos_reason:
        print(f"Photo note: {summary.skipped_photos_reason}")
    print("No messaging, auth, guardian-link, or FHH-link data was touched.")


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        as_of = parse_as_of(args.as_of)
        if args.school_slug != DEFAULT_SCHOOL_SLUG:
            fail(f"Only {DEFAULT_SCHOOL_SLUG!r} is supported by this seeder")
        require_write_guards(args)

        db = SessionLocal()
        try:
            summary = seed_school(db, school_slug=args.school_slug, as_of=as_of, apply=args.apply, scale=args.scale)
            print_summary(summary)
            if not args.apply:
                print("DRY RUN: rolled back, no changes were committed.")
            return 0
        finally:
            db.close()
    except SeedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

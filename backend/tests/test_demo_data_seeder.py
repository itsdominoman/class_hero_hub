import os
import sys
from datetime import datetime, timezone
from importlib import util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, inspect, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

from app import auth, database  # noqa: E402
from app.database import Base  # noqa: E402
from app.models_school import (  # noqa: E402
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
    GuardianLink,
    FhhLink,
    FhhLinkInvite,
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
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "seed_realistic_demo_school.py"

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
database.engine = engine
database.SessionLocal = TestingSessionLocal


def load_module():
    spec = util.spec_from_file_location("seed_realistic_demo_school", SCRIPT_PATH)
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.SessionLocal = TestingSessionLocal
    return module


module = load_module()


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def create_category(db, category_type: str, label: str, points_value: int, sort_order: int = 0) -> BehaviourCategory:
    category = BehaviourCategory(
        school_id=1,
        type=category_type,
        label=label,
        points_value=points_value,
        sort_order=sort_order,
        active=True,
    )
    db.add(category)
    return category


def build_world(db):
    school = School(name="United International School", slug="united-international-school", status="pending_setup")
    db.add(school)
    db.flush()

    year = AcademicYear(school_id=school.id, code="2026-27", name="2026/27", status="active", is_current=True, sort_order=1)
    branch = BranchCampus(school_id=school.id, code="MAIN", name="Main Branch", status="active", sort_order=1)
    db.add_all([year, branch])
    db.flush()

    grades = [
        GradeLevel(school_id=school.id, code="G1", name="Grade 1", status="active", sort_order=1),
        GradeLevel(school_id=school.id, code="G4", name="Grade 4", status="active", sort_order=4),
        GradeLevel(school_id=school.id, code="G10", name="Grade 10", status="active", sort_order=10),
    ]
    db.add_all(grades)
    db.flush()

    sections = {}
    for grade in grades:
        for section_code in ("A", "B"):
            section = ClassSection(
                school_id=school.id,
                branch_campus_id=branch.id,
                academic_year_id=year.id,
                grade_level_id=grade.id,
                code=section_code,
                name=f"{grade.name} {section_code}",
                status="active",
                sort_order=1 if section_code == "A" else 2,
            )
            db.add(section)
            db.flush()
            sections[f"{grade.code} {section_code}"] = section

    subjects = {}
    for order, (code, name) in enumerate((("ENG", "English"), ("MAT", "Maths"), ("SCI", "Science")), start=1):
        subject = Subject(school_id=school.id, code=code, name=name, status="active", sort_order=order)
        db.add(subject)
        db.flush()
        subjects[code] = subject

    teachers = []
    for idx, name in enumerate(("Alice Teacher", "Ben Teacher", "Cara Teacher"), start=1):
        user = User(email=f"teacher{idx}@demo.test", name=name, status="active")
        db.add(user)
        db.flush()
        membership = Membership(school_id=school.id, user_id=user.id, role="teacher", status="active")
        db.add(membership)
        db.flush()
        teachers.append((user, membership))

    section_teacher_map = {
        "G1 A": teachers[0],
        "G1 B": teachers[0],
        "G4 A": teachers[1],
        "G4 B": teachers[1],
        "G10 A": teachers[2],
        "G10 B": teachers[2],
    }

    for section_code, (user, membership) in section_teacher_map.items():
        section = sections[section_code]
        db.add(
            StaffAssignment(
                school_id=school.id,
                membership_id=membership.id,
                class_section_id=section.id,
                role="homeroom",
                valid_from=year.start_date or datetime.now(timezone.utc).date(),
            )
        )
        for subject in subjects.values():
            group = SubjectGroup(
                school_id=school.id,
                academic_year_id=year.id,
                class_section_id=section.id,
                subject_id=subject.id,
                code=f"{section_code.replace(' ', '')}-{subject.code}",
                name=f"{section.name} {subject.name}",
                status="active",
                enrolment_policy="default_for_section",
            )
            db.add(group)
            db.flush()
            db.add(
                StaffAssignment(
                    school_id=school.id,
                    membership_id=membership.id,
                    subject_group_id=group.id,
                    role="subject",
                    valid_from=year.start_date or datetime.now(timezone.utc).date(),
                )
            )
    db.flush()

    bob = Student(school_id=school.id, first_name="Bob", last_name="Smith", status="active")
    db.add(bob)
    db.flush()
    db.add(Enrolment(school_id=school.id, student_id=bob.id, class_section_id=sections["G1 A"].id, kind="member"))
    guardian = User(email="guardian1@demo.test", name="Guardian One", status="active")
    db.add(guardian)
    db.flush()
    db.add(GuardianLink(school_id=school.id, student_id=bob.id, user_id=guardian.id, status="active"))

    linked = Student(school_id=school.id, first_name="Jill", last_name="White", status="active")
    db.add(linked)
    db.flush()
    db.add(Enrolment(school_id=school.id, student_id=linked.id, class_section_id=sections["G4 B"].id, kind="member"))
    guardian2 = User(email="guardian2@demo.test", name="Guardian Two", status="active")
    db.add(guardian2)
    db.flush()
    db.add(GuardianLink(school_id=school.id, student_id=linked.id, user_id=guardian2.id, status="active"))

    student_specs = [
        ("Alice", "Jones", "G1 A"),
        ("Ivy", "Stone", "G1 A"),
        ("Charlie", "Brown", "G1 B"),
        ("Jack", "Hill", "G1 B"),
        ("Dana", "White", "G4 A"),
        ("Kira", "Ray", "G4 A"),
        ("Ethan", "Black", "G4 B"),
        ("Leo", "Moss", "G4 B"),
        ("Farah", "Green", "G10 A"),
        ("Mia", "Ross", "G10 A"),
        ("Grace", "Lee", "G10 B"),
        ("Noah", "West", "G10 B"),
    ]
    for first_name, last_name, section_code in student_specs:
        student = Student(school_id=school.id, first_name=first_name, last_name=last_name, status="active")
        db.add(student)
        db.flush()
        db.add(Enrolment(school_id=school.id, student_id=student.id, class_section_id=sections[section_code].id, kind="member"))

    categories = [
        ("positive", "Good work", 1),
        ("positive", "Great effort", 1),
        ("positive", "Participation", 1),
        ("positive", "Listening well", 1),
        ("positive", "Kindness", 1),
        ("positive", "Responsible behaviour", 1),
        ("positive", "Leadership", 1),
        ("positive", "Above and beyond", 2),
        ("positive", "Safe play", 1),
        ("positive", "Helping at break", 1),
        ("positive", "Teamwork", 1),
        ("positive", "Respectful behaviour", 1),
        ("positive", "Improvement", 1),
        ("positive", "Good sportsmanship", 1),
        ("needs_work", "Homework incomplete", -1),
        ("needs_work", "Forgot equipment", -1),
        ("needs_work", "Not following instructions", -1),
        ("needs_work", "Off-task", -1),
        ("needs_work", "Wandering halls", -1),
        ("needs_work", "Late for class", -1),
        ("needs_work", "Unsafe play", -1),
        ("needs_work", "Disrespect", -1),
        ("needs_work", "Running indoors", -1),
        ("needs_work", "Out of bounds", -1),
        ("needs_work", "Leaving area without permission", -1),
        ("needs_work", "Not listening", -1),
        ("needs_work", "Unsafe behaviour", -1),
    ]
    for sort_order, (category_type, label, points_value) in enumerate(categories):
        db.add(
            BehaviourCategory(
                school_id=school.id,
                type=category_type,
                label=label,
                points_value=points_value,
                sort_order=sort_order,
                active=True,
            )
        )

    manual_announcement = Announcement(
        school_id=school.id,
        author_user_id=teachers[0][0].id,
        title="Manual announcement",
        body="Manual test data that should not be modified.",
        audience_type="school",
        status="published",
    )
    db.add(manual_announcement)
    db.commit()

    return {
        "school": school,
        "year": year,
        "sections": sections,
        "subjects": subjects,
        "teachers": teachers,
        "bob": bob,
        "linked": linked,
        "manual_announcement_id": manual_announcement.id,
    }


def build_showcase_world(db):
    base = build_world(db)
    school = base["school"]
    year = base["year"]
    sections = base["sections"]
    teachers = base["teachers"]
    bob = base["bob"]

    kg_grade = GradeLevel(school_id=school.id, code="KG1", name="Kindergarten 1", status="active", sort_order=0)
    db.add(kg_grade)
    db.flush()
    kg_section = ClassSection(
        school_id=school.id,
        branch_campus_id=next(iter(sections.values())).branch_campus_id,
        academic_year_id=year.id,
        grade_level_id=kg_grade.id,
        code="A",
        name="KG1 A",
        status="active",
        sort_order=0,
    )
    db.add(kg_section)
    db.flush()
    sections["KG1 A"] = kg_section

    extra_subjects = {}
    for order, (code, name) in enumerate((("ARA", "Arabic"), ("ICT", "ICT"), ("PE", "PE")), start=10):
        subject = Subject(school_id=school.id, code=code, name=name, status="active", sort_order=order)
        db.add(subject)
        db.flush()
        extra_subjects[code] = subject

    kg_teacher = User(email="teacher4@demo.test", name="Dana Teacher", status="active")
    db.add(kg_teacher)
    db.flush()
    kg_membership = Membership(school_id=school.id, user_id=kg_teacher.id, role="teacher", status="active")
    db.add(kg_membership)
    db.flush()
    teachers.append((kg_teacher, kg_membership))

    db.add(
        StaffAssignment(
            school_id=school.id,
            membership_id=kg_membership.id,
            class_section_id=kg_section.id,
            role="homeroom",
            valid_from=year.start_date or datetime.now(timezone.utc).date(),
        )
    )

    for subject in list(extra_subjects.values()) + list(base["subjects"].values()):
        group = SubjectGroup(
            school_id=school.id,
            academic_year_id=year.id,
            class_section_id=kg_section.id,
            subject_id=subject.id,
            code=f"KG1A-{subject.code}",
            name=f"KG1 A {subject.name}",
            status="active",
            enrolment_policy="default_for_section",
        )
        db.add(group)
        db.flush()
        db.add(
            StaffAssignment(
                school_id=school.id,
                membership_id=kg_membership.id,
                subject_group_id=group.id,
                role="subject",
                valid_from=year.start_date or datetime.now(timezone.utc).date(),
            )
        )

    bob_enrolment = db.query(Enrolment).filter(Enrolment.student_id == bob.id, Enrolment.kind == "member").one()
    bob_enrolment.class_section_id = kg_section.id

    invite = FhhLinkInvite(
        school_id=school.id,
        student_id=bob.id,
        token_hash="bob-fhh-invite-hash",
        display_code_last4="1234",
        created_by_user_id=teachers[0][0].id,
    )
    db.add(invite)
    db.flush()
    db.add(
        FhhLink(
            school_id=school.id,
            student_id=bob.id,
            source_invite_id=invite.id,
            link_token_hash="bob-fhh-link-hash",
            fhh_child_ref="child-bob-smith",
            status="active",
        )
    )

    for first_name, last_name in (("Mila", "Stone"), ("Noor", "Ali"), ("Omar", "Hassan")):
        student = Student(school_id=school.id, first_name=first_name, last_name=last_name, status="active")
        db.add(student)
        db.flush()
        db.add(Enrolment(school_id=school.id, student_id=student.id, class_section_id=kg_section.id, kind="member"))

    base["subjects"].update(extra_subjects)
    db.commit()
    return {**base, "kg_section": kg_section, "kg_teacher": kg_teacher}


def build_management_world(db):
    base = build_showcase_world(db)
    school = base["school"]
    year = base["year"]
    sections = base["sections"]

    extra_subjects = {}
    for order, (code, name) in enumerate((("ARA", "Arabic"), ("ICT", "ICT"), ("PE", "PE")), start=20):
        if code in base["subjects"]:
            continue
        subject = Subject(school_id=school.id, code=code, name=name, status="active", sort_order=order)
        db.add(subject)
        db.flush()
        extra_subjects[code] = subject
    base["subjects"].update(extra_subjects)

    teacher_by_grade = {
        "KG1": base["teachers"][-1][1],
        "G1": base["teachers"][0][1],
        "G4": base["teachers"][1][1],
        "G10": base["teachers"][2][1],
    }

    for section_code, section in sections.items():
        grade_prefix = section_code.split(" ", 1)[0]
        membership = teacher_by_grade.get(grade_prefix, base["teachers"][0][1])
        for subject in base["subjects"].values():
            exists = (
                db.query(SubjectGroup)
                .filter(
                    SubjectGroup.school_id == school.id,
                    SubjectGroup.class_section_id == section.id,
                    SubjectGroup.subject_id == subject.id,
                )
                .count()
            )
            if exists:
                continue
            group = SubjectGroup(
                school_id=school.id,
                academic_year_id=year.id,
                class_section_id=section.id,
                subject_id=subject.id,
                code=f"{section_code.replace(' ', '')}-{subject.code}",
                name=f"{section.name} {subject.name}",
                status="active",
                enrolment_policy="default_for_section",
            )
            db.add(group)
            db.flush()
            db.add(
                StaffAssignment(
                    school_id=school.id,
                    membership_id=membership.id,
                    subject_group_id=group.id,
                    role="subject",
                    valid_from=year.start_date or datetime.now(timezone.utc).date(),
                )
            )

    section_codes = list(sections.keys())
    for idx in range(70 * len(section_codes)):
        section_code = section_codes[idx % len(section_codes)]
        student = Student(
            school_id=school.id,
            first_name=f"Mgmt{idx:03d}",
            last_name=section_code.replace(" ", ""),
            status="active",
        )
        db.add(student)
        db.flush()
        db.add(Enrolment(school_id=school.id, student_id=student.id, class_section_id=sections[section_code].id, kind="member"))

    db.commit()
    return base


def current_counts(db):
    return {
        "behaviour_events": db.query(BehaviourEvent).count(),
        "announcements": db.query(Announcement).count(),
        "homework_items": db.query(HomeworkItem).count(),
        "update_posts": db.query(UpdatePost).count(),
        "update_photos": db.query(UpdatePhoto).count(),
        "calendar_events": db.query(CalendarEvent).count(),
        "demo_seed_records": db.query(DemoSeedRecord).count(),
    }


def namespace_counts(db, namespace: str):
    return {
        row[0]: row[1]
        for row in db.query(DemoSeedRecord.entity_type, func.count(DemoSeedRecord.id))
        .filter(DemoSeedRecord.seed_namespace == namespace)
        .group_by(DemoSeedRecord.entity_type)
        .all()
    }


def demo_seed_record_total(db, namespace: str) -> int:
    return db.query(DemoSeedRecord).filter(DemoSeedRecord.seed_namespace == namespace).count()


@pytest.fixture
def world(db):
    return build_world(db)


def test_dry_run_rolls_back_without_commit(db, world, monkeypatch):
    commit_calls = {"count": 0}
    rollback_calls = {"count": 0}
    original_rollback = db.rollback

    monkeypatch.setattr(db, "commit", lambda: (_ for _ in ()).throw(AssertionError("commit should not be called in dry-run")))

    def rollback_wrapper():
        rollback_calls["count"] += 1
        return original_rollback()

    monkeypatch.setattr(db, "rollback", rollback_wrapper)

    summary = module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=False)

    assert summary.mode == "dry-run"
    assert commit_calls["count"] == 0
    assert rollback_calls["count"] == 1
    assert current_counts(db)["demo_seed_records"] == 0


def test_apply_requires_development_and_confirm(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("DEMO_SEED_CONFIRM", raising=False)
    assert module.main(["--apply", "--scale", "management", "--as-of", "2026-07-12"]) == 1

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEMO_SEED_CONFIRM", "wrong")
    assert module.main(["--apply", "--scale", "management", "--as-of", "2026-07-12"]) == 1


def test_wrong_school_suspended_or_missing_year_abort(db, world):
    with pytest.raises(module.SeedError):
        module.load_world(db, "not-the-school")

    duplicate = School(name="United International School", slug="duplicate-uis", status="active")
    db.add(duplicate)
    db.commit()
    with pytest.raises(module.SeedError):
        module.load_world(db, "united-international-school")

    db.delete(duplicate)
    db.commit()
    world["school"].suspended_at = datetime.now(timezone.utc)
    db.commit()
    with pytest.raises(module.SeedError):
        module.load_world(db, "united-international-school")

    world["school"].suspended_at = None
    world["year"].is_current = False
    db.commit()
    with pytest.raises(module.SeedError):
        module.load_world(db, "united-international-school")


def test_second_apply_creates_no_duplicates(db, world, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEMO_SEED_CONFIRM", "united-international-school")

    first = module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=True)
    first_counts = current_counts(db)
    second = module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=True)
    second_counts = current_counts(db)

    assert first.counts["created"] > 0
    assert second.counts["created"] == 0
    assert second.counts["already_present"] > 0
    assert first_counts == second_counts


def test_seeded_behaviour_events_include_required_contexts(db, world, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEMO_SEED_CONFIRM", "united-international-school")

    module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=True)

    counts = {
        row[0]: row[1]
        for row in db.query(BehaviourEvent.context_type, func.count(BehaviourEvent.id)).group_by(BehaviourEvent.context_type).all()
    }
    assert counts["subject"] > 0
    assert counts["class"] > 0
    assert counts["duty"] > 0


def test_persona_selection_excludes_bob_and_linked_students(db, world):
    summary = module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=False)

    excluded_ids = {world["bob"].id, world["linked"].id}
    assert all(selection.student_id not in excluded_ids for selection in summary.personas.values())
    assert all(selection.student_name != "Bob Smith" for selection in summary.personas.values())


def test_showcase_dry_run_rolls_back_without_commit(db, monkeypatch):
    build_showcase_world(db)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEMO_SEED_CONFIRM", "united-international-school")

    summary = module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=False, scale="showcase")

    assert summary.mode == "dry-run"
    assert summary.scale == "showcase"
    assert demo_seed_record_total(db, "s22c-showcase-v1") == 0
    assert namespace_counts(db, "s22c-showcase-v1") == {}


def test_showcase_creates_expected_manifest_counts_and_is_idempotent(db, monkeypatch):
    build_showcase_world(db)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEMO_SEED_CONFIRM", "united-international-school")

    first = module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=True, scale="showcase")
    first_namespace_counts = namespace_counts(db, "s22c-showcase-v1")
    first_total = demo_seed_record_total(db, "s22c-showcase-v1")
    second = module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=True, scale="showcase")
    second_namespace_counts = namespace_counts(db, "s22c-showcase-v1")

    assert first.scale == "showcase"
    assert first.counts["created"] == 2390
    assert first.counts["already_present"] == 0
    assert second.counts["created"] == 0
    assert second.counts["already_present"] == 2390
    assert first_namespace_counts == {
        "announcement": 60,
        "behaviour_event": 2000,
        "calendar_event": 80,
        "homework_item": 200,
        "update_post": 50,
    }
    assert second_namespace_counts == first_namespace_counts
    assert first_total == 2390
    assert demo_seed_record_total(db, "s22-demo-v1") == 0


def test_showcase_includes_bob_kg1a_and_required_contexts(db, monkeypatch):
    build_showcase_world(db)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEMO_SEED_CONFIRM", "united-international-school")

    module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=True, scale="showcase")

    bob = db.query(Student).filter(Student.first_name == "Bob", Student.last_name == "Smith").one()
    section_id, section_code, grade_code = module.class_section_for_student(db, bob.id)
    assert f"{grade_code} {section_code}" == "KG1 A"
    assert db.query(FhhLink).filter(FhhLink.student_id == bob.id, FhhLink.status == "active").count() == 1
    kg1_subject_group_ids = [
        row[0]
        for row in db.query(SubjectGroup.id).filter(SubjectGroup.class_section_id == section_id).all()
    ]

    bob_behaviour_count = (
        db.query(BehaviourEvent)
        .join(DemoSeedRecord, DemoSeedRecord.model_id == BehaviourEvent.id)
        .filter(
            DemoSeedRecord.seed_namespace == "s22c-showcase-v1",
            DemoSeedRecord.entity_type == "behaviour_event",
            BehaviourEvent.student_id == bob.id,
        )
        .count()
    )
    assert 1 <= bob_behaviour_count <= 12

    behaviour_contexts = {
        row[0]: row[1]
        for row in db.query(BehaviourEvent.context_type, func.count(BehaviourEvent.id))
        .join(DemoSeedRecord, DemoSeedRecord.model_id == BehaviourEvent.id)
        .filter(DemoSeedRecord.seed_namespace == "s22c-showcase-v1", DemoSeedRecord.entity_type == "behaviour_event")
        .group_by(BehaviourEvent.context_type)
        .all()
    }
    assert behaviour_contexts["class"] > 0
    assert behaviour_contexts["subject"] > 0
    assert behaviour_contexts["duty"] > 0

    kg1_updates = (
        db.query(UpdatePost)
        .join(DemoSeedRecord, DemoSeedRecord.model_id == UpdatePost.id)
        .filter(
            DemoSeedRecord.seed_namespace == "s22c-showcase-v1",
            DemoSeedRecord.entity_type == "update_post",
            or_(
                (UpdatePost.audience_type == "class_section") & (UpdatePost.class_section_id == section_id),
                (UpdatePost.audience_type == "subject_group") & (UpdatePost.subject_group_id.in_(kg1_subject_group_ids)),
            ),
        )
        .count()
    )
    kg1_calendar_events = (
        db.query(CalendarEvent)
        .join(DemoSeedRecord, DemoSeedRecord.model_id == CalendarEvent.id)
        .filter(
            DemoSeedRecord.seed_namespace == "s22c-showcase-v1",
            DemoSeedRecord.entity_type == "calendar_event",
            or_(
                (CalendarEvent.audience_type == "class_section") & (CalendarEvent.class_section_id == section_id),
                (CalendarEvent.audience_type == "subject_group") & (CalendarEvent.subject_group_id.in_(kg1_subject_group_ids)),
            ),
        )
        .count()
    )
    assert kg1_updates >= 10
    assert kg1_calendar_events >= 10


def test_management_dry_run_rolls_back_without_commit(db, monkeypatch):
    build_management_world(db)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEMO_SEED_CONFIRM", "united-international-school")

    summary = module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=False, scale="management")

    assert summary.mode == "dry-run"
    assert summary.scale == "management"
    assert demo_seed_record_total(db, "s22d-management-v1") == 0


def test_management_creates_expected_manifest_counts_and_is_idempotent(db, monkeypatch):
    build_management_world(db)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEMO_SEED_CONFIRM", "united-international-school")

    first = module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=True, scale="management")
    first_namespace_counts = namespace_counts(db, "s22d-management-v1")
    first_total = demo_seed_record_total(db, "s22d-management-v1")
    second = module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=True, scale="management")
    second_namespace_counts = namespace_counts(db, "s22d-management-v1")

    assert first.counts["created"] == 8620
    assert first.counts["already_present"] == 0
    assert second.counts["created"] == 0
    assert second.counts["already_present"] == 8620
    assert first_total == 8620
    assert first_namespace_counts == {
        "announcement": 100,
        "behaviour_event": 8000,
        "calendar_event": 120,
        "homework_item": 300,
        "update_post": 100,
    }
    assert second_namespace_counts == first_namespace_counts
    assert demo_seed_record_total(db, "s22-demo-v1") == 0
    assert demo_seed_record_total(db, "s22c-showcase-v1") == 0


def test_management_includes_bob_kg1a_and_required_distribution(db, monkeypatch):
    world = build_management_world(db)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEMO_SEED_CONFIRM", "united-international-school")

    module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=True, scale="management")

    bob = db.query(Student).filter(Student.first_name == "Bob", Student.last_name == "Smith").one()
    section_id, section_code, grade_code = module.class_section_for_student(db, bob.id)
    assert f"{grade_code} {section_code}" == "KG1 A"

    bob_behaviour_count = (
        db.query(BehaviourEvent)
        .join(DemoSeedRecord, DemoSeedRecord.model_id == BehaviourEvent.id)
        .filter(
            DemoSeedRecord.seed_namespace == "s22d-management-v1",
            DemoSeedRecord.entity_type == "behaviour_event",
            BehaviourEvent.student_id == bob.id,
        )
        .count()
    )
    assert 6 <= bob_behaviour_count <= 20

    contexts = {row[0]: row[1] for row in db.query(BehaviourEvent.context_type, func.count(BehaviourEvent.id)).join(DemoSeedRecord, DemoSeedRecord.model_id == BehaviourEvent.id).filter(DemoSeedRecord.seed_namespace == "s22d-management-v1", DemoSeedRecord.entity_type == "behaviour_event").group_by(BehaviourEvent.context_type).all()}
    assert contexts["class"] > 0
    assert contexts["subject"] > 0
    assert contexts["duty"] > 0
    unique_students = (
        db.query(func.count(func.distinct(BehaviourEvent.student_id)))
        .join(DemoSeedRecord, DemoSeedRecord.model_id == BehaviourEvent.id)
        .filter(DemoSeedRecord.seed_namespace == "s22d-management-v1", DemoSeedRecord.entity_type == "behaviour_event")
        .scalar()
    )
    unique_sections = (
        db.query(func.count(func.distinct(BehaviourEvent.class_section_id)))
        .join(DemoSeedRecord, DemoSeedRecord.model_id == BehaviourEvent.id)
        .filter(
            DemoSeedRecord.seed_namespace == "s22d-management-v1",
            DemoSeedRecord.entity_type == "behaviour_event",
            BehaviourEvent.class_section_id.isnot(None),
        )
        .scalar()
    )
    unique_teachers = (
        db.query(func.count(func.distinct(BehaviourEvent.actor_user_id)))
        .join(DemoSeedRecord, DemoSeedRecord.model_id == BehaviourEvent.id)
        .filter(DemoSeedRecord.seed_namespace == "s22d-management-v1", DemoSeedRecord.entity_type == "behaviour_event")
        .scalar()
    )
    assert unique_students is not None and unique_students >= 450
    assert unique_sections is not None and unique_sections >= 6
    assert unique_teachers is not None and unique_teachers >= 4


def test_manual_records_are_not_modified(db, world, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEMO_SEED_CONFIRM", "united-international-school")

    before = db.query(Announcement).filter(Announcement.id == world["manual_announcement_id"]).one()
    module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=True)
    after = db.query(Announcement).filter(Announcement.id == world["manual_announcement_id"]).one()

    assert before.title == "Manual announcement"
    assert after.title == "Manual announcement"
    assert db.query(Announcement).filter(Announcement.title == "Manual announcement").count() == 1


def test_external_helpers_are_not_called(db, world, monkeypatch):
    monkeypatch.setattr(auth, "create_access_token", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("auth token helper should not be called")))

    try:
        from app import mailer
    except Exception:
        mailer = None
    if mailer is not None and hasattr(mailer, "send_staff_invite"):
        monkeypatch.setattr(mailer, "send_staff_invite", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("mailer helper should not be called")))
    if mailer is not None and hasattr(mailer, "send_magic_login"):
        monkeypatch.setattr(mailer, "send_magic_login", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("mailer helper should not be called")))

    summary = module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=False)
    assert summary.mode == "dry-run"


def test_forced_failure_rolls_back_cleanly(db, world, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEMO_SEED_CONFIRM", "united-international-school")

    original = module.persist_task
    call_count = {"value": 0}

    def boom(db_session, task, *, apply, counts, school_id=None):
        call_count["value"] += 1
        if call_count["value"] == 4:
            raise RuntimeError("boom")
        return original(db_session, task, apply=apply, counts=counts, school_id=school_id)

    monkeypatch.setattr(module, "persist_task", boom)

    with pytest.raises(RuntimeError):
        module.seed_school(db, school_slug="united-international-school", as_of=module.parse_as_of("2026-07-12"), apply=True)

    assert current_counts(db)["demo_seed_records"] == 0
    assert current_counts(db)["behaviour_events"] == 0


def test_manifest_table_schema_is_creatable(tmp_path):
    sqlite_path = tmp_path / "manifest.db"
    engine = create_engine(f"sqlite:///{sqlite_path}")
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    assert "demo_seed_records" in inspector.get_table_names()
    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("demo_seed_records")
    }
    assert "uq_demo_seed_records_namespace_type_key" in unique_constraints

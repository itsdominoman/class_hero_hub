from __future__ import annotations

from contextlib import contextmanager
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.database import Base
from app.models_school import (
    AcademicYear,
    BranchCampus,
    ClassSection,
    Enrolment,
    GradeLevel,
    School,
    Student,
    Subject,
    SubjectGroup,
)
from app.rosters import (
    bulk_subject_groups_for_students,
    current_subject_groups_for_student,
    roster_payload,
    subject_group_members,
)


TODAY = date(2026, 7, 16)
test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def db():
    database.engine = test_engine
    database.SessionLocal = TestingSessionLocal
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@contextmanager
def count_queries():
    statements: list[str] = []

    def before_cursor_execute(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(test_engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(test_engine, "before_cursor_execute", before_cursor_execute)


@pytest.fixture
def roster_world(db):
    alpha = School(name="Alpha", slug="roster-alpha", status="active")
    beta = School(name="Beta", slug="roster-beta", status="active")
    db.add_all([alpha, beta])
    db.flush()

    alpha_main = BranchCampus(school_id=alpha.id, code="MAIN", name="Main", status="active")
    alpha_west = BranchCampus(school_id=alpha.id, code="WEST", name="West", status="active")
    beta_main = BranchCampus(school_id=beta.id, code="MAIN", name="Main", status="active")
    current_year = AcademicYear(school_id=alpha.id, code="2026", name="2026", status="active", is_current=True)
    old_year = AcademicYear(school_id=alpha.id, code="2025", name="2025", status="inactive", is_current=False)
    beta_year = AcademicYear(school_id=beta.id, code="2026", name="2026", status="active", is_current=True)
    grade_one = GradeLevel(school_id=alpha.id, code="G1", name="Grade 1", status="active")
    grade_two = GradeLevel(school_id=alpha.id, code="G2", name="Grade 2", status="active")
    beta_grade = GradeLevel(school_id=beta.id, code="G1", name="Grade 1", status="active")
    alpha_subject = Subject(school_id=alpha.id, code="ENG", name="English", status="active")
    beta_subject = Subject(school_id=beta.id, code="ENG", name="English", status="active")
    db.add_all([
        alpha_main,
        alpha_west,
        beta_main,
        current_year,
        old_year,
        beta_year,
        grade_one,
        grade_two,
        beta_grade,
        alpha_subject,
        beta_subject,
    ])
    db.flush()

    section_main = ClassSection(
        school_id=alpha.id,
        branch_campus_id=alpha_main.id,
        academic_year_id=current_year.id,
        grade_level_id=grade_one.id,
        code="G1A",
        name="Grade 1 A",
        status="active",
    )
    section_west = ClassSection(
        school_id=alpha.id,
        branch_campus_id=alpha_west.id,
        academic_year_id=current_year.id,
        grade_level_id=grade_one.id,
        code="G1W",
        name="Grade 1 West",
        status="active",
    )
    section_old_year = ClassSection(
        school_id=alpha.id,
        branch_campus_id=alpha_main.id,
        academic_year_id=old_year.id,
        grade_level_id=grade_one.id,
        code="G1OLD",
        name="Grade 1 Old",
        status="active",
    )
    section_grade_two = ClassSection(
        school_id=alpha.id,
        branch_campus_id=alpha_main.id,
        academic_year_id=current_year.id,
        grade_level_id=grade_two.id,
        code="G2A",
        name="Grade 2 A",
        status="active",
    )
    inactive_section = ClassSection(
        school_id=alpha.id,
        branch_campus_id=alpha_main.id,
        academic_year_id=current_year.id,
        grade_level_id=grade_one.id,
        code="G1X",
        name="Grade 1 Inactive",
        status="inactive",
    )
    beta_section = ClassSection(
        school_id=beta.id,
        branch_campus_id=beta_main.id,
        academic_year_id=beta_year.id,
        grade_level_id=beta_grade.id,
        code="G1A",
        name="Grade 1 A",
        status="active",
    )
    db.add_all([section_main, section_west, section_old_year, section_grade_two, inactive_section, beta_section])
    db.flush()

    explicit_group = SubjectGroup(
        school_id=alpha.id,
        academic_year_id=current_year.id,
        class_section_id=section_main.id,
        subject_id=alpha_subject.id,
        code="EXPLICIT",
        name="Explicit",
        status="active",
        enrolment_policy="explicit_only",
        sort_order=10,
    )
    section_group = SubjectGroup(
        school_id=alpha.id,
        academic_year_id=current_year.id,
        class_section_id=section_main.id,
        subject_id=alpha_subject.id,
        code="SECTION",
        name="Section default",
        status="active",
        enrolment_policy="default_for_section",
        sort_order=20,
    )
    grade_group = SubjectGroup(
        school_id=alpha.id,
        academic_year_id=current_year.id,
        grade_level_id=grade_one.id,
        subject_id=alpha_subject.id,
        code="GRADE",
        name="Grade default",
        status="active",
        enrolment_policy="default_for_grade",
        sort_order=30,
    )
    old_year_group = SubjectGroup(
        school_id=alpha.id,
        academic_year_id=old_year.id,
        grade_level_id=grade_one.id,
        subject_id=alpha_subject.id,
        code="GRADE-OLD",
        name="Old grade default",
        status="active",
        enrolment_policy="default_for_grade",
        sort_order=40,
    )
    archived_group = SubjectGroup(
        school_id=alpha.id,
        academic_year_id=current_year.id,
        class_section_id=section_main.id,
        subject_id=alpha_subject.id,
        code="ARCHIVED",
        name="Archived",
        status="archived",
        enrolment_policy="default_for_section",
        sort_order=50,
    )
    inactive_section_group = SubjectGroup(
        school_id=alpha.id,
        academic_year_id=current_year.id,
        class_section_id=inactive_section.id,
        subject_id=alpha_subject.id,
        code="INACTIVE-SECTION",
        name="Inactive section default",
        status="active",
        enrolment_policy="default_for_section",
        sort_order=60,
    )
    beta_group = SubjectGroup(
        school_id=beta.id,
        academic_year_id=beta_year.id,
        class_section_id=beta_section.id,
        subject_id=beta_subject.id,
        code="BETA",
        name="Beta group",
        status="active",
        enrolment_policy="default_for_section",
    )
    db.add_all([explicit_group, section_group, grade_group, old_year_group, archived_group, inactive_section_group, beta_group])
    db.flush()

    def student(ref: str, first_name: str, last_name: str = "Student", *, school_id: int = alpha.id, status: str = "active"):
        row = Student(
            school_id=school_id,
            external_ref=ref,
            first_name=first_name,
            last_name=last_name,
            status=status,
        )
        db.add(row)
        db.flush()
        return row

    explicit_only = student("EXPLICIT", "Explicit")
    section_default = student("SECTION", "Section")
    grade_branch = student("BRANCH", "Branch")
    grade_old_year = student("OLD-YEAR", "OldYear")
    excluded_section = student("EX-SECTION", "ExcludedSection")
    excluded_grade = student("EX-GRADE", "ExcludedGrade")
    duplicate_path = student("DUPLICATE", "Duplicate")
    moved_section = student("MOVED", "Moved")
    inactive_student = student("INACTIVE-STUDENT", "Inactive", status="inactive")
    inactive_section_student = student("INACTIVE-SECTION", "InactiveSection")
    closed_enrolment = student("CLOSED", "Closed")
    no_group = student("NO-GROUP", "NoGroup")
    cross_school_student = student("CROSS", "CrossSchool", school_id=beta.id)

    def class_member(student_row, section, *, valid_from=TODAY, valid_to=None):
        db.add(Enrolment(
            school_id=alpha.id,
            student_id=student_row.id,
            class_section_id=section.id,
            kind="member",
            valid_from=valid_from,
            valid_to=valid_to,
        ))

    class_member(section_default, section_main)
    class_member(grade_branch, section_west)
    class_member(grade_old_year, section_old_year)
    class_member(excluded_section, section_main)
    class_member(excluded_grade, section_main)
    class_member(duplicate_path, section_main)
    class_member(moved_section, section_main, valid_from=TODAY - timedelta(days=5), valid_to=TODAY)
    class_member(moved_section, section_grade_two)
    class_member(inactive_student, section_main)
    class_member(inactive_section_student, inactive_section)
    class_member(closed_enrolment, section_main, valid_from=TODAY - timedelta(days=5), valid_to=TODAY)
    class_member(no_group, section_grade_two)

    db.add_all([
        Enrolment(school_id=alpha.id, student_id=explicit_only.id, subject_group_id=explicit_group.id, kind="member", valid_from=TODAY),
        Enrolment(school_id=alpha.id, student_id=duplicate_path.id, subject_group_id=section_group.id, kind="member", valid_from=TODAY),
        Enrolment(school_id=alpha.id, student_id=excluded_section.id, subject_group_id=section_group.id, kind="excluded", valid_from=TODAY),
        Enrolment(school_id=alpha.id, student_id=excluded_grade.id, subject_group_id=grade_group.id, kind="excluded", valid_from=TODAY),
        Enrolment(school_id=alpha.id, student_id=excluded_grade.id, subject_group_id=grade_group.id, kind="member", valid_from=TODAY),
        Enrolment(school_id=alpha.id, student_id=explicit_only.id, subject_group_id=archived_group.id, kind="member", valid_from=TODAY),
        # Deliberately inconsistent tenant row: the resolver must still reject the
        # beta-school student even though enrolment.school_id is alpha.
        Enrolment(school_id=alpha.id, student_id=cross_school_student.id, subject_group_id=explicit_group.id, kind="member", valid_from=TODAY),
    ])
    db.commit()

    return {
        "school": alpha,
        "students": {
            "explicit_only": explicit_only,
            "section_default": section_default,
            "grade_branch": grade_branch,
            "grade_old_year": grade_old_year,
            "excluded_section": excluded_section,
            "excluded_grade": excluded_grade,
            "duplicate_path": duplicate_path,
            "moved_section": moved_section,
            "inactive_student": inactive_student,
            "inactive_section_student": inactive_section_student,
            "closed_enrolment": closed_enrolment,
            "no_group": no_group,
            "cross_school_student": cross_school_student,
        },
        "groups": {
            "explicit": explicit_group,
            "section": section_group,
            "grade": grade_group,
            "old_year": old_year_group,
            "archived": archived_group,
            "inactive_section": inactive_section_group,
        },
        "section": section_main,
    }


def test_subject_group_membership_truth_table(db, roster_world):
    world = roster_world
    students = world["students"]
    groups = world["groups"]
    resolved = bulk_subject_groups_for_students(db, world["school"].id, TODAY)
    memberships = {
        student_id: {group["id"]: group for group in group_rows}
        for student_id, group_rows in resolved.items()
    }

    assert memberships[students["explicit_only"].id][groups["explicit"].id]["source"] == "explicit"
    assert memberships[students["section_default"].id][groups["section"].id]["source"] == "default"
    assert memberships[students["section_default"].id][groups["grade"].id]["source"] == "default"

    # Grade defaults span branches, but never a different academic year.
    assert groups["grade"].id in memberships[students["grade_branch"].id]
    assert groups["grade"].id not in memberships[students["grade_old_year"].id]
    assert groups["old_year"].id in memberships[students["grade_old_year"].id]

    assert groups["section"].id not in memberships.get(students["excluded_section"].id, {})
    assert groups["grade"].id not in memberships.get(students["excluded_grade"].id, {})

    duplicate_groups = [
        row for row in resolved[students["duplicate_path"].id]
        if row["id"] == groups["section"].id
    ]
    assert len(duplicate_groups) == 1
    assert duplicate_groups[0]["source"] == "explicit"

    for absent in (
        "moved_section",
        "inactive_student",
        "inactive_section_student",
        "closed_enrolment",
        "no_group",
        "cross_school_student",
    ):
        assert groups["section"].id not in memberships.get(students[absent].id, {})

    assert groups["archived"].id not in {
        group["id"] for group_rows in resolved.values() for group in group_rows
    }
    assert groups["inactive_section"].id not in memberships.get(students["inactive_section_student"].id, {})
    assert students["cross_school_student"].id not in memberships
    assert all(
        len(group_rows) == len({group["id"] for group in group_rows})
        for group_rows in resolved.values()
    )


def test_archived_subject_group_has_no_current_roster(db, roster_world):
    world = roster_world
    members, excluded = subject_group_members(
        db,
        world["school"].id,
        world["groups"]["archived"],
        TODAY,
    )
    assert members == []
    assert excluded == []


def test_roster_result_order_is_deterministic(db, roster_world):
    world = roster_world
    first = bulk_subject_groups_for_students(db, world["school"].id, TODAY)
    db.expire_all()
    second = bulk_subject_groups_for_students(db, world["school"].id, TODAY)
    assert first == second
    assert all(
        group_rows == sorted(group_rows, key=lambda row: (row["sort_order"], row["id"]))
        for group_rows in first.values()
    )


def test_subject_group_resolution_query_count_is_bounded(db, roster_world):
    world = roster_world
    school_id = world["school"].id
    student_id = world["students"]["section_default"].id
    section_id = world["section"].id
    academic_year_id = world["groups"]["section"].academic_year_id
    teacher_group = world["groups"]["section"]
    # Load every attribute used by the resolver before query counting so ORM
    # expiration does not make the test count fixture access.
    _ = (
        teacher_group.id,
        teacher_group.school_id,
        teacher_group.status,
        teacher_group.sort_order,
        teacher_group.enrolment_policy,
        teacher_group.class_section_id,
        teacher_group.grade_level_id,
        teacher_group.academic_year_id,
    )

    with count_queries() as whole_school_queries:
        bulk_subject_groups_for_students(db, school_id, TODAY)
    with count_queries() as one_student_queries:
        current_subject_groups_for_student(
            db,
            school_id,
            student_id,
            TODAY,
        )
    with count_queries() as class_queries:
        roster_payload(
            db,
            school_id,
            class_section_id=section_id,
            today=TODAY,
        )
    with count_queries() as teacher_group_queries:
        subject_group_members(db, school_id, teacher_group, TODAY)

    assert len(whole_school_queries) <= 3
    assert len(one_student_queries) <= 3
    assert len(class_queries) <= 2
    assert len(teacher_group_queries) <= 2

    subject = db.query(Subject).filter(Subject.school_id == school_id).first()
    for index in range(20):
        db.add(SubjectGroup(
            school_id=school_id,
            academic_year_id=academic_year_id,
            class_section_id=section_id,
            subject_id=subject.id,
            code=f"SCALE-{index}",
            name=f"Scale {index}",
            status="active",
            enrolment_policy="default_for_section",
            sort_order=100 + index,
        ))
    db.commit()

    with count_queries() as scaled_queries:
        bulk_subject_groups_for_students(db, school_id, TODAY)
    assert len(scaled_queries) <= 3
    assert len(scaled_queries) == len(whole_school_queries)

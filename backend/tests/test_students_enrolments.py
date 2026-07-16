import os
from datetime import datetime, timedelta, timezone

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database, invite_tokens
from app.database import Base, get_db
from app.main import app
from app.models_school import (
    AcademicYear,
    BehaviourCategory,
    BehaviourEvent,
    BranchCampus,
    ClassSection,
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


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
database.engine = engine
database.SessionLocal = TestingSessionLocal


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def bearer(email: str, school_id: int | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {auth.create_access_token({'sub': email})}"}
    if school_id is not None:
        headers["X-School-Id"] = str(school_id)
    return headers


def create_user(db, email: str, name: str) -> User:
    user = User(email=email, name=name, google_sub=f"sub-{email}")
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def enrolment_world(db):
    alpha_admin = create_user(db, "alpha-admin@example.com", "Alpha Admin")
    alpha_teacher = create_user(db, "alpha-teacher@example.com", "Alpha Teacher")
    other_teacher = create_user(db, "other-teacher@example.com", "Other Teacher")
    beta_admin = create_user(db, "beta-admin@example.com", "Beta Admin")
    beta_teacher = create_user(db, "beta-teacher@example.com", "Beta Teacher")
    no_role = create_user(db, "no-role@example.com", "No Role")

    alpha = School(name="Alpha Academy", slug="alpha", status="active")
    beta = School(name="Beta School", slug="beta", status="active")
    db.add_all([alpha, beta])
    db.flush()

    alpha_admin_membership = Membership(school_id=alpha.id, user_id=alpha_admin.id, role="school_admin")
    alpha_teacher_membership = Membership(school_id=alpha.id, user_id=alpha_teacher.id, role="teacher")
    other_teacher_membership = Membership(school_id=alpha.id, user_id=other_teacher.id, role="teacher")
    beta_admin_membership = Membership(school_id=beta.id, user_id=beta_admin.id, role="school_admin")
    beta_teacher_membership = Membership(school_id=beta.id, user_id=beta_teacher.id, role="teacher")
    db.add_all([alpha_admin_membership, alpha_teacher_membership, other_teacher_membership, beta_admin_membership, beta_teacher_membership])
    db.flush()

    branch = BranchCampus(school_id=alpha.id, code="MAIN", name="Main", status="active")
    beta_branch = BranchCampus(school_id=beta.id, code="MAIN", name="Main", status="active")
    year = AcademicYear(school_id=alpha.id, code="2026", name="2026", status="active", is_current=True)
    beta_year = AcademicYear(school_id=beta.id, code="2026", name="2026", status="active", is_current=True)
    level = GradeLevel(school_id=alpha.id, code="KG1", name="KG 1", status="active")
    beta_level = GradeLevel(school_id=beta.id, code="KG1", name="KG 1", status="active")
    subject = Subject(school_id=alpha.id, code="ENG", name="English", status="active")
    db.add_all([branch, beta_branch, year, beta_year, level, beta_level, subject])
    db.flush()

    section_a = ClassSection(school_id=alpha.id, branch_campus_id=branch.id, academic_year_id=year.id, grade_level_id=level.id, code="A", name="KG 1 A", status="active")
    section_b = ClassSection(school_id=alpha.id, branch_campus_id=branch.id, academic_year_id=year.id, grade_level_id=level.id, code="B", name="KG 1 B", status="active")
    inactive_section = ClassSection(school_id=alpha.id, branch_campus_id=branch.id, academic_year_id=year.id, grade_level_id=level.id, code="X", name="KG 1 X", status="inactive")
    beta_section = ClassSection(school_id=beta.id, branch_campus_id=beta_branch.id, academic_year_id=beta_year.id, grade_level_id=beta_level.id, code="A", name="KG 1 A", status="active")
    db.add_all([section_a, section_b, inactive_section, beta_section])
    db.flush()

    group = SubjectGroup(school_id=alpha.id, academic_year_id=year.id, class_section_id=section_a.id, subject_id=subject.id, code="KG1A-ENG", name="KG 1 A English", status="active")
    inactive_group = SubjectGroup(school_id=alpha.id, academic_year_id=year.id, class_section_id=section_a.id, subject_id=subject.id, code="KG1A-OLD", name="Old English", status="inactive")
    group_archived_parent = SubjectGroup(school_id=alpha.id, academic_year_id=year.id, class_section_id=inactive_section.id, subject_id=subject.id, code="KG1X-ENG", name="KG 1 X English", status="active")
    db.add_all([group, inactive_group, group_archived_parent])
    db.commit()

    return {
        "alpha": alpha,
        "beta": beta,
        "alpha_admin": alpha_admin,
        "alpha_teacher": alpha_teacher,
        "other_teacher": other_teacher,
        "beta_admin": beta_admin,
        "beta_teacher": beta_teacher,
        "no_role": no_role,
        "alpha_teacher_membership": alpha_teacher_membership,
        "other_teacher_membership": other_teacher_membership,
        "beta_teacher_membership": beta_teacher_membership,
        "year": year,
        "level": level,
        "subject": subject,
        "section_a": section_a,
        "section_b": section_b,
        "inactive_section": inactive_section,
        "beta_section": beta_section,
        "group": group,
        "inactive_group": inactive_group,
        "group_archived_parent": group_archived_parent,
    }


def student_payload(ref="S-001", first="Ali", last="Khan"):
    return {"external_ref": ref, "first_name": first, "last_name": last, "preferred_name": "", "name_ar": "", "gender": ""}


def create_student_api(client, world, ref="S-001", first="Ali", last="Khan"):
    return client.post("/api/school/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id), json=student_payload(ref, first, last))


def enrol_student(client, world, student_id, payload):
    return client.post(
        f"/api/school/students/{student_id}/enrolments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json=payload,
    )


def test_school_admin_student_lifecycle_and_duplicate_policy(db, client, enrolment_world):
    world = enrolment_world
    created = create_student_api(client, world)
    assert created.status_code == 201
    student_id = created.json()["id"]
    assert created.json()["display_name"] == "Ali Khan"
    listed = client.get("/api/school/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert listed.status_code == 200
    assert any(row["id"] == student_id for row in listed.json())

    duplicate = create_student_api(client, world)
    assert duplicate.status_code == 409

    inactive_dup = client.put(
        f"/api/school/students/{student_id}",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={**student_payload(), "status": "inactive"},
    )
    assert inactive_dup.status_code == 200
    assert create_student_api(client, world).status_code == 409

    updated = client.put(
        f"/api/school/students/{student_id}",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={**student_payload(), "first_name": "Alya", "preferred_name": "Aly"},
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Aly Khan"

    archived = client.delete(f"/api/school/students/{student_id}", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert archived.status_code == 204
    assert all(row["id"] != student_id for row in client.get("/api/school/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id)).json())
    assert any(row["id"] == student_id for row in client.get("/api/school/students?include_archived=true", headers=bearer(world["alpha_admin"].email, world["alpha"].id)).json())

    restored = create_student_api(client, world, first="Restored")
    assert restored.status_code == 201
    assert restored.json()["id"] == student_id
    assert restored.json()["restored"] is True


def test_student_access_boundaries(db, client, enrolment_world):
    world = enrolment_world
    assert create_student_api(client, world).status_code == 201
    assert client.post("/api/school/students", headers=bearer(world["alpha_teacher"].email, world["alpha"].id), json=student_payload("S-002")).status_code == 403
    assert client.post("/api/school/students", headers=bearer(world["no_role"].email, world["alpha"].id), json=student_payload("S-003")).status_code == 403
    assert client.get("/api/school/students", headers=bearer(world["alpha_admin"].email, world["beta"].id)).status_code == 403


def test_student_gender_validation(db, client, enrolment_world):
    world = enrolment_world
    invalid = client.post(
        "/api/school/students",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={**student_payload(ref="S-900"), "gender": "banana"},
    )
    assert invalid.status_code == 422


def test_student_remove_mistake_requires_no_history_and_school_admin(db, client, enrolment_world):
    world = enrolment_world
    draft_id = create_student_api(client, world, ref="S-DRAFT").json()["id"]
    assert client.delete(
        f"/api/school/students/{draft_id}/remove-mistake",
        headers=bearer(world["alpha_teacher"].email, world["alpha"].id),
    ).status_code == 403
    assert client.delete(
        f"/api/school/students/{draft_id}/remove-mistake",
        headers=bearer(world["beta_admin"].email, world["beta"].id),
    ).status_code == 404
    removed = client.delete(
        f"/api/school/students/{draft_id}/remove-mistake",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    assert removed.status_code == 204
    db.expire_all()
    assert db.query(Student).filter_by(id=draft_id).first() is None

    enrolled_id = create_student_api(client, world, ref="S-HISTORY").json()["id"]
    client.post(
        f"/api/school/students/{enrolled_id}/enrolments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"class_section_id": world["section_a"].id},
    )
    blocked = client.delete(
        f"/api/school/students/{enrolled_id}/remove-mistake",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    assert blocked.status_code == 409
    assert "Archive instead" in blocked.json()["detail"]
    assert db.query(Student).filter_by(id=enrolled_id).first() is not None


def test_class_section_enrolment_move_and_history(db, client, enrolment_world):
    world = enrolment_world
    student_id = create_student_api(client, world).json()["id"]
    first = client.post(
        f"/api/school/students/{student_id}/enrolments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"class_section_id": world["section_a"].id},
    )
    assert first.status_code == 201
    assert first.json()["class_section_id"] == world["section_a"].id
    filtered = client.get(
        f"/api/school/students?class_section_id={world['section_a'].id}",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    assert filtered.status_code == 200
    assert [row["id"] for row in filtered.json()] == [student_id]

    duplicate = client.post(
        f"/api/school/students/{student_id}/enrolments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"class_section_id": world["section_b"].id},
    )
    assert duplicate.status_code == 409

    moved = client.post(
        f"/api/school/students/{student_id}/move-section",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"class_section_id": world["section_b"].id},
    )
    assert moved.status_code == 201
    db.expire_all()
    old_row = db.query(Enrolment).filter_by(id=first.json()["id"]).one()
    assert old_row.valid_to == invite_tokens.now_utc().date()

    history = client.get(f"/api/school/students/{student_id}/enrolments", headers=bearer(world["alpha_admin"].email, world["alpha"].id)).json()
    assert len(history) == 2
    assert any(row["valid_to"] is not None for row in history)
    roster = client.get(f"/api/school/class-sections/{world['section_b'].id}/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert roster.status_code == 200
    assert [row["id"] for row in roster.json()["students"]] == [student_id]


def test_admin_class_roster_setup_payload(db, client, enrolment_world):
    world = enrolment_world
    empty = client.get(
        f"/api/school/class-sections/{world['section_a'].id}/roster",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    assert empty.status_code == 200
    assert empty.json()["students"] == []

    student_id = create_student_api(client, world, ref="S-ROSTER", first="Bob", last="Smith").json()["id"]
    client.post(
        f"/api/school/students/{student_id}/enrolments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"class_section_id": world["section_a"].id},
    )
    homeroom_assignment = StaffAssignment(
        school_id=world["alpha"].id,
        membership_id=world["alpha_teacher_membership"].id,
        class_section_id=world["section_a"].id,
        role="homeroom",
        valid_from=invite_tokens.now_utc().date(),
    )
    subject_assignment = StaffAssignment(
        school_id=world["alpha"].id,
        membership_id=world["alpha_teacher_membership"].id,
        subject_group_id=world["group"].id,
        role="subject",
        valid_from=invite_tokens.now_utc().date(),
    )
    db.add_all([homeroom_assignment, subject_assignment])
    db.commit()

    roster = client.get(
        f"/api/school/class-sections/{world['section_a'].id}/roster",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    assert roster.status_code == 200
    body = roster.json()
    assert body["class_section"]["id"] == world["section_a"].id
    assert body["branch"]["name"] == "Main"
    assert body["academic_year"]["name"] == "2026"
    assert body["grade_level"]["name"] == "KG 1"
    assert [row["id"] for row in body["students"]] == [student_id]
    assert body["homeroom_teacher"]["user"]["email"] == world["alpha_teacher"].email
    assert body["subject_groups"][0]["subject_group"]["id"] == world["group"].id
    assert body["subject_groups"][0]["subject"]["name"] == "English"
    assert body["subject_groups"][0]["teacher"]["user"]["email"] == world["alpha_teacher"].email

    assert client.get(
        f"/api/school/class-sections/{world['section_a'].id}/roster",
        headers=bearer(world["alpha_teacher"].email, world["alpha"].id),
    ).status_code == 403
    assert client.get(
        f"/api/school/class-sections/{world['section_a'].id}/roster",
        headers=bearer(world["beta_admin"].email, world["beta"].id),
    ).status_code == 404


def test_subject_group_enrolment_is_explicit_and_target_status_validated(db, client, enrolment_world):
    world = enrolment_world
    student_id = create_student_api(client, world).json()["id"]
    assert client.post(
        f"/api/school/students/{student_id}/enrolments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"class_section_id": world["section_a"].id},
    ).status_code == 201

    empty_group_roster = client.get(f"/api/school/subject-groups/{world['group'].id}/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert empty_group_roster.status_code == 200
    assert empty_group_roster.json()["students"] == []

    group_enrolment = client.post(
        f"/api/school/students/{student_id}/enrolments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"subject_group_id": world["group"].id},
    )
    assert group_enrolment.status_code == 201
    group_roster = client.get(f"/api/school/subject-groups/{world['group'].id}/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert group_roster.status_code == 200
    assert [(row["id"], row["source"], row["enrolment_id"]) for row in group_roster.json()["students"]] == [(student_id, "explicit", group_enrolment.json()["id"])]
    assert client.post(
        f"/api/school/students/{student_id}/enrolments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"subject_group_id": world["group"].id},
    ).status_code == 409

    assert client.post(
        f"/api/school/students/{student_id}/enrolments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"class_section_id": world["inactive_section"].id},
    ).status_code == 400
    assert client.post(
        f"/api/school/students/{student_id}/enrolments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"subject_group_id": world["inactive_group"].id},
    ).status_code == 400
    assert client.post(
        f"/api/school/students/{student_id}/enrolments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"subject_group_id": world["group_archived_parent"].id},
    ).status_code == 400


def test_default_for_section_roster_matches_section_members(db, client, enrolment_world):
    world = enrolment_world
    world["group"].enrolment_policy = "default_for_section"
    db.commit()
    in_section = create_student_api(client, world, ref="S-A", first="Alya").json()["id"]
    other_section = create_student_api(client, world, ref="S-B", first="Badr").json()["id"]
    enrol_student(client, world, in_section, {"class_section_id": world["section_a"].id})
    enrol_student(client, world, other_section, {"class_section_id": world["section_b"].id})

    roster = client.get(f"/api/school/subject-groups/{world['group'].id}/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert roster.status_code == 200
    body = roster.json()
    assert body["enrolment_policy"] == "default_for_section"
    assert [(row["id"], row["source"], row["enrolment_id"]) for row in body["students"]] == [(in_section, "default", None)]


def test_default_for_grade_roster_spans_grade_sections(db, client, enrolment_world):
    world = enrolment_world
    group = SubjectGroup(
        school_id=world["alpha"].id,
        academic_year_id=world["year"].id,
        grade_level_id=world["level"].id,
        subject_id=world["subject"].id,
        code="KG1-ENG",
        name="KG 1 English",
        status="active",
        enrolment_policy="default_for_grade",
    )
    db.add(group)
    db.commit()
    student_a = create_student_api(client, world, ref="S-GA", first="A").json()["id"]
    student_b = create_student_api(client, world, ref="S-GB", first="B").json()["id"]
    enrol_student(client, world, student_a, {"class_section_id": world["section_a"].id})
    enrol_student(client, world, student_b, {"class_section_id": world["section_b"].id})

    roster = client.get(f"/api/school/subject-groups/{group.id}/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert roster.status_code == 200
    assert {row["id"] for row in roster.json()["students"]} == {student_a, student_b}
    assert {row["source"] for row in roster.json()["students"]} == {"default"}


def test_default_group_exclusion_can_be_closed_to_restore_member(db, client, enrolment_world):
    world = enrolment_world
    world["group"].enrolment_policy = "default_for_section"
    db.commit()
    student_id = create_student_api(client, world, ref="S-EX").json()["id"]
    enrol_student(client, world, student_id, {"class_section_id": world["section_a"].id})

    excluded = enrol_student(client, world, student_id, {"subject_group_id": world["group"].id, "kind": "excluded"})
    assert excluded.status_code == 201
    roster = client.get(f"/api/school/subject-groups/{world['group'].id}/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id)).json()
    assert roster["students"] == []
    assert [row["id"] for row in roster["excluded_students"]] == [student_id]

    closed = client.delete(f"/api/school/enrolments/{excluded.json()['id']}", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert closed.status_code == 200
    restored = client.get(f"/api/school/subject-groups/{world['group'].id}/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id)).json()
    assert [(row["id"], row["source"]) for row in restored["students"]] == [(student_id, "default")]


def test_explicit_member_on_default_group_wins_without_duplicates(db, client, enrolment_world):
    world = enrolment_world
    world["group"].enrolment_policy = "default_for_section"
    db.commit()
    student_id = create_student_api(client, world, ref="S-UNION").json()["id"]
    enrol_student(client, world, student_id, {"class_section_id": world["section_a"].id})
    explicit = enrol_student(client, world, student_id, {"subject_group_id": world["group"].id})
    assert explicit.status_code == 201

    roster = client.get(f"/api/school/subject-groups/{world['group'].id}/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id)).json()
    assert [(row["id"], row["source"], row["enrolment_id"]) for row in roster["students"]] == [(student_id, "explicit", explicit.json()["id"])]


def test_class_move_updates_default_subject_rosters_without_subject_writes(db, client, enrolment_world):
    world = enrolment_world
    group_b = SubjectGroup(
        school_id=world["alpha"].id,
        academic_year_id=world["year"].id,
        class_section_id=world["section_b"].id,
        subject_id=world["subject"].id,
        code="KG1B-ENG",
        name="KG 1 B English",
        status="active",
        enrolment_policy="default_for_section",
    )
    world["group"].enrolment_policy = "default_for_section"
    db.add(group_b)
    db.commit()
    student_id = create_student_api(client, world, ref="S-MOVE").json()["id"]
    enrol_student(client, world, student_id, {"class_section_id": world["section_a"].id})

    before_a = client.get(f"/api/school/subject-groups/{world['group'].id}/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id)).json()
    before_b = client.get(f"/api/school/subject-groups/{group_b.id}/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id)).json()
    assert [row["id"] for row in before_a["students"]] == [student_id]
    assert before_b["students"] == []

    moved = client.post(
        f"/api/school/students/{student_id}/move-section",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"class_section_id": world["section_b"].id},
    )
    assert moved.status_code == 201
    after_a = client.get(f"/api/school/subject-groups/{world['group'].id}/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id)).json()
    after_b = client.get(f"/api/school/subject-groups/{group_b.id}/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id)).json()
    assert after_a["students"] == []
    assert [row["id"] for row in after_b["students"]] == [student_id]


def test_enrolment_policy_and_exclusion_validation(db, client, enrolment_world):
    world = enrolment_world
    headers = bearer(world["alpha_admin"].email, world["alpha"].id)
    bad_policy = client.post(
        "/api/school/subject-groups",
        headers=headers,
        json={
            "code": "BAD",
            "name": "Bad",
            "academic_year_id": world["year"].id,
            "grade_level_id": world["level"].id,
            "subject_id": world["subject"].id,
            "enrolment_policy": "default_for_section",
        },
    )
    assert bad_policy.status_code == 400
    student_id = create_student_api(client, world, ref="S-VAL").json()["id"]
    assert enrol_student(client, world, student_id, {"subject_group_id": world["group"].id, "kind": "excluded"}).status_code == 400
    assert enrol_student(client, world, student_id, {"class_section_id": world["section_a"].id, "kind": "excluded"}).status_code == 400

    world["group"].enrolment_policy = "default_for_section"
    db.commit()
    excluded = enrol_student(client, world, student_id, {"subject_group_id": world["group"].id, "kind": "excluded"})
    assert excluded.status_code == 201
    blocked_member = enrol_student(client, world, student_id, {"subject_group_id": world["group"].id})
    assert blocked_member.status_code == 400
    assert "Close the other" in blocked_member.json()["detail"]


def test_teacher_roster_returns_policy_derived_subject_group(db, client, enrolment_world):
    world = enrolment_world
    world["group"].enrolment_policy = "default_for_section"
    student_id = create_student_api(client, world, ref="S-TEACH").json()["id"]
    enrol_student(client, world, student_id, {"class_section_id": world["section_a"].id})
    db.add(
        StaffAssignment(
            school_id=world["alpha"].id,
            membership_id=world["alpha_teacher_membership"].id,
            subject_group_id=world["group"].id,
            role="subject",
            valid_from=invite_tokens.now_utc().date(),
        )
    )
    db.commit()
    roster = client.get(
        f"/api/teach/schools/{world['alpha'].id}/subject-groups/{world['group'].id}/roster",
        headers=bearer(world["alpha_teacher"].email),
    )
    assert roster.status_code == 200
    assert roster.json()["enrolment_policy"] == "default_for_section"
    assert [(row["id"], row["source"], row["enrolment_id"]) for row in roster.json()["students"]] == [(student_id, "default", None)]


def test_bulk_create_section_subject_groups_defaults_to_default_for_section(db, client, enrolment_world):
    world = enrolment_world
    response = client.post(
        "/api/school/subject-groups/bulk-section",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={
            "academic_year_id": world["year"].id,
            "grade_level_id": world["level"].id,
            "subject_id": world["subject"].id,
            "class_section_ids": [world["section_b"].id],
        },
    )
    assert response.status_code == 200
    assert response.json()["created"] == 1
    assert response.json()["results"][0]["subject_group"]["enrolment_policy"] == "default_for_section"


def test_list_students_includes_default_for_section_subject_groups(db, client, enrolment_world):
    world = enrolment_world
    world["group"].enrolment_policy = "default_for_section"
    db.commit()
    in_section = create_student_api(client, world, ref="S-LSA", first="Alya").json()["id"]
    other_section = create_student_api(client, world, ref="S-LSB", first="Badr").json()["id"]
    enrol_student(client, world, in_section, {"class_section_id": world["section_a"].id})
    enrol_student(client, world, other_section, {"class_section_id": world["section_b"].id})

    response = client.get("/api/school/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert response.status_code == 200
    by_id = {row["id"]: row for row in response.json()}
    assert [g["source"] for g in by_id[in_section]["current_subject_groups"]] == ["default"]
    assert by_id[other_section]["current_subject_groups"] == []


def test_list_students_includes_default_for_grade_subject_groups(db, client, enrolment_world):
    world = enrolment_world
    group = SubjectGroup(
        school_id=world["alpha"].id,
        academic_year_id=world["year"].id,
        grade_level_id=world["level"].id,
        subject_id=world["subject"].id,
        code="KG1-ENG",
        name="KG 1 English",
        status="active",
        enrolment_policy="default_for_grade",
    )
    db.add(group)
    db.commit()
    student_a = create_student_api(client, world, ref="S-LGA", first="A").json()["id"]
    student_b = create_student_api(client, world, ref="S-LGB", first="B").json()["id"]
    enrol_student(client, world, student_a, {"class_section_id": world["section_a"].id})
    enrol_student(client, world, student_b, {"class_section_id": world["section_b"].id})

    response = client.get("/api/school/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    by_id = {row["id"]: row for row in response.json()}
    assert group.code in {g["code"] for g in by_id[student_a]["current_subject_groups"]}
    assert group.code in {g["code"] for g in by_id[student_b]["current_subject_groups"]}


def test_list_students_excludes_student_with_exclusion_row(db, client, enrolment_world):
    world = enrolment_world
    world["group"].enrolment_policy = "default_for_section"
    db.commit()
    student_id = create_student_api(client, world, ref="S-LEX").json()["id"]
    enrol_student(client, world, student_id, {"class_section_id": world["section_a"].id})
    excluded = enrol_student(client, world, student_id, {"subject_group_id": world["group"].id, "kind": "excluded"})
    assert excluded.status_code == 201

    response = client.get("/api/school/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    by_id = {row["id"]: row for row in response.json()}
    assert by_id[student_id]["current_subject_groups"] == []


def test_list_students_includes_explicit_only_subject_group(db, client, enrolment_world):
    world = enrolment_world
    student_id = create_student_api(client, world, ref="S-LEXP").json()["id"]
    enrol_student(client, world, student_id, {"class_section_id": world["section_a"].id})
    explicit = enrol_student(client, world, student_id, {"subject_group_id": world["group"].id})
    assert explicit.status_code == 201

    response = client.get("/api/school/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    by_id = {row["id"]: row for row in response.json()}
    assert [(g["source"], g["enrolment_id"]) for g in by_id[student_id]["current_subject_groups"]] == [("explicit", explicit.json()["id"])]


def test_list_students_uses_set_based_subject_group_resolution(db, client, enrolment_world, monkeypatch):
    world = enrolment_world
    world["group"].enrolment_policy = "default_for_section"
    db.commit()
    student_ids = []
    for i in range(5):
        student_id = create_student_api(client, world, ref=f"S-FAN-{i}", first=f"F{i}").json()["id"]
        enrol_student(client, world, student_id, {"class_section_id": world["section_a"].id})
        student_ids.append(student_id)

    expected_group_calls = db.query(SubjectGroup).filter(SubjectGroup.school_id == world["alpha"].id, SubjectGroup.status != "archived").count()
    assert expected_group_calls < len(student_ids)  # otherwise this test can't distinguish per-group from per-student

    import app.rosters as rosters_module

    original = rosters_module.subject_group_members
    calls = {"n": 0}

    def counting_wrapper(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(rosters_module, "subject_group_members", counting_wrapper)

    response = client.get("/api/school/students", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert response.status_code == 200
    assert len(response.json()) == len(student_ids)
    # Whole-school resolution no longer calls the single-group helper at all;
    # query-count scaling is asserted directly in test_roster_resolution.py.
    assert calls["n"] == 0


def test_enrolment_date_validation(db, client, enrolment_world):
    world = enrolment_world
    student_id = create_student_api(client, world).json()["id"]
    tomorrow = (invite_tokens.now_utc().date() + timedelta(days=1)).isoformat()
    yesterday = (invite_tokens.now_utc().date() - timedelta(days=1)).isoformat()
    assert client.post(
        f"/api/school/students/{student_id}/enrolments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"class_section_id": world["section_a"].id, "valid_from": tomorrow},
    ).status_code == 400
    row = client.post(
        f"/api/school/students/{student_id}/enrolments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"class_section_id": world["section_a"].id},
    ).json()
    assert client.request(
        "DELETE",
        f"/api/school/enrolments/{row['id']}",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"valid_to": yesterday},
    ).status_code == 400


def test_teacher_rosters_assignment_scope_and_archived_students(db, client, enrolment_world):
    world = enrolment_world
    student_id = create_student_api(client, world).json()["id"]
    client.post(f"/api/school/students/{student_id}/enrolments", headers=bearer(world["alpha_admin"].email, world["alpha"].id), json={"class_section_id": world["section_a"].id})
    client.post(f"/api/school/students/{student_id}/enrolments", headers=bearer(world["alpha_admin"].email, world["alpha"].id), json={"subject_group_id": world["group"].id})
    section_assignment = StaffAssignment(
        school_id=world["alpha"].id,
        membership_id=world["alpha_teacher_membership"].id,
        class_section_id=world["section_a"].id,
        role="homeroom",
        valid_from=invite_tokens.now_utc().date(),
    )
    group_assignment = StaffAssignment(
        school_id=world["alpha"].id,
        membership_id=world["alpha_teacher_membership"].id,
        subject_group_id=world["group"].id,
        role="subject",
        valid_from=invite_tokens.now_utc().date(),
    )
    db.add_all([section_assignment, group_assignment])
    db.commit()

    section_roster = client.get(
        f"/api/teach/schools/{world['alpha'].id}/sections/{world['section_a'].id}/roster",
        headers=bearer(world["alpha_teacher"].email),
    )
    assert section_roster.status_code == 200
    assert [row["id"] for row in section_roster.json()["students"]] == [student_id]
    group_roster = client.get(
        f"/api/teach/schools/{world['alpha'].id}/subject-groups/{world['group'].id}/roster",
        headers=bearer(world["alpha_teacher"].email),
    )
    assert group_roster.status_code == 200
    assert [row["id"] for row in group_roster.json()["students"]] == [student_id]

    assert client.get(f"/api/teach/schools/{world['alpha'].id}/sections/{world['section_a'].id}/roster", headers=bearer(world["other_teacher"].email)).status_code == 403
    section_assignment.valid_to = invite_tokens.now_utc().date()
    db.commit()
    assert client.get(f"/api/teach/schools/{world['alpha'].id}/sections/{world['section_a'].id}/roster", headers=bearer(world["alpha_teacher"].email)).status_code == 403
    assert client.get(f"/api/teach/schools/{world['alpha'].id}/sections/{world['section_a'].id}/roster", headers=bearer(world["beta_teacher"].email)).status_code == 403
    assert client.get(f"/api/teach/schools/{world['alpha'].id}/sections/{world['section_a'].id}/roster", headers=bearer(world["no_role"].email)).status_code == 403


def test_teacher_subject_group_roster_empty_and_dashboard_target_type(db, client, enrolment_world):
    world = enrolment_world
    db.add(
        StaffAssignment(
            school_id=world["alpha"].id,
            membership_id=world["alpha_teacher_membership"].id,
            subject_group_id=world["group"].id,
            role="subject",
            valid_from=invite_tokens.now_utc().date(),
        )
    )
    db.commit()

    dashboard = client.get("/api/teach/dashboard", headers=bearer(world["alpha_teacher"].email))
    assert dashboard.status_code == 200
    subject_cards = [row for row in dashboard.json()["assignments"] if row["subject_group"]]
    assert len(subject_cards) == 1
    assert subject_cards[0]["target_type"] == "subject_group"
    assert subject_cards[0]["class_section"]["id"] == world["section_a"].id

    group_roster = client.get(
        f"/api/teach/schools/{world['alpha'].id}/subject-groups/{world['group'].id}/roster",
        headers=bearer(world["alpha_teacher"].email),
    )
    assert group_roster.status_code == 200
    assert group_roster.json()["students"] == []

    not_assigned = client.get(
        f"/api/teach/schools/{world['alpha'].id}/subject-groups/{world['group'].id}/roster",
        headers=bearer(world["other_teacher"].email),
    )
    assert not_assigned.status_code == 403


def _add_classroom_students(db, world):
    students = [
        Student(school_id=world["alpha"].id, external_ref="AV-M1", first_name="Adam", last_name="One", gender="male"),
        Student(school_id=world["alpha"].id, external_ref="AV-M2", first_name="Basil", last_name="Two", gender="male"),
        Student(school_id=world["alpha"].id, external_ref="AV-F1", first_name="Clara", last_name="Three", gender="female"),
        Student(school_id=world["alpha"].id, external_ref="AV-U1", first_name="Dana", last_name="Four", gender="unspecified"),
        Student(school_id=world["alpha"].id, external_ref="OFF-ROSTER", first_name="Hidden", last_name="Student", gender="female"),
    ]
    db.add_all(students)
    db.flush()
    for student in students[:4]:
        db.add(Enrolment(school_id=world["alpha"].id, student_id=student.id, class_section_id=world["section_a"].id, kind="member", valid_from=invite_tokens.now_utc().date()))
    assignment = StaffAssignment(
        school_id=world["alpha"].id,
        membership_id=world["alpha_teacher_membership"].id,
        class_section_id=world["section_a"].id,
        role="homeroom",
        valid_from=invite_tokens.now_utc().date(),
    )
    db.add(assignment)
    db.commit()
    return students, assignment


def test_teacher_class_detail_assigns_stable_gender_aware_unique_avatars(db, client, enrolment_world):
    world = enrolment_world
    students, assignment = _add_classroom_students(db, world)

    first = client.get(f"/api/teach/assignments/{assignment.id}", headers=bearer(world["alpha_teacher"].email))
    assert first.status_code == 200
    body = first.json()
    assert body["assignment"]["role"] == "homeroom"
    assert body["assignment"]["target_type"] == "class_section"
    assert body["assignment"]["school"]["name"] == "Alpha Academy"
    assert body["assignment"]["class_section"]["name"] == "KG 1 A"
    assert body["student_count"] == 4
    assert {row["id"] for row in body["students"]} == {student.id for student in students[:4]}
    assert students[4].id not in {row["id"] for row in body["students"]}

    by_id = {row["id"]: row for row in body["students"]}
    assert 31 <= by_id[students[0].id]["avatar_id"] <= 60
    assert 31 <= by_id[students[1].id]["avatar_id"] <= 60
    assert by_id[students[2].id]["avatar_id"] in {*range(61, 74), *range(75, 91)}
    assert by_id[students[3].id]["avatar_id"] in {*range(31, 74), *range(75, 91)}
    assert 74 not in {row["avatar_id"] for row in body["students"]}
    assert len({row["avatar_id"] for row in body["students"]}) == 4
    for row in body["students"]:
        assert row["points_total"] == 0
        assert row["avatar_url_128"] == f"/avatars/128/{row['avatar_id']}-128.webp"
        assert row["avatar_url_256"] == f"/avatars/256/{row['avatar_id']}-256.webp"

    second = client.get(f"/api/teach/assignments/{assignment.id}", headers=bearer(world["alpha_teacher"].email))
    assert {row["id"]: row["avatar_id"] for row in second.json()["students"]} == {
        row["id"]: row["avatar_id"] for row in body["students"]
    }

    serialized = str(body).lower()
    for forbidden in ("guardian", "email", "phone", "invite", "token", "hash", "external_ref", "date_of_birth", "gender"):
        assert forbidden not in serialized


def test_teacher_class_detail_batches_persisted_point_totals_and_excludes_reversals(db, client, enrolment_world):
    world = enrolment_world
    students, assignment = _add_classroom_students(db, world)
    positive = BehaviourCategory(school_id=world["alpha"].id, type="positive", label="Great effort", points_value=2, active=True)
    needs_work = BehaviourCategory(school_id=world["alpha"].id, type="needs_work", label="Off-task", points_value=-1, active=True)
    db.add_all([positive, needs_work])
    db.flush()
    db.add_all([
        BehaviourEvent(school_id=world["alpha"].id, student_id=students[0].id, category_id=positive.id, actor_user_id=world["alpha_teacher"].id, points_delta=2, source="teacher"),
        BehaviourEvent(school_id=world["alpha"].id, student_id=students[0].id, category_id=needs_work.id, actor_user_id=world["alpha_teacher"].id, points_delta=-1, source="teacher"),
        BehaviourEvent(school_id=world["alpha"].id, student_id=students[1].id, category_id=positive.id, actor_user_id=world["alpha_teacher"].id, points_delta=2, source="teacher", reversed_at=datetime.now(timezone.utc)),
    ])
    db.commit()

    response = client.get(f"/api/teach/assignments/{assignment.id}", headers=bearer(world["alpha_teacher"].email))
    assert response.status_code == 200
    totals = {row["id"]: row["points_total"] for row in response.json()["students"]}
    assert totals[students[0].id] == 1
    assert totals[students[1].id] == 0
    assert totals[students[2].id] == 0

    # An active teacher in another school cannot open this assignment or see its totals.
    assert client.get(f"/api/teach/assignments/{assignment.id}", headers=bearer(world["beta_teacher"].email)).status_code == 403


def test_teacher_subject_group_detail_is_scoped_to_active_assignment(db, client, enrolment_world):
    world = enrolment_world
    included = Student(school_id=world["alpha"].id, external_ref="SUB-IN", first_name="Group", last_name="Member", gender="female")
    excluded = Student(school_id=world["alpha"].id, external_ref="SUB-OUT", first_name="Other", last_name="Student", gender="male")
    db.add_all([included, excluded])
    db.flush()
    db.add(Enrolment(school_id=world["alpha"].id, student_id=included.id, subject_group_id=world["group"].id, kind="member", valid_from=invite_tokens.now_utc().date()))
    assignment = StaffAssignment(
        school_id=world["alpha"].id,
        membership_id=world["alpha_teacher_membership"].id,
        subject_group_id=world["group"].id,
        role="subject",
        valid_from=invite_tokens.now_utc().date(),
    )
    db.add(assignment)
    db.commit()

    response = client.get(f"/api/teach/assignments/{assignment.id}", headers=bearer(world["alpha_teacher"].email))
    assert response.status_code == 200
    assert response.json()["assignment"]["target_type"] == "subject_group"
    assert response.json()["assignment"]["subject_group"]["name"] == "KG 1 A English"
    assert [row["id"] for row in response.json()["students"]] == [included.id]
    assert client.get(f"/api/teach/assignments/{assignment.id}", headers=bearer(world["other_teacher"].email)).status_code == 403

    assignment.valid_to = invite_tokens.now_utc().date()
    db.commit()
    assert client.get(f"/api/teach/assignments/{assignment.id}", headers=bearer(world["alpha_teacher"].email)).status_code == 403


def test_teacher_cannot_guess_another_school_assignment_detail(db, client, enrolment_world):
    world = enrolment_world
    beta_assignment = StaffAssignment(
        school_id=world["beta"].id,
        membership_id=world["beta_teacher_membership"].id,
        class_section_id=world["beta_section"].id,
        role="homeroom",
        valid_from=invite_tokens.now_utc().date(),
    )
    db.add(beta_assignment)
    db.commit()
    assert client.get(f"/api/teach/assignments/{beta_assignment.id}", headers=bearer(world["alpha_teacher"].email)).status_code == 403
    assert client.get(f"/api/teach/assignments/{beta_assignment.id}", headers=bearer(world["beta_teacher"].email)).status_code == 200


def test_staff_assignment_date_validation_and_deactivated_invite_revoke(db, client, enrolment_world):
    world = enrolment_world
    tomorrow = (invite_tokens.now_utc().date() + timedelta(days=1)).isoformat()
    yesterday = (invite_tokens.now_utc().date() - timedelta(days=1)).isoformat()
    future = client.post(
        f"/api/school/teachers/{world['alpha_teacher_membership'].id}/assignments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"role": "homeroom", "class_section_id": world["section_a"].id, "valid_from": tomorrow},
    )
    assert future.status_code == 400
    assignment = client.post(
        f"/api/school/teachers/{world['alpha_teacher_membership'].id}/assignments",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"role": "homeroom", "class_section_id": world["section_a"].id},
    ).json()
    assert client.request(
        "DELETE",
        f"/api/school/assignments/{assignment['id']}",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json={"valid_to": yesterday},
    ).status_code == 400

    invite = StaffInvite(
        school_id=world["alpha"].id,
        email=world["alpha_teacher"].email,
        role="teacher",
        token_hash=invite_tokens.hash_token("pending-token"),
        invited_by_user_id=world["alpha_admin"].id,
        expires_at=invite_tokens.now_utc() + timedelta(days=1),
    )
    db.add(invite)
    db.commit()
    deactivated = client.post(
        f"/api/school/teachers/{world['alpha_teacher_membership'].id}/deactivate",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["revoked_invites"] == 1
    db.expire_all()
    assert db.query(StaffInvite).filter_by(id=invite.id).one().revoked_at is not None

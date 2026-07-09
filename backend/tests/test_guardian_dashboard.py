import os

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
    BranchCampus,
    ClassSection,
    Enrolment,
    GradeLevel,
    GuardianLink,
    Membership,
    School,
    Student,
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


def bearer(email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth.create_access_token({'sub': email})}"}


def create_user(db, email: str, name: str) -> User:
    user = User(email=email, name=name, google_sub=f"sub-{email}")
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def world(db):
    guardian = create_user(db, "fatima@example.com", "Fatima Ahmed")
    other_guardian = create_user(db, "other@example.com", "Other Guardian")
    alpha_teacher = create_user(db, "teacher@example.com", "Alpha Teacher")

    alpha = School(name="Alpha Academy", slug="alpha", status="active")
    beta = School(name="Beta School", slug="beta", status="active")
    db.add_all([alpha, beta])
    db.flush()

    db.add(Membership(school_id=alpha.id, user_id=alpha_teacher.id, role="teacher"))

    alpha_branch = BranchCampus(school_id=alpha.id, code="MAIN", name="Main", status="active")
    beta_branch = BranchCampus(school_id=beta.id, code="MAIN", name="Main", status="active")
    db.add_all([alpha_branch, beta_branch])
    db.flush()

    alpha_year = AcademicYear(school_id=alpha.id, code="2026", name="2026", status="active", is_current=True)
    beta_year = AcademicYear(school_id=beta.id, code="2026", name="2026", status="active", is_current=True)
    db.add_all([alpha_year, beta_year])
    db.flush()

    alpha_level = GradeLevel(school_id=alpha.id, code="KG1", name="KG 1", status="active")
    beta_level = GradeLevel(school_id=beta.id, code="G1", name="Grade 1", status="active")
    db.add_all([alpha_level, beta_level])
    db.flush()

    alpha_section = ClassSection(
        school_id=alpha.id,
        branch_campus_id=alpha_branch.id,
        academic_year_id=alpha_year.id,
        grade_level_id=alpha_level.id,
        code="A",
        name="KG 1 A",
        status="active",
    )
    beta_section = ClassSection(
        school_id=beta.id,
        branch_campus_id=beta_branch.id,
        academic_year_id=beta_year.id,
        grade_level_id=beta_level.id,
        code="A",
        name="Grade 1 A",
        status="active",
    )
    db.add_all([alpha_section, beta_section])
    db.flush()

    sara = Student(school_id=alpha.id, external_ref="S1", first_name="Sara", last_name="Ahmed", status="active")
    omar = Student(school_id=alpha.id, external_ref="S2", first_name="Omar", last_name="Ahmed", status="active")
    layla = Student(school_id=beta.id, external_ref="B1", first_name="Layla", last_name="Beta", status="active")
    other_child = Student(school_id=alpha.id, external_ref="S3", first_name="Zayd", last_name="Other", status="active")
    db.add_all([sara, omar, layla, other_child])
    db.flush()

    db.add_all(
        [
            Enrolment(school_id=alpha.id, student_id=sara.id, class_section_id=alpha_section.id, kind="member"),
            Enrolment(school_id=alpha.id, student_id=omar.id, class_section_id=alpha_section.id, kind="member"),
            Enrolment(school_id=beta.id, student_id=layla.id, class_section_id=beta_section.id, kind="member"),
            Enrolment(school_id=alpha.id, student_id=other_child.id, class_section_id=alpha_section.id, kind="member"),
        ]
    )
    db.commit()
    return locals()


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    from app.routes.join import JOIN_RATE_LIMITER

    JOIN_RATE_LIMITER._attempts.clear()
    yield


def link_guardian(db, *, school_id, student_id, user_id, relationship="mother", status="active", email_matched=None):
    link = GuardianLink(
        school_id=school_id,
        student_id=student_id,
        user_id=user_id,
        relationship=relationship,
        display_name=None,
        status=status,
        email_matched_contact=email_matched,
    )
    db.add(link)
    existing_membership = (
        db.query(Membership)
        .filter(Membership.school_id == school_id, Membership.user_id == user_id, Membership.role == "guardian")
        .first()
    )
    if not existing_membership:
        db.add(Membership(school_id=school_id, user_id=user_id, role="guardian", status="active"))
    db.commit()
    db.refresh(link)
    return link


def test_unauthenticated_guardian_dashboard_blocked(client):
    resp = client.get("/api/guardian/dashboard")
    assert resp.status_code == 401


def test_guardian_with_one_active_link_sees_only_that_child(db, client, world):
    link_guardian(db, school_id=world["alpha"].id, student_id=world["sara"].id, user_id=world["guardian"].id, relationship="mother", email_matched=True)

    resp = client.get("/api/guardian/dashboard", headers=bearer(world["guardian"].email))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["children"]) == 1
    child = body["children"][0]
    assert child["student_id"] == world["sara"].id
    assert child["first_name"] == "Sara"
    assert child["last_name"] == "Ahmed"
    assert child["display_name"] == "Sara Ahmed"
    assert child["initials"] == "SA"
    assert child["school_name"] == "Alpha Academy"
    assert child["class_section_name"] == "KG 1 A"
    assert child["grade_level_name"] == "KG 1"
    assert child["relationship"] == "mother"
    assert child["link_status"] == "active"
    assert child["email_matched_contact"] is True


def test_guardian_with_multiple_active_links_sees_multiple_children(db, client, world):
    link_guardian(db, school_id=world["alpha"].id, student_id=world["sara"].id, user_id=world["guardian"].id)
    link_guardian(db, school_id=world["alpha"].id, student_id=world["omar"].id, user_id=world["guardian"].id, relationship="father")

    resp = client.get("/api/guardian/dashboard", headers=bearer(world["guardian"].email))
    assert resp.status_code == 200
    body = resp.json()
    assert {child["student_id"] for child in body["children"]} == {world["sara"].id, world["omar"].id}


def test_guardian_cannot_see_another_guardians_child(db, client, world):
    link_guardian(db, school_id=world["alpha"].id, student_id=world["other_child"].id, user_id=world["other_guardian"].id)
    link_guardian(db, school_id=world["alpha"].id, student_id=world["sara"].id, user_id=world["guardian"].id)

    resp = client.get("/api/guardian/dashboard", headers=bearer(world["guardian"].email))
    assert resp.status_code == 200
    body = resp.json()
    assert {child["student_id"] for child in body["children"]} == {world["sara"].id}


def test_revoked_guardian_link_does_not_show(db, client, world):
    active_link = link_guardian(db, school_id=world["alpha"].id, student_id=world["sara"].id, user_id=world["guardian"].id)
    link_guardian(db, school_id=world["alpha"].id, student_id=world["omar"].id, user_id=world["guardian"].id)

    revoked = db.query(GuardianLink).filter(GuardianLink.student_id == world["omar"].id).one()
    revoked.status = "revoked"
    revoked.revoked_at = invite_tokens.now_utc()
    db.commit()

    resp = client.get("/api/guardian/dashboard", headers=bearer(world["guardian"].email))
    assert resp.status_code == 200
    body = resp.json()
    assert {child["student_id"] for child in body["children"]} == {world["sara"].id}
    assert active_link.status == "active"


def test_cross_school_isolation(db, client, world):
    link_guardian(db, school_id=world["alpha"].id, student_id=world["sara"].id, user_id=world["guardian"].id)
    link_guardian(db, school_id=world["beta"].id, student_id=world["layla"].id, user_id=world["guardian"].id)

    resp = client.get("/api/guardian/dashboard", headers=bearer(world["guardian"].email))
    assert resp.status_code == 200
    body = resp.json()
    schools = {child["school_name"] for child in body["children"]}
    assert schools == {"Alpha Academy", "Beta School"}
    assert len(body["children"]) == 2


def test_school_membership_alone_does_not_grant_dashboard_access(db, client, world):
    resp = client.get("/api/guardian/dashboard", headers=bearer(world["alpha_teacher"].email))
    assert resp.status_code == 200
    body = resp.json()
    assert body["children"] == []


def test_response_includes_expected_fields_and_no_invite_details(db, client, world):
    link_guardian(db, school_id=world["alpha"].id, student_id=world["sara"].id, user_id=world["guardian"].id)

    resp = client.get("/api/guardian/dashboard", headers=bearer(world["guardian"].email))
    body = resp.json()
    child = body["children"][0]
    serialized = str(child)
    assert "token" not in serialized.lower()
    assert "code" not in serialized.lower()
    assert "hash" not in serialized.lower()
    for field in (
        "student_id",
        "first_name",
        "last_name",
        "display_name",
        "initials",
        "school_id",
        "school_name",
        "class_section_name",
        "grade_level_name",
        "relationship",
        "link_status",
        "email_matched_contact",
    ):
        assert field in child


# --- Nav/role-summary coverage ---------------------------------------------
#
# Frontend nav visibility ("show a Family link if this account has guardian
# access") is derived entirely from the existing GET /api/me payload's
# memberships list, since linking a guardian already creates an active
# Membership(role="guardian") in lockstep with the GuardianLink (see
# join.py's _ensure_guardian_membership). No new backend endpoint/field was
# needed; these tests pin down that the existing /me payload already carries
# what the nav needs, and that it never leaks invite/token/code data.


def test_guardian_linked_user_has_guardian_role_in_me_payload(db, client, world):
    link_guardian(db, school_id=world["alpha"].id, student_id=world["sara"].id, user_id=world["guardian"].id)

    resp = client.get("/api/me", headers=bearer(world["guardian"].email))
    assert resp.status_code == 200
    roles = {membership["role"] for membership in resp.json()["memberships"]}
    assert "guardian" in roles


def test_user_with_no_guardian_link_has_no_guardian_role_in_me_payload(db, client, world):
    resp = client.get("/api/me", headers=bearer(world["alpha_teacher"].email))
    assert resp.status_code == 200
    roles = {membership["role"] for membership in resp.json()["memberships"]}
    assert "guardian" not in roles
    assert "teacher" in roles


def test_multi_role_user_can_access_both_teach_and_parent_dashboard(db, client, world):
    # alpha_teacher already has a teacher membership from the world fixture;
    # linking them as a guardian too must not disturb that membership or
    # either endpoint's own scope check.
    link_guardian(db, school_id=world["alpha"].id, student_id=world["sara"].id, user_id=world["alpha_teacher"].id)

    me_resp = client.get("/api/me", headers=bearer(world["alpha_teacher"].email))
    roles = {membership["role"] for membership in me_resp.json()["memberships"]}
    assert roles == {"teacher", "guardian"}

    teach_resp = client.get(
        "/api/teach/dashboard",
        headers={**bearer(world["alpha_teacher"].email), "X-School-Id": str(world["alpha"].id)},
    )
    assert teach_resp.status_code == 200

    dashboard_resp = client.get("/api/guardian/dashboard", headers=bearer(world["alpha_teacher"].email))
    assert dashboard_resp.status_code == 200
    assert {child["student_id"] for child in dashboard_resp.json()["children"]} == {world["sara"].id}


def test_me_payload_exposes_no_invite_token_or_code_data(db, client, world):
    link_guardian(db, school_id=world["alpha"].id, student_id=world["sara"].id, user_id=world["guardian"].id)

    resp = client.get("/api/me", headers=bearer(world["guardian"].email))
    serialized = str(resp.json()).lower()
    assert "token" not in serialized
    assert "code" not in serialized
    assert "hash" not in serialized

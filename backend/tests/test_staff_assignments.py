import os
from datetime import timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database, invite_tokens
from app.database import Base, get_db
from app.main import app
from app.models_school import (
    AcademicYear,
    AuditLog,
    BranchCampus,
    ClassSection,
    GradeLevel,
    Membership,
    PlatformAdmin,
    School,
    StaffAssignment,
    StaffInvite,
    Subject,
    SubjectGroup,
    User,
)
from app.school_scope import require_teacher_of


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


def token_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def create_user(db, email: str, name: str) -> User:
    user = User(email=email, name=name, google_sub=f"sub-{email}")
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def staff_world(db):
    platform = create_user(db, "platform@example.com", "Platform")
    alpha_admin = create_user(db, "alpha-admin@example.com", "Alpha Admin")
    beta_admin = create_user(db, "beta-admin@example.com", "Beta Admin")
    alpha_teacher = create_user(db, "alpha-teacher@example.com", "Alpha Teacher")
    other_teacher = create_user(db, "other-teacher@example.com", "Other Teacher")
    no_role = create_user(db, "no-role@example.com", "No Role")

    alpha = School(name="Alpha Academy", slug="alpha", status="active")
    beta = School(name="Beta School", slug="beta", status="active")
    db.add_all([alpha, beta])
    db.flush()

    alpha_admin_membership = Membership(school_id=alpha.id, user_id=alpha_admin.id, role="school_admin", created_by_user_id=platform.id)
    beta_admin_membership = Membership(school_id=beta.id, user_id=beta_admin.id, role="school_admin", created_by_user_id=platform.id)
    alpha_teacher_membership = Membership(school_id=alpha.id, user_id=alpha_teacher.id, role="teacher", created_by_user_id=alpha_admin.id)
    other_teacher_membership = Membership(school_id=alpha.id, user_id=other_teacher.id, role="teacher", created_by_user_id=alpha_admin.id)
    db.add_all(
        [
            PlatformAdmin(user_id=platform.id),
            alpha_admin_membership,
            beta_admin_membership,
            alpha_teacher_membership,
            other_teacher_membership,
        ]
    )
    db.flush()

    branch = BranchCampus(school_id=alpha.id, code="MAIN", name="Main", status="active")
    year = AcademicYear(school_id=alpha.id, code="2026", name="2026", status="active", is_current=True)
    level = GradeLevel(school_id=alpha.id, code="Y1", name="Year 1", status="active")
    subject = Subject(school_id=alpha.id, code="ENG", name="English", status="active")
    db.add_all([branch, year, level, subject])
    db.flush()
    section = ClassSection(
        school_id=alpha.id,
        branch_campus_id=branch.id,
        academic_year_id=year.id,
        grade_level_id=level.id,
        code="RED",
        name="Year 1 Red",
        status="active",
    )
    inactive_section = ClassSection(
        school_id=alpha.id,
        branch_campus_id=branch.id,
        academic_year_id=year.id,
        grade_level_id=level.id,
        code="BLUE",
        name="Year 1 Blue",
        status="inactive",
    )
    db.add_all([section, inactive_section])
    db.flush()
    group = SubjectGroup(
        school_id=alpha.id,
        academic_year_id=year.id,
        class_section_id=section.id,
        subject_id=subject.id,
        code="Y1RED-ENG",
        name="Year 1 Red English",
        status="active",
    )
    archived_group = SubjectGroup(
        school_id=alpha.id,
        academic_year_id=year.id,
        class_section_id=section.id,
        subject_id=subject.id,
        code="OLD-ENG",
        name="Old English",
        status="archived",
    )
    db.add_all([group, archived_group])
    db.commit()

    return {
        "platform": platform,
        "alpha": alpha,
        "beta": beta,
        "alpha_admin": alpha_admin,
        "beta_admin": beta_admin,
        "alpha_teacher": alpha_teacher,
        "other_teacher": other_teacher,
        "no_role": no_role,
        "alpha_teacher_membership": alpha_teacher_membership,
        "other_teacher_membership": other_teacher_membership,
        "section": section,
        "inactive_section": inactive_section,
        "group": group,
        "archived_group": archived_group,
    }


def test_school_admin_invites_teacher_and_exchange_creates_teacher_membership(db, client, staff_world, monkeypatch):
    sent = []
    monkeypatch.setattr("app.routes.platform.send_staff_invite", lambda email: sent.append(email))

    alpha = staff_world["alpha"]
    admin = staff_world["alpha_admin"]
    response = client.post(
        "/api/school/teachers/invites",
        headers=bearer(admin.email, alpha.id),
        json={"email": "new-teacher@example.com"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "teacher"
    assert sent[-1].to_email == "new-teacher@example.com"
    token = token_from_url(sent[-1].accept_url)

    wrong_user = create_user(db, "wrong@example.com", "Wrong")
    mismatch = client.post("/api/invites/exchange", headers=bearer(wrong_user.email), json={"token": token})
    assert mismatch.status_code == 403

    invited = create_user(db, "new-teacher@example.com", "New Teacher")
    accepted = client.post("/api/invites/exchange", headers=bearer(invited.email), json={"token": token})
    assert accepted.status_code == 200
    assert accepted.json()["membership"]["role"] == "teacher"
    assert accepted.json()["landing_path"] == "/teach"
    assert db.query(Membership).filter_by(school_id=alpha.id, user_id=invited.id, role="teacher").one().status == "active"

    reused = client.post("/api/invites/exchange", headers=bearer(invited.email), json={"token": token})
    assert reused.status_code == 410
    assert "staff_invite.accepted" in {row.action for row in db.query(AuditLog).all()}


def test_teacher_invite_duplicate_revoke_expired_and_suspended_school_behaviour(db, client, staff_world, monkeypatch):
    sent = []
    monkeypatch.setattr("app.routes.platform.send_staff_invite", lambda email: sent.append(email))
    alpha = staff_world["alpha"]
    admin = staff_world["alpha_admin"]

    first = client.post("/api/school/teachers/invites", headers=bearer(admin.email, alpha.id), json={"email": "dup@example.com"})
    second = client.post("/api/school/teachers/invites", headers=bearer(admin.email, alpha.id), json={"email": "dup@example.com"})
    assert first.status_code == 201
    assert second.status_code == 201
    assert db.query(StaffInvite).filter_by(id=first.json()["id"]).one().revoked_at is not None

    revoke = client.delete(f"/api/school/teachers/invites/{second.json()['id']}", headers=bearer(admin.email, alpha.id))
    assert revoke.status_code == 204
    revoked_user = create_user(db, "dup@example.com", "Dup")
    revoked_exchange = client.post("/api/invites/exchange", headers=bearer(revoked_user.email), json={"token": token_from_url(sent[-1].accept_url)})
    assert revoked_exchange.status_code == 410

    expired = client.post("/api/school/teachers/invites", headers=bearer(admin.email, alpha.id), json={"email": "expired@example.com"})
    expired_invite = db.query(StaffInvite).filter_by(id=expired.json()["id"]).one()
    expired_invite.expires_at = invite_tokens.now_utc() - timedelta(minutes=1)
    db.commit()
    expired_user = create_user(db, "expired@example.com", "Expired")
    assert client.post("/api/invites/exchange", headers=bearer(expired_user.email), json={"token": token_from_url(sent[-1].accept_url)}).status_code == 410

    suspended = client.post("/api/school/teachers/invites", headers=bearer(admin.email, alpha.id), json={"email": "suspended@example.com"})
    alpha.status = "suspended"
    db.commit()
    suspended_user = create_user(db, "suspended@example.com", "Suspended")
    assert client.post("/api/invites/exchange", headers=bearer(suspended_user.email), json={"token": token_from_url(sent[-1].accept_url)}).status_code == 403
    alpha.status = "active"
    db.commit()

    active_member_invite = client.post("/api/school/teachers/invites", headers=bearer(admin.email, alpha.id), json={"email": staff_world["alpha_teacher"].email})
    assert active_member_invite.status_code == 409


def test_assignment_create_close_reassign_target_validation_and_dashboard(db, client, staff_world):
    alpha = staff_world["alpha"]
    admin = staff_world["alpha_admin"]
    teacher_membership = staff_world["alpha_teacher_membership"]
    other_membership = staff_world["other_teacher_membership"]
    section = staff_world["section"]
    group = staff_world["group"]

    homeroom = client.post(
        f"/api/school/teachers/{teacher_membership.id}/assignments",
        headers=bearer(admin.email, alpha.id),
        json={"role": "homeroom", "class_section_id": section.id},
    )
    assert homeroom.status_code == 201
    duplicate_same = client.post(
        f"/api/school/teachers/{teacher_membership.id}/assignments",
        headers=bearer(admin.email, alpha.id),
        json={"role": "homeroom", "class_section_id": section.id},
    )
    assert duplicate_same.status_code == 409
    duplicate_other = client.post(
        f"/api/school/teachers/{other_membership.id}/assignments",
        headers=bearer(admin.email, alpha.id),
        json={"role": "homeroom", "class_section_id": section.id},
    )
    assert duplicate_other.status_code == 409

    subject = client.post(
        f"/api/school/teachers/{teacher_membership.id}/assignments",
        headers=bearer(admin.email, alpha.id),
        json={"role": "subject", "subject_group_id": group.id},
    )
    assert subject.status_code == 201

    inactive = client.post(
        f"/api/school/teachers/{teacher_membership.id}/assignments",
        headers=bearer(admin.email, alpha.id),
        json={"role": "homeroom", "class_section_id": staff_world["inactive_section"].id},
    )
    assert inactive.status_code == 400
    archived = client.post(
        f"/api/school/teachers/{teacher_membership.id}/assignments",
        headers=bearer(admin.email, alpha.id),
        json={"role": "subject", "subject_group_id": staff_world["archived_group"].id},
    )
    assert archived.status_code == 400

    dashboard = client.get("/api/teach/dashboard", headers=bearer(staff_world["alpha_teacher"].email))
    assert dashboard.status_code == 200
    assert {card["role"] for card in dashboard.json()["assignments"]} == {"homeroom", "subject"}
    assert client.get("/api/teach/dashboard", headers=bearer(staff_world["other_teacher"].email)).json()["assignments"] == []
    assert client.get("/api/teach/dashboard", headers=bearer(staff_world["no_role"].email)).status_code == 403

    close = client.delete(f"/api/school/assignments/{subject.json()['id']}", headers=bearer(admin.email, alpha.id))
    assert close.status_code == 200
    assert close.json()["valid_to"] is not None
    assert {card["role"] for card in client.get("/api/teach/dashboard", headers=bearer(staff_world["alpha_teacher"].email)).json()["assignments"]} == {"homeroom"}

    new_section = ClassSection(
        school_id=alpha.id,
        branch_campus_id=section.branch_campus_id,
        academic_year_id=section.academic_year_id,
        grade_level_id=section.grade_level_id,
        code="GREEN",
        name="Year 1 Green",
        status="active",
    )
    db.add(new_section)
    db.commit()
    reassigned = client.post(
        f"/api/school/teachers/{teacher_membership.id}/assignments",
        headers=bearer(admin.email, alpha.id),
        json={"role": "homeroom", "class_section_id": new_section.id},
    )
    assert reassigned.status_code == 201
    old_homeroom = db.query(StaffAssignment).filter_by(id=homeroom.json()["id"]).one()
    assert old_homeroom.valid_to is not None
    assert db.query(StaffAssignment).filter_by(membership_id=teacher_membership.id, role="homeroom").count() == 2

    actions = {row.action for row in db.query(AuditLog).all()}
    assert {"school.staff_assignment.created", "school.staff_assignment.closed"}.issubset(actions)


def test_batch_teacher_assignments_grouped_by_membership_and_permission_boundaries(db, client, staff_world):
    alpha = staff_world["alpha"]
    admin = staff_world["alpha_admin"]
    teacher_membership = staff_world["alpha_teacher_membership"]
    other_membership = staff_world["other_teacher_membership"]
    section = staff_world["section"]

    homeroom = client.post(
        f"/api/school/teachers/{teacher_membership.id}/assignments",
        headers=bearer(admin.email, alpha.id),
        json={"role": "homeroom", "class_section_id": section.id},
    )
    assert homeroom.status_code == 201

    batch = client.get("/api/school/teachers/assignments", headers=bearer(admin.email, alpha.id))
    assert batch.status_code == 200
    body = batch.json()
    assert set(body.keys()) == {str(teacher_membership.id), str(other_membership.id)}
    assert [row["id"] for row in body[str(teacher_membership.id)]] == [homeroom.json()["id"]]
    assert body[str(other_membership.id)] == []

    assert client.get("/api/school/teachers/assignments", headers=bearer(staff_world["alpha_teacher"].email, alpha.id)).status_code == 403
    assert client.get("/api/school/teachers/assignments", headers=bearer(staff_world["no_role"].email, alpha.id)).status_code == 403
    assert client.get("/api/school/teachers/assignments", headers=bearer(staff_world["beta_admin"].email, alpha.id)).status_code == 403


def test_school_admin_permission_boundaries_and_deactivation(db, client, staff_world):
    alpha = staff_world["alpha"]
    teacher_membership = staff_world["alpha_teacher_membership"]
    section = staff_world["section"]

    platform_denied = client.get("/api/school/teachers", headers=bearer(staff_world["platform"].email, alpha.id))
    assert platform_denied.status_code == 403
    teacher_denied = client.get("/api/school/teachers", headers=bearer(staff_world["alpha_teacher"].email, alpha.id))
    assert teacher_denied.status_code == 403
    wrong_school = client.post(
        f"/api/school/teachers/{teacher_membership.id}/assignments",
        headers=bearer(staff_world["beta_admin"].email, staff_world["beta"].id),
        json={"role": "homeroom", "class_section_id": section.id},
    )
    assert wrong_school.status_code == 404

    assignment = client.post(
        f"/api/school/teachers/{teacher_membership.id}/assignments",
        headers=bearer(staff_world["alpha_admin"].email, alpha.id),
        json={"role": "homeroom", "class_section_id": section.id},
    )
    assert assignment.status_code == 201
    deactivated = client.post(
        f"/api/school/teachers/{teacher_membership.id}/deactivate",
        headers=bearer(staff_world["alpha_admin"].email, alpha.id),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["closed_assignments"] == 1
    db.expire_all()
    assert db.query(Membership).filter_by(id=teacher_membership.id).one().status == "revoked"
    assert db.query(StaffAssignment).filter_by(id=assignment.json()["id"]).one().valid_to is not None
    assert "school.teacher_membership.deactivated" in {row.action for row in db.query(AuditLog).all()}


def test_require_teacher_of_passes_and_fails_for_assignment_scope(db, staff_world):
    assignment = StaffAssignment(
        school_id=staff_world["alpha"].id,
        membership_id=staff_world["alpha_teacher_membership"].id,
        class_section_id=staff_world["section"].id,
        role="homeroom",
        valid_from=invite_tokens.now_utc().date(),
    )
    db.add(assignment)
    db.commit()

    test_app = FastAPI()

    @test_app.get("/schools/{school_id}/sections/{class_section_id}")
    def scoped_route(membership: Membership = Depends(require_teacher_of(class_section_param="class_section_id"))):
        return {"membership_id": membership.id}

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    test_app.dependency_overrides[get_db] = override_get_db
    guard_client = TestClient(test_app)

    path = f"/schools/{staff_world['alpha'].id}/sections/{staff_world['section'].id}"
    assert guard_client.get(path, headers=bearer(staff_world["alpha_teacher"].email)).status_code == 200
    assert guard_client.get(path, headers=bearer(staff_world["other_teacher"].email)).status_code == 403
    assignment.valid_to = invite_tokens.now_utc().date() - timedelta(days=1)
    db.commit()
    assert guard_client.get(path, headers=bearer(staff_world["alpha_teacher"].email)).status_code == 403

import os
from datetime import timedelta

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
from app.routes.join import JOIN_RATE_LIMITER
from app.models_school import (
    AcademicYear,
    AuditLog,
    BranchCampus,
    ClassSection,
    Enrolment,
    GradeLevel,
    GuardianInvite,
    GuardianLink,
    MagicLoginToken,
    Membership,
    PlatformAdmin,
    School,
    StaffInvite,
    Student,
    StudentGuardianContact,
    User,
)


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
database.engine = engine
database.SessionLocal = TestingSessionLocal


@pytest.fixture
def db():
    JOIN_RATE_LIMITER._attempts.clear()
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
def world(db):
    alpha_admin = create_user(db, "alpha-admin@example.com", "Alpha Admin")
    alpha_teacher = create_user(db, "alpha-teacher@example.com", "Alpha Teacher")
    beta_admin = create_user(db, "beta-admin@example.com", "Beta Admin")
    platform = create_user(db, "platform@example.com", "Platform")
    guardian = create_user(db, "fatima@example.com", "Fatima Signed")
    other_guardian = create_user(db, "other@example.com", "Other Guardian")

    alpha = School(name="Alpha Academy", name_ar="أكاديمية ألفا", slug="alpha", status="active")
    beta = School(name="Beta School", slug="beta", status="active")
    db.add_all([alpha, beta])
    db.flush()
    db.add_all(
        [
            Membership(school_id=alpha.id, user_id=alpha_admin.id, role="school_admin"),
            Membership(school_id=alpha.id, user_id=alpha_teacher.id, role="teacher"),
            Membership(school_id=beta.id, user_id=beta_admin.id, role="school_admin"),
            PlatformAdmin(user_id=platform.id),
        ]
    )
    db.flush()
    branch = BranchCampus(school_id=alpha.id, code="MAIN", name="Main", status="active")
    beta_branch = BranchCampus(school_id=beta.id, code="MAIN", name="Main", status="active")
    db.add_all([branch, beta_branch])
    db.flush()
    year = AcademicYear(school_id=alpha.id, code="2026", name="2026", status="active", is_current=True)
    beta_year = AcademicYear(school_id=beta.id, code="2026", name="2026", status="active", is_current=True)
    db.add_all([year, beta_year])
    db.flush()
    level = GradeLevel(school_id=alpha.id, code="KG1", name="KG 1", status="active")
    beta_level = GradeLevel(school_id=beta.id, code="KG1", name="KG 1", status="active")
    db.add_all([level, beta_level])
    db.flush()
    section = ClassSection(school_id=alpha.id, branch_campus_id=branch.id, academic_year_id=year.id, grade_level_id=level.id, code="A", name="KG 1 A", status="active")
    beta_section = ClassSection(school_id=beta.id, branch_campus_id=beta_branch.id, academic_year_id=beta_year.id, grade_level_id=beta_level.id, code="A", name="KG 1 A", status="active")
    db.add_all([section, beta_section])
    db.flush()
    student = Student(school_id=alpha.id, external_ref="S1", first_name="Sara", last_name="Ahmed", status="active")
    second_student = Student(school_id=alpha.id, external_ref="S2", first_name="Omar", last_name="Ahmed", status="active")
    beta_student = Student(school_id=beta.id, external_ref="B1", first_name="Beta", last_name="Child", status="active")
    db.add_all([student, second_student, beta_student])
    db.flush()
    db.add_all(
        [
            Enrolment(school_id=alpha.id, student_id=student.id, class_section_id=section.id, kind="member"),
            Enrolment(school_id=alpha.id, student_id=second_student.id, class_section_id=section.id, kind="member"),
            Enrolment(school_id=beta.id, student_id=beta_student.id, class_section_id=beta_section.id, kind="member"),
        ]
    )
    contact = StudentGuardianContact(
        school_id=alpha.id,
        student_id=student.id,
        slot=1,
        name="Fatima Ahmed",
        email="fatima@example.com",
        relationship="mother",
        status="draft",
    )
    contact2 = StudentGuardianContact(
        school_id=alpha.id,
        student_id=student.id,
        slot=2,
        name="Khaled Ahmed",
        email="khaled@example.com",
        relationship="father",
        status="draft",
    )
    db.add_all([contact, contact2])
    db.commit()
    return locals()


def create_invite(client, world, *, student=None, contact=None, slot=None):
    student = student or world["student"]
    payload = {"contact_id": (contact or world["contact"]).id} if contact or slot is None else {"slot": slot}
    return client.post(
        f"/api/school/students/{student.id}/guardian-invites",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        json=payload,
    )


def test_admin_creates_invite_from_contact_without_storing_raw_code(db, client, world):
    resp = create_invite(client, world)
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["code"].startswith("CHH-")
    assert payload["join_url"].endswith(f"/join?c={payload['code']}")
    invite = db.query(GuardianInvite).one()
    assert invite.guardian_name == "Fatima Ahmed"
    assert invite.guardian_email == "fatima@example.com"
    assert invite.relationship == "mother"
    assert invite.token_hash != invite_tokens.normalize_short_code(payload["code"])
    assert payload["code"] not in invite.token_hash
    assert db.query(StaffInvite).count() == 0
    assert db.query(MagicLoginToken).count() == 0


def test_admin_lists_contact_invite_link_status_and_blocks_wrong_roles(db, client, world):
    create_invite(client, world)
    listed = client.get(f"/api/school/students/{world['student'].id}/guardian-invites", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert listed.status_code == 200
    assert listed.json()["contacts"][0]["email"] == "fatima@example.com"
    assert listed.json()["invites"][0]["status"] == "active"
    assert "code" not in listed.json()["invites"][0]

    teacher = client.post(f"/api/school/students/{world['student'].id}/guardian-invites", headers=bearer(world["alpha_teacher"].email, world["alpha"].id), json={"contact_id": world["contact"].id})
    assert teacher.status_code == 403
    platform = client.post(f"/api/school/students/{world['student'].id}/guardian-invites", headers=bearer(world["platform"].email, world["alpha"].id), json={"contact_id": world["contact"].id})
    assert platform.status_code == 403
    wrong_school = client.post(f"/api/school/students/{world['student'].id}/guardian-invites", headers=bearer(world["beta_admin"].email, world["beta"].id), json={"contact_id": world["contact"].id})
    assert wrong_school.status_code == 404


def test_one_live_invite_per_slot_revoke_and_ignored_contact(db, client, world):
    first = create_invite(client, world)
    assert first.status_code == 201
    duplicate = create_invite(client, world)
    assert duplicate.status_code == 409
    invite_id = first.json()["id"]
    revoked = client.post(f"/api/school/guardian-invites/{invite_id}/revoke", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    second = create_invite(client, world)
    assert second.status_code == 201
    ignored = client.post(f"/api/school/guardian-contacts/{world['contact2'].id}/ignore", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert ignored.status_code == 200
    blocked = create_invite(client, world, contact=world["contact2"])
    assert blocked.status_code == 400


def test_preview_is_safe_and_does_not_consume_code(db, client, world):
    code = create_invite(client, world).json()["code"]
    preview = client.get(f"/api/join/guardian?c={code}")
    assert preview.status_code == 200
    assert preview.json() == {"school_name": "Alpha Academy", "school_name_ar": "أكاديمية ألفا", "auth_required": True}
    assert "Sara" not in preview.text
    assert db.query(GuardianInvite).one().claimed_at is None

    details = client.get(f"/api/join/guardian/details?c={code}", headers=bearer(world["guardian"].email))
    assert details.status_code == 200
    assert details.json()["student_first_name"] == "Sara"
    assert details.json()["class_section_name"] == "KG 1 A"
    assert details.json()["relationship"] == "mother"


def test_confirm_creates_membership_link_claims_invite_and_marks_contact_linked(db, client, world):
    code = create_invite(client, world).json()["code"]
    resp = client.post("/api/join/guardian/confirm", headers=bearer(world["guardian"].email), json={"code": code, "relationship": "mother"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "linked"
    invite = db.query(GuardianInvite).one()
    assert invite.claimed_at is not None
    assert invite.claimed_by_user_id == world["guardian"].id
    link = db.query(GuardianLink).one()
    assert link.school_id == world["alpha"].id
    assert link.student_id == world["student"].id
    assert link.user_id == world["guardian"].id
    assert link.relationship == "mother"
    assert link.email_matched_contact is True
    assert db.query(Membership).filter_by(school_id=world["alpha"].id, user_id=world["guardian"].id, role="guardian", status="active").one()
    db.expire_all()
    assert db.query(StudentGuardianContact).filter_by(id=world["contact"].id).one().status == "linked"
    assert "school.guardian_invite.claimed" in {row.action for row in db.query(AuditLog).all()}


def test_email_mismatch_still_links_and_is_admin_visible(db, client, world):
    code = create_invite(client, world).json()["code"]
    resp = client.post("/api/join/guardian/confirm", headers=bearer(world["other_guardian"].email), json={"code": code, "relationship": "guardian"})
    assert resp.status_code == 200
    link = db.query(GuardianLink).one()
    assert link.email_matched_contact is False
    listed = client.get(f"/api/school/students/{world['student'].id}/guardian-invites", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert listed.json()["links"][0]["email_matched_contact"] is False


def test_claimed_revoked_expired_invalid_codes_fail_generically(db, client, world):
    invalid = client.get("/api/join/guardian?c=CHH-XXXX-XXXX")
    assert invalid.status_code == 404
    generic = invalid.json()["detail"]

    code = create_invite(client, world).json()["code"]
    client.post("/api/join/guardian/confirm", headers=bearer(world["guardian"].email), json={"code": code, "relationship": "mother"})
    reused = client.post("/api/join/guardian/confirm", headers=bearer(world["other_guardian"].email), json={"code": code, "relationship": "guardian"})
    assert reused.status_code == 404
    assert reused.json()["detail"] == generic

    revoked_code = create_invite(client, world, contact=world["contact2"]).json()["code"]
    invite_id = db.query(GuardianInvite).filter(GuardianInvite.display_code_last4 == invite_tokens.normalize_short_code(revoked_code)[-4:]).one().id
    client.post(f"/api/school/guardian-invites/{invite_id}/revoke", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    revoked = client.get(f"/api/join/guardian?c={revoked_code}")
    assert revoked.status_code == 404
    assert revoked.json()["detail"] == generic

    expired = GuardianInvite(
        school_id=world["alpha"].id,
        student_id=world["second_student"].id,
        slot=1,
        token_hash=invite_tokens.hash_token("ABCDEFGH"),
        expires_at=invite_tokens.now_utc() - timedelta(days=1),
        created_by_user_id=world["alpha_admin"].id,
    )
    db.add(expired)
    db.commit()
    expired_resp = client.get("/api/join/guardian?c=CHH-ABCD-EFGH")
    assert expired_resp.status_code == 404
    assert expired_resp.json()["detail"] == generic


def test_revoked_link_can_be_restored_by_fresh_invite_and_membership_revoked_only_after_last_link(db, client, world):
    code = create_invite(client, world).json()["code"]
    client.post("/api/join/guardian/confirm", headers=bearer(world["guardian"].email), json={"code": code, "relationship": "mother"})
    link = db.query(GuardianLink).one()
    revoked = client.post(f"/api/school/guardian-links/{link.id}/revoke", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert revoked.status_code == 200
    db.expire_all()
    assert db.query(Membership).filter_by(school_id=world["alpha"].id, user_id=world["guardian"].id, role="guardian").one().status == "revoked"

    fresh = create_invite(client, world, student=world["second_student"], slot=1).json()["code"]
    client.post("/api/join/guardian/confirm", headers=bearer(world["guardian"].email), json={"code": fresh, "relationship": "guardian"})
    assert db.query(Membership).filter_by(school_id=world["alpha"].id, user_id=world["guardian"].id, role="guardian").one().status == "active"


def test_suspended_school_and_archived_student_block_join(db, client, world):
    code = create_invite(client, world).json()["code"]
    world["student"].status = "archived"
    db.commit()
    assert client.get(f"/api/join/guardian?c={code}").status_code == 404
    world["student"].status = "active"
    world["alpha"].status = "suspended"
    db.commit()
    assert client.get(f"/api/join/guardian?c={code}").status_code == 404

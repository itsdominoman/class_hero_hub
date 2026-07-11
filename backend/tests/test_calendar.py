import os
from datetime import date, timedelta

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
    CalendarEvent,
    ClassSection,
    Enrolment,
    GradeLevel,
    GuardianLink,
    Membership,
    School,
    StaffAssignment,
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
def world(db):
    admin = create_user(db, "admin@example.com", "Admin")
    teacher = create_user(db, "teacher@example.com", "Teacher")
    other_teacher = create_user(db, "other-teacher@example.com", "Other Teacher")
    guardian = create_user(db, "guardian@example.com", "Guardian")
    other_guardian = create_user(db, "other-guardian@example.com", "Other Guardian")

    alpha = School(name="Alpha Academy", slug="alpha", status="active")
    beta = School(name="Beta School", slug="beta", status="active")
    db.add_all([alpha, beta])
    db.flush()

    admin_membership = Membership(school_id=alpha.id, user_id=admin.id, role="school_admin")
    teacher_membership = Membership(school_id=alpha.id, user_id=teacher.id, role="teacher")
    other_teacher_membership = Membership(school_id=alpha.id, user_id=other_teacher.id, role="teacher")
    guardian_membership = Membership(school_id=alpha.id, user_id=guardian.id, role="guardian")
    db.add_all([admin_membership, teacher_membership, other_teacher_membership, guardian_membership])
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
    other_section = ClassSection(school_id=alpha.id, branch_campus_id=branch.id, academic_year_id=year.id, grade_level_id=level.id, code="B", name="KG 1 B", status="active")
    beta_section = ClassSection(school_id=beta.id, branch_campus_id=beta_branch.id, academic_year_id=beta_year.id, grade_level_id=beta_level.id, code="A", name="KG 1 A", status="active")
    db.add_all([section, other_section, beta_section])
    db.flush()
    subject = Subject(school_id=alpha.id, code="ENG", name="English", status="active")
    db.add(subject)
    db.flush()
    group = SubjectGroup(
        school_id=alpha.id,
        academic_year_id=year.id,
        class_section_id=section.id,
        subject_id=subject.id,
        code="KG1A-ENG",
        name="KG 1 A English",
        status="active",
        enrolment_policy="default_for_section",
    )
    db.add(group)
    db.flush()

    student = Student(school_id=alpha.id, external_ref="S1", first_name="Sara", last_name="Ahmed", status="active")
    other_student = Student(school_id=alpha.id, external_ref="S3", first_name="Lina", last_name="Ali", status="active")
    db.add_all([student, other_student])
    db.flush()
    enrolment = Enrolment(school_id=alpha.id, student_id=student.id, class_section_id=section.id, kind="member")
    db.add_all(
        [
            enrolment,
            Enrolment(school_id=alpha.id, student_id=other_student.id, class_section_id=other_section.id, kind="member"),
            StaffAssignment(school_id=alpha.id, membership_id=teacher_membership.id, class_section_id=section.id, role="homeroom"),
            StaffAssignment(school_id=alpha.id, membership_id=teacher_membership.id, subject_group_id=group.id, role="subject"),
            StaffAssignment(school_id=alpha.id, membership_id=other_teacher_membership.id, class_section_id=other_section.id, role="homeroom"),
            GuardianLink(school_id=alpha.id, student_id=student.id, user_id=guardian.id, relationship="mother", status="active"),
            GuardianLink(school_id=alpha.id, student_id=other_student.id, user_id=other_guardian.id, relationship="father", status="active"),
        ]
    )
    db.commit()
    return locals()


TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def create_event(client, world, **overrides):
    payload = {
        "title": "Spelling test",
        "body": "Units 1-3",
        "event_type": "test",
        "audience_type": "class_section",
        "class_section_id": world["section"].id,
        "starts_at": f"{TOMORROW}T08:00:00Z",
    }
    payload.update(overrides.pop("payload", {}))
    return client.post(
        "/api/school/calendar",
        headers=bearer(overrides.pop("email", world["teacher"].email), overrides.pop("school_id", world["alpha"].id)),
        json=payload,
    )


def create_homework(client, world, **overrides):
    payload = {"item_type": "homework", "title": "Math worksheet", "body": "Page 4", "audience_type": "class_section", "class_section_id": world["section"].id, "due_at": f"{TOMORROW}T16:00:00Z"}
    payload.update(overrides.pop("payload", {}))
    return client.post("/api/teach/homework", headers=bearer(world["teacher"].email, world["alpha"].id), json=payload)


def teacher_calendar(client, world, query="", email=None):
    return client.get(f"/api/teach/calendar{query}", headers=bearer(email or world["teacher"].email, world["alpha"].id))


def test_teacher_create_scope_and_validation(db, client, world):
    assert create_event(client, world).status_code == 201
    defaulted = client.post(
        "/api/school/calendar",
        headers=bearer(world["teacher"].email, world["alpha"].id),
        json={
            "title": "Bring library books",
            "audience_type": "class_section",
            "class_section_id": world["section"].id,
            "starts_at": f"{TOMORROW}T08:00:00Z",
        },
    )
    assert defaulted.status_code == 201 and defaulted.json()["event_type"] == "event"
    assert create_event(client, world, payload={"audience_type": "subject_group", "class_section_id": None, "subject_group_id": world["group"].id, "event_type": "reminder"}).status_code == 201
    # Teacher cannot create school-wide or unassigned-target events
    assert create_event(client, world, payload={"audience_type": "school", "class_section_id": None}).status_code == 403
    assert create_event(client, world, payload={"class_section_id": world["other_section"].id}).status_code == 403
    assert create_event(client, world, payload={"class_section_id": world["beta_section"].id}).status_code == 404
    # Invalid event type and inverted range rejected
    assert create_event(client, world, payload={"event_type": "party"}).status_code == 422
    assert create_event(client, world, payload={"ends_at": f"{TOMORROW}T07:00:00Z"}).status_code == 422
    assert create_event(client, world, payload={"event_type": "civvies"}).status_code == 403
    assert db.query(CalendarEvent).count() == 3


def test_admin_creates_school_wide_event(client, world):
    created = create_event(client, world, email=world["admin"].email, payload={"audience_type": "school", "class_section_id": None, "event_type": "civvies", "title": "Civvies day", "all_day": True})
    assert created.status_code == 201
    body = created.json()
    assert body["audience_type"] == "school" and body["all_day"] is True
    # School-wide events appear in the teacher calendar but are not manageable by teachers
    items = teacher_calendar(client, world).json()["items"]
    school_items = [item for item in items if item["audience_type"] == "school"]
    assert len(school_items) == 1 and school_items[0]["can_manage"] is False
    admin_items = client.get("/api/school/calendar", headers=bearer(world["admin"].email, world["alpha"].id)).json()["items"]
    assert {item["id"] for item in admin_items} == {body["id"]}


def test_teacher_calendar_visibility_and_target_filter(client, world):
    class_event = create_event(client, world).json()
    group_event = create_event(client, world, payload={"audience_type": "subject_group", "class_section_id": None, "subject_group_id": world["group"].id}).json()
    other_event = create_event(client, world, email=world["other_teacher"].email, payload={"class_section_id": world["other_section"].id}).json()
    homework = create_homework(client, world).json()

    items = teacher_calendar(client, world).json()["items"]
    ids = {item["id"] for item in items}
    assert ids == {class_event["id"], group_event["id"], f'homework-{homework["id"]}'}
    assert other_event["id"] not in ids
    # Class-scoped filter returns only that target plus its homework due items
    scoped = teacher_calendar(client, world, query=f'?class_section_id={world["section"].id}').json()["items"]
    assert {item["id"] for item in scoped} == {class_event["id"], f'homework-{homework["id"]}'}
    # Filtering an unassigned target is rejected
    assert teacher_calendar(client, world, query=f'?class_section_id={world["other_section"].id}').status_code == 403
    # Date range excludes events outside the window
    empty = teacher_calendar(client, world, query=f"?start={date.today() + timedelta(days=30)}").json()["items"]
    assert empty == []


def test_teacher_edit_archive_scope_and_archived_lock(db, client, world):
    event = create_event(client, world).json()
    headers = bearer(world["teacher"].email, world["alpha"].id)
    other = bearer(world["other_teacher"].email, world["alpha"].id)
    update = {"title": "Moved test", "event_type": "test", "starts_at": f"{TOMORROW}T10:00:00Z"}
    assert client.patch(f'/api/school/calendar/{event["event_id"]}', headers=other, json=update).status_code == 404
    assert client.delete(f'/api/school/calendar/{event["event_id"]}', headers=other).status_code == 404
    edited = client.patch(f'/api/school/calendar/{event["event_id"]}', headers=headers, json=update)
    assert edited.status_code == 200 and edited.json()["title"] == "Moved test"
    # Admin can manage teacher events; teacher cannot manage school-wide events
    school_event = create_event(client, world, email=world["admin"].email, payload={"audience_type": "school", "class_section_id": None}).json()
    assert client.patch(f'/api/school/calendar/{school_event["event_id"]}', headers=headers, json=update).status_code == 404
    assert client.patch(f'/api/school/calendar/{event["event_id"]}', headers=bearer(world["admin"].email, world["alpha"].id), json=update).status_code == 200
    # Archive is soft and locks edits
    assert client.delete(f'/api/school/calendar/{event["event_id"]}', headers=headers).status_code == 200
    archived = db.query(CalendarEvent).filter_by(id=event["event_id"]).one()
    assert archived.status == "archived" and archived.archived_at is not None
    assert client.patch(f'/api/school/calendar/{event["event_id"]}', headers=headers, json=update).status_code == 409


def test_guardian_calendar_scope_and_lifecycle(db, client, world):
    class_event = create_event(client, world).json()
    school_event = create_event(client, world, email=world["admin"].email, payload={"audience_type": "school", "class_section_id": None, "title": "Sports day"}).json()
    create_event(client, world, email=world["other_teacher"].email, payload={"class_section_id": world["other_section"].id})
    homework = create_homework(client, world).json()

    headers = bearer(world["guardian"].email)
    listed = client.get("/api/guardian/calendar", headers=headers)
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert {item["id"] for item in items} == {class_event["id"], school_event["id"], f'homework-{homework["id"]}'}
    forbidden_keys = {"guardian_email", "token", "invite", "email", "user_id", "author_user_id"}
    assert not forbidden_keys.intersection(items[0])
    # Homework due items expose the id needed to open homework detail
    homework_item = next(item for item in items if item["kind"] == "homework_due")
    assert homework_item["homework_item_id"] == homework["id"]

    # Archived event and archived homework disappear
    assert client.delete(f'/api/school/calendar/{class_event["event_id"]}', headers=bearer(world["teacher"].email, world["alpha"].id)).status_code == 200
    assert client.delete(f'/api/teach/homework/{homework["id"]}', headers=bearer(world["teacher"].email, world["alpha"].id)).status_code == 200
    remaining = {item["id"] for item in client.get("/api/guardian/calendar", headers=headers).json()["items"]}
    assert remaining == {school_event["id"]}

    # Homework due date edits move the calendar item
    fresh = create_homework(client, world).json()
    moved_date = (date.today() + timedelta(days=3)).isoformat()
    client.patch(f'/api/teach/homework/{fresh["id"]}', headers=bearer(world["teacher"].email, world["alpha"].id), json={"item_type": "homework", "title": fresh["title"], "body": "Page 4", "due_at": f"{moved_date}T16:00:00Z"})
    moved = next(item for item in client.get("/api/guardian/calendar", headers=headers).json()["items"] if item["kind"] == "homework_due")
    assert moved["starts_at"].startswith(moved_date)


def test_guardian_revoked_link_and_ended_enrolment_remove_access(db, client, world):
    class_event = create_event(client, world).json()
    headers = bearer(world["guardian"].email)
    assert class_event["id"] in {item["id"] for item in client.get("/api/guardian/calendar", headers=headers).json()["items"]}
    # Ended enrolment removes class events (school-wide would remain via link)
    enrolment = db.query(Enrolment).filter_by(student_id=world["student"].id).one()
    enrolment.valid_to = date.today() - timedelta(days=1)
    db.commit()
    assert class_event["id"] not in {item["id"] for item in client.get("/api/guardian/calendar", headers=headers).json()["items"]}
    # Revoked link removes everything
    enrolment.valid_to = None
    for link in db.query(GuardianLink).filter(GuardianLink.user_id == world["guardian"].id).all():
        link.status = "revoked"
        link.revoked_at = invite_tokens.now_utc()
    db.commit()
    assert client.get("/api/guardian/calendar", headers=headers).json()["items"] == []
    # Guardians cannot create or manage events
    assert create_event(client, world, email=world["guardian"].email).status_code == 403
    assert client.get("/api/guardian/calendar").status_code == 401

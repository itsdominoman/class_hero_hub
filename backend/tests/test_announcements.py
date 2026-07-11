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
from app.models_school import (
    AcademicYear,
    Announcement,
    AnnouncementAttachment,
    AnnouncementRead,
    BranchCampus,
    ClassSection,
    Enrolment,
    GuardianInvite,
    GuardianLink,
    HomeworkAttachment,
    HomeworkItem,
    HomeworkItemCompletion,
    GradeLevel,
    MagicLoginToken,
    Membership,
    School,
    StaffAssignment,
    StaffInvite,
    Student,
    Subject,
    SubjectGroup,
    User,
)
from app.routes import announcements, homework


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
database.engine = engine
database.SessionLocal = TestingSessionLocal


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(announcements, "UPLOAD_ROOT", tmp_path / "announcement_uploads")
    monkeypatch.setattr(homework, "UPLOAD_ROOT", tmp_path / "homework_uploads")
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
    beta_admin = create_user(db, "beta-admin@example.com", "Beta Admin")

    alpha = School(name="Alpha Academy", slug="alpha", status="active")
    beta = School(name="Beta School", slug="beta", status="active")
    db.add_all([alpha, beta])
    db.flush()

    admin_membership = Membership(school_id=alpha.id, user_id=admin.id, role="school_admin")
    teacher_membership = Membership(school_id=alpha.id, user_id=teacher.id, role="teacher")
    other_teacher_membership = Membership(school_id=alpha.id, user_id=other_teacher.id, role="teacher")
    guardian_membership = Membership(school_id=alpha.id, user_id=guardian.id, role="guardian")
    other_guardian_membership = Membership(school_id=alpha.id, user_id=other_guardian.id, role="guardian")
    beta_admin_membership = Membership(school_id=beta.id, user_id=beta_admin.id, role="school_admin")
    db.add_all([admin_membership, teacher_membership, other_teacher_membership, guardian_membership, other_guardian_membership, beta_admin_membership])
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
    sibling = Student(school_id=alpha.id, external_ref="S2", first_name="Omar", last_name="Ahmed", status="active")
    other_student = Student(school_id=alpha.id, external_ref="S3", first_name="Lina", last_name="Ali", status="active")
    beta_student = Student(school_id=beta.id, external_ref="B1", first_name="Beta", last_name="Child", status="active")
    db.add_all([student, sibling, other_student, beta_student])
    db.flush()
    db.add_all(
        [
            Enrolment(school_id=alpha.id, student_id=student.id, class_section_id=section.id, kind="member"),
            Enrolment(school_id=alpha.id, student_id=sibling.id, class_section_id=section.id, kind="member"),
            Enrolment(school_id=alpha.id, student_id=other_student.id, class_section_id=other_section.id, kind="member"),
            Enrolment(school_id=beta.id, student_id=beta_student.id, class_section_id=beta_section.id, kind="member"),
            StaffAssignment(school_id=alpha.id, membership_id=teacher_membership.id, class_section_id=section.id, role="homeroom"),
            StaffAssignment(school_id=alpha.id, membership_id=teacher_membership.id, subject_group_id=group.id, role="subject"),
            GuardianLink(school_id=alpha.id, student_id=student.id, user_id=guardian.id, relationship="mother", status="active"),
            GuardianLink(school_id=alpha.id, student_id=sibling.id, user_id=guardian.id, relationship="mother", status="active"),
            GuardianLink(school_id=alpha.id, student_id=other_student.id, user_id=other_guardian.id, relationship="father", status="active"),
        ]
    )
    db.commit()
    return locals()


def create_announcement(client, world, payload, *, email=None, school=None):
    return client.post(
        "/api/school/announcements",
        headers=bearer(email or world["admin"].email, (school or world["alpha"]).id),
        json=payload,
    )


def create_homework(client, world, **overrides):
    payload = {"item_type": "homework", "title": "Math worksheet", "body": "Complete page 4", "audience_type": "class_section", "class_section_id": world["section"].id, "due_at": "2026-07-12T16:00:00Z"}
    payload.update(overrides.pop("payload", {}))
    return client.post("/api/teach/homework", headers=bearer(overrides.pop("email", world["teacher"].email), overrides.pop("school_id", world["alpha"].id)), json=payload)


def test_homework_teacher_create_assignment_scope_and_dates(db, client, world):
    class_item = create_homework(client, world)
    assert class_item.status_code == 201
    assert class_item.json()["due_at"] is not None
    group_item = create_homework(client, world, payload={"audience_type": "subject_group", "class_section_id": None, "subject_group_id": world["group"].id})
    assert group_item.status_code == 201
    diary = create_homework(client, world, payload={"item_type": "diary", "title": "Library day", "due_at": None})
    assert diary.status_code == 201 and diary.json()["due_at"] is None
    unassigned = create_homework(client, world, payload={"class_section_id": world["other_section"].id})
    assert unassigned.status_code == 403
    other_teacher = create_homework(client, world, email=world["other_teacher"].email)
    assert other_teacher.status_code == 403
    cross_school = create_homework(client, world, payload={"class_section_id": world["beta_section"].id})
    assert cross_school.status_code == 404
    assert db.query(HomeworkItem).count() == 3


def test_homework_resource_links_are_validated_and_authorized(client, world):
    created = create_homework(client, world, payload={"resource_links": [{"url": "https://youtu.be/abc123", "label": "Watch lesson"}, {"url": "https://www.youtube.com/shorts/demo"} ]})
    assert created.status_code == 201
    assert created.json()["resource_links"][0] == {"url": "https://youtu.be/abc123", "label": "Watch lesson"}
    assert client.get(f'/api/guardian/homework/{created.json()["id"]}', headers=bearer(world["guardian"].email)).json()["resource_links"][1]["url"].endswith("/shorts/demo")
    for unsafe in ["javascript:alert(1)", "http://youtube.com/watch?v=x", "https://localhost/video", "https://127.0.0.1/video", "data:text/plain,x"]:
        assert create_homework(client, world, payload={"resource_links": [{"url": unsafe}]}).status_code == 422
    assert create_homework(client, world, payload={"resource_links": [{"url": f"https://example.com/{i}"} for i in range(6)]}).status_code == 422


def test_homework_attachment_rules_and_teacher_download(client, world):
    item = create_homework(client, world).json()
    headers = bearer(world["teacher"].email, world["alpha"].id)
    allowed = client.post(f'/api/teach/homework/{item["id"]}/attachments', headers=headers, files={"file": ("sheet.pdf", b"pdf", "application/pdf")})
    assert allowed.status_code == 201
    attachment = allowed.json()
    download = client.get(f'/api/teach/homework/{item["id"]}/attachments/{attachment["id"]}/download', headers=headers)
    assert download.status_code == 200 and download.content == b"pdf"
    blocked = client.post(f'/api/teach/homework/{item["id"]}/attachments', headers=headers, files={"file": ("bad.exe", b"bad")})
    assert blocked.status_code == 400
    oversized = client.post(f'/api/teach/homework/{item["id"]}/attachments', headers=headers, files={"file": ("huge.txt", b"x" * (10 * 1024 * 1024 + 1))})
    assert oversized.status_code == 400
    denied = client.get(f'/api/teach/homework/{item["id"]}/attachments/{attachment["id"]}/download', headers=bearer(world["other_teacher"].email, world["alpha"].id))
    assert denied.status_code == 404
    spreadsheet = client.post(f'/api/teach/homework/{item["id"]}/attachments', headers=headers, files={"file": ("work.xlsx", b"sheet")})
    assert spreadsheet.status_code == 201
    csv_file = client.post(f'/api/teach/homework/{item["id"]}/attachments', headers=headers, files={"file": ("data.csv", b"a,b")})
    assert csv_file.status_code == 201
    for filename in ("photo.jpg", "photo.jpeg", "photo.png", "photo.webp", "slides.pptx", "sheet.xls"):
        separate = create_homework(client, world).json()
        response = client.post(f'/api/teach/homework/{separate["id"]}/attachments', headers=headers, files={"file": (filename, b"file")})
        assert response.status_code == 201, filename
    heic = client.post(f'/api/teach/homework/{item["id"]}/attachments', headers=headers, files={"file": ("iphone.heic", b"photo")})
    assert heic.status_code == 400
    assert "iPhone photo format is not supported yet" in heic.json()["detail"]


def test_guardian_homework_visibility_archive_revoke_and_allowlist(db, client, world):
    class_item = create_homework(client, world).json()
    group_item = create_homework(client, world, payload={"audience_type": "subject_group", "class_section_id": None, "subject_group_id": world["group"].id}).json()
    headers = bearer(world["guardian"].email)
    listed = client.get("/api/guardian/homework", headers=headers)
    assert listed.status_code == 200
    assert {row["id"] for row in listed.json()["items"]} == {class_item["id"], group_item["id"]}
    forbidden_keys = {"guardian_email", "token", "invite", "email", "user_id", "author_user_id"}
    assert not forbidden_keys.intersection(listed.json()["items"][0])
    assert client.get(f'/api/guardian/homework/{class_item["id"]}', headers=bearer(world["other_guardian"].email)).status_code == 404
    client.delete(f'/api/teach/homework/{class_item["id"]}', headers=bearer(world["teacher"].email, world["alpha"].id))
    assert {row["id"] for row in client.get("/api/guardian/homework", headers=headers).json()["items"]} == {group_item["id"]}
    for link in db.query(GuardianLink).filter(GuardianLink.user_id == world["guardian"].id).all():
        link.status = "revoked"; link.revoked_at = invite_tokens.now_utc()
    db.commit()
    assert client.get("/api/guardian/homework", headers=headers).json()["items"] == []


def test_unrelated_guardian_cannot_download_homework_attachment(client, world):
    item = create_homework(client, world).json()
    upload = client.post(f'/api/teach/homework/{item["id"]}/attachments', headers=bearer(world["teacher"].email, world["alpha"].id), files={"file": ("note.txt", b"private")}).json()
    assert client.get(f'/api/guardian/homework/{item["id"]}/attachments/{upload["id"]}/download', headers=bearer(world["guardian"].email)).status_code == 200
    assert client.get(f'/api/guardian/homework/{item["id"]}/attachments/{upload["id"]}/download', headers=bearer(world["other_guardian"].email)).status_code == 404


def test_unrelated_guardian_direct_access_is_not_found_and_cannot_mark_done(client, world):
    item = create_homework(client, world).json()
    upload = client.post(f'/api/teach/homework/{item["id"]}/attachments', headers=bearer(world["teacher"].email, world["alpha"].id), files={"file": ("work.pdf", b"private")}).json()
    allowed = bearer(world["guardian"].email)
    denied = bearer(world["other_guardian"].email)
    assert item["id"] in {row["id"] for row in client.get("/api/guardian/homework", headers=allowed).json()["items"]}
    assert client.get(f'/api/guardian/homework/{item["id"]}', headers=allowed).status_code == 200
    assert client.get(f'/api/guardian/homework/{item["id"]}/attachments/{upload["id"]}/download', headers=allowed).status_code == 200
    assert item["id"] not in {row["id"] for row in client.get("/api/guardian/homework", headers=denied).json()["items"]}
    assert client.get(f'/api/guardian/homework/{item["id"]}', headers=denied).status_code == 404
    assert client.get(f'/api/guardian/homework/{item["id"]}/attachments/{upload["id"]}/download', headers=denied).status_code == 404
    assert client.post(f'/api/guardian/homework/{item["id"]}/done', headers=denied).status_code == 404


def test_guardian_done_is_private_idempotent_and_reopenable(db, client, world):
    item = create_homework(client, world).json()
    second_link = GuardianLink(school_id=world["alpha"].id, student_id=world["student"].id, user_id=world["other_guardian"].id, relationship="father", status="active")
    db.add(second_link); db.commit()
    guardian_headers = bearer(world["guardian"].email)
    other_headers = bearer(world["other_guardian"].email)
    assert client.post(f'/api/guardian/homework/{item["id"]}/done', headers=guardian_headers).status_code == 201
    assert client.post(f'/api/guardian/homework/{item["id"]}/done', headers=guardian_headers).status_code == 201
    assert db.query(HomeworkItemCompletion).filter_by(homework_item_id=item["id"], guardian_user_id=world["guardian"].id).count() == 1
    assert item["id"] not in {row["id"] for row in client.get("/api/guardian/homework", headers=guardian_headers).json()["items"]}
    # Completed items stay reopenable for the owner, but stay private to that guardian
    assert client.get(f'/api/guardian/homework/{item["id"]}', headers=guardian_headers).status_code == 200
    assert item["id"] in {row["id"] for row in client.get("/api/guardian/homework", headers=other_headers).json()["items"]}
    assert item["id"] not in {row["id"] for row in client.get("/api/guardian/homework?status=completed", headers=other_headers).json()["items"]}


def test_guardian_completed_history_view_download_and_undo(db, client, world):
    item = create_homework(client, world).json()
    upload = client.post(f'/api/teach/homework/{item["id"]}/attachments', headers=bearer(world["teacher"].email, world["alpha"].id), files={"file": ("note.pdf", b"pdf")}).json()
    guardian = bearer(world["guardian"].email)
    other = bearer(world["other_guardian"].email)
    active_url, completed_url = "/api/guardian/homework", "/api/guardian/homework?status=completed"
    # Mark done: leaves active, appears in completed
    assert client.post(f'/api/guardian/homework/{item["id"]}/done', headers=guardian).status_code == 201
    assert item["id"] not in {row["id"] for row in client.get(active_url, headers=guardian).json()["items"]}
    assert item["id"] in {row["id"] for row in client.get(completed_url, headers=guardian).json()["items"]}
    # Completed detail + attachment download still work for the owner
    assert client.get(f'/api/guardian/homework/{item["id"]}', headers=guardian).status_code == 200
    assert client.get(f'/api/guardian/homework/{item["id"]}/attachments/{upload["id"]}/download', headers=guardian).status_code == 200
    # Another (unrelated) guardian's completed state is independent, and they cannot undo the owner's completion
    assert client.get(completed_url, headers=other).json()["items"] == []
    assert client.delete(f'/api/guardian/homework/{item["id"]}/done', headers=other).status_code == 404
    assert db.query(HomeworkItemCompletion).filter_by(homework_item_id=item["id"], guardian_user_id=world["guardian"].id).count() == 1
    # Owner marks not done: returns to active, leaves completed
    assert client.delete(f'/api/guardian/homework/{item["id"]}/done', headers=guardian).status_code == 200
    assert item["id"] in {row["id"] for row in client.get(active_url, headers=guardian).json()["items"]}
    assert client.get(completed_url, headers=guardian).json()["items"] == []


def test_guardian_completed_unauthorized_and_archived_and_revoked(db, client, world):
    item = create_homework(client, world).json()
    guardian = bearer(world["guardian"].email)
    unrelated = bearer(world["other_guardian"].email)
    assert client.post(f'/api/guardian/homework/{item["id"]}/done', headers=guardian).status_code == 201
    # Unrelated guardian: cannot see, detail, or undo
    assert client.get("/api/guardian/homework?status=completed", headers=unrelated).json()["items"] == []
    assert client.get(f'/api/guardian/homework/{item["id"]}', headers=unrelated).status_code == 404
    assert client.delete(f'/api/guardian/homework/{item["id"]}/done', headers=unrelated).status_code == 404
    # Bad status value rejected
    assert client.get("/api/guardian/homework?status=bogus", headers=guardian).status_code == 400
    # Archived teacher item drops out of completed and 404s for detail/not-done
    assert client.delete(f'/api/teach/homework/{item["id"]}', headers=bearer(world["teacher"].email, world["alpha"].id)).status_code == 200
    assert client.get("/api/guardian/homework?status=completed", headers=guardian).json()["items"] == []
    assert client.get(f'/api/guardian/homework/{item["id"]}', headers=guardian).status_code == 404
    assert client.delete(f'/api/guardian/homework/{item["id"]}/done', headers=guardian).status_code == 404


def test_guardian_completed_hidden_after_link_revoked(db, client, world):
    item = create_homework(client, world).json()
    guardian = bearer(world["guardian"].email)
    assert client.post(f'/api/guardian/homework/{item["id"]}/done', headers=guardian).status_code == 201
    assert item["id"] in {row["id"] for row in client.get("/api/guardian/homework?status=completed", headers=guardian).json()["items"]}
    for link in db.query(GuardianLink).filter(GuardianLink.user_id == world["guardian"].id).all():
        link.status = "revoked"; link.revoked_at = invite_tokens.now_utc()
    db.commit()
    assert client.get("/api/guardian/homework?status=completed", headers=guardian).json()["items"] == []
    assert client.get(f'/api/guardian/homework/{item["id"]}', headers=guardian).status_code == 404
    assert client.delete(f'/api/guardian/homework/{item["id"]}/done', headers=guardian).status_code == 404


def test_teacher_can_edit_homework_fields_and_guardian_sees_update(db, client, world):
    item = create_homework(client, world).json()
    headers = bearer(world["teacher"].email, world["alpha"].id)
    edit = client.patch(f'/api/teach/homework/{item["id"]}', headers=headers, json={
        "item_type": "diary", "title": "Write an Essay", "body": "Fixed typo", "due_at": None,
        "resource_links": [{"url": "https://youtu.be/xyz", "label": "Lesson"}],
    })
    assert edit.status_code == 200
    payload = edit.json()
    assert payload["item_type"] == "diary" and payload["title"] == "Write an Essay"
    assert payload["due_at"] is None and payload["resource_links"] == [{"url": "https://youtu.be/xyz", "label": "Lesson"}]
    guardian = client.get(f'/api/guardian/homework/{item["id"]}', headers=bearer(world["guardian"].email)).json()
    assert guardian["title"] == "Write an Essay" and guardian["body"] == "Fixed typo"


def test_teacher_edit_rejects_unauthorized_archived_and_invalid(db, client, world):
    item = create_homework(client, world).json()
    headers = bearer(world["teacher"].email, world["alpha"].id)
    body = {"item_type": "homework", "title": "New", "body": "New body", "due_at": None, "resource_links": []}
    # Unauthorized teacher cannot edit another target's item
    assert client.patch(f'/api/teach/homework/{item["id"]}', headers=bearer(world["other_teacher"].email, world["alpha"].id), json=body).status_code == 404
    # Server-side validation matches create (required title, HTTPS-only links)
    assert client.patch(f'/api/teach/homework/{item["id"]}', headers=headers, json={**body, "title": "   "}).status_code == 422
    assert client.patch(f'/api/teach/homework/{item["id"]}', headers=headers, json={**body, "resource_links": [{"url": "http://youtube.com/x"}]}).status_code == 422
    # Archived items cannot be edited
    assert client.delete(f'/api/teach/homework/{item["id"]}', headers=headers).status_code == 200
    assert client.patch(f'/api/teach/homework/{item["id"]}', headers=headers, json=body).status_code == 409


def test_guardian_done_survives_teacher_edit(db, client, world):
    item = create_homework(client, world).json()
    guardian_headers = bearer(world["guardian"].email)
    assert client.post(f'/api/guardian/homework/{item["id"]}/done', headers=guardian_headers).status_code == 201
    edit = client.patch(f'/api/teach/homework/{item["id"]}', headers=bearer(world["teacher"].email, world["alpha"].id), json={
        "item_type": "homework", "title": "Edited after done", "body": "Body", "due_at": None, "resource_links": [],
    })
    assert edit.status_code == 200
    # Done stays done: completion preserved and item is not re-shown to that guardian
    assert db.query(HomeworkItemCompletion).filter_by(homework_item_id=item["id"], guardian_user_id=world["guardian"].id).count() == 1
    assert item["id"] not in {row["id"] for row in client.get("/api/guardian/homework", headers=guardian_headers).json()["items"]}


def test_teacher_exact_audience_manage_list_detail_and_soft_archive(db, client, world):
    class_item = create_homework(client, world).json()
    group_item = create_homework(client, world, payload={"audience_type": "subject_group", "class_section_id": None, "subject_group_id": world["group"].id}).json()
    headers = bearer(world["teacher"].email, world["alpha"].id)
    class_list = client.get(f'/api/teach/homework?class_section_id={world["section"].id}', headers=headers).json()["items"]
    assert [row["id"] for row in class_list] == [class_item["id"]]
    assert client.get(f'/api/teach/homework/{class_item["id"]}', headers=headers).status_code == 200
    assert client.get(f'/api/teach/homework?class_section_id={world["other_section"].id}', headers=headers).status_code == 403
    assert client.delete(f'/api/teach/homework/{class_item["id"]}', headers=headers).status_code == 200
    archived = db.query(HomeworkItem).filter_by(id=class_item["id"]).one()
    assert archived.status == "archived" and archived.archived_at is not None
    assert group_item["id"] in {row["id"] for row in client.get("/api/guardian/homework", headers=bearer(world["guardian"].email)).json()["items"]}
    assert client.get(f'/api/guardian/homework/{class_item["id"]}', headers=bearer(world["guardian"].email)).status_code == 404


def test_school_admin_can_create_school_wide_announcement_without_invite_side_effects(db, client, world):
    resp = create_announcement(client, world, {"title": "School notice", "body": "Plain text only", "audience_type": "school"})
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["title"] == "School notice"
    assert payload["audience_type"] == "school"
    assert payload["attachment_count"] == 0
    assert db.query(Announcement).count() == 1
    assert db.query(GuardianInvite).count() == 0
    assert db.query(StaffInvite).count() == 0
    assert db.query(MagicLoginToken).count() == 0


def test_teacher_can_create_only_for_assigned_class_or_subject_group(client, world):
    assigned = create_announcement(
        client,
        world,
        {"title": "Class notice", "body": "Bring PE kit", "audience_type": "class_section", "class_section_id": world["section"].id},
        email=world["teacher"].email,
    )
    assert assigned.status_code == 201
    subject = create_announcement(
        client,
        world,
        {"title": "English", "body": "Reading book", "audience_type": "subject_group", "subject_group_id": world["group"].id},
        email=world["teacher"].email,
    )
    assert subject.status_code == 201
    unassigned = create_announcement(
        client,
        world,
        {"title": "Wrong class", "body": "No access", "audience_type": "class_section", "class_section_id": world["other_section"].id},
        email=world["teacher"].email,
    )
    assert unassigned.status_code == 403
    school_wide = create_announcement(client, world, {"title": "All", "body": "No", "audience_type": "school"}, email=world["teacher"].email)
    assert school_wide.status_code == 403
    other_teacher = create_announcement(
        client,
        world,
        {"title": "No assignment", "body": "No", "audience_type": "class_section", "class_section_id": world["section"].id},
        email=world["other_teacher"].email,
    )
    assert other_teacher.status_code == 403


def test_teacher_manage_scope_excludes_all_school_posts_and_includes_authored_or_assigned_targets(db, client, world):
    admin_school = create_announcement(client, world, {"title": "Admin school", "body": "All families", "audience_type": "school"}).json()
    admin_assigned_class = create_announcement(
        client,
        world,
        {"title": "Assigned class", "body": "For KG1A", "audience_type": "class_section", "class_section_id": world["section"].id},
    ).json()
    admin_assigned_subject = create_announcement(
        client,
        world,
        {"title": "Assigned subject", "body": "For English", "audience_type": "subject_group", "subject_group_id": world["group"].id},
    ).json()
    admin_other_class = create_announcement(
        client,
        world,
        {"title": "Other class", "body": "Not assigned", "audience_type": "class_section", "class_section_id": world["other_section"].id},
    ).json()
    teacher_own = create_announcement(
        client,
        world,
        {"title": "Teacher own", "body": "Created by teacher", "audience_type": "class_section", "class_section_id": world["section"].id},
        email=world["teacher"].email,
    ).json()
    teacher_authored_school = Announcement(
        school_id=world["alpha"].id,
        author_user_id=world["teacher"].id,
        title="Teacher-authored school",
        body="Legacy or admin-authored-by-this-user post",
        audience_type="school",
        status="published",
    )
    db.add(teacher_authored_school)
    db.add(Membership(school_id=world["alpha"].id, user_id=world["teacher"].id, role="school_admin"))
    db.commit()

    teacher_response = client.get(
        "/api/teach/announcements",
        headers=bearer(world["teacher"].email, world["alpha"].id),
    )
    assert teacher_response.status_code == 200
    teacher_ids = {row["id"] for row in teacher_response.json()["announcements"]}
    assert teacher_ids == {
        admin_assigned_class["id"],
        admin_assigned_subject["id"],
        teacher_own["id"],
    }
    assert admin_school["id"] not in teacher_ids
    assert teacher_authored_school.id not in teacher_ids
    assert admin_other_class["id"] not in teacher_ids

    admin_response = client.get(
        "/api/school/announcements",
        headers=bearer(world["admin"].email, world["alpha"].id),
    )
    assert admin_response.status_code == 200
    assert admin_school["id"] in {row["id"] for row in admin_response.json()["announcements"]}

    guardian_response = client.get("/api/guardian/announcements", headers=bearer(world["guardian"].email))
    assert guardian_response.status_code == 200
    assert admin_school["id"] in {row["id"] for row in guardian_response.json()["announcements"]}


def test_teacher_manage_attachment_download_uses_same_scope(db, client, world):
    unrelated = create_announcement(client, world, {"title": "Admin school file", "body": "Private to management", "audience_type": "school"}).json()
    unrelated_attachment = client.post(
        f"/api/school/announcements/{unrelated['id']}/attachments",
        headers=bearer(world["admin"].email, world["alpha"].id),
        files={"file": ("school.pdf", b"school-wide", "application/pdf")},
    ).json()
    assigned = create_announcement(
        client,
        world,
        {"title": "Assigned file", "body": "Teacher can manage", "audience_type": "class_section", "class_section_id": world["section"].id},
    ).json()
    assigned_attachment = client.post(
        f"/api/school/announcements/{assigned['id']}/attachments",
        headers=bearer(world["admin"].email, world["alpha"].id),
        files={"file": ("class.pdf", b"assigned-class", "application/pdf")},
    ).json()

    denied = client.get(
        f"/api/teach/announcements/{unrelated['id']}/attachments/{unrelated_attachment['id']}/download",
        headers=bearer(world["teacher"].email, world["alpha"].id),
    )
    assert denied.status_code == 404

    allowed = client.get(
        f"/api/teach/announcements/{assigned['id']}/attachments/{assigned_attachment['id']}/download",
        headers=bearer(world["teacher"].email, world["alpha"].id),
    )
    assert allowed.status_code == 200
    assert allowed.content == b"assigned-class"


def test_teacher_manage_list_is_cross_school_isolated(client, world):
    beta_school = create_announcement(
        client,
        world,
        {"title": "Beta school", "body": "Beta only", "audience_type": "school"},
        email=world["beta_admin"].email,
        school=world["beta"],
    )
    assert beta_school.status_code == 201

    alpha_list = client.get(
        "/api/teach/announcements",
        headers=bearer(world["teacher"].email, world["alpha"].id),
    )
    assert alpha_list.status_code == 200
    assert beta_school.json()["id"] not in {row["id"] for row in alpha_list.json()["announcements"]}

    beta_list = client.get(
        "/api/teach/announcements",
        headers=bearer(world["teacher"].email, world["beta"].id),
    )
    assert beta_list.status_code == 403


def test_wrong_school_and_unauthenticated_requests_are_blocked(client, world):
    wrong_school = create_announcement(
        client,
        world,
        {"title": "Cross school", "body": "No", "audience_type": "class_section", "class_section_id": world["section"].id},
        email=world["beta_admin"].email,
        school=world["beta"],
    )
    assert wrong_school.status_code == 404
    unauthenticated = client.get("/api/guardian/announcements")
    assert unauthenticated.status_code == 401


def test_guardian_sees_relevant_school_class_subject_posts_without_duplicates(db, client, world):
    create_announcement(client, world, {"title": "School", "body": "All families", "audience_type": "school"})
    create_announcement(client, world, {"title": "Class", "body": "For KG1A", "audience_type": "class_section", "class_section_id": world["section"].id})
    create_announcement(client, world, {"title": "Subject", "body": "For English", "audience_type": "subject_group", "subject_group_id": world["group"].id})
    create_announcement(client, world, {"title": "Other class", "body": "Hidden", "audience_type": "class_section", "class_section_id": world["other_section"].id})

    resp = client.get("/api/guardian/announcements", headers=bearer(world["guardian"].email))
    assert resp.status_code == 200
    titles = [row["title"] for row in resp.json()["announcements"]]
    assert titles.count("School") == 1
    assert titles.count("Class") == 1
    assert titles.count("Subject") == 1
    assert "Other class" not in titles
    assert all("body" not in row for row in resp.json()["announcements"])
    assert all("preview" in row for row in resp.json()["announcements"])


def test_revoked_link_loses_access_and_archived_hidden(db, client, world):
    created = create_announcement(client, world, {"title": "Class", "body": "For KG1A", "audience_type": "class_section", "class_section_id": world["section"].id}).json()
    listed = client.get("/api/guardian/announcements", headers=bearer(world["guardian"].email))
    assert len(listed.json()["announcements"]) == 1

    link = db.query(GuardianLink).filter_by(user_id=world["guardian"].id, student_id=world["student"].id).one()
    link.status = "revoked"
    link.revoked_at = invite_tokens.now_utc()
    sibling_link = db.query(GuardianLink).filter_by(user_id=world["guardian"].id, student_id=world["sibling"].id).one()
    sibling_link.status = "revoked"
    sibling_link.revoked_at = invite_tokens.now_utc()
    db.commit()
    revoked = client.get("/api/guardian/announcements", headers=bearer(world["guardian"].email))
    assert revoked.json()["announcements"] == []

    admin_archive = client.delete(f"/api/school/announcements/{created['id']}", headers=bearer(world["admin"].email, world["alpha"].id))
    assert admin_archive.status_code == 200
    link.status = "active"
    link.revoked_at = None
    sibling_link.status = "active"
    sibling_link.revoked_at = None
    db.commit()
    archived = client.get("/api/guardian/announcements", headers=bearer(world["guardian"].email))
    assert archived.json()["announcements"] == []


def test_detail_authorization_and_attachment_upload_download(db, client, world):
    created = create_announcement(client, world, {"title": "Files", "body": "See attached", "audience_type": "school"}).json()
    upload = client.post(
        f"/api/school/announcements/{created['id']}/attachments",
        headers=bearer(world["admin"].email, world["alpha"].id),
        files={"file": ("notice.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert upload.status_code == 201
    attachment = upload.json()
    assert attachment["original_filename"] == "notice.pdf"
    stored = db.query(AnnouncementAttachment).one()
    assert stored.storage_key != "notice.pdf"
    assert not stored.storage_key.startswith("/")

    detail = client.get(f"/api/guardian/announcements/{created['id']}", headers=bearer(world["guardian"].email))
    assert detail.status_code == 200
    assert detail.json()["body"] == "See attached"
    assert detail.json()["attachments"][0]["original_filename"] == "notice.pdf"

    download = client.get(
        f"/api/guardian/announcements/{created['id']}/attachments/{attachment['id']}/download",
        headers=bearer(world["guardian"].email),
    )
    assert download.status_code == 200
    assert download.content == b"%PDF-1.4"
    unauthorized = client.get(
        f"/api/guardian/announcements/{created['id']}/attachments/{attachment['id']}/download",
        headers=bearer(world["other_guardian"].email),
    )
    assert unauthorized.status_code == 200  # school-wide is visible to any active guardian in the school


def test_guardian_cannot_download_unauthorized_class_attachment(client, world):
    created = create_announcement(
        client,
        world,
        {"title": "Class file", "body": "For KG1A", "audience_type": "class_section", "class_section_id": world["section"].id},
    ).json()
    upload = client.post(
        f"/api/school/announcements/{created['id']}/attachments",
        headers=bearer(world["admin"].email, world["alpha"].id),
        files={"file": ("image.png", b"pngdata", "image/png")},
    ).json()
    unauthorized = client.get(
        f"/api/guardian/announcements/{created['id']}/attachments/{upload['id']}/download",
        headers=bearer(world["other_guardian"].email),
    )
    assert unauthorized.status_code == 404


def test_guardian_list_returns_unread_count_newest_first_without_marking_read(db, client, world):
    first = create_announcement(client, world, {"title": "First", "body": "A", "audience_type": "school"}).json()
    second = create_announcement(client, world, {"title": "Second", "body": "B", "audience_type": "school"}).json()

    resp = client.get("/api/guardian/announcements", headers=bearer(world["guardian"].email))
    assert resp.status_code == 200
    body = resp.json()
    assert body["unread_count"] == 2
    ids_in_order = [row["id"] for row in body["announcements"]]
    assert ids_in_order == [second["id"], first["id"]]
    assert all(row["is_read"] is False for row in body["announcements"])
    assert db.query(AnnouncementRead).count() == 0


def test_opening_announcement_marks_read_and_decreases_unread_count(db, client, world):
    created = create_announcement(client, world, {"title": "Notice", "body": "Read me", "audience_type": "school"}).json()

    before = client.get("/api/guardian/announcements", headers=bearer(world["guardian"].email)).json()
    assert before["unread_count"] == 1

    detail = client.get(f"/api/guardian/announcements/{created['id']}", headers=bearer(world["guardian"].email))
    assert detail.status_code == 200
    assert detail.json()["is_read"] is True

    after = client.get("/api/guardian/announcements", headers=bearer(world["guardian"].email)).json()
    assert after["unread_count"] == 0
    assert after["announcements"][0]["is_read"] is True

    read_row = db.query(AnnouncementRead).one()
    assert read_row.user_id == world["guardian"].id
    assert read_row.announcement_id == created["id"]

    # Reopening does not create a duplicate read row.
    client.get(f"/api/guardian/announcements/{created['id']}", headers=bearer(world["guardian"].email))
    assert db.query(AnnouncementRead).count() == 1


def test_read_state_is_per_user_and_does_not_leak(client, world):
    created = create_announcement(client, world, {"title": "School wide", "body": "Everyone", "audience_type": "school"}).json()

    client.get(f"/api/guardian/announcements/{created['id']}", headers=bearer(world["guardian"].email))

    guardian_view = client.get("/api/guardian/announcements", headers=bearer(world["guardian"].email)).json()
    assert guardian_view["unread_count"] == 0

    other_guardian_view = client.get("/api/guardian/announcements", headers=bearer(world["other_guardian"].email)).json()
    assert other_guardian_view["unread_count"] == 1
    assert other_guardian_view["announcements"][0]["is_read"] is False


def test_unauthorized_guardian_cannot_mark_or_read_announcement(db, client, world):
    created = create_announcement(
        client,
        world,
        {"title": "Class only", "body": "KG1A families", "audience_type": "class_section", "class_section_id": world["section"].id},
    ).json()

    unauthorized = client.get(f"/api/guardian/announcements/{created['id']}", headers=bearer(world["other_guardian"].email))
    assert unauthorized.status_code == 404
    assert db.query(AnnouncementRead).count() == 0


def test_attachment_validation_rejects_blocked_and_oversized_files(client, world):
    created = create_announcement(client, world, {"title": "Files", "body": "See attached", "audience_type": "school"}).json()
    blocked = client.post(
        f"/api/school/announcements/{created['id']}/attachments",
        headers=bearer(world["admin"].email, world["alpha"].id),
        files={"file": ("bad.js", b"alert(1)", "application/javascript")},
    )
    assert blocked.status_code == 400

    oversized = client.post(
        f"/api/school/announcements/{created['id']}/attachments",
        headers=bearer(world["admin"].email, world["alpha"].id),
        files={"file": ("large.pdf", b"x" * (announcements.MAX_ATTACHMENT_BYTES + 1), "application/pdf")},
    )
    assert oversized.status_code == 400

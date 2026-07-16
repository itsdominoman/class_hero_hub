import os
from io import BytesIO
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pillow_heif import register_heif_opener
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
    StaffAssignment,
    Student,
    Subject,
    SubjectGroup,
    UpdatePhoto,
    UpdatePost,
    User,
)
from app.routes import updates
from app.update_image_service import (
    MAX_OUTPUT_IMAGE_BYTES,
    PREFERRED_MINIMUM_QUALITY,
    STARTING_QUALITY,
    TARGET_OUTPUT_IMAGE_BYTES,
    optimise_update_photo,
)

register_heif_opener()


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
database.engine = engine
database.SessionLocal = TestingSessionLocal


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(updates, "UPLOAD_ROOT", tmp_path / "update_uploads")
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
    teacher = create_user(db, "teacher@example.com", "Teacher")
    other_teacher = create_user(db, "other-teacher@example.com", "Other Teacher")
    guardian = create_user(db, "guardian@example.com", "Guardian")
    other_guardian = create_user(db, "other-guardian@example.com", "Other Guardian")

    alpha = School(name="Alpha Academy", slug="alpha", status="active")
    beta = School(name="Beta School", slug="beta", status="active")
    db.add_all([alpha, beta])
    db.flush()

    teacher_membership = Membership(school_id=alpha.id, user_id=teacher.id, role="teacher")
    other_teacher_membership = Membership(school_id=alpha.id, user_id=other_teacher.id, role="teacher")
    guardian_membership = Membership(school_id=alpha.id, user_id=guardian.id, role="guardian")
    other_guardian_membership = Membership(school_id=alpha.id, user_id=other_guardian.id, role="guardian")
    db.add_all([teacher_membership, other_teacher_membership, guardian_membership, other_guardian_membership])
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
            GuardianLink(school_id=alpha.id, student_id=student.id, user_id=guardian.id, relationship="mother", status="active"),
            GuardianLink(school_id=alpha.id, student_id=other_student.id, user_id=other_guardian.id, relationship="father", status="active"),
        ]
    )
    db.commit()
    return locals()


def create_update(client, world, **overrides):
    payload = {"body": "We built volcanoes today!", "audience_type": "class_section", "class_section_id": world["section"].id}
    payload.update(overrides.pop("payload", {}))
    return client.post("/api/teach/updates", headers=bearer(overrides.pop("email", world["teacher"].email), overrides.pop("school_id", world["alpha"].id)), json=payload)


def image_bytes(format="JPEG", size=(120, 80), *, orientation=None, transparency=False):
    image = Image.new("RGBA" if transparency else "RGB", size, (20, 80, 160, 120) if transparency else (20, 80, 160))
    output = BytesIO()
    options = {}
    if orientation:
        exif = Image.Exif(); exif[274] = orientation; options["exif"] = exif
    image.save(output, format=format, **options)
    return output.getvalue()


def upload_photo(client, world, post_id, filename="photo.jpg", content=None, **overrides):
    if content is None:
        content = image_bytes()
    return client.post(
        f"/api/teach/updates/{post_id}/photos",
        headers=bearer(overrides.pop("email", world["teacher"].email), overrides.pop("school_id", world["alpha"].id)),
        files={"file": (filename, content)},
    )


def test_teacher_create_requires_exact_assignment(db, client, world):
    assert create_update(client, world).status_code == 201
    assert create_update(client, world, payload={"audience_type": "subject_group", "class_section_id": None, "subject_group_id": world["group"].id}).status_code == 201
    # Unassigned target and unassigned teacher are both rejected
    assert create_update(client, world, payload={"class_section_id": world["other_section"].id}).status_code == 403
    assert create_update(client, world, email=world["other_teacher"].email).status_code == 403
    # Cross-school target is not found
    assert create_update(client, world, payload={"class_section_id": world["beta_section"].id}).status_code == 404
    assert db.query(UpdatePost).count() == 2


def test_teacher_edit_archive_scope_and_archived_lock(db, client, world):
    post = create_update(client, world).json()
    headers = bearer(world["teacher"].email, world["alpha"].id)
    other = bearer(world["other_teacher"].email, world["alpha"].id)
    assert client.patch(f'/api/teach/updates/{post["id"]}', headers=other, json={"body": "Hacked"}).status_code == 404
    assert client.delete(f'/api/teach/updates/{post["id"]}', headers=other).status_code == 404
    edited = client.patch(f'/api/teach/updates/{post["id"]}', headers=headers, json={"body": "Corrected caption"})
    assert edited.status_code == 200 and edited.json()["body"] == "Corrected caption"
    assert client.delete(f'/api/teach/updates/{post["id"]}', headers=headers).status_code == 200
    archived = db.query(UpdatePost).filter_by(id=post["id"]).one()
    assert archived.status == "archived" and archived.archived_at is not None
    # Archived posts cannot be edited or receive photos
    assert client.patch(f'/api/teach/updates/{post["id"]}', headers=headers, json={"body": "Too late"}).status_code == 409
    assert upload_photo(client, world, post["id"]).status_code == 409


def test_teacher_list_scoped_to_target_and_assignments(client, world):
    class_post = create_update(client, world).json()
    group_post = create_update(client, world, payload={"audience_type": "subject_group", "class_section_id": None, "subject_group_id": world["group"].id}).json()
    headers = bearer(world["teacher"].email, world["alpha"].id)
    listed = client.get(f'/api/teach/updates?class_section_id={world["section"].id}', headers=headers).json()["items"]
    assert [row["id"] for row in listed] == [class_post["id"]]
    assert client.get(f'/api/teach/updates?class_section_id={world["other_section"].id}', headers=headers).status_code == 403
    assert client.get("/api/teach/updates", headers=bearer(world["other_teacher"].email, world["alpha"].id)).json()["items"] == []
    assert group_post["id"] in {row["id"] for row in client.get("/api/teach/updates", headers=headers).json()["items"]}


def test_photo_type_size_and_count_rules(client, world):
    post = create_update(client, world).json()
    for filename, format in (("a.jpg", "JPEG"), ("b.png", "PNG"), ("c.webp", "WEBP"), ("iphone.heic", "HEIF")):
        response = upload_photo(client, world, post["id"], filename=filename, content=image_bytes(format))
        assert response.status_code == 201, f"{filename}: {response.text}"
        assert response.json()["content_type"] == "image/jpeg"
    # Content, rather than a claimed extension or MIME type, is decisive.
    for filename in ("clip.mp4", "movie.mov", "sound.mp3", "archive.zip", "run.exe", "raw.cr2", "page.html"):
        assert upload_photo(client, world, post["id"], filename=filename, content=b"not-an-image").status_code == 400, filename
    oversized = upload_photo(client, world, post["id"], filename="big.jpg", content=b"x" * (50 * 1024 * 1024 + 1))
    assert oversized.status_code == 400
    # Fifth photo is allowed, sixth is not
    assert upload_photo(client, world, post["id"], filename="e.png", content=image_bytes("PNG")).status_code == 201
    sixth = upload_photo(client, world, post["id"], filename="f.png")
    assert sixth.status_code == 400 and "Maximum 5 photos" in sixth.json()["detail"]


def test_unassigned_teacher_cannot_upload_or_view_photo(client, world):
    post = create_update(client, world).json()
    photo = upload_photo(client, world, post["id"]).json()
    assert upload_photo(client, world, post["id"], email=world["other_teacher"].email).status_code == 404
    denied = client.get(f'/api/teach/updates/{post["id"]}/photos/{photo["id"]}/view', headers=bearer(world["other_teacher"].email, world["alpha"].id))
    assert denied.status_code == 404
    allowed = client.get(f'/api/teach/updates/{post["id"]}/photos/{photo["id"]}/view', headers=bearer(world["teacher"].email, world["alpha"].id))
    assert allowed.status_code == 200 and allowed.headers["content-type"] == "image/jpeg"
    assert "attachment" not in allowed.headers.get("content-disposition", "")


def test_guardian_sees_only_relevant_active_posts(db, client, world):
    class_post = create_update(client, world).json()
    group_post = create_update(client, world, payload={"audience_type": "subject_group", "class_section_id": None, "subject_group_id": world["group"].id}).json()
    hidden_post = create_update(client, world, payload={"body": "Other class", "class_section_id": world["other_section"].id}, email=world["other_teacher"].email)
    assert hidden_post.status_code == 403  # other_teacher unassigned; create directly instead
    db.add(UpdatePost(school_id=world["alpha"].id, author_user_id=world["other_teacher"].id, body="Other class only", audience_type="class_section", class_section_id=world["other_section"].id))
    db.commit()
    headers = bearer(world["guardian"].email)
    listed = client.get("/api/guardian/updates", headers=headers)
    assert listed.status_code == 200
    assert {row["id"] for row in listed.json()["items"]} == {class_post["id"], group_post["id"]}
    forbidden_keys = {"guardian_email", "token", "invite", "email", "user_id", "author_user_id"}
    assert not forbidden_keys.intersection(listed.json()["items"][0])
    assert all("body" not in row for row in listed.json()["items"])
    assert client.get(f'/api/guardian/updates/{class_post["id"]}', headers=headers).status_code == 200
    assert client.get(f'/api/guardian/updates/{class_post["id"]}', headers=bearer(world["other_guardian"].email)).status_code == 404


def test_guardian_photo_view_authorization(client, world):
    post = create_update(client, world).json()
    photo = upload_photo(client, world, post["id"]).json()
    allowed = client.get(f'/api/guardian/updates/{post["id"]}/photos/{photo["id"]}/view', headers=bearer(world["guardian"].email))
    assert allowed.status_code == 200 and allowed.headers["content-type"] == "image/jpeg"
    assert client.get(f'/api/guardian/updates/{post["id"]}/photos/{photo["id"]}/view', headers=bearer(world["other_guardian"].email)).status_code == 404
    # Invalid photo ids do not leak files
    assert client.get(f'/api/guardian/updates/{post["id"]}/photos/999999/view', headers=bearer(world["guardian"].email)).status_code == 404


def test_archived_post_disappears_from_guardian_access(client, world):
    post = create_update(client, world).json()
    photo = upload_photo(client, world, post["id"]).json()
    headers = bearer(world["guardian"].email)
    assert post["id"] in {row["id"] for row in client.get("/api/guardian/updates", headers=headers).json()["items"]}
    assert client.delete(f'/api/teach/updates/{post["id"]}', headers=bearer(world["teacher"].email, world["alpha"].id)).status_code == 200
    assert client.get("/api/guardian/updates", headers=headers).json()["items"] == []
    assert client.get(f'/api/guardian/updates/{post["id"]}', headers=headers).status_code == 404
    assert client.get(f'/api/guardian/updates/{post["id"]}/photos/{photo["id"]}/view', headers=headers).status_code == 404


def test_revoked_link_and_ended_enrolment_remove_access(db, client, world):
    post = create_update(client, world).json()
    headers = bearer(world["guardian"].email)
    assert post["id"] in {row["id"] for row in client.get("/api/guardian/updates", headers=headers).json()["items"]}
    # Ended enrolment removes access
    enrolment = db.query(Enrolment).filter_by(student_id=world["student"].id).one()
    enrolment.valid_to = date.today() - timedelta(days=1)
    db.commit()
    assert client.get("/api/guardian/updates", headers=headers).json()["items"] == []
    assert client.get(f'/api/guardian/updates/{post["id"]}', headers=headers).status_code == 404
    # Restore enrolment, then revoke the guardian link
    enrolment.valid_to = None
    for link in db.query(GuardianLink).filter(GuardianLink.user_id == world["guardian"].id).all():
        link.status = "revoked"; link.revoked_at = invite_tokens.now_utc()
    db.commit()
    assert client.get("/api/guardian/updates", headers=headers).json()["items"] == []
    assert client.get(f'/api/guardian/updates/{post["id"]}', headers=headers).status_code == 404


def test_storage_keys_are_safe_and_traversal_is_blocked(db, client, world):
    post = create_update(client, world).json()
    photo = upload_photo(client, world, post["id"], filename="../../../etc/passwd.jpg").json()
    stored = db.query(UpdatePhoto).one()
    assert not stored.storage_key.startswith("/") and ".." not in stored.storage_key
    assert stored.original_filename == "passwd.jpg"
    # A tampered storage key resolving outside the upload root is refused
    stored.storage_key = "../../etc/hosts"
    db.commit()
    tampered = client.get(f'/api/guardian/updates/{post["id"]}/photos/{photo["id"]}/view', headers=bearer(world["guardian"].email))
    assert tampered.status_code == 404


def test_optimisation_corrects_orientation_strips_metadata_and_keeps_only_display_image(db, client, world):
    post = create_update(client, world).json()
    raw = image_bytes("JPEG", size=(1000, 1800), orientation=6)
    photo = upload_photo(client, world, post["id"], filename="portrait.jpg", content=raw).json()
    stored = db.query(UpdatePhoto).one()
    stored_path = updates._path(stored.storage_key)
    assert stored.content_type == "image/jpeg" and stored.size_bytes == stored_path.stat().st_size
    assert stored.size_bytes < 1.5 * 1024 * 1024
    assert stored_path.suffix == ".jpg" and stored_path.read_bytes() != raw
    with Image.open(stored_path) as image:
        assert image.size == (1600, 889)  # orientation is applied before resize
        assert not image.getexif()
    assert [path for path in updates.UPLOAD_ROOT.rglob("*") if path.is_file()] == [stored_path]
    response = client.get(f'/api/teach/updates/{post["id"]}/photos/{photo["id"]}/view', headers=bearer(world["teacher"].email, world["alpha"].id))
    assert response.status_code == 200 and response.headers["content-type"] == "image/jpeg"


def test_huge_dimensions_are_resized_and_transparency_uses_webp(db, client, world):
    post = create_update(client, world).json()
    photo = upload_photo(client, world, post["id"], filename="large.png", content=image_bytes("PNG", (3200, 2400), transparency=True)).json()
    stored = db.query(UpdatePhoto).one()
    assert stored.content_type == "image/webp" and stored.size_bytes <= 1.5 * 1024 * 1024
    with Image.open(updates._path(stored.storage_key)) as image:
        assert max(image.size) == 1600
        assert image.mode == "RGBA"


def test_optimisation_is_quality_first_for_simple_and_detailed_images():
    # A low-detail image should retain the initial quality rather than being
    # made tiny simply because it can be compressed further.
    simple = optimise_update_photo(image_bytes("JPEG", (1600, 1200)))
    assert simple.quality_used == STARTING_QUALITY
    assert len(simple.content) <= TARGET_OUTPUT_IMAGE_BYTES

    # Deterministic high-frequency pixels emulate detailed artwork/writing.
    # It needs more bytes at 1600px, so it may use the preferred 78 quality
    # and remain above the normal target, but it must never exceed the cap.
    source = Image.frombytes("RGB", (1600, 1200), bytes((index * 73 + index // 17) % 256 for index in range(1600 * 1200 * 3)))
    raw = BytesIO()
    source.save(raw, format="JPEG", quality=95)
    detailed = optimise_update_photo(raw.getvalue())
    assert detailed.quality_used >= PREFERRED_MINIMUM_QUALITY
    assert len(detailed.content) <= MAX_OUTPUT_IMAGE_BYTES


def test_body_validation_and_unauthenticated_blocked(client, world):
    assert create_update(client, world, payload={"body": "   "}).status_code == 422
    assert create_update(client, world, payload={"audience_type": "school", "class_section_id": None}).status_code == 422
    assert create_update(client, world, payload={"class_section_id": None}).status_code == 400
    assert client.get("/api/guardian/updates").status_code == 401

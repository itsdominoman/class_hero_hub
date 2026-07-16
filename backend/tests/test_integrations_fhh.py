import os
import logging
from io import BytesIO
from datetime import timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database, invite_tokens
from app.database import Base, get_db
from app.main import app, protected_media_access_log_filter
from app.models_school import AcademicYear, BehaviourCategory, BehaviourEvent, BranchCampus, ClassSection, Enrolment, FhhLink, FhhLinkInvite, GradeLevel, Membership, School, Student, Subject, SubjectGroup, UpdatePhoto, UpdatePost, User
from app.routes import integrations_fhh, updates

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)


@pytest.fixture
def db(tmp_path, monkeypatch):
    database.engine = engine; database.SessionLocal = Session
    monkeypatch.setattr(database.settings, "FHH_INTEGRATION_ENABLED", True)
    monkeypatch.setattr(database.settings, "FHH_INTEGRATION_SERVICE_TOKEN", "s" * 40)
    monkeypatch.setattr(database.settings, "FHH_INTEGRATION_ALLOWED_IPS", "")
    monkeypatch.setattr(updates, "UPLOAD_ROOT", tmp_path / "update_uploads")
    integrations_fhh.AUTH_LIMITER._attempts.clear(); integrations_fhh.LINK_LIMITER._attempts.clear()
    Base.metadata.create_all(engine); session = Session()
    yield session
    session.close(); Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    def override():
        session = Session()
        try: yield session
        finally: session.close()
    app.dependency_overrides[get_db] = override
    yield TestClient(app, client=("127.0.0.1", 50000))
    app.dependency_overrides.clear()


@pytest.fixture
def world(db):
    admin = User(email="admin@test", name="Admin", google_sub="admin")
    school = School(name="Alpha", name_ar="ألفا", slug="alpha", status="active")
    db.add_all([admin, school]); db.flush()
    db.add(Membership(school_id=school.id, user_id=admin.id, role="school_admin", status="active"))
    branch = BranchCampus(school_id=school.id, code="M", name="Main", status="active")
    year = AcademicYear(school_id=school.id, code="26", name="2026", status="active", is_current=True)
    grade = GradeLevel(school_id=school.id, code="G1", name="Grade 1", status="active")
    db.add_all([branch, year, grade]); db.flush()
    section = ClassSection(school_id=school.id, branch_campus_id=branch.id, academic_year_id=year.id, grade_level_id=grade.id, code="A", name="1A", status="active")
    db.add(section); db.flush()
    one = Student(school_id=school.id, first_name="Sara", last_name="A", status="active")
    two = Student(school_id=school.id, first_name="Omar", last_name="B", status="active")
    db.add_all([one, two]); db.flush()
    db.add_all([Enrolment(school_id=school.id, student_id=s.id, class_section_id=section.id, kind="member") for s in (one, two)])
    db.commit(); return locals()


def service(token="s" * 40, link_token=None):
    headers = {"Authorization": f"Bearer {token}"}
    if link_token: headers["X-FHH-Link-Token"] = link_token
    return headers


def admin(world):
    return {"Authorization": f"Bearer {auth.create_access_token({'sub': world['admin'].email})}", "X-School-Id": str(world["school"].id)}


def issue(client, world, student=None):
    return client.post(f"/api/school/students/{(student or world['one']).id}/fhh-invites", headers=admin(world))


def consume(client, code, ref="child-1"):
    return client.post("/api/integrations/fhh/link/consume", headers=service(), json={"code": code, "fhh_child_ref": ref})


def test_service_auth_disabled_missing_wrong_allowed_and_ip_allowlist(db, client, monkeypatch):
    monkeypatch.setattr(database.settings, "FHH_INTEGRATION_ENABLED", False)
    assert client.post("/api/integrations/fhh/link/verify", json={"code": "CHH-AAAA-BBBB"}).status_code == 404
    monkeypatch.setattr(database.settings, "FHH_INTEGRATION_ENABLED", True)
    assert client.post("/api/integrations/fhh/link/verify", json={"code": "CHH-AAAA-BBBB"}).status_code == 401
    assert client.post("/api/integrations/fhh/link/verify", headers=service("wrong"), json={"code": "CHH-AAAA-BBBB"}).status_code == 401
    assert client.post("/api/integrations/fhh/link/verify", headers=service(), json={"code": "CHH-AAAA-BBBB"}).status_code == 404
    monkeypatch.setattr(database.settings, "FHH_INTEGRATION_ALLOWED_IPS", "10.250.50.1")
    assert client.post("/api/integrations/fhh/link/verify", headers=service(), json={"code": "CHH-AAAA-BBBB"}).status_code == 403
    monkeypatch.setattr(database.settings, "FHH_INTEGRATION_ALLOWED_IPS", "127.0.0.1/8")
    assert client.post("/api/integrations/fhh/link/verify", headers=service(), json={"code": "CHH-AAAA-BBBB"}).status_code == 404


def test_admin_issue_list_and_same_school_active_rules(db, client, world):
    created = issue(client, world); assert created.status_code == 201
    assert created.json()["code"].startswith("CHH-")
    row = db.query(FhhLinkInvite).one(); assert created.json()["code"] not in row.token_hash
    listed = client.get(f"/api/school/students/{world['one'].id}/fhh-invites", headers=admin(world))
    assert listed.status_code == 200
    assert "code" not in listed.json()["invites"][0] and "token_hash" not in listed.json()["invites"][0]
    world["two"].status = "archived"; db.commit()
    assert issue(client, world, world["two"]).status_code == 400


def test_verify_expired_revoked_and_consume_single_use(db, client, world):
    code = issue(client, world).json()["code"]
    verified = client.post("/api/integrations/fhh/link/verify", headers=service(), json={"code": code})
    assert verified.status_code == 200 and verified.json()["student"]["display_name"] == "Sara A"
    row = db.query(FhhLinkInvite).one(); row.expires_at = invite_tokens.now_utc() - timedelta(seconds=1); db.commit()
    assert client.post("/api/integrations/fhh/link/verify", headers=service(), json={"code": code}).status_code == 404
    row.expires_at = invite_tokens.now_utc() + timedelta(hours=1); row.revoked_at = invite_tokens.now_utc(); db.commit()
    assert client.post("/api/integrations/fhh/link/verify", headers=service(), json={"code": code}).status_code == 404
    row.revoked_at = None; db.commit()
    first = consume(client, code); assert first.status_code == 200 and first.json()["link_token"]
    assert consume(client, code).status_code == 404
    link = db.query(FhhLink).one(); assert link.status == "active" and link.link_token_hash != first.json()["link_token"]


def test_dashboard_link_token_scope_and_revocation(db, client, world):
    one = consume(client, issue(client, world).json()["code"], "one").json()
    two = consume(client, issue(client, world, world["two"]).json()["code"], "two").json()
    url = f"/api/integrations/fhh/links/{one['link_id']}/dashboard"
    assert client.get(url, headers=service()).status_code == 404
    assert client.get(url, headers=service("wrong")).status_code == 401
    assert client.get(url, headers=service(link_token=two["link_token"])).status_code == 404
    ok = client.get(url, headers=service(link_token=one["link_token"])); assert ok.status_code == 200
    assert ok.json()["student"]["display_name"] == "Sara A"
    assert "avatar_id" in ok.json()["student"] and "Omar" not in ok.text
    for forbidden in ("token_hash", "link_token_hash", "storage_key", "/app/data/", "file://", "http://", "https://"):
        assert forbidden not in ok.text
    deleted = client.delete(f"/api/integrations/fhh/links/{one['link_id']}", headers=service(link_token=one["link_token"]))
    assert deleted.status_code == 200
    assert client.get(url, headers=service(link_token=one["link_token"])).status_code == 404


def test_link_scope_resolves_only_the_linked_student_with_bounded_queries(db, client, world):
    subject = Subject(school_id=world["school"].id, code="MAT", name="Maths", status="active")
    db.add(subject); db.flush()
    section_default = SubjectGroup(
        school_id=world["school"].id,
        academic_year_id=world["year"].id,
        class_section_id=world["section"].id,
        subject_id=subject.id,
        code="1A-MAT",
        name="1A Maths",
        status="active",
        enrolment_policy="default_for_section",
    )
    grade_default = SubjectGroup(
        school_id=world["school"].id,
        academic_year_id=world["year"].id,
        grade_level_id=world["grade"].id,
        subject_id=subject.id,
        code="G1-MAT",
        name="Grade 1 Maths",
        status="active",
        enrolment_policy="default_for_grade",
    )
    explicit = SubjectGroup(
        school_id=world["school"].id,
        academic_year_id=world["year"].id,
        class_section_id=world["section"].id,
        subject_id=subject.id,
        code="1A-MAT-X",
        name="1A Maths explicit",
        status="active",
        enrolment_policy="explicit_only",
    )
    archived = SubjectGroup(
        school_id=world["school"].id,
        academic_year_id=world["year"].id,
        grade_level_id=world["grade"].id,
        subject_id=subject.id,
        code="G1-MAT-OLD",
        name="Archived Grade 1 Maths",
        status="archived",
        enrolment_policy="default_for_grade",
    )
    db.add_all([section_default, grade_default, explicit, archived]); db.flush()
    db.add_all([
        Enrolment(school_id=world["school"].id, student_id=world["one"].id, subject_group_id=explicit.id, kind="member"),
        Enrolment(school_id=world["school"].id, student_id=world["one"].id, subject_group_id=section_default.id, kind="excluded"),
    ])
    db.commit()
    linked = consume(client, issue(client, world).json()["code"], "one").json()
    link = db.query(FhhLink).filter(FhhLink.id == linked["link_id"]).one()

    statements = []

    def count_statement(*_args):
        statements.append(1)

    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        sections, groups = integrations_fhh._scope(db, link)
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)

    assert sections == {world["section"].id}
    assert groups == {grade_default.id, explicit.id}
    assert len(statements) == 3


def test_fhh_update_photo_proxy_serves_only_optimised_artifact(db, client, world):
    linked = consume(client, issue(client, world).json()["code"], "one").json()
    update = UpdatePost(school_id=world["school"].id, author_user_id=world["admin"].id, body="Photo update", audience_type="class_section", class_section_id=world["section"].id)
    db.add(update); db.flush()
    image = Image.new("RGB", (20, 10), "red")
    output = BytesIO(); image.save(output, "JPEG", quality=75)
    storage_key = f"school-{world['school'].id}/update-{update.id}/optimised.jpg"
    path = updates._path(storage_key); path.parent.mkdir(parents=True); path.write_bytes(output.getvalue())
    photo = UpdatePhoto(post_id=update.id, school_id=world["school"].id, uploaded_by_user_id=world["admin"].id, original_filename="iphone.heic", storage_key=storage_key, content_type="image/jpeg", size_bytes=path.stat().st_size)
    db.add(photo); db.commit()
    response = client.get(f"/api/integrations/fhh/links/{linked['link_id']}/updates/{update.id}/photos/{photo.id}/view", headers=service(link_token=linked["link_token"]))
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == path.read_bytes()
    assert b"heic" not in response.content.lower()
    thumbnail_key = updates.thumbnail_storage_key(storage_key, ".jpg")
    thumbnail_path = updates._path(thumbnail_key)
    thumbnail_path.write_bytes(b"protected-thumbnail")
    thumbnail = client.get(f"/api/integrations/fhh/links/{linked['link_id']}/updates/{update.id}/photos/{photo.id}/thumbnail", headers=service(link_token=linked["link_token"]))
    assert thumbnail.status_code == 200
    assert thumbnail.content == b"protected-thumbnail"
    assert thumbnail.headers["content-type"] == "image/jpeg"
    assert thumbnail.headers["cache-control"] == "private, no-store, max-age=0"
    assert thumbnail.headers["x-content-type-options"] == "nosniff"


def test_fhh_update_photo_rejects_invalid_revoked_cross_student_and_cross_school_links(db, client, world):
    one_link = consume(client, issue(client, world).json()["code"], "one").json()
    two_link = consume(client, issue(client, world, world["two"]).json()["code"], "two").json()
    subject = Subject(school_id=world["school"].id, code="SCI", name="Science", status="active")
    db.add(subject); db.flush()
    group = SubjectGroup(
        school_id=world["school"].id,
        academic_year_id=world["year"].id,
        class_section_id=world["section"].id,
        subject_id=subject.id,
        code="1A-SCI-X",
        name="Science explicit",
        status="active",
        enrolment_policy="explicit_only",
    )
    db.add(group); db.flush()
    db.add(Enrolment(school_id=world["school"].id, student_id=world["one"].id, subject_group_id=group.id, kind="member"))
    update = UpdatePost(
        school_id=world["school"].id,
        author_user_id=world["admin"].id,
        body="Scoped photo",
        audience_type="subject_group",
        subject_group_id=group.id,
    )
    db.add(update); db.flush()
    storage_key = f"school-{world['school'].id}/update-{update.id}/scoped.jpg"
    path = updates._path(storage_key); path.parent.mkdir(parents=True); path.write_bytes(b"scoped-private-bytes")
    thumbnail_path = updates._path(updates.thumbnail_storage_key(storage_key, ".jpg"))
    thumbnail_path.write_bytes(b"scoped-private-thumbnail")
    photo = UpdatePhoto(
        post_id=update.id,
        school_id=world["school"].id,
        uploaded_by_user_id=world["admin"].id,
        original_filename="scoped.jpg",
        storage_key=storage_key,
        content_type="image/jpeg",
        size_bytes=path.stat().st_size,
    )
    db.add(photo); db.commit()

    one_url = f"/api/integrations/fhh/links/{one_link['link_id']}/updates/{update.id}/photos/{photo.id}/view"
    one_thumbnail_url = f"/api/integrations/fhh/links/{one_link['link_id']}/updates/{update.id}/photos/{photo.id}/thumbnail"
    assert client.get(one_url, headers=service(link_token="invalid-link-token")).status_code == 404
    assert client.get(one_url, headers=service(link_token=one_link["link_token"])).content == b"scoped-private-bytes"
    assert client.get(one_thumbnail_url, headers=service(link_token="invalid-link-token")).status_code == 404
    assert client.get(one_thumbnail_url, headers=service(link_token=one_link["link_token"])).content == b"scoped-private-thumbnail"
    two_url = f"/api/integrations/fhh/links/{two_link['link_id']}/updates/{update.id}/photos/{photo.id}/view"
    two_thumbnail_url = f"/api/integrations/fhh/links/{two_link['link_id']}/updates/{update.id}/photos/{photo.id}/thumbnail"
    assert client.get(two_url, headers=service(link_token=two_link["link_token"])).status_code == 404
    assert client.get(two_thumbnail_url, headers=service(link_token=two_link["link_token"])).status_code == 404

    other_school = School(name="Other", slug="other", status="active")
    db.add(other_school); db.flush()
    other_student = Student(school_id=other_school.id, first_name="Other", last_name="Student", status="active")
    db.add(other_student); db.flush()
    other_invite = FhhLinkInvite(
        school_id=other_school.id,
        student_id=other_student.id,
        token_hash=invite_tokens.hash_token("other-invite"),
        display_code_last4="TEST",
        expires_at=invite_tokens.now_utc() + timedelta(hours=1),
        created_by_user_id=world["admin"].id,
    )
    db.add(other_invite); db.flush()
    other_raw_token = "other-link-token"
    other_link = FhhLink(
        school_id=other_school.id,
        student_id=other_student.id,
        source_invite_id=other_invite.id,
        link_token_hash=invite_tokens.hash_token(other_raw_token),
        fhh_child_ref="other-child",
    )
    db.add(other_link); db.commit()
    other_url = f"/api/integrations/fhh/links/{other_link.id}/updates/{update.id}/photos/{photo.id}/view"
    assert client.get(other_url, headers=service(link_token=other_raw_token)).status_code == 404

    stored_one_link = db.query(FhhLink).filter(FhhLink.id == one_link["link_id"]).one()
    stored_one_link.status = "revoked"; stored_one_link.revoked_at = invite_tokens.now_utc(); db.commit()
    assert client.get(one_url, headers=service(link_token=one_link["link_token"])).status_code == 404
    assert client.get(one_thumbnail_url, headers=service(link_token=one_link["link_token"])).status_code == 404


def test_dashboard_point_events_include_only_safe_display_context(db, client, world):
    category = BehaviourCategory(school_id=world["school"].id, type="positive", label="Respectful behaviour", points_value=1, active=True)
    subject = Subject(school_id=world["school"].id, code="ENG", name="English", status="active")
    db.add_all([category, subject]); db.flush()
    group = SubjectGroup(school_id=world["school"].id, academic_year_id=world["year"].id, class_section_id=world["section"].id, subject_id=subject.id, code="1A-ENG", name="1A English", status="active", enrolment_policy="default_for_section")
    db.add(group); db.flush()
    db.add_all([
        BehaviourEvent(school_id=world["school"].id, student_id=world["one"].id, category_id=category.id, actor_user_id=world["admin"].id, points_delta=1, source="teacher", context_type="subject", subject_group_id=group.id),
        BehaviourEvent(school_id=world["school"].id, student_id=world["one"].id, category_id=category.id, actor_user_id=world["admin"].id, points_delta=1, source="teacher", context_type="duty", duty_context="break"),
    ])
    db.commit()
    linked = consume(client, issue(client, world).json()["code"], "one").json()
    response = client.get(f"/api/integrations/fhh/links/{linked['link_id']}/dashboard", headers=service(link_token=linked["link_token"]))
    assert response.status_code == 200
    events = response.json()["points"]["recent_events"]
    subject_event = next(event for event in events if event["context_type"] == "subject")
    assert subject_event["staff_display_name"] == world["admin"].name
    assert subject_event["class_section_name"] == world["section"].name
    assert subject_event["subject_name"] == "English" and subject_event["subject_code"] == "ENG"
    duty_event = next(event for event in events if event["context_type"] == "duty")
    assert duty_event["duty_context"] == "break" and duty_event["class_section_name"] is None
    for event in events:
        for forbidden in ("actor_user_id", "staff_id", "email", "subject_group_id", "subject_id", "class_section_id", "token", "hash", "storage_key", "path"):
            assert forbidden not in event


def test_models_store_only_hashed_tokens_and_have_scope_indexes(db):
    assert "token" not in {column.name for column in FhhLinkInvite.__table__.columns}
    assert "link_token" not in {column.name for column in FhhLink.__table__.columns}
    assert FhhLinkInvite.__table__.c.token_hash.unique is True
    assert FhhLink.__table__.c.link_token_hash.unique is True
    index_names = {index.name for index in FhhLinkInvite.__table__.indexes | FhhLink.__table__.indexes}
    assert "ix_fhh_link_invites_school_student" in index_names
    assert "ix_fhh_links_school_student_status" in index_names


def test_protected_integration_media_access_log_filter_redacts_route_identifiers():
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        (
            "client",
            "GET",
            "/api/integrations/fhh/links/123/updates/456/photos/789/view",
            "1.1",
            200,
        ),
        None,
    )
    assert protected_media_access_log_filter.filter(record)
    rendered = record.getMessage()
    assert "/api/integrations/fhh/links/<redacted>/<protected-media>" in rendered
    for protected_identifier in ("123", "456", "789"):
        assert protected_identifier not in rendered

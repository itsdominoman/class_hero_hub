import os
from contextlib import contextmanager

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database, mailer
from app.database import Base, get_db
from app.main import app
from app.models_school import (
    Import,
    ImportRow,
    MagicLoginToken,
    Membership,
    School,
    StaffAssignment,
    StaffInvite,
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


@contextmanager
def count_queries():
    counter = {"n": 0}

    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1

    event.listen(engine, "before_cursor_execute", _before_cursor_execute)
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", _before_cursor_execute)


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
def teacher_import_world(db):
    alpha_admin = create_user(db, "alpha-admin@example.com", "Alpha Admin")
    alpha_teacher = create_user(db, "alpha-teacher@example.com", "Alpha Teacher")
    no_role = create_user(db, "no-role@example.com", "No Role")
    beta_admin = create_user(db, "beta-admin@example.com", "Beta Admin")
    beta_teacher = create_user(db, "beta-teacher@example.com", "Beta Teacher")
    platform_only = create_user(db, "platform-only@example.com", "Platform Only")

    alpha = School(name="Alpha Academy", slug="alpha", status="active")
    beta = School(name="Beta School", slug="beta", status="active")
    db.add_all([alpha, beta])
    db.flush()

    db.add_all(
        [
            Membership(school_id=alpha.id, user_id=alpha_admin.id, role="school_admin"),
            Membership(school_id=alpha.id, user_id=alpha_teacher.id, role="teacher"),
            Membership(school_id=beta.id, user_id=beta_admin.id, role="school_admin"),
            Membership(school_id=beta.id, user_id=beta_teacher.id, role="teacher"),
        ]
    )
    db.commit()

    return {
        "alpha": alpha,
        "beta": beta,
        "alpha_admin": alpha_admin,
        "alpha_teacher": alpha_teacher,
        "no_role": no_role,
        "beta_admin": beta_admin,
        "beta_teacher": beta_teacher,
        "platform_only": platform_only,
    }


CSV_HEADER = "email,first_name,last_name,name_ar"


def csv_row(email="", first_name="", last_name="", name_ar="") -> str:
    return ",".join([email, first_name, last_name, name_ar])


def csv_bytes(rows: list[str], header: str = CSV_HEADER, encoding: str = "utf-8-sig") -> bytes:
    text = "\n".join([header, *rows]) + "\n"
    return text.encode(encoding)


def upload(client, world, rows: list[str], *, header: str = CSV_HEADER, encoding: str = "utf-8-sig", filename: str = "teachers.csv"):
    content = csv_bytes(rows, header=header, encoding=encoding)
    return client.post(
        "/api/school/teachers/imports",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        files={"file": (filename, content, "text/csv")},
    )


def commit(client, world, import_id):
    return client.post(f"/api/school/teachers/imports/{import_id}/commit", headers=bearer(world["alpha_admin"].email, world["alpha"].id))


def row_for(payload, email):
    return next(row for row in payload["rows"] if row["email"] == email)


def test_template_download_has_expected_headers(client, teacher_import_world):
    world = teacher_import_world
    resp = client.get("/api/school/teachers/import-template", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    header_line = resp.text.strip().splitlines()[0]
    assert header_line.split(",") == CSV_HEADER.split(",")


def test_upload_parses_utf8_and_bom(client, teacher_import_world):
    world = teacher_import_world
    plain = upload(client, world, [csv_row(email="new1@example.com", first_name="Sam", last_name="Lee")], encoding="utf-8")
    assert plain.status_code == 201
    assert plain.json()["summary"]["create"] == 1

    bom = upload(client, world, [csv_row(email="new2@example.com", first_name="Nour", last_name="Hassan", name_ar="نور حسن")], encoding="utf-8-sig")
    assert bom.status_code == 201
    row = row_for(bom.json(), "new2@example.com")
    assert row["errors"] == []
    assert row["name_ar"] == "نور حسن"


def test_header_case_and_whitespace_insensitive(client, teacher_import_world):
    world = teacher_import_world
    mixed_header = "Email, First_Name ,Last_Name,Name_AR"
    resp = upload(client, world, [csv_row(email="new3@example.com", first_name="Ali", last_name="Khan")], header=mixed_header)
    assert resp.status_code == 201
    row = row_for(resp.json(), "new3@example.com")
    assert row["action"] == "create"
    assert row["first_name"] == "Ali"
    assert row["last_name"] == "Khan"


def test_required_field_errors(client, teacher_import_world):
    resp = upload(client, teacher_import_world, [csv_row()])
    row = resp.json()["rows"][0]
    assert row["action"] == "error"
    assert any("email is required" in msg for msg in row["errors"])
    assert any("first_name is required" in msg for msg in row["errors"])
    assert any("last_name is required" in msg for msg in row["errors"])


def test_invalid_email_error(client, teacher_import_world):
    resp = upload(client, teacher_import_world, [csv_row(email="not-an-email", first_name="Ali", last_name="Khan")])
    row = resp.json()["rows"][0]
    assert row["action"] == "error"
    assert any("valid email" in msg for msg in row["errors"])


def test_duplicate_email_in_file_errors(client, teacher_import_world):
    rows = [
        csv_row(email="dupe@example.com", first_name="Ali", last_name="Khan"),
        csv_row(email="DUPE@example.com", first_name="Sara", last_name="Khan"),
    ]
    resp = upload(client, teacher_import_world, rows)
    payload = resp.json()
    assert payload["summary"]["error"] == 2
    for row in payload["rows"]:
        assert row["action"] == "error"
        assert "Duplicate email in file" in row["errors"]


def test_existing_user_without_teacher_membership_becomes_teacher(client, teacher_import_world, db):
    world = teacher_import_world
    staged = upload(client, world, [csv_row(email=world["no_role"].email, first_name="No", last_name="Role")])
    row = row_for(staged.json(), world["no_role"].email)
    assert row["action"] == "create"

    committed = commit(client, world, staged.json()["id"])
    assert committed.status_code == 200
    assert committed.json()["summary"]["create"] == 1

    assert db.query(User).filter(User.email == world["no_role"].email).count() == 1
    membership = db.query(Membership).filter(
        Membership.school_id == world["alpha"].id, Membership.user_id == world["no_role"].id, Membership.role == "teacher"
    ).first()
    assert membership is not None
    assert membership.status == "active"


def test_existing_teacher_membership_resolves_to_skip_not_duplicate(client, teacher_import_world, db):
    world = teacher_import_world
    staged = upload(client, world, [csv_row(email=world["alpha_teacher"].email, first_name="Alpha", last_name="Teacher")])
    row = row_for(staged.json(), world["alpha_teacher"].email)
    assert row["action"] == "skip"

    committed = commit(client, world, staged.json()["id"])
    assert committed.status_code == 200
    memberships = db.query(Membership).filter(
        Membership.school_id == world["alpha"].id, Membership.user_id == world["alpha_teacher"].id, Membership.role == "teacher"
    ).all()
    assert len(memberships) == 1


def test_reimport_is_idempotent(client, teacher_import_world, db):
    world = teacher_import_world
    rows = [csv_row(email="idempotent@example.com", first_name="Ali", last_name="Khan")]
    first = upload(client, world, rows)
    commit(client, world, first.json()["id"])

    second = upload(client, world, rows)
    payload = second.json()
    assert payload["summary"]["skip"] == 1
    committed = commit(client, world, payload["id"])
    assert committed.status_code == 200

    users = db.query(User).filter(User.email == "idempotent@example.com").all()
    assert len(users) == 1
    memberships = db.query(Membership).filter(
        Membership.school_id == world["alpha"].id, Membership.user_id == users[0].id, Membership.role == "teacher"
    ).all()
    assert len(memberships) == 1


def test_existing_mixed_case_email_is_matched_case_insensitively(client, teacher_import_world, db):
    world = teacher_import_world
    # A historical row stored with mixed case (e.g. from a provider login
    # that didn't normalize) must still be matched by a lowercase CSV email,
    # not treated as a brand-new user.
    mixed_case_user = create_user(db, "Mixed.Case@Example.com", "Mixed Case")
    db.commit()

    staged = upload(client, world, [csv_row(email="mixed.case@example.com", first_name="Mixed", last_name="Case")])
    row = row_for(staged.json(), "mixed.case@example.com")
    assert row["action"] == "create"

    committed = commit(client, world, staged.json()["id"])
    assert committed.status_code == 200

    assert db.query(User).filter(User.email == "Mixed.Case@Example.com").count() == 1
    membership = db.query(Membership).filter(
        Membership.school_id == world["alpha"].id, Membership.user_id == mixed_case_user.id, Membership.role == "teacher"
    ).first()
    assert membership is not None


def test_previously_revoked_teacher_is_not_reactivated_by_import(client, teacher_import_world, db):
    world = teacher_import_world
    revoked_membership = db.query(Membership).filter(
        Membership.school_id == world["alpha"].id, Membership.user_id == world["alpha_teacher"].id, Membership.role == "teacher"
    ).first()
    revoked_membership.status = "revoked"
    db.commit()

    staged = upload(client, world, [csv_row(email=world["alpha_teacher"].email, first_name="Alpha", last_name="Teacher")])
    row = row_for(staged.json(), world["alpha_teacher"].email)
    assert row["action"] == "skip"
    assert any("previously removed" in warning for warning in row["warnings"])

    commit(client, world, staged.json()["id"])
    db.refresh(revoked_membership)
    assert revoked_membership.status == "revoked"


def test_cross_school_isolation(client, teacher_import_world, db):
    world = teacher_import_world
    # beta_teacher is already an active teacher at beta only; importing them
    # into alpha must create a separate, alpha-scoped membership, not skip.
    staged = upload(client, world, [csv_row(email=world["beta_teacher"].email, first_name="Beta", last_name="Teacher")])
    row = row_for(staged.json(), world["beta_teacher"].email)
    assert row["action"] == "create"
    commit(client, world, staged.json()["id"])

    users = db.query(User).filter(User.email == world["beta_teacher"].email).all()
    assert len(users) == 1
    memberships = db.query(Membership).filter(Membership.user_id == users[0].id, Membership.role == "teacher").all()
    assert {m.school_id for m in memberships} == {world["alpha"].id, world["beta"].id}


def test_commit_applies_valid_rows_and_leaves_error_rows_unapplied(client, teacher_import_world, db):
    world = teacher_import_world
    rows = [
        csv_row(email="good@example.com", first_name="Ali", last_name="Khan"),
        csv_row(email="", first_name="Bad"),
    ]
    staged = upload(client, world, rows)
    payload = staged.json()
    assert payload["summary"]["create"] == 1
    assert payload["summary"]["error"] == 1

    committed = commit(client, world, payload["id"])
    body = committed.json()
    good_row = row_for(body, "good@example.com")
    assert good_row["applied_entity_id"] is not None
    bad_row = next(row for row in body["rows"] if row["action"] == "error")
    assert bad_row["applied_entity_id"] is None

    assert db.query(User).filter(User.email == "good@example.com").count() == 1


def test_cannot_commit_already_committed_import(client, teacher_import_world):
    world = teacher_import_world
    staged = upload(client, world, [csv_row(email="once@example.com", first_name="Ali", last_name="Khan")])
    import_id = staged.json()["id"]
    assert commit(client, world, import_id).status_code == 200
    assert commit(client, world, import_id).status_code == 409


def test_discard_prevents_commit(client, teacher_import_world, db):
    world = teacher_import_world
    staged = upload(client, world, [csv_row(email="discard@example.com", first_name="Ali", last_name="Khan")])
    import_id = staged.json()["id"]
    discarded = client.post(f"/api/school/teachers/imports/{import_id}/discard", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert discarded.status_code == 200
    assert discarded.json()["status"] == "discarded"
    assert commit(client, world, import_id).status_code == 409
    assert db.query(User).filter(User.email == "discard@example.com").count() == 0


def test_wrong_role_is_blocked(client, teacher_import_world):
    world = teacher_import_world
    resp = client.post(
        "/api/school/teachers/imports",
        headers=bearer(world["alpha_teacher"].email, world["alpha"].id),
        files={"file": ("teachers.csv", csv_bytes([csv_row(email="x@example.com", first_name="Ali", last_name="Khan")]), "text/csv")},
    )
    assert resp.status_code == 403


def test_wrong_school_is_blocked(client, teacher_import_world):
    world = teacher_import_world
    resp = client.post(
        "/api/school/teachers/imports",
        headers=bearer(world["beta_admin"].email, world["alpha"].id),
        files={"file": ("teachers.csv", csv_bytes([csv_row(email="x@example.com", first_name="Ali", last_name="Khan")]), "text/csv")},
    )
    assert resp.status_code == 403


def test_platform_admin_without_school_membership_is_blocked(client, teacher_import_world):
    world = teacher_import_world
    resp = client.post(
        "/api/school/teachers/imports",
        headers=bearer(world["platform_only"].email, world["alpha"].id),
        files={"file": ("teachers.csv", csv_bytes([csv_row(email="x@example.com", first_name="Ali", last_name="Khan")]), "text/csv")},
    )
    assert resp.status_code == 403


def test_import_creates_no_teacher_assignments(client, teacher_import_world, db):
    world = teacher_import_world
    staged = upload(
        client, world,
        [
            csv_row(email="assign1@example.com", first_name="Ali", last_name="Khan"),
            csv_row(email=world["alpha_teacher"].email, first_name="Alpha", last_name="Teacher"),
        ],
    )
    commit(client, world, staged.json()["id"])
    assert db.query(StaffAssignment).count() == 0


def test_import_sends_zero_outbound_communication(client, teacher_import_world, db, monkeypatch):
    world = teacher_import_world
    invite_calls = []
    magic_calls = []
    monkeypatch.setattr(mailer, "send_staff_invite", lambda email: invite_calls.append(email))
    monkeypatch.setattr(mailer, "send_magic_login", lambda email: magic_calls.append(email))

    staged = upload(client, world, [csv_row(email="quiet@example.com", first_name="Ali", last_name="Khan")])
    commit(client, world, staged.json()["id"])

    assert invite_calls == []
    assert magic_calls == []
    assert db.query(StaffInvite).count() == 0
    assert db.query(MagicLoginToken).count() == 0


def test_import_query_shape_does_not_scale_with_row_count(client, teacher_import_world):
    world = teacher_import_world
    small_rows = [csv_row(email=f"small{i}@example.com", first_name=f"First{i}", last_name=f"Last{i}") for i in range(5)]
    large_rows = [csv_row(email=f"large{i}@example.com", first_name=f"First{i}", last_name=f"Last{i}") for i in range(40)]
    extra_rows = len(large_rows) - len(small_rows)

    with count_queries() as small_counter:
        small = upload(client, world, small_rows)
    assert small.status_code == 201

    with count_queries() as large_counter:
        large = upload(client, world, large_rows)
    assert large.status_code == 201

    assert large_counter["n"] - small_counter["n"] < extra_rows * 3 + 15

    with count_queries() as small_commit_counter:
        small_committed = commit(client, world, small.json()["id"])
    assert small_committed.status_code == 200

    with count_queries() as large_commit_counter:
        large_committed = commit(client, world, large.json()["id"])
    assert large_committed.status_code == 200

    assert large_commit_counter["n"] - small_commit_counter["n"] < extra_rows * 5

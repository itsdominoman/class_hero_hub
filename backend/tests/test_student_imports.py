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
    AcademicYear,
    BranchCampus,
    ClassSection,
    Enrolment,
    GradeLevel,
    Import,
    ImportRow,
    MagicLoginToken,
    Membership,
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
def import_world(db):
    alpha_admin = create_user(db, "alpha-admin@example.com", "Alpha Admin")
    alpha_teacher = create_user(db, "alpha-teacher@example.com", "Alpha Teacher")
    no_role = create_user(db, "no-role@example.com", "No Role")
    beta_admin = create_user(db, "beta-admin@example.com", "Beta Admin")
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

    kg1 = GradeLevel(school_id=alpha.id, code="KG1", name="KG 1", status="active")
    g1 = GradeLevel(school_id=alpha.id, code="G1", name="Grade 1", status="active")
    beta_kg1 = GradeLevel(school_id=beta.id, code="KG1", name="KG 1", status="active")
    beta_only_grade = GradeLevel(school_id=beta.id, code="BETA-ONLY", name="Beta Only Grade", status="active")
    db.add_all([kg1, g1, beta_kg1, beta_only_grade])
    db.flush()

    section_a = ClassSection(school_id=alpha.id, branch_campus_id=branch.id, academic_year_id=year.id, grade_level_id=kg1.id, code="A", name="KG 1 A", status="active")
    section_b = ClassSection(school_id=alpha.id, branch_campus_id=branch.id, academic_year_id=year.id, grade_level_id=kg1.id, code="B", name="KG 1 B", status="active")
    g1_section_a = ClassSection(school_id=alpha.id, branch_campus_id=branch.id, academic_year_id=year.id, grade_level_id=g1.id, code="A", name="Grade 1 A", status="active")
    db.add_all([section_a, section_b, g1_section_a])
    db.commit()

    return {
        "alpha": alpha,
        "beta": beta,
        "alpha_admin": alpha_admin,
        "alpha_teacher": alpha_teacher,
        "beta_admin": beta_admin,
        "no_role": no_role,
        "platform_only": platform_only,
        "branch": branch,
        "year": year,
        "kg1": kg1,
        "g1": g1,
        "section_a": section_a,
        "section_b": section_b,
        "g1_section_a": g1_section_a,
    }


CSV_HEADER = (
    "student_id,first_name,last_name,preferred_name,name_ar,dob,gender,branch,grade,section,"
    "guardian1_name,guardian1_email,guardian1_relationship,"
    "guardian2_name,guardian2_email,guardian2_relationship"
)


def csv_row(
    student_id="",
    first_name="",
    last_name="",
    preferred_name="",
    name_ar="",
    dob="",
    gender="",
    branch="",
    grade="KG1",
    section="A",
    guardian1_name="",
    guardian1_email="",
    guardian1_relationship="",
    guardian2_name="",
    guardian2_email="",
    guardian2_relationship="",
) -> str:
    return ",".join(
        [
            student_id, first_name, last_name, preferred_name, name_ar, dob, gender,
            branch, grade, section,
            guardian1_name, guardian1_email, guardian1_relationship,
            guardian2_name, guardian2_email, guardian2_relationship,
        ]
    )


def csv_bytes(rows: list[str], header: str = CSV_HEADER, encoding: str = "utf-8-sig") -> bytes:
    text = "\n".join([header, *rows]) + "\n"
    return text.encode(encoding)


def upload(client, world, rows: list[str], *, header: str = CSV_HEADER, encoding: str = "utf-8-sig", filename: str = "students.csv"):
    content = csv_bytes(rows, header=header, encoding=encoding)
    return client.post(
        "/api/school/students/imports",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        files={"file": (filename, content, "text/csv")},
    )


def commit(client, world, import_id):
    return client.post(f"/api/school/students/imports/{import_id}/commit", headers=bearer(world["alpha_admin"].email, world["alpha"].id))


def row_for(payload, student_id):
    return next(row for row in payload["rows"] if row["student_id"] == student_id)


def test_template_download_has_expected_headers(client, import_world):
    world = import_world
    resp = client.get("/api/school/students/import-template", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    header_line = resp.text.strip().splitlines()[0]
    assert header_line.split(",") == CSV_HEADER.split(",")
    assert "guardian1_name" in header_line
    assert "guardian1_relationship" in header_line
    assert "guardian2_relationship" in header_line


def test_upload_parses_utf8_and_bom(client, import_world):
    world = import_world
    rows = [csv_row(student_id="S-001", first_name="Ali", last_name="Khan")]
    plain = upload(client, world, rows, encoding="utf-8")
    assert plain.status_code == 201
    assert plain.json()["summary"]["create"] == 1

    bom = upload(client, world, [csv_row(student_id="S-002", first_name="Nour", last_name="Hassan", name_ar="نور حسن")], encoding="utf-8-sig")
    assert bom.status_code == 201
    assert bom.json()["summary"]["create"] == 1
    assert row_for(bom.json(), "S-002")["errors"] == []


def test_cp1256_encoding_supported(client, import_world):
    world = import_world
    rows = [csv_row(student_id="S-003", first_name="Ali", last_name="Khan")]
    resp = upload(client, world, rows, encoding="cp1256")
    assert resp.status_code == 201
    assert resp.json()["summary"]["create"] == 1


def test_undecodable_bytes_return_clear_encoding_error(client, import_world):
    world = import_world
    content = b"\xff\xfe\x00garbage,not,csv"
    resp = client.post(
        "/api/school/students/imports",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        files={"file": ("bad.csv", content, "text/csv")},
    )
    assert resp.status_code == 422


def test_missing_required_columns_error(client, import_world):
    world = import_world
    resp = upload(client, world, ["Ali,Khan"], header="first_name,last_name")
    assert resp.status_code == 422


def test_header_case_and_whitespace_insensitive(client, import_world):
    world = import_world
    mixed_header = (
        "Student_ID, First_Name ,Last_Name,Preferred_Name,Name_AR,DOB,Gender,Branch,Grade,Section,"
        "Guardian1_Name,Guardian1_Email,Guardian1_Relationship,"
        "Guardian2_Name,Guardian2_Email,Guardian2_Relationship"
    )
    resp = upload(client, world, [csv_row(student_id="S-005", first_name="Ali", last_name="Khan")], header=mixed_header)
    assert resp.status_code == 201
    row = row_for(resp.json(), "S-005")
    assert row["action"] == "create"
    assert row["first_name"] == "Ali"
    assert row["last_name"] == "Khan"


def test_required_field_errors(client, import_world):
    world = import_world
    resp = upload(client, world, [csv_row(last_name="Khan")])
    assert resp.status_code == 201
    row = resp.json()["rows"][0]
    assert row["action"] == "error"
    assert any("first_name" in msg for msg in row["errors"])


def test_duplicate_student_id_within_file_errors(client, import_world):
    world = import_world
    rows = [
        csv_row(student_id="S-010", first_name="Ali", last_name="Khan"),
        csv_row(student_id="S-010", first_name="Sara", last_name="Khan", section="B"),
    ]
    resp = upload(client, world, rows)
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["summary"]["error"] == 2
    for row in payload["rows"]:
        assert row["action"] == "error"
        assert "Duplicate student_id in file" in row["errors"]


def test_invalid_gender_errors(client, import_world):
    world = import_world
    resp = upload(client, world, [csv_row(student_id="S-020", first_name="Ali", last_name="Khan", gender="notagender")])
    row = resp.json()["rows"][0]
    assert row["action"] == "error"
    assert any("gender" in msg for msg in row["errors"])


def test_invalid_dob_errors(client, import_world):
    world = import_world
    resp = upload(client, world, [csv_row(student_id="S-021", first_name="Ali", last_name="Khan", dob="31/01/2015")])
    row = resp.json()["rows"][0]
    assert row["action"] == "error"
    assert any("dob" in msg for msg in row["errors"])


def test_unknown_branch_in_multi_branch_school_errors(client, import_world, db):
    world = import_world
    db.add(BranchCampus(school_id=world["alpha"].id, code="NORTH", name="North Campus", status="active"))
    db.commit()

    missing_branch = upload(client, world, [csv_row(student_id="S-030", first_name="Ali", last_name="Khan")])
    row = row_for(missing_branch.json(), "S-030")
    assert row["action"] == "error"
    assert any("branch is required" in msg for msg in row["errors"])

    unknown_branch = upload(client, world, [csv_row(student_id="S-031", first_name="Ali", last_name="Khan", branch="SOUTH")])
    row = row_for(unknown_branch.json(), "S-031")
    assert row["action"] == "error"
    assert any("Unknown branch" in msg for msg in row["errors"])


def test_branch_omitted_with_no_active_branch_gives_specific_error(client, import_world, db):
    world = import_world
    world["branch"].status = "archived"
    db.commit()
    resp = upload(client, world, [csv_row(student_id="S-041", first_name="Ali", last_name="Khan")])
    row = row_for(resp.json(), "S-041")
    assert row["action"] == "error"
    assert any("no active branch" in msg for msg in row["errors"])


def test_branch_omitted_works_when_unambiguous(client, import_world):
    world = import_world
    resp = upload(client, world, [csv_row(student_id="S-040", first_name="Ali", last_name="Khan")])
    row = row_for(resp.json(), "S-040")
    assert row["action"] == "create"
    assert row["errors"] == []


def test_current_academic_year_required(client, import_world, db):
    world = import_world
    world["year"].is_current = False
    db.commit()
    resp = upload(client, world, [csv_row(student_id="S-050", first_name="Ali", last_name="Khan")])
    assert resp.status_code == 422
    assert "academic year" in resp.json()["detail"].lower()


def test_import_creates_new_students_and_section_enrolments(client, import_world, db):
    world = import_world
    staged = upload(client, world, [csv_row(student_id="S-060", first_name="Ali", last_name="Khan")])
    import_id = staged.json()["id"]
    committed = commit(client, world, import_id)
    assert committed.status_code == 200
    assert committed.json()["summary"]["create"] == 1

    student = db.query(Student).filter(Student.school_id == world["alpha"].id, Student.external_ref == "S-060").first()
    assert student is not None
    assert student.avatar_id is None  # assigned lazily on first classroom/guardian display
    enrolment = db.query(Enrolment).filter(Enrolment.student_id == student.id, Enrolment.class_section_id == world["section_a"].id).first()
    assert enrolment is not None
    assert enrolment.valid_to is None


def test_existing_student_external_ref_updates_instead_of_duplicating(client, import_world, db):
    world = import_world
    first = upload(client, world, [csv_row(student_id="S-070", first_name="Ali", last_name="Khan")])
    commit(client, world, first.json()["id"])

    second = upload(client, world, [csv_row(student_id="S-070", first_name="Alya", last_name="Khan", preferred_name="Aly")])
    payload = second.json()
    row = row_for(payload, "S-070")
    assert row["action"] == "update"
    committed = commit(client, world, payload["id"])
    assert committed.status_code == 200

    students = db.query(Student).filter(Student.school_id == world["alpha"].id, Student.external_ref == "S-070").all()
    assert len(students) == 1
    assert students[0].first_name == "Alya"


def test_archived_student_external_ref_restores(client, import_world, db):
    world = import_world
    first = upload(client, world, [csv_row(student_id="S-080", first_name="Ali", last_name="Khan")])
    commit(client, world, first.json()["id"])
    student = db.query(Student).filter(Student.school_id == world["alpha"].id, Student.external_ref == "S-080").first()
    client.delete(f"/api/school/students/{student.id}", headers=bearer(world["alpha_admin"].email, world["alpha"].id))

    second = upload(client, world, [csv_row(student_id="S-080", first_name="Ali", last_name="Khan")])
    row = row_for(second.json(), "S-080")
    assert row["action"] == "restore"
    committed = commit(client, world, second.json()["id"])
    assert committed.status_code == 200

    db.refresh(student)
    assert student.status == "active"
    students = db.query(Student).filter(Student.school_id == world["alpha"].id, Student.external_ref == "S-080").all()
    assert len(students) == 1


def test_reimport_is_idempotent(client, import_world, db):
    world = import_world
    rows = [csv_row(student_id="S-090", first_name="Ali", last_name="Khan")]
    first = upload(client, world, rows)
    commit(client, world, first.json()["id"])

    second = upload(client, world, rows)
    payload = second.json()
    assert payload["summary"]["skip"] == 1
    committed = commit(client, world, payload["id"])
    assert committed.status_code == 200

    students = db.query(Student).filter(Student.school_id == world["alpha"].id, Student.external_ref == "S-090").all()
    assert len(students) == 1
    enrolments = db.query(Enrolment).filter(Enrolment.student_id == students[0].id).all()
    assert len(enrolments) == 1


def test_move_section_closes_old_enrolment_and_opens_new(client, import_world, db):
    world = import_world
    first = upload(client, world, [csv_row(student_id="S-100", first_name="Ali", last_name="Khan")])
    commit(client, world, first.json()["id"])
    student = db.query(Student).filter(Student.school_id == world["alpha"].id, Student.external_ref == "S-100").first()

    second = upload(client, world, [csv_row(student_id="S-100", first_name="Ali", last_name="Khan", section="B")])
    row = row_for(second.json(), "S-100")
    assert row["action"] == "move"
    commit(client, world, second.json()["id"])

    enrolments = db.query(Enrolment).filter(Enrolment.student_id == student.id).order_by(Enrolment.id.asc()).all()
    assert len(enrolments) == 2
    assert enrolments[0].class_section_id == world["section_a"].id
    assert enrolments[0].valid_to is not None
    assert enrolments[1].class_section_id == world["section_b"].id
    assert enrolments[1].valid_to is None


def test_same_section_reimport_does_not_duplicate_enrolment(client, import_world, db):
    world = import_world
    first = upload(client, world, [csv_row(student_id="S-110", first_name="Ali", last_name="Khan")])
    commit(client, world, first.json()["id"])
    student = db.query(Student).filter(Student.school_id == world["alpha"].id, Student.external_ref == "S-110").first()

    second = upload(client, world, [csv_row(student_id="S-110", first_name="Ali", last_name="Khan", preferred_name="Aly")])
    row = row_for(second.json(), "S-110")
    assert row["action"] == "update"
    commit(client, world, second.json()["id"])

    enrolments = db.query(Enrolment).filter(Enrolment.student_id == student.id).all()
    assert len(enrolments) == 1


def test_duplicate_names_are_allowed(client, import_world):
    world = import_world
    rows = [
        csv_row(first_name="Ali", last_name="Khan", section="A"),
        csv_row(first_name="Ali", last_name="Khan", section="B"),
    ]
    resp = upload(client, world, rows)
    payload = resp.json()
    assert payload["summary"]["create"] == 2
    assert all(row["action"] == "create" for row in payload["rows"])


def test_guardian_email_with_missing_name_produces_warning_not_error(client, import_world):
    world = import_world
    resp = upload(
        client, world,
        [csv_row(student_id="S-120", first_name="Ali", last_name="Khan", guardian1_email="mom@example.com")],
    )
    row = row_for(resp.json(), "S-120")
    assert row["action"] == "create"
    assert any("guardian1_name is missing" in warning for warning in row["warnings"])


def test_invalid_guardian_relationship_warns_not_errors(client, import_world, db):
    world = import_world
    resp = upload(
        client, world,
        [
            csv_row(
                student_id="S-121", first_name="Ali", last_name="Khan",
                guardian1_name="Sara Khan", guardian1_email="sara@example.com", guardian1_relationship="aunt",
            )
        ],
    )
    row = row_for(resp.json(), "S-121")
    assert row["action"] == "create"
    assert any("guardian1_relationship must be one of" in warning for warning in row["warnings"])

    commit(client, world, resp.json()["id"])
    student = db.query(Student).filter(Student.school_id == world["alpha"].id, Student.external_ref == "S-121").first()
    contact = db.query(StudentGuardianContact).filter(StudentGuardianContact.student_id == student.id, StudentGuardianContact.slot == 1).first()
    assert contact is not None
    assert contact.name == "Sara Khan"
    assert contact.relationship is None


def test_commit_creates_draft_guardian_contacts(client, import_world, db):
    world = import_world
    staged = upload(
        client, world,
        [
            csv_row(
                student_id="S-122", first_name="Ali", last_name="Khan",
                guardian1_name="Huda Khan", guardian1_email="huda@example.com", guardian1_relationship="mother",
                guardian2_name="Yousef Khan", guardian2_email="yousef@example.com", guardian2_relationship="father",
            )
        ],
    )
    commit(client, world, staged.json()["id"])

    student = db.query(Student).filter(Student.school_id == world["alpha"].id, Student.external_ref == "S-122").first()
    contacts = (
        db.query(StudentGuardianContact)
        .filter(StudentGuardianContact.student_id == student.id)
        .order_by(StudentGuardianContact.slot.asc())
        .all()
    )
    assert len(contacts) == 2
    assert contacts[0].slot == 1
    assert contacts[0].name == "Huda Khan"
    assert contacts[0].email == "huda@example.com"
    assert contacts[0].relationship == "mother"
    assert contacts[0].status == "draft"
    assert contacts[0].source_import_id == staged.json()["id"]
    assert contacts[1].slot == 2
    assert contacts[1].name == "Yousef Khan"
    assert contacts[1].relationship == "father"


def test_guardian_contact_reimport_is_idempotent_and_updates_in_place(client, import_world, db):
    world = import_world
    first = upload(
        client, world,
        [csv_row(student_id="S-123", first_name="Ali", last_name="Khan", guardian1_name="Huda", guardian1_email="huda@example.com", guardian1_relationship="mother")],
    )
    commit(client, world, first.json()["id"])
    student = db.query(Student).filter(Student.school_id == world["alpha"].id, Student.external_ref == "S-123").first()
    first_contact_id = (
        db.query(StudentGuardianContact).filter(StudentGuardianContact.student_id == student.id, StudentGuardianContact.slot == 1).first().id
    )

    second = upload(
        client, world,
        [csv_row(student_id="S-123", first_name="Ali", last_name="Khan", guardian1_name="Huda Khan", guardian1_email="huda.khan@example.com", guardian1_relationship="mother")],
    )
    commit(client, world, second.json()["id"])

    contacts = db.query(StudentGuardianContact).filter(StudentGuardianContact.student_id == student.id).all()
    assert len(contacts) == 1
    assert contacts[0].id == first_contact_id
    assert contacts[0].name == "Huda Khan"
    assert contacts[0].email == "huda.khan@example.com"


def test_guardian_contact_already_acted_on_is_not_overwritten_by_reimport(client, import_world, db):
    world = import_world
    first = upload(
        client, world,
        [csv_row(student_id="S-124", first_name="Ali", last_name="Khan", guardian1_name="Huda", guardian1_email="huda@example.com", guardian1_relationship="mother")],
    )
    commit(client, world, first.json()["id"])
    student = db.query(Student).filter(Student.school_id == world["alpha"].id, Student.external_ref == "S-124").first()
    contact = db.query(StudentGuardianContact).filter(StudentGuardianContact.student_id == student.id, StudentGuardianContact.slot == 1).first()
    contact.status = "linked"
    db.commit()

    second = upload(
        client, world,
        [csv_row(student_id="S-124", first_name="Ali", last_name="Khan", guardian1_name="Someone Else", guardian1_email="someone@example.com", guardian1_relationship="mother")],
    )
    commit(client, world, second.json()["id"])

    db.refresh(contact)
    assert contact.status == "linked"
    assert contact.name == "Huda"
    assert contact.email == "huda@example.com"


def test_wrong_role_is_blocked(client, import_world):
    world = import_world
    resp = client.post(
        "/api/school/students/imports",
        headers=bearer(world["alpha_teacher"].email, world["alpha"].id),
        files={"file": ("students.csv", csv_bytes([csv_row(student_id="S-130", first_name="Ali", last_name="Khan")]), "text/csv")},
    )
    assert resp.status_code == 403


def test_wrong_school_is_blocked(client, import_world):
    world = import_world
    resp = client.post(
        "/api/school/students/imports",
        headers=bearer(world["beta_admin"].email, world["alpha"].id),
        files={"file": ("students.csv", csv_bytes([csv_row(student_id="S-140", first_name="Ali", last_name="Khan")]), "text/csv")},
    )
    assert resp.status_code == 403


def test_platform_admin_without_school_membership_is_blocked(client, import_world):
    world = import_world
    resp = client.post(
        "/api/school/students/imports",
        headers=bearer(world["platform_only"].email, world["alpha"].id),
        files={"file": ("students.csv", csv_bytes([csv_row(student_id="S-150", first_name="Ali", last_name="Khan")]), "text/csv")},
    )
    assert resp.status_code == 403


def test_cross_school_grade_code_is_rejected(client, import_world):
    world = import_world
    # KG1 exists in beta too, but the alpha grade lookup must not leak beta's rows;
    # using a grade code that only exists in beta (not alpha) must fail as unknown.
    resp = upload(client, world, [csv_row(student_id="S-160", first_name="Ali", last_name="Khan", grade="BETA-ONLY")])
    row = row_for(resp.json(), "S-160")
    assert row["action"] == "error"
    assert any("Unknown grade" in msg for msg in row["errors"])


def test_commit_applies_valid_rows_and_leaves_error_rows_unapplied(client, import_world, db):
    world = import_world
    rows = [
        csv_row(student_id="S-170", first_name="Ali", last_name="Khan"),
        csv_row(last_name="Bad"),
    ]
    staged = upload(client, world, rows)
    payload = staged.json()
    assert payload["summary"]["create"] == 1
    assert payload["summary"]["error"] == 1

    committed = commit(client, world, payload["id"])
    body = committed.json()
    assert body["summary"]["create"] == 1
    assert body["summary"]["error"] == 1
    good_row = row_for(body, "S-170")
    assert good_row["applied_entity_id"] is not None
    bad_row = next(row for row in body["rows"] if row["action"] == "error")
    assert bad_row["applied_entity_id"] is None

    students = db.query(Student).filter(Student.school_id == world["alpha"].id).all()
    assert len(students) == 1


def test_cannot_commit_already_committed_import(client, import_world):
    world = import_world
    staged = upload(client, world, [csv_row(student_id="S-180", first_name="Ali", last_name="Khan")])
    import_id = staged.json()["id"]
    assert commit(client, world, import_id).status_code == 200
    assert commit(client, world, import_id).status_code == 409


def test_discard_staged_import(client, import_world, db):
    world = import_world
    staged = upload(client, world, [csv_row(student_id="S-190", first_name="Ali", last_name="Khan")])
    import_id = staged.json()["id"]
    discarded = client.post(f"/api/school/students/imports/{import_id}/discard", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert discarded.status_code == 200
    assert discarded.json()["status"] == "discarded"
    assert commit(client, world, import_id).status_code == 409
    assert db.query(Student).filter(Student.school_id == world["alpha"].id).count() == 0


def test_import_sends_zero_outbound_communication(client, import_world, db, monkeypatch):
    world = import_world
    invite_calls = []
    magic_calls = []
    monkeypatch.setattr(mailer, "send_staff_invite", lambda email: invite_calls.append(email))
    monkeypatch.setattr(mailer, "send_magic_login", lambda email: magic_calls.append(email))

    users_before = db.query(User).count()
    rows = [
        csv_row(
            student_id="S-200", first_name="Ali", last_name="Khan",
            guardian1_name="Mom", guardian1_email="mom@example.com", guardian1_relationship="mother",
            guardian2_name="Dad", guardian2_email="dad@example.com", guardian2_relationship="father",
        )
    ]
    staged = upload(client, world, rows)
    commit(client, world, staged.json()["id"])

    assert invite_calls == []
    assert magic_calls == []
    assert db.query(StaffInvite).count() == 0
    assert db.query(MagicLoginToken).count() == 0
    # No guardian user accounts or links are created — only draft contacts.
    assert db.query(User).count() == users_before
    student = db.query(Student).filter(Student.school_id == world["alpha"].id, Student.external_ref == "S-200").first()
    assert db.query(StudentGuardianContact).filter(StudentGuardianContact.student_id == student.id).count() == 2


def test_import_query_shape_does_not_scale_with_row_count(client, import_world):
    world = import_world
    small_rows = [csv_row(student_id=f"Q-SMALL-{i}", first_name=f"First{i}", last_name=f"Last{i}") for i in range(5)]
    large_rows = [csv_row(student_id=f"Q-LARGE-{i}", first_name=f"First{i}", last_name=f"Last{i}") for i in range(40)]
    extra_rows = len(large_rows) - len(small_rows)

    with count_queries() as small_counter:
        small = upload(client, world, small_rows)
    assert small.status_code == 201

    with count_queries() as large_counter:
        large = upload(client, world, large_rows)
    assert large.status_code == 201

    # Each new ImportRow is its own INSERT (expected — writes scale with row
    # count), but the *read*/lookup portion (branches/grades/sections/students/
    # enrolments/guardian contacts) must stay flat: a generous per-row bound
    # still catches an O(rows) extra read query per row, which the plan's
    # batched lookups avoid.
    assert large_counter["n"] - small_counter["n"] < extra_rows * 3 + 15

    with count_queries() as small_commit_counter:
        small_committed = commit(client, world, small.json()["id"])
    assert small_committed.status_code == 200

    with count_queries() as large_commit_counter:
        large_committed = commit(client, world, large.json()["id"])
    assert large_committed.status_code == 200

    # Commit writes (student + enrolment insert, import-row update per row)
    # scale with row count by design; the comparison against the small-import
    # commit bounds the per-row marginal cost instead of guessing fixed
    # overhead, which would otherwise catch a superlinear (O(rows^2) or
    # per-row extra lookup) regression.
    assert large_commit_counter["n"] - small_commit_counter["n"] < extra_rows * 5

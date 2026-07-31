import csv
import io
import os
from contextlib import contextmanager
from datetime import date

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database, mailer
from app.admission import has_active_entitlement
from app.database import Base, get_db
from app.imports_service import parse_csv_rows
from app.main import app
from app.models_school import (
    AcademicYear,
    AuditLog,
    BranchCampus,
    ClassSection,
    Enrolment,
    GradeLevel,
    GuardianLink,
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

    year = AcademicYear(
        school_id=alpha.id,
        code="2026",
        name="2026",
        status="active",
        is_current=True,
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30),
    )
    next_year = AcademicYear(
        school_id=alpha.id,
        code="2027",
        name="2027",
        status="active",
        is_current=False,
        start_date=date(2027, 7, 1),
        end_date=date(2028, 6, 30),
    )
    beta_year = AcademicYear(
        school_id=beta.id,
        code="2026",
        name="2026",
        status="active",
        is_current=True,
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30),
    )
    db.add_all([year, next_year, beta_year])
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
    next_kg1_section_a = ClassSection(school_id=alpha.id, branch_campus_id=branch.id, academic_year_id=next_year.id, grade_level_id=kg1.id, code="A", name="2027 KG 1 A", status="active")
    next_kg1_section_b = ClassSection(school_id=alpha.id, branch_campus_id=branch.id, academic_year_id=next_year.id, grade_level_id=kg1.id, code="B", name="2027 KG 1 B", status="active")
    next_g1_section_a = ClassSection(school_id=alpha.id, branch_campus_id=branch.id, academic_year_id=next_year.id, grade_level_id=g1.id, code="A", name="2027 Grade 1 A", status="active")
    db.add_all([section_a, section_b, g1_section_a, next_kg1_section_a, next_kg1_section_b, next_g1_section_a])
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
        "next_year": next_year,
        "beta_year": beta_year,
        "kg1": kg1,
        "g1": g1,
        "section_a": section_a,
        "section_b": section_b,
        "g1_section_a": g1_section_a,
        "next_kg1_section_a": next_kg1_section_a,
        "next_kg1_section_b": next_kg1_section_b,
        "next_g1_section_a": next_g1_section_a,
    }


CSV_HEADER = (
    "student_id,first_name,last_name,preferred_name,name_ar,dob,gender,branch,grade,section,student_status,"
    "guardian1_name,guardian1_id,guardian1_email,guardian1_phone,guardian1_relationship,"
    "guardian2_name,guardian2_id,guardian2_email,guardian2_phone,guardian2_relationship"
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
    student_status="",
    guardian1_name="",
    guardian1_id="",
    guardian1_email="",
    guardian1_phone="",
    guardian1_relationship="",
    guardian2_name="",
    guardian2_id="",
    guardian2_email="",
    guardian2_phone="",
    guardian2_relationship="",
) -> str:
    return ",".join(
        [
            student_id, first_name, last_name, preferred_name, name_ar, dob, gender,
            branch, grade, section,
            student_status,
            guardian1_name, guardian1_id, guardian1_email, guardian1_phone, guardian1_relationship,
            guardian2_name, guardian2_id, guardian2_email, guardian2_phone, guardian2_relationship,
        ]
    )


def csv_bytes(rows: list[str], header: str = CSV_HEADER, encoding: str = "utf-8-sig") -> bytes:
    text = "\n".join([header, *rows]) + "\n"
    return text.encode(encoding)


def upload(
    client,
    world,
    rows: list[str],
    *,
    header: str = CSV_HEADER,
    encoding: str = "utf-8-sig",
    filename: str = "students.csv",
    mode: str = "normal",
    academic_year_id: int | None = None,
    effective_date: str | None = None,
):
    content = csv_bytes(rows, header=header, encoding=encoding)
    data = {"mode": mode}
    if academic_year_id is not None:
        data["academic_year_id"] = str(academic_year_id)
    if effective_date is not None:
        data["effective_date"] = effective_date
    return client.post(
        "/api/school/students/imports",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        files={"file": (filename, content, "text/csv")},
        data=data,
    )


def commit(client, world, import_id):
    return client.post(f"/api/school/students/imports/{import_id}/commit", headers=bearer(world["alpha_admin"].email, world["alpha"].id))


def annual_upload(client, world, rows: list[str], *, effective_date: str | None = None):
    return upload(
        client,
        world,
        rows,
        mode="annual",
        academic_year_id=world["next_year"].id,
        effective_date=effective_date,
    )


def row_for(payload, student_id):
    return next(row for row in payload["rows"] if row["student_id"] == student_id)


def csv_download_rows(response):
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    return list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))


def test_template_download_has_expected_headers(client, import_world):
    world = import_world
    resp = client.get("/api/school/students/import-template", headers=bearer(world["alpha_admin"].email, world["alpha"].id))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    header_line = resp.text.strip().splitlines()[0]
    assert header_line.split(",") == CSV_HEADER.split(",")
    assert "guardian1_name" in header_line
    assert "guardian1_phone" in header_line
    assert "guardian2_phone" in header_line
    assert "student_status" in header_line
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


def test_formula_safe_export_cells_are_reimportable():
    rows = parse_csv_rows(
        "student_id,guardian1_phone,first_name\n'=MIS-1,'+96812345678,Ali\n",
        ["student_id", "guardian1_phone", "first_name"],
    )
    assert rows == [
        {
            "student_id": "=MIS-1",
            "guardian1_phone": "+96812345678",
            "first_name": "Ali",
        }
    ]


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


def test_missing_student_id_is_an_error(client, import_world):
    resp = upload(client, import_world, [csv_row(first_name="Ali", last_name="Khan")])
    row = resp.json()["rows"][0]
    assert row["action"] == "error"
    assert "student_id is required" in row["errors"]


def test_duplicate_student_id_within_file_errors(client, import_world):
    world = import_world
    rows = [
        csv_row(student_id="S-010", first_name="Ali", last_name="Khan"),
        csv_row(student_id=" s-010 ", first_name="Sara", last_name="Khan", section="B"),
    ]
    resp = upload(client, world, rows)
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["summary"]["conflict"] == 2
    for row in payload["rows"]:
        assert row["action"] == "conflict"
        assert "Duplicate normalised student_id in file" in row["errors"]


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

    second = upload(client, world, [csv_row(student_id=" s-070 ", first_name="Alya", last_name="Khan", preferred_name="Aly")])
    payload = second.json()
    row = row_for(payload, "s-070")
    assert row["action"] == "update"
    committed = commit(client, world, payload["id"])
    assert committed.status_code == 200

    students = db.query(Student).filter(Student.school_id == world["alpha"].id).all()
    assert len(students) == 1
    assert students[0].first_name == "Alya"
    assert students[0].external_ref == "s-070"


def test_blank_optional_student_values_preserve_existing_data(client, import_world, db):
    world = import_world
    first = upload(
        client,
        world,
        [
            csv_row(
                student_id="S-071",
                first_name="Ali",
                last_name="Khan",
                preferred_name="Aly",
                name_ar="علي خان",
                dob="2015-02-03",
                gender="male",
            )
        ],
    )
    commit(client, world, first.json()["id"])

    second = upload(client, world, [csv_row(student_id="S-071", first_name="Ali", last_name="Khan")])
    assert row_for(second.json(), "S-071")["action"] == "skip"
    commit(client, world, second.json()["id"])

    student = db.query(Student).filter(Student.school_id == world["alpha"].id, Student.external_ref == "S-071").one()
    assert student.preferred_name == "Aly"
    assert student.name_ar == "علي خان"
    assert str(student.date_of_birth) == "2015-02-03"
    assert student.gender == "male"


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


def test_annual_update_requires_scoped_year_and_defaults_to_its_start_date(client, import_world):
    world = import_world
    row = csv_row(
        student_id="ANNUAL-001",
        first_name="Ali",
        last_name="Khan",
        student_status="active",
    )

    missing_year = upload(client, world, [row], mode="annual")
    assert missing_year.status_code == 422
    assert "destination academic year" in missing_year.json()["detail"]

    wrong_school = upload(
        client,
        world,
        [row],
        mode="annual",
        academic_year_id=world["beta_year"].id,
    )
    assert wrong_school.status_code == 422
    assert "not available for this school" in wrong_school.json()["detail"]

    staged = annual_upload(client, world, [row])
    assert staged.status_code == 201
    assert staged.json()["mode"] == "annual"
    assert staged.json()["academic_year_id"] == world["next_year"].id
    assert staged.json()["effective_date"] == "2027-07-01"


def test_annual_update_moves_existing_student_preserves_history_and_is_idempotent(
    client, import_world, db
):
    world = import_world
    initial = upload(
        client,
        world,
        [csv_row(student_id="ANNUAL-MOVE", first_name="Ali", last_name="Khan")],
    )
    assert commit(client, world, initial.json()["id"]).status_code == 200
    student = (
        db.query(Student)
        .filter(Student.school_id == world["alpha"].id, Student.external_ref == "ANNUAL-MOVE")
        .one()
    )

    annual_row = csv_row(
        student_id=" annual-move ",
        first_name="Ali",
        last_name="Khan",
        grade="G1",
        section="A",
        student_status="active",
    )
    staged = annual_upload(client, world, [annual_row], effective_date="2027-07-15")
    assert staged.status_code == 201
    assert row_for(staged.json(), "annual-move")["action"] == "move"
    committed = commit(client, world, staged.json()["id"])
    assert committed.status_code == 200
    assert committed.json()["effective_date"] == "2027-07-15"

    enrolments = (
        db.query(Enrolment)
        .filter(Enrolment.student_id == student.id)
        .order_by(Enrolment.valid_from.asc(), Enrolment.id.asc())
        .all()
    )
    assert len(enrolments) == 2
    assert enrolments[0].class_section_id == world["section_a"].id
    assert enrolments[0].valid_to == date(2027, 7, 15)
    assert enrolments[1].class_section_id == world["next_g1_section_a"].id
    assert enrolments[1].valid_from == date(2027, 7, 15)
    assert enrolments[1].valid_to is None
    assert db.query(Student).filter(Student.school_id == world["alpha"].id).count() == 1

    repeated = annual_upload(client, world, [annual_row], effective_date="2027-07-15")
    assert row_for(repeated.json(), "annual-move")["action"] == "skip"
    assert commit(client, world, repeated.json()["id"]).status_code == 200
    assert db.query(Enrolment).filter(Enrolment.student_id == student.id).count() == 2

    audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.action == "school.student_import.row_applied",
            AuditLog.entity_id == student.id,
        )
        .order_by(AuditLog.id.asc())
        .first()
    )
    assert audit.actor_user_id == world["alpha_admin"].id
    assert audit.detail["import_id"] == staged.json()["id"]
    assert audit.detail["effective_date"] == "2027-07-15"
    assert audit.detail["previous_enrolment_id"] == enrolments[0].id
    assert audit.detail["new_enrolment_id"] == enrolments[1].id
    assert audit.detail["previous_student_status"] == "active"
    assert audit.detail["new_student_status"] == "active"
    assert "email" not in str(audit.detail).lower()
    assert "phone" not in str(audit.detail).lower()


def test_annual_update_creates_new_student_and_keeps_non_promoted_student_in_imported_class(
    client, import_world, db
):
    world = import_world
    initial = upload(
        client,
        world,
        [csv_row(student_id="REPEAT-KG1", first_name="Noor", last_name="Hassan")],
    )
    commit(client, world, initial.json()["id"])

    rows = [
        csv_row(
            student_id="REPEAT-KG1",
            first_name="Noor",
            last_name="Hassan",
            grade="KG1",
            section="B",
            student_status="active",
        ),
        csv_row(
            student_id="NEW-G1",
            first_name="Sara",
            last_name="Ahmed",
            grade="G1",
            section="A",
            student_status="active",
        ),
        csv_row(
            student_id="NEW-INACTIVE",
            first_name="Former",
            last_name="Student",
            branch="",
            grade="",
            section="",
            student_status="inactive",
        ),
    ]
    staged = annual_upload(client, world, rows)
    assert staged.json()["summary"]["move"] == 1
    assert staged.json()["summary"]["create"] == 1
    assert staged.json()["summary"]["inactive"] == 1
    assert commit(client, world, staged.json()["id"]).status_code == 200

    repeated_student = db.query(Student).filter_by(external_ref="REPEAT-KG1").one()
    new_student = db.query(Student).filter_by(external_ref="NEW-G1").one()
    new_inactive = db.query(Student).filter_by(external_ref="NEW-INACTIVE").one()
    repeated_enrolment = (
        db.query(Enrolment)
        .filter(Enrolment.student_id == repeated_student.id, Enrolment.valid_to.is_(None))
        .one()
    )
    new_enrolment = (
        db.query(Enrolment)
        .filter(Enrolment.student_id == new_student.id, Enrolment.valid_to.is_(None))
        .one()
    )
    assert repeated_enrolment.class_section_id == world["next_kg1_section_b"].id
    assert new_enrolment.class_section_id == world["next_g1_section_a"].id
    assert new_inactive.status == "inactive"
    assert db.query(Enrolment).filter(Enrolment.student_id == new_inactive.id).count() == 0


def test_annual_explicit_leaver_removes_current_access_but_preserves_links_and_reactivates(
    client, import_world, db
):
    world = import_world
    initial_rows = [
        csv_row(student_id="LEAVER-1", first_name="Ali", last_name="Khan"),
        csv_row(student_id="STILL-ACTIVE", first_name="Maya", last_name="Khan"),
    ]
    initial = upload(client, world, initial_rows)
    commit(client, world, initial.json()["id"])
    leaver = db.query(Student).filter_by(external_ref="LEAVER-1").one()
    untouched = db.query(Student).filter_by(external_ref="STILL-ACTIVE").one()
    guardian = create_user(db, "leaver-guardian@example.com", "Leaver Guardian")
    link = GuardianLink(
        school_id=world["alpha"].id,
        student_id=leaver.id,
        user_id=guardian.id,
        relationship="guardian",
        status="active",
    )
    db.add(link)
    db.commit()
    assert has_active_entitlement(db, guardian.id) is True

    leaver_row = csv_row(
        student_id="LEAVER-1",
        first_name="Ali",
        last_name="Khan",
        branch="",
        grade="",
        section="",
        student_status="leaver",
    )
    staged = annual_upload(client, world, [leaver_row])
    assert row_for(staged.json(), "LEAVER-1")["action"] == "leaver"
    assert commit(client, world, staged.json()["id"]).status_code == 200

    db.refresh(leaver)
    db.refresh(untouched)
    db.refresh(link)
    assert leaver.status == "leaver"
    assert untouched.status == "active"
    assert link.status == "active"
    assert link.revoked_at is None
    assert has_active_entitlement(db, guardian.id) is False
    closed = db.query(Enrolment).filter(Enrolment.student_id == leaver.id).one()
    untouched_enrolment = db.query(Enrolment).filter(Enrolment.student_id == untouched.id).one()
    assert closed.valid_to == date(2027, 7, 1)
    assert untouched_enrolment.valid_to is None

    returning_row = csv_row(
        student_id="LEAVER-1",
        first_name="Ali",
        last_name="Khan",
        grade="G1",
        section="A",
        student_status="active",
    )
    returning = annual_upload(client, world, [returning_row])
    assert row_for(returning.json(), "LEAVER-1")["action"] == "reactivate"
    assert commit(client, world, returning.json()["id"]).status_code == 200
    db.refresh(leaver)
    assert leaver.status == "active"
    assert has_active_entitlement(db, guardian.id) is True
    assert (
        db.query(Enrolment)
        .filter(
            Enrolment.student_id == leaver.id,
            Enrolment.class_section_id == world["next_g1_section_a"].id,
            Enrolment.valid_from == date(2027, 7, 1),
            Enrolment.valid_to.is_(None),
        )
        .count()
        == 1
    )


def test_annual_inactive_student_cannot_move_without_explicit_reactivation(
    client, import_world, db
):
    world = import_world
    initial = upload(
        client,
        world,
        [csv_row(student_id="INACTIVE-1", first_name="Omar", last_name="Saleh")],
    )
    commit(client, world, initial.json()["id"])
    student = db.query(Student).filter_by(external_ref="INACTIVE-1").one()

    inactive_row = csv_row(
        student_id="INACTIVE-1",
        first_name="Omar",
        last_name="Saleh",
        branch="",
        grade="",
        section="",
        student_status="inactive",
    )
    inactive = annual_upload(client, world, [inactive_row])
    assert row_for(inactive.json(), "INACTIVE-1")["action"] == "inactive"
    commit(client, world, inactive.json()["id"])
    db.refresh(student)
    assert student.status == "inactive"

    invalid_move = annual_upload(
        client,
        world,
        [
            csv_row(
                student_id="INACTIVE-1",
                first_name="Omar",
                last_name="Saleh",
                grade="G1",
                section="A",
                student_status="inactive",
            )
        ],
    )
    row = row_for(invalid_move.json(), "INACTIVE-1")
    assert row["action"] == "conflict"
    assert any("cannot move" in message for message in row["errors"])
    assert commit(client, world, invalid_move.json()["id"]).status_code == 200
    assert db.query(Enrolment).filter(Enrolment.student_id == student.id).count() == 1


def test_annual_overlap_and_future_boundary_are_conflicts(client, import_world, db):
    world = import_world
    overlap_student = Student(
        school_id=world["alpha"].id,
        external_ref="OVERLAP-1",
        first_name="Aya",
        last_name="Noor",
        status="active",
    )
    future_student = Student(
        school_id=world["alpha"].id,
        external_ref="FUTURE-1",
        first_name="Zain",
        last_name="Noor",
        status="active",
    )
    db.add_all([overlap_student, future_student])
    db.flush()
    db.add_all(
        [
            Enrolment(
                school_id=world["alpha"].id,
                student_id=overlap_student.id,
                class_section_id=world["section_a"].id,
                valid_from=date(2026, 7, 1),
            ),
            Enrolment(
                school_id=world["alpha"].id,
                student_id=overlap_student.id,
                class_section_id=world["section_b"].id,
                valid_from=date(2027, 1, 1),
            ),
            Enrolment(
                school_id=world["alpha"].id,
                student_id=future_student.id,
                class_section_id=world["next_g1_section_a"].id,
                valid_from=date(2027, 8, 1),
            ),
        ]
    )
    db.commit()

    staged = annual_upload(
        client,
        world,
        [
            csv_row(
                student_id="OVERLAP-1",
                first_name="Aya",
                last_name="Noor",
                grade="G1",
                student_status="active",
            ),
            csv_row(
                student_id="FUTURE-1",
                first_name="Zain",
                last_name="Noor",
                grade="G1",
                student_status="active",
            ),
        ],
    )
    assert row_for(staged.json(), "OVERLAP-1")["action"] == "conflict"
    assert any("Overlapping" in message for message in row_for(staged.json(), "OVERLAP-1")["errors"])
    assert row_for(staged.json(), "FUTURE-1")["action"] == "conflict"
    assert any("earlier" in message for message in row_for(staged.json(), "FUTURE-1")["errors"])


def test_annual_mixed_valid_and_unknown_structure_rows_commit_independently(
    client, import_world, db
):
    world = import_world
    staged = annual_upload(
        client,
        world,
        [
            csv_row(
                student_id="VALID-ANNUAL",
                first_name="Valid",
                last_name="Student",
                grade="G1",
                section="A",
                student_status="active",
            ),
            csv_row(
                student_id="BAD-SECTION",
                first_name="Bad",
                last_name="Section",
                grade="G1",
                section="UNKNOWN",
                student_status="active",
            ),
            csv_row(
                student_id="BAD-STATUS",
                first_name="Bad",
                last_name="Status",
                grade="G1",
                section="A",
                student_status="departed",
            ),
        ],
    )
    assert staged.json()["summary"]["create"] == 1
    assert staged.json()["summary"]["conflict"] == 2
    assert row_for(staged.json(), "BAD-SECTION")["action"] == "conflict"
    assert row_for(staged.json(), "BAD-STATUS")["action"] == "conflict"
    assert commit(client, world, staged.json()["id"]).status_code == 200
    assert db.query(Student).filter_by(external_ref="VALID-ANNUAL").count() == 1
    assert db.query(Student).filter_by(external_ref="BAD-SECTION").count() == 0
    assert db.query(Student).filter_by(external_ref="BAD-STATUS").count() == 0


def test_duplicate_names_are_allowed(client, import_world):
    world = import_world
    rows = [
        csv_row(student_id="S-NAME-1", first_name="Ali", last_name="Khan", section="A"),
        csv_row(student_id="S-NAME-2", first_name="Ali", last_name="Khan", section="B"),
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


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("guardian1_email", "not-an-email", "guardian1_email is not a valid email"),
        ("guardian1_phone", "call-me", "guardian1_phone must contain 7 to 15 digits"),
    ],
)
def test_invalid_guardian_email_or_phone_is_an_error(client, import_world, field, value, message):
    kwargs = {field: value}
    resp = upload(
        client,
        import_world,
        [csv_row(student_id="S-120-BAD", first_name="Ali", last_name="Khan", guardian1_name="Huda", **kwargs)],
    )
    row = row_for(resp.json(), "S-120-BAD")
    assert row["action"] == "error"
    assert any(message in error for error in row["errors"])


def test_guardian_phone_and_stable_id_import_are_blank_preserving_and_idempotent(client, import_world, db):
    first = upload(
        client,
        import_world,
        [
            csv_row(
                student_id="S-120-PHONE",
                first_name="Ali",
                last_name="Khan",
                guardian1_id=" G-100 ",
                guardian1_name="Huda",
                guardian1_email="HUDA@example.com",
                guardian1_phone="00 968 9123 4567",
                guardian1_relationship="mother",
            )
        ],
    )
    commit(client, import_world, first.json()["id"])
    student = db.query(Student).filter_by(external_ref="S-120-PHONE").one()
    contact = db.query(StudentGuardianContact).filter_by(student_id=student.id).one()
    assert contact.external_ref == "G-100"
    assert contact.email == "huda@example.com"
    assert contact.phone == "00 968 9123 4567"
    assert contact.phone_normalized == "+96891234567"
    assert contact.source == "import"
    first_import_id = contact.source_import_id
    first_updated_at = contact.updated_at

    second = upload(
        client,
        import_world,
        [
            csv_row(
                student_id="S-120-PHONE",
                first_name="Ali",
                last_name="Khan",
                guardian2_id="G-100",
                guardian2_name="Huda",
                guardian2_email="huda@example.com",
                guardian2_phone="",
            )
        ],
    )
    assert row_for(second.json(), "S-120-PHONE")["action"] == "skip"
    commit(client, import_world, second.json()["id"])
    db.refresh(contact)
    assert db.query(StudentGuardianContact).filter_by(student_id=student.id).count() == 1
    assert contact.phone_normalized == "+96891234567"
    assert contact.source_import_id == first_import_id
    assert contact.updated_at == first_updated_at


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
    audits = db.query(AuditLog).filter_by(action="school.guardian_contact.created").all()
    assert len(audits) == 2
    assert all(row.detail["source"] == "import" for row in audits)
    assert "huda@example.com" not in str([row.detail for row in audits])


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
        [csv_row(student_id="S-123", first_name="Ali", last_name="Khan", guardian1_email="huda.khan@example.com")],
    )
    assert row_for(second.json(), "S-123")["action"] == "update"
    commit(client, world, second.json()["id"])

    contacts = db.query(StudentGuardianContact).filter(StudentGuardianContact.student_id == student.id).all()
    assert len(contacts) == 1
    assert contacts[0].id == first_contact_id
    assert contacts[0].name == "Huda"
    assert contacts[0].email == "huda.khan@example.com"
    assert contacts[0].relationship == "mother"


def test_identical_guardian_reimport_is_true_no_op(client, import_world, db):
    world = import_world
    row = csv_row(
        student_id="S-123-NOOP",
        first_name="Ali",
        last_name="Khan",
        guardian1_name="Huda",
        guardian1_email="huda@example.com",
        guardian1_relationship="mother",
    )
    first = upload(client, world, [row])
    commit(client, world, first.json()["id"])
    student = db.query(Student).filter(Student.external_ref == "S-123-NOOP").one()
    contact = db.query(StudentGuardianContact).filter_by(student_id=student.id, slot=1).one()
    first_source_import_id = contact.source_import_id
    first_updated_at = contact.updated_at

    second = upload(client, world, [row])
    assert row_for(second.json(), "S-123-NOOP")["action"] == "skip"
    commit(client, world, second.json()["id"])

    db.refresh(contact)
    assert contact.source_import_id == first_source_import_id
    assert contact.updated_at == first_updated_at


@pytest.mark.parametrize("contact_status", ["linked", "ignored"])
def test_guardian_contact_already_acted_on_is_conflict_and_not_overwritten(
    client, import_world, db, contact_status
):
    world = import_world
    first = upload(
        client, world,
        [csv_row(student_id="S-124", first_name="Ali", last_name="Khan", guardian1_name="Huda", guardian1_email="huda@example.com", guardian1_relationship="mother")],
    )
    commit(client, world, first.json()["id"])
    student = db.query(Student).filter(Student.school_id == world["alpha"].id, Student.external_ref == "S-124").first()
    contact = db.query(StudentGuardianContact).filter(StudentGuardianContact.student_id == student.id, StudentGuardianContact.slot == 1).first()
    contact.status = contact_status
    db.commit()

    second = upload(
        client, world,
        [csv_row(student_id="S-124", first_name="Ali", last_name="Khan", guardian1_name="Someone Else", guardian1_email="someone@example.com", guardian1_relationship="mother")],
    )
    preview_row = row_for(second.json(), "S-124")
    assert preview_row["action"] == "conflict"
    assert contact_status in " ".join(preview_row["errors"])
    committed = commit(client, world, second.json()["id"])
    committed_row = row_for(committed.json(), "S-124")
    assert committed_row["action"] == "conflict"
    assert committed_row["applied_entity_id"] is None

    db.refresh(contact)
    assert contact.status == contact_status
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


def test_import_history_is_school_scoped_paginated_and_filterable(
    client, import_world
):
    world = import_world
    committed = upload(
        client,
        world,
        [csv_row(student_id="HISTORY-1", first_name="Ali", last_name="Khan")],
        filename="normal.csv",
    )
    commit(client, world, committed.json()["id"])
    annual = annual_upload(
        client,
        world,
        [
            csv_row(
                student_id="HISTORY-2",
                first_name="Noor",
                last_name="Hassan",
                student_status="active",
            )
        ],
    )
    discarded = upload(
        client,
        world,
        [csv_row(student_id="HISTORY-3", first_name="Sara", last_name="Ali")],
        filename="discarded.csv",
    )
    client.post(
        f"/api/school/students/imports/{discarded.json()['id']}/discard",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    failed_upload = client.post(
        "/api/school/students/imports",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        files={"file": ("failed.csv", b"\xff\xfe\x00bad", "text/csv")},
    )
    assert failed_upload.status_code == 422

    first_page = client.get(
        "/api/school/students/imports?page=1&page_size=2",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    assert first_page.status_code == 200
    assert first_page.json()["total"] == 4
    assert first_page.json()["pages"] == 2
    assert len(first_page.json()["items"]) == 2

    committed_only = client.get(
        "/api/school/students/imports?status=committed&mode=normal",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    item = committed_only.json()["items"][0]
    assert committed_only.json()["total"] == 1
    assert item["id"] == committed.json()["id"]
    assert item["filename"] == "normal.csv"
    assert item["mode"] == "normal"
    assert item["file_hash"] is None
    assert item["uploaded_by"]["name"] == "Alpha Admin"
    assert item["committed_by"]["name"] == "Alpha Admin"
    assert item["summary"]["create"] == 1
    created_date = item["created_at"][:10]

    annual_only = client.get(
        "/api/school/students/imports?status=staged&mode=annual",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    annual_item = annual_only.json()["items"][0]
    assert annual_item["id"] == annual.json()["id"]
    assert annual_item["academic_year"]["id"] == world["next_year"].id
    assert annual_item["effective_date"] == "2027-07-01"

    by_date = client.get(
        f"/api/school/students/imports?date_from={created_date}&date_to={created_date}",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    assert by_date.json()["total"] == 4

    failed = client.get(
        "/api/school/students/imports?status=failed",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    assert failed.status_code == 200
    assert failed.json()["total"] == 1
    assert failed.json()["items"][0]["filename"] == "failed.csv"
    assert failed.json()["items"][0]["summary"]["error"] == 1
    failed_detail = client.get(
        f"/api/school/students/imports/{failed.json()['items'][0]['id']}",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    assert failed_detail.status_code == 200
    assert failed_detail.json()["rows"][0]["action"] == "error"
    assert failed_detail.json()["rows"][0]["reason"]

    beta = client.get(
        "/api/school/students/imports",
        headers=bearer(world["beta_admin"].email, world["beta"].id),
    )
    assert beta.status_code == 200
    assert beta.json()["total"] == 0


def test_import_history_rows_are_paginated_private_and_audited(
    client, import_world, db
):
    world = import_world
    staged = upload(
        client,
        world,
        [
            csv_row(
                student_id="HISTORY-ROW",
                first_name="Ali",
                last_name="Khan",
                guardian1_name="Private Guardian",
                guardian1_email="private.guardian@example.com",
                guardian1_phone="+96891234567",
            )
        ],
    )
    commit(client, world, staged.json()["id"])

    detail = client.get(
        f"/api/school/students/imports/{staged.json()['id']}?page=1&page_size=1",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["rows_pagination"] == {
        "page": 1,
        "page_size": 1,
        "total": 1,
        "pages": 1,
    }
    row = body["rows"][0]
    assert row["student_id"] == "HISTORY-ROW"
    assert row["student_name"] == "Ali Khan"
    assert row["intended_placement"]["section"] == "A"
    assert row["action"] == "create"
    assert row["affected_student"]["student_id"] == "HISTORY-ROW"
    assert "private.guardian@example.com" not in detail.text
    assert "+96891234567" not in detail.text

    teacher = client.get(
        f"/api/school/students/imports/{staged.json()['id']}",
        headers=bearer(world["alpha_teacher"].email, world["alpha"].id),
    )
    assert teacher.status_code == 403
    cross_school = client.get(
        f"/api/school/students/imports/{staged.json()['id']}",
        headers=bearer(world["beta_admin"].email, world["beta"].id),
    )
    assert cross_school.status_code == 404
    audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.action == "school.import.history.viewed",
            AuditLog.entity_id == staged.json()["id"],
        )
        .one()
    )
    assert audit.actor_user_id == world["alpha_admin"].id
    assert "email" not in str(audit.detail).lower()
    assert "phone" not in str(audit.detail).lower()


def test_import_result_reports_cover_all_filters_utf8_and_formula_safety(
    client, import_world, db
):
    world = import_world
    staged = upload(
        client,
        world,
        [
            csv_row(
                student_id="REPORT-VALID",
                first_name="=1+1",
                last_name="Khan",
                name_ar="نور",
            ),
            csv_row(student_id="REPORT-DUP", first_name="One", last_name="Duplicate"),
            csv_row(student_id=" report-dup ", first_name="Two", last_name="Duplicate"),
            csv_row(student_id="REPORT-ERROR", first_name="", last_name="Missing"),
        ],
    )
    assert commit(client, world, staged.json()["id"]).status_code == 200

    report_rows = {}
    for report_type, expected_count in {
        "all": 4,
        "conflicts": 2,
        "errors": 1,
        "committed": 1,
    }.items():
        response = client.get(
            f"/api/school/students/imports/{staged.json()['id']}/reports/{report_type}.csv",
            headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        )
        assert response.content.startswith(b"\xef\xbb\xbf")
        rows = csv_download_rows(response)
        assert len(rows) == expected_count
        report_rows[report_type] = rows

    committed_row = report_rows["committed"][0]
    assert committed_row["outcome"] == "create"
    assert committed_row["first_name"] == "'=1+1"
    assert committed_row["name_ar"] == "نور"
    assert committed_row["affected_student_id"]
    assert report_rows["conflicts"][0]["reason"]
    assert report_rows["errors"][0]["reason"]
    assert set(CSV_HEADER.split(",")).issubset(report_rows["all"][0].keys())

    cross_school = client.get(
        f"/api/school/students/imports/{staged.json()['id']}/reports/all.csv",
        headers=bearer(world["beta_admin"].email, world["beta"].id),
    )
    assert cross_school.status_code == 404
    assert (
        db.query(AuditLog)
        .filter(
            AuditLog.action == "school.import.report.exported",
            AuditLog.entity_id == staged.json()["id"],
        )
        .count()
        == 4
    )


def test_current_roster_guardian_enrolment_and_annual_exports_are_safe(
    client, import_world, db
):
    world = import_world
    staged = upload(
        client,
        world,
        [
            csv_row(
                student_id="EXPORT-1",
                first_name="=Ali",
                last_name="Khan",
                preferred_name="Aly",
                name_ar="علي خان",
                dob="2015-02-03",
                gender="male",
                guardian1_id="G-EXPORT-1",
                guardian1_name="@Guardian",
                guardian1_email="guardian.export@example.com",
                guardian1_phone="+96891234567",
                guardian1_relationship="guardian",
            )
        ],
    )
    commit(client, world, staged.json()["id"])
    student = db.query(Student).filter_by(external_ref="EXPORT-1").one()
    contact = db.query(StudentGuardianContact).filter_by(student_id=student.id).one()
    contact.is_primary = True
    contact.is_emergency = True
    db.commit()

    active = client.get(
        "/api/school/students/exports/active-roster.csv",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    active_rows = csv_download_rows(active)
    assert active_rows[0]["student_id"] == "EXPORT-1"
    assert active_rows[0]["first_name"] == "'=Ali"
    assert active_rows[0]["name_ar"] == "علي خان"
    assert active_rows[0]["student_status"] == "active"
    assert active_rows[0]["branch"] == "MAIN"
    assert active_rows[0]["grade"] == "KG1"
    assert active_rows[0]["section"] == "A"

    guardians = client.get(
        "/api/school/students/exports/guardian-contacts.csv",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    guardian_rows = csv_download_rows(guardians)
    assert guardian_rows[0]["guardian_contact_id"] == "G-EXPORT-1"
    assert guardian_rows[0]["guardian_name"] == "'@Guardian"
    assert guardian_rows[0]["email"] == "guardian.export@example.com"
    assert guardian_rows[0]["phone"] == "'+96891234567"
    assert guardian_rows[0]["is_primary"] == "true"
    assert guardian_rows[0]["is_emergency"] == "true"
    assert guardian_rows[0]["contact_active"] == "true"

    enrolments = client.get(
        "/api/school/students/exports/class-enrolments.csv",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    enrolment_rows = csv_download_rows(enrolments)
    assert enrolment_rows[0]["student_id"] == "EXPORT-1"
    assert enrolment_rows[0]["academic_year"] == "2026"
    assert enrolment_rows[0]["valid_from"]

    annual = client.get(
        "/api/school/students/exports/annual-update.csv",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    annual_rows = csv_download_rows(annual)
    assert list(annual_rows[0].keys()) == CSV_HEADER.split(",")
    assert annual_rows[0]["student_id"] == "EXPORT-1"
    assert annual_rows[0]["name_ar"] == "علي خان"
    assert annual_rows[0]["student_status"] == "active"
    assert annual_rows[0]["guardian1_id"] == "G-EXPORT-1"
    assert annual_rows[0]["guardian1_name"] == "'@Guardian"
    assert annual_rows[0]["guardian1_email"] == "guardian.export@example.com"

    forbidden_headers = {
        "user_id",
        "password",
        "session",
        "token",
        "fhh_child_ref",
        "fhh_household_ref",
        "message",
        "behaviour",
        "safeguarding",
    }
    for rows in (active_rows, guardian_rows, enrolment_rows, annual_rows):
        assert forbidden_headers.isdisjoint(rows[0].keys())

    beta = client.get(
        "/api/school/students/exports/annual-update.csv",
        headers=bearer(world["beta_admin"].email, world["beta"].id),
    )
    assert beta.status_code == 200
    assert csv_download_rows(beta) == []
    teacher = client.get(
        "/api/school/students/exports/active-roster.csv",
        headers=bearer(world["alpha_teacher"].email, world["alpha"].id),
    )
    assert teacher.status_code == 403
    assert (
        db.query(AuditLog)
        .filter(AuditLog.action == "school.student_export.downloaded")
        .count()
        == 5
    )
    history = client.get(
        "/api/school/students/export-history?page=1&page_size=2",
        headers=bearer(world["alpha_admin"].email, world["alpha"].id),
    )
    assert history.status_code == 200
    assert history.json()["total"] == 4
    assert history.json()["pages"] == 2
    assert len(history.json()["items"]) == 2
    assert history.json()["items"][0]["activity"] == "export"
    assert history.json()["items"][0]["status"] == "downloaded"
    assert history.json()["items"][0]["row_count"] == 1
    assert history.json()["items"][0]["actor"]["name"] == "Alpha Admin"

    beta_history = client.get(
        "/api/school/students/export-history",
        headers=bearer(world["beta_admin"].email, world["beta"].id),
    )
    assert beta_history.status_code == 200
    assert beta_history.json()["total"] == 1
    teacher_history = client.get(
        "/api/school/students/export-history",
        headers=bearer(world["alpha_teacher"].email, world["alpha"].id),
    )
    assert teacher_history.status_code == 403


def test_large_import_history_and_exports_have_bounded_query_shape(
    client, import_world, db
):
    world = import_world
    imp = Import(
        school_id=world["alpha"].id,
        kind="students",
        mode="normal",
        filename="large.csv",
        status="staged",
        uploaded_by_user_id=world["alpha_admin"].id,
        summary={"total": 500, "skip": 500},
    )
    db.add(imp)
    db.flush()
    students = [
        Student(
            school_id=world["alpha"].id,
            external_ref=f"BOUNDED-{idx}",
            first_name=f"First{idx}",
            last_name=f"Last{idx}",
            status="active",
        )
        for idx in range(40)
    ]
    db.add_all(students)
    db.flush()
    db.add_all(
        [
            ImportRow(
                import_id=imp.id,
                row_number=idx,
                raw={
                    "student_id": f"LARGE-{idx}",
                    "first_name": f"First{idx}",
                    "last_name": f"Last{idx}",
                    "branch": "MAIN",
                    "grade": "KG1",
                    "section": "A",
                },
                action="skip",
            )
            for idx in range(1, 501)
        ]
    )
    db.commit()

    with count_queries() as detail_queries:
        detail = client.get(
            f"/api/school/students/imports/{imp.id}?page=7&page_size=25",
            headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        )
    assert detail.status_code == 200
    assert len(detail.json()["rows"]) == 25
    assert detail.json()["rows_pagination"]["total"] == 500
    assert detail_queries["n"] < 20

    with count_queries() as export_queries:
        active = client.get(
            "/api/school/students/exports/active-roster.csv",
            headers=bearer(world["alpha_admin"].email, world["alpha"].id),
        )
    assert active.status_code == 200
    assert len(csv_download_rows(active)) == 40
    assert export_queries["n"] < 10

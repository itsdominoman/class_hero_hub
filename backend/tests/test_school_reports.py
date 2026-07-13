import os
from datetime import datetime, timezone

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database
from app.database import Base, get_db
from app.main import app
from app.models_school import AcademicYear, BehaviourCategory, BehaviourEvent, BranchCampus, ClassSection, Enrolment, GradeLevel, Membership, School, Student, Subject, SubjectGroup, User


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)
database.engine = engine
database.SessionLocal = Session


@pytest.fixture
def db():
    Base.metadata.create_all(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    def override():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def report_world(db):
    school = School(name="Alpha", slug="alpha", status="active")
    other_school = School(name="Beta", slug="beta", status="active")
    admin = User(email="admin@example.test", name="Admin")
    teacher = User(email="teacher@example.test", name="Teacher")
    guardian = User(email="guardian@example.test", name="Guardian")
    student = Student(school_id=1, first_name="Ava", last_name="Student", status="active")
    other_student = Student(school_id=2, first_name="Ben", last_name="Other", status="active")
    db.add_all([school, other_school, admin, teacher, guardian])
    db.flush()
    student.school_id = school.id
    other_student.school_id = other_school.id
    db.add_all([student, other_student])
    db.flush()
    db.add_all([
        Membership(school_id=school.id, user_id=admin.id, role="school_admin"),
        Membership(school_id=school.id, user_id=teacher.id, role="teacher"),
    ])
    positive = BehaviourCategory(school_id=school.id, type="positive", label="Helpful", points_value=2)
    needs_work = BehaviourCategory(school_id=school.id, type="needs_work", label="Off task", points_value=-1)
    db.add_all([positive, needs_work])
    db.flush()
    db.add_all([
        BehaviourEvent(school_id=school.id, student_id=student.id, category_id=positive.id, actor_user_id=teacher.id, points_delta=2, context_type="general", source="teacher"),
        BehaviourEvent(school_id=school.id, student_id=student.id, category_id=needs_work.id, actor_user_id=teacher.id, points_delta=-1, context_type="general", source="teacher", note="private note"),
        BehaviourEvent(school_id=school.id, student_id=student.id, category_id=positive.id, actor_user_id=teacher.id, points_delta=2, context_type="general", source="teacher", reversed_at=datetime.now()),
    ])
    db.commit()
    return {"school": school, "other_school": other_school, "admin": admin, "teacher": teacher, "guardian": guardian, "student": student, "other_student": other_student}


def headers(user, school):
    return {"Authorization": f"Bearer {auth.create_access_token({'sub': user.email})}", "X-School-Id": str(school.id)}


def add_context_events(db, world):
    branch = BranchCampus(school_id=world["school"].id, code="MAIN", name="Main")
    year = AcademicYear(school_id=world["school"].id, code="2026", name="2026")
    grade = GradeLevel(school_id=world["school"].id, code="G1", name="Grade 1")
    subject = Subject(school_id=world["school"].id, code="ENG", name="English")
    db.add_all([branch, year, grade, subject])
    db.flush()
    section = ClassSection(school_id=world["school"].id, branch_campus_id=branch.id, academic_year_id=year.id, grade_level_id=grade.id, code="A", name="Grade 1 A")
    db.add(section)
    db.flush()
    group = SubjectGroup(school_id=world["school"].id, academic_year_id=year.id, class_section_id=section.id, subject_id=subject.id, code="G1A-ENG", name="Grade 1 A English")
    db.add(group)
    db.flush()
    db.add(Enrolment(school_id=world["school"].id, student_id=world["student"].id, class_section_id=section.id, kind="member"))
    positive = db.query(BehaviourCategory).filter_by(school_id=world["school"].id, type="positive").one()
    needs_work = db.query(BehaviourCategory).filter_by(school_id=world["school"].id, type="needs_work").one()
    db.add_all([
        BehaviourEvent(school_id=world["school"].id, student_id=world["student"].id, category_id=positive.id, actor_user_id=world["teacher"].id, points_delta=2, context_type="subject", subject_group_id=group.id, source="teacher"),
        BehaviourEvent(school_id=world["school"].id, student_id=world["student"].id, category_id=needs_work.id, actor_user_id=world["teacher"].id, points_delta=-1, context_type="class", class_section_id=section.id, source="teacher"),
    ])
    db.commit()
    return {"branch": branch, "year": year, "grade": grade, "section": section, "subject": subject, "group": group}


def test_reports_admin_scope_aggregates_and_safe_events(client, report_world):
    world = report_world
    overview = client.get("/api/school/reports/behaviour/overview", headers=headers(world["admin"], world["school"]))
    assert overview.status_code == 200
    assert overview.json()["metrics"] == {"total_events": 2, "positive_count": 1, "needs_work_count": 1, "signed_points_total": 1, "active_students": 1, "active_teachers": 1, "positive_ratio": 0.5}
    events = client.get("/api/school/reports/behaviour/events?limit=1", headers=headers(world["admin"], world["school"]))
    assert events.status_code == 200 and events.json()["pagination"] == {"limit": 1, "offset": 0, "total": 2}
    payload = events.json()["events"][0]
    assert "note" not in payload
    for forbidden in ("email", "token", "hash", "storage_key", "path", "fhh"):
        assert forbidden not in str(payload).lower()
    ordered = client.get("/api/school/reports/behaviour/events?limit=100", headers=headers(world["admin"], world["school"])).json()["events"]
    assert [row["id"] for row in ordered] == sorted((row["id"] for row in ordered), reverse=True)
    first_page = client.get("/api/school/reports/behaviour/events?limit=1", headers=headers(world["admin"], world["school"])).json()["events"]
    second_page = client.get("/api/school/reports/behaviour/events?limit=1&offset=1", headers=headers(world["admin"], world["school"])).json()["events"]
    assert first_page[0]["id"] > second_page[0]["id"]


def test_reports_reject_non_admin_cross_school_and_invalid_filters(client, report_world):
    world = report_world
    path = "/api/school/reports/behaviour/overview"
    assert client.get(path, headers=headers(world["teacher"], world["school"])).status_code == 403
    assert client.get(path, headers=headers(world["guardian"], world["school"])).status_code == 403
    assert client.get(path, headers=headers(world["admin"], world["other_school"])).status_code == 403
    assert client.get(f"{path}?student_id={world['other_student'].id}", headers=headers(world["admin"], world["school"])).status_code == 422
    assert client.get(f"{path}?date_from=2026-02-01&date_to=2025-01-01", headers=headers(world["admin"], world["school"])).status_code == 422


def test_matrix_validation_and_single_dimension(client, report_world):
    world = report_world
    headers_value = headers(world["admin"], world["school"])
    response = client.get("/api/school/reports/behaviour/matrix?row_dimension=category_type", headers=headers_value)
    assert response.status_code == 200
    assert {row["label"] for row in response.json()["rows"]} == {"positive", "needs_work"}
    assert client.get("/api/school/reports/behaviour/matrix?row_dimension=unknown", headers=headers_value).status_code == 400
    assert client.get("/api/school/reports/behaviour/matrix?row_dimension=student&column_dimension=student", headers=headers_value).status_code == 400
    assert client.get("/api/school/reports/behaviour/matrix?row_dimension=student&order_by=bad", headers=headers_value).status_code == 400
    for pair in (("subject", "duty_context"), ("subject_group", "duty_context")):
        response = client.get(f"/api/school/reports/behaviour/matrix?row_dimension={pair[0]}&column_dimension={pair[1]}", headers=headers_value)
        assert response.status_code == 400
        assert "Incompatible matrix dimensions" in response.json()["detail"]


def test_report_endpoint_smoke_and_matrix_pairs(client, db, report_world):
    world = report_world
    context = add_context_events(db, world)
    headers_value = headers(world["admin"], world["school"])
    for path in (
        "/api/school/reports/behaviour/trends",
        "/api/school/reports/behaviour/breakdowns",
        "/api/school/reports/behaviour/students",
        "/api/school/reports/behaviour/teachers",
        "/api/school/reports/behaviour/events?offset=1&limit=1",
    ):
        response = client.get(path, headers=headers_value)
        assert response.status_code == 200, response.text
    trend = client.get("/api/school/reports/behaviour/trends", headers=headers_value).json()
    assert trend["interval"] == "day" and sum(row["total_events"] for row in trend["series"]) == 4
    breakdowns = client.get("/api/school/reports/behaviour/breakdowns", headers=headers_value).json()
    assert breakdowns["classes"][0]["dimension_key"] == context["section"].id
    assert breakdowns["grades"][0]["dimension_key"] == context["grade"].id
    assert breakdowns["subjects"][0]["dimension_key"] == context["subject"].id
    assert all(row["category_type"] in {"positive", "needs_work"} for row in breakdowns["categories"])
    student_support = client.get("/api/school/reports/behaviour/students", headers=headers_value).json()
    assert student_support["repeated_needs_work"][0]["display_name"] == "Ava Student"
    teacher_usage = client.get("/api/school/reports/behaviour/teachers", headers=headers_value).json()
    assert teacher_usage["teachers"][0]["display_name"] == "Teacher"
    pairs = (
        ("student", "subject"),
        ("teacher", "subject"),
        ("class_section", "category"),
        ("subject", "category_type"),
        ("student", "teacher"),
    )
    for row_dimension, column_dimension in pairs:
        response = client.get(f"/api/school/reports/behaviour/matrix?row_dimension={row_dimension}&column_dimension={column_dimension}", headers=headers_value)
        assert response.status_code == 200, response.text
        assert response.json()["rows"]
        for forbidden in ("email", "token", "hash", "storage_key", "path", "fhh", "note"):
            assert forbidden not in str(response.json()).lower()


def test_matrix_grade_by_duty_uses_event_time_enrolment(client, db, report_world):
    world = report_world
    context = add_context_events(db, world)
    category = db.query(BehaviourCategory).filter_by(school_id=world["school"].id, type="positive").one()
    db.add(BehaviourEvent(school_id=world["school"].id, student_id=world["student"].id, category_id=category.id, actor_user_id=world["teacher"].id, points_delta=2, context_type="duty", duty_context="break", source="teacher"))
    db.commit()
    response = client.get("/api/school/reports/behaviour/matrix?row_dimension=grade&column_dimension=duty_context", headers=headers(world["admin"], world["school"]))
    assert response.status_code == 200, response.text
    grade_row = next(row for row in response.json()["rows"] if row["label"] == "Grade 1")
    assert next(cell for cell in grade_row["cells"] if cell["label"] == "break")["total_events"] == 1


def test_two_dimension_limit_returns_complete_selected_rows(client, db, report_world):
    world = report_world
    second = Student(school_id=world["school"].id, first_name="Cara", last_name="Student", status="active")
    third_category = BehaviourCategory(school_id=world["school"].id, type="positive", label="Leadership", points_value=1)
    db.add_all([second, third_category])
    db.flush()
    categories = db.query(BehaviourCategory).filter_by(school_id=world["school"].id).all()
    for student in (world["student"], second):
        for category in categories:
            db.add(BehaviourEvent(school_id=world["school"].id, student_id=student.id, category_id=category.id, actor_user_id=world["teacher"].id, points_delta=category.points_value, context_type="general", source="teacher"))
    db.commit()
    response = client.get("/api/school/reports/behaviour/matrix?row_dimension=student&column_dimension=category&limit=2", headers=headers(world["admin"], world["school"]))
    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload["rows"]) == 2
    assert all(len(row["cells"]) == 3 for row in payload["rows"])
    assert payload["truncation"]["returned_cells"] == 6
    assert payload["truncation"]["columns_truncated"] is False


def test_trends_and_matrix_bucket_by_school_local_day(client, db, report_world):
    world = report_world
    world["school"].timezone = "Asia/Muscat"
    category = BehaviourCategory(school_id=world["school"].id, type="positive", label="Midnight local", points_value=1)
    db.add(category)
    db.flush()
    db.add(BehaviourEvent(school_id=world["school"].id, student_id=world["student"].id, category_id=category.id, actor_user_id=world["teacher"].id, points_delta=1, context_type="general", source="teacher", created_at=datetime(2026, 7, 12, 21, 30, tzinfo=timezone.utc)))
    db.commit()
    suffix = f"date_from=2026-07-13&date_to=2026-07-13&category_id={category.id}"
    trend = client.get(f"/api/school/reports/behaviour/trends?{suffix}", headers=headers(world["admin"], world["school"]))
    assert trend.status_code == 200, trend.text
    assert trend.json()["series"] == [{"date": "2026-07-13", "total_events": 1, "positive_count": 1, "needs_work_count": 0, "signed_points_total": 1, "active_students": 1}]
    matrix = client.get(f"/api/school/reports/behaviour/matrix?row_dimension=date_bucket&{suffix}", headers=headers(world["admin"], world["school"]))
    assert matrix.status_code == 200, matrix.text
    assert matrix.json()["rows"][0]["label"] == "2026-07-13"

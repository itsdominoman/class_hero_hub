from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database
from app.database import Base, get_db
from app.main import app
from app.models_school import (
    AcademicYear,
    AuditLog,
    BehaviourCategory,
    BehaviourEvent,
    BranchCampus,
    ClassSection,
    Enrolment,
    GradeLevel,
    Membership,
    School,
    Student,
    StudentRecognitionCandidate,
    StudentRecognitionReview,
    User,
)


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


def headers(user, school):
    return {
        "Authorization": f"Bearer {auth.create_access_token({'sub': user.email})}",
        "X-School-Id": str(school.id),
    }


@pytest.fixture
def recognition_world(db):
    school = School(name="Alpha School", slug="recognition-alpha", status="active", timezone="Asia/Muscat")
    other_school = School(name="Beta School", slug="recognition-beta", status="active")
    admin = User(email="recognition.admin@example.test", name="Admin")
    teacher = User(email="recognition.teacher@example.test", name="Teacher")
    outsider = User(email="recognition.outsider@example.test", name="Outsider")
    db.add_all([school, other_school, admin, teacher, outsider])
    db.flush()
    db.add_all([
        Membership(school_id=school.id, user_id=admin.id, role="school_admin", status="active"),
        Membership(school_id=school.id, user_id=teacher.id, role="teacher", status="active"),
        Membership(school_id=other_school.id, user_id=outsider.id, role="school_admin", status="active"),
    ])
    branch = BranchCampus(school_id=school.id, code="MAIN", name="Main Campus", status="active")
    other_branch = BranchCampus(school_id=other_school.id, code="MAIN", name="Other Campus", status="active")
    year = AcademicYear(school_id=school.id, code="2026", name="2026/27", status="active", is_current=True)
    other_year = AcademicYear(school_id=other_school.id, code="2026", name="2026/27", status="active", is_current=True)
    grade = GradeLevel(school_id=school.id, code="G5", name="Grade 5", status="active")
    other_grade = GradeLevel(school_id=other_school.id, code="G5", name="Grade 5", status="active")
    db.add_all([branch, other_branch, year, other_year, grade, other_grade])
    db.flush()
    section = ClassSection(school_id=school.id, branch_campus_id=branch.id, academic_year_id=year.id, grade_level_id=grade.id, code="A", name="Grade 5 A", status="active")
    other_section = ClassSection(school_id=other_school.id, branch_campus_id=other_branch.id, academic_year_id=other_year.id, grade_level_id=other_grade.id, code="A", name="Other 5 A", status="active")
    db.add_all([section, other_section])
    db.flush()
    students = [
        Student(school_id=school.id, external_ref=f"REC-{index}", first_name=name, last_name="Student", name_ar=arabic, status="active")
        for index, (name, arabic) in enumerate((("Ava", "آفا ستودنت"), ("Ben", "بن ستودنت"), ("Cara", "كارا ستودنت")), 1)
    ]
    other_student = Student(school_id=other_school.id, external_ref="REC-X", first_name="Other", last_name="Student", status="active")
    db.add_all([*students, other_student])
    db.flush()
    db.add_all([
        Enrolment(school_id=school.id, student_id=student.id, class_section_id=section.id, kind="member", valid_from=date(2026, 7, 1))
        for student in students[:2]
    ])
    db.add(Enrolment(school_id=other_school.id, student_id=other_student.id, class_section_id=other_section.id, kind="member", valid_from=date(2026, 7, 1)))
    positive = BehaviourCategory(school_id=school.id, type="positive", label="Helpful", points_value=2, active=True)
    leadership = BehaviourCategory(school_id=school.id, type="positive", label="Leadership", points_value=2, active=True)
    negative = BehaviourCategory(school_id=school.id, type="needs_work", label="Off task", points_value=-2, active=True)
    late = BehaviourCategory(school_id=school.id, type="needs_work", label="Late for class", points_value=-1, active=True)
    other_positive = BehaviourCategory(school_id=other_school.id, type="positive", label="Helpful", points_value=2, active=True)
    db.add_all([positive, leadership, negative, late, other_positive])
    db.flush()
    event_time = datetime(2026, 7, 29, 10, tzinfo=timezone.utc)
    events = []
    for student in students[:2]:
        events.extend([
            BehaviourEvent(school_id=school.id, student_id=student.id, category_id=positive.id, actor_user_id=teacher.id, points_delta=2, source="teacher", context_type="general", created_at=event_time),
            BehaviourEvent(school_id=school.id, student_id=student.id, category_id=positive.id, actor_user_id=teacher.id, points_delta=2, source="teacher", context_type="general", created_at=event_time),
            BehaviourEvent(school_id=school.id, student_id=student.id, category_id=leadership.id, actor_user_id=teacher.id, points_delta=2, source="teacher", context_type="general", created_at=event_time),
        ])
    events.extend([
        BehaviourEvent(school_id=school.id, student_id=students[0].id, category_id=negative.id, actor_user_id=teacher.id, points_delta=-2, source="teacher", context_type="general", note="private negative evidence", created_at=event_time),
        BehaviourEvent(school_id=school.id, student_id=students[0].id, category_id=positive.id, actor_user_id=teacher.id, points_delta=50, source="teacher", context_type="general", created_at=event_time, reversed_at=event_time, reversed_by_user_id=admin.id, reversal_reason="Correction"),
        BehaviourEvent(school_id=school.id, student_id=students[0].id, category_id=positive.id, actor_user_id=teacher.id, points_delta=50, source="teacher", context_type="general", created_at=datetime(2026, 7, 1, tzinfo=timezone.utc)),
    ])
    db.add_all(events)
    db.commit()
    return {
        "school": school,
        "other_school": other_school,
        "admin": admin,
        "teacher": teacher,
        "outsider": outsider,
        "branch": branch,
        "grade": grade,
        "section": section,
        "students": students,
        "positive": positive,
        "leadership": leadership,
        "negative": negative,
        "late": late,
        "other_positive": other_positive,
    }


def config_body(world, **overrides):
    body = {
        "recognition_type": "star_of_week",
        "name": "Star of the Week",
        "scope_type": "class",
        "scope_ref_id": world["section"].id,
        "review_period_days": 7,
        "category_ids": [world["positive"].id, world["leadership"].id],
        "minimum_positive_points": 1,
        "shortlist_size": 1,
        "certificate_title": "Star of the Week",
        "signatory_text": "Head of School",
        "active": True,
    }
    body.update(overrides)
    return body


def create_config(client, world, **overrides):
    response = client.post("/api/school/recognition/configs", headers=headers(world["admin"], world["school"]), json=config_body(world, **overrides))
    assert response.status_code == 201, response.text
    return response.json()


def add_event(db, world, student, category, *, reversed=False):
    event_time = datetime(2026, 7, 29, 10, tzinfo=timezone.utc)
    event = BehaviourEvent(
        school_id=world["school"].id,
        student_id=student.id,
        category_id=category.id,
        actor_user_id=world["teacher"].id,
        points_delta=category.points_value,
        source="teacher",
        context_type="general",
        note="internal evidence must not reach certificates",
        created_at=event_time,
        reversed_at=event_time if reversed else None,
        reversed_by_user_id=world["admin"].id if reversed else None,
        reversal_reason="Correction" if reversed else None,
    )
    db.add(event)
    return event


def test_configuration_is_positive_only_admin_scoped_and_audited(client, db, recognition_world):
    world = recognition_world
    path = "/api/school/recognition/configs"
    assert client.post(path, headers=headers(world["teacher"], world["school"]), json=config_body(world)).status_code == 403
    assert client.post(path, headers=headers(world["admin"], world["school"]), json=config_body(world, category_ids=[world["negative"].id])).status_code == 422
    assert client.post(path, headers=headers(world["admin"], world["school"]), json=config_body(world, category_ids=[world["other_positive"].id])).status_code == 422
    assert client.post(path, headers=headers(world["admin"], world["school"]), json=config_body(world, needs_work_category_ids=[world["positive"].id])).status_code == 422
    assert client.post(path, headers=headers(world["outsider"], world["other_school"]), json=config_body(world)).status_code == 422
    config = create_config(client, world)
    assert config["scope"] == {"type": "class", "id": world["section"].id, "name": "Grade 5 A", "name_ar": None}
    assert [row["label"] for row in config["categories"]] == ["Helpful", "Leadership"]
    assert config["needs_work_safeguard_enabled"] is False
    assert config["maximum_needs_work_events"] == 0
    assert config["needs_work_category_ids"] == []
    assert db.query(AuditLog).filter_by(action="recognition.config.created", school_id=world["school"].id).count() == 1


def test_shortlist_uses_only_unreversed_positive_scoped_period_evidence_and_shows_ties(client, db, recognition_world):
    world = recognition_world
    config = create_config(client, world)
    response = client.post(
        "/api/school/recognition/reviews",
        headers=headers(world["admin"], world["school"]),
        json={"config_id": config["id"], "period_end": "2026-08-01"},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "draft" and payload["selected_student_id"] is None
    assert payload["period_start"] == "2026-07-26" and payload["period_end"] == "2026-08-01"
    assert payload["criteria"]["ordering"] == "positive_points_desc_then_positive_events_desc"
    assert payload["criteria"]["tie_rule"] == "shared_rank_and_include_cutoff_ties"
    assert len(payload["candidates"]) == 2  # one configured slot, extended for the cutoff tie
    assert {row["student_id"] for row in payload["candidates"]} == {world["students"][0].id, world["students"][1].id}
    for candidate in payload["candidates"]:
        assert candidate["positive_points_total"] == 6
        assert candidate["positive_event_count"] == 3
        assert candidate["rank"] == 1
        assert candidate["safeguard_excluded"] is False
        assert candidate["safeguard_counted_total"] == 0
        assert candidate["is_eligible"] is True
        assert {row["label"] for row in candidate["category_totals"]} == {"Helpful", "Leadership"}
        assert "private negative evidence" not in str(candidate)
    assert world["students"][2].id not in {row["student_id"] for row in payload["candidates"]}
    assert db.query(AuditLog).filter_by(action="recognition.shortlist.generated", school_id=world["school"].id).count() == 1


def test_safeguard_threshold_selected_categories_reversals_override_and_positive_ranking(client, db, recognition_world):
    world = recognition_world
    cara = world["students"][2]
    db.add(
        Enrolment(
            school_id=world["school"].id,
            student_id=cara.id,
            class_section_id=world["section"].id,
            kind="member",
            valid_from=date(2026, 7, 1),
        )
    )
    add_event(db, world, cara, world["positive"])
    for _ in range(3):
        add_event(db, world, world["students"][0], world["negative"])
        add_event(db, world, world["students"][1], world["negative"])
    for _ in range(2):
        add_event(db, world, cara, world["negative"])
    for _ in range(5):
        add_event(db, world, world["students"][0], world["late"])
    add_event(db, world, world["students"][0], world["negative"], reversed=True)
    db.commit()

    config = create_config(
        client,
        world,
        shortlist_size=3,
        needs_work_safeguard_enabled=True,
        maximum_needs_work_events=3,
        needs_work_category_ids=[world["negative"].id],
    )
    response = client.post(
        "/api/school/recognition/reviews",
        headers=headers(world["admin"], world["school"]),
        json={"config_id": config["id"], "period_end": "2026-08-01"},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    candidates = {row["student_id"]: row for row in payload["candidates"]}
    ava = candidates[world["students"][0].id]
    ben = candidates[world["students"][1].id]
    cara_candidate = candidates[cara.id]

    assert (ava["safeguard_counted_total"], ava["safeguard_excluded"], ava["is_eligible"]) == (4, True, False)
    assert (ben["safeguard_counted_total"], ben["safeguard_excluded"], ben["is_eligible"]) == (3, False, True)
    assert (cara_candidate["safeguard_counted_total"], cara_candidate["safeguard_excluded"], cara_candidate["is_eligible"]) == (2, False, True)
    assert ava["safeguard_category_totals"] == [{"id": world["negative"].id, "label": "Off task", "events": 4}]
    assert (ava["rank"], ben["rank"], cara_candidate["rank"]) == (1, 1, 3)
    assert "internal evidence must not reach certificates" not in str(payload)

    endpoint = f"/api/school/recognition/reviews/{payload['id']}"
    blocked = client.post(
        f"{endpoint}/confirm",
        headers=headers(world["admin"], world["school"]),
        json={"student_id": ava["student_id"]},
    )
    assert blocked.status_code == 422
    assert blocked.json()["detail"] == "Selected student is not eligible under current criteria"
    assert client.post(
        f"{endpoint}/candidates/{ava['id']}/override-safeguard",
        headers=headers(world["admin"], world["school"]),
        json={"reason": " "},
    ).status_code == 422
    overridden = client.post(
        f"{endpoint}/candidates/{ava['id']}/override-safeguard",
        headers=headers(world["admin"], world["school"]),
        json={"reason": "Staff reviewed the full context"},
    )
    assert overridden.status_code == 200, overridden.text
    assert overridden.json()["safeguard_overridden"] is True
    assert overridden.json()["is_eligible"] is True
    confirmed = client.post(
        f"{endpoint}/confirm",
        headers=headers(world["admin"], world["school"]),
        json={"student_id": ava["student_id"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    actions = [
        row.action
        for row in db.query(AuditLog).filter(AuditLog.school_id == world["school"].id).all()
    ]
    assert actions.count("recognition.candidate.safeguard_excluded") == 1
    assert actions.count("recognition.candidate.safeguard_overridden") == 1


def test_safeguard_empty_category_selection_counts_all_needs_work_categories(client, db, recognition_world):
    world = recognition_world
    add_event(db, world, world["students"][0], world["late"])
    db.commit()
    config = create_config(
        client,
        world,
        needs_work_safeguard_enabled=True,
        maximum_needs_work_events=1,
        needs_work_category_ids=[],
    )
    payload = client.post(
        "/api/school/recognition/reviews",
        headers=headers(world["admin"], world["school"]),
        json={"config_id": config["id"], "period_end": "2026-08-01"},
    ).json()
    ava = next(row for row in payload["candidates"] if row["student_id"] == world["students"][0].id)
    assert payload["criteria"]["needs_work_safeguard"]["category_filter"] == "all_needs_work"
    assert ava["safeguard_counted_total"] == 2
    assert {row["label"] for row in ava["safeguard_category_totals"]} == {"Off task", "Late for class"}
    assert ava["safeguard_excluded"] is True


def test_exclusion_confirmation_duplicate_prevention_and_audited_correction(client, db, recognition_world):
    world = recognition_world
    config = create_config(client, world)
    endpoint = "/api/school/recognition/reviews"
    first = client.post(endpoint, headers=headers(world["admin"], world["school"]), json={"config_id": config["id"], "period_end": "2026-07-31"}).json()
    excluded = first["candidates"][0]
    exclusion = client.post(
        f"{endpoint}/{first['id']}/candidates/{excluded['id']}/exclude",
        headers=headers(world["admin"], world["school"]),
        json={"reason": "Not available for the presentation"},
    )
    assert exclusion.status_code == 200 and exclusion.json()["is_excluded"] is True
    assert client.post(f"{endpoint}/{first['id']}/confirm", headers=headers(world["admin"], world["school"]), json={"student_id": excluded["student_id"]}).status_code == 422
    selected = first["candidates"][1]
    confirmed = client.post(
        f"{endpoint}/{first['id']}/confirm",
        headers=headers(world["admin"], world["school"]),
        json={"student_id": selected["student_id"], "citation": "For consistent kindness."},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["selected_candidate"]["class_name"] == "Grade 5 A"

    second = client.post(endpoint, headers=headers(world["admin"], world["school"]), json={"config_id": config["id"], "period_end": "2026-07-31"}).json()
    duplicate = client.post(f"{endpoint}/{second['id']}/confirm", headers=headers(world["admin"], world["school"]), json={"student_id": second["candidates"][0]["student_id"]})
    assert duplicate.status_code == 409
    revoked = client.post(f"{endpoint}/{first['id']}/revoke", headers=headers(world["admin"], world["school"]), json={"reason": "Correcting the recorded recipient"})
    assert revoked.status_code == 200 and revoked.json()["status"] == "revoked"
    corrected = client.post(f"{endpoint}/{second['id']}/confirm", headers=headers(world["admin"], world["school"]), json={"student_id": second["candidates"][0]["student_id"]})
    assert corrected.status_code == 200 and corrected.json()["status"] == "confirmed"
    assert db.query(StudentRecognitionReview).filter_by(school_id=world["school"].id, status="revoked").count() == 1
    assert db.query(StudentRecognitionReview).filter_by(school_id=world["school"].id, status="confirmed").count() == 1
    assert db.query(StudentRecognitionCandidate).filter_by(review_id=first["id"], is_excluded=True).count() == 1
    actions = {row.action for row in db.query(AuditLog).filter(AuditLog.school_id == world["school"].id).all()}
    assert {"recognition.candidate.excluded", "recognition.review.confirmed", "recognition.review.revoked"} <= actions


def test_review_detail_and_lists_cannot_cross_school_boundary(client, recognition_world):
    world = recognition_world
    config = create_config(client, world)
    review = client.post("/api/school/recognition/reviews", headers=headers(world["admin"], world["school"]), json={"config_id": config["id"], "period_end": "2026-07-31"}).json()
    assert client.get(f"/api/school/recognition/reviews/{review['id']}", headers=headers(world["outsider"], world["other_school"])).status_code == 404
    assert client.get("/api/school/recognition/reviews", headers=headers(world["outsider"], world["other_school"])).json() == {"reviews": []}
    detail = client.get(f"/api/school/recognition/reviews/{review['id']}", headers=headers(world["admin"], world["school"])).json()
    assert detail["school"] == {"name": "Alpha School", "name_ar": None, "logo_url": None}
    assert "private negative evidence" not in str(detail)

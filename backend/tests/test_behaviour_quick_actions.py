import os

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
from app.models_school import BehaviourCategory, BehaviourEvent, GuardianLink, Membership, School, Student, User


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


def headers(user, school=None):
    result = {"Authorization": f"Bearer {auth.create_access_token({'sub': user.email})}"}
    if school:
        result["X-School-Id"] = str(school.id)
    return result


@pytest.fixture
def world(db):
    alpha = School(name="Alpha", slug="alpha", status="active")
    beta = School(name="Beta", slug="beta", status="active")
    admin = User(email="admin@alpha.test", name="Admin")
    teacher = User(email="teacher@alpha.test", name="Teacher")
    guardian = User(email="guardian@alpha.test", name="Guardian")
    outsider = User(email="outsider@test", name="Outsider")
    db.add_all([alpha, beta, admin, teacher, guardian, outsider])
    db.flush()
    db.add_all([
        Membership(school_id=alpha.id, user_id=admin.id, role="school_admin"),
        Membership(school_id=alpha.id, user_id=teacher.id, role="teacher"),
    ])
    student = Student(school_id=alpha.id, first_name="Amina", last_name="Ali", status="active")
    db.add(student)
    db.flush()
    db.add(GuardianLink(school_id=alpha.id, student_id=student.id, user_id=guardian.id, status="active"))
    db.commit()
    return locals()


def add_category(db, school_id, category_type, label, points_value, sort_order, *, active=True):
    category = BehaviourCategory(
        school_id=school_id,
        type=category_type,
        label=label,
        points_value=points_value,
        sort_order=sort_order,
        active=active,
    )
    db.add(category)
    db.flush()
    return category


def configure(client, world, positive_ids, needs_work_ids):
    return client.put(
        "/api/school/behaviour/quick-actions",
        headers=headers(world["admin"], world["alpha"]),
        json={"positive_category_ids": positive_ids, "needs_work_category_ids": needs_work_ids},
    )


def test_admin_configures_ordered_lists_and_teacher_receives_quick_and_other_actions(db, client, world):
    w = world
    good_work = add_category(db, w["alpha"].id, "positive", "Good work", 1, 20)
    kindness = add_category(db, w["alpha"].id, "positive", "Kindness", 2, 10)
    teamwork = add_category(db, w["alpha"].id, "positive", "Teamwork", 1, 30)
    listening = add_category(db, w["alpha"].id, "needs_work", "Not listening", -1, 20)
    unsafe = add_category(db, w["alpha"].id, "needs_work", "Unsafe behaviour", -2, 10)
    db.commit()

    response = configure(client, w, [good_work.id, kindness.id], [listening.id, unsafe.id])
    assert response.status_code == 200
    saved = {row["id"]: row for row in response.json()["categories"]}
    assert saved[good_work.id]["is_quick_action"] is True and saved[good_work.id]["quick_action_order"] == 1
    assert saved[kindness.id]["is_quick_action"] is True and saved[kindness.id]["quick_action_order"] == 2
    assert saved[teamwork.id]["is_quick_action"] is False and saved[teamwork.id]["quick_action_order"] is None

    response = client.get(f"/api/teach/behaviour/quick-actions?school_id={w['alpha'].id}", headers=headers(w["teacher"]))
    assert response.status_code == 200
    payload = response.json()
    assert payload["quick_actions"]["positive"] == [
        {"id": good_work.id, "label": "Good work", "points_value": 1},
        {"id": kindness.id, "label": "Kindness", "points_value": 2},
    ]
    assert payload["quick_actions"]["needs_work"] == [
        {"id": listening.id, "label": "Not listening", "points_value": -1},
        {"id": unsafe.id, "label": "Unsafe behaviour", "points_value": -2},
    ]
    assert payload["other_actions"]["positive"] == [{"id": teamwork.id, "label": "Teamwork", "points_value": 1}]
    assert payload["other_actions"]["needs_work"] == []


def test_quick_action_configuration_rejects_invalid_ids_and_permissions(db, client, world):
    w = world
    positive = add_category(db, w["alpha"].id, "positive", "Positive", 1, 10)
    negative = add_category(db, w["alpha"].id, "needs_work", "Negative", -1, 10)
    inactive = add_category(db, w["alpha"].id, "positive", "Inactive", 1, 20, active=False)
    foreign = add_category(db, w["beta"].id, "positive", "Foreign", 1, 10)
    extras = [add_category(db, w["alpha"].id, "positive", f"Extra {index}", 1, index + 30) for index in range(7)]
    db.commit()

    endpoint = "/api/school/behaviour/quick-actions"
    body = {"positive_category_ids": [positive.id], "needs_work_category_ids": []}
    assert client.put(endpoint, headers=headers(w["teacher"], w["alpha"]), json=body).status_code == 403
    assert client.put(endpoint, headers=headers(w["guardian"], w["alpha"]), json=body).status_code == 403
    assert client.put(endpoint, headers=headers(w["outsider"], w["alpha"]), json=body).status_code == 403
    assert configure(client, w, [foreign.id], []).status_code == 422
    assert configure(client, w, [inactive.id], []).status_code == 422
    assert configure(client, w, [negative.id], []).status_code == 422
    assert configure(client, w, [positive.id, positive.id], []).status_code == 422
    assert configure(client, w, [positive.id], [positive.id]).status_code == 422
    assert configure(client, w, [category.id for category in extras], []).status_code == 422


def test_omitted_categories_clear_and_deactivation_removes_quick_actions(db, client, world):
    w = world
    first = add_category(db, w["alpha"].id, "positive", "First", 1, 10)
    second = add_category(db, w["alpha"].id, "positive", "Second", 1, 20)
    db.commit()
    assert configure(client, w, [first.id, second.id], []).status_code == 200
    assert configure(client, w, [second.id], []).status_code == 200
    db.refresh(first)
    db.refresh(second)
    assert (first.is_quick_action, first.quick_action_order) == (False, None)
    assert (second.is_quick_action, second.quick_action_order) == (True, 1)

    response = client.patch(
        f"/api/school/behaviour/categories/{second.id}",
        headers=headers(w["admin"], w["alpha"]),
        json={"active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_quick_action"] is False
    assert response.json()["quick_action_order"] is None
    payload = client.get(f"/api/teach/behaviour/quick-actions?school_id={w['alpha'].id}", headers=headers(w["teacher"])).json()
    assert payload == {
        "quick_actions": {"positive": [], "needs_work": []},
        "other_actions": {"positive": [{"id": first.id, "label": "First", "points_value": 1}], "needs_work": []},
    }


def test_teacher_quick_actions_are_pure_and_school_scoped(db, client, world):
    w = world
    before = db.query(BehaviourCategory).filter_by(school_id=w["alpha"].id).count()
    response = client.get(f"/api/teach/behaviour/quick-actions?school_id={w['alpha'].id}", headers=headers(w["teacher"]))
    assert response.status_code == 200
    assert response.json() == {"quick_actions": {"positive": [], "needs_work": []}, "other_actions": {"positive": [], "needs_work": []}}
    assert db.query(BehaviourCategory).filter_by(school_id=w["alpha"].id).count() == before == 0
    assert client.get(f"/api/teach/behaviour/quick-actions?school_id={w['beta'].id}", headers=headers(w["teacher"])).status_code == 403
    assert client.get(f"/api/teach/behaviour/quick-actions?school_id={w['alpha'].id}", headers=headers(w["guardian"])).status_code == 403
    w["alpha"].status = "suspended"
    db.commit()
    assert client.get(f"/api/teach/behaviour/quick-actions?school_id={w['alpha'].id}", headers=headers(w["teacher"])).status_code == 403


def test_existing_award_endpoint_records_quick_category_and_context_normally(db, client, world):
    w = world
    category = add_category(db, w["alpha"].id, "positive", "Quick praise", 2, 10)
    db.commit()
    assert configure(client, w, [category.id], []).status_code == 200
    response = client.post(
        "/api/teach/behaviour/events",
        headers=headers(w["teacher"]),
        json={"school_id": w["alpha"].id, "student_ids": [w["student"].id], "category_id": category.id, "context_type": "duty", "duty_context": "break"},
    )
    assert response.status_code == 201
    event = db.query(BehaviourEvent).one()
    assert event.category_id == category.id
    assert event.points_delta == 2
    assert event.context_type == "duty" and event.duty_context == "break"

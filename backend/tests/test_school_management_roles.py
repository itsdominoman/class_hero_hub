from datetime import date, timedelta
from uuid import UUID

from app.models_school import (
    BehaviourCategory,
    BehaviourEvent,
    Conversation,
    Department,
    Membership,
    MessagingAuditEvent,
    MessagingPolicyAcknowledgement,
    StaffDepartmentAssignment,
    Student,
    User,
)
from test_messaging_api import (
    _create_teacher_thread,
    _headers,
    _school_world,
    client,
    db,
)


def _add_management_roles(db, world):
    principal_user = User(email=f"principal-{world['school'].slug}@test", name="Priya Principal")
    hod_user = User(email=f"hod-{world['school'].slug}@test", name="Hana HOD")
    second_teacher_user = User(email=f"teacher2-{world['school'].slug}@test", name="Taylor Two")
    support_user = User(email=f"support-{world['school'].slug}@test", name="Sam Support")
    db.add_all([principal_user, hod_user, second_teacher_user, support_user])
    db.flush()
    principal = Membership(school_id=world["school"].id, user_id=principal_user.id, role="principal", status="active")
    hod = Membership(school_id=world["school"].id, user_id=hod_user.id, role="head_of_department", status="active")
    second_teacher = Membership(school_id=world["school"].id, user_id=second_teacher_user.id, role="teacher", status="active")
    support = Membership(school_id=world["school"].id, user_id=support_user.id, role="support_staff", status="active")
    db.add_all([principal, hod, second_teacher, support])
    db.flush()
    department = Department(school_id=world["school"].id, code="ENG", name="English", status="active")
    other_department = Department(school_id=world["school"].id, code="SCI", name="Science", status="active")
    db.add_all([department, other_department])
    db.flush()
    db.add_all(
        [
            StaffDepartmentAssignment(
                school_id=world["school"].id,
                department_id=department.id,
                membership_id=hod.id,
                responsibility="head",
                valid_from=date.today() - timedelta(days=10),
            ),
            StaffDepartmentAssignment(
                school_id=world["school"].id,
                department_id=department.id,
                membership_id=world["teacher"].id,
                responsibility="member",
                valid_from=date.today() - timedelta(days=10),
            ),
            StaffDepartmentAssignment(
                school_id=world["school"].id,
                department_id=other_department.id,
                membership_id=second_teacher.id,
                responsibility="member",
                valid_from=date.today() - timedelta(days=10),
            ),
        ]
    )
    db.commit()
    return {
        "principal_user": principal_user,
        "principal": principal,
        "hod_user": hod_user,
        "hod": hod,
        "second_teacher_user": second_teacher_user,
        "second_teacher": second_teacher,
        "support_user": support_user,
        "support": support,
        "department": department,
        "other_department": other_department,
    }


def test_staff_messaging_includes_support_and_new_management_roles_but_not_other_schools(db, client):
    world = _school_world(db, "role-messaging")
    other = _school_world(db, "role-messaging-other")
    roles = _add_management_roles(db, world)

    support_headers = _headers(roles["support_user"], world["school"], roles["support"])
    recipients = client.get("/api/messaging/recipients?search=Tea", headers=support_headers)
    assert recipients.status_code == 200, recipients.text
    assert world["teacher"].id in {row["membership_id"] for row in recipients.json()["staff"]}

    created = client.post(
        "/api/messaging/conversations",
        headers=support_headers,
        json={"kind": "staff_direct", "other_staff_membership_id": world["teacher"].id},
    )
    assert created.status_code == 200, created.text
    denied = client.post(
        "/api/messaging/conversations",
        headers=support_headers,
        json={"kind": "staff_direct", "other_staff_membership_id": other["teacher"].id},
    )
    assert denied.status_code == 404


def test_teacher_roster_search_is_scoped_and_covers_identity_assignment_and_department(db, client):
    world = _school_world(db, "teacher-search")
    other = _school_world(db, "teacher-search-other")
    roles = _add_management_roles(db, world)
    admin_headers = _headers(world["users"]["admin"], world["school"], world["admin"])

    def found(query: str) -> set[int]:
        response = client.get("/api/school/teachers", params={"search": query}, headers=admin_headers)
        assert response.status_code == 200, response.text
        return {row["membership_id"] for row in response.json()["teachers"]}

    assert found(world["users"]["teacher"].name_ar) == {world["teacher"].id}
    assert found(world["section"].name) == {world["teacher"].id}
    assert found(roles["department"].name) == {world["teacher"].id}
    assert found(str(world["teacher"].id)) == {world["teacher"].id}
    assert found(world["users"]["teacher"].email.upper()) == {world["teacher"].id}
    assert found("T") == set()
    assert found(other["users"]["teacher"].name) == set()


def test_staff_messaging_policy_acknowledgement_is_versioned_and_user_scoped(db, client):
    world = _school_world(db, "messaging-policy-ack")
    admin_headers = _headers(world["users"]["admin"], world["school"], world["admin"])
    teacher_headers = _headers(world["users"]["teacher"], world["school"], world["teacher"])

    initial = client.get("/api/messaging/policy-acknowledgement", headers=admin_headers)
    assert initial.status_code == 200, initial.text
    policy_version = initial.json()["policy_version"]
    assert initial.json() == {
        "policy_version": policy_version,
        "acknowledged": False,
        "acknowledged_at": None,
    }
    assert client.post(
        "/api/messaging/policy-acknowledgement",
        headers=admin_headers,
        json={"policy_version": policy_version, "acknowledged": False},
    ).status_code == 422
    changed = client.post(
        "/api/messaging/policy-acknowledgement",
        headers=admin_headers,
        json={"policy_version": "obsolete-policy", "acknowledged": True},
    )
    assert changed.status_code == 409
    assert changed.json()["detail"]["current_version"] == policy_version

    recorded = client.post(
        "/api/messaging/policy-acknowledgement",
        headers=admin_headers,
        json={"policy_version": policy_version, "acknowledged": True},
    )
    assert recorded.status_code == 200, recorded.text
    assert recorded.json()["acknowledged"] is True
    assert recorded.json()["acknowledged_at"]
    repeated = client.post(
        "/api/messaging/policy-acknowledgement",
        headers=admin_headers,
        json={"policy_version": policy_version, "acknowledged": True},
    )
    assert repeated.json()["acknowledged_at"] == recorded.json()["acknowledged_at"]
    assert db.query(MessagingPolicyAcknowledgement).count() == 1

    teacher_status = client.get(
        "/api/messaging/policy-acknowledgement",
        headers=teacher_headers,
    )
    assert teacher_status.status_code == 200
    assert teacher_status.json()["acknowledged"] is False


def test_school_admin_department_configuration_enforces_role_and_school_boundaries(db, client):
    world = _school_world(db, "department-admin")
    other = _school_world(db, "department-admin-other")
    roles = _add_management_roles(db, world)
    admin_headers = _headers(world["users"]["admin"], world["school"], world["admin"])

    staff_search = client.get("/api/school/staff?search=Sam", headers=admin_headers)
    assert staff_search.status_code == 200, staff_search.text
    assert [row["membership_id"] for row in staff_search.json()["staff"]] == [roles["support"].id]
    created = client.post(
        "/api/school/departments",
        headers=admin_headers,
        json={"code": "ART", "name": "Arts", "name_ar": "الفنون", "sort_order": 2, "status": "active"},
    )
    assert created.status_code == 201, created.text
    duplicate = client.post(
        "/api/school/departments",
        headers=admin_headers,
        json={"code": "art", "name": "Duplicate", "sort_order": 3, "status": "active"},
    )
    assert duplicate.status_code == 409
    department_id = created.json()["id"]
    wrong_role = client.post(
        f"/api/school/departments/{department_id}/assignments",
        headers=admin_headers,
        json={"membership_id": world["teacher"].id, "responsibility": "head"},
    )
    assert wrong_role.status_code == 422
    cross_school = client.post(
        f"/api/school/departments/{department_id}/assignments",
        headers=admin_headers,
        json={"membership_id": other["teacher"].id, "responsibility": "member"},
    )
    assert cross_school.status_code == 404
    assigned = client.post(
        f"/api/school/departments/{department_id}/assignments",
        headers=admin_headers,
        json={"membership_id": roles["hod"].id, "responsibility": "head"},
    )
    assert assigned.status_code == 201, assigned.text
    listing = client.get("/api/school/departments", headers=admin_headers)
    assert listing.status_code == 200, listing.text
    arts = next(row for row in listing.json() if row["id"] == department_id)
    assert arts["assignments"][0]["staff"]["membership_id"] == roles["hod"].id


def test_hod_reports_are_department_scoped_and_leadership_reports_are_school_wide(db, client):
    world = _school_world(db, "role-reports")
    roles = _add_management_roles(db, world)
    other_student = Student(school_id=world["school"].id, first_name="Zara", last_name="Outside", status="active")
    category = BehaviourCategory(school_id=world["school"].id, type="positive", label="Helpful", points_value=1)
    db.add_all([other_student, category])
    db.flush()
    db.add_all(
        [
            BehaviourEvent(
                school_id=world["school"].id,
                student_id=world["student"].id,
                category_id=category.id,
                actor_user_id=world["users"]["teacher"].id,
                points_delta=1,
                context_type="general",
                source="teacher",
            ),
            BehaviourEvent(
                school_id=world["school"].id,
                student_id=other_student.id,
                category_id=category.id,
                actor_user_id=roles["second_teacher_user"].id,
                points_delta=1,
                context_type="general",
                source="teacher",
            ),
        ]
    )
    db.commit()

    hod_headers = _headers(roles["hod_user"], world["school"], roles["hod"])
    principal_headers = _headers(roles["principal_user"], world["school"], roles["principal"])
    hod_overview = client.get("/api/school/reports/behaviour/overview", headers=hod_headers)
    principal_overview = client.get("/api/school/reports/behaviour/overview", headers=principal_headers)
    assert hod_overview.status_code == 200, hod_overview.text
    assert hod_overview.json()["metrics"]["total_events"] == 1
    assert principal_overview.status_code == 200, principal_overview.text
    assert principal_overview.json()["metrics"]["total_events"] == 2

    denied_filter = client.get(
        f"/api/school/reports/behaviour/overview?actor_user_id={roles['second_teacher_user'].id}",
        headers=hod_headers,
    )
    assert denied_filter.status_code == 422
    context = client.get("/api/school/reports/behaviour/context", headers=hod_headers)
    assert context.status_code == 200, context.text
    assert context.json()["scope"] == {
        "type": "department",
        "departments": [{"id": roles["department"].id, "name": "English", "name_ar": None}],
    }
    assert roles["second_teacher_user"].id not in {row["id"] for row in context.json()["staff"]}
    search = client.get("/api/school/reports/behaviour/students/search?search=Zara", headers=hod_headers)
    assert search.status_code == 200 and search.json() == []


def test_hod_communication_oversight_is_department_scoped_and_audited(db, client):
    world = _school_world(db, "role-oversight")
    roles = _add_management_roles(db, world)
    related_conversation_id = _create_teacher_thread(client, world)
    unrelated = client.post(
        "/api/messaging/conversations",
        headers=_headers(world["users"]["admin"], world["school"], world["admin"]),
        json={"kind": "staff_direct", "other_staff_membership_id": roles["second_teacher"].id},
    )
    assert unrelated.status_code == 200, unrelated.text
    unrelated_conversation_id = unrelated.json()["conversation_id"]

    hod_headers = _headers(roles["hod_user"], world["school"], roles["hod"])
    principal_headers = _headers(roles["principal_user"], world["school"], roles["principal"])
    hod_search = client.get("/api/safeguarding/conversations", headers=hod_headers)
    assert hod_search.status_code == 200, hod_search.text
    assert {row["conversation_id"] for row in hod_search.json()["items"]} == {related_conversation_id}
    principal_search = client.get("/api/safeguarding/conversations", headers=principal_headers)
    assert principal_search.status_code == 200, principal_search.text
    assert {row["conversation_id"] for row in principal_search.json()["items"]} == {
        related_conversation_id,
        unrelated_conversation_id,
    }

    denied_review = client.post(
        "/api/safeguarding/reviews",
        headers=hod_headers,
        json={
            "conversation_id": unrelated_conversation_id,
            "reason_category": "parent_communication_review",
            "justification": "Management review requested for a specific communication concern",
            "acknowledgement": True,
            "ttl_minutes": 30,
        },
    )
    assert denied_review.status_code == 404
    related_review = client.post(
        "/api/safeguarding/reviews",
        headers=hod_headers,
        json={
            "conversation_id": related_conversation_id,
            "reason_category": "parent_communication_review",
            "justification": "Management review requested for a specific communication concern",
            "acknowledgement": True,
            "ttl_minutes": 30,
        },
    )
    assert related_review.status_code == 200, related_review.text
    detail = client.get(
        f"/api/safeguarding/reviews/{related_review.json()['review_session_id']}",
        headers=hod_headers,
    )
    assert detail.status_code == 200, detail.text
    related = db.query(Conversation).filter(Conversation.public_id == UUID(related_conversation_id)).one()
    events = db.query(MessagingAuditEvent).filter(
        MessagingAuditEvent.actor_membership_id == roles["hod"].id,
        MessagingAuditEvent.conversation_id == related.id,
    ).all()
    assert {row.event_type for row in events} >= {
        "safeguarding.review_started",
        "safeguarding.conversation_opened",
    }

import os
import io
import subprocess
from time import perf_counter
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database
from app.database import Base, get_db
from app.main import app
from app.models_school import (
    AcademicYear,
    BranchCampus,
    ClassSection,
    Conversation,
    ConversationAccessGrant,
    ConversationParticipant,
    Enrolment,
    FhhLink,
    FhhLinkInvite,
    FhhMessagingIdentity,
    FhhMessagingIdentityLink,
    GradeLevel,
    GuardianLink,
    Membership,
    Message,
    MessageMedia,
    MessageVoiceMedia,
    School,
    SchoolFeatureControlAuditEvent,
    SchoolMessagingPolicy,
    StaffAssignment,
    Student,
    User,
)
from app import message_media_service, message_voice_service


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine)


@pytest.fixture
def db(monkeypatch):
    database.engine = engine
    database.SessionLocal = Session
    monkeypatch.setattr(database.settings, "MESSAGING_ENABLED", True)
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


def _headers(user, school, membership=None):
    headers = {
        "Authorization": f"Bearer {auth.create_access_token({'sub': user.email})}",
        "X-School-Id": str(school.id),
    }
    if membership is not None:
        headers["X-Membership-Id"] = str(membership.id)
    return headers


def _school_world(db, suffix):
    school = School(name=f"School {suffix}", slug=f"school-{suffix}", status="active")
    users = {
        name: User(
            email=f"{name}-{suffix}@test",
            name=f"{name.title()} {suffix}",
            name_ar=f"{name} عربي",
            google_sub=f"{name}-{suffix}",
        )
        for name in ("admin", "teacher", "guardian", "guardian2")
    }
    db.add_all([school, *users.values()])
    db.flush()
    admin = Membership(
        school_id=school.id,
        user_id=users["admin"].id,
        role="school_admin",
        status="active",
    )
    teacher = Membership(
        school_id=school.id,
        user_id=users["teacher"].id,
        role="teacher",
        status="active",
    )
    branch = BranchCampus(
        school_id=school.id, code=f"B-{suffix}", name="Main", status="active"
    )
    year = AcademicYear(
        school_id=school.id,
        code=f"Y-{suffix}",
        name="Year",
        is_current=True,
        status="active",
    )
    grade = GradeLevel(
        school_id=school.id, code=f"G-{suffix}", name="KG1", name_ar="الروضة الأولى", status="active"
    )
    student = Student(
        school_id=school.id,
        first_name=f"Student {suffix}",
        last_name="Test",
        status="active",
    )
    policy = SchoolMessagingPolicy(school_id=school.id, enabled=True)
    db.add_all([admin, teacher, branch, year, grade, student, policy])
    db.flush()
    section = ClassSection(
        school_id=school.id,
        branch_campus_id=branch.id,
        academic_year_id=year.id,
        grade_level_id=grade.id,
        code=f"C-{suffix}",
        name="KG1A",
        name_ar="الروضة الأولى أ",
        status="active",
    )
    db.add(section)
    db.flush()
    enrolment = Enrolment(
        school_id=school.id,
        student_id=student.id,
        class_section_id=section.id,
        kind="member",
        valid_from=date.today() - timedelta(days=10),
    )
    assignment = StaffAssignment(
        school_id=school.id,
        membership_id=teacher.id,
        class_section_id=section.id,
        role="homeroom",
        valid_from=date.today() - timedelta(days=10),
    )
    links = [
        GuardianLink(
            school_id=school.id,
            student_id=student.id,
            user_id=users[key].id,
            relationship="father" if key == "guardian" else "mother",
            display_name=users[key].name,
            status="active",
        )
        for key in ("guardian", "guardian2")
    ]
    db.add_all([enrolment, assignment, *links])
    db.commit()
    return {
        "school": school,
        "users": users,
        "admin": admin,
        "teacher": teacher,
        "student": student,
        "assignment": assignment,
        "section": section,
        "year": year,
        "grade": grade,
        "links": links,
        "policy": policy,
    }


def _create_teacher_thread(client, world):
    response = client.post(
        "/api/messaging/conversations",
        headers=_headers(
            world["users"]["teacher"], world["school"], world["teacher"]
        ),
        json={"kind": "student_staff", "student_id": world["student"].id},
    )
    assert response.status_code == 200, response.text
    return response.json()["conversation_id"]


def test_messaging_feature_flag_and_school_policy_fail_closed(db, client, monkeypatch):
    world = _school_world(db, "disabled")
    headers = _headers(world["users"]["teacher"], world["school"], world["teacher"])
    world["policy"].enabled = False
    db.commit()
    assert client.get("/api/messaging/inbox", headers=headers).status_code == 404
    world["policy"].enabled = True
    db.commit()
    monkeypatch.setattr(database.settings, "MESSAGING_ENABLED", False)
    assert client.get("/api/messaging/inbox", headers=headers).status_code == 404


def test_shared_guardians_text_send_unread_ack_and_idempotent_retry(db, client):
    world = _school_world(db, "shared")
    conversation_id = _create_teacher_thread(client, world)
    client_message_id = str(uuid4())
    sent = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=_headers(
            world["users"]["teacher"], world["school"], world["teacher"]
        ),
        json={"client_message_id": client_message_id, "body": "Hello guardians"},
    )
    assert sent.status_code == 200 and sent.json()["sequence"] == 1
    assert sent.json()["receipt"]["state"] == "sent"
    retried = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=_headers(
            world["users"]["teacher"], world["school"], world["teacher"]
        ),
        json={"client_message_id": client_message_id, "body": "Hello guardians"},
    )
    assert retried.status_code == 200 and retried.json()["duplicate"] is True
    assert db.query(Message).count() == 1

    for key in ("guardian", "guardian2"):
        headers = _headers(world["users"][key], world["school"])
        inbox = client.get("/api/guardian/messaging/inbox", headers=headers)
        assert inbox.status_code == 200
        assert inbox.json()["items"][0]["unread_count"] == 1
        messages = client.get(
            f"/api/guardian/messaging/conversations/{conversation_id}/messages",
            headers=headers,
        )
        assert messages.status_code == 200
        assert messages.json()["items"][0]["body"] == "Hello guardians"
        ack = client.post(
            f"/api/guardian/messaging/conversations/{conversation_id}/acknowledgements",
            headers=headers,
            json={
                "event_type": "read",
                "through_sequence": 1,
                "client_ack_id": str(uuid4()),
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert ack.status_code == 200
        assert (
            client.get("/api/guardian/messaging/unread-count", headers=headers)
            .json()["total"]
            == 0
        )


def test_incremental_refresh_is_append_only_and_guardian_attribution_is_exact(db, client):
    world = _school_world(db, "incremental")
    conversation_id = _create_teacher_thread(client, world)
    teacher_headers = _headers(
        world["users"]["teacher"], world["school"], world["teacher"]
    )
    guardian_headers = _headers(world["users"]["guardian"], world["school"])

    first = client.post(
        f"/api/guardian/messaging/conversations/{conversation_id}/messages",
        headers=guardian_headers,
        json={"client_message_id": str(uuid4()), "body": "First parent note"},
    )
    assert first.status_code == 200
    assert first.json()["sender_display_name"] == world["users"]["guardian"].name
    assert first.json()["sender_kind"] == "chh_guardian"
    assert first.json()["sender_relationship"] == "father"

    initial = client.get(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=teacher_headers,
    )
    assert initial.status_code == 200
    assert initial.json()["latest_sequence"] == 1
    assert initial.json()["items"][0]["sender_relationship"] == "father"

    second = client.post(
        f"/api/guardian/messaging/conversations/{conversation_id}/messages",
        headers=_headers(world["users"]["guardian2"], world["school"]),
        json={"client_message_id": str(uuid4()), "body": "Second parent note"},
    )
    assert second.status_code == 200
    assert second.json()["sender_relationship"] == "mother"

    incremental = client.get(
        f"/api/messaging/conversations/{conversation_id}/messages?after_sequence=1",
        headers=teacher_headers,
    )
    assert incremental.status_code == 200
    assert incremental.json()["latest_sequence"] == 2
    assert [row["sequence"] for row in incremental.json()["items"]] == [2]
    assert incremental.json()["items"][0]["sender_display_name"] == world["users"]["guardian2"].name
    assert incremental.json()["items"][0]["sender_relationship"] == "mother"

    empty = client.get(
        f"/api/messaging/conversations/{conversation_id}/messages?after_sequence=2",
        headers=teacher_headers,
    )
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert client.get(
        f"/api/messaging/conversations/{conversation_id}/messages?cursor=invalid&after_sequence=1",
        headers=teacher_headers,
    ).status_code == 400


def test_inbox_detail_and_recipient_context_show_current_class_and_guardians(db, client):
    world = _school_world(db, "context")
    conversation_id = _create_teacher_thread(client, world)
    headers = _headers(world["users"]["teacher"], world["school"], world["teacher"])
    inbox = client.get("/api/messaging/inbox", headers=headers)
    assert inbox.status_code == 200
    summary = inbox.json()["items"][0]
    assert summary["student"]["class_label"] == "KG1A"
    assert summary["student"]["grade_label"] == "KG1"
    assert summary["staff_context"] == {
        "relationship": "homeroom_teacher",
        "subjects": [],
    }

    detail = client.get(
        f"/api/messaging/conversations/{conversation_id}", headers=headers
    )
    guardian_details = [
        row for row in detail.json()["participant_details"] if row["side"] == "guardian"
    ]
    assert {(row["display_name"], row["relationship"]) for row in guardian_details} == {
        (world["users"]["guardian"].name, "father"),
        (world["users"]["guardian2"].name, "mother"),
    }

    recipients = client.get("/api/messaging/recipients?q=KG1A", headers=headers)
    assert recipients.status_code == 200
    student = recipients.json()["students"][0]
    assert student["student_id"] == world["student"].id
    assert student["class_label"] == "KG1A"
    assert {(row["display_name"], row["relationship"]) for row in student["guardian_details"]} == {
        (world["users"]["guardian"].name, "father"),
        (world["users"]["guardian2"].name, "mother"),
    }


def test_staff_recipient_resolves_fhh_guardian_and_existing_conversation_idempotently(db, client):
    world = _school_world(db, "fhh-recipient")
    for link in world["links"]:
        link.status = "revoked"
        link.revoked_at = datetime.now(timezone.utc)

    invite = FhhLinkInvite(
        school_id=world["school"].id,
        student_id=world["student"].id,
        token_hash=f"invite-{uuid4()}",
        display_code_last4="4321",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        consumed_at=datetime.now(timezone.utc),
        consumed_by="bob-child",
        created_by_user_id=world["users"]["teacher"].id,
    )
    db.add(invite)
    db.flush()
    fhh_link = FhhLink(
        school_id=world["school"].id,
        student_id=world["student"].id,
        source_invite_id=invite.id,
        link_token_hash=f"link-{uuid4()}",
        fhh_child_ref="bob-child",
    )
    identity = FhhMessagingIdentity(
        school_id=world["school"].id,
        external_subject_ref=uuid4(),
        display_name="Bob's FHH Parent",
        preferred_locale="en",
    )
    db.add_all([fhh_link, identity])
    db.flush()
    db.add(
        FhhMessagingIdentityLink(
            school_id=world["school"].id,
            fhh_link_id=fhh_link.id,
            identity_id=identity.id,
            status="active",
            sync_version=1,
        )
    )
    db.commit()

    conversation_id = _create_teacher_thread(client, world)
    headers = _headers(world["users"]["teacher"], world["school"], world["teacher"])
    recipients = client.get(
        f"/api/messaging/recipients?student_id={world['student'].id}",
        headers=headers,
    )
    assert recipients.status_code == 200
    assert len(recipients.json()["students"]) == 1
    student = recipients.json()["students"][0]
    assert student["guardian_names"] == ["Bob's FHH Parent"]
    assert student["guardian_details"] == [
        {"display_name": "Bob's FHH Parent", "relationship": None}
    ]
    assert student["conversation_id"] == conversation_id

    reopened = client.post(
        "/api/messaging/conversations",
        headers=headers,
        json={"kind": "student_staff", "student_id": world["student"].id},
    )
    assert reopened.status_code == 200
    assert reopened.json()["conversation_id"] == conversation_id
    assert db.query(Conversation).filter(Conversation.kind == "student_staff").count() == 1


def test_guardian_can_create_and_reply_only_for_explicit_link_and_assignment(db, client):
    one = _school_world(db, "one")
    two = _school_world(db, "two")
    guardian_headers = _headers(one["users"]["guardian"], one["school"])
    created = client.post(
        "/api/guardian/messaging/conversations",
        headers=guardian_headers,
        json={
            "kind": "student_staff",
            "student_id": one["student"].id,
            "staff_membership_id": one["teacher"].id,
        },
    )
    assert created.status_code == 200
    conversation_id = created.json()["conversation_id"]
    reply = client.post(
        f"/api/guardian/messaging/conversations/{conversation_id}/messages",
        headers=guardian_headers,
        json={"client_message_id": str(uuid4()), "body": "Parent reply"},
    )
    assert reply.status_code == 200
    swapped = client.post(
        "/api/guardian/messaging/conversations",
        headers=guardian_headers,
        json={
            "kind": "student_staff",
            "student_id": two["student"].id,
            "staff_membership_id": two["teacher"].id,
        },
    )
    assert swapped.status_code == 404

    one["assignment"].valid_to = date.today() - timedelta(days=1)
    db.commit()
    closed_reply = client.post(
        f"/api/guardian/messaging/conversations/{conversation_id}/messages",
        headers=guardian_headers,
        json={"client_message_id": str(uuid4()), "body": "Too late"},
    )
    assert closed_reply.status_code == 409


def test_cross_school_revocation_and_resource_enumeration_are_denied(db, client):
    one = _school_world(db, "scope-one")
    two = _school_world(db, "scope-two")
    conversation_id = _create_teacher_thread(client, one)
    wrong_school = client.get(
        f"/api/messaging/conversations/{conversation_id}",
        headers=_headers(two["users"]["teacher"], two["school"], two["teacher"]),
    )
    assert wrong_school.status_code == 404
    link = one["links"][0]
    link.status = "revoked"
    link.revoked_at = datetime.now(timezone.utc)
    db.commit()
    revoked = client.get(
        f"/api/guardian/messaging/conversations/{conversation_id}",
        headers=_headers(one["users"]["guardian"], one["school"]),
    )
    assert revoked.status_code == 403


def test_signed_message_cursor_is_stable_and_tamper_evident(db, client):
    world = _school_world(db, "cursor")
    conversation_id = _create_teacher_thread(client, world)
    headers = _headers(world["users"]["teacher"], world["school"], world["teacher"])
    for index in range(5):
        assert (
            client.post(
                f"/api/messaging/conversations/{conversation_id}/messages",
                headers=headers,
                json={
                    "client_message_id": str(uuid4()),
                    "body": f"Message {index}",
                },
            ).status_code
            == 200
        )
    first = client.get(
        f"/api/messaging/conversations/{conversation_id}/messages?limit=2",
        headers=headers,
    )
    assert [row["sequence"] for row in first.json()["items"]] == [4, 5]
    cursor = first.json()["next_cursor"]
    client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=headers,
        json={"client_message_id": str(uuid4()), "body": "New arrival"},
    )
    second = client.get(
        f"/api/messaging/conversations/{conversation_id}/messages?limit=2&cursor={cursor}",
        headers=headers,
    )
    assert [row["sequence"] for row in second.json()["items"]] == [2, 3]
    tampered = client.get(
        f"/api/messaging/conversations/{conversation_id}/messages?cursor={cursor}x",
        headers=headers,
    )
    assert tampered.status_code == 400


def test_explicit_membership_context_for_overlapping_staff_roles(db, client):
    world = _school_world(db, "roles")
    admin_teacher = Membership(
        school_id=world["school"].id,
        user_id=world["users"]["admin"].id,
        role="teacher",
        status="active",
    )
    db.add(admin_teacher)
    db.commit()
    ambiguous = client.get(
        "/api/messaging/inbox",
        headers=_headers(world["users"]["admin"], world["school"]),
    )
    assert ambiguous.status_code == 409
    explicit = client.get(
        "/api/messaging/inbox",
        headers=_headers(
            world["users"]["admin"], world["school"], world["admin"]
        ),
    )
    assert explicit.status_code == 200


def test_cookie_auth_send_requires_csrf_but_native_bearer_does_not(db, client):
    world = _school_world(db, "csrf")
    conversation_id = _create_teacher_thread(client, world)
    token = auth.create_access_token({"sub": world["users"]["teacher"].email})
    client.cookies.set("access_token", token)
    missing = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers={
            "X-School-Id": str(world["school"].id),
            "X-Membership-Id": str(world["teacher"].id),
        },
        json={"client_message_id": str(uuid4()), "body": "Cookie send"},
    )
    assert missing.status_code == 403
    csrf = auth.create_csrf_token()
    client.cookies.set(auth.CSRF_COOKIE_NAME, csrf)
    allowed = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers={
            "X-School-Id": str(world["school"].id),
            "X-Membership-Id": str(world["teacher"].id),
            auth.CSRF_HEADER_NAME: csrf,
        },
        json={"client_message_id": str(uuid4()), "body": "Cookie send"},
    )
    assert allowed.status_code == 200


def test_inbox_query_count_is_bounded(db, client):
    world = _school_world(db, "queries")
    conversation_id = _create_teacher_thread(client, world)
    headers = _headers(world["users"]["teacher"], world["school"], world["teacher"])
    client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=headers,
        json={"client_message_id": str(uuid4()), "body": "Bounded"},
    )
    statements = []

    def count(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        response = client.get("/api/messaging/inbox", headers=headers)
    finally:
        event.remove(engine, "before_cursor_execute", count)
    assert response.status_code == 200
    # Current class/grade and staff-role context adds only fixed, set-based
    # roster lookups; the budget must not grow with conversations.
    # Feature capability and attached-voice metadata each add one fixed,
    # set-based select; the budget remains independent of inbox size.
    assert len(statements) <= 28


def test_recipient_search_filters_before_cap_and_searches_guardian_names(db, client):
    world = _school_world(db, "recipient-search")
    late_students = [
        Student(
            school_id=world["school"].id,
            first_name=f"ZZZ Student {index:03d}",
            last_name="Late",
            status="active",
        )
        for index in range(300)
    ]
    db.add_all(late_students)
    db.flush()
    target = late_students[-1]
    target.first_name = "ZZZ Unique Target"
    db.add(
        GuardianLink(
            school_id=world["school"].id,
            student_id=target.id,
            user_id=world["users"]["guardian2"].id,
            relationship="guardian",
            display_name="Rare Guardian Search Name",
            status="active",
        )
    )
    db.commit()
    headers = _headers(world["users"]["admin"], world["school"], world["admin"])

    by_student = client.get(
        "/api/messaging/recipients?q=Unique%20Target",
        headers=headers,
    )
    assert by_student.status_code == 200
    assert [row["student_id"] for row in by_student.json()["students"]] == [
        target.id
    ]

    by_guardian = client.get(
        "/api/messaging/recipients?q=Rare%20Guardian",
        headers=headers,
    )
    assert by_guardian.status_code == 200
    assert [row["student_id"] for row in by_guardian.json()["students"]] == [
        target.id
    ]

    literal_wildcard = client.get(
        "/api/messaging/recipients?q=%25",
        headers=headers,
    )
    assert literal_wildcard.status_code == 200
    assert literal_wildcard.json()["students"] == []


def test_assignment_replacement_archive_school_suspension_and_dual_role(db, client):
    world = _school_world(db, "lifecycle-hardening")
    conversation_id = _create_teacher_thread(client, world)
    teacher_headers = _headers(
        world["users"]["teacher"], world["school"], world["teacher"]
    )
    guardian_headers = _headers(world["users"]["guardian"], world["school"])
    assert client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=teacher_headers,
        json={"client_message_id": str(uuid4()), "body": "Historical message"},
    ).status_code == 200

    replacement_user = User(
        email="replacement-lifecycle-hardening@test",
        name="Replacement Teacher",
        google_sub="replacement-lifecycle-hardening",
    )
    db.add(replacement_user)
    db.flush()
    replacement = Membership(
        school_id=world["school"].id,
        user_id=replacement_user.id,
        role="teacher",
        status="active",
    )
    db.add(replacement)
    db.flush()
    db.add(
        StaffAssignment(
            school_id=world["school"].id,
            membership_id=replacement.id,
            class_section_id=world["assignment"].class_section_id,
            role="homeroom",
            valid_from=date.today(),
        )
    )
    world["assignment"].valid_to = date.today()
    db.commit()

    # Former staff lose participant access; the guardian retains read-only history.
    assert client.get(
        f"/api/messaging/conversations/{conversation_id}",
        headers=teacher_headers,
    ).status_code == 404
    guardian_history = client.get(
        f"/api/guardian/messaging/conversations/{conversation_id}",
        headers=guardian_headers,
    )
    assert guardian_history.status_code == 200
    assert guardian_history.json()["read_only"] is True

    replacement_headers = _headers(
        replacement_user, world["school"], replacement
    )
    assert client.get(
        f"/api/messaging/conversations/{conversation_id}",
        headers=replacement_headers,
    ).status_code == 404
    replacement_thread = client.post(
        "/api/messaging/conversations",
        headers=replacement_headers,
        json={"kind": "student_staff", "student_id": world["student"].id},
    )
    assert replacement_thread.status_code == 200
    assert replacement_thread.json()["conversation_id"] != conversation_id

    # Archiving the student closes current teacher access without reassignment.
    world["student"].status = "archived"
    db.commit()
    assert client.get(
        "/api/messaging/inbox", headers=replacement_headers
    ).json()["items"] == []

    # A suspended school fails closed for every ordinary actor.
    world["school"].status = "suspended"
    db.commit()
    assert client.get("/api/messaging/inbox", headers=replacement_headers).status_code == 403
    assert client.get(
        "/api/guardian/messaging/inbox", headers=guardian_headers
    ).status_code == 403

    # One user may hold school-admin and guardian identities, but the route/context
    # selects the actor explicitly rather than merging permissions.
    world["school"].status = "active"
    world["student"].status = "active"
    db.add(
        GuardianLink(
            school_id=world["school"].id,
            student_id=world["student"].id,
            user_id=world["users"]["admin"].id,
            relationship="guardian",
            display_name="Admin Parent",
            status="active",
        )
    )
    db.commit()
    assert client.get(
        "/api/messaging/inbox",
        headers=_headers(
            world["users"]["admin"], world["school"], world["admin"]
        ),
    ).status_code == 200
    assert client.get(
        "/api/guardian/messaging/inbox",
        headers=_headers(world["users"]["admin"], world["school"]),
    ).status_code == 200


def test_pending_setup_school_is_eligible_but_archived_school_fails_closed(db, client):
    world = _school_world(db, "pending-setup")
    admin_headers = _headers(
        world["users"]["admin"], world["school"], world["admin"]
    )
    guardian_headers = _headers(world["users"]["guardian"], world["school"])

    world["school"].status = "pending_setup"
    db.commit()
    assert client.get(
        "/api/messaging/unread-count", headers=admin_headers
    ).status_code == 200
    assert client.get(
        "/api/guardian/messaging/unread-count", headers=guardian_headers
    ).status_code == 200

    world["school"].status = "archived"
    db.commit()
    assert client.get(
        "/api/messaging/unread-count", headers=admin_headers
    ).status_code == 403
    assert client.get(
        "/api/guardian/messaging/unread-count", headers=guardian_headers
    ).status_code == 403


def test_representative_inbox_unread_and_history_are_bounded_and_fast(db, client):
    world = _school_world(db, "performance")
    section_id = world["assignment"].class_section_id
    students = [
        Student(
            school_id=world["school"].id,
            first_name=f"Perf {index:03d}",
            last_name="Student",
            status="active",
        )
        for index in range(100)
    ]
    db.add_all(students)
    db.flush()
    db.add_all(
        [
            Enrolment(
                school_id=world["school"].id,
                student_id=student.id,
                class_section_id=section_id,
                kind="member",
                valid_from=date.today() - timedelta(days=1),
            )
            for student in students
        ]
    )
    conversations = [
        Conversation(
            school_id=world["school"].id,
            kind="student_staff",
            student_id=student.id,
            primary_staff_membership_id=world["teacher"].id,
        )
        for student in students
    ]
    db.add_all(conversations)
    db.flush()
    participants = [
        ConversationParticipant(
            conversation_id=conversation.id,
            participant_kind="staff",
            user_id=world["users"]["teacher"].id,
            membership_id=world["teacher"].id,
            side="staff",
            display_name_snapshot=world["users"]["teacher"].name,
        )
        for conversation in conversations
    ]
    db.add_all(participants)
    db.flush()
    db.add_all(
        [
            ConversationAccessGrant(
                conversation_id=conversation.id,
                participant_id=participant.id,
                source_type="staff_assignment",
                staff_assignment_id=world["assignment"].id,
                grant_reason="performance_fixture",
            )
            for conversation, participant in zip(conversations, participants)
        ]
    )
    db.commit()
    headers = _headers(world["users"]["teacher"], world["school"], world["teacher"])

    selects: list[str] = []

    def count_selects(_conn, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    event.listen(engine, "before_cursor_execute", count_selects)
    try:
        inbox = client.get("/api/messaging/inbox?limit=50", headers=headers)
    finally:
        event.remove(engine, "before_cursor_execute", count_selects)
    assert inbox.status_code == 200
    assert len(inbox.json()["items"]) == 50
    inbox_select_count = len(selects)
    assert inbox_select_count <= 26

    selects.clear()
    event.listen(engine, "before_cursor_execute", count_selects)
    try:
        unread = client.get("/api/messaging/unread-count", headers=headers)
    finally:
        event.remove(engine, "before_cursor_execute", count_selects)
    assert unread.status_code == 200
    unread_select_count = len(selects)
    assert unread_select_count <= 20

    target_conversation = conversations[0]
    target_participant = participants[0]
    db.add_all(
        [
            Message(
                school_id=world["school"].id,
                conversation_id=target_conversation.id,
                sequence=sequence,
                sender_participant_id=target_participant.id,
                sender_display_name_snapshot=target_participant.display_name_snapshot,
                client_message_id=uuid4(),
                body=f"Performance message {sequence}",
            )
            for sequence in range(1, 101)
        ]
    )
    target_conversation.last_message_sequence = 100
    target_conversation.last_message_at = datetime.now(timezone.utc)
    db.commit()
    selects.clear()
    event.listen(engine, "before_cursor_execute", count_selects)
    try:
        history = client.get(
            f"/api/messaging/conversations/{target_conversation.public_id}/messages"
            "?limit=50",
            headers=headers,
        )
    finally:
        event.remove(engine, "before_cursor_execute", count_selects)
    assert history.status_code == 200
    assert [row["sequence"] for row in history.json()["items"]] == list(
        range(51, 101)
    )
    history_select_count = len(selects)
    # Slice 8 adds exactly one set-based attachment metadata query for the whole
    # page. The budget remains fixed as message/photo population grows.
    # Voice-note metadata adds one fixed set-based select for the page. Slice 9
    # adds one more fixed receipt aggregation select for all 50 messages; the
    # budget remains independent of message and participant counts.
    assert history_select_count <= 28

    durations_ms = []
    for _ in range(12):
        started = perf_counter()
        assert client.get(
            "/api/messaging/inbox?limit=50", headers=headers
        ).status_code == 200
        durations_ms.append((perf_counter() - started) * 1000)
    p95_ms = sorted(durations_ms)[int(len(durations_ms) * 0.95) - 1]
    print(
        "messaging_perf "
        f"conversations=100 inbox_selects={inbox_select_count} "
        f"unread_selects={unread_select_count} "
        f"history_selects={history_select_count} inbox_p95_ms={p95_ms:.2f}"
    )
    # This is a regression tripwire, not a production SLO. The documented measured
    # value is expected to be much lower on the disposable development database.
    assert p95_ms < 1000


def _jpeg_bytes(*, size=(96, 64), exif_gps=False):
    image = Image.new("RGB", size, (32, 120, 210))
    output = io.BytesIO()
    exif = Image.Exif()
    if exif_gps:
        exif[0x010E] = "private description"
        exif[0x0112] = 6
    image.save(output, "JPEG", exif=exif)
    return output.getvalue()


def test_protected_photo_upload_attach_serve_scope_and_cleanup(
    db, client, monkeypatch, tmp_path
):
    monkeypatch.setattr(message_media_service, "MESSAGE_MEDIA_ROOT", tmp_path)
    one = _school_world(db, "media-one")
    two = _school_world(db, "media-two")
    conversation_id = _create_teacher_thread(client, one)
    teacher_headers = _headers(one["users"]["teacher"], one["school"], one["teacher"])
    guardian_headers = _headers(one["users"]["guardian"], one["school"])
    raw = _jpeg_bytes(exif_gps=True)
    upload_id = str(uuid4())

    uploaded = client.post(
        f"/api/messaging/conversations/{conversation_id}/media",
        headers={**teacher_headers, "X-Upload-Id": upload_id},
        files={"file": ("spoofed.txt", raw, "text/plain")},
    )
    assert uploaded.status_code == 201, uploaded.text
    staged = uploaded.json()
    assert staged["state"] == "ready"
    assert staged["duplicate"] is False
    assert staged["thumbnail_available"] is False
    assert staged["full_available"] is False

    retried = client.post(
        f"/api/messaging/conversations/{conversation_id}/media",
        headers={**teacher_headers, "X-Upload-Id": upload_id},
        files={"file": ("anything.png", raw, "image/png")},
    )
    assert retried.status_code == 201
    assert retried.json()["id"] == staged["id"]
    assert retried.json()["duplicate"] is True

    stolen = client.post(
        f"/api/guardian/messaging/conversations/{conversation_id}/messages",
        headers=guardian_headers,
        json={
            "client_message_id": str(uuid4()),
            "body": None,
            "staged_media_ids": [staged["id"]],
        },
    )
    assert stolen.status_code == 409

    sent_id = str(uuid4())
    sent = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=teacher_headers,
        json={
            "client_message_id": sent_id,
            "body": None,
            "staged_media_ids": [staged["id"]],
        },
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["body"] is None
    assert sent.json()["receipt"]["state"] == "sent"
    assert [photo["id"] for photo in sent.json()["photos"]] == [staged["id"]]
    assert sent.json()["photos"][0]["thumbnail_available"] is True

    duplicate_send = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=teacher_headers,
        json={
            "client_message_id": sent_id,
            "body": None,
            "staged_media_ids": [staged["id"]],
        },
    )
    assert duplicate_send.status_code == 200
    assert duplicate_send.json()["duplicate"] is True

    history = client.get(
        f"/api/guardian/messaging/conversations/{conversation_id}/messages",
        headers=guardian_headers,
    )
    assert history.status_code == 200
    assert history.json()["items"][0]["body"] is None
    assert history.json()["items"][0]["photos"][0]["id"] == staged["id"]

    for variant in ("thumbnail", "full"):
        media = client.get(
            f"/api/guardian/messaging/conversations/{conversation_id}/media/{staged['id']}/{variant}",
            headers=guardian_headers,
        )
        assert media.status_code == 200
        assert media.headers["cache-control"] == "private, no-store, max-age=0"
        assert media.headers["x-content-type-options"] == "nosniff"
        assert media.headers["content-type"] in {"image/jpeg", "image/webp"}
        decoded = Image.open(io.BytesIO(media.content))
        assert not decoded.getexif()
        assert max(decoded.size) <= (400 if variant == "thumbnail" else 1600)

    wrong_school = client.get(
        f"/api/messaging/conversations/{conversation_id}/media/{staged['id']}/thumbnail",
        headers=_headers(two["users"]["teacher"], two["school"], two["teacher"]),
    )
    assert wrong_school.status_code == 404

    corrupt = client.post(
        f"/api/messaging/conversations/{conversation_id}/media",
        headers={**teacher_headers, "X-Upload-Id": str(uuid4())},
        files={"file": ("fake.jpg", b"not an image", "image/jpeg")},
    )
    assert corrupt.status_code == 400
    text_after_failure = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=teacher_headers,
        json={"client_message_id": str(uuid4()), "body": "Text still works"},
    )
    assert text_after_failure.status_code == 200

    abandoned_upload_id = str(uuid4())
    abandoned = client.post(
        f"/api/messaging/conversations/{conversation_id}/media",
        headers={**teacher_headers, "X-Upload-Id": abandoned_upload_id},
        files={"file": ("photo.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert abandoned.status_code == 201
    abandoned_row = (
        db.query(MessageMedia)
        .filter(MessageMedia.public_id == UUID(abandoned.json()["id"]))
        .first()
    )
    abandoned_row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert message_media_service.cleanup_expired_staged_media(db, limit=10) == 1
    db.refresh(abandoned_row)
    assert abandoned_row.state == "expired"
    assert abandoned_row.full_storage_key is None
    assert abandoned_row.thumbnail_storage_key is None

    stored_files = [path for path in tmp_path.rglob("*") if path.is_file()]
    # Only the one attached photo's two metadata-free derivatives remain.
    assert len(stored_files) == 2
    assert all(path.read_bytes() != raw for path in stored_files)

    too_many = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=teacher_headers,
        json={
            "client_message_id": str(uuid4()),
            "body": "too many",
            "staged_media_ids": [str(uuid4()) for _ in range(6)],
        },
    )
    assert too_many.status_code == 422


def _voice_tone_bytes(tmp_path, *, duration=1.1, frequency=523):
    target = tmp_path / f"tone-{duration}-{frequency}.wav"
    result = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency}:sample_rate=44100",
            "-t",
            str(duration),
            str(target),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    return target.read_bytes()


def test_voice_feature_control_upload_attach_playback_scope_retry_and_cleanup(
    db, client, monkeypatch, tmp_path
):
    media_root = tmp_path / "protected-message-media"
    monkeypatch.setattr(message_media_service, "MESSAGE_MEDIA_ROOT", media_root)
    monkeypatch.setattr(message_voice_service, "MESSAGE_MEDIA_ROOT", media_root)
    one = _school_world(db, "voice-one")
    two = _school_world(db, "voice-two")
    conversation_id = _create_teacher_thread(client, one)
    admin_headers = _headers(one["users"]["admin"], one["school"], one["admin"])
    teacher_headers = _headers(one["users"]["teacher"], one["school"], one["teacher"])
    guardian_headers = _headers(one["users"]["guardian"], one["school"])

    controls = client.get("/api/school/feature-controls", headers=admin_headers)
    assert controls.status_code == 200, controls.text
    assert controls.json()["voice_notes"]["enabled"] is False
    assert controls.json()["voice_notes"]["control_version"] == 1
    raw = _voice_tone_bytes(tmp_path)
    disabled_upload = client.post(
        f"/api/messaging/conversations/{conversation_id}/voice-media",
        headers={**teacher_headers, "X-Upload-Id": str(uuid4())},
        files={"file": ("voice.bin", raw, "application/octet-stream")},
    )
    assert disabled_upload.status_code == 403

    disclosure = controls.json()["voice_notes"]["disclosure_version"]
    missing_ack = client.put(
        "/api/school/feature-controls/voice-notes",
        headers=admin_headers,
        json={
            "enabled": True,
            "expected_control_version": 1,
            "disclosure_version": disclosure,
            "acknowledged": False,
        },
    )
    assert missing_ack.status_code == 422
    enabled = client.put(
        "/api/school/feature-controls/voice-notes",
        headers=admin_headers,
        json={
            "enabled": True,
            "expected_control_version": 1,
            "disclosure_version": disclosure,
            "acknowledged": True,
        },
    )
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["enabled"] is True
    assert enabled.json()["control_version"] == 2
    audit = db.query(SchoolFeatureControlAuditEvent).one()
    assert audit.enabled is True
    assert audit.acknowledging_user_id == one["users"]["admin"].id
    assert audit.acknowledging_membership_id == one["admin"].id
    assert audit.disclosure_version == disclosure

    upload_id = str(uuid4())
    uploaded = client.post(
        f"/api/messaging/conversations/{conversation_id}/voice-media",
        headers={**teacher_headers, "X-Upload-Id": upload_id},
        files={"file": ("spoofed-video.mp4", raw, "video/mp4")},
    )
    assert uploaded.status_code == 201, uploaded.text
    staged = uploaded.json()
    assert staged["state"] == "ready"
    assert staged["content_type"] == "audio/mp4"
    assert staged["codec"] == "aac"
    assert staged["container"] == "mp4"
    assert 1_000 <= staged["duration_ms"] <= 1_200
    assert staged["available"] is False
    assert staged["transcription"] == {"available": False, "state": "not_requested"}

    retried = client.post(
        f"/api/messaging/conversations/{conversation_id}/voice-media",
        headers={**teacher_headers, "X-Upload-Id": upload_id},
        files={"file": ("same.webm", raw, "audio/webm")},
    )
    assert retried.status_code == 201
    assert retried.json()["id"] == staged["id"]
    assert retried.json()["duplicate"] is True
    conflict = client.post(
        f"/api/messaging/conversations/{conversation_id}/voice-media",
        headers={**teacher_headers, "X-Upload-Id": upload_id},
        files={"file": ("different.wav", _voice_tone_bytes(tmp_path, frequency=660), "audio/wav")},
    )
    assert conflict.status_code == 409

    stolen = client.post(
        f"/api/guardian/messaging/conversations/{conversation_id}/messages",
        headers=guardian_headers,
        json={
            "client_message_id": str(uuid4()),
            "body": None,
            "staged_voice_id": staged["id"],
        },
    )
    assert stolen.status_code == 409
    other_student = Student(
        school_id=one["school"].id,
        first_name="Other",
        last_name="Student",
        status="active",
    )
    db.add(other_student)
    db.flush()
    db.add(
        Enrolment(
            school_id=one["school"].id,
            student_id=other_student.id,
            class_section_id=one["section"].id,
            kind="member",
            valid_from=date.today() - timedelta(days=1),
        )
    )
    db.add(
        GuardianLink(
            school_id=one["school"].id,
            student_id=other_student.id,
            user_id=one["users"]["guardian2"].id,
            relationship="mother",
            display_name=one["users"]["guardian2"].name,
            status="active",
        )
    )
    db.commit()
    other_conversation = client.post(
        "/api/messaging/conversations",
        headers=teacher_headers,
        json={
            "kind": "student_staff",
            "student_id": other_student.id,
        },
    )
    assert other_conversation.status_code == 200
    moved = client.post(
        f"/api/messaging/conversations/{other_conversation.json()['conversation_id']}/messages",
        headers=teacher_headers,
        json={
            "client_message_id": str(uuid4()),
            "body": None,
            "staged_voice_id": staged["id"],
        },
    )
    assert moved.status_code == 409

    client_message_id = str(uuid4())
    sent = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=teacher_headers,
        json={
            "client_message_id": client_message_id,
            "body": None,
            "staged_voice_id": staged["id"],
        },
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["message_type"] == "voice_note"
    assert sent.json()["body"] is None
    assert sent.json()["receipt"]["state"] == "sent"
    assert sent.json()["photos"] == []
    assert sent.json()["voice_note"]["id"] == staged["id"]
    assert sent.json()["voice_note"]["available"] is True
    duplicate_send = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=teacher_headers,
        json={
            "client_message_id": client_message_id,
            "body": None,
            "staged_voice_id": staged["id"],
        },
    )
    assert duplicate_send.status_code == 200
    assert duplicate_send.json()["duplicate"] is True
    assert db.query(Message).filter(Message.message_type == "voice_note").count() == 1

    history = client.get(
        f"/api/guardian/messaging/conversations/{conversation_id}/messages",
        headers=guardian_headers,
    )
    assert history.status_code == 200
    assert history.json()["items"][0]["voice_note"]["id"] == staged["id"]
    played = client.get(
        f"/api/guardian/messaging/conversations/{conversation_id}/voice-media/{staged['id']}",
        headers=guardian_headers,
    )
    assert played.status_code == 200
    assert played.headers["content-type"].startswith("audio/mp4")
    assert played.headers["cache-control"] == "private, no-store, max-age=0"
    assert played.content != raw
    wrong_school = client.get(
        f"/api/messaging/conversations/{conversation_id}/voice-media/{staged['id']}",
        headers=_headers(two["users"]["teacher"], two["school"], two["teacher"]),
    )
    assert wrong_school.status_code == 404

    second = client.post(
        f"/api/messaging/conversations/{conversation_id}/voice-media",
        headers={**teacher_headers, "X-Upload-Id": str(uuid4())},
        files={"file": ("voice.wav", raw, "audio/wav")},
    )
    assert second.status_code == 201
    combined = client.post(
        f"/api/messaging/conversations/{conversation_id}/messages",
        headers=teacher_headers,
        json={
            "client_message_id": str(uuid4()),
            "body": "Voice notes are their own message",
            "staged_voice_id": second.json()["id"],
        },
    )
    assert combined.status_code == 422
    malformed = client.post(
        f"/api/messaging/conversations/{conversation_id}/voice-media",
        headers={**teacher_headers, "X-Upload-Id": str(uuid4())},
        files={"file": ("not-audio.m4a", b"not audio", "audio/mp4")},
    )
    assert malformed.status_code == 422
    short = client.post(
        f"/api/messaging/conversations/{conversation_id}/voice-media",
        headers={**teacher_headers, "X-Upload-Id": str(uuid4())},
        files={"file": ("short.wav", _voice_tone_bytes(tmp_path, duration=0.2), "audio/wav")},
    )
    assert short.status_code == 422

    disabled = client.put(
        "/api/school/feature-controls/voice-notes",
        headers=admin_headers,
        json={
            "enabled": False,
            "expected_control_version": 2,
            "disclosure_version": disclosure,
            "acknowledged": True,
        },
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    assert db.query(SchoolFeatureControlAuditEvent).count() == 2
    assert client.get(
        f"/api/guardian/messaging/conversations/{conversation_id}/voice-media/{staged['id']}",
        headers=guardian_headers,
    ).status_code == 200
    assert client.post(
        f"/api/messaging/conversations/{conversation_id}/voice-media",
        headers={**teacher_headers, "X-Upload-Id": str(uuid4())},
        files={"file": ("disabled.wav", raw, "audio/wav")},
    ).status_code == 403

    abandoned = db.query(MessageVoiceMedia).filter(
        MessageVoiceMedia.public_id == UUID(second.json()["id"])
    ).one()
    abandoned.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert message_voice_service.cleanup_expired_staged_voice(db, limit=10) >= 1
    db.refresh(abandoned)
    assert abandoned.state == "expired"
    assert abandoned.storage_key is None

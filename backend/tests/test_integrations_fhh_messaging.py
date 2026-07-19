import os
import base64
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database, invite_tokens
from app.database import Base, get_db
from app.fhh_messaging_assertions import canonical_body_hash
from app.main import app
from app.models_school import (
    AcademicYear,
    BranchCampus,
    ClassSection,
    Conversation,
    ConversationParticipant,
    Enrolment,
    FhhLink,
    FhhLinkInvite,
    FhhMessagingAssertionUse,
    FhhMessagingIdentity,
    FhhMessagingIdentityLink,
    GradeLevel,
    Membership,
    Message,
    School,
    SchoolMessagingPolicy,
    StaffAssignment,
    Student,
    Subject,
    SubjectGroup,
    User,
)
from app.routes import integrations_fhh


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine)
SERVICE_TOKEN = "service-" + ("s" * 40)
ASSERTION_SECRET = "assertion-" + ("a" * 40)


@pytest.fixture
def db(monkeypatch):
    database.engine = engine
    database.SessionLocal = Session
    monkeypatch.setattr(database.settings, "FHH_INTEGRATION_ENABLED", True)
    monkeypatch.setattr(
        database.settings, "FHH_INTEGRATION_SERVICE_TOKEN", SERVICE_TOKEN
    )
    monkeypatch.setattr(database.settings, "FHH_INTEGRATION_ALLOWED_IPS", "")
    monkeypatch.setattr(database.settings, "MESSAGING_ENABLED", True)
    monkeypatch.setattr(
        database.settings, "FHH_MESSAGING_ASSERTION_SECRET", ASSERTION_SECRET
    )
    integrations_fhh.AUTH_LIMITER._attempts.clear()
    integrations_fhh.LINK_LIMITER._attempts.clear()
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
    yield TestClient(app, client=("127.0.0.1", 50000))
    app.dependency_overrides.clear()


def _world(db):
    school = School(name="Assertion School", slug="assertion-school", status="active")
    teacher_user = User(
        email="assertion-teacher@test",
        name="Verified Teacher",
        google_sub="assertion-teacher",
    )
    subject_teacher_user = User(
        email="assertion-subject-teacher@test",
        name="Zulu Subject Teacher",
        name_ar="معلم المواد",
        google_sub="assertion-subject-teacher",
    )
    admin_user = User(
        email="assertion-school-admin@test",
        name="Zulu School Office",
        name_ar="إدارة المدرسة",
        google_sub="assertion-school-admin",
    )
    db.add_all([school, teacher_user, subject_teacher_user, admin_user])
    db.flush()
    teacher = Membership(
        school_id=school.id,
        user_id=teacher_user.id,
        role="teacher",
        status="active",
    )
    subject_teacher = Membership(
        school_id=school.id,
        user_id=subject_teacher_user.id,
        role="teacher",
        status="active",
    )
    school_admin = Membership(
        school_id=school.id,
        user_id=admin_user.id,
        role="school_admin",
        status="active",
    )
    branch = BranchCampus(
        school_id=school.id, code="ASSERT-B", name="Main", status="active"
    )
    year = AcademicYear(
        school_id=school.id,
        code="ASSERT-Y",
        name="Year",
        is_current=True,
        status="active",
    )
    grade = GradeLevel(
        school_id=school.id, code="ASSERT-G", name="Grade", status="active"
    )
    students = [
        Student(
            school_id=school.id,
            first_name=f"Linked {index}",
            last_name="Student",
            status="active",
        )
        for index in (1, 2)
    ]
    db.add_all(
        [
            teacher,
            subject_teacher,
            school_admin,
            branch,
            year,
            grade,
            *students,
            SchoolMessagingPolicy(school_id=school.id, enabled=True),
        ]
    )
    db.flush()
    section = ClassSection(
        school_id=school.id,
        branch_campus_id=branch.id,
        academic_year_id=year.id,
        grade_level_id=grade.id,
        code="ASSERT-C",
        name="Class",
        status="active",
    )
    db.add(section)
    db.flush()
    subjects = [
        Subject(
            school_id=school.id,
            code="ENG",
            name="English",
            name_ar="اللغة الإنجليزية",
            status="active",
        ),
        Subject(
            school_id=school.id,
            code="SCI",
            name="Science",
            name_ar="العلوم",
            status="active",
        ),
    ]
    db.add_all(subjects)
    db.flush()
    groups = [
        SubjectGroup(
            school_id=school.id,
            academic_year_id=year.id,
            class_section_id=section.id,
            subject_id=subject.id,
            code=f"{subject.code}-ASSERT",
            name=subject.name,
            name_ar=subject.name_ar,
            status="active",
            enrolment_policy="default_for_section",
        )
        for subject in subjects
    ]
    db.add_all(groups)
    db.flush()
    db.add(
        StaffAssignment(
            school_id=school.id,
            membership_id=teacher.id,
            class_section_id=section.id,
            role="homeroom",
            valid_from=date.today() - timedelta(days=5),
        )
    )
    db.add_all(
        [
            StaffAssignment(
                school_id=school.id,
                membership_id=subject_teacher.id,
                subject_group_id=group.id,
                role="subject",
                valid_from=date.today() - timedelta(days=5),
            )
            for group in groups
        ]
    )
    for student in students:
        db.add(
            Enrolment(
                school_id=school.id,
                student_id=student.id,
                class_section_id=section.id,
                kind="member",
                valid_from=date.today() - timedelta(days=5),
            )
        )
    links = []
    tokens = []
    for index, student in enumerate(students, start=1):
        invite = FhhLinkInvite(
            school_id=school.id,
            student_id=student.id,
            token_hash=f"assertion-invite-{index}",
            display_code_last4=f"00{index}",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            consumed_at=datetime.now(timezone.utc),
            consumed_by=f"opaque-child-{index}",
            created_by_user_id=teacher_user.id,
        )
        db.add(invite)
        db.flush()
        token = f"opaque-link-token-{index}"
        link = FhhLink(
            school_id=school.id,
            student_id=student.id,
            source_invite_id=invite.id,
            link_token_hash=invite_tokens.hash_token(token),
            fhh_child_ref=f"opaque-child-{index}",
        )
        db.add(link)
        db.flush()
        links.append(link)
        tokens.append(token)
    identities = [
        FhhMessagingIdentity(
            school_id=school.id,
            external_subject_ref=uuid4(),
            display_name=(
                "ولي أمر موثّق"
                if index == 2
                else "Verified Parent 1"
            ),
            preferred_locale="ar" if index == 2 else "en",
        )
        for index in (1, 2)
    ]
    db.add_all(identities)
    db.flush()
    for identity in identities:
        db.add(
            FhhMessagingIdentityLink(
                school_id=school.id,
                fhh_link_id=links[0].id,
                identity_id=identity.id,
                status="active",
                sync_version=1,
            )
        )
    db.commit()
    return {
        "school": school,
        "teacher": teacher,
        "subject_teacher": subject_teacher,
        "school_admin": school_admin,
        "students": students,
        "links": links,
        "tokens": tokens,
        "identities": identities,
    }


def _path(link, suffix):
    return f"/api/integrations/fhh/links/{link.id}/messaging{suffix}"


def _assertion(identity, link, *, method, path, body=None, **overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "iss": database.settings.FHH_MESSAGING_ASSERTION_ISSUER,
        "aud": database.settings.FHH_MESSAGING_ASSERTION_AUDIENCE,
        "sub": str(identity.external_subject_ref),
        "link_id": link.id,
        "display_name": identity.display_name,
        "locale": identity.preferred_locale,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "jti": str(uuid4()),
        "method": method,
        "path": path,
        "body_sha256": canonical_body_hash(body),
        **overrides,
    }
    return jwt.encode(claims, ASSERTION_SECRET, algorithm="HS256")


def _headers(token, assertion):
    return {
        "Authorization": f"Bearer {SERVICE_TOKEN}",
        "X-FHH-Link-Token": token,
        "X-FHH-Messaging-Actor": assertion,
    }


def _request(client, world, identity, method, suffix, *, body=None, link_index=0):
    link = world["links"][link_index]
    path = _path(link, suffix)
    headers = _headers(
        world["tokens"][link_index],
        _assertion(identity, link, method=method, path=path, body=body),
    )
    return client.request(method, path, headers=headers, json=body)


def test_two_fhh_parents_have_distinct_attribution_and_read_state(db, client):
    world = _world(db)
    parent_one, parent_two = world["identities"]

    recipient_response = _request(
        client, world, parent_one, "GET", "/recipients"
    )
    assert recipient_response.status_code == 200, recipient_response.text
    recipient = recipient_response.json()["staff"][0]
    assert "membership_id" not in recipient
    decoded_reference = base64.urlsafe_b64decode(
        recipient["recipient_ref"]
        + ("=" * (-len(recipient["recipient_ref"]) % 4))
    )
    assert b"membership_id" not in decoded_reference
    assert recipient["staff_context"] == {
        "relationship": "homeroom_teacher",
        "subjects": [],
    }

    create_body = {
        "kind": "student_staff",
        "recipient_ref": recipient["recipient_ref"],
    }
    created = _request(
        client,
        world,
        parent_one,
        "POST",
        "/conversations",
        body=create_body,
    )
    assert created.status_code == 200, created.text
    conversation_id = created.json()["conversation_id"]

    send_body = {
        "client_message_id": str(uuid4()),
        "body": "Message from the first parent",
        "urgent": False,
    }
    sent = _request(
        client,
        world,
        parent_one,
        "POST",
        f"/conversations/{conversation_id}/messages",
        body=send_body,
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["sender_display_name"] == parent_one.display_name

    second_history = _request(
        client,
        world,
        parent_two,
        "GET",
        f"/conversations/{conversation_id}/messages",
    )
    assert second_history.status_code == 200, second_history.text
    assert second_history.json()["items"][0]["sender_is_self"] is False
    before_ack = (
        db.query(ConversationParticipant)
        .filter(ConversationParticipant.participant_kind == "fhh_parent")
        .all()
    )
    before_by_identity = {
        row.external_participant_id: row for row in before_ack
    }
    assert before_by_identity[parent_one.id].last_read_sequence == 1
    assert before_by_identity[parent_two.id].last_read_sequence == 0
    ack_body = {
        "event_type": "read",
        "through_sequence": 1,
        "client_ack_id": str(uuid4()),
        "occurred_at": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "device_session_ref": None,
    }
    acknowledged = _request(
        client,
        world,
        parent_two,
        "POST",
        f"/conversations/{conversation_id}/acknowledgements",
        body=ack_body,
    )
    assert acknowledged.status_code == 200, acknowledged.text

    db.expire_all()
    participants = (
        db.query(ConversationParticipant)
        .filter(ConversationParticipant.participant_kind == "fhh_parent")
        .order_by(ConversationParticipant.external_participant_id)
        .all()
    )
    assert len(participants) == 2
    by_identity = {row.external_participant_id: row for row in participants}
    assert by_identity[parent_one.id].last_read_sequence == 1
    assert by_identity[parent_two.id].last_read_sequence == 1

    policy = db.query(SchoolMessagingPolicy).filter_by(school_id=world["school"].id).one()
    for delivery_visible, read_visible, expected_state in (
        (True, False, "delivered"),
        (False, True, "read"),
        (False, False, "sent"),
        (True, True, "read"),
    ):
        policy.delivery_receipts_visible = delivery_visible
        policy.read_receipts_visible = read_visible
        policy.policy_version += 1
        db.commit()
        history = _request(
            client,
            world,
            parent_one,
            "GET",
            f"/conversations/{conversation_id}/messages",
        )
        assert history.status_code == 200, history.text
        payload = history.json()
        receipt = payload["items"][0]["receipt"]
        assert receipt == {
            "delivery_visible": delivery_visible,
            "read_visible": read_visible,
            "delivered": True,
            "read": True,
            "state": expected_state,
            "policy_version": policy.policy_version,
        }
        assert payload["receipt_updates"] == [
            {
                "id": payload["items"][0]["id"],
                "sequence": 1,
                "receipt": receipt,
            }
        ]
        assert "recipient" not in str(receipt).lower()


def test_recipients_expose_current_assignment_context_without_raw_membership_ids(db, client):
    world = _world(db)
    response = _request(client, world, world["identities"][0], "GET", "/recipients")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["student"]["class_label"] == "Class"
    assert payload["student"]["grade_label"] == "Grade"
    by_name = {row["display_name"]: row for row in payload["staff"]}
    assert by_name["Zulu Subject Teacher"]["staff_context"] == {
        "relationship": "subject_teacher",
        "subjects": [
            {"name": "English", "name_ar": "اللغة الإنجليزية"},
            {"name": "Science", "name_ar": "العلوم"},
        ],
    }
    assert by_name["Zulu School Office"]["staff_context"] == {
        "relationship": "school_administration",
        "subjects": [],
    }
    assert all("membership_id" not in row for row in payload["staff"])

    path = _path(world["links"][0], "/recipients")
    searched = client.get(
        f"{path}?q=Science",
        headers=_headers(
            world["tokens"][0],
            _assertion(
                world["identities"][0],
                world["links"][0],
                method="GET",
                path=path,
            ),
        ),
    )
    assert searched.status_code == 200
    assert [row["display_name"] for row in searched.json()["staff"]] == [
        "Zulu Subject Teacher"
    ]


def test_assertions_are_one_time_request_bound_and_profile_bound(db, client):
    world = _world(db)
    identity = world["identities"][0]
    link = world["links"][0]
    path = _path(link, "/inbox")
    token = _assertion(identity, link, method="GET", path=path)
    headers = _headers(world["tokens"][0], token)
    first = client.get(path, headers=headers)
    assert first.status_code == 200, first.text
    assert client.get(path, headers=headers).status_code == 409
    assert db.query(FhhMessagingAssertionUse).count() == 1

    wrong_path = client.get(
        _path(link, "/unread-count"),
        headers=_headers(
            world["tokens"][0],
            _assertion(identity, link, method="GET", path=path),
        ),
    )
    assert wrong_path.status_code == 401
    forged_profile = client.get(
        path,
        headers=_headers(
            world["tokens"][0],
            _assertion(
                identity,
                link,
                method="GET",
                path=path,
                display_name="Client supplied name",
            ),
        ),
    )
    assert forged_profile.status_code == 409
    wrong_audience = client.get(
        path,
        headers=_headers(
            world["tokens"][0],
            _assertion(
                identity,
                link,
                method="GET",
                path=path,
                aud="not-chh-messaging",
            ),
        ),
    )
    assert wrong_audience.status_code == 401
    expired = client.get(
        path,
        headers=_headers(
            world["tokens"][0],
            _assertion(
                identity,
                link,
                method="GET",
                path=path,
                iat=int(
                    (datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp()
                ),
                exp=int(
                    (datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp()
                ),
            ),
        ),
    )
    assert expired.status_code == 401


def test_link_and_student_swaps_cannot_cross_scope_or_mutate_state(db, client):
    world = _world(db)
    parent = world["identities"][0]
    db.add(
        FhhMessagingIdentityLink(
            school_id=world["school"].id,
            fhh_link_id=world["links"][1].id,
            identity_id=parent.id,
            status="active",
            sync_version=1,
        )
    )
    db.commit()
    recipients = _request(client, world, parent, "GET", "/recipients").json()
    create_body = {
        "kind": "student_staff",
        "recipient_ref": recipients["staff"][0]["recipient_ref"],
    }
    created = _request(
        client, world, parent, "POST", "/conversations", body=create_body
    )
    conversation_id = created.json()["conversation_id"]

    swapped_link = world["links"][1]
    swapped_path = _path(
        swapped_link, f"/conversations/{conversation_id}"
    )
    swapped = client.get(
        swapped_path,
        headers=_headers(
            world["tokens"][1],
            _assertion(
                parent,
                swapped_link,
                method="GET",
                path=swapped_path,
            ),
        ),
    )
    assert swapped.status_code == 404

    recipient_swap = _request(
        client,
        world,
        parent,
        "POST",
        "/conversations",
        body=create_body,
        link_index=1,
    )
    assert recipient_swap.status_code == 400

    mismatched_claim = client.get(
        _path(world["links"][0], f"/conversations/{conversation_id}"),
        headers=_headers(
            world["tokens"][0],
            _assertion(
                parent,
                swapped_link,
                method="GET",
                path=_path(
                    world["links"][0], f"/conversations/{conversation_id}"
                ),
            ),
        ),
    )
    assert mismatched_claim.status_code == 401
    assert db.query(ConversationParticipant).filter(
        ConversationParticipant.external_participant_id == parent.id
    ).count() == 1


def test_revoked_identity_link_archived_student_link_revoke_and_school_suspend_fail_closed(
    db, client
):
    world = _world(db)
    parent = world["identities"][0]
    world["school"].status = "pending_setup"
    db.commit()
    recipients = _request(client, world, parent, "GET", "/recipients")
    assert recipients.status_code == 200
    world["school"].status = "active"
    db.commit()
    created = _request(
        client,
        world,
        parent,
        "POST",
        "/conversations",
        body={
            "kind": "student_staff",
            "recipient_ref": recipients.json()["staff"][0]["recipient_ref"],
        },
    )
    assert created.status_code == 200
    conversation_id = created.json()["conversation_id"]
    participant_count = db.query(ConversationParticipant).count()

    identity_link = (
        db.query(FhhMessagingIdentityLink)
        .filter(
            FhhMessagingIdentityLink.fhh_link_id == world["links"][0].id,
            FhhMessagingIdentityLink.identity_id == parent.id,
        )
        .one()
    )
    identity_link.status = "revoked"
    identity_link.revoked_at = datetime.now(timezone.utc)
    db.commit()
    denied_identity = _request(
        client,
        world,
        parent,
        "POST",
        f"/conversations/{conversation_id}/messages",
        body={
            "client_message_id": str(uuid4()),
            "body": "Must not be accepted",
            "urgent": False,
        },
    )
    assert denied_identity.status_code == 409
    assert db.query(Message).count() == 0
    assert db.query(ConversationParticipant).count() == participant_count

    identity_link.status = "active"
    identity_link.revoked_at = None
    world["students"][0].status = "archived"
    db.commit()
    archived = _request(client, world, parent, "GET", "/recipients")
    assert archived.status_code == 404

    world["students"][0].status = "active"
    world["links"][0].status = "revoked"
    world["links"][0].revoked_at = datetime.now(timezone.utc)
    db.commit()
    revoked_link = _request(
        client,
        world,
        parent,
        "GET",
        f"/conversations/{conversation_id}",
    )
    assert revoked_link.status_code == 404

    world["links"][0].status = "active"
    world["links"][0].revoked_at = None
    world["school"].status = "suspended"
    db.commit()
    suspended = _request(
        client,
        world,
        parent,
        "GET",
        f"/conversations/{conversation_id}",
    )
    assert suspended.status_code == 404


def test_assertion_and_payload_never_accept_fhh_private_identifiers(db, client):
    world = _world(db)
    identity = world["identities"][0]
    body = {
        "kind": "student_staff",
        "recipient_ref": "r" * 32,
        "family_id": 88,
        "parent_id": 99,
        "email": "private@example.test",
        "device_token": "secret-device-token",
        "sender_display_name": "Forged",
    }
    response = _request(
        client, world, identity, "POST", "/conversations", body=body
    )
    assert response.status_code == 422
    assert db.query(ConversationParticipant).count() == 0


def test_external_inbox_guardian_resolution_uses_bounded_selects(db, client):
    world = _world(db)
    for index in range(20):
        user = User(
            email=f"bounded-{index}@test",
            name=f"Bounded Teacher {index}",
            google_sub=f"bounded-{index}",
        )
        db.add(user)
        db.flush()
        membership = Membership(
            school_id=world["school"].id,
            user_id=user.id,
            role="teacher",
            status="active",
        )
        db.add(membership)
        db.flush()
        db.add(
            Conversation(
                school_id=world["school"].id,
                kind="student_staff",
                student_id=world["students"][0].id,
                primary_staff_membership_id=membership.id,
            )
        )
    db.commit()
    parent = world["identities"][0]
    # First fetch provisions missing guardian participants in one set-based pass.
    provisioned = _request(client, world, parent, "GET", "/inbox")
    assert provisioned.status_code == 200
    assert len(provisioned.json()["items"]) == 20

    statements = []

    def count(_conn, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        steady_state = _request(client, world, parent, "GET", "/inbox")
    finally:
        event.remove(engine, "before_cursor_execute", count)
    assert steady_state.status_code == 200
    assert len(steady_state.json()["items"]) == 20
    # Assignment-derived context uses fixed set-based roster/subject queries.
    assert len(statements) <= 28


def test_runtime_requires_separate_assertion_secret_only_for_fhh_messaging():
    staff_only = database.Settings(
        APP_ENV="test",
        FHH_INTEGRATION_ENABLED=False,
        FHH_INTEGRATION_SERVICE_TOKEN="",
        FHH_MESSAGING_ASSERTION_SECRET="",
        MESSAGING_ENABLED=True,
        _env_file=None,
    )
    assert database.validate_runtime_configuration(staff_only) == "test"

    reused = database.Settings(
        APP_ENV="test",
        FHH_INTEGRATION_ENABLED=True,
        FHH_INTEGRATION_SERVICE_TOKEN="s" * 40,
        FHH_MESSAGING_ASSERTION_SECRET="s" * 40,
        MESSAGING_ENABLED=True,
        _env_file=None,
    )
    with pytest.raises(RuntimeError, match="must be separate"):
        database.validate_runtime_configuration(reused)

    valid = database.Settings(
        APP_ENV="test",
        FHH_INTEGRATION_ENABLED=True,
        FHH_INTEGRATION_SERVICE_TOKEN="s" * 40,
        FHH_MESSAGING_ASSERTION_SECRET="a" * 40,
        MESSAGING_ENABLED=True,
        _env_file=None,
    )
    assert database.validate_runtime_configuration(valid) == "test"

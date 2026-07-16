import os
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.messaging_service import (
    MessagingAccessDenied,
    MessagingConflict,
    participant_sequence_access,
    send_text_message,
)
from app.models_school import (
    AcademicYear,
    BranchCampus,
    ClassSection,
    Conversation,
    ConversationAccessGrant,
    ConversationParticipant,
    Enrolment,
    GradeLevel,
    GuardianLink,
    Membership,
    Message,
    MessageReceiptEvent,
    MessagingAuditEvent,
    School,
    SchoolMessagingPolicy,
    StaffAssignment,
    Student,
    User,
)


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def _school_world(db, suffix: str):
    school = School(name=f"School {suffix}", slug=f"school-{suffix}", status="active")
    admin_user = User(
        email=f"admin-{suffix}@test", name=f"Admin {suffix}", google_sub=f"admin-{suffix}"
    )
    teacher_user = User(
        email=f"teacher-{suffix}@test",
        name=f"Teacher {suffix}",
        google_sub=f"teacher-{suffix}",
    )
    guardian_user = User(
        email=f"guardian-{suffix}@test",
        name=f"Guardian {suffix}",
        google_sub=f"guardian-{suffix}",
    )
    db.add_all([school, admin_user, teacher_user, guardian_user])
    db.flush()

    admin = Membership(
        school_id=school.id,
        user_id=admin_user.id,
        role="school_admin",
        status="active",
    )
    teacher = Membership(
        school_id=school.id,
        user_id=teacher_user.id,
        role="teacher",
        status="active",
    )
    branch = BranchCampus(
        school_id=school.id, code=f"B-{suffix}", name="Main", status="active"
    )
    year = AcademicYear(
        school_id=school.id,
        code=f"Y-{suffix}",
        name=f"Year {suffix}",
        is_current=True,
        status="active",
    )
    grade = GradeLevel(
        school_id=school.id, code=f"G-{suffix}", name="Grade", status="active"
    )
    student = Student(
        school_id=school.id,
        first_name=f"Student {suffix}",
        last_name="Test",
        status="active",
    )
    policy = SchoolMessagingPolicy(school_id=school.id)
    db.add_all([admin, teacher, branch, year, grade, student, policy])
    db.flush()

    section = ClassSection(
        school_id=school.id,
        branch_campus_id=branch.id,
        academic_year_id=year.id,
        grade_level_id=grade.id,
        code=f"C-{suffix}",
        name="Class",
        status="active",
    )
    db.add(section)
    db.flush()
    enrolment = Enrolment(
        school_id=school.id,
        student_id=student.id,
        class_section_id=section.id,
        kind="member",
        valid_from=date.today() - timedelta(days=30),
    )
    assignment = StaffAssignment(
        school_id=school.id,
        membership_id=teacher.id,
        class_section_id=section.id,
        role="class_teacher",
        valid_from=date.today() - timedelta(days=30),
    )
    guardian_link = GuardianLink(
        school_id=school.id,
        student_id=student.id,
        user_id=guardian_user.id,
        relationship="guardian",
        display_name=guardian_user.name,
        status="active",
    )
    db.add_all([enrolment, assignment, guardian_link])
    db.commit()
    return {
        "school": school,
        "admin_user": admin_user,
        "admin": admin,
        "teacher_user": teacher_user,
        "teacher": teacher,
        "guardian_user": guardian_user,
        "guardian_link": guardian_link,
        "student": student,
        "section": section,
        "assignment": assignment,
        "policy": policy,
    }


def _student_thread(db, world, *, visible_from=1, visible_through=None):
    conversation = Conversation(
        school_id=world["school"].id,
        kind="student_staff",
        student_id=world["student"].id,
        primary_staff_membership_id=world["teacher"].id,
        context_class_section_id=world["section"].id,
        context_label=world["section"].name,
    )
    db.add(conversation)
    db.flush()
    staff = ConversationParticipant(
        conversation_id=conversation.id,
        participant_kind="staff",
        user_id=world["teacher_user"].id,
        membership_id=world["teacher"].id,
        side="staff",
        display_name_snapshot=world["teacher_user"].name,
    )
    guardian = ConversationParticipant(
        conversation_id=conversation.id,
        participant_kind="chh_guardian",
        user_id=world["guardian_user"].id,
        side="guardian",
        display_name_snapshot=world["guardian_user"].name,
    )
    db.add_all([staff, guardian])
    db.flush()
    db.add_all(
        [
            ConversationAccessGrant(
                conversation_id=conversation.id,
                participant_id=staff.id,
                source_type="staff_assignment",
                staff_assignment_id=world["assignment"].id,
                grant_reason="conversation_created",
                visible_from_sequence=visible_from,
                visible_through_sequence=visible_through,
            ),
            ConversationAccessGrant(
                conversation_id=conversation.id,
                participant_id=guardian.id,
                source_type="guardian_link",
                guardian_link_id=world["guardian_link"].id,
                grant_reason="conversation_created",
                visible_from_sequence=visible_from,
                visible_through_sequence=visible_through,
            ),
        ]
    )
    conversation.created_by_participant_id = staff.id
    db.commit()
    return conversation, staff, guardian


@pytest.mark.parametrize(
    "values",
    [
        {"kind": "student_staff"},
        {
            "kind": "student_staff",
            "student_id": 1,
            "primary_staff_membership_id": 1,
            "internal_guardian_user_id": 1,
        },
        {
            "kind": "staff_direct",
            "staff_membership_low_id": 2,
            "staff_membership_high_id": 1,
        },
        {"kind": "guardian_direct", "primary_staff_membership_id": 1},
        {
            "kind": "guardian_direct",
            "primary_staff_membership_id": 1,
            "internal_guardian_user_id": 1,
            "external_guardian_participant_id": 1,
        },
        {"kind": "unknown"},
    ],
)
def test_conversation_kind_constraints_reject_invalid_shapes(db, values):
    world = _school_world(db, str(uuid4())[:8])
    row = Conversation(school_id=world["school"].id, **values)
    db.add(row)
    with pytest.raises(IntegrityError):
        db.commit()


def test_all_conversation_kinds_accept_valid_shapes(db):
    world = _school_world(db, "valid")
    second_user = User(email="second@test", name="Second", google_sub="second")
    db.add(second_user)
    db.flush()
    second_staff = Membership(
        school_id=world["school"].id,
        user_id=second_user.id,
        role="teacher",
        status="active",
    )
    db.add(second_staff)
    db.flush()
    db.add_all(
        [
            Conversation(
                school_id=world["school"].id,
                kind="student_staff",
                student_id=world["student"].id,
                primary_staff_membership_id=world["teacher"].id,
            ),
            Conversation(
                school_id=world["school"].id,
                kind="staff_direct",
                staff_membership_low_id=min(world["teacher"].id, second_staff.id),
                staff_membership_high_id=max(world["teacher"].id, second_staff.id),
            ),
            Conversation(
                school_id=world["school"].id,
                kind="guardian_direct",
                student_id=world["student"].id,
                primary_staff_membership_id=world["teacher"].id,
                internal_guardian_user_id=world["guardian_user"].id,
            ),
        ]
    )
    db.commit()
    assert db.query(Conversation).count() == 3


def test_duplicate_current_thread_is_prevented_but_closed_history_is_retained(db):
    world = _school_world(db, "duplicate")
    first, _, _ = _student_thread(db, world)
    db.add(
        Conversation(
            school_id=world["school"].id,
            kind="student_staff",
            student_id=world["student"].id,
            primary_staff_membership_id=world["teacher"].id,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    first.status = "closed_assignment_ended"
    first.closed_at = datetime.now(timezone.utc)
    first.closed_reason = "assignment_ended"
    db.commit()
    db.add(
        Conversation(
            school_id=world["school"].id,
            kind="student_staff",
            student_id=world["student"].id,
            primary_staff_membership_id=world["teacher"].id,
        )
    )
    db.commit()
    assert db.query(Conversation).count() == 2


def test_participant_actor_shape_constraints(db):
    world = _school_world(db, "actor")
    conversation = Conversation(
        school_id=world["school"].id,
        kind="student_staff",
        student_id=world["student"].id,
        primary_staff_membership_id=world["teacher"].id,
    )
    db.add(conversation)
    db.flush()
    db.add(
        ConversationParticipant(
            conversation_id=conversation.id,
            participant_kind="staff",
            user_id=world["teacher_user"].id,
            membership_id=world["teacher"].id,
            external_participant_id=1,
            side="staff",
            display_name_snapshot="Forged",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_message_sequence_idempotency_and_immutable_attribution(db):
    world = _school_world(db, "send")
    conversation, staff, _ = _student_thread(db, world)
    client_id = uuid4()
    first, duplicate = send_text_message(
        db,
        conversation_id=conversation.id,
        sender_participant_id=staff.id,
        client_message_id=client_id,
        body="  First\r\nmessage  ",
    )
    db.commit()
    assert duplicate is False
    assert first.sequence == 1
    assert first.body == "First\nmessage"
    assert first.sender_display_name_snapshot == world["teacher_user"].name
    same, duplicate = send_text_message(
        db,
        conversation_id=conversation.id,
        sender_participant_id=staff.id,
        client_message_id=client_id,
        body="First\nmessage",
    )
    assert duplicate is True and same.id == first.id
    with pytest.raises(MessagingConflict):
        send_text_message(
            db,
            conversation_id=conversation.id,
            sender_participant_id=staff.id,
            client_message_id=client_id,
            body="Different",
        )
    second, _ = send_text_message(
        db,
        conversation_id=conversation.id,
        sender_participant_id=staff.id,
        client_message_id=uuid4(),
        body="Second",
    )
    db.commit()
    assert second.sequence == 2
    assert db.query(MessagingAuditEvent).filter_by(event_type="message.sent").count() == 2
    first.body = "edited"
    with pytest.raises(ValueError, match="immutable"):
        db.commit()


def test_access_sequence_boundary_assignment_expiry_and_guardian_revocation(db):
    world = _school_world(db, "lifecycle")
    conversation, staff, guardian = _student_thread(
        db, world, visible_from=3, visible_through=7
    )
    access = participant_sequence_access(
        db, conversation=conversation, participant=staff
    )
    assert access.includes(3) and access.includes(7)
    assert not access.includes(2) and not access.includes(8)

    world["assignment"].valid_to = date.today() - timedelta(days=1)
    db.commit()
    with pytest.raises(MessagingAccessDenied):
        participant_sequence_access(db, conversation=conversation, participant=staff)

    world["guardian_link"].status = "revoked"
    world["guardian_link"].revoked_at = datetime.now(timezone.utc)
    db.commit()
    with pytest.raises(MessagingAccessDenied):
        participant_sequence_access(db, conversation=conversation, participant=guardian)


def test_cross_school_sources_never_authorize(db):
    one = _school_world(db, "one")
    two = _school_world(db, "two")
    conversation, staff, _ = _student_thread(db, one)
    grant = db.query(ConversationAccessGrant).filter_by(participant_id=staff.id).one()
    grant.staff_assignment_id = two["assignment"].id
    db.commit()
    with pytest.raises(MessagingAccessDenied):
        participant_sequence_access(db, conversation=conversation, participant=staff)


def test_staff_direct_teacher_access_requires_current_school_membership(db):
    world = _school_world(db, "direct")
    conversation = Conversation(
        school_id=world["school"].id,
        kind="staff_direct",
        staff_membership_low_id=min(world["teacher"].id, world["admin"].id),
        staff_membership_high_id=max(world["teacher"].id, world["admin"].id),
    )
    db.add(conversation)
    db.flush()
    participant = ConversationParticipant(
        conversation_id=conversation.id,
        participant_kind="staff",
        user_id=world["teacher_user"].id,
        membership_id=world["teacher"].id,
        side="staff",
        display_name_snapshot=world["teacher_user"].name,
    )
    db.add(participant)
    db.flush()
    db.add(
        ConversationAccessGrant(
            conversation_id=conversation.id,
            participant_id=participant.id,
            source_type="school_admin_membership",
            membership_id=world["teacher"].id,
            grant_reason="staff_direct_membership",
        )
    )
    db.commit()
    assert participant_sequence_access(
        db, conversation=conversation, participant=participant
    ).visible_from == 1
    world["teacher"].status = "revoked"
    world["teacher"].revoked_at = datetime.now(timezone.utc)
    db.commit()
    with pytest.raises(MessagingAccessDenied):
        participant_sequence_access(db, conversation=conversation, participant=participant)


def test_receipt_and_audit_evidence_are_append_only(db):
    world = _school_world(db, "evidence")
    conversation, staff, _ = _student_thread(db, world)
    receipt = MessageReceiptEvent(
        conversation_id=conversation.id,
        participant_id=staff.id,
        event_type="read",
        through_sequence=0,
        client_ack_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
    )
    audit = MessagingAuditEvent(
        school_id=world["school"].id,
        actor_kind="system",
        event_type="conversation.created",
        conversation_id=conversation.id,
        detail={},
    )
    db.add_all([receipt, audit])
    db.commit()
    receipt.through_sequence = 1
    with pytest.raises(ValueError, match="append-only"):
        db.commit()
    db.rollback()
    db.delete(audit)
    with pytest.raises(ValueError, match="append-only"):
        db.commit()

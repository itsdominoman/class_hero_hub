from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.family_notifications import enqueue_family_notifications, revalidate_family_notification
from app.models_school import (
    AcademicYear, Announcement, BehaviourCategory, BehaviourEvent, BranchCampus,
    CalendarEvent, ClassSection, Enrolment, FhhLink, FhhLinkInvite, GradeLevel,
    HomeworkItem, NotificationOutbox, School, Student, UpdatePost, User,
)


UTC = timezone.utc


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _world(db):
    user = User(email="teacher@push.test", name="Teacher", google_sub="push-teacher", status="active")
    # Operational CHH schools may remain in pending_setup; the established
    # school-chat path treats both pending_setup and active as eligible.
    school = School(name="Push School", slug="push-school", status="pending_setup")
    db.add_all([user, school]); db.flush()
    branch = BranchCampus(school_id=school.id, code="MAIN", name="Main", status="active")
    year = AcademicYear(school_id=school.id, code="2026", name="2026", status="active", is_current=True)
    level = GradeLevel(school_id=school.id, code="G1", name="Grade 1", status="active")
    db.add_all([branch, year, level]); db.flush()
    section = ClassSection(school_id=school.id, branch_campus_id=branch.id, academic_year_id=year.id, grade_level_id=level.id, code="A", name="1A", status="active")
    other = ClassSection(school_id=school.id, branch_campus_id=branch.id, academic_year_id=year.id, grade_level_id=level.id, code="B", name="1B", status="active")
    db.add_all([section, other]); db.flush()
    sara = Student(school_id=school.id, external_ref="S1", first_name="Sara", last_name="A", status="active")
    bob = Student(school_id=school.id, external_ref="S2", first_name="Bob", last_name="B", status="active")
    db.add_all([sara, bob]); db.flush()
    db.add_all([
        Enrolment(school_id=school.id, student_id=sara.id, class_section_id=section.id, kind="member"),
        Enrolment(school_id=school.id, student_id=bob.id, class_section_id=other.id, kind="member"),
    ])
    links = []
    for index, student in enumerate((sara, bob), 1):
        invite = FhhLinkInvite(
            school_id=school.id, student_id=student.id, token_hash=f"invite-{index}",
            display_code_last4=f"000{index}", created_by_user_id=user.id,
        )
        db.add(invite); db.flush()
        link = FhhLink(
            school_id=school.id, student_id=student.id, source_invite_id=invite.id,
            link_token_hash=f"link-{index}", fhh_child_ref=f"child-{index}", status="active",
        )
        db.add(link); db.flush(); links.append(link)
    db.commit()
    return school, user, section, sara, bob, links


def test_audience_status_idempotency_and_privacy_shape(db):
    school, user, section, sara, _bob, links = _world(db)
    homework = HomeworkItem(
        school_id=school.id, author_user_id=user.id, item_type="homework", title="Math",
        body="Private body", audience_type="class_section", class_section_id=section.id,
        due_at=datetime.now(UTC) + timedelta(days=1), status="active", resource_links=[],
    )
    db.add(homework); db.flush()
    rows = enqueue_family_notifications(db, category="homework", source=homework, action="published", version=1)
    assert [row.recipient_fhh_link_id for row in rows] == [links[0].id]
    assert rows[0].template_args == {}
    assert "Private body" not in str(rows[0].template_args)
    assert enqueue_family_notifications(db, category="homework", source=homework, action="published", version=1) == []

    homework.status = "archived"
    cancelled = enqueue_family_notifications(db, category="homework", source=homework, action="cancelled", version=2)
    assert len(cancelled) == 1
    links[0].status = "revoked"
    links[0].revoked_at = datetime.now(UTC)
    assert not revalidate_family_notification(db, cancelled[0])


def test_school_notice_update_calendar_and_points_create_category_evidence(db):
    school, user, section, sara, _bob, links = _world(db)
    notice = Announcement(
        school_id=school.id, author_user_id=user.id, title="Closure", body="Sensitive notice body",
        audience_type="school", status="published", urgent=True,
    )
    db.add(notice); db.flush()
    notices = enqueue_family_notifications(db, category="notice", source=notice, action="published")
    assert len(notices) == 2 and all(row.urgent for row in notices)

    update = UpdatePost(
        school_id=school.id, author_user_id=user.id, body="Photo caption",
        audience_type="class_section", class_section_id=section.id, status="active",
    )
    calendar = CalendarEvent(
        school_id=school.id, author_user_id=user.id, title="Trip", body="Private details",
        event_type="trip", audience_type="class_section", class_section_id=section.id,
        starts_at=datetime.now(UTC) + timedelta(days=3), status="active",
    )
    category = BehaviourCategory(school_id=school.id, type="positive", label="Effort", points_value=1, active=True)
    db.add_all([update, calendar, category]); db.flush()
    point = BehaviourEvent(
        school_id=school.id, student_id=sara.id, category_id=category.id, actor_user_id=user.id,
        points_delta=1, note="Private teacher note", source="teacher", context_type="general",
    )
    db.add(point); db.flush()
    assert len(enqueue_family_notifications(db, category="update", source=update, action="published")) == 1
    assert len(enqueue_family_notifications(db, category="calendar", source=calendar, action="published")) == 1
    point_rows = enqueue_family_notifications(db, category="points", source=point, action="awarded")
    assert len(point_rows) == 1 and point_rows[0].template_args == {"variant": "positive"}
    assert "Private teacher note" not in str(point_rows[0].template_args)
    assert {row.event_category for row in db.query(NotificationOutbox).all()} == {"notice", "update", "calendar", "points"}

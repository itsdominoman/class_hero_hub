import os
import uuid
from datetime import timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from app import auth, database, invite_tokens
from app.admission_cleanup import (
    CleanupBlocked,
    REQUIRED_REMOVALS,
    SEEDED_EXCEPTIONS,
    apply_cleanup,
    build_inventory,
)
from app.database import Base
from app.models_school import (
    DevicePushRegistration,
    GuardianLink,
    MagicLoginToken,
    Membership,
    PlatformAdmin,
    School,
    Student,
    User,
    UserRefreshSession,
)


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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


def _user(db, email: str) -> User:
    row = User(email=email, name=email, status="active")
    db.add(row)
    db.flush()
    return row


def _add_account_state(db, user: User, index: int) -> None:
    auth.create_refresh_session(
        db,
        user,
        Request({"type": "http", "headers": []}),
        client_type="android",
    )
    db.add(
        DevicePushRegistration(
            installation_id=uuid.uuid4(),
            user_id=user.id,
            app_package="com.classherohub.app",
            fcm_token=f"unauthorised-fcm-{index}",
        )
    )
    db.add(
        MagicLoginToken(
            email=user.email,
            token_hash=invite_tokens.hash_token(f"magic-{index}"),
            expires_at=invite_tokens.now_utc() + timedelta(minutes=15),
            used_at=invite_tokens.now_utc(),
        )
    )
    db.commit()


def test_inventory_cleanup_removes_only_unauthorised_accounts_and_owned_state(db):
    unauthorised = [_user(db, email) for email in sorted(REQUIRED_REMOVALS)]
    seeded = _user(db, next(iter(SEEDED_EXCEPTIONS)))
    platform = _user(db, "legitimate-platform@example.com")
    admin = _user(db, "legitimate-admin@example.com")
    teacher = _user(db, "legitimate-teacher@example.com")
    guardian = _user(db, "legitimate-guardian@example.com")
    school = School(name="Pilot School", slug="pilot-school", status="active")
    db.add(school)
    db.flush()
    student = Student(
        school_id=school.id,
        first_name="Legitimate",
        last_name="Child",
        status="active",
    )
    db.add(student)
    db.flush()
    db.add_all(
        [
            PlatformAdmin(user_id=platform.id),
            Membership(
                school_id=school.id,
                user_id=admin.id,
                role="school_admin",
                status="active",
            ),
            Membership(
                school_id=school.id,
                user_id=teacher.id,
                role="teacher",
                status="active",
            ),
            GuardianLink(
                school_id=school.id,
                student_id=student.id,
                user_id=guardian.id,
                status="active",
            ),
        ]
    )
    db.commit()
    for index, user in enumerate(unauthorised):
        _add_account_state(db, user, index)

    inventory = build_inventory(db)
    assert {row.email_address for row in inventory} == REQUIRED_REMOVALS | {
        seeded.email
    }
    assert [
        row.disposition
        for row in inventory
        if row.email_address == seeded.email
    ] == ["preserved_seeded_identity"]
    planned_ids = [
        row.user_id for row in inventory if row.disposition == "planned_removal"
    ]

    removed = apply_cleanup(db, planned_ids)
    db.commit()

    assert set(removed) == {user.id for user in unauthorised}
    assert db.query(User).filter(User.email.in_(REQUIRED_REMOVALS)).count() == 0
    assert db.query(User).filter_by(id=seeded.id).count() == 1
    assert db.query(User).filter(
        User.id.in_([platform.id, admin.id, teacher.id, guardian.id])
    ).count() == 4
    assert db.query(UserRefreshSession).filter(
        UserRefreshSession.user_id.in_(removed)
    ).count() == 0
    assert db.query(DevicePushRegistration).filter(
        DevicePushRegistration.user_id.in_(removed)
    ).count() == 0
    assert db.query(MagicLoginToken).filter(
        MagicLoginToken.email.in_(REQUIRED_REMOVALS)
    ).count() == 0


def test_cleanup_fails_closed_if_candidate_gains_entitlement(db):
    candidate = _user(db, "candidate@example.com")
    school = School(name="School", slug="school", status="active")
    db.add(school)
    db.commit()
    inventory = build_inventory(db)
    assert [row.user_id for row in inventory] == [candidate.id]
    db.add(
        Membership(
            school_id=school.id,
            user_id=candidate.id,
            role="teacher",
            status="active",
        )
    )
    db.commit()

    with pytest.raises(CleanupBlocked, match="gained a valid entitlement"):
        apply_cleanup(db, [candidate.id])
    db.rollback()

    assert db.query(User).filter_by(id=candidate.id).count() == 1

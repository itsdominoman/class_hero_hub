import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"
os.environ["DEV_AUTH_ENABLED"] = "false"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database, models  # noqa: F401
from app.database import Base
from app.models_school import AuditLog, Membership, PlatformAdmin, School, User
from app.school_scope import write_audit
from school_fixtures import seeded_schools  # noqa: F401


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


def test_user_email_is_unique(db):
    db.add_all(
        [
            User(email="same@example.com", name="First"),
            User(email="same@example.com", name="Second"),
        ]
    )

    with pytest.raises(IntegrityError):
        db.commit()


def test_membership_school_user_role_is_unique(db, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    alpha_admin = seeded_schools["users"]["alpha_admin"]
    db.add(Membership(school_id=alpha.id, user_id=alpha_admin.id, role="school_admin"))

    with pytest.raises(IntegrityError):
        db.commit()


def test_write_audit_creates_row(db, seeded_schools):
    alpha = seeded_schools["schools"]["alpha"]
    actor = seeded_schools["users"]["alpha_admin"]

    row = write_audit(
        db,
        actor,
        "school.updated",
        alpha,
        {"field": "name"},
        school_id=alpha.id,
    )

    audit_log = db.query(AuditLog).one()
    assert row.id == audit_log.id
    assert audit_log.actor_user_id == actor.id
    assert audit_log.school_id == alpha.id
    assert audit_log.action == "school.updated"
    assert audit_log.entity_type == "schools"
    assert audit_log.entity_id == alpha.id
    assert audit_log.detail == {"field": "name"}


def test_seeded_school_fixture_integrity(db, seeded_schools):
    assert db.query(School).count() == 2
    assert db.query(User).count() == 5
    assert db.query(Membership).count() == 4
    assert db.query(PlatformAdmin).count() == 1

    alpha = seeded_schools["schools"]["alpha"]
    beta = seeded_schools["schools"]["beta"]
    assert alpha.name == "Alpha Academy"
    assert beta.name == "Beta School"
    assert alpha.timezone == "Asia/Muscat"
    assert alpha.locale_default == "en"
    assert alpha.points_label == "Points"
    assert alpha.status == "pending_setup"

    roles_by_school = {
        school.name: {membership.role for membership in db.query(Membership).filter_by(school_id=school.id)}
        for school in (alpha, beta)
    }
    assert roles_by_school == {
        "Alpha Academy": {"school_admin", "teacher"},
        "Beta School": {"school_admin", "teacher"},
    }

import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, database, models
from app.database import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
database.engine = engine
database.SessionLocal = TestingSessionLocal


def override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def make_client(parent: models.ParentUser):
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[auth.get_current_parent] = lambda: parent
    return TestClient(app)


def test_child_patch_updates_only_supplied_fields_and_keeps_numeric_avatar_key():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        family = models.Family(timezone="Europe/Berlin", week_start_day=6)
        db.add(family)
        db.flush()
        parent = models.ParentUser(
            email="parent@example.com",
            name="Parent",
            google_sub="sub-parent",
            family_id=family.id,
        )
        db.add(parent)
        db.flush()
        child = models.Child(
            display_name="Old Name",
            avatar_name="2",
            family_id=family.id,
            active=True,
        )
        db.add(child)
        db.commit()
        db.refresh(parent)
        db.refresh(child)

        client = make_client(parent)
        try:
            response = client.patch(
                f"/api/children/{child.id}",
                json={"display_name": "New Name", "avatar_name": "7"},
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["display_name"] == "New Name"
            assert payload["avatar_name"] == "7"
            assert payload["active"] is True

            partial_response = client.patch(
                f"/api/children/{child.id}",
                json={"display_name": "Newer Name"},
            )
            assert partial_response.status_code == 200
            partial_payload = partial_response.json()
            assert partial_payload["display_name"] == "Newer Name"
            assert partial_payload["avatar_name"] == "7"
            assert partial_payload["active"] is True
        finally:
            app.dependency_overrides.clear()
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

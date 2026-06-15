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
from app.services import points_service

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
database.engine = engine
database.SessionLocal = TestingSessionLocal


def _override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        family = models.Family(timezone="Asia/Muscat", week_start_day=6)
        db.add(family)
        db.commit()
        db.refresh(family)
        parent = models.ParentUser(
            email="adjustment-http@example.com",
            name="Parent",
            google_sub="sub-adjustment-http",
            family_id=family.id,
            status="active",
        )
        child = models.Child(display_name="Kid", family_id=family.id, active=True)
        db.add_all([parent, child])
        db.commit()
        db.refresh(parent)
        db.refresh(child)
        return family.id, parent.id, child.id
    finally:
        db.close()


def _client(parent_id):
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def _authenticate(client, parent_email: str):
    csrf_token = "test-csrf-token"
    client.cookies.set("access_token", auth.create_access_token({"sub": parent_email}))
    client.cookies.set("csrf_token", csrf_token)
    return {"X-CSRF-Token": csrf_token}


def _add_balance(db, child_id, parent_id, points, jar):
    tx = models.LedgerTransaction(
        child_id=child_id,
        jar=jar,
        transaction_type=models.TransactionType.award,
        points=points,
        description="Seed",
        created_by_parent_id=parent_id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)


def _ledger_count(child_id):
    db = TestingSessionLocal()
    try:
        return db.query(models.LedgerTransaction).filter(
            models.LedgerTransaction.child_id == child_id
        ).count()
    finally:
        db.close()


def test_negative_admin_adjustment_within_spending_balance_succeeds():
    _, parent_id, child_id = _seed()
    client = _client(parent_id)
    db = TestingSessionLocal()
    try:
        parent_email = db.get(models.ParentUser, parent_id).email
        _add_balance(db, child_id, parent_id, 10, models.JarType.spending)
    finally:
        db.close()

    headers = _authenticate(client, parent_email)
    try:
        response = client.post(
            f"/api/children/{child_id}/adjustment",
            headers=headers,
            params={
                "points": -7,
                "description": "Manual spending adjustment",
                "jar": "spending",
            },
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["transaction_type"] == "adjustment"
        assert body["points"] == -7
        assert body["jar"] == "spending"
    finally:
        app.dependency_overrides.clear()


def test_negative_admin_adjustment_exactly_equal_to_savings_balance_succeeds():
    _, parent_id, child_id = _seed()
    client = _client(parent_id)
    db = TestingSessionLocal()
    try:
        parent_email = db.get(models.ParentUser, parent_id).email
        _add_balance(db, child_id, parent_id, 100, models.JarType.spending)
        _add_balance(db, child_id, parent_id, 8, models.JarType.savings)
    finally:
        db.close()

    headers = _authenticate(client, parent_email)
    try:
        response = client.post(
            f"/api/children/{child_id}/adjustment",
            headers=headers,
            params={
                "points": -8,
                "description": "Manual savings adjustment",
                "jar": "savings",
            },
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["transaction_type"] == "adjustment"
        assert body["points"] == -8
        assert body["jar"] == "savings"

        db = TestingSessionLocal()
        try:
            balances = points_service.calculate_balances(db, child_id)
            assert balances["spending_balance"] == 100
            assert balances["savings_balance"] == 0
        finally:
            db.close()
    finally:
        app.dependency_overrides.clear()


def test_negative_admin_adjustment_greater_than_available_balance_fails_without_transaction():
    _, parent_id, child_id = _seed()
    client = _client(parent_id)
    db = TestingSessionLocal()
    try:
        parent_email = db.get(models.ParentUser, parent_id).email
        _add_balance(db, child_id, parent_id, 100, models.JarType.spending)
        _add_balance(db, child_id, parent_id, 3, models.JarType.savings)
        before_count = _ledger_count(child_id)
    finally:
        db.close()

    headers = _authenticate(client, parent_email)
    try:
        response = client.post(
            f"/api/children/{child_id}/adjustment",
            headers=headers,
            params={
                "points": -4,
                "description": "Too much savings adjustment",
                "jar": "savings",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Insufficient savings points"
        assert _ledger_count(child_id) == before_count
    finally:
        app.dependency_overrides.clear()


def test_positive_admin_adjustment_still_succeeds():
    _, parent_id, child_id = _seed()
    client = _client(parent_id)
    db = TestingSessionLocal()
    try:
        parent_email = db.get(models.ParentUser, parent_id).email
    finally:
        db.close()

    headers = _authenticate(client, parent_email)
    try:
        response = client.post(
            f"/api/children/{child_id}/adjustment",
            headers=headers,
            params={
                "points": 5,
                "description": "Manual positive adjustment",
                "jar": "spending",
            },
        )

        assert response.status_code == 200, response.text
        assert response.json()["points"] == 5
        assert response.json()["jar"] == "spending"
    finally:
        app.dependency_overrides.clear()


def test_admin_adjustment_requires_authentication():
    _, parent_id, child_id = _seed()
    client = _client(parent_id)
    csrf_token = "test-csrf-token"
    client.cookies.set("csrf_token", csrf_token)

    try:
        response = client.post(
            f"/api/children/{child_id}/adjustment",
            headers={"X-CSRF-Token": csrf_token},
            params={
                "points": 5,
                "description": "Manual adjustment",
                "jar": "spending",
            },
        )

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_admin_adjustment_respects_family_scoping():
    _, parent_id, child_id = _seed()
    db = TestingSessionLocal()
    try:
        other_family = models.Family(timezone="Asia/Muscat", week_start_day=6)
        db.add(other_family)
        db.commit()
        db.refresh(other_family)
        other_parent = models.ParentUser(
            email="other-adjustment@example.com",
            name="Other Parent",
            google_sub="sub-other-adjustment",
            family_id=other_family.id,
            status="active",
        )
        db.add(other_parent)
        db.commit()
        db.refresh(other_parent)
    finally:
        db.close()

    client = _client(parent_id)
    headers = _authenticate(client, "other-adjustment@example.com")
    try:
        response = client.post(
            f"/api/children/{child_id}/adjustment",
            headers=headers,
            params={
                "points": 5,
                "description": "Wrong family",
                "jar": "spending",
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Child not found"
    finally:
        app.dependency_overrides.clear()

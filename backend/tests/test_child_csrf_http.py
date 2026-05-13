import os
from datetime import datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import child_auth, database, models
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


def override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_family(db):
    family = models.Family(timezone="Asia/Muscat", week_start_day=6)
    db.add(family)
    db.commit()
    db.refresh(family)
    return family


def create_parent(db, family, email, name, google_sub):
    parent = models.ParentUser(
        email=email,
        name=name,
        google_sub=google_sub,
        family_id=family.id,
        status="active",
    )
    db.add(parent)
    db.commit()
    db.refresh(parent)
    return parent


def create_child(db, family, display_name="Kid"):
    child = models.Child(display_name=display_name, family_id=family.id, active=True)
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


def create_child_session(db, child, parent):
    invite, invite_token = child_auth.issue_child_device_invite(db, child, child.family_id, parent.id)
    _, session, session_token = child_auth.exchange_child_link(db, invite_token)
    return invite, session, session_token


def create_award(db, child, parent, points=50):
    db.add(models.LedgerTransaction(
        child_id=child.id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.award,
        points=points,
        description="Starting points",
        created_by_parent_id=parent.id,
    ))
    db.commit()


def make_client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_child_me_mints_csrf_for_valid_child_session():
    client = make_client()
    try:
        db = TestingSessionLocal()
        try:
            family = create_family(db)
            parent = create_parent(db, family, "csrf-parent@example.com", "Parent", "sub-parent")
            child = create_child(db, family)
            child_id = child.id
            _, _, session_token = create_child_session(db, child, parent)
        finally:
            db.close()

        client.cookies.clear()
        client.cookies.set("child_session", session_token)

        response = client.get("/api/child/me")

        assert response.status_code == 200
        assert response.json()["child"]["id"] == child_id
        assert client.cookies.get("csrf_token")
        assert "csrf_token" in (response.headers.get("set-cookie") or "")
    finally:
        app.dependency_overrides.clear()


def test_child_redemption_missing_csrf_is_blocked_before_handler():
    client = make_client()
    try:
        db = TestingSessionLocal()
        try:
            family = create_family(db)
            parent = create_parent(db, family, "csrf-parent2@example.com", "Parent", "sub-parent-2")
            child = create_child(db, family)
            child_id = child.id
            _, _, session_token = create_child_session(db, child, parent)
            create_award(db, child, parent, points=50)
        finally:
            db.close()

        client.cookies.clear()
        client.cookies.set("child_session", session_token)

        response = client.post(
            "/api/child/redemptions",
            json={"title": "Movie night", "points": 20, "description": "Requested from the child dashboard"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Missing CSRF token"
        check_db = TestingSessionLocal()
        try:
            assert check_db.query(models.RedemptionRequest).filter_by(child_id=child_id).count() == 0
            assert (
                check_db.query(models.LedgerTransaction)
                .filter(
                    models.LedgerTransaction.child_id == child_id,
                    models.LedgerTransaction.transaction_type == models.TransactionType.redemption_hold,
                )
                .count()
                == 0
            )
        finally:
            check_db.close()
    finally:
        app.dependency_overrides.clear()


def test_child_redemption_succeeds_after_child_me_mints_csrf():
    client = make_client()
    try:
        db = TestingSessionLocal()
        try:
            family = create_family(db)
            parent = create_parent(db, family, "csrf-parent3@example.com", "Parent", "sub-parent-3")
            child = create_child(db, family)
            child_id = child.id
            _, _, session_token = create_child_session(db, child, parent)
            create_award(db, child, parent, points=50)
        finally:
            db.close()

        client.cookies.clear()
        client.cookies.set("child_session", session_token)

        me_response = client.get("/api/child/me")
        assert me_response.status_code == 200

        csrf_token = client.cookies.get("csrf_token")
        assert csrf_token

        response = client.post(
            "/api/child/redemptions",
            headers={"X-CSRF-Token": csrf_token},
            json={"title": "Movie night", "points": 20, "description": "Requested from the child dashboard"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "pending"
        check_db = TestingSessionLocal()
        try:
            assert check_db.query(models.RedemptionRequest).filter_by(child_id=child_id).count() == 1
            assert (
                check_db.query(models.LedgerTransaction)
                .filter(
                    models.LedgerTransaction.child_id == child_id,
                    models.LedgerTransaction.transaction_type == models.TransactionType.redemption_hold,
                )
                .count()
                == 1
            )
            assert points_service.calculate_balances(check_db, child_id)["spending_balance"] == 30
        finally:
            check_db.close()
    finally:
        app.dependency_overrides.clear()


def test_child_redemption_invalid_csrf_fails():
    client = make_client()
    try:
        db = TestingSessionLocal()
        try:
            family = create_family(db)
            parent = create_parent(db, family, "csrf-parent4@example.com", "Parent", "sub-parent-4")
            child = create_child(db, family)
            child_id = child.id
            _, _, session_token = create_child_session(db, child, parent)
            create_award(db, child, parent, points=50)
        finally:
            db.close()

        client.cookies.clear()
        client.cookies.set("child_session", session_token)

        me_response = client.get("/api/child/me")
        assert me_response.status_code == 200

        response = client.post(
            "/api/child/redemptions",
            headers={"X-CSRF-Token": "wrong-token"},
            json={"title": "Movie night", "points": 20, "description": "Requested from the child dashboard"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid CSRF token"
        check_db = TestingSessionLocal()
        try:
            assert check_db.query(models.RedemptionRequest).filter_by(child_id=child_id).count() == 0
            assert (
                check_db.query(models.LedgerTransaction)
                .filter(
                    models.LedgerTransaction.child_id == child_id,
                    models.LedgerTransaction.transaction_type == models.TransactionType.redemption_hold,
                )
                .count()
                == 0
            )
        finally:
            check_db.close()
    finally:
        app.dependency_overrides.clear()


def test_child_link_exchange_rejects_expired_invite_cleanly():
    client = make_client()
    try:
        db = TestingSessionLocal()
        try:
            family = create_family(db)
            parent = create_parent(db, family, "expired-link-parent@example.com", "Parent", "sub-expired-link")
            child = create_child(db, family)
            invite, raw_token = child_auth.issue_child_device_invite(db, child, family.id, parent.id)
            invite_id = invite.id
            invite.expires_at = datetime.utcnow() - timedelta(minutes=1)
            db.commit()
        finally:
            db.close()

        response = client.post("/api/child-link/exchange", json={"token": raw_token})

        assert response.status_code == 401
        assert response.json()["detail"] == "Child link expired"

        check_db = TestingSessionLocal()
        try:
            assert check_db.query(models.ChildDeviceSession).count() == 0
            refreshed_invite = check_db.query(models.ChildDeviceInvite).filter_by(id=invite_id).one()
            assert refreshed_invite.used_at is None
        finally:
            check_db.close()
    finally:
        app.dependency_overrides.clear()


def test_child_me_without_session_does_not_mint_csrf():
    client = make_client()
    try:
        response = client.get("/api/child/me")

        assert response.status_code == 401
        assert client.cookies.get("csrf_token") is None
        assert "csrf_token" not in (response.headers.get("set-cookie") or "")
    finally:
        app.dependency_overrides.clear()


def test_expired_child_session_is_rejected_without_csrf():
    client = make_client()
    try:
        db = TestingSessionLocal()
        try:
            family = create_family(db)
            parent = create_parent(db, family, "csrf-parent5@example.com", "Parent", "sub-parent-5")
            child = create_child(db, family)
            _, session, session_token = create_child_session(db, child, parent)
            session.expires_at = datetime.utcnow() - timedelta(minutes=1)
            db.commit()
        finally:
            db.close()

        client.cookies.clear()
        client.cookies.set("child_session", session_token)

        response = client.get("/api/child/me")

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
        assert client.cookies.get("csrf_token") is None
        assert "csrf_token" not in (response.headers.get("set-cookie") or "")
    finally:
        app.dependency_overrides.clear()

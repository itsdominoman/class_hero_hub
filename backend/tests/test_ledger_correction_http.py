"""HTTP-level regression tests for the A6 "Correct this entry" endpoint.

These go through the actual FastAPI route (`POST /api/children/{child_id}/
ledger/{tx_id}/reverse`) via TestClient, not `points_service` directly. The
original A6 unit tests exercised the service function in isolation and so could
not catch a route/contract problem (wrong path, request-body shape, response
serialization, or — as happened on dev — a route that simply wasn't wired up in
the running app). This file closes that gap: if the endpoint is missing or its
request/response contract drifts, these fail.
"""
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

from datetime import datetime, timedelta

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
    """Fresh schema + a family/parent/child; returns ids."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        family = models.Family(timezone="Asia/Muscat", week_start_day=6)
        db.add(family)
        db.commit()
        db.refresh(family)
        parent = models.ParentUser(
            email="correct-http@example.com",
            name="Parent",
            google_sub="sub-correct-http",
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


def _add_tx(child_id, parent_id, points=1, jar=models.JarType.spending,
            tx_type=models.TransactionType.award, created_at=None):
    db = TestingSessionLocal()
    try:
        tx = models.LedgerTransaction(
            child_id=child_id,
            jar=jar,
            transaction_type=tx_type,
            points=points,
            description="Original",
            created_by_parent_id=parent_id,
        )
        if created_at is not None:
            tx.created_at = created_at
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx.id
    finally:
        db.close()


def _ledger_count(child_id):
    db = TestingSessionLocal()
    try:
        return db.query(models.LedgerTransaction).filter(
            models.LedgerTransaction.child_id == child_id
        ).count()
    finally:
        db.close()


def _client(parent_id):
    app.dependency_overrides[get_db] = _override_get_db

    def _fake_parent():
        session = TestingSessionLocal()
        try:
            return session.get(models.ParentUser, parent_id)
        finally:
            session.close()

    app.dependency_overrides[auth.get_current_parent] = _fake_parent
    return TestClient(app)


def test_reverse_endpoint_corrects_a_plain_award_end_to_end():
    """The basic success case that was failing on dev for every attempt."""
    _, parent_id, child_id = _seed()
    tx_id = _add_tx(child_id, parent_id, points=1)
    client = _client(parent_id)
    try:
        resp = client.post(
            f"/api/children/{child_id}/ledger/{tx_id}/reverse",
            json={"reason": "Awarded by mistake"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["transaction_type"] == "reversal"
        assert body["points"] == -1
        assert body["source_transaction_id"] == tx_id
        assert body["description"] == "Awarded by mistake"

        # Original row survives; balance nets to zero.
        db = TestingSessionLocal()
        try:
            assert db.query(models.LedgerTransaction).filter_by(id=tx_id).first() is not None
            from app.services import points_service
            assert points_service.calculate_balances(db, child_id)["spending_balance"] == 0
        finally:
            db.close()
    finally:
        app.dependency_overrides.clear()


def test_reverse_endpoint_accepts_missing_and_null_reason():
    _, parent_id, child_id = _seed()
    client = _client(parent_id)
    try:
        tx_a = _add_tx(child_id, parent_id, points=2)
        assert client.post(f"/api/children/{child_id}/ledger/{tx_a}/reverse", json={}).status_code == 200
        tx_b = _add_tx(child_id, parent_id, points=3)
        assert client.post(
            f"/api/children/{child_id}/ledger/{tx_b}/reverse", json={"reason": None}
        ).status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_reverse_endpoint_allows_correction_when_available_spending_remains():
    _, parent_id, child_id = _seed()
    tx_id = _add_tx(child_id, parent_id, points=5)
    _add_tx(child_id, parent_id, points=10)
    _add_tx(
        child_id,
        parent_id,
        points=-3,
        tx_type=models.TransactionType.redemption_hold,
    )
    client = _client(parent_id)
    try:
        resp = client.post(
            f"/api/children/{child_id}/ledger/{tx_id}/reverse",
            json={"reason": "Awarded by mistake"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["points"] == -5
        assert resp.json()["source_transaction_id"] == tx_id

        db = TestingSessionLocal()
        try:
            assert points_service.calculate_balances(db, child_id)["available_spending"] == 7
        finally:
            db.close()
    finally:
        app.dependency_overrides.clear()


def test_reverse_endpoint_allows_correction_to_project_exactly_zero():
    _, parent_id, child_id = _seed()
    tx_id = _add_tx(child_id, parent_id, points=10)
    _add_tx(
        child_id,
        parent_id,
        points=-4,
        tx_type=models.TransactionType.redemption_hold,
    )
    _add_tx(child_id, parent_id, points=4)
    client = _client(parent_id)
    try:
        resp = client.post(
            f"/api/children/{child_id}/ledger/{tx_id}/reverse",
            json={"reason": "Awarded by mistake"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["points"] == -10

        db = TestingSessionLocal()
        try:
            assert points_service.calculate_balances(db, child_id)["available_spending"] == 0
        finally:
            db.close()
    finally:
        app.dependency_overrides.clear()


def test_reverse_endpoint_blocks_when_award_points_were_spent():
    _, parent_id, child_id = _seed()
    tx_id = _add_tx(child_id, parent_id, points=10)
    _add_tx(
        child_id,
        parent_id,
        points=-7,
        tx_type=models.TransactionType.redemption_hold,
    )
    client = _client(parent_id)
    try:
        before_count = _ledger_count(child_id)
        db = TestingSessionLocal()
        try:
            before_balance = points_service.calculate_balances(db, child_id)["available_spending"]
            original = db.get(models.LedgerTransaction, tx_id)
            original_points = original.points
            original_type = original.transaction_type
            original_source = original.source_transaction_id
        finally:
            db.close()

        resp = client.post(
            f"/api/children/{child_id}/ledger/{tx_id}/reverse",
            json={"reason": "Awarded by mistake"},
        )

        assert resp.status_code == 400
        assert resp.json()["detail"] == "correction_insufficient_available_balance"
        assert _ledger_count(child_id) == before_count

        db = TestingSessionLocal()
        try:
            after_balance = points_service.calculate_balances(db, child_id)["available_spending"]
            original = db.get(models.LedgerTransaction, tx_id)
            assert after_balance == before_balance == 3
            assert original.points == original_points == 10
            assert original.transaction_type == original_type == models.TransactionType.award
            assert original.source_transaction_id == original_source
            assert db.query(models.LedgerTransaction).filter(
                models.LedgerTransaction.source_transaction_id == tx_id,
                models.LedgerTransaction.transaction_type == models.TransactionType.reversal,
            ).count() == 0
        finally:
            db.close()
    finally:
        app.dependency_overrides.clear()


def test_reverse_endpoint_rejects_with_specific_codes():
    _, parent_id, child_id = _seed()
    client = _client(parent_id)
    try:
        # Ineligible kind (savings deposit -> downstream effects).
        deposit = _add_tx(child_id, parent_id, jar=models.JarType.savings,
                          tx_type=models.TransactionType.savings_deposit)
        r = client.post(f"/api/children/{child_id}/ledger/{deposit}/reverse", json={})
        assert r.status_code == 400
        assert r.json()["detail"] == "correction_ineligible_type"

        # Outside the 7-day window.
        old = _add_tx(child_id, parent_id, points=1,
                      created_at=datetime.utcnow() - timedelta(days=8))
        r = client.post(f"/api/children/{child_id}/ledger/{old}/reverse", json={})
        assert r.status_code == 400
        assert r.json()["detail"] == "correction_window_expired"

        # Already corrected.
        tx = _add_tx(child_id, parent_id, points=1)
        assert client.post(f"/api/children/{child_id}/ledger/{tx}/reverse", json={}).status_code == 200
        r = client.post(f"/api/children/{child_id}/ledger/{tx}/reverse", json={})
        assert r.status_code == 409
        assert r.json()["detail"] == "correction_already_processed"

        # Unknown transaction id -> 404.
        r = client.post(f"/api/children/{child_id}/ledger/999999/reverse", json={})
        assert r.status_code == 404
    finally:
        app.dependency_overrides.clear()

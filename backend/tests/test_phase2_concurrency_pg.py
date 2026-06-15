"""Phase 2 PostgreSQL concurrency coverage for balance-affecting operations.

These tests use a disposable PostgreSQL database and separate sessions per
worker. SQLite is not sufficient for these checks because the guarantees depend
on concurrent transactions and PostgreSQL partial unique indexes.
"""
from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

_PG_USER = os.environ.get("POSTGRES_USER")
_PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
_PG_HOST = os.environ.get("POSTGRES_HOST", "postgres")
_PG_PORT = os.environ.get("POSTGRES_PORT", "5432")
_IS_PG = bool(_PG_USER and _PG_PASSWORD)
_REQUIRE_PG = os.environ.get("REQUIRE_PHASE2_PG_TESTS") == "1"
_TEST_DB_NAME = "fhh_phase2_concurrency_pg_test"

if _REQUIRE_PG and not _IS_PG:
    raise RuntimeError(
        "REQUIRE_PHASE2_PG_TESTS=1 but POSTGRES_USER/POSTGRES_PASSWORD are not set"
    )

pytestmark = pytest.mark.skipif(
    not _IS_PG,
    reason="POSTGRES_USER/POSTGRES_PASSWORD not set; Phase 2 concurrency tests need real PostgreSQL",
)


def _url_for(db_name: str) -> str:
    return f"postgresql+psycopg://{_PG_USER}:{_PG_PASSWORD}@{_PG_HOST}:{_PG_PORT}/{db_name}"


@pytest.fixture(scope="module")
def pg_engine():
    admin = create_engine(_url_for("postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {_TEST_DB_NAME}"))
        conn.execute(text(f"CREATE DATABASE {_TEST_DB_NAME}"))
    admin.dispose()

    engine = create_engine(_url_for(_TEST_DB_NAME))
    from app.database import Base
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        engine.dispose()
        admin = create_engine(_url_for("postgres"), isolation_level="AUTOCOMMIT")
        with admin.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": _TEST_DB_NAME},
            )
            conn.execute(text(f"DROP DATABASE IF EXISTS {_TEST_DB_NAME}"))
        admin.dispose()


@pytest.fixture
def Session(pg_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
    yield SessionLocal
    with pg_engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE "
                "ledger_transactions, redemption_requests, children, parent_users, families "
                "RESTART IDENTITY CASCADE"
            )
        )


def _seed_family(Session):
    from app import models

    db = Session()
    try:
        family = models.Family(timezone="Europe/Berlin", week_start_day=0)
        db.add(family)
        db.commit()
        parent = models.ParentUser(
            email="phase2-parent@example.com",
            name="Parent",
            google_sub="phase2-parent-sub",
            family_id=family.id,
            status="active",
        )
        child = models.Child(display_name="Kid", family_id=family.id, active=True)
        db.add_all([parent, child])
        db.commit()
        return family.id, parent.id, child.id
    finally:
        db.close()


def _add_spending_award(Session, child_id: int, parent_id: int, points: int = 100) -> int:
    from app import models

    db = Session()
    try:
        tx = models.LedgerTransaction(
            child_id=child_id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=points,
            description="Seed award",
            created_by_parent_id=parent_id,
        )
        db.add(tx)
        db.commit()
        return tx.id
    finally:
        db.close()


def _create_redemption(Session, child_id: int, parent_id: int, points: int = 40) -> int:
    from app import models

    db = Session()
    try:
        request = models.RedemptionRequest(
            child_id=child_id,
            points=points,
            title="Movie",
            description="Movie night",
            status=models.RedemptionStatus.pending,
        )
        db.add(request)
        db.flush()
        hold = models.LedgerTransaction(
            child_id=child_id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.redemption_hold,
            points=-points,
            description="Redemption Hold: Movie",
            redemption_request_id=request.id,
            created_by_parent_id=parent_id,
        )
        db.add(hold)
        db.commit()
        return request.id
    finally:
        db.close()


def _review(Session, request_id: int, parent_id: int, action: str, barrier: Barrier) -> tuple[int, str]:
    from app import models, schemas
    from app.routes import redemptions as redemption_routes

    db = Session()
    try:
        parent = db.get(models.ParentUser, parent_id)
        barrier.wait(timeout=10)
        try:
            if action == "approve":
                result = asyncio.run(
                    redemption_routes.approve_redemption(
                        request_id,
                        schemas.RedemptionReviewRequest(parent_note="ok"),
                        db,
                        parent,
                    )
                )
            else:
                result = asyncio.run(
                    redemption_routes.reject_redemption(
                        request_id,
                        schemas.RedemptionReviewRequest(parent_note="no"),
                        db,
                        parent,
                    )
                )
            return 200, result.status.value
        except HTTPException as exc:
            return exc.status_code, str(exc.detail)
    finally:
        db.close()


def _run_reviews(Session, request_id: int, parent_id: int, actions: list[str]) -> list[tuple[int, str]]:
    barrier = Barrier(len(actions))
    with ThreadPoolExecutor(max_workers=len(actions)) as executor:
        futures = [
            executor.submit(_review, Session, request_id, parent_id, action, barrier)
            for action in actions
        ]
        return [future.result(timeout=20) for future in futures]


def _release_count(Session, redemption_id: int) -> int:
    from app import models

    db = Session()
    try:
        return (
            db.query(models.LedgerTransaction)
            .filter(
                models.LedgerTransaction.redemption_request_id == redemption_id,
                models.LedgerTransaction.transaction_type == models.TransactionType.redemption_rejected,
            )
            .count()
        )
    finally:
        db.close()


def test_two_concurrent_rejects_release_points_once(Session):
    from app import models
    from app.services import points_service

    _family_id, parent_id, child_id = _seed_family(Session)
    _add_spending_award(Session, child_id, parent_id)
    redemption_id = _create_redemption(Session, child_id, parent_id)

    results = _run_reviews(Session, redemption_id, parent_id, ["reject", "reject"])

    assert sorted(status_code for status_code, _detail in results) == [200, 409]
    assert _release_count(Session, redemption_id) == 1

    db = Session()
    try:
        request = db.get(models.RedemptionRequest, redemption_id)
        assert request.status == models.RedemptionStatus.rejected
        assert points_service.calculate_balances(db, child_id)["spending_balance"] == 100
    finally:
        db.close()


def test_approve_and_reject_race_has_one_winner(Session):
    from app import models
    from app.services import points_service

    _family_id, parent_id, child_id = _seed_family(Session)
    _add_spending_award(Session, child_id, parent_id)
    redemption_id = _create_redemption(Session, child_id, parent_id)

    results = _run_reviews(Session, redemption_id, parent_id, ["approve", "reject"])

    assert sorted(status_code for status_code, _detail in results) == [200, 409]
    db = Session()
    try:
        request = db.get(models.RedemptionRequest, redemption_id)
        release_count = _release_count(Session, redemption_id)
        balance = points_service.calculate_balances(db, child_id)["spending_balance"]
        if request.status == models.RedemptionStatus.rejected:
            assert release_count == 1
            assert balance == 100
        else:
            assert request.status == models.RedemptionStatus.approved
            assert release_count == 0
            assert balance == 60
    finally:
        db.close()


def test_two_concurrent_approves_transition_once_and_retry_conflicts(Session):
    from app import models, schemas
    from app.routes import redemptions as redemption_routes

    _family_id, parent_id, child_id = _seed_family(Session)
    _add_spending_award(Session, child_id, parent_id)
    redemption_id = _create_redemption(Session, child_id, parent_id)

    results = _run_reviews(Session, redemption_id, parent_id, ["approve", "approve"])

    assert sorted(status_code for status_code, _detail in results) == [200, 409]
    assert _release_count(Session, redemption_id) == 0

    db = Session()
    try:
        parent = db.get(models.ParentUser, parent_id)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                redemption_routes.approve_redemption(
                    redemption_id,
                    schemas.RedemptionReviewRequest(parent_note="retry"),
                    db,
                    parent,
                )
            )
        assert exc.value.status_code == 409
    finally:
        db.close()


def _correct_worker(Session, child_id: int, parent_id: int, tx_id: int, barrier: Barrier) -> tuple[str, str]:
    from app.services import points_service

    db = Session()
    try:
        barrier.wait(timeout=10)
        try:
            reversal = points_service.correct_transaction(
                db,
                child_id,
                tx_id,
                reason="duplicate tap",
                created_by_parent_id=parent_id,
            )
            db.commit()
            return "ok", str(reversal.id)
        except points_service.CorrectionError as exc:
            db.rollback()
            return "error", exc.code
    finally:
        db.close()


def test_concurrent_corrections_create_one_reversal(Session):
    from app import models

    _family_id, parent_id, child_id = _seed_family(Session)
    tx_id = _add_spending_award(Session, child_id, parent_id, points=10)
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [
            future.result(timeout=20)
            for future in [
                executor.submit(_correct_worker, Session, child_id, parent_id, tx_id, barrier),
                executor.submit(_correct_worker, Session, child_id, parent_id, tx_id, barrier),
            ]
        ]

    assert sorted(status for status, _detail in results) == ["error", "ok"]
    assert [detail for status, detail in results if status == "error"] == ["correction_already_processed"]

    db = Session()
    try:
        reversals = (
            db.query(models.LedgerTransaction)
            .filter(
                models.LedgerTransaction.source_transaction_id == tx_id,
                models.LedgerTransaction.transaction_type == models.TransactionType.reversal,
            )
            .all()
        )
        assert len(reversals) == 1
    finally:
        db.close()


def test_reversal_unique_index_blocks_direct_duplicate_insert(Session):
    from app import models

    _family_id, parent_id, child_id = _seed_family(Session)
    tx_id = _add_spending_award(Session, child_id, parent_id, points=10)
    db = Session()
    try:
        db.add(
            models.LedgerTransaction(
                child_id=child_id,
                jar=models.JarType.spending,
                transaction_type=models.TransactionType.reversal,
                points=-10,
                source_transaction_id=tx_id,
                description="first",
            )
        )
        db.commit()
        db.add(
            models.LedgerTransaction(
                child_id=child_id,
                jar=models.JarType.spending,
                transaction_type=models.TransactionType.reversal,
                points=-10,
                source_transaction_id=tx_id,
                description="duplicate",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_redemption_hold_unique_index_blocks_direct_duplicate_insert(Session):
    from app import models

    _family_id, parent_id, child_id = _seed_family(Session)
    _add_spending_award(Session, child_id, parent_id)
    redemption_id = _create_redemption(Session, child_id, parent_id)

    db = Session()
    try:
        db.add(
            models.LedgerTransaction(
                child_id=child_id,
                jar=models.JarType.spending,
                transaction_type=models.TransactionType.redemption_hold,
                points=-40,
                redemption_request_id=redemption_id,
                description="duplicate hold",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_redemption_release_unique_index_blocks_direct_duplicate_insert(Session):
    from app import models

    _family_id, parent_id, child_id = _seed_family(Session)
    _add_spending_award(Session, child_id, parent_id)
    redemption_id = _create_redemption(Session, child_id, parent_id)

    db = Session()
    try:
        for description in ["first release", "duplicate release"]:
            db.add(
                models.LedgerTransaction(
                    child_id=child_id,
                    jar=models.JarType.spending,
                    transaction_type=models.TransactionType.redemption_rejected,
                    points=40,
                    redemption_request_id=redemption_id,
                    description=description,
                )
            )
            if description == "first release":
                db.commit()
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_redemption_ledger_fk_requires_matching_child(Session):
    from app import models

    family_id, parent_id, child_id = _seed_family(Session)
    db = Session()
    try:
        other_child = models.Child(display_name="Other Kid", family_id=family_id, active=True)
        db.add(other_child)
        db.commit()
        db.refresh(other_child)
        other_child_id = other_child.id
    finally:
        db.close()

    redemption_id = _create_redemption(Session, child_id, parent_id)
    db = Session()
    try:
        db.add(
            models.LedgerTransaction(
                child_id=other_child_id,
                jar=models.JarType.spending,
                transaction_type=models.TransactionType.redemption_rejected,
                points=40,
                redemption_request_id=redemption_id,
                description="wrong child release",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_different_source_transactions_can_be_corrected_independently(Session):
    from app import models
    from app.services import points_service

    _family_id, parent_id, child_id = _seed_family(Session)
    tx_a = _add_spending_award(Session, child_id, parent_id, points=10)
    tx_b = _add_spending_award(Session, child_id, parent_id, points=8)
    db = Session()
    try:
        a = points_service.correct_transaction(db, child_id, tx_a, created_by_parent_id=parent_id)
        b = points_service.correct_transaction(db, child_id, tx_b, created_by_parent_id=parent_id)
        db.commit()
        assert {a.source_transaction_id, b.source_transaction_id} == {tx_a, tx_b}
        assert (
            db.query(models.LedgerTransaction)
            .filter(models.LedgerTransaction.transaction_type == models.TransactionType.reversal)
            .count()
            == 2
        )
    finally:
        db.close()


def _create_mature_deposit(Session, child_id: int, parent_id: int, points: int, now: datetime) -> int:
    from app import models

    db = Session()
    try:
        deposit = models.LedgerTransaction(
            child_id=child_id,
            jar=models.JarType.savings,
            transaction_type=models.TransactionType.savings_deposit,
            points=points,
            description=f"Deposit {points}",
            locked_until=now - timedelta(minutes=1),
            created_by_parent_id=parent_id,
        )
        db.add(deposit)
        db.commit()
        return deposit.id
    finally:
        db.close()


def _mature_worker(Session, child_id: int, now: datetime, barrier: Barrier) -> int:
    from app.services import points_service

    db = Session()
    try:
        barrier.wait(timeout=10)
        rows = points_service.mature_savings_deposits(db, child_id, now=now)
        db.commit()
        return len(rows)
    finally:
        db.close()


def test_concurrent_savings_maturity_processes_deposit_once(Session):
    from app import models
    from app.services import points_service

    _family_id, parent_id, child_id = _seed_family(Session)
    now = datetime(2026, 6, 15, 12, 0, 0)
    deposit_id = _create_mature_deposit(Session, child_id, parent_id, 30, now)
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [
            future.result(timeout=20)
            for future in [
                executor.submit(_mature_worker, Session, child_id, now, barrier),
                executor.submit(_mature_worker, Session, child_id, now, barrier),
            ]
        ]

    assert sorted(results) == [0, 3]
    db = Session()
    try:
        assert (
            db.query(models.LedgerTransaction)
            .filter(
                models.LedgerTransaction.source_transaction_id == deposit_id,
                models.LedgerTransaction.transaction_type == models.TransactionType.savings_maturity,
            )
            .count()
            == 2
        )
        assert (
            db.query(models.LedgerTransaction)
            .filter(
                models.LedgerTransaction.source_transaction_id == deposit_id,
                models.LedgerTransaction.transaction_type == models.TransactionType.savings_bonus,
            )
            .count()
            == 1
        )
        assert points_service.calculate_balances(db, child_id, now=now)["spending_balance"] == 33
        assert points_service.mature_savings_deposits(db, child_id, now=now) == []
    finally:
        db.close()


def test_multiple_eligible_savings_deposits_process_correctly(Session):
    from app.services import points_service

    _family_id, parent_id, child_id = _seed_family(Session)
    now = datetime(2026, 6, 15, 12, 0, 0)
    _create_mature_deposit(Session, child_id, parent_id, 30, now)
    _create_mature_deposit(Session, child_id, parent_id, 6, now)
    db = Session()
    try:
        rows = points_service.mature_savings_deposits(db, child_id, now=now)
        db.commit()
        assert len(rows) == 6
        assert points_service.calculate_balances(db, child_id, now=now)["spending_balance"] == 40
    finally:
        db.close()


def test_savings_maturity_unique_index_blocks_direct_duplicate_insert(Session):
    from app import models

    _family_id, parent_id, child_id = _seed_family(Session)
    now = datetime(2026, 6, 15, 12, 0, 0)
    deposit_id = _create_mature_deposit(Session, child_id, parent_id, 30, now)

    db = Session()
    try:
        for description in ["first maturity", "duplicate maturity"]:
            db.add(
                models.LedgerTransaction(
                    child_id=child_id,
                    jar=models.JarType.savings,
                    transaction_type=models.TransactionType.savings_maturity,
                    points=-30,
                    source_transaction_id=deposit_id,
                    description=description,
                )
            )
            if description == "first maturity":
                db.commit()
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_savings_bonus_unique_index_blocks_direct_duplicate_insert(Session):
    from app import models

    _family_id, parent_id, child_id = _seed_family(Session)
    now = datetime(2026, 6, 15, 12, 0, 0)
    deposit_id = _create_mature_deposit(Session, child_id, parent_id, 30, now)

    db = Session()
    try:
        for description in ["first bonus", "duplicate bonus"]:
            db.add(
                models.LedgerTransaction(
                    child_id=child_id,
                    jar=models.JarType.spending,
                    transaction_type=models.TransactionType.savings_bonus,
                    points=3,
                    source_transaction_id=deposit_id,
                    description=description,
                )
            )
            if description == "first bonus":
                db.commit()
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_maturity_nested_failure_rolls_back_only_failed_duplicate(Session):
    from app import models
    from app.services import points_service

    _family_id, parent_id, child_id = _seed_family(Session)
    now = datetime(2026, 6, 15, 12, 0, 0)
    duplicate_deposit = _create_mature_deposit(Session, child_id, parent_id, 30, now)
    fresh_deposit = _create_mature_deposit(Session, child_id, parent_id, 6, now)

    db = Session()
    try:
        db.add(
            models.LedgerTransaction(
                child_id=child_id,
                jar=models.JarType.savings,
                transaction_type=models.TransactionType.savings_maturity,
                points=-30,
                description="pre-existing duplicate blocker",
                source_transaction_id=duplicate_deposit,
            )
        )
        db.commit()

        rows = points_service.mature_savings_deposits(db, child_id, now=now)
        db.commit()
        assert {row.source_transaction_id for row in rows} == {fresh_deposit}
        assert len(rows) == 3
    finally:
        db.close()

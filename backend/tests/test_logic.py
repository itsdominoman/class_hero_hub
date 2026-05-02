import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app import models, schemas
from app.services import points_service
from datetime import datetime, timedelta

# Setup in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_pet_stage_evolution(db):
    child = models.Child(display_name="Test Kid")
    db.add(child)
    db.commit()
    db.refresh(child)

    # Initial stage: egg
    pet = points_service.update_pet_progress(db, child.id, 0, False)
    assert pet.current_stage == models.PetStage.egg

    # Hatchling: 50 points
    pet = points_service.update_pet_progress(db, child.id, 50, True)
    assert pet.current_stage == models.PetStage.hatchling

    # Beast: 600 points
    pet = points_service.update_pet_progress(db, child.id, 550, True)
    assert pet.current_stage == models.PetStage.beast

def test_balance_calculation_with_locks(db):
    child = models.Child(display_name="Test Kid")
    db.add(child)
    db.commit()
    db.refresh(child)

    # Award 100 spending
    tx1 = models.LedgerTransaction(
        child_id=child.id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.award,
        points=100,
        description="Award"
    )
    db.add(tx1)

    # Award 50 savings (locked)
    locked_until = datetime.utcnow() + timedelta(days=30)
    tx2 = models.LedgerTransaction(
        child_id=child.id,
        jar=models.JarType.savings,
        transaction_type=models.TransactionType.award,
        points=50,
        description="Savings Award",
        locked_until=locked_until
    )
    db.add(tx2)
    db.commit()

    balances = points_service.calculate_balances(db, child.id)
    assert balances["spending_balance"] == 100
    assert balances["savings_balance"] == 50
    assert balances["locked_savings"] == 50
    assert balances["available_savings"] == 0

def test_redemption_hold_and_release(db):
    child = models.Child(display_name="Test Kid")
    db.add(child)
    db.commit()
    db.refresh(child)

    # Award 100
    tx1 = models.LedgerTransaction(
        child_id=child.id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.award,
        points=100,
        description="Award"
    )
    db.add(tx1)
    db.commit()

    # Hold 40
    hold_tx = models.LedgerTransaction(
        child_id=child.id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.redemption_hold,
        points=-40,
        description="Hold"
    )
    db.add(hold_tx)
    db.commit()

    balances = points_service.calculate_balances(db, child.id)
    assert balances["spending_balance"] == 60

    # Release (Reject)
    release_tx = models.LedgerTransaction(
        child_id=child.id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.redemption_rejected,
        points=40,
        description="Release"
    )
    db.add(release_tx)
    db.commit()

    balances = points_service.calculate_balances(db, child.id)
    assert balances["spending_balance"] == 100


def test_ledger_summary_and_filters(db):
    child = models.Child(display_name="Summary Kid")
    db.add(child)
    db.commit()
    db.refresh(child)

    now = datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)

    transactions = [
        models.LedgerTransaction(child_id=child.id, jar=models.JarType.spending, transaction_type=models.TransactionType.award, points=20, description="Award", created_at=now),
        models.LedgerTransaction(child_id=child.id, jar=models.JarType.spending, transaction_type=models.TransactionType.penalty, points=-3, description="Penalty", created_at=now),
        models.LedgerTransaction(child_id=child.id, jar=models.JarType.spending, transaction_type=models.TransactionType.savings_deposit, points=-10, description="Move to savings", created_at=now),
        models.LedgerTransaction(child_id=child.id, jar=models.JarType.savings, transaction_type=models.TransactionType.savings_deposit, points=10, description="Move to savings", created_at=now),
        models.LedgerTransaction(child_id=child.id, jar=models.JarType.spending, transaction_type=models.TransactionType.redemption_hold, points=-6, description="Hold", created_at=now),
        models.LedgerTransaction(child_id=child.id, jar=models.JarType.spending, transaction_type=models.TransactionType.redemption_rejected, points=6, description="Release", created_at=now),
        models.LedgerTransaction(child_id=child.id, jar=models.JarType.spending, transaction_type=models.TransactionType.adjustment, points=5, description="Adjustment", created_at=now),
    ]
    db.add_all(transactions)
    db.commit()

    summary = points_service.get_ledger_summary(db, child.id, period="month")
    assert summary["gained"] == 25
    assert summary["lost"] == 3
    assert summary["spent"] == 6
    assert summary["net"] == 16
    assert summary["saved_in"] == 10
    assert summary["saved_out"] == 0
    assert summary["held"] == 0
    assert summary["released"] == 6
    assert summary["transaction_count"] == 7

    earned = points_service.get_ledger_transactions(db, child.id, period="month", tx_type="earned")
    assert len(earned) == 2

    saved = points_service.get_ledger_transactions(db, child.id, period="month", tx_type="saved")
    assert len(saved) == 2

    held = points_service.get_ledger_transactions(db, child.id, period="month", tx_type="held")
    assert len(held) == 1

    spent = points_service.get_ledger_transactions(db, child.id, period="month", tx_type="spent")
    assert len(spent) == 1


def test_redemption_approval_marker_does_not_double_count_balance(db):
    child = models.Child(display_name="Approval Kid")
    db.add(child)
    db.commit()
    db.refresh(child)

    db.add_all([
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=100,
            description="Award",
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.redemption_hold,
            points=-40,
            description="Hold",
        ),
    ])
    db.commit()

    balances = points_service.calculate_balances(db, child.id)
    assert balances["spending_balance"] == 60

    summary = points_service.get_ledger_summary(db, child.id, period="month")
    assert summary["spent"] == 40
    assert summary["held"] == 0
    assert summary["transaction_count"] == 2


def test_period_filter_uses_exact_end_boundaries(db):
    child = models.Child(display_name="Boundary Kid")
    db.add(child)
    db.commit()
    db.refresh(child)

    now = datetime(2026, 5, 6, 12, 0, 0)
    start_of_day = datetime(2026, 5, 6, 0, 0, 0)
    start_next_day = datetime(2026, 5, 7, 0, 0, 0)
    start_of_week = datetime(2026, 5, 4, 0, 0, 0)
    start_next_week = datetime(2026, 5, 11, 0, 0, 0)
    start_of_month = datetime(2026, 5, 1, 0, 0, 0)
    start_next_month = datetime(2026, 6, 1, 0, 0, 0)

    db.add_all([
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=1,
            description="Day start",
            created_at=start_of_day,
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=2,
            description="Day end exclusive",
            created_at=start_next_day,
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=3,
            description="Week start",
            created_at=start_of_week,
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=4,
            description="Week end exclusive",
            created_at=start_next_week,
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=5,
            description="Month start",
            created_at=start_of_month,
        ),
        models.LedgerTransaction(
            child_id=child.id,
            jar=models.JarType.spending,
            transaction_type=models.TransactionType.award,
            points=6,
            description="Month end exclusive",
            created_at=start_next_month,
        ),
    ])
    db.commit()

    day_txs = points_service.get_ledger_transactions(db, child.id, period="day", now=now)
    assert [tx.points for tx in day_txs] == [1]

    week_txs = points_service.get_ledger_transactions(db, child.id, period="week", now=now)
    assert [tx.points for tx in week_txs] == [2, 1, 3]

    month_txs = points_service.get_ledger_transactions(db, child.id, period="month", now=now)
    assert [tx.points for tx in month_txs] == [4, 2, 1, 3, 5]

    day_summary = points_service.get_ledger_summary(db, child.id, period="day", now=now)
    assert day_summary["gained"] == 1
    assert day_summary["transaction_count"] == 1

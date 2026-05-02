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

import pytest
import asyncio
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app import models, schemas
from app.services import points_service
from app.services.rewards_service import get_family_rewards
from app.routes import child_access as child_access_routes
from app.routes import children as child_routes
from app.routes import family as family_routes
from app.routes import ledger as ledger_routes
from app.routes import rewards as reward_routes
from app.routes import redemptions as redemption_routes
from app import auth, child_auth
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

def test_preset_behaviour_crud(db):
    parent = models.ParentUser(email="preset@example.com", name="Preset Parent")
    db.add(parent)
    db.commit()
    db.refresh(parent)

    # Create
    preset = models.PresetBehaviour(
        parent_id=parent.id,
        title="Brush Teeth",
        points=5,
        icon="🪥"
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    assert preset.id is not None
    assert preset.title == "Brush Teeth"
    assert preset.icon == "🪥"

    # Query
    presets = db.query(models.PresetBehaviour).filter_by(parent_id=parent.id).all()
    assert len(presets) == 1

    # Update
    preset.points = 10
    db.commit()
    db.refresh(preset)
    assert preset.points == 10

    # Delete
    db.delete(preset)
    db.commit()
    assert db.query(models.PresetBehaviour).filter_by(parent_id=parent.id).count() == 0

def test_reward_crud_and_family_scope(db):
    family = models.Family()
    other_family = models.Family()
    db.add_all([family, other_family])
    db.commit()

    parent = models.ParentUser(email="reward@example.com", name="Reward Parent", family_id=family.id)
    other_parent = models.ParentUser(email="other-reward@example.com", name="Other Parent", family_id=other_family.id)
    db.add_all([parent, other_parent])
    db.commit()
    db.refresh(parent)
    db.refresh(other_parent)

    created = asyncio.run(reward_routes.create_reward(
        schemas.RewardCreate(title="Movie night", points=30, description="Family movie"),
        db,
        parent,
    ))
    assert created.title == "Movie night"
    assert created.points == 30

    other_created = asyncio.run(reward_routes.create_reward(
        schemas.RewardCreate(title="Other family reward", points=20, description=""),
        db,
        other_parent,
    ))
    assert other_created.family_id == other_family.id

    rewards = get_family_rewards(db, family.id)
    assert len(rewards) == 1
    assert rewards[0].title == "Movie night"

    updated = asyncio.run(reward_routes.update_reward(
        created.id,
        schemas.RewardCreate(title="Movie night+", points=35, description="Updated", is_active=False),
        db,
        parent,
    ))
    assert updated.title == "Movie night+"
    assert updated.points == 35
    assert updated.is_active is False

    asyncio.run(reward_routes.delete_reward(created.id, db, parent))
    assert db.query(models.Reward).filter_by(family_id=family.id).count() == 0
    assert db.query(models.Reward).filter_by(family_id=other_family.id).count() == 1

def test_family_support(db):
    # Setup two families
    f1 = models.Family()
    f2 = models.Family()
    db.add_all([f1, f2])
    db.commit()

    # Setup parents
    p1 = models.ParentUser(email="p1@f1.com", name="P1", family_id=f1.id)
    p1_coparent = models.ParentUser(email="p1_co@f1.com", name="P1 Co", family_id=f1.id)
    p2 = models.ParentUser(email="p2@f2.com", name="P2", family_id=f2.id)
    db.add_all([p1, p1_coparent, p2])
    db.commit()

    # Setup children
    c1 = models.Child(display_name="C1", family_id=f1.id)
    c2 = models.Child(display_name="C2", family_id=f2.id)
    db.add_all([c1, c2])
    db.commit()

    # Setup presets
    pr1 = models.PresetBehaviour(title="Pr1", points=10, family_id=f1.id, parent_id=p1.id)
    db.add(pr1)
    db.commit()

    # Verify P1 sees C1 but not C2
    from app.routes import children as child_routes
    # We'd need to mock auth.get_current_parent or call routes directly
    # For logic test, we check DB queries which routes use
    
    f1_children = db.query(models.Child).filter(models.Child.family_id == f1.id).all()
    assert len(f1_children) == 1
    assert f1_children[0].display_name == "C1"

    f2_children = db.query(models.Child).filter(models.Child.family_id == f2.id).all()
    assert len(f2_children) == 1
    assert f2_children[0].display_name == "C2"

    # Verify co-parent sees same children
    p1_co_family_children = db.query(models.Child).filter(models.Child.family_id == p1_coparent.family_id).all()
    assert len(p1_co_family_children) == 1
    assert p1_co_family_children[0].display_name == "C1"

    # Verify presets are shared in family
    p1_co_family_presets = db.query(models.PresetBehaviour).filter(models.PresetBehaviour.family_id == p1_coparent.family_id).all()
    assert len(p1_co_family_presets) == 1
    assert p1_co_family_presets[0].title == "Pr1"

def test_family_invite_flow(db):
    # Setup first parent and family
    f1 = models.Family()
    db.add(f1)
    db.commit()
    p1 = models.ParentUser(email="p1@f1.com", name="P1", family_id=f1.id)
    db.add(p1)
    db.commit()

    # P1 invites P2
    p2_email = "p2@f1.com"
    invite = models.FamilyInvite(family_id=f1.id, email=p2_email, invited_by_parent_id=p1.id)
    db.add(invite)
    db.commit()

    # Simulate P2 registration/callback logic
    # In a real app, this happens in authentication.py callback
    existing_invite = db.query(models.FamilyInvite).filter(
        models.FamilyInvite.email == p2_email,
        models.FamilyInvite.status == "pending"
    ).first()
    
    assert existing_invite is not None
    
    p2 = models.ParentUser(
        email=p2_email,
        name="P2",
        google_sub="p2_sub",
        family_id=existing_invite.family_id
    )
    existing_invite.status = "accepted"
    existing_invite.accepted_at = models.func.now()
    db.add(p2)
    db.commit()

    # Verify P2 is in P1's family
    assert p2.family_id == p1.family_id
    assert db.query(models.FamilyInvite).filter_by(email=p2_email).first().status == "accepted"


def create_two_family_context(db):
    f1 = models.Family()
    f2 = models.Family()
    db.add_all([f1, f2])
    db.commit()

    p1 = models.ParentUser(email="p1@example.com", name="P1", family_id=f1.id)
    p2 = models.ParentUser(email="p2@example.com", name="P2", family_id=f2.id)
    db.add_all([p1, p2])
    db.commit()

    c1 = models.Child(display_name="C1", family_id=f1.id)
    c2 = models.Child(display_name="C2", family_id=f2.id)
    db.add_all([c1, c2])
    db.commit()
    db.refresh(p1)
    db.refresh(p2)
    db.refresh(c1)
    db.refresh(c2)
    return p1, p2, c1, c2


def test_cross_family_ledger_read_denied(db):
    p1, _p2, _c1, c2 = create_two_family_context(db)
    db.add(models.LedgerTransaction(
        child_id=c2.id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.award,
        points=10,
        description="Other family award",
        created_by_parent_id=p1.id,
    ))
    db.commit()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(ledger_routes.get_ledger(c2.id, "month", "all", db, p1))

    assert exc.value.status_code == 404


def test_cross_family_ledger_write_denied(db):
    p1, _p2, _c1, c2 = create_two_family_context(db)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(ledger_routes.award_points(
            c2.id,
            schemas.AwardRequest(points=5, description="Bad write"),
            db,
            p1,
        ))

    assert exc.value.status_code == 404
    assert db.query(models.LedgerTransaction).filter_by(child_id=c2.id).count() == 0


def test_cross_family_redemption_list_excludes_other_family(db):
    p1, _p2, c1, c2 = create_two_family_context(db)
    db.add_all([
        models.RedemptionRequest(child_id=c1.id, points=5, title="Own", description="", status=models.RedemptionStatus.pending),
        models.RedemptionRequest(child_id=c2.id, points=7, title="Other", description="", status=models.RedemptionStatus.pending),
    ])
    db.commit()

    redemptions = asyncio.run(redemption_routes.get_all_redemptions(db, p1))

    assert len(redemptions) == 1
    assert redemptions[0].child_id == c1.id


def test_cross_family_redemption_approve_reject_denied(db):
    p1, _p2, _c1, c2 = create_two_family_context(db)
    request = models.RedemptionRequest(
        child_id=c2.id,
        points=7,
        title="Other",
        description="",
        status=models.RedemptionStatus.pending,
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    with pytest.raises(HTTPException) as approve_exc:
        asyncio.run(redemption_routes.approve_redemption(
            request.id,
            schemas.RedemptionReviewRequest(parent_note="no"),
            db,
            p1,
        ))
    with pytest.raises(HTTPException) as reject_exc:
        asyncio.run(redemption_routes.reject_redemption(
            request.id,
            schemas.RedemptionReviewRequest(parent_note="no"),
            db,
            p1,
        ))

    assert approve_exc.value.status_code == 404
    assert reject_exc.value.status_code == 404
    db.refresh(request)
    assert request.status == models.RedemptionStatus.pending


def test_cross_family_redemption_create_denied(db):
    p1, _p2, _c1, c2 = create_two_family_context(db)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(redemption_routes.request_redemption(
            c2.id,
            schemas.RedemptionRequestCreate(points=5, title="Other", description=""),
            db,
            p1,
        ))

    assert exc.value.status_code == 404
    assert db.query(models.RedemptionRequest).filter_by(child_id=c2.id).count() == 0


def test_child_reward_request_surfaces_to_parent_and_respects_balance(db):
    family = models.Family()
    db.add(family)
    db.commit()

    parent = models.ParentUser(email="parent@example.com", name="Parent", family_id=family.id)
    child = models.Child(display_name="Kid", family_id=family.id, active=True)
    db.add_all([parent, child])
    db.commit()
    db.refresh(parent)
    db.refresh(child)

    db.add(models.LedgerTransaction(
        child_id=child.id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.award,
        points=50,
        description="Starting points",
        created_by_parent_id=parent.id,
    ))
    db.commit()

    request = asyncio.run(child_access_routes.request_my_redemption(
        schemas.RedemptionRequestCreate(points=20, title="Movie night", description="Requested from the child dashboard"),
        db,
        child,
    ))
    assert request.status == models.RedemptionStatus.pending
    assert request.child_id == child.id

    parent_redemptions = asyncio.run(redemption_routes.get_all_redemptions(db, parent))
    assert len(parent_redemptions) == 1
    assert parent_redemptions[0].id == request.id
    assert parent_redemptions[0].title == "Movie night"

    balances = points_service.calculate_balances(db, child.id)
    assert balances["spending_balance"] == 30

    approved = asyncio.run(redemption_routes.approve_redemption(
        request.id,
        schemas.RedemptionReviewRequest(parent_note="Approved"),
        db,
        parent,
    ))
    assert approved.status == models.RedemptionStatus.approved

    db.refresh(request)
    assert request.status == models.RedemptionStatus.approved
    balances_after_approve = points_service.calculate_balances(db, child.id)
    assert balances_after_approve["spending_balance"] == 30

    # Create a second request, then reject it and ensure the held points are released.
    second_request = asyncio.run(child_access_routes.request_my_redemption(
        schemas.RedemptionRequestCreate(points=10, title="Ice cream", description="Requested from the child dashboard"),
        db,
        child,
    ))
    assert second_request.status == models.RedemptionStatus.pending

    balances_with_second_hold = points_service.calculate_balances(db, child.id)
    assert balances_with_second_hold["spending_balance"] == 20

    rejected = asyncio.run(redemption_routes.reject_redemption(
        second_request.id,
        schemas.RedemptionReviewRequest(parent_note="Not today"),
        db,
        parent,
    ))
    assert rejected.status == models.RedemptionStatus.rejected
    balances_after_reject = points_service.calculate_balances(db, child.id)
    assert balances_after_reject["spending_balance"] == 30


def test_child_invite_exchange_creates_session_for_correct_child(db):
    family = models.Family()
    db.add(family)
    db.commit()

    parent = models.ParentUser(email="parent-device@example.com", name="Parent", family_id=family.id)
    jackson = models.Child(display_name="Jackson", family_id=family.id, active=True)
    leah = models.Child(display_name="Leah", family_id=family.id, active=True)
    db.add_all([parent, jackson, leah])
    db.commit()
    db.refresh(parent)
    db.refresh(jackson)
    db.refresh(leah)

    invite, raw_token = child_auth.issue_child_device_invite(db, jackson, family.id, parent.id)
    exchanged_invite, session, session_token = child_auth.exchange_child_link(db, raw_token)
    context = child_auth.resolve_child_session(db, session_token)

    assert exchanged_invite.id == invite.id
    assert session.child_id == jackson.id
    assert session.family_id == family.id
    assert context.child.id == jackson.id
    assert context.child.id != leah.id


def test_child_dashboard_routes_survive_rejected_child_redemption(db):
    family = models.Family()
    db.add(family)
    db.commit()

    parent = models.ParentUser(email="parent-redemption@example.com", name="Parent", family_id=family.id)
    child = models.Child(display_name="Jackson", family_id=family.id, active=True)
    db.add_all([parent, child])
    db.commit()
    db.refresh(parent)
    db.refresh(child)

    db.add(models.LedgerTransaction(
        child_id=child.id,
        jar=models.JarType.spending,
        transaction_type=models.TransactionType.award,
        points=25,
        description="Starting points",
        created_by_parent_id=parent.id,
    ))
    db.commit()

    request = asyncio.run(child_access_routes.request_my_redemption(
        schemas.RedemptionRequestCreate(points=5, title="Screen time", description="Requested by child"),
        db,
        child,
    ))
    rejected = asyncio.run(redemption_routes.reject_redemption(
        request.id,
        schemas.RedemptionReviewRequest(parent_note="Just a test"),
        db,
        parent,
    ))
    assert rejected.status == models.RedemptionStatus.rejected

    dashboard = asyncio.run(child_access_routes.get_my_dashboard(db, child))
    ledger = asyncio.run(child_access_routes.get_my_ledger("month", "all", db, child))
    summary = asyncio.run(child_access_routes.get_my_ledger_summary("month", db, child))
    redemptions = asyncio.run(child_access_routes.get_my_redemptions(db, child))

    assert dashboard["child"].id == child.id
    assert summary["released"] == 5
    assert any(tx.created_by_parent_id is None for tx in ledger)
    assert any(req.status == models.RedemptionStatus.rejected for req in redemptions)

    serialized_ledger = [schemas.LedgerTransaction.model_validate(tx) for tx in ledger]
    assert any(tx.created_by_parent_id is None for tx in serialized_ledger)


def test_invite_email_normalization_and_case_insensitive_duplicate_prevention(db):
    family = models.Family()
    db.add(family)
    db.commit()
    parent = models.ParentUser(email="parent@example.com", family_id=family.id)
    db.add(parent)
    db.commit()
    db.refresh(parent)

    invite = asyncio.run(family_routes.create_family_invite(
        schemas.FamilyInviteCreate(email="CoParent@Example.COM"),
        db,
        parent,
    ))

    assert invite.email == "coparent@example.com"
    with pytest.raises(HTTPException) as exc:
        asyncio.run(family_routes.create_family_invite(
            schemas.FamilyInviteCreate(email="coparent@example.com"),
            db,
            parent,
        ))

    assert exc.value.status_code == 400


def test_self_invite_blocked(db):
    family = models.Family()
    db.add(family)
    db.commit()
    parent = models.ParentUser(email="parent@example.com", family_id=family.id)
    db.add(parent)
    db.commit()
    db.refresh(parent)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(family_routes.create_family_invite(
            schemas.FamilyInviteCreate(email="PARENT@example.com"),
            db,
            parent,
        ))

    assert exc.value.status_code == 400


def test_inviting_existing_family_member_blocked(db):
    family = models.Family()
    db.add(family)
    db.commit()
    parent = models.ParentUser(email="parent@example.com", family_id=family.id)
    member = models.ParentUser(email="member@example.com", family_id=family.id)
    db.add_all([parent, member])
    db.commit()
    db.refresh(parent)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(family_routes.create_family_invite(
            schemas.FamilyInviteCreate(email="MEMBER@example.com"),
            db,
            parent,
        ))

    assert exc.value.status_code == 400


def test_only_pending_invites_can_be_revoked(db):
    family = models.Family()
    db.add(family)
    db.commit()
    parent = models.ParentUser(email="parent@example.com", family_id=family.id)
    db.add(parent)
    db.commit()
    db.refresh(parent)
    invite = models.FamilyInvite(
        family_id=family.id,
        email="accepted@example.com",
        status="accepted",
        invited_by_parent_id=parent.id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(family_routes.revoke_family_invite(invite.id, db, parent))

    assert exc.value.status_code == 404


def test_parent_with_null_family_id_is_repaired_and_does_not_see_null_family_children(db):
    parent = models.ParentUser(email="null-family@example.com")
    null_child = models.Child(display_name="Legacy Null Child")
    db.add_all([parent, null_child])
    db.commit()
    db.refresh(parent)

    repaired_parent = auth.ensure_parent_family(db, parent)
    children = asyncio.run(child_routes.get_children(db, repaired_parent))

    assert repaired_parent.family_id is not None
    assert children == []


def test_presets_reject_empty_title_and_zero_points(db):
    with pytest.raises(ValidationError):
        schemas.PresetBehaviourCreate(title="   ", points=5)

    with pytest.raises(ValidationError):
        schemas.PresetBehaviourCreate(title="Valid", points=0)

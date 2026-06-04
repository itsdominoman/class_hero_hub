from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .. import auth, child_auth, models
from . import calendar_service

QA_CHILD_PARENT_EMAIL = "qa-child-parent@dev.familyherohub.com"
QA_CHILD_PARENT_NAME = "QA Child Parent"
QA_CHILD_DISPLAY_NAME = "QA Seed Child"
QA_CHILD_FAMILY_TIMEZONE = "Europe/Berlin"
QA_CHILD_AVATAR_NAME = "1"
QA_CHILD_ALLOWANCE_CURRENCY = "USD"
QA_CHILD_ALLOWANCE_AMOUNT_MINOR = 2500
QA_CHILD_ALLOWANCE_POINT_GOAL = 50
QA_CHILD_SESSION_SEED = "qa-child-session"
QA_PARENT_CARD_SPECS = [
    {
        "display_name": "Jackson",
        "avatar_name": "2",
        "spending_points": 58,
        "savings_points": 30,
        "pending_requests": [
            {
                "title": "Jackson wants game time",
                "description": "QA pending request used to keep the parent child-card row visible.",
                "points": 5,
            }
        ],
    },
    {
        "display_name": "Leah",
        "avatar_name": "1",
        "spending_points": 42,
        "savings_points": 18,
        "pending_requests": [],
    },
]

QA_REWARD_SPECS = [
    {
        "title": "QA Reward Short",
        "description": "Short reward.",
        "points": 5,
    },
    {
        "title": "QA Reward Very Long Name Designed To Stress Mobile Card Wrapping",
        "description": "Long name reward used to force narrow mobile cards to wrap the title and allowance badge correctly.",
        "points": 12,
    },
    {
        "title": "QA Reward Long Description Stress Case",
        "description": (
            "This reward description is intentionally long so the child reward cards, "
            "helper badges, and mobile spacing all get exercised together without "
            "needing a brittle pixel snapshot."
        ),
        "points": 18,
    },
    {
        "title": "QA Reward Bonus",
        "description": "Extra reward card to keep the grid dense on phones.",
        "points": 30,
    },
]

QA_PENDING_REQUEST_SPECS = [
    {
        "title": "QA Pending Request",
        "description": "Pending request used to keep the waiting requests card visible.",
        "points": 15,
    },
    {
        "title": "QA Waiting Request",
        "description": "Second waiting request to keep the approval queue visible on mobile.",
        "points": 12,
    },
]

QA_TASK_SPECS = [
    {
        "title": "QA Task Pack Bag",
        "description": "Pack the school bag and make sure the notebook is ready.",
        "points_value": 8,
    },
]

QA_EVENT_SPECS = [
    {
        "title": "QA Event Piano Lesson",
        "description": "Piano lesson after school so the events card stays visible.",
    },
]

QA_SCHOOL_ITEM_SPECS = [
    {
        "weekday_offset": 0,
        "class_name": "QA School Bag Pack",
        "needed_item": "Pack the school bag and notebook.",
    },
    {
        "weekday_offset": 1,
        "class_name": "QA School Bag Piano",
        "needed_item": "Bring the music book.",
    },
]


@dataclass
class QAChildSeedResult:
    parent: models.ParentUser
    family: models.Family
    child: models.Child
    reused: bool

    @property
    def child_route(self) -> str:
        return f"/child/{self.child.id}"


def _current_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _child_session_seed() -> str:
    return (child_auth.settings.QA_CHILD_LOGIN_TOKEN or child_auth.settings.QA_LOGIN_TOKEN or "").strip()


def _deterministic_child_session_token(child_id: int) -> str:
    seed = _child_session_seed()
    if not seed:
        raise RuntimeError("QA child login token is not configured")

    digest = hashlib.sha256(f"{seed}:{QA_CHILD_SESSION_SEED}:{child_id}".encode("utf-8")).hexdigest()
    return f"qa-child-session:{digest}"


def _reset_child_seed_rows(db: Session, child_id: int, family_id: int) -> None:
    db.query(models.CalendarCompletion).filter(models.CalendarCompletion.child_id == child_id).delete(synchronize_session=False)
    db.query(models.CalendarEntry).filter(models.CalendarEntry.child_id == child_id).delete(synchronize_session=False)
    db.query(models.RedemptionRequest).filter(models.RedemptionRequest.child_id == child_id).delete(synchronize_session=False)
    db.query(models.LedgerTransaction).filter(models.LedgerTransaction.child_id == child_id).delete(synchronize_session=False)
    db.query(models.SchoolItem).filter(models.SchoolItem.child_id == child_id).delete(synchronize_session=False)
    db.query(models.ChildAllowanceSetting).filter(models.ChildAllowanceSetting.child_id == child_id).delete(synchronize_session=False)
    db.query(models.WeeklyStreak).filter(models.WeeklyStreak.child_id == child_id).delete(synchronize_session=False)
    db.query(models.PetProgress).filter(models.PetProgress.child_id == child_id).delete(synchronize_session=False)
    db.query(models.ChildDeviceSession).filter(models.ChildDeviceSession.child_id == child_id).delete(synchronize_session=False)
    db.query(models.ChildDeviceInvite).filter(models.ChildDeviceInvite.child_id == child_id).delete(synchronize_session=False)
    db.query(models.Reward).filter(models.Reward.family_id == family_id).delete(synchronize_session=False)


def _reset_parent_child_rows(db: Session, child_id: int) -> None:
    db.query(models.CalendarCompletion).filter(models.CalendarCompletion.child_id == child_id).delete(synchronize_session=False)
    db.query(models.CalendarEntry).filter(models.CalendarEntry.child_id == child_id).delete(synchronize_session=False)
    db.query(models.RedemptionRequest).filter(models.RedemptionRequest.child_id == child_id).delete(synchronize_session=False)
    db.query(models.LedgerTransaction).filter(models.LedgerTransaction.child_id == child_id).delete(synchronize_session=False)
    db.query(models.SchoolItem).filter(models.SchoolItem.child_id == child_id).delete(synchronize_session=False)
    db.query(models.ChildAllowanceSetting).filter(models.ChildAllowanceSetting.child_id == child_id).delete(synchronize_session=False)
    db.query(models.WeeklyStreak).filter(models.WeeklyStreak.child_id == child_id).delete(synchronize_session=False)
    db.query(models.PetProgress).filter(models.PetProgress.child_id == child_id).delete(synchronize_session=False)
    db.query(models.ChildDeviceSession).filter(models.ChildDeviceSession.child_id == child_id).delete(synchronize_session=False)
    db.query(models.ChildDeviceInvite).filter(models.ChildDeviceInvite.child_id == child_id).delete(synchronize_session=False)


def _get_or_create_parent(db: Session) -> tuple[models.ParentUser, models.Family, bool]:
    family = (
        db.query(models.Family)
        .join(models.ParentUser, models.ParentUser.family_id == models.Family.id)
        .filter(models.ParentUser.email == QA_CHILD_PARENT_EMAIL)
        .first()
    )
    parent = db.query(models.ParentUser).filter(models.ParentUser.email == QA_CHILD_PARENT_EMAIL).first()
    reused = parent is not None

    if parent is None:
        family = models.Family(timezone=QA_CHILD_FAMILY_TIMEZONE, week_start_day=6)
        db.add(family)
        db.flush()
        parent = models.ParentUser(
            email=QA_CHILD_PARENT_EMAIL,
            name=QA_CHILD_PARENT_NAME,
            google_sub=f"qa-child-login:{QA_CHILD_PARENT_EMAIL}",
            family_id=family.id,
            last_login_at=_current_utc(),
        )
        db.add(parent)
        db.flush()
        parent.family = family
        return parent, family, False

    if parent.family_id is None:
        family = models.Family(timezone=QA_CHILD_FAMILY_TIMEZONE, week_start_day=6)
        db.add(family)
        db.flush()
        parent.family_id = family.id
        parent.family = family
    elif family is None:
        family = models.Family(timezone=QA_CHILD_FAMILY_TIMEZONE, week_start_day=6)
        db.add(family)
        db.flush()
        parent.family_id = family.id
        parent.family = family

    if auth.is_parent_revoked(parent):
        raise PermissionError("This account has been revoked")
    if auth.is_family_suspended(family):
        raise PermissionError("This family account is currently suspended. Please contact support@familyherohub.com.")

    parent.name = QA_CHILD_PARENT_NAME
    parent.google_sub = f"qa-child-login:{QA_CHILD_PARENT_EMAIL}"
    parent.last_login_at = _current_utc()
    if family:
        family.timezone = QA_CHILD_FAMILY_TIMEZONE
        family.week_start_day = 6
        family.status = "active"
    db.flush()
    return parent, family, reused


def _get_or_create_child(db: Session, family: models.Family) -> tuple[models.Child, bool]:
    child = (
        db.query(models.Child)
        .filter(
            models.Child.family_id == family.id,
            models.Child.display_name == QA_CHILD_DISPLAY_NAME,
        )
        .first()
    )
    reused = child is not None

    if child is None:
        child = models.Child(
            display_name=QA_CHILD_DISPLAY_NAME,
            family_id=family.id,
            avatar_name=QA_CHILD_AVATAR_NAME,
            active=True,
        )
        db.add(child)
        db.flush()
    else:
        child.family_id = family.id
        child.display_name = QA_CHILD_DISPLAY_NAME
        child.avatar_name = QA_CHILD_AVATAR_NAME
        child.active = True
        db.flush()

    extra_children = (
        db.query(models.Child)
        .filter(
            models.Child.family_id == family.id,
            models.Child.id != child.id,
        )
        .all()
    )
    for extra_child in extra_children:
        _reset_child_seed_rows(db, extra_child.id, family.id)
        db.delete(extra_child)

    return child, reused


def _seed_rewards(db: Session, family_id: int, parent_id: int) -> None:
    for spec in QA_REWARD_SPECS:
        reward = models.Reward(
            parent_id=parent_id,
            family_id=family_id,
            title=spec["title"],
            description=spec["description"],
            icon="sparkles",
            points=spec["points"],
            is_active=True,
        )
        db.add(reward)


def _seed_savings_transactions(db: Session, child_id: int, parent_id: int) -> None:
    now = _current_utc()
    db.add_all(
        [
            models.LedgerTransaction(
                child_id=child_id,
                jar=models.JarType.spending,
                transaction_type=models.TransactionType.award,
                points=100,
                description="QA Seed Spending Award",
                created_by_parent_id=parent_id,
                created_at=now - timedelta(hours=6),
            ),
            models.LedgerTransaction(
                child_id=child_id,
                jar=models.JarType.spending,
                transaction_type=models.TransactionType.adjustment,
                points=20,
                description="QA Seed Adjustment",
                created_by_parent_id=parent_id,
                created_at=now - timedelta(hours=5),
            ),
            models.LedgerTransaction(
                child_id=child_id,
                jar=models.JarType.spending,
                transaction_type=models.TransactionType.penalty,
                points=-5,
                description="QA Seed Penalty",
                created_by_parent_id=parent_id,
                created_at=now - timedelta(hours=4),
            ),
            models.LedgerTransaction(
                child_id=child_id,
                jar=models.JarType.spending,
                transaction_type=models.TransactionType.savings_deposit,
                points=-20,
                description="QA Seed Savings Locked Transfer",
                created_by_parent_id=parent_id,
                created_at=now - timedelta(hours=3),
            ),
            models.LedgerTransaction(
                child_id=child_id,
                jar=models.JarType.savings,
                transaction_type=models.TransactionType.savings_deposit,
                points=20,
                description="QA Seed Savings Locked",
                locked_until=now + timedelta(days=30),
                created_by_parent_id=parent_id,
                created_at=now - timedelta(hours=3),
            ),
            models.LedgerTransaction(
                child_id=child_id,
                jar=models.JarType.spending,
                transaction_type=models.TransactionType.savings_deposit,
                points=-10,
                description="QA Seed Savings Available Transfer",
                created_by_parent_id=parent_id,
                created_at=now - timedelta(hours=2),
            ),
            models.LedgerTransaction(
                child_id=child_id,
                jar=models.JarType.savings,
                transaction_type=models.TransactionType.savings_deposit,
                points=10,
                description="QA Seed Savings Available",
                created_by_parent_id=parent_id,
                created_at=now - timedelta(hours=2),
            ),
        ]
    )


def _seed_pending_requests(db: Session, child_id: int, parent_id: int) -> None:
    now = _current_utc()
    for index, spec in enumerate(QA_PENDING_REQUEST_SPECS):
        request = models.RedemptionRequest(
            child_id=child_id,
            points=spec["points"],
            title=spec["title"],
            description=spec["description"],
            status=models.RedemptionStatus.pending,
            created_at=now - timedelta(minutes=30 - index * 3),
        )
        db.add(request)
        db.flush()

        db.add(
            models.LedgerTransaction(
                child_id=child_id,
                jar=models.JarType.spending,
                transaction_type=models.TransactionType.redemption_hold,
                points=-spec["points"],
                description=f"QA Seed Hold: {spec['title']}",
                created_by_parent_id=parent_id,
                created_at=now - timedelta(minutes=30 - index * 3),
            )
        )


def _seed_calendar(db: Session, family: models.Family, child: models.Child, parent_id: int) -> None:
    today = calendar_service.get_family_today(family.timezone)
    now = _current_utc()

    task = models.CalendarEntry(
        family_id=family.id,
        child_id=child.id,
        created_by_parent_id=parent_id,
        title=QA_TASK_SPECS[0]["title"],
        description=QA_TASK_SPECS[0]["description"],
        entry_type="task",
        is_rewardable=True,
        points_value=QA_TASK_SPECS[0]["points_value"],
        recurrence_type="none",
        start_date=today,
        start_time=datetime.now().replace(hour=15, minute=0, second=0, microsecond=0).time(),
        duration_minutes=30,
        created_at=now - timedelta(minutes=15),
    )
    event = models.CalendarEntry(
        family_id=family.id,
        child_id=child.id,
        created_by_parent_id=parent_id,
        title=QA_EVENT_SPECS[0]["title"],
        description=QA_EVENT_SPECS[0]["description"],
        entry_type="event",
        is_rewardable=False,
        points_value=None,
        recurrence_type="none",
        start_date=today,
        start_time=datetime.now().replace(hour=17, minute=0, second=0, microsecond=0).time(),
        duration_minutes=45,
        created_at=now - timedelta(minutes=12),
    )
    db.add_all([task, event])


def _seed_school_items(db: Session, family: models.Family, child: models.Child, parent_id: int) -> None:
    for spec in QA_SCHOOL_ITEM_SPECS:
        db.add(
            models.SchoolItem(
                family_id=family.id,
                child_id=child.id,
                weekday=(calendar_service.get_family_today(family.timezone) + timedelta(days=spec["weekday_offset"])).weekday(),
                class_name=spec["class_name"],
                needed_item=spec["needed_item"],
                sort_order=spec["weekday_offset"],
                is_active=True,
                created_by_parent_id=parent_id,
            )
        )


def _seed_allowance(db: Session, family: models.Family, child: models.Child, parent_id: int) -> None:
    db.add(
        models.ChildAllowanceSetting(
            family_id=family.id,
            child_id=child.id,
            is_enabled=True,
            currency=QA_CHILD_ALLOWANCE_CURRENCY,
            allowance_amount_minor=QA_CHILD_ALLOWANCE_AMOUNT_MINOR,
            currency_exponent=2,
            period="weekly",
            point_goal=QA_CHILD_ALLOWANCE_POINT_GOAL,
            allowance_enabled_at=_current_utc() - timedelta(days=1),
            created_by_parent_id=parent_id,
            updated_by_parent_id=parent_id,
        )
    )


def _seed_pet_progress(db: Session, child: models.Child) -> None:
    db.add(
        models.PetProgress(
            child_id=child.id,
            lifetime_points=180,
            current_stage=models.PetStage.cub,
        )
    )


def _seed_parent_child_dashboard(db: Session, family: models.Family, parent_id: int, spec: dict, child: models.Child) -> None:
    now = _current_utc()
    db.add_all(
        [
            models.LedgerTransaction(
                child_id=child.id,
                jar=models.JarType.spending,
                transaction_type=models.TransactionType.award,
                points=spec["spending_points"],
                description=f"QA Parent Seed Spending for {spec['display_name']}",
                created_by_parent_id=parent_id,
                created_at=now - timedelta(hours=4),
            ),
            models.LedgerTransaction(
                child_id=child.id,
                jar=models.JarType.savings,
                transaction_type=models.TransactionType.savings_deposit,
                points=spec["savings_points"],
                description=f"QA Parent Seed Savings for {spec['display_name']}",
                created_by_parent_id=parent_id,
                created_at=now - timedelta(hours=3),
            ),
        ]
    )

    for index, request_spec in enumerate(spec.get("pending_requests", [])):
        request_created_at = now - timedelta(minutes=25 - (index * 2))
        db.add(
            models.RedemptionRequest(
                child_id=child.id,
                points=request_spec["points"],
                title=request_spec["title"],
                description=request_spec["description"],
                status=models.RedemptionStatus.pending,
                created_at=request_created_at,
            )
        )
        db.add(
            models.LedgerTransaction(
                child_id=child.id,
                jar=models.JarType.spending,
                transaction_type=models.TransactionType.redemption_hold,
                points=-request_spec["points"],
                description=f"QA Parent Seed Hold: {request_spec['title']}",
                created_by_parent_id=parent_id,
                created_at=request_created_at,
            )
        )


def seed_qa_parent_dashboard(db: Session, parent: models.ParentUser) -> list[models.Child]:
    family = parent.family
    if family is None:
        family = db.query(models.Family).filter(models.Family.id == parent.family_id).first()
    if family is None:
        family = models.Family(timezone=QA_CHILD_FAMILY_TIMEZONE, week_start_day=6)
        db.add(family)
        db.flush()
        parent.family_id = family.id
        parent.family = family

    children = (
        db.query(models.Child)
        .filter(models.Child.family_id == family.id)
        .order_by(models.Child.id.asc())
        .all()
    )

    desired_children: list[models.Child] = []
    for spec in QA_PARENT_CARD_SPECS:
        child = next((item for item in children if item.display_name == spec["display_name"]), None)
        if child is None:
            child = models.Child(
                display_name=spec["display_name"],
                family_id=family.id,
                avatar_name=spec["avatar_name"],
                active=True,
            )
            db.add(child)
            db.flush()
        else:
            child.family_id = family.id
            child.display_name = spec["display_name"]
            child.avatar_name = spec["avatar_name"]
            child.active = True
            db.flush()

        _reset_parent_child_rows(db, child.id)
        _seed_parent_child_dashboard(db, family, parent.id, spec, child)
        desired_children.append(child)

    extra_children = [child for child in children if child.display_name not in {spec["display_name"] for spec in QA_PARENT_CARD_SPECS}]
    for extra_child in extra_children:
        _reset_parent_child_rows(db, extra_child.id)
        db.delete(extra_child)

    db.commit()
    for child in desired_children:
        db.refresh(child)
    return desired_children


def seed_qa_child_dashboard(db: Session) -> QAChildSeedResult:
    parent, family, parent_reused = _get_or_create_parent(db)
    child, child_reused = _get_or_create_child(db, family)

    _reset_child_seed_rows(db, child.id, family.id)
    _seed_allowance(db, family, child, parent.id)
    _seed_rewards(db, family.id, parent.id)
    _seed_savings_transactions(db, child.id, parent.id)
    _seed_pending_requests(db, child.id, parent.id)
    _seed_calendar(db, family, child, parent.id)
    _seed_school_items(db, family, child, parent.id)
    _seed_pet_progress(db, child)

    db.commit()
    db.refresh(parent)
    db.refresh(family)
    db.refresh(child)
    return QAChildSeedResult(
        parent=parent,
        family=family,
        child=child,
        reused=parent_reused or child_reused,
    )


def ensure_qa_child_session(db: Session, child: models.Child) -> tuple[models.ChildDeviceSession, str]:
    raw_token = _deterministic_child_session_token(child.id)
    token_hash = child_auth.hash_token(raw_token)
    current = _current_utc()

    session = db.query(models.ChildDeviceSession).filter(models.ChildDeviceSession.session_hash == token_hash).first()
    if session is None:
        session = models.ChildDeviceSession(
            family_id=child.family_id,
            child_id=child.id,
            session_hash=token_hash,
            expires_at=current + child_auth.CHILD_SESSION_TTL,
            last_seen_at=current,
        )
        db.add(session)
    else:
        session.family_id = child.family_id
        session.child_id = child.id
        session.revoked_at = None
        session.expires_at = current + child_auth.CHILD_SESSION_TTL
        session.last_seen_at = current

    db.commit()
    db.refresh(session)
    return session, raw_token

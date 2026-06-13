"""FIX 1 (audit coverage-gap #1) — PostgreSQL-level test for school-item deletion.

The rest of the suite runs on SQLite, which does NOT enforce foreign keys by
default, so it cannot catch the original bug: ``replace_school_items``
hard-deleted removed items, but ``school_item_checks.school_item_id`` is an
ON DELETE NO ACTION foreign key, so deleting an item that had ever been packed
raised an FK violation in PostgreSQL.

This module talks to a REAL PostgreSQL server (the compose ``postgres`` service)
in a throwaway database, so it both (a) proves the FK constraint is genuinely
enforced — the thing SQLite hides — and (b) confirms the soft-delete fix lets a
parent remove a previously-packed item without error while preserving history.

Skipped automatically when no PostgreSQL DATABASE_URL is configured (e.g. a
SQLite-only local run), so it never breaks the default suite.
"""
from __future__ import annotations

import os
from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

# Resolve a PostgreSQL connection from the POSTGRES_* env vars rather than
# DATABASE_URL: other SQLite-only test modules overwrite DATABASE_URL to
# "sqlite://" at import time, and module import order would make this test skip
# itself during a full-suite run. POSTGRES_USER/PASSWORD/DB are set by the
# compose env and never mutated by tests. Host/port match the compose service.
# We always target a dedicated throwaway database so we never create_all /
# drop_all against dev data.
_PG_USER = os.environ.get("POSTGRES_USER")
_PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
_PG_HOST = os.environ.get("POSTGRES_HOST", "postgres")
_PG_PORT = os.environ.get("POSTGRES_PORT", "5432")
_IS_PG = bool(_PG_USER and _PG_PASSWORD)
_TEST_DB_NAME = "fhh_fk_pg_test"

pytestmark = pytest.mark.skipif(
    not _IS_PG,
    reason="POSTGRES_USER/POSTGRES_PASSWORD not set; FK-enforcement test needs a real PG server",
)


def _url_for(db_name: str) -> str:
    return (
        f"postgresql+psycopg://{_PG_USER}:{_PG_PASSWORD}@{_PG_HOST}:{_PG_PORT}/{db_name}"
    )


def _admin_url() -> str:
    # Connect to the maintenance 'postgres' database to CREATE/DROP the test DB.
    return _url_for("postgres")


def _test_url() -> str:
    return _url_for(_TEST_DB_NAME)


@pytest.fixture(scope="module")
def pg_engine():
    admin = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {_TEST_DB_NAME}"))
        conn.execute(text(f"CREATE DATABASE {_TEST_DB_NAME}"))
    admin.dispose()

    engine = create_engine(_test_url())

    # Import models/Base AFTER we know we're running, and create the schema
    # straight from the ORM models (same path as app startup).
    from app.database import Base
    from app import models  # noqa: F401  (registers tables on Base)

    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        engine.dispose()
        admin = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
        with admin.connect() as conn:
            # Terminate any lingering connections before dropping.
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
def db(pg_engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        # Clean rows between tests so each starts fresh.
        for table in (
            "school_item_checks",
            "school_items",
            "children",
            "parent_users",
            "families",
        ):
            session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        session.commit()
        session.close()


def _family_parent_child(db):
    from app import models

    family = models.Family(timezone="Asia/Muscat", week_start_day=6)
    db.add(family)
    db.commit()
    parent = models.ParentUser(
        email="fk-parent@example.com", family_id=family.id, google_sub="fk-sub"
    )
    child = models.Child(display_name="Kid", family_id=family.id)
    db.add_all([parent, child])
    db.commit()
    return family, parent, child


def _packed_item(db, family, parent, child, weekday: int = 2):
    """Create a school item and a packing row referencing it."""
    from app import models

    item = models.SchoolItem(
        family_id=family.id,
        child_id=child.id,
        weekday=weekday,
        class_name="Math",
        needed_item="Math book",
        sort_order=0,
        is_active=True,
        created_by_parent_id=parent.id,
    )
    db.add(item)
    db.commit()

    check = models.SchoolItemCheck(
        school_item_id=item.id,
        child_id=child.id,
        check_date=date(2026, 6, 17),  # a Wednesday (weekday 2)
    )
    db.add(check)
    db.commit()
    return item, check


def test_fk_blocks_hard_delete_of_packed_item(db):
    """Demonstrates the original bug at the PG level: a raw hard-delete of a
    packed item violates the ON DELETE NO ACTION FK. This is exactly what SQLite
    silently allowed, hiding the bug from the rest of the suite."""
    from app import models

    family, parent, child = _family_parent_child(db)
    item, _check = _packed_item(db, family, parent, child)

    db.delete(item)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_replace_soft_deletes_packed_item_and_preserves_history(db):
    """The fix: removing a previously-packed item via replace_school_items
    succeeds, marks the item inactive (not gone), drops it from the current
    list, and leaves its packing history intact."""
    import asyncio

    from app import models, schemas
    from app.routes import school_items as si_routes

    family, parent, child = _family_parent_child(db)
    item, check = _packed_item(db, family, parent, child)

    # Replace the Wednesday list with a brand-new item, removing the packed one.
    result = asyncio.run(
        si_routes.replace_school_items(
            items=[schemas.SchoolItemUpsert(class_name="Science", needed_item="Lab coat")],
            child_id=child.id,
            weekday=2,
            db=db,
            current_parent=parent,
        )
    )

    # Endpoint returns only the active list → just the new item.
    assert [r.class_name for r in result] == ["Science"]

    # The removed item is soft-deleted, not gone.
    db.expire_all()
    refreshed = db.query(models.SchoolItem).filter(models.SchoolItem.id == item.id).one()
    assert refreshed.is_active is False

    # Its packing history survives the FK intact.
    surviving = (
        db.query(models.SchoolItemCheck)
        .filter(models.SchoolItemCheck.id == check.id)
        .one()
    )
    assert surviving.school_item_id == item.id

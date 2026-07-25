from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from app.models_school import AuditLog, School, User
from app.school_scope import write_audit


def _audit_test_database_url() -> str:
    explicit_url = os.getenv("AUDIT_TEST_DATABASE_URL")
    if explicit_url:
        return explicit_url

    database_name = os.getenv("AUDIT_TEST_DATABASE")
    source_url = os.getenv("DATABASE_URL")
    if database_name and source_url:
        return make_url(source_url).set(database=database_name).render_as_string(
            hide_password=False
        )

    pytest.skip(
        "AUDIT_TEST_DATABASE_URL or AUDIT_TEST_DATABASE with DATABASE_URL is required"
    )


@pytest.fixture(scope="module")
def audit_engine():
    engine = create_engine(_audit_test_database_url())
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db(audit_engine):
    session = sessionmaker(bind=audit_engine)()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _create_audit_row(db, action: str) -> AuditLog:
    suffix = uuid4().hex
    school = School(
        name=f"Audit Test {suffix}",
        slug=f"audit-test-{suffix}",
        status="active",
    )
    actor = User(email=f"audit-{suffix}@example.test", name="Audit Test Actor")
    db.add_all([school, actor])
    db.flush()
    row = AuditLog(
        school_id=school.id,
        actor_user_id=actor.id,
        action=action,
        entity_type="audit_test",
        entity_id=school.id,
        detail={"source": "focused-test"},
    )
    db.add(row)
    db.commit()
    return row


def test_normal_audit_insert_and_select_succeed(db):
    row = _create_audit_row(db, "audit.test.insert")

    stored = db.query(AuditLog).filter_by(id=row.id).one()
    assert stored.action == "audit.test.insert"
    assert stored.detail == {"source": "focused-test"}


def test_bulk_orm_update_and_delete_are_rejected_and_row_is_unchanged(db):
    row = _create_audit_row(db, "audit.test.orm")
    original = (row.action, row.detail)

    with pytest.raises(DBAPIError, match="general audit rows are append-only"):
        db.query(AuditLog).filter_by(id=row.id).update(
            {AuditLog.action: "audit.test.orm.changed"},
            synchronize_session=False,
        )
    db.rollback()

    with pytest.raises(DBAPIError, match="general audit rows are append-only"):
        db.query(AuditLog).filter_by(id=row.id).delete(synchronize_session=False)
    db.rollback()

    stored = db.query(AuditLog).filter_by(id=row.id).one()
    assert (stored.action, stored.detail) == original


def test_raw_sql_update_and_delete_are_rejected_and_row_is_unchanged(db):
    row = _create_audit_row(db, "audit.test.raw-sql")
    original = (row.action, row.detail)

    with pytest.raises(DBAPIError, match="general audit rows are append-only"):
        db.execute(
            text("UPDATE audit_logs SET action = :action WHERE id = :id"),
            {"action": "audit.test.raw-sql.changed", "id": row.id},
        )
    db.rollback()

    with pytest.raises(DBAPIError, match="general audit rows are append-only"):
        db.execute(text("DELETE FROM audit_logs WHERE id = :id"), {"id": row.id})
    db.rollback()

    stored = db.query(AuditLog).filter_by(id=row.id).one()
    assert (stored.action, stored.detail) == original


def test_existing_write_audit_workflow_still_succeeds(db):
    suffix = uuid4().hex
    school = School(name=f"Audit Workflow {suffix}", slug=f"audit-workflow-{suffix}")
    actor = User(email=f"audit-workflow-{suffix}@example.test", name="Workflow Actor")
    db.add_all([school, actor])
    db.flush()

    row = write_audit(
        db,
        actor,
        "school.updated",
        school,
        {"field": "name"},
        school_id=school.id,
    )
    db.commit()

    stored = db.query(AuditLog).filter_by(id=row.id).one()
    assert stored.action == "school.updated"
    assert stored.entity_type == "schools"
    assert stored.entity_id == school.id

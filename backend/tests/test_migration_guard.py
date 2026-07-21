from __future__ import annotations

import io

import pytest

from app.migration_guard import parse_target, validate_migration_target


def test_target_label_never_contains_credentials():
    target = parse_target("postgresql://user:secret@db.example:5432/chh_validation_one", source="test")
    assert target.label == "db.example/chh_validation_one"
    assert "secret" not in target.label


def test_protected_downgrade_is_fail_closed(monkeypatch):
    monkeypatch.delenv("MIGRATION_EMERGENCY_OVERRIDE", raising=False)
    monkeypatch.setenv("MIGRATION_NONINTERACTIVE", "1")
    target = parse_target("postgresql://u:p@postgres/class_hero_hub", source="test")
    with pytest.raises(RuntimeError, match="Protected database downgrade refused"):
        validate_migration_target(target, downgrade=True, explicit_migration_url=True)


def test_disposable_noninteractive_downgrade(monkeypatch):
    monkeypatch.setenv("MIGRATION_NONINTERACTIVE", "1")
    target = parse_target("postgresql://u:p@localhost/chh_validation_one", source="test")
    validate_migration_target(target, downgrade=True, explicit_migration_url=True)


def test_downgrade_never_accepts_dotenv_fallback(monkeypatch):
    monkeypatch.setenv("MIGRATION_NONINTERACTIVE", "1")
    target = parse_target("postgresql://u:p@localhost/chh_validation_one", source="dotenv")
    with pytest.raises(RuntimeError, match="requires MIGRATION_DATABASE_URL"):
        validate_migration_target(target, downgrade=True, explicit_migration_url=False, input_stream=io.StringIO())

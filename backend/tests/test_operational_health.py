from __future__ import annotations

from fastapi.testclient import TestClient

from app import operational_health
from app.main import create_app


def test_liveness_remains_lightweight_and_compatible():
    with TestClient(create_app()) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_is_healthy_when_database_and_migration_are_current(monkeypatch):
    monkeypatch.setattr(
        operational_health,
        "_database_probe",
        lambda: operational_health.EXPECTED_MIGRATION_REVISION,
    )

    with TestClient(create_app()) as client:
        response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok", "migration": "current"},
    }


def test_readiness_is_degraded_when_migration_is_outdated(monkeypatch):
    monkeypatch.setattr(operational_health, "_database_probe", lambda: "previous-revision")

    with TestClient(create_app()) as client:
        response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "checks": {"database": "ok", "migration": "outdated"},
    }


def test_readiness_is_unavailable_without_exposing_dependency_errors(monkeypatch):
    def unavailable_probe():
        raise TimeoutError("database connection included private diagnostics")

    monkeypatch.setattr(operational_health, "_database_probe", unavailable_probe)

    with TestClient(create_app()) as client:
        response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "checks": {"database": "unavailable", "migration": "unknown"},
    }
    assert "private diagnostics" not in response.text


def test_legacy_readiness_route_is_not_exposed():
    with TestClient(create_app()) as client:
        response = client.get("/api/ready")

    assert response.status_code == 404

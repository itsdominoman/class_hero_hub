import os
import asyncio
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient

from app import database
from app.database import Settings, validate_runtime_configuration
from app.main import create_app
from app.security import BoundedInMemoryRateLimiter, TrustedProxyHeadersMiddleware, get_client_ip_from_scope


def _base_settings(**overrides) -> Settings:
    values = {
        "APP_ENV": "test",
        "JWT_SECRET": "",
        "SESSION_SECRET": "",
        "GOOGLE_CLIENT_ID": "",
        "GOOGLE_CLIENT_SECRET": "",
        "GOOGLE_REDIRECT_URI": "http://localhost:8000/api/auth/google/callback",
        "PUBLIC_APP_URL": "http://localhost:5173",
        "API_BASE_URL": "http://localhost:8000",
        "CORS_ORIGINS": "http://localhost:5173,http://localhost:8000",
        "TRUSTED_PROXY_IPS": "127.0.0.1,::1",
        "QA_BLOCKED_HOSTNAMES": "familyherohub.com,www.familyherohub.com",
        "QA_LOGIN_ENABLED": False,
        "QA_CHILD_LOGIN_ENABLED": False,
    }
    values.update(overrides)
    return Settings(**values)


def test_validate_runtime_configuration_accepts_canonical_test_environment():
    config = _base_settings()

    assert validate_runtime_configuration(config) == "test"


def test_notification_scheduler_requires_messaging_and_valid_bounds():
    with pytest.raises(RuntimeError, match="MESSAGING_NOTIFICATION_SCHEDULER_ENABLED"):
        validate_runtime_configuration(
            _base_settings(
                MESSAGING_ENABLED=False,
                MESSAGING_NOTIFICATION_SCHEDULER_ENABLED=True,
            )
        )
    with pytest.raises(RuntimeError, match="MESSAGING_NOTIFICATION_SCHEDULER_LEASE_SECONDS"):
        validate_runtime_configuration(
            _base_settings(
                MESSAGING_ENABLED=True,
                MESSAGING_NOTIFICATION_SCHEDULER_ENABLED=True,
                MESSAGING_NOTIFICATION_SCHEDULER_LEASE_SECONDS=10,
            )
        )
    assert (
        validate_runtime_configuration(
            _base_settings(
                MESSAGING_ENABLED=True,
                MESSAGING_NOTIFICATION_SCHEDULER_ENABLED=True,
            )
        )
        == "test"
    )


def test_fhh_integration_requires_strong_non_placeholder_token_when_enabled():
    with pytest.raises(RuntimeError, match="FHH_INTEGRATION_SERVICE_TOKEN"):
        validate_runtime_configuration(_base_settings(FHH_INTEGRATION_ENABLED=True, FHH_INTEGRATION_SERVICE_TOKEN="change_me"))
    assert validate_runtime_configuration(_base_settings(FHH_INTEGRATION_ENABLED=True, FHH_INTEGRATION_SERVICE_TOKEN="f" * 32)) == "test"


def test_validate_runtime_configuration_rejects_missing_or_invalid_app_env():
    config = _base_settings(APP_ENV="")

    with pytest.raises(RuntimeError, match="APP_ENV"):
        validate_runtime_configuration(config)


def test_validate_runtime_configuration_rejects_legacy_environment_variable():
    config = _base_settings(APP_ENV="production", ENVIRONMENT="development")

    with pytest.raises(RuntimeError, match="ENVIRONMENT"):
        validate_runtime_configuration(config)


@pytest.mark.parametrize(
    ("setting_name", "value", "expected_message"),
    [
        ("JWT_SECRET", "", "JWT_SECRET"),
        ("JWT_SECRET", "secret", "placeholder"),
        ("SESSION_SECRET", "session_secret", "placeholder"),
        ("JWT_SECRET", "short-secret", "32"),
    ],
)
def test_validate_runtime_configuration_rejects_bad_production_secrets(setting_name, value, expected_message):
    config = _base_settings(
        APP_ENV="production",
        JWT_SECRET="a" * 32,
        SESSION_SECRET="b" * 32,
        GOOGLE_CLIENT_ID="client-id",
        GOOGLE_CLIENT_SECRET="c" * 16,
        PUBLIC_APP_URL="https://familyherohub.com",
        API_BASE_URL="https://familyherohub.com",
        GOOGLE_REDIRECT_URI="https://familyherohub.com/api/auth/google/callback",
        CORS_ORIGINS="https://familyherohub.com",
    )
    setattr(config, setting_name, value)

    with pytest.raises(RuntimeError, match=expected_message):
        validate_runtime_configuration(config)


def test_validate_runtime_configuration_accepts_valid_production_configuration():
    config = _base_settings(
        APP_ENV="production",
        JWT_SECRET="a" * 32,
        SESSION_SECRET="b" * 32,
        GOOGLE_CLIENT_ID="client-id",
        GOOGLE_CLIENT_SECRET="c" * 16,
        PUBLIC_APP_URL="https://familyherohub.com",
        API_BASE_URL="https://familyherohub.com",
        GOOGLE_REDIRECT_URI="https://familyherohub.com/api/auth/google/callback",
        CORS_ORIGINS="https://familyherohub.com",
    )

    assert validate_runtime_configuration(config) == "production"


def test_validate_runtime_configuration_rejects_localhost_cors_in_production():
    config = _base_settings(
        APP_ENV="production",
        JWT_SECRET="a" * 32,
        SESSION_SECRET="b" * 32,
        GOOGLE_CLIENT_ID="client-id",
        GOOGLE_CLIENT_SECRET="c" * 16,
        PUBLIC_APP_URL="https://familyherohub.com",
        API_BASE_URL="https://familyherohub.com",
        GOOGLE_REDIRECT_URI="https://familyherohub.com/api/auth/google/callback",
        CORS_ORIGINS="https://familyherohub.com,http://localhost:5173",
    )

    with pytest.raises(RuntimeError, match="localhost origins"):
        validate_runtime_configuration(config)


def test_validate_runtime_configuration_rejects_malformed_cors_origin():
    config = _base_settings(
        APP_ENV="production",
        JWT_SECRET="a" * 32,
        SESSION_SECRET="b" * 32,
        GOOGLE_CLIENT_ID="client-id",
        GOOGLE_CLIENT_SECRET="c" * 16,
        PUBLIC_APP_URL="https://familyherohub.com",
        API_BASE_URL="https://familyherohub.com",
        GOOGLE_REDIRECT_URI="https://familyherohub.com/api/auth/google/callback",
        CORS_ORIGINS="familyherohub.com",
    )

    with pytest.raises(RuntimeError, match="invalid origin"):
        validate_runtime_configuration(config)


def test_validate_runtime_configuration_rejects_wildcard_proxy_trust_in_production():
    config = _base_settings(
        APP_ENV="production",
        JWT_SECRET="a" * 32,
        SESSION_SECRET="b" * 32,
        GOOGLE_CLIENT_ID="client-id",
        GOOGLE_CLIENT_SECRET="c" * 16,
        PUBLIC_APP_URL="https://familyherohub.com",
        API_BASE_URL="https://familyherohub.com",
        GOOGLE_REDIRECT_URI="https://familyherohub.com/api/auth/google/callback",
        CORS_ORIGINS="https://familyherohub.com",
        TRUSTED_PROXY_IPS="*",
    )

    with pytest.raises(RuntimeError, match="TRUSTED_PROXY_IPS"):
        validate_runtime_configuration(config)


def test_validate_runtime_configuration_rejects_enabled_qa_routes_without_token():
    config = _base_settings(
        QA_LOGIN_ENABLED=True,
        QA_LOGIN_TOKEN="",
    )

    with pytest.raises(RuntimeError, match="QA_LOGIN_TOKEN"):
        validate_runtime_configuration(config)


def test_production_app_does_not_mount_dev_routes(monkeypatch):
    monkeypatch.setattr(database.settings, "APP_ENV", "production")
    monkeypatch.setattr(database.settings, "ENVIRONMENT", "")
    monkeypatch.setattr(database.settings, "JWT_SECRET", "a" * 32)
    monkeypatch.setattr(database.settings, "SESSION_SECRET", "b" * 32)
    monkeypatch.setattr(database.settings, "GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setattr(database.settings, "GOOGLE_CLIENT_SECRET", "c" * 16)
    monkeypatch.setattr(database.settings, "PUBLIC_APP_URL", "https://familyherohub.com")
    monkeypatch.setattr(database.settings, "API_BASE_URL", "https://familyherohub.com")
    monkeypatch.setattr(database.settings, "GOOGLE_REDIRECT_URI", "https://familyherohub.com/api/auth/google/callback")
    monkeypatch.setattr(database.settings, "CORS_ORIGINS", "https://familyherohub.com")
    monkeypatch.setattr(database.settings, "TRUSTED_PROXY_IPS", "127.0.0.1,::1")
    monkeypatch.setattr(database.settings, "QA_BLOCKED_HOSTNAMES", "familyherohub.com,www.familyherohub.com")

    production_app = create_app()
    client = TestClient(production_app)

    response = client.post("/api/dev/qa-login", json={"token": "qa-token"})

    assert response.status_code == 404


async def _call_proxy_middleware(trusted_proxy_ips: str, client_ip: str, headers: dict[str, str]):
    captured: dict[str, object] = {}

    async def downstream(scope, receive, send):
        captured["client"] = scope.get("client")
        captured["scheme"] = scope.get("scheme")
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = TrustedProxyHeadersMiddleware(downstream, trusted_proxy_ips=trusted_proxy_ips)
    scope = {
        "type": "http",
        "client": (client_ip, 12345),
        "scheme": "http",
        "headers": [(key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in headers.items()],
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        captured.setdefault("messages", []).append(message)

    await middleware(scope, receive, send)
    return captured


def test_trusted_proxy_headers_are_honored():
    captured = asyncio.run(
        _call_proxy_middleware(
            trusted_proxy_ips="127.0.0.1,::1",
            client_ip="127.0.0.1",
            headers={
                "X-Forwarded-For": "203.0.113.99, 127.0.0.1",
                "X-Forwarded-Proto": "https",
            },
        )
    )

    assert captured["client"] == ("203.0.113.99", 12345)
    assert captured["scheme"] == "https"


def test_untrusted_direct_client_forwarded_headers_are_ignored():
    captured = asyncio.run(
        _call_proxy_middleware(
            trusted_proxy_ips="127.0.0.1,::1",
            client_ip="198.51.100.10",
            headers={
                "X-Forwarded-For": "203.0.113.99, 127.0.0.1",
                "X-Forwarded-Proto": "https",
            },
        )
    )

    assert captured["client"] == ("198.51.100.10", 12345)
    assert captured["scheme"] == "http"


def test_client_ip_helper_uses_rewritten_scope_ip():
    scope = {"client": ("203.0.113.50", 5555)}

    assert get_client_ip_from_scope(scope) == "203.0.113.50"


def test_rate_limiter_allows_requests_within_limit():
    limiter = BoundedInMemoryRateLimiter(window_seconds=60, max_attempts=3)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert limiter.allow("203.0.113.10", now=start)
    assert limiter.allow("203.0.113.10", now=start + timedelta(seconds=1))
    assert limiter.allow("203.0.113.10", now=start + timedelta(seconds=2))
    assert limiter.allow("203.0.113.10", now=start + timedelta(seconds=3)) is False


def test_rate_limiter_blocks_requests_over_the_limit():
    limiter = BoundedInMemoryRateLimiter(window_seconds=60, max_attempts=2)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert limiter.allow("203.0.113.11", now=start)
    assert limiter.allow("203.0.113.11", now=start + timedelta(seconds=1))
    assert limiter.allow("203.0.113.11", now=start + timedelta(seconds=2)) is False


def test_rate_limiter_removes_expired_timestamps_from_buckets():
    limiter = BoundedInMemoryRateLimiter(window_seconds=60, max_attempts=3)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert limiter.allow("203.0.113.12", now=start)
    assert limiter.allow("203.0.113.12", now=start + timedelta(seconds=61))

    bucket = limiter._attempts["203.0.113.12"]
    assert len(bucket) == 1
    assert bucket[0] == start + timedelta(seconds=61)


def test_rate_limiter_removes_empty_ip_entries():
    limiter = BoundedInMemoryRateLimiter(window_seconds=60, max_attempts=3)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert limiter.allow("203.0.113.13", now=start)
    limiter.cleanup_expired(now=start + timedelta(seconds=61))

    assert "203.0.113.13" not in limiter._attempts


def test_rate_limiter_cleanup_clears_many_one_off_ips():
    limiter = BoundedInMemoryRateLimiter(window_seconds=60, max_attempts=3)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    for index in range(100):
        assert limiter.allow(f"203.0.113.{index}", now=start)

    limiter.cleanup_expired(now=start + timedelta(seconds=61))

    assert limiter._attempts == {}


def test_rate_limiter_cleanup_keeps_active_entries():
    limiter = BoundedInMemoryRateLimiter(window_seconds=60, max_attempts=3)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    limiter._attempts["203.0.113.14"] = deque([start])
    limiter._attempts["203.0.113.15"] = deque([start - timedelta(seconds=61)])
    limiter._last_cleanup_at = start - timedelta(seconds=61)

    limiter.cleanup_expired(now=start)

    assert "203.0.113.14" in limiter._attempts
    assert "203.0.113.15" not in limiter._attempts


def test_rate_limiter_handles_concurrent_access_without_corruption():
    limiter = BoundedInMemoryRateLimiter(window_seconds=60, max_attempts=20)
    current = datetime(2026, 1, 1, tzinfo=timezone.utc)

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(lambda _: limiter.allow("203.0.113.16", now=current), range(100)))

    assert sum(results) == 20
    assert len(limiter._attempts["203.0.113.16"]) == 20

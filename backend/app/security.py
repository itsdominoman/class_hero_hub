from __future__ import annotations

import ipaddress
from collections import deque
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
import threading


class BoundedInMemoryRateLimiter:
    def __init__(
        self,
        window_seconds: int,
        max_attempts: int,
        *,
        cleanup_interval_seconds: int | None = None,
    ) -> None:
        self.window = timedelta(seconds=window_seconds)
        self.max_attempts = max_attempts
        cleanup_interval = window_seconds if cleanup_interval_seconds is None else cleanup_interval_seconds
        self.cleanup_interval = timedelta(seconds=cleanup_interval)
        self._attempts: dict[str, deque[datetime]] = {}
        self._last_cleanup_at: datetime | None = None
        self._lock = threading.RLock()

    def _purge_expired_locked(self, bucket: deque[datetime], now: datetime) -> None:
        cutoff = now - self.window
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

    def _cleanup_locked(self, now: datetime) -> None:
        if self._last_cleanup_at is not None and (now - self._last_cleanup_at) < self.cleanup_interval:
            return

        stale_keys: list[str] = []
        for key, bucket in self._attempts.items():
            self._purge_expired_locked(bucket, now)
            if not bucket:
                stale_keys.append(key)

        for key in stale_keys:
            self._attempts.pop(key, None)

        self._last_cleanup_at = now

    def cleanup_expired(self, now: datetime | None = None) -> None:
        current = now or datetime.now(timezone.utc)
        with self._lock:
            self._cleanup_locked(current)

    def allow(self, key: str, now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        with self._lock:
            self._cleanup_locked(current)

            bucket = self._attempts.get(key)
            if bucket is None:
                bucket = deque()
                self._attempts[key] = bucket
            else:
                self._purge_expired_locked(bucket, current)
                if not bucket:
                    self._attempts.pop(key, None)
                    bucket = deque()
                    self._attempts[key] = bucket

            if len(bucket) >= self.max_attempts:
                return False

            bucket.append(current)
            return True


def parse_csv_values(raw_value: str | None) -> list[str]:
    return [item.strip() for item in (raw_value or "").split(",") if item.strip()]


def parse_ip_networks(raw_value: str | None) -> tuple[ipaddress._BaseNetwork, ...]:
    networks: list[ipaddress._BaseNetwork] = []
    for value in parse_csv_values(raw_value):
        if value in {"*", "0.0.0.0/0", "::/0"}:
            raise ValueError("wildcard proxy trust is not allowed")
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError as exc:
            raise ValueError(f"invalid trusted proxy IP or CIDR: {value}") from exc
    return tuple(networks)


def is_ip_trusted(ip_address: str | None, trusted_networks: Iterable[ipaddress._BaseNetwork]) -> bool:
    if not ip_address:
        return False

    try:
        candidate = ipaddress.ip_address(ip_address)
    except ValueError:
        return False

    return any(candidate in network for network in trusted_networks)


def get_client_ip_from_scope(scope: dict) -> str | None:
    client = scope.get("client")
    if not client:
        return None

    host = client[0]
    if not isinstance(host, str) or not host:
        return None

    return host


def extract_forwarded_value(header_value: str | None) -> str | None:
    if not header_value:
        return None

    first_value = header_value.split(",", 1)[0].strip()
    return first_value or None


class TrustedProxyHeadersMiddleware:
    def __init__(self, app, trusted_proxy_ips: str) -> None:
        self.app = app
        self.trusted_networks = parse_ip_networks(trusted_proxy_ips)

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http" and is_ip_trusted(
            get_client_ip_from_scope(scope),
            self.trusted_networks,
        ):
            headers = {key.decode("latin-1"): value.decode("latin-1") for key, value in scope.get("headers", [])}

            forwarded_for = extract_forwarded_value(headers.get("x-forwarded-for"))
            if forwarded_for:
                client = scope.get("client")
                client_port = client[1] if client and len(client) > 1 else 0
                scope["client"] = (forwarded_for, client_port)

            forwarded_proto = extract_forwarded_value(headers.get("x-forwarded-proto"))
            if forwarded_proto:
                scope["scheme"] = forwarded_proto

        await self.app(scope, receive, send)

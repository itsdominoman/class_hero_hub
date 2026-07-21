"""Fail-closed Alembic target selection and downgrade protection.

The guard is deliberately free of application imports so it can be unit tested and
used before Alembic opens a database connection.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from urllib.parse import unquote, urlparse


DEFAULT_PROTECTED_DATABASES = frozenset(
    {"class_hero_hub", "family_hero_hub", "family_hero_hub_dev"}
)
# Generic Compose service names are intentionally not protected by default: a
# disposable validation database normally lives on the same PostgreSQL host as
# development.  Real protected hostnames are supplied explicitly via
# MIGRATION_PROTECTED_HOSTS; well-known protected database names remain guarded.
DEFAULT_PROTECTED_HOSTS: frozenset[str] = frozenset()


@dataclass(frozen=True)
class MigrationTarget:
    url: str
    host: str
    database: str
    source: str

    @property
    def label(self) -> str:
        return f"{self.host}/{self.database}"


def parse_target(url: str, *, source: str) -> MigrationTarget:
    parsed = urlparse(url)
    database = unquote((parsed.path or "").lstrip("/"))
    if not parsed.scheme or not database:
        raise RuntimeError("Migration URL must include a scheme and database name")
    host = (parsed.hostname or "local").lower()
    return MigrationTarget(url=url, host=host, database=database, source=source)


def _csv(name: str) -> set[str]:
    return {item.strip().lower() for item in os.getenv(name, "").split(",") if item.strip()}


def is_protected(target: MigrationTarget) -> bool:
    databases = set(DEFAULT_PROTECTED_DATABASES) | _csv("MIGRATION_PROTECTED_DATABASES")
    hosts = set(DEFAULT_PROTECTED_HOSTS) | _csv("MIGRATION_PROTECTED_HOSTS")
    return target.database.lower() in databases or target.host in hosts


def is_downgrade(argv: list[str] | None = None) -> bool:
    words = [word.lower() for word in (argv if argv is not None else sys.argv[1:])]
    return "downgrade" in words


def validate_migration_target(
    target: MigrationTarget,
    *,
    downgrade: bool,
    explicit_migration_url: bool,
    input_stream=None,
) -> None:
    """Validate a migration target without ever printing credentials."""
    print(f"Migration target: {target.label} (source={target.source})", flush=True)
    if not downgrade:
        return
    if not explicit_migration_url:
        raise RuntimeError("Downgrade requires MIGRATION_DATABASE_URL set explicitly in the environment")

    noninteractive = os.getenv("MIGRATION_NONINTERACTIVE") == "1"
    expected = f"ALLOW:{target.label}"
    if is_protected(target):
        if not noninteractive or os.getenv("MIGRATION_EMERGENCY_OVERRIDE") != expected:
            raise RuntimeError(
                "Protected database downgrade refused. Set MIGRATION_NONINTERACTIVE=1 and the exact "
                f"MIGRATION_EMERGENCY_OVERRIDE={expected} only under an approved emergency procedure."
            )
        return

    if noninteractive:
        return
    stream = input_stream if input_stream is not None else sys.stdin
    if not getattr(stream, "isatty", lambda: False)():
        raise RuntimeError("Non-interactive downgrade requires MIGRATION_NONINTERACTIVE=1")
    confirmation = input(f"Type DOWNGRADE {target.label} to continue: ").strip()
    if confirmation != f"DOWNGRADE {target.label}":
        raise RuntimeError("Downgrade confirmation did not match")

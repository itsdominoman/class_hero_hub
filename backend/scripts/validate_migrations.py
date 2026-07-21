#!/usr/bin/env python3
"""Exercise upgrade, downgrade and re-upgrade only on an explicit disposable DB."""
from __future__ import annotations

import os
import subprocess
import sys

from sqlalchemy.engine import make_url

from app.migration_guard import is_protected, parse_target


def main() -> int:
    url = os.getenv("MIGRATION_VALIDATION_DATABASE_URL", "")
    database_name = os.getenv("MIGRATION_VALIDATION_DATABASE", "")
    if not url and database_name:
        source_url = os.getenv("DATABASE_URL", "")
        if not source_url:
            raise SystemExit("DATABASE_URL is required when MIGRATION_VALIDATION_DATABASE is used")
        url = make_url(source_url).set(database=database_name).render_as_string(hide_password=False)
    if not url:
        raise SystemExit("MIGRATION_VALIDATION_DATABASE_URL or MIGRATION_VALIDATION_DATABASE is required")
    target = parse_target(url, source="environment:MIGRATION_VALIDATION_DATABASE_URL")
    allowed_prefix = os.getenv("MIGRATION_VALIDATION_DATABASE_PREFIX", "chh_validation_")
    if is_protected(target) or not target.database.startswith(allowed_prefix):
        raise SystemExit(
            f"Refusing validation target {target.label}; database must start with {allowed_prefix!r} and be unprotected"
        )
    env = os.environ.copy()
    env["MIGRATION_DATABASE_URL"] = url
    env["MIGRATION_NONINTERACTIVE"] = "1"
    commands = (
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        [sys.executable, "-m", "alembic", "downgrade", "-1"],
        [sys.executable, "-m", "alembic", "upgrade", "head"],
    )
    for command in commands:
        subprocess.run(command, env=env, check=True)
    if os.getenv("MIGRATION_VALIDATION_APP_SMOKE") == "1":
        os.environ["DATABASE_URL"] = url
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine, text

        with create_engine(url).connect() as connection:
            version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            connection.execute(text("SELECT count(*) FROM messages")).scalar_one()
        from app.main import create_app

        with TestClient(create_app()) as client:
            response = client.get("/api/health")
            if response.status_code != 200 or response.json() != {"status": "ok"}:
                raise SystemExit(f"App smoke failed: HTTP {response.status_code}")
        print(f"Restored app smoke passed at Alembic {version}")
    print(f"Migration round-trip passed for {target.label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

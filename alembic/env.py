from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

repo_root = Path(__file__).resolve().parents[1]
backend_dir = repo_root / "backend"
sys.path.insert(0, str(backend_dir))


def _load_dotenv_value(name: str) -> str | None:
    env_file = repo_root / ".env"
    if not env_file.exists():
        return None

    for line in env_file.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key == name:
            return value.strip().strip('"').strip("'")
    return None


def _database_url() -> str:
    url = (
        os.getenv("MIGRATION_DATABASE_URL")
        or _load_dotenv_value("MIGRATION_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or _load_dotenv_value("DATABASE_URL")
    )
    if not url:
        raise RuntimeError("MIGRATION_DATABASE_URL or DATABASE_URL is required")
    return url


from app.database import Base  # noqa: E402
from app import models  # noqa: F401,E402

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", _database_url())


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

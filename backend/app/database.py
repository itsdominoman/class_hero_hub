from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/family_hero_hub.sqlite"
    SECRET_KEY: str = "secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    PUBLIC_APP_URL: str = "http://localhost:5173"
    API_BASE_URL: str = "http://localhost:8000"
    APP_ENV: str = "development"
    ENVIRONMENT: str = ""
    PARENT_EMAILS: str = "parent@example.com"
    SESSION_SECRET: str = "session_secret"
    DEV_AUTH_ENABLED: bool = False
    DEV_AUTH_PARENT_EMAIL: str = "parent@example.com"
    QA_LOGIN_ENABLED: bool = False
    QA_LOGIN_TOKEN: str = ""
    QA_LOGIN_EMAIL: str = "qa-parent@dev.familyherohub.com"
    QA_LOGIN_NAME: str = "QA Parent"
    QA_CHILD_LOGIN_ENABLED: bool = False
    QA_CHILD_LOGIN_TOKEN: str = ""
    CORS_ORIGINS: str = "https://families.loginto.me,http://localhost:5173,http://localhost:8000"
    SAVINGS_MATURITY_SWEEP_INTERVAL_SECONDS: int = 3600

    # SMTP Settings
    SMTP_HOST: str = "mail.familyherohub.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "noreply@familyherohub.com"
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@familyherohub.com"
    SMTP_FROM_NAME: str = "Family Hero Hub"
    SMTP_USE_STARTTLS: bool = True
    SMTP_USE_SSL: bool = False
    INVITE_EXPIRY_DAYS: int = 7

    @property
    def COOKIE_SECURE(self) -> bool:
        return self.APP_ENV == "production"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_runtime_schema():
    """
    Backfill additive columns for the live SQLite database.

    Legacy compatibility for SQLite only. PostgreSQL schema is managed by
    Alembic and must not execute SQLite-specific inspection or DDL here.
    """

    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    def get_table_columns(connection, table_name: str) -> set[str]:
        rows = connection.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
        return {row[1] for row in rows}

    table_columns = {
        "parent_users": {
            "status": "TEXT DEFAULT 'active'",
            "revoked_at": "DATETIME",
            "revoked_by_parent_id": "INTEGER",
            "revoke_reason": "TEXT",
            "restored_at": "DATETIME",
            "restored_by_parent_id": "INTEGER",
        },
        "approved_parent_emails": {
            "revoked_at": "DATETIME",
            "revoked_by_parent_id": "INTEGER",
            "revoke_reason": "TEXT",
            "restored_at": "DATETIME",
            "restored_by_parent_id": "INTEGER",
        },
        "families": {
            "timezone": "TEXT DEFAULT 'Asia/Muscat'",
            "week_start_day": "INTEGER DEFAULT 6",
            "status": "TEXT DEFAULT 'active'",
            "suspended_at": "DATETIME",
            "suspended_by_parent_id": "INTEGER",
            "suspend_reason": "TEXT",
            "restored_at": "DATETIME",
            "restored_by_parent_id": "INTEGER",
        },
    }

    with engine.begin() as connection:
        for table_name, columns in table_columns.items():
            existing_tables = {
                row[0]
                for row in connection.exec_driver_sql(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if table_name not in existing_tables:
                continue

            current_columns = get_table_columns(connection, table_name)
            for column_name, ddl in columns.items():
                if column_name in current_columns:
                    continue
                connection.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}")
                )
                current_columns.add(column_name)

        connection.execute(
            text("UPDATE parent_users SET status = COALESCE(status, 'active')")
        )
        connection.execute(
            text("UPDATE families SET timezone = COALESCE(timezone, 'Asia/Muscat')")
        )
        connection.execute(
            text("UPDATE families SET week_start_day = COALESCE(week_start_day, 6)")
        )
        connection.execute(
            text("UPDATE families SET status = COALESCE(status, 'active')")
        )

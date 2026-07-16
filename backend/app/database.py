from __future__ import annotations

from urllib.parse import urlparse

from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from .security import parse_csv_values, parse_ip_networks

VALID_APP_ENVIRONMENTS = {"development", "test", "production"}
MIN_JWT_SECRET_LENGTH = 32
MIN_SESSION_SECRET_LENGTH = 32
MIN_QA_TOKEN_LENGTH = 24
MIN_GOOGLE_SECRET_LENGTH = 16
MIN_FHH_SERVICE_TOKEN_LENGTH = 32
PLACEHOLDER_SECRET_VALUES = {
    "",
    "change_me",
    "changeme",
    "placeholder",
    "secret",
    "session_secret",
    "replace_me",
    "replace_with_generated_secret",
    "replace_with_generated_password",
    "test_secret",
    "your-secret-here",
}


def _normalize_value(value: str | None) -> str:
    return (value or "").strip()


def _normalize_environment(value: str | None) -> str:
    return _normalize_value(value).lower()


def _is_placeholder_secret(value: str | None) -> bool:
    normalized = _normalize_environment(value)
    if normalized in PLACEHOLDER_SECRET_VALUES:
        return True
    return normalized.startswith("replace_")


def _fail(setting_name: str, message: str) -> None:
    raise RuntimeError(f"{setting_name}: {message}")


def _validate_url_setting(
    setting_name: str,
    value: str,
    *,
    production: bool,
    require_path: bool = False,
) -> None:
    parsed = urlparse(_normalize_value(value))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        _fail(setting_name, "must be an absolute http(s) URL with a hostname")
    if parsed.query or parsed.fragment:
        _fail(setting_name, "must not include query or fragment components")
    if require_path and not parsed.path:
        _fail(setting_name, "must include a callback path")

    if production:
        if parsed.scheme != "https":
            _fail(setting_name, "must use https in production")
        if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
            _fail(setting_name, "must not use localhost in production")


def _validate_origin_list(setting_name: str, value: str, *, production: bool) -> None:
    origins = parse_csv_values(value)
    if production and not origins:
        _fail(setting_name, "must not be empty in production")

    for origin in origins:
        if origin == "*":
            _fail(setting_name, "must not include wildcard origins")

        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            _fail(setting_name, f"contains an invalid origin: {origin}")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            _fail(setting_name, f"contains a malformed origin: {origin}")
        if production and parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
            _fail(setting_name, "must not include localhost origins in production")


def _validate_hostname_list(setting_name: str, value: str, *, required: bool) -> None:
    hostnames = parse_csv_values(value)
    if required and not hostnames:
        _fail(setting_name, "must not be empty when QA routes are enabled")

    for hostname in hostnames:
        if hostname in {"*", "0.0.0.0", "127.0.0.1", "::1"}:
            continue
        parsed = urlparse(f"//{hostname}")
        if parsed.hostname != hostname:
            _fail(setting_name, f"contains an invalid hostname: {hostname}")


def _validate_secret(setting_name: str, value: str, *, min_length: int, required: bool) -> None:
    normalized = _normalize_value(value)
    if not normalized:
        if required:
            _fail(setting_name, "is required")
        return

    if _is_placeholder_secret(normalized):
        _fail(setting_name, "uses a placeholder value")

    if len(normalized) < min_length:
        _fail(setting_name, f"must be at least {min_length} characters long")


def _validate_optional_secret(setting_name: str, value: str) -> None:
    normalized = _normalize_value(value)
    if normalized and _is_placeholder_secret(normalized):
        _fail(setting_name, "uses a placeholder value")


def _validate_trusted_proxy_ips(setting_name: str, value: str, *, production: bool) -> None:
    normalized = _normalize_value(value)
    if not normalized:
        _fail(setting_name, "must not be empty")

    try:
        parse_ip_networks(normalized)
    except ValueError as exc:
        _fail(setting_name, str(exc))

    if production and any(token in normalized for token in ("*", "0.0.0.0/0", "::/0")):
        _fail(setting_name, "must not trust wildcard proxies in production")


def _validate_runtime_environment(settings: "Settings") -> str:
    if _normalize_value(settings.ENVIRONMENT):
        _fail("ENVIRONMENT", "is no longer supported; use APP_ENV")

    runtime_environment = _normalize_environment(settings.APP_ENV)
    if runtime_environment not in VALID_APP_ENVIRONMENTS:
        _fail("APP_ENV", "must be one of development, test, or production")
    return runtime_environment


def validate_runtime_configuration(settings: "Settings" | None = None) -> str:
    config = settings or globals()["settings"]
    runtime_environment = _validate_runtime_environment(config)
    production = runtime_environment == "production"

    _validate_url_setting("PUBLIC_APP_URL", config.PUBLIC_APP_URL, production=production)
    _validate_url_setting("API_BASE_URL", config.API_BASE_URL, production=production)
    _validate_url_setting(
        "GOOGLE_REDIRECT_URI",
        config.GOOGLE_REDIRECT_URI,
        production=production,
        require_path=True,
    )
    _validate_origin_list("CORS_ORIGINS", config.CORS_ORIGINS, production=production)
    _validate_trusted_proxy_ips("TRUSTED_PROXY_IPS", config.TRUSTED_PROXY_IPS, production=production)

    _validate_secret(
        "JWT_SECRET",
        config.JWT_SECRET,
        min_length=MIN_JWT_SECRET_LENGTH,
        required=production,
    )
    _validate_secret(
        "SESSION_SECRET",
        config.SESSION_SECRET,
        min_length=MIN_SESSION_SECRET_LENGTH,
        required=production,
    )
    _validate_secret(
        "GOOGLE_CLIENT_SECRET",
        config.GOOGLE_CLIENT_SECRET,
        min_length=MIN_GOOGLE_SECRET_LENGTH,
        required=production,
    )

    if production:
        if not _normalize_value(config.GOOGLE_CLIENT_ID):
            _fail("GOOGLE_CLIENT_ID", "is required")
    else:
        _validate_optional_secret("GOOGLE_CLIENT_SECRET", config.GOOGLE_CLIENT_SECRET)

    qa_enabled = bool(config.QA_LOGIN_ENABLED or config.QA_CHILD_LOGIN_ENABLED)
    _validate_hostname_list("QA_BLOCKED_HOSTNAMES", config.QA_BLOCKED_HOSTNAMES, required=qa_enabled)
    if qa_enabled:
        _validate_secret(
            "QA_LOGIN_TOKEN",
            config.QA_LOGIN_TOKEN,
            min_length=MIN_QA_TOKEN_LENGTH,
            required=True,
        )
        if config.QA_CHILD_LOGIN_ENABLED:
            child_token = _normalize_value(config.QA_CHILD_LOGIN_TOKEN)
            if not child_token and not _normalize_value(config.QA_LOGIN_TOKEN):
                _fail("QA_CHILD_LOGIN_TOKEN", "requires either QA_CHILD_LOGIN_TOKEN or QA_LOGIN_TOKEN")
            if child_token:
                _validate_secret(
                    "QA_CHILD_LOGIN_TOKEN",
                    child_token,
                    min_length=MIN_QA_TOKEN_LENGTH,
                    required=True,
                )
    else:
        _validate_optional_secret("QA_LOGIN_TOKEN", config.QA_LOGIN_TOKEN)
        _validate_optional_secret("QA_CHILD_LOGIN_TOKEN", config.QA_CHILD_LOGIN_TOKEN)

    if config.FHH_INTEGRATION_ENABLED:
        _validate_secret(
            "FHH_INTEGRATION_SERVICE_TOKEN",
            config.FHH_INTEGRATION_SERVICE_TOKEN,
            min_length=MIN_FHH_SERVICE_TOKEN_LENGTH,
            required=True,
        )
    else:
        _validate_optional_secret("FHH_INTEGRATION_SERVICE_TOKEN", config.FHH_INTEGRATION_SERVICE_TOKEN)
    try:
        parse_ip_networks(config.FHH_INTEGRATION_ALLOWED_IPS)
    except ValueError as exc:
        _fail("FHH_INTEGRATION_ALLOWED_IPS", str(exc))

    return runtime_environment

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/family_hero_hub.sqlite"
    JWT_SECRET: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    PUBLIC_APP_URL: str = "http://localhost:5173"
    API_BASE_URL: str = "http://localhost:8000"
    APP_ENV: str = ""
    ENVIRONMENT: str = ""
    PLATFORM_ADMIN_EMAILS: str = ""
    SESSION_SECRET: str = ""
    QA_LOGIN_ENABLED: bool = False
    QA_LOGIN_TOKEN: str = ""
    QA_LOGIN_EMAIL: str = "qa-parent@dev.familyherohub.com"
    QA_LOGIN_NAME: str = "QA Parent"
    QA_CHILD_LOGIN_ENABLED: bool = False
    QA_CHILD_LOGIN_TOKEN: str = ""
    QA_BLOCKED_HOSTNAMES: str = "familyherohub.com,www.familyherohub.com"
    TRUSTED_PROXY_IPS: str = "127.0.0.1,::1"
    FHH_INTEGRATION_ENABLED: bool = False
    FHH_INTEGRATION_SERVICE_TOKEN: str = ""
    FHH_INTEGRATION_ALLOWED_IPS: str = ""
    MESSAGING_ENABLED: bool = False
    CORS_ORIGINS: str = "https://families.loginto.me,http://localhost:5173,http://localhost:8000"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Class Hero Hub"
    SMTP_USE_TLS: bool = True
    DB_POOL_SIZE: int = 40
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT_SECONDS: int = 10
    DB_POOL_RECYCLE_SECONDS: int = 1800
    DB_STATEMENT_TIMEOUT_MS: int = 30000
    DB_IDLE_IN_TRANSACTION_SESSION_TIMEOUT_MS: int = 60000

    @property
    def COOKIE_SECURE(self) -> bool:
        return _normalize_environment(self.APP_ENV) == "production"

    @property
    def SECRET_KEY(self) -> str:
        return self.JWT_SECRET

    @property
    def runtime_environment(self) -> str:
        return _validate_runtime_environment(self)

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

_resolved_runtime_environment = validate_runtime_configuration(settings)

connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine_kwargs = {"connect_args": connect_args}
if not settings.DATABASE_URL.startswith("sqlite"):
    postgres_options = []
    if settings.DB_STATEMENT_TIMEOUT_MS > 0:
        postgres_options.append(f"-c statement_timeout={settings.DB_STATEMENT_TIMEOUT_MS}")
    if settings.DB_IDLE_IN_TRANSACTION_SESSION_TIMEOUT_MS > 0:
        postgres_options.append(
            f"-c idle_in_transaction_session_timeout={settings.DB_IDLE_IN_TRANSACTION_SESSION_TIMEOUT_MS}"
        )
    if postgres_options:
        connect_args["options"] = " ".join(postgres_options)

    engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT_SECONDS,
            "pool_recycle": settings.DB_POOL_RECYCLE_SECONDS,
        }
    )

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

REQUEST_DB_SESSION_KEY = "_class_hero_hub_db"


def get_db(request: Request):
    db = getattr(request.state, REQUEST_DB_SESSION_KEY, None)
    if db is None:
        db = SessionLocal()
        setattr(request.state, REQUEST_DB_SESSION_KEY, db)
    return db


def close_request_db(request: Request, *, rollback: bool = True) -> None:
    db = getattr(request.state, REQUEST_DB_SESSION_KEY, None)
    if db is None:
        return
    try:
        if rollback and db.in_transaction():
            db.rollback()
    finally:
        db.close()
        setattr(request.state, REQUEST_DB_SESSION_KEY, None)


def ensure_runtime_schema():
    """
    Legacy SQLite household backfills were removed with the household domain.

    PostgreSQL schema is managed by Alembic. SQLite tests create the current
    metadata directly.
    """
    return

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/family_hero_hub.sqlite"
    SECRET_KEY: str = "secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    PUBLIC_APP_URL: str = "http://localhost:5173"
    API_BASE_URL: str = "http://localhost:8000"
    APP_ENV: str = "development"
    PARENT_EMAILS: str = "parent@example.com"
    SESSION_SECRET: str = "session_secret"
    DEV_AUTH_ENABLED: bool = False
    DEV_AUTH_PARENT_EMAIL: str = "parent@example.com"
    CORS_ORIGINS: str = "https://families.loginto.me,http://localhost:5173,http://localhost:8000"

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

engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

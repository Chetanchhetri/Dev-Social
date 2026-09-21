import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "DevSocial"
    SECRET_KEY: str = "super-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    OTP_EXPIRE_MINUTES: int = 10

    # Database & Redis
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres_password@localhost:5432/devsocial_db"
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    MEDIA_DIR: str = "uploads"

    # Superadmin Defaults from ENV
    SUPERADMIN_NAME: str = "Super Admin"
    SUPERADMIN_EMAIL: str = "superadmin@devsocial.com"
    SUPERADMIN_PASSWORD: str = "SuperAdminPassword123!"

    # SMTP Mail Credentials
    EMAIL_SENDER: Optional[str] = ""
    EMAIL_PASSWORD: Optional[str] = ""

    # Pydantic v2 Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",         # Silently ignore unmapped .env variables instead of throwing ValidationError
        case_sensitive=False
    )

settings = Settings()
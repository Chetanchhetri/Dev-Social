import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "DevSocial"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-change-in-production-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    OTP_EXPIRE_MINUTES: int = 10

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+psycopg2://postgres:postgres_password@db:5432/devsocial_db"
    )

    # Superadmin Defaults from ENV
    SUPERADMIN_NAME: str = os.getenv("SUPERADMIN_NAME", "Super Admin")
    SUPERADMIN_EMAIL: str = os.getenv("SUPERADMIN_EMAIL", "superadmin@devsocial.com")
    SUPERADMIN_PASSWORD: str = os.getenv("SUPERADMIN_PASSWORD", "SuperAdminPassword123!")

    # SMTP Mail Credentials
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")

    class Config:
        env_file = ".env"

settings = Settings()
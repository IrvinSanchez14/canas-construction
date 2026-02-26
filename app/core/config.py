from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import os


class Settings(BaseSettings):
    """Application settings with AWS best practices."""

    def __init__(self, **kwargs):
        # pydantic_settings JSON-parses List fields from env vars before
        # validators run. Empty strings cause JSONDecodeError, so temporarily
        # remove them to let defaults apply instead.
        _list_env_vars = ["SETUP_ALLOWED_EMAILS", "CORS_ORIGINS"]
        _removed = {}
        for var in _list_env_vars:
            val = os.environ.get(var)
            if val is not None and not val.strip():
                _removed[var] = os.environ.pop(var)
        try:
            super().__init__(**kwargs)
        finally:
            os.environ.update(_removed)

    # Application
    APP_NAME: str = "Canas Construction API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 0

    # Redis
    REDIS_URL: Optional[str] = None

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # CORS - Allow JSON string for AWS environment variables
    # Default includes common development ports: React (3000), Vite (5173), Next.js (3000)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None

    # Cloudflare R2 Configuration
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: Optional[str] = None
    R2_PUBLIC_URL: Optional[str] = None  # Optional: Custom domain or public bucket URL

    # Logging
    LOG_LEVEL: str = "INFO"

    # Resend Email Configuration
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "notifications@canas-construction.com"
    RESEND_FROM_NAME: str = "Canas Construction Notifications"

    # Company Branding
    COMPANY_LOGO_URL: str = ""
    COMPANY_NAME: str = "Canas Construction"

    # Setup
    SETUP_ALLOWED_EMAILS: List[str] = []
    FRONTEND_URL: str = "http://localhost:5173"

    @field_validator("SETUP_ALLOWED_EMAILS", mode="before")
    @classmethod
    def parse_setup_allowed_emails(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [email.strip() for email in v.split(",") if email.strip()]
        return v

    # Feature Flags
    NOTIFICATIONS_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"


settings = Settings()

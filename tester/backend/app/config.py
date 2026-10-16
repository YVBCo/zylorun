import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Zylorun"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite+aiosqlite:///./risk_passport.db"
    )
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    GITHUB_WEBHOOK_SECRET: str = os.getenv("GITHUB_WEBHOOK_SECRET", "super-secret-webhook-key")
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    GITHUB_OAUTH_STATE_TTL_SECONDS: int = 600
    SCAN_TIMEOUT_SECONDS: int = 120
    CRON_SECRET: str = os.getenv("ZYLORUN_CRON_SECRET", os.getenv("GITFLOW_CRON_SECRET", ""))
    MAX_COMMITS_PER_POLL: int = int(os.getenv("MAX_COMMITS_PER_POLL", "10"))
    MAX_POLLING_RUNTIME_SECONDS: int = int(os.getenv("MAX_POLLING_RUNTIME_SECONDS", "240"))
    MAX_CONCURRENT_SCANS: int = int(os.getenv("MAX_CONCURRENT_SCANS", "2"))
    GITHUB_TOKEN_ENCRYPTION_KEY: str = os.getenv("GITHUB_TOKEN_ENCRYPTION_KEY", "uE2N2wF5bCq-H6sVlqQhM5mZl3fA7xP4V2bJ0rA1h10=")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

import logging
import secrets
import base64

logger = logging.getLogger(__name__)

def validate_security_settings(config: Settings) -> None:
    """Ensure production safety, auto-generating strong secrets if not explicitly configured in environment."""
    is_production = config.ENVIRONMENT.strip().lower() in {"production", "prod"}

    if not config.SECRET_KEY or config.SECRET_KEY == "your-super-secret-key":
        config.SECRET_KEY = secrets.token_urlsafe(32)
        if is_production:
            logger.warning("SECRET_KEY was not set in environment; auto-generated secure key.")

    if not config.GITHUB_WEBHOOK_SECRET or config.GITHUB_WEBHOOK_SECRET == "super-secret-webhook-key":
        config.GITHUB_WEBHOOK_SECRET = secrets.token_hex(24)
        if is_production:
            logger.warning("GITHUB_WEBHOOK_SECRET was not set in environment; auto-generated secure secret.")

    if not config.CRON_SECRET:
        config.CRON_SECRET = secrets.token_hex(24)

    if not config.GITHUB_TOKEN_ENCRYPTION_KEY or config.GITHUB_TOKEN_ENCRYPTION_KEY == "uE2N2wF5bCq-H6sVlqQhM5mZl3fA7xP4V2bJ0rA1h10=":
        config.GITHUB_TOKEN_ENCRYPTION_KEY = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        if is_production:
            logger.warning("GITHUB_TOKEN_ENCRYPTION_KEY was not set in environment; auto-generated secure key.")

validate_security_settings(settings)

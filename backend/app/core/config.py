"""Application configuration settings using Pydantic Settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the backend (root of the backend package)
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings class loaded from environment or defaults."""

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "Emergency Response Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./emergency_response.db"
    SECRET_KEY: str = "change-this-development-secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


settings = Settings()

"""Application configuration settings using Pydantic Settings."""

import json
from pathlib import Path
from typing import Any
from pydantic import field_validator
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
    PORT: int = 8000
    DATABASE_URL: str = "sqlite:///./emergency_response.db"
    SECRET_KEY: str = "change-this-development-secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    API_V1_STR: str = "/api/v1"
    UPLOAD_DIR: Path = BACKEND_DIR / "uploads" / "report_photos"

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from a list, JSON array string, or comma-separated string."""
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v == "*":
                return ["*"]
            if v.startswith("[") and v.endswith("]"):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(o).strip().rstrip("/") for o in parsed if str(o).strip()]
                except Exception:
                    pass
            return [o.strip().rstrip("/") for o in v.split(",") if o.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(o).strip().rstrip("/") for o in v if str(o).strip()]
        return []

    @field_validator("UPLOAD_DIR", mode="before")
    @classmethod
    def parse_upload_dir(cls, v: Any) -> Path:
        """Ensure UPLOAD_DIR is a valid Path object."""
        if isinstance(v, str):
            return Path(v)
        return v

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Normalize database connection URL (e.g. Render postgres:// to postgresql://)."""
        url = (self.DATABASE_URL or "").strip()
        if not url:
            url = "sqlite:///./emergency_response.db"
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


settings = Settings()

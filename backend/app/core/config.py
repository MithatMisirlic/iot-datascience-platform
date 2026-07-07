"""Validated application configuration loaded from environment variables."""

from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend settings shared by startup, persistence, and integrations."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "sqlite:///./data/experiment_platform.db"
    upload_dir: Path = Path("./data/uploads")
    testing_mode: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    pi_adapter_mode: Literal["noop"] = "noop"
    cors_origins: str = "http://localhost:3000,http://localhost:8501"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Reject an empty database connection string."""

        value = value.strip()
        if not value:
            raise ValueError("DATABASE_URL must not be empty.")
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        """Accept conventional case-insensitive logging level values."""

        return value.upper() if isinstance(value, str) else value

    @property
    def cors_origin_list(self) -> list[str]:
        """Return normalized browser origins for CORS middleware."""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def resolved_upload_dir(self) -> Path:
        """Return the absolute artifact storage directory."""

        return self.upload_dir.expanduser().resolve()

    def validate_runtime(self) -> None:
        """Validate path settings that depend on the host filesystem."""

        upload_dir = self.resolved_upload_dir
        filesystem_root = Path(upload_dir.anchor).resolve()
        if upload_dir == filesystem_root:
            raise ValueError("UPLOAD_DIR must not be a filesystem root.")
        if upload_dir.exists() and not upload_dir.is_dir():
            raise ValueError("UPLOAD_DIR must reference a directory.")


settings = Settings()

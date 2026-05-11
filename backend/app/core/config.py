from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LeadFlow AI API"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./leadflow.db"
    secret_key: str = "development-only-change-me-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    ai_provider: str = Field(
        default="mock",
        validation_alias=AliasChoices("AI_PROVIDER", "LLM_PROVIDER"),
    )
    openai_api_key: str | None = None
    gemini_api_key: str | None = None

    upload_dir: Path = Path("../uploads")
    export_dir: Path = Path("../exports")
    max_upload_size_mb: int = 10

    cors_origins: list[str] = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

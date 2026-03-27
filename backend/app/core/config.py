from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="KVITT_",
        extra="ignore",
    )

    app_name: str = "KVITT API"
    app_version: str = "0.1.0"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"
    default_access_tier: str = "free"
    auto_create_tables: bool = True
    require_db_ready: bool = True
    database_url: str = Field(
        default="postgresql+psycopg://kvitt:kvitt@localhost:5432/kvitt"
    )
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout_seconds: float = 8.0
    openai_categorization_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    github_token: str | None = None
    github_api_base_url: str = "https://api.github.com"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    database_url: str | None = None
    analysis_cache_ttl_seconds: int = Field(default=900, ge=0)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache  # ilk çağrıda Settings() oluşturur. Sonraki çağrılarda cache'lenmiş aynı nesneyi döndürür.
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    github_token: str | None = None
    github_api_base_url: str = "https://api.github.com"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache  # ilk çağrıda Settings() oluşturur. Sonraki çağrılarda cache'lenmiş aynı nesneyi döndürür.
def get_settings() -> Settings:
    return Settings()

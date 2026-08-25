from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORS_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


class Settings(BaseSettings):
    github_token: str | None = None
    github_api_base_url: str = "https://api.github.com"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    database_url: str | None = None
    analysis_cache_ttl_seconds: int = Field(default=900, ge=0)
    cors_allowed_origins: str = DEFAULT_CORS_ALLOWED_ORIGINS

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_allowed_origins(cls, value: str) -> str:
        origins = cls._parse_cors_origins(value)
        if not origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must contain at least one origin.")
        return ",".join(origins)

    @staticmethod
    def _parse_cors_origins(value: str) -> list[str]:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        for origin in origins:
            if origin == "*":
                raise ValueError("Wildcard CORS origins are not allowed.")
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise ValueError(f"Invalid CORS origin: {origin}")
        return origins

    @property
    def cors_origins(self) -> list[str]:
        return self._parse_cors_origins(self.cors_allowed_origins)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache  # ilk çağrıda Settings() oluşturur. Sonraki çağrılarda cache'lenmiş aynı nesneyi döndürür.
def get_settings() -> Settings:
    return Settings()

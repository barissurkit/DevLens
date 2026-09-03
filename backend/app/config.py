from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.auth.crypto import decode_encryption_key

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORS_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


class Settings(BaseSettings):
    environment: Literal["development", "test", "production"] = "development"
    auth_enabled: bool | None = None
    github_token: str | None = None
    github_api_base_url: str = "https://api.github.com"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash"
    database_url: str | None = None
    analysis_cache_ttl_seconds: int = Field(default=900, ge=0)
    cors_allowed_origins: str = DEFAULT_CORS_ALLOWED_ORIGINS
    github_app_client_id: str | None = None
    github_app_client_secret: str | None = None
    github_app_callback_url: str | None = None
    auth_state_encryption_key: str | None = None
    frontend_origin: str | None = None

    @field_validator(
        "github_app_client_id",
        "github_app_client_secret",
        "github_app_callback_url",
        "auth_state_encryption_key",
        "frontend_origin",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_allowed_origins(cls, value: str) -> str:
        origins = cls._parse_cors_origins(value)
        if not origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must contain at least one origin.")
        return ",".join(origins)

    @model_validator(mode="after")
    def validate_structural_configuration(self) -> "Settings":
        oauth_values = (
            self.github_app_client_id,
            self.github_app_client_secret,
            self.github_app_callback_url,
            self.auth_state_encryption_key,
        )
        if any(oauth_values) and not all(oauth_values):
            raise ValueError("GitHub OAuth configuration is incomplete.")

        if self.github_app_callback_url:
            parsed = urlsplit(self.github_app_callback_url)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or parsed.path != "/api/v1/auth/github/callback"
            ):
                raise ValueError("GITHUB_APP_CALLBACK_URL is invalid.")

        if self.frontend_origin:
            parsed = urlsplit(self.frontend_origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise ValueError("FRONTEND_ORIGIN is invalid.")

        if self.auth_state_encryption_key:
            decode_encryption_key(self.auth_state_encryption_key)
        return self

    def validate_runtime_configuration(self) -> None:
        if self.environment == "production" and self.auth_enabled is None:
            raise ValueError("AUTH_ENABLED must be explicitly set in production.")

        frontend_origin = self.auth_frontend_origin
        if self.environment == "production":
            if not self.frontend_origin:
                raise ValueError("FRONTEND_ORIGIN is required in production.")
            if not frontend_origin.startswith("https://"):
                raise ValueError("Production frontend origin must use HTTPS.")
            if any(not origin.startswith("https://") for origin in self.cors_origins):
                raise ValueError("Production CORS origins must use HTTPS.")

        if self.auth_enabled:
            if not all(
                (
                    self.github_app_client_id,
                    self.github_app_client_secret,
                    self.github_app_callback_url,
                    self.auth_state_encryption_key,
                )
            ):
                raise ValueError("Authentication requires complete GitHub OAuth configuration.")
            if not self.database_url:
                raise ValueError("Authentication requires DATABASE_URL.")
            callback_url = self.github_app_callback_url
            if self.environment == "production" and not callback_url.startswith("https://"):
                raise ValueError("Production GitHub OAuth callback must use HTTPS.")

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

    @property
    def auth_frontend_origin(self) -> str:
        origin = self.frontend_origin or self.cors_origins[0]
        if origin not in self.cors_origins:
            raise ValueError("FRONTEND_ORIGIN must be included in CORS_ALLOWED_ORIGINS.")
        return origin

    @property
    def auth_cookie_secure(self) -> bool:
        return self.environment == "production"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        hide_input_in_errors=True,
        extra="ignore",
    )


@lru_cache  # ilk çağrıda Settings() oluşturur. Sonraki çağrılarda cache'lenmiş aynı nesneyi döndürür.
def get_settings() -> Settings:
    return Settings()

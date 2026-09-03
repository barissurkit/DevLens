import base64

from app.config import Settings, get_settings

import pytest


def test_default_github_api_base_url() -> None:
    settings = Settings(_env_file=None)

    assert settings.github_api_base_url == "https://api.github.com"


def test_analysis_cache_ttl_defaults_to_fifteen_minutes() -> None:
    assert Settings(_env_file=None).analysis_cache_ttl_seconds == 900


def test_analysis_cache_ttl_rejects_negative_values() -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, analysis_cache_ttl_seconds=-1)


def test_enviroment_variable_overrides_default(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_API_BASE_URL", "https://example.test")
    # monkeypatch.setenv() : pytest'in yerleşik fixture'ıdır. test süresince environment variable ekler ve test bitince değişikliği geri alır.

    settings = Settings(_env_file=None)
    # _env_file=None ile test sırasında proje root'undaki .env dosyasını devre dışı bırakır.

    assert settings.github_api_base_url == "https://example.test"


def test_get_settings_returns_cached_instance() -> None:

    first = get_settings()
    second = get_settings()

    assert first is second


def test_cors_origins_default_to_local_frontend_origins() -> None:
    settings = Settings(_env_file=None)

    assert settings.cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_cors_origins_normalize_whitespace_and_support_multiple_origins() -> None:
    settings = Settings(
        _env_file=None,
        cors_allowed_origins=" https://devlens.example , https://admin.example ",
    )

    assert settings.cors_origins == [
        "https://devlens.example",
        "https://admin.example",
    ]


@pytest.mark.parametrize(
    "value",
    ["", "*", "http://", "ftp://devlens.example", "https://devlens.example/path"],
)
def test_cors_origins_reject_malformed_or_wildcard_values(value: str) -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, cors_allowed_origins=value)


def _auth_values() -> dict[str, str]:
    return {
        "github_app_client_id": "client-id",
        "github_app_client_secret": "client-secret",
        "github_app_callback_url": "https://api.example.com/api/v1/auth/github/callback",
        "auth_state_encryption_key": base64.urlsafe_b64encode(b"k" * 32).decode(),
    }


def _production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "environment": "production",
        "auth_enabled": True,
        "database_url": "postgresql+asyncpg://db.example/test",
        "frontend_origin": "https://frontend.example",
        "cors_allowed_origins": "https://frontend.example",
        **_auth_values(),
    }
    values.update(overrides)
    return Settings(**values)


def test_environment_defaults_to_development_and_auth_is_opt_in() -> None:
    settings = Settings(_env_file=None)
    assert settings.environment == "development"
    assert settings.auth_enabled is None


def test_partial_oauth_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="OAuth configuration is incomplete"):
        Settings(_env_file=None, github_app_client_id="client-id")


def test_supplied_encryption_key_must_decode_to_32_bytes() -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        Settings(
            _env_file=None,
            github_app_client_id="client-id",
            github_app_client_secret="client-secret",
            github_app_callback_url="https://api.example.com/api/v1/auth/github/callback",
            auth_state_encryption_key="aW52YWxpZA",
        )


def test_production_requires_explicit_auth_flag_and_https_origins() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        frontend_origin="https://frontend.example",
        cors_allowed_origins="https://frontend.example",
    )
    with pytest.raises(ValueError, match="AUTH_ENABLED"):
        settings.validate_runtime_configuration()

    http_settings = Settings(
        _env_file=None,
        environment="production",
        auth_enabled=False,
        frontend_origin="http://frontend.example",
        cors_allowed_origins="http://frontend.example",
    )
    with pytest.raises(ValueError, match="HTTPS"):
        http_settings.validate_runtime_configuration()


def test_production_auth_requires_database_and_https_callback() -> None:
    settings = _production_settings(database_url=None)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        settings.validate_runtime_configuration()

    settings = _production_settings(
        github_app_callback_url="http://api.example.com/api/v1/auth/github/callback"
    )
    with pytest.raises(ValueError, match="callback must use HTTPS"):
        settings.validate_runtime_configuration()


def test_valid_production_configuration_passes_runtime_validation() -> None:
    settings = _production_settings()
    settings.validate_runtime_configuration()
    assert settings.auth_cookie_secure is True

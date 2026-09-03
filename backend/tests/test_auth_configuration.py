import asyncio
import base64

import pytest
from fastapi import Request, Response

import app.api.auth as auth_api
from app.config import Settings
from app.main import create_app


def _key() -> str:
    return base64.urlsafe_b64encode(b"k" * 32).decode()


def _production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "environment": "production",
        "auth_enabled": True,
        "database_url": "postgresql+asyncpg://db.example/test",
        "frontend_origin": "https://frontend.example",
        "cors_allowed_origins": "https://frontend.example",
        "github_app_client_id": "client-id",
        "github_app_client_secret": "client-secret",
        "github_app_callback_url": "https://api.example.com/api/v1/auth/github/callback",
        "auth_state_encryption_key": _key(),
    }
    values.update(overrides)
    return Settings(**values)


def _request_for(application) -> Request:
    request = Request({"type": "http", "headers": []})
    request.scope["app"] = application
    return request


def test_create_app_fails_before_serving_invalid_production_configuration() -> None:
    invalid = _production_settings(auth_enabled=None)
    with pytest.raises(ValueError, match="AUTH_ENABLED"):
        create_app(invalid)


def test_custom_app_settings_are_used_by_auth_client_dependency(monkeypatch) -> None:
    settings_a = _production_settings(github_app_client_id="settings-a")
    settings_b = _production_settings(github_app_client_id="settings-b")
    application = create_app(settings_a)

    captured: list[Settings] = []

    class FakeAuthClient:
        def __init__(self, settings: Settings) -> None:
            captured.append(settings)

    monkeypatch.setattr(auth_api, "GitHubAuthClient", FakeAuthClient)
    monkeypatch.setattr(auth_api, "get_settings", lambda: settings_b, raising=False)

    client = asyncio.run(auth_api.get_auth_github_client(_request_for(application)))

    assert isinstance(client, FakeAuthClient)
    assert captured == [settings_a]


def test_production_cookie_contract_uses_environment_authority() -> None:
    production_response = Response()
    auth_api._set_session_cookie(
        production_response, _production_settings(), "opaque-token", 60
    )
    production_cookie = production_response.headers["set-cookie"]
    assert production_cookie.startswith("__Host-devlens_session=opaque-token")
    assert "Secure" in production_cookie
    assert "HttpOnly" in production_cookie
    assert "SameSite=lax" in production_cookie
    assert "Path=/" in production_cookie
    assert "Domain=" not in production_cookie

    development_response = Response()
    auth_api._set_session_cookie(
        development_response,
        Settings(_env_file=None, environment="test"),
        "opaque-token",
        60,
    )
    development_cookie = development_response.headers["set-cookie"]
    assert development_cookie.startswith("devlens_session=opaque-token")
    assert "Secure" not in development_cookie


def test_complete_oauth_configuration_does_not_enable_auth_when_flag_is_false() -> None:
    settings = _production_settings(auth_enabled=False)
    assert auth_api._configuration_error(settings) == "Authentication is not configured."


def test_auth_disabled_does_not_create_github_auth_client(monkeypatch) -> None:
    application = create_app(
        _production_settings(auth_enabled=False)
    )

    def fail_if_called(settings: Settings):
        raise AssertionError("GitHub auth client must not be created when auth is disabled")

    monkeypatch.setattr(auth_api, "GitHubAuthClient", fail_if_called)
    client = asyncio.run(auth_api.get_auth_github_client(_request_for(application)))

    assert client is None

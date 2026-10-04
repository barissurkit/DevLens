from app.config import get_settings
from app.main import app, health_check


def test_health_check() -> None:
    response = health_check()

    assert response.model_dump(exclude_none=True) == {"status": "ok"}


def test_health_endpoint_is_registered() -> None:
    assert "/health" in app.openapi()["paths"]


def test_app_uses_cached_settings() -> None:
    assert app.state.settings is get_settings()

    assert app.state.settings.github_api_base_url == get_settings().github_api_base_url


def test_health_reports_configuration_flags_without_secrets() -> None:
    from app.config import Settings

    settings = Settings(_env_file=None, github_token="ghp_secret", gemini_api_key=None, database_url=None)

    body = health_check(settings).model_dump()

    assert body == {
        "status": "ok",
        "github_token_configured": True,
        "ai_configured": False,
        "database_configured": False,
    }
    assert "ghp_secret" not in str(body)


def test_health_endpoint_returns_flags() -> None:
    from fastapi.testclient import TestClient

    from app.config import Settings
    from app.main import create_app

    client = TestClient(create_app(Settings(_env_file=None, github_token="x")))

    assert client.get("/health").json()["github_token_configured"] is True

from app.config import get_settings
from app.main import app, health_check


def test_health_check() -> None:
    response = health_check()

    assert response.model_dump() == {"status": "ok"}


def test_health_endpoint_is_registered() -> None:
    assert "/health" in app.openapi()["paths"]


def test_app_uses_cached_settings() -> None:
    assert app.state.settings is get_settings()

    assert app.state.settings.github_api_base_url == get_settings().github_api_base_url

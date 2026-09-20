import asyncio
import os

import app.api.github as github_api
import app.main as main_module
from app.config import Settings, get_settings
from app.main import create_app
from fastapi import Request


def _request_for(application) -> Request:
    request = Request({"type": "http", "headers": []})
    request.scope["app"] = application
    return request


def _settings(label: str) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        auth_enabled=False,
        github_token=f"github-token-{label}",
        github_api_base_url=f"https://github-{label}.example",
        gemini_api_key=f"gemini-key-{label}",
        gemini_model=f"gemini-model-{label}",
        database_url=f"postgresql+asyncpg://{label}/devlens",
        cors_allowed_origins="http://localhost:3000",
    )


def test_request_factories_use_the_owning_app_settings(monkeypatch) -> None:
    settings_a = _settings("a")
    settings_b = _settings("b")
    app_a = create_app(settings_a)
    app_b = create_app(settings_b)
    captured: dict[str, list[Settings]] = {
        "github": [],
        "gemini": [],
        "persistence": [],
        "cache": [],
        "history": [],
    }

    class CapturingGitHubClient:
        def __init__(self, settings: Settings) -> None:
            captured["github"].append(settings)

    class CapturingGeminiClient:
        def __init__(self, settings: Settings) -> None:
            captured["gemini"].append(settings)

    class CapturingPersistenceService:
        def __init__(self, settings: Settings) -> None:
            captured["persistence"].append(settings)

    class CapturingCacheService:
        def __init__(self, settings: Settings) -> None:
            captured["cache"].append(settings)

    class CapturingHistoryService:
        def __init__(self, settings: Settings) -> None:
            captured["history"].append(settings)

    monkeypatch.setattr(github_api, "GitHubClient", CapturingGitHubClient)
    monkeypatch.setattr(github_api, "GeminiClient", CapturingGeminiClient)
    monkeypatch.setattr(
        github_api,
        "AnalysisSnapshotPersistenceService",
        CapturingPersistenceService,
    )
    monkeypatch.setattr(
        github_api,
        "AnalysisSnapshotCacheService",
        CapturingCacheService,
    )
    monkeypatch.setattr(github_api, "PortfolioHistoryService", CapturingHistoryService)

    async def resolve(application) -> None:
        request = _request_for(application)
        await github_api.get_github_client(request)
        await github_api.get_gemini_client(request)
        await github_api.get_snapshot_persistence_service(request)
        await github_api.get_analysis_snapshot_cache_service(request)
        await github_api.get_portfolio_history_service(request)

    asyncio.run(resolve(app_a))
    asyncio.run(resolve(app_b))

    for settings in captured.values():
        assert settings == [settings_a, settings_b]
        assert settings[0] is app_a.state.settings
        assert settings[1] is app_b.state.settings


def test_existing_app_ignores_environment_cache_reconstruction(monkeypatch) -> None:
    settings_a = _settings("stable")
    application = create_app(settings_a)
    captured: list[Settings] = []
    original_environment_value = os.environ.get("GITHUB_API_BASE_URL")
    original_default_app_settings = main_module.app.state.settings

    class CapturingGitHubClient:
        def __init__(self, settings: Settings) -> None:
            captured.append(settings)

    monkeypatch.setattr(github_api, "GitHubClient", CapturingGitHubClient)
    monkeypatch.setenv("GITHUB_API_BASE_URL", "https://environment-mutated.example")
    get_settings.cache_clear()
    try:
        asyncio.run(github_api.get_github_client(_request_for(application)))
        assert captured == [settings_a]
    finally:
        if original_environment_value is None:
            os.environ.pop("GITHUB_API_BASE_URL", None)
        else:
            os.environ["GITHUB_API_BASE_URL"] = original_environment_value
        get_settings.cache_clear()
        main_module.app.state.settings = get_settings()
        assert main_module.app.state.settings is not original_default_app_settings

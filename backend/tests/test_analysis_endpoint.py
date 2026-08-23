import asyncio
from collections.abc import Iterator
from unittest.mock import AsyncMock

import httpx
import pytest

import app.api.analysis as analysis_api
from app.api.github import (
    get_analysis_snapshot_cache_service,
    get_github_client,
    get_snapshot_persistence_service,
)
from app.main import app
from app.schemas.analysis import (
    GitHubPortfolioAnalysis,
    PortfolioAggregation,
    PortfolioIntelligence,
    PortfolioRepositoryAnalysis,
    PortfolioRepositorySelection,
    PortfolioScore,
)
from app.schemas.github import GitHubUser
from app.services.github.client import GitHubClient


def create_result() -> GitHubPortfolioAnalysis:
    user = GitHubUser.model_validate(
        {
            "login": "synthetic-user",
            "name": None,
            "avatar_url": "https://avatars.example/user.png",
            "bio": None,
            "public_repos": 0,
            "followers": 0,
            "following": 0,
            "html_url": "https://github.com/synthetic-user",
            "created_at": "2025-01-01T00:00:00Z",
        }
    )
    return GitHubPortfolioAnalysis.model_construct(
        user=user,
        selection=PortfolioRepositorySelection.model_construct(
            version="1.0",
            selected=[],
            excluded=[],
        ),
        repository_analysis=PortfolioRepositoryAnalysis.model_construct(
            selection_version="1.0",
            repositories=[],
            failures=[],
            has_failures=False,
        ),
        aggregation=PortfolioAggregation.model_construct(
            selection_version="1.0",
            selected_repository_count=0,
            successful_repository_count=0,
            failed_repository_count=0,
            has_failures=False,
            partial_evidence_repository_count=0,
            technology_distribution=[],
            category_distribution=[],
            primary_category_distribution=[],
            portfolio_signals=[],
            repository_score_distribution=[],
        ),
        intelligence=PortfolioIntelligence.model_construct(
            version="1.0",
            strength_signals=[],
            improvement_signals=[],
            recurring_technologies=[],
            dominant_areas=[],
            limitations=["No analyzed repositories."],
        ),
        score=PortfolioScore.model_construct(
            version="1.0",
            is_available=False,
            overall_score=None,
            scored_repository_count=0,
            dimensions=[],
            is_partial=False,
            limitations=["A portfolio score requires analyzed repositories."],
        ),
    )


def request_app(payload: object) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.post("/api/v1/analysis", json=payload)

    return asyncio.run(send_request())


def use_mock_client(mock_client: AsyncMock) -> None:
    async def override_github_client() -> AsyncMock:
        return mock_client

    app.dependency_overrides[get_github_client] = override_github_client


def use_mock_persistence(mock_persistence: object) -> None:
    async def override_persistence() -> object:
        return mock_persistence

    app.dependency_overrides[get_snapshot_persistence_service] = override_persistence


def use_mock_cache(mock_cache: object) -> None:
    async def override_cache() -> object:
        return mock_cache

    app.dependency_overrides[get_analysis_snapshot_cache_service] = override_cache


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def test_analysis_route_is_registered_with_typed_response() -> None:
    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/analysis"
    )

    assert "POST" in route.methods
    assert route.response_model is GitHubPortfolioAnalysis


def test_analysis_openapi_documents_public_contract() -> None:
    operation = app.openapi()["paths"]["/api/v1/analysis"]["post"]

    assert operation["tags"] == ["Analysis"]
    assert operation["summary"] == "Analyze a GitHub portfolio"
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/PortfolioAnalysisRequest"
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/GitHubPortfolioAnalysis"
    }

    for status_code in ("404", "429", "502", "503"):
        assert operation["responses"][status_code]["content"]["application/json"][
            "schema"
        ] == {"$ref": "#/components/schemas/APIErrorResponse"}

    request_schema = app.openapi()["components"]["schemas"]["PortfolioAnalysisRequest"]
    assert request_schema["additionalProperties"] is False
    assert request_schema["properties"]["username"]["maxLength"] == 39


def test_analysis_endpoint_calls_application_service_once() -> None:
    mock_client = AsyncMock(spec=GitHubClient)
    use_mock_client(mock_client)
    application_mock = AsyncMock(return_value=create_result())
    original = analysis_api.run_github_portfolio_analysis
    analysis_api.run_github_portfolio_analysis = application_mock

    try:
        response = request_app({"username": "synthetic-user"})
    finally:
        analysis_api.run_github_portfolio_analysis = original

    assert response.status_code == 200
    assert set(response.json()) == {
        "user",
        "selection",
        "repository_analysis",
        "aggregation",
        "intelligence",
        "score",
    }
    assert response.json()["score"]["overall_score"] is None
    application_mock.assert_awaited_once_with(
        username="synthetic-user",
        client=mock_client,
    )


def test_analysis_endpoint_persists_one_analysis_only_snapshot() -> None:
    mock_client = AsyncMock(spec=GitHubClient)
    use_mock_client(mock_client)
    persistence = AsyncMock()
    use_mock_persistence(persistence)
    application_mock = AsyncMock(return_value=create_result())
    original = analysis_api.run_github_portfolio_analysis
    analysis_api.run_github_portfolio_analysis = application_mock

    try:
        response = request_app({"username": "synthetic-user"})
    finally:
        analysis_api.run_github_portfolio_analysis = original

    assert response.status_code == 200
    persistence.persist.assert_awaited_once()
    persistence_call = persistence.persist.await_args.kwargs
    assert persistence_call["analysis"] is application_mock.return_value
    assert persistence_call["analysis_generated_at"].tzinfo is not None
    assert persistence_call["request_kind"] == "analysis"


def test_analysis_endpoint_returns_fresh_cached_analysis_without_pipeline_or_write() -> None:
    cached = create_result()
    cache = AsyncMock()
    cache.get_fresh_analysis.return_value = type(
        "CachedAnalysis", (), {"analysis": cached}
    )()
    use_mock_cache(cache)
    persistence = AsyncMock()
    use_mock_persistence(persistence)
    application_mock = AsyncMock(side_effect=AssertionError("cache hit must skip pipeline"))
    original = analysis_api.run_github_portfolio_analysis
    analysis_api.run_github_portfolio_analysis = application_mock

    try:
        response = request_app({"username": "synthetic-user"})
    finally:
        analysis_api.run_github_portfolio_analysis = original

    assert response.status_code == 200
    assert response.json() == cached.model_dump(mode="json")
    application_mock.assert_not_awaited()
    persistence.persist.assert_not_awaited()


@pytest.mark.parametrize(
    ("payload", "status_code"),
    [
        ({}, 422),
        ({"username": 42}, 422),
        ({"username": ""}, 422),
        ({"username": "   "}, 422),
        ({"username": "a" * 40}, 422),
        ({"username": "synthetic-user", "max_concurrency": 100}, 422),
    ],
)
def test_analysis_endpoint_validates_request(
    payload: object,
    status_code: int,
) -> None:
    response = request_app(payload)

    assert response.status_code == status_code


def test_analysis_endpoint_maps_user_not_found() -> None:
    mock_client = AsyncMock(spec=GitHubClient)
    request = httpx.Request("GET", "https://api.github.com/users/missing")
    response = httpx.Response(404, request=request)
    mock_client.get_user.side_effect = httpx.HTTPStatusError(
        "Synthetic user not found.",
        request=request,
        response=response,
    )
    use_mock_client(mock_client)

    result = request_app({"username": "missing"})

    assert result.status_code == 404
    assert result.json() == {
        "detail": {
            "code": "github_user_not_found",
            "message": "GitHub user was not found.",
        }
    }


def test_analysis_endpoint_normalizes_username_whitespace() -> None:
    mock_client = AsyncMock(spec=GitHubClient)
    use_mock_client(mock_client)
    application_mock = AsyncMock(return_value=create_result())
    original = analysis_api.run_github_portfolio_analysis
    analysis_api.run_github_portfolio_analysis = application_mock

    try:
        response = request_app({"username": "  synthetic-user  "})
    finally:
        analysis_api.run_github_portfolio_analysis = original

    assert response.status_code == 200
    application_mock.assert_awaited_once_with(
        username="synthetic-user",
        client=mock_client,
    )


def test_analysis_endpoint_does_not_map_unexpected_internal_errors() -> None:
    mock_client = AsyncMock(spec=GitHubClient)
    use_mock_client(mock_client)
    application_mock = AsyncMock(side_effect=RuntimeError("synthetic bug"))
    original = analysis_api.run_github_portfolio_analysis
    analysis_api.run_github_portfolio_analysis = application_mock

    try:
        with pytest.raises(RuntimeError, match="synthetic bug"):
            request_app({"username": "synthetic-user"})
    finally:
        analysis_api.run_github_portfolio_analysis = original

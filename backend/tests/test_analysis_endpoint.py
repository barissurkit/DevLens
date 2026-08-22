import asyncio
from collections.abc import Iterator
from unittest.mock import AsyncMock

import httpx
import pytest

import app.api.analysis as analysis_api
from app.api.github import get_github_client
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


@pytest.mark.parametrize(
    ("payload", "status_code"),
    [({}, 422), ({"username": 42}, 422), ({"username": ""}, 422)],
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
    assert result.json() == {"detail": "GitHub user not found."}


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

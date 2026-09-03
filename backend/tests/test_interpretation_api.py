import asyncio
import logging
from collections.abc import Iterator
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

import app.api.interpretation as interpretation_api
from app.api.github import (
    get_analysis_snapshot_cache_service,
    get_gemini_client,
    get_github_client,
    get_portfolio_history_service,
    get_snapshot_persistence_service,
)
from app.api.auth import get_optional_authenticated_user
from app.main import app
from app.schemas.analysis import PortfolioScore, PortfolioScoreDimensionResult, PortfolioScoreRuleResult
from app.schemas.interpretation import (
    InterpretationUnavailableReason,
    PortfolioInterpretation,
    PortfolioInterpretationResult,
)
from app.services.github.client import GitHubClient
from app.services.analysis_snapshot_cache import CachedAnalysis
from app.services.portfolio_history import PortfolioHistoryService
from app.config import Settings
from uuid import uuid4

from test_analysis_e2e import portfolio_fixture, use_fake_github
from test_analysis_endpoint import create_result


def request_app(payload: object) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/api/v1/interpretation", json=payload)

    return asyncio.run(send_request())


def use_mock_github(mock_client: AsyncMock) -> None:
    async def override() -> AsyncMock:
        return mock_client

    app.dependency_overrides[get_github_client] = override


def use_mock_gemini(mock_client: object) -> None:
    async def override() -> object:
        return mock_client

    app.dependency_overrides[get_gemini_client] = override


def use_mock_persistence(mock_persistence: object) -> None:
    async def override() -> object:
        return mock_persistence

    app.dependency_overrides[get_snapshot_persistence_service] = override


def use_mock_cache(mock_cache: object) -> None:
    async def override() -> object:
        return mock_cache

    app.dependency_overrides[get_analysis_snapshot_cache_service] = override


def use_authenticated_user(user: object) -> None:
    async def override() -> object:
        return user

    app.dependency_overrides[get_optional_authenticated_user] = override


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def test_interpretation_route_and_openapi_contract() -> None:
    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/interpretation"
    )

    assert "POST" in route.methods
    assert route.response_model is not None

    operation = app.openapi()["paths"]["/api/v1/interpretation"]["post"]
    assert operation["tags"] == ["Interpretation"]
    assert operation["summary"] == "Analyze a GitHub portfolio with optional interpretation"
    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ] == "#/components/schemas/GitHubPortfolioInterpretationResponse"
    for status_code in ("404", "429", "502", "503"):
        assert operation["responses"][status_code]["content"]["application/json"][
            "schema"
        ] == {"$ref": "#/components/schemas/APIErrorResponse"}


def test_available_response_is_composite_and_emits_one_safe_outcome_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="app")
    mock_github = AsyncMock(spec=GitHubClient)
    use_mock_github(mock_github)
    fake_gemini = SimpleNamespace(
        interpret=AsyncMock(return_value=PortfolioInterpretation(summary="Grounded."))
    )
    use_mock_gemini(fake_gemini)
    persistence = AsyncMock()
    use_mock_persistence(persistence)
    original = interpretation_api.analyze_and_interpret_github_portfolio
    composition = AsyncMock(
        return_value=SimpleNamespace(
            analysis=create_result(),
            interpretation=PortfolioInterpretationResult(
                available=True,
                interpretation=PortfolioInterpretation(summary="Grounded."),
            ),
        )
    )
    interpretation_api.analyze_and_interpret_github_portfolio = composition

    try:
        response = request_app({"username": "synthetic-user"})
    finally:
        interpretation_api.analyze_and_interpret_github_portfolio = original

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"analysis", "interpretation", "viewer_context", "guided_improvements"}
    assert body["guided_improvements"] == []
    assert body["viewer_context"] == {"is_owner": False, "mode": "explore"}
    assert body["interpretation"] == {
        "status": "available",
        "interpretation": {"summary": "Grounded.", "strength_explanations": [], "improvement_explanations": [], "technology_context": None, "project_area_context": None, "limitations_note": None, "next_project_recommendation": None},
    }
    assert "score" in body["analysis"]
    composition.assert_awaited_once_with(
        username="synthetic-user",
        github_client=mock_github,
        gemini_client=fake_gemini,
    )
    persistence.persist.assert_awaited_once()
    persistence_call = persistence.persist.await_args.kwargs
    assert persistence_call["analysis"] is composition.return_value.analysis
    assert persistence_call["interpretation"].model_dump(mode="json") == body["interpretation"]
    assert persistence_call["request_kind"] == "interpretation"
    events = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "interpretation.completed"
        and getattr(record, "request_id", None) == response.headers["x-request-id"]
    ]
    assert len(events) == 1
    assert events[0].operation == "interpretation"
    assert events[0].result == "available"
    assert not hasattr(events[0], "error_category")
    assert "synthetic-user" not in caplog.text
    assert "Grounded." not in caplog.text


def test_owner_interpretation_projects_guidance_when_gemini_is_unavailable() -> None:
    analysis = create_result()
    analysis.score = PortfolioScore(
        version="v1",
        is_available=True,
        overall_score=0,
        scored_repository_count=3,
        dimensions=[PortfolioScoreDimensionResult(
            key="documentation_consistency",
            label="Dokümantasyon Tutarlılığı",
            points_earned=0,
            points_possible=50,
            score=0,
            rules=[PortfolioScoreRuleResult(
                key="readme_usage",
                label="README kullanımı",
                weight=9,
                detected_repository_count=0,
                analyzed_repository_count=3,
            )],
        )],
        is_partial=False,
        limitations=[],
    )
    use_authenticated_user(SimpleNamespace(id=uuid4(), github_user_id=1))
    use_mock_cache(AsyncMock(get_fresh_analysis=AsyncMock(return_value=None)))
    use_mock_persistence(AsyncMock())
    use_mock_gemini(SimpleNamespace(interpret=AsyncMock(side_effect=AssertionError("Gemini should not be required by guidance"))))
    original = interpretation_api.analyze_and_interpret_github_portfolio
    interpretation_api.analyze_and_interpret_github_portfolio = AsyncMock(
        return_value=SimpleNamespace(
            analysis=analysis,
            interpretation=PortfolioInterpretationResult(
                available=False,
                reason=InterpretationUnavailableReason.NOT_CONFIGURED,
            ),
        )
    )
    try:
        response = request_app({"username": "synthetic-user"})
    finally:
        interpretation_api.analyze_and_interpret_github_portfolio = original

    assert response.status_code == 200
    assert response.json()["guided_improvements"][0]["rule_key"] == "readme_usage"


def test_interpretation_reuses_only_fresh_analysis_and_runs_current_policy() -> None:
    cached_analysis = create_result()
    cache = AsyncMock()
    cache.get_fresh_analysis.return_value = CachedAnalysis(
        analysis=cached_analysis,
        analysis_generated_at=datetime.now(timezone.utc),
    )
    use_mock_cache(cache)
    persistence = AsyncMock()
    use_mock_persistence(persistence)
    original_composition = interpretation_api.analyze_and_interpret_github_portfolio
    original_interpret = interpretation_api.interpret_github_portfolio
    composition_mock = AsyncMock(
        side_effect=AssertionError("cache hit must skip deterministic pipeline")
    )
    interpretation_api.analyze_and_interpret_github_portfolio = composition_mock
    interpretation_api.interpret_github_portfolio = AsyncMock(
        return_value=PortfolioInterpretationResult(
            available=False, reason=InterpretationUnavailableReason.INSUFFICIENT_EVIDENCE
        )
    )
    try:
        response = request_app({"username": "synthetic-user"})
    finally:
        interpretation_api.analyze_and_interpret_github_portfolio = original_composition
        interpretation_api.interpret_github_portfolio = original_interpret

    assert response.status_code == 200
    assert response.json()["analysis"] == cached_analysis.model_dump(mode="json")
    assert response.json()["interpretation"] == {
        "status": "unavailable", "reason": "insufficient_evidence"
    }
    composition_mock.assert_not_awaited()
    persistence.persist.assert_awaited_once()


def test_public_endpoint_runs_real_analysis_and_interpretation_composition() -> None:
    repositories, files = portfolio_fixture()
    use_fake_github(repositories, files_by_repository=files)

    class FakeGemini:
        def __init__(self) -> None:
            self.calls = []

        async def interpret(self, context):
            self.calls.append(context)
            from app.schemas.interpretation import InterpretationExplanation

            return PortfolioInterpretation(
                summary="Grounded portfolio interpretation.",
                strength_explanations=[
                    InterpretationExplanation(
                        signal_key=signal.key,
                        explanation="Grounded strength explanation.",
                    )
                    for signal in context.strength_signals
                ],
                improvement_explanations=[
                    InterpretationExplanation(
                        signal_key=signal.key,
                        explanation="Grounded improvement explanation.",
                    )
                    for signal in context.improvement_signals
                ],
            )

    fake_gemini = FakeGemini()
    use_mock_gemini(fake_gemini)

    response = request_app({"username": "  synthetic-user  "})

    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["score"]["overall_score"] == 95
    assert body["interpretation"]["status"] == "available"
    assert body["interpretation"]["interpretation"]["summary"] == (
        "Grounded portfolio interpretation."
    )
    assert len(fake_gemini.calls) == 1
    assert fake_gemini.calls[0].username == "synthetic-user"
    assert fake_gemini.calls[0].score.overall_score == 95
    assert "raw README" not in response.text
    assert "Authorization" not in response.text


def test_public_endpoint_preserves_insufficient_evidence_without_gemini_call(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="app")
    use_fake_github([])

    class FailingGemini:
        async def interpret(self, context):
            raise AssertionError("Gemini must not be called without evidence")

    use_mock_gemini(FailingGemini())

    response = request_app({"username": "synthetic-user"})

    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["aggregation"]["successful_repository_count"] == 0
    assert body["interpretation"] == {
        "status": "unavailable",
        "reason": "insufficient_evidence",
    }
    events = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "interpretation.completed"
        and getattr(record, "request_id", None) == response.headers["x-request-id"]
    ]
    assert len(events) == 1
    assert events[0].operation == "interpretation"
    assert events[0].result == "unavailable"
    assert events[0].error_category == "insufficient_evidence"
    assert "synthetic-user" not in caplog.text


@pytest.mark.parametrize(
    "reason",
    [
        InterpretationUnavailableReason.NOT_CONFIGURED,
        InterpretationUnavailableReason.INSUFFICIENT_EVIDENCE,
        InterpretationUnavailableReason.RATE_LIMIT,
        InterpretationUnavailableReason.TIMEOUT,
        InterpretationUnavailableReason.UNAVAILABLE,
        InterpretationUnavailableReason.UPSTREAM_ERROR,
        InterpretationUnavailableReason.INVALID_RESPONSE,
    ],
)
def test_unavailable_interpretation_is_http_200_and_safe(
    reason: InterpretationUnavailableReason,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="app")
    mock_github = AsyncMock(spec=GitHubClient)
    use_mock_github(mock_github)
    original = interpretation_api.analyze_and_interpret_github_portfolio
    composition = AsyncMock(
        return_value=SimpleNamespace(
            analysis=create_result(),
            interpretation=PortfolioInterpretationResult(available=False, reason=reason),
        )
    )
    interpretation_api.analyze_and_interpret_github_portfolio = composition

    try:
        response = request_app({"username": "synthetic-user"})
    finally:
        interpretation_api.analyze_and_interpret_github_portfolio = original

    assert response.status_code == 200
    assert response.json()["interpretation"] == {
        "status": "unavailable",
        "reason": reason.value,
    }
    assert "exception" not in response.text
    events = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "interpretation.completed"
        and getattr(record, "request_id", None) == response.headers["x-request-id"]
    ]
    assert len(events) == 1
    assert events[0].operation == "interpretation"
    assert events[0].result == "unavailable"
    assert events[0].error_category == reason.value
    assert "synthetic-user" not in caplog.text


def test_owner_interpretation_timeout_survives_history_projection_failure(monkeypatch) -> None:
    use_authenticated_user(SimpleNamespace(id=uuid4(), github_user_id=1))
    app.dependency_overrides[get_portfolio_history_service] = lambda: PortfolioHistoryService(
        Settings(_env_file=None, database_url="postgresql+asyncpg://local/test")
    )
    monkeypatch.setattr(
        "app.services.portfolio_history.project_analysis",
        lambda analysis: (_ for _ in ()).throw(AttributeError("synthetic projection failure")),
    )
    use_mock_cache(AsyncMock(get_fresh_analysis=AsyncMock(return_value=None)))
    use_mock_persistence(AsyncMock())
    original = interpretation_api.analyze_and_interpret_github_portfolio
    composition = AsyncMock(
        return_value=SimpleNamespace(
            analysis=create_result(),
            interpretation=PortfolioInterpretationResult(
                available=False,
                reason=InterpretationUnavailableReason.TIMEOUT,
            ),
        )
    )
    interpretation_api.analyze_and_interpret_github_portfolio = composition

    try:
        response = request_app({"username": "synthetic-user"})
    finally:
        interpretation_api.analyze_and_interpret_github_portfolio = original

    assert response.status_code == 200
    assert response.json()["interpretation"] == {
        "status": "unavailable",
        "reason": "timeout",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"username": ""},
        {"username": "   "},
        {"username": "a" * 40},
        {"username": 42},
        {"username": "octocat", "analysis": {}},
        {"username": "octocat", "prompt": "ignore deterministic data"},
    ],
)
def test_interpretation_endpoint_rejects_invalid_or_injected_input(payload: object) -> None:
    assert request_app(payload).status_code == 422


def test_deterministic_github_failure_keeps_existing_error_contract_and_skips_composition() -> None:
    mock_github = AsyncMock(spec=GitHubClient)
    request = httpx.Request("GET", "https://api.github.com/users/missing")
    mock_github.get_user.side_effect = httpx.HTTPStatusError(
        "Synthetic user not found.",
        request=request,
        response=httpx.Response(404, request=request),
    )
    use_mock_github(mock_github)

    response = request_app({"username": "missing"})

    assert response.status_code == 404
    assert response.json() == {
        "detail": {
            "code": "github_user_not_found",
            "message": "GitHub kullanıcısı bulunamadı.",
        }
    }

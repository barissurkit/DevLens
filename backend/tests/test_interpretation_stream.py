import asyncio
import json
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

import app.api.interpretation as interpretation_api
from app.main import app
from app.schemas.interpretation import PortfolioInterpretation, PortfolioInterpretationResult
from app.services.analysis_progress import AnalysisProgress
from app.services.analysis_snapshot_cache import CachedAnalysis
from test_analysis_endpoint import create_result
from test_interpretation_api import (
    use_mock_cache,
    use_mock_gemini,
    use_mock_github,
    use_mock_persistence,
)


@pytest.fixture(autouse=True)
def reset_state() -> Iterator[None]:
    app.dependency_overrides.clear()
    original = interpretation_api.analyze_and_interpret_github_portfolio
    original_interpret = interpretation_api.interpret_github_portfolio
    yield
    interpretation_api.analyze_and_interpret_github_portfolio = original
    interpretation_api.interpret_github_portfolio = original_interpret
    app.dependency_overrides.clear()


def available_interpretation() -> PortfolioInterpretationResult:
    return PortfolioInterpretationResult(
        available=True,
        interpretation=PortfolioInterpretation(summary="Grounded."),
    )


def post(path: str, payload: object) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


def events_of(response: httpx.Response) -> list[dict]:
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def setup_common(*, cache: AsyncMock | None = None) -> AsyncMock:
    use_mock_github(AsyncMock())
    use_mock_gemini(SimpleNamespace(interpret=AsyncMock()))
    persistence = AsyncMock()
    use_mock_persistence(persistence)
    fresh_cache = cache or AsyncMock()
    if cache is None:
        fresh_cache.get_fresh_analysis.return_value = None
    use_mock_cache(fresh_cache)
    return persistence


def test_stream_emits_ordered_progress_then_the_final_result() -> None:
    setup_common()

    async def composition(*, username, github_client, gemini_client, on_progress):
        on_progress(AnalysisProgress(stage="profile"))
        on_progress(AnalysisProgress(stage="repositories", completed=0, total=2))
        on_progress(AnalysisProgress(stage="repositories", completed=1, total=2))
        on_progress(AnalysisProgress(stage="repositories", completed=2, total=2))
        on_progress(AnalysisProgress(stage="interpretation"))
        return SimpleNamespace(analysis=create_result(), interpretation=available_interpretation())

    interpretation_api.analyze_and_interpret_github_portfolio = composition

    response = post("/api/v1/interpretation/stream", {"username": "synthetic-user"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert response.headers["cache-control"] == "no-cache, no-transform"
    events = events_of(response)
    assert [event["event"] for event in events] == ["progress"] * 5 + ["result"]
    assert [(e["stage"], e["completed"], e["total"]) for e in events[:5]] == [
        ("profile", 0, 0),
        ("repositories", 0, 2),
        ("repositories", 1, 2),
        ("repositories", 2, 2),
        ("interpretation", 0, 0),
    ]
    result = events[-1]["data"]
    assert result["interpretation"]["status"] == "available"
    assert result["cached"] is False
    assert result["analysis_generated_at"] is not None
    assert result["viewer_context"] == {"is_owner": False, "mode": "explore"}


def test_stream_reports_operational_failures_as_an_error_event() -> None:
    setup_common()
    request = httpx.Request("GET", "https://api.github.com/users/missing")
    failure = httpx.HTTPStatusError(
        "not found", request=request, response=httpx.Response(404, request=request)
    )
    interpretation_api.analyze_and_interpret_github_portfolio = AsyncMock(side_effect=failure)

    response = post("/api/v1/interpretation/stream", {"username": "missing"})

    assert response.status_code == 200
    events = events_of(response)
    assert events[-1]["event"] == "error"
    assert events[-1]["status"] == 404
    assert events[-1]["detail"]["code"] == "github_user_not_found"
    assert all(event["event"] != "result" for event in events)


def test_stream_hides_unexpected_errors_behind_a_generic_message() -> None:
    setup_common()
    interpretation_api.analyze_and_interpret_github_portfolio = AsyncMock(
        side_effect=RuntimeError("secret internal detail")
    )

    response = post("/api/v1/interpretation/stream", {"username": "synthetic-user"})

    events = events_of(response)
    assert events[-1] == {
        "event": "error",
        "status": 500,
        "detail": {"code": "internal_error", "message": "Analiz tamamlanamadı."},
    }
    assert "secret internal detail" not in response.text


def test_stream_rejects_invalid_requests_before_streaming() -> None:
    setup_common()

    response = post("/api/v1/interpretation/stream", {"username": ""})

    assert response.status_code == 422


def test_cached_analysis_is_flagged_and_reports_its_generation_time() -> None:
    generated_at = datetime.now(timezone.utc) - timedelta(minutes=4)
    cache = AsyncMock()
    cache.get_fresh_analysis.return_value = CachedAnalysis(
        analysis=create_result(), analysis_generated_at=generated_at
    )
    setup_common(cache=cache)
    interpretation_api.analyze_and_interpret_github_portfolio = AsyncMock(
        side_effect=AssertionError("cache hit must skip the deterministic pipeline")
    )
    interpretation_api.interpret_github_portfolio = AsyncMock(return_value=available_interpretation())

    response = post("/api/v1/interpretation", {"username": "synthetic-user"})

    assert response.status_code == 200
    body = response.json()
    assert body["cached"] is True
    assert datetime.fromisoformat(body["analysis_generated_at"]) == generated_at


def test_refresh_bypasses_the_cache_and_recomputes() -> None:
    cache = AsyncMock()
    cache.get_fresh_analysis.return_value = CachedAnalysis(
        analysis=create_result(), analysis_generated_at=datetime.now(timezone.utc)
    )
    setup_common(cache=cache)
    composition = AsyncMock(
        return_value=SimpleNamespace(analysis=create_result(), interpretation=available_interpretation())
    )
    interpretation_api.analyze_and_interpret_github_portfolio = composition

    response = post("/api/v1/interpretation", {"username": "synthetic-user", "refresh": True})

    assert response.status_code == 200
    assert response.json()["cached"] is False
    cache.get_fresh_analysis.assert_not_awaited()
    composition.assert_awaited_once()
    assert "on_progress" not in composition.await_args.kwargs


def test_refresh_must_be_a_boolean() -> None:
    setup_common()

    response = post("/api/v1/interpretation", {"username": "synthetic-user", "refresh": "yes-please"})

    assert response.status_code == 422

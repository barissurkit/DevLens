import asyncio
import json
from collections.abc import Iterator
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

import app.api.interpretation as interpretation_api
from app.main import app
from app.schemas.interpretation import (
    InterpretationUnavailableReason,
    PortfolioInterpretation,
    PortfolioInterpretationResult,
    PublicInterpretationAvailable,
    PublicInterpretationUnavailable,
)
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


STORED = PublicInterpretationAvailable(
    status="available", interpretation=PortfolioInterpretation(summary="Stored interpretation.")
)


def cached(interpretation, schema: str | None = "v1") -> AsyncMock:
    cache = AsyncMock()
    cache.get_fresh_analysis.return_value = CachedAnalysis(
        analysis=create_result(),
        analysis_generated_at=datetime.now(timezone.utc),
        interpretation=interpretation,
        interpretation_schema_version=schema,
    )
    return cache


def setup(cache: AsyncMock, *, gemini_result: PortfolioInterpretationResult | None = None):
    use_mock_github(AsyncMock())
    use_mock_gemini(SimpleNamespace(interpret=AsyncMock()))
    persistence = AsyncMock()
    use_mock_persistence(persistence)
    use_mock_cache(cache)
    interpret = AsyncMock(
        return_value=gemini_result
        or PortfolioInterpretationResult(
            available=True, interpretation=PortfolioInterpretation(summary="Fresh interpretation.")
        )
    )
    interpretation_api.interpret_github_portfolio = interpret
    composition = AsyncMock(
        return_value=SimpleNamespace(analysis=create_result(), interpretation=interpret.return_value)
    )
    interpretation_api.analyze_and_interpret_github_portfolio = composition
    return interpret, persistence, composition


def post(path: str, payload: dict) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(path, json=payload)

    return asyncio.run(send())


def test_a_stored_successful_interpretation_is_reused_without_calling_the_ai_provider() -> None:
    interpret, persistence, composition = setup(cached(STORED))

    response = post("/api/v1/interpretation", {"username": "synthetic-user"})

    assert response.status_code == 200
    body = response.json()
    assert body["cached"] is True
    assert body["interpretation"]["status"] == "available"
    assert body["interpretation"]["interpretation"]["summary"] == "Stored interpretation."
    interpret.assert_not_awaited()
    composition.assert_not_awaited()
    persistence.persist.assert_not_awaited()


def test_an_unavailable_stored_interpretation_is_retried_and_the_result_persisted() -> None:
    unavailable = PublicInterpretationUnavailable(
        status="unavailable", reason=InterpretationUnavailableReason.RATE_LIMIT
    )
    interpret, persistence, _ = setup(cached(unavailable))

    response = post("/api/v1/interpretation", {"username": "synthetic-user"})

    body = response.json()
    assert body["interpretation"]["interpretation"]["summary"] == "Fresh interpretation."
    interpret.assert_awaited_once()
    persistence.persist.assert_awaited_once()


def test_a_snapshot_without_an_interpretation_still_calls_the_provider() -> None:
    interpret, persistence, _ = setup(cached(None, schema=None))

    response = post("/api/v1/interpretation", {"username": "synthetic-user"})

    assert response.json()["interpretation"]["interpretation"]["summary"] == "Fresh interpretation."
    interpret.assert_awaited_once()
    persistence.persist.assert_awaited_once()


def test_an_interpretation_from_another_schema_version_is_not_reused() -> None:
    interpret, _, _ = setup(cached(STORED, schema="v0"))

    response = post("/api/v1/interpretation", {"username": "synthetic-user"})

    assert response.json()["interpretation"]["interpretation"]["summary"] == "Fresh interpretation."
    interpret.assert_awaited_once()


def test_refresh_recomputes_even_when_a_successful_interpretation_is_stored() -> None:
    interpret, persistence, composition = setup(cached(STORED))

    response = post("/api/v1/interpretation", {"username": "synthetic-user", "refresh": True})

    body = response.json()
    assert body["cached"] is False
    assert body["interpretation"]["interpretation"]["summary"] == "Fresh interpretation."
    composition.assert_awaited_once()
    persistence.persist.assert_awaited_once()


def test_streamed_reuse_skips_the_ai_progress_step() -> None:
    interpret, _, _ = setup(cached(STORED))

    response = post("/api/v1/interpretation/stream", {"username": "synthetic-user"})

    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert [event["event"] for event in events] == ["result"]
    assert events[0]["data"]["interpretation"]["interpretation"]["summary"] == "Stored interpretation."
    interpret.assert_not_awaited()


def test_streamed_retry_of_an_unavailable_interpretation_reports_the_ai_step() -> None:
    unavailable = PublicInterpretationUnavailable(
        status="unavailable", reason=InterpretationUnavailableReason.TIMEOUT
    )
    setup(cached(unavailable))

    response = post("/api/v1/interpretation/stream", {"username": "synthetic-user"})

    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert [event["event"] for event in events] == ["progress", "result"]
    assert events[0]["stage"] == "interpretation"

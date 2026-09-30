import asyncio
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

import app.api.interpretation as interpretation_api
from app.main import app
from app.rate_limit import CACHE_HIT_REFUND_FRACTION, POLICIES, RateLimiter
from app.schemas.interpretation import PortfolioInterpretation, PortfolioInterpretationResult
from app.services.analysis_snapshot_cache import CachedAnalysis
from test_analysis_endpoint import create_result
from test_interpretation_api import (
    use_mock_cache,
    use_mock_gemini,
    use_mock_github,
    use_mock_persistence,
)


@dataclass
class FakeClock:
    value: float = 0.0

    def __call__(self) -> float:
        return self.value


def run(coro):
    return asyncio.run(coro)


# --- limiter unit behaviour -------------------------------------------------


def test_refund_returns_tokens_but_never_beyond_capacity() -> None:
    limiter = RateLimiter(clock=FakeClock())
    assert run(limiter.acquire("portfolio_analysis", "anon:a")) is None  # 3 -> 2

    run(limiter.refund("portfolio_analysis", "anon:a", 0.75))
    assert limiter._states[("portfolio_analysis", "anon:a")].tokens == pytest.approx(2.75)

    run(limiter.refund("portfolio_analysis", "anon:a", 50))
    assert limiter._states[("portfolio_analysis", "anon:a")].tokens == POLICIES["portfolio_analysis"].capacity


def test_refund_is_a_noop_without_state_or_for_non_positive_amounts() -> None:
    limiter = RateLimiter(clock=FakeClock())
    run(limiter.refund("portfolio_analysis", "anon:unknown", 0.75))
    assert limiter.state_count == 0

    assert run(limiter.acquire("portfolio_analysis", "anon:a")) is None
    before = limiter._states[("portfolio_analysis", "anon:a")].tokens
    run(limiter.refund("portfolio_analysis", "anon:a", 0))
    run(limiter.refund("portfolio_analysis", "anon:a", -1))
    assert limiter._states[("portfolio_analysis", "anon:a")].tokens == before


def test_refunded_hits_cost_a_quarter_while_full_cost_requests_still_hit_the_limit() -> None:
    limiter = RateLimiter(clock=FakeClock())
    cache_hit_cost = 1 - CACHE_HIT_REFUND_FRACTION
    assert cache_hit_cost == pytest.approx(0.25)

    passed = 0
    while run(limiter.acquire("portfolio_analysis", "anon:a")) is None:
        run(limiter.refund("portfolio_analysis", "anon:a", POLICIES["portfolio_analysis"].cost * CACHE_HIT_REFUND_FRACTION))
        passed += 1
        assert passed < 100
    assert passed == 9  # 3 tokens, each hit nets 0.25, a request needs 1 token to start

    fresh = RateLimiter(clock=FakeClock())
    full_cost = 0
    while run(fresh.acquire("portfolio_analysis", "anon:a")) is None:
        full_cost += 1
    assert full_cost == 3  # recomputations keep the original budget


# --- endpoint behaviour -----------------------------------------------------


@pytest.fixture(autouse=True)
def reset_state() -> Iterator[None]:
    app.dependency_overrides.clear()
    original = interpretation_api.analyze_and_interpret_github_portfolio
    original_interpret = interpretation_api.interpret_github_portfolio
    yield
    interpretation_api.analyze_and_interpret_github_portfolio = original
    interpretation_api.interpret_github_portfolio = original_interpret
    app.dependency_overrides.clear()


def fresh_cache() -> AsyncMock:
    cache = AsyncMock()
    cache.get_fresh_analysis.return_value = CachedAnalysis(
        analysis=create_result(), analysis_generated_at=datetime.now(timezone.utc)
    )
    return cache


def setup(cache: AsyncMock) -> AsyncMock:
    use_mock_github(AsyncMock())
    use_mock_gemini(SimpleNamespace(interpret=AsyncMock()))
    use_mock_persistence(AsyncMock())
    use_mock_cache(cache)
    interpretation_api.interpret_github_portfolio = AsyncMock(
        return_value=PortfolioInterpretationResult(
            available=True, interpretation=PortfolioInterpretation(summary="Grounded.")
        )
    )
    composition = AsyncMock(
        return_value=SimpleNamespace(
            analysis=create_result(),
            interpretation=PortfolioInterpretationResult(
                available=True, interpretation=PortfolioInterpretation(summary="Grounded.")
            ),
        )
    )
    interpretation_api.analyze_and_interpret_github_portfolio = composition
    return composition


def statuses(path: str, payload: dict, count: int) -> list[int]:
    async def send() -> list[int]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return [(await client.post(path, json=payload)).status_code for _ in range(count)]

    return asyncio.run(send())


def test_cached_interpretations_allow_many_more_requests_than_recomputations() -> None:
    setup(fresh_cache())

    assert statuses("/api/v1/interpretation", {"username": "synthetic-user"}, 10) == [200] * 9 + [429]


def test_recomputing_keeps_the_original_three_request_budget() -> None:
    cache = AsyncMock()
    cache.get_fresh_analysis.return_value = None
    composition = setup(cache)

    assert statuses("/api/v1/interpretation", {"username": "synthetic-user"}, 4) == [200, 200, 200, 429]
    assert composition.await_count == 3


def test_refresh_pays_full_price_even_when_a_snapshot_exists() -> None:
    cache = fresh_cache()
    setup(cache)

    assert statuses("/api/v1/interpretation", {"username": "synthetic-user", "refresh": True}, 4) == [200, 200, 200, 429]
    cache.get_fresh_analysis.assert_not_awaited()


def test_streamed_cache_hits_use_the_same_cheaper_budget() -> None:
    setup(fresh_cache())

    assert statuses("/api/v1/interpretation/stream", {"username": "synthetic-user"}, 10) == [200] * 9 + [429]


def test_analysis_endpoint_cache_hits_are_cheaper_too() -> None:
    cache = fresh_cache()
    use_mock_cache(cache)
    use_mock_persistence(AsyncMock())

    assert statuses("/api/v1/analysis", {"username": "synthetic-user"}, 10) == [200] * 9 + [429]

import asyncio
from types import SimpleNamespace

import pytest

from app.clients.gemini import (
    GeminiInvalidResponseError,
    GeminiNotConfiguredError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GeminiUnavailableError,
    GeminiUpstreamError,
)
from app.schemas.interpretation import (
    InterpretationExplanation,
    InterpretationUnavailableReason,
    PortfolioInterpretation,
)
from app.services.portfolio_interpretation import interpret_github_portfolio


def analysis(successful_repository_count: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        user=SimpleNamespace(username="octocat", public_repos=successful_repository_count),
        aggregation=SimpleNamespace(
            selected_repository_count=successful_repository_count,
            successful_repository_count=successful_repository_count,
            failed_repository_count=0,
            has_failures=False,
            partial_evidence_repository_count=0,
        ),
        score=SimpleNamespace(
            is_available=successful_repository_count > 1,
            overall_score=0 if successful_repository_count > 1 else None,
            scored_repository_count=successful_repository_count,
            dimensions=[],
            is_partial=False,
            limitations=[],
        ),
        intelligence=SimpleNamespace(
            strength_signals=[],
            improvement_signals=[],
            recurring_technologies=[],
            dominant_areas=[],
            limitations=[],
        ),
        repository_analysis=SimpleNamespace(repositories=[]),
    )


class FakeClient:
    def __init__(self, result: PortfolioInterpretation | BaseException) -> None:
        self.result = result
        self.calls = []

    async def interpret(self, context: object) -> PortfolioInterpretation:
        self.calls.append(context)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def run(result: PortfolioInterpretation | BaseException, count: int = 1):
    client = FakeClient(result)
    service_result = asyncio.run(
        interpret_github_portfolio(analysis=analysis(count), client=client)  # type: ignore[arg-type]
    )
    return service_result, client


def test_success_forwards_context_and_calls_client_once() -> None:
    interpretation = PortfolioInterpretation(summary="Grounded.")
    result, client = run(interpretation)

    assert result.available is True
    assert result.interpretation == interpretation
    assert result.reason is None
    assert len(client.calls) == 1
    assert client.calls[0].successful_repository_count == 1


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (GeminiNotConfiguredError(), InterpretationUnavailableReason.NOT_CONFIGURED),
        (GeminiTimeoutError(), InterpretationUnavailableReason.TIMEOUT),
        (GeminiRateLimitError(), InterpretationUnavailableReason.RATE_LIMIT),
        (GeminiUnavailableError(), InterpretationUnavailableReason.UNAVAILABLE),
        (GeminiUpstreamError(), InterpretationUnavailableReason.UPSTREAM_ERROR),
        (GeminiInvalidResponseError(), InterpretationUnavailableReason.INVALID_RESPONSE),
    ],
)
def test_expected_gemini_failures_are_safe_unavailable_results(
    error: Exception, reason: InterpretationUnavailableReason
) -> None:
    result, client = run(error)

    assert result.available is False
    assert result.interpretation is None
    assert result.reason == reason
    assert len(client.calls) == 1


def test_zero_successful_repositories_skip_gemini() -> None:
    result, client = run(PortfolioInterpretation(summary="unused"), count=0)

    assert result.available is False
    assert result.reason == InterpretationUnavailableReason.INSUFFICIENT_EVIDENCE
    assert client.calls == []


def test_unexpected_errors_propagate() -> None:
    with pytest.raises(RuntimeError, match="bug"):
        run(RuntimeError("programmer bug"))


def test_cancellation_propagates() -> None:
    with pytest.raises(asyncio.CancelledError):
        run(asyncio.CancelledError())

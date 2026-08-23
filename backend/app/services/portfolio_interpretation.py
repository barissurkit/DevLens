from typing import Protocol

from app.clients.gemini import (
    GeminiInvalidResponseError,
    GeminiNotConfiguredError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GeminiUnavailableError,
    GeminiUpstreamError,
    validate_interpretation_references,
)
from app.schemas.analysis import GitHubPortfolioAnalysis
from app.schemas.interpretation import (
    InterpretationUnavailableReason,
    PortfolioInterpretation,
    PortfolioInterpretationContext,
    PortfolioInterpretationResult,
)
from app.services.portfolio_interpretation_context import (
    build_portfolio_interpretation_context,
)


class PortfolioInterpreter(Protocol):
    async def interpret(
        self, context: PortfolioInterpretationContext
    ) -> PortfolioInterpretation: ...


def _unavailable(reason: InterpretationUnavailableReason) -> PortfolioInterpretationResult:
    return PortfolioInterpretationResult(available=False, reason=reason)


async def interpret_github_portfolio(
    *,
    analysis: GitHubPortfolioAnalysis,
    client: PortfolioInterpreter | None,
) -> PortfolioInterpretationResult:
    """Interpret an already-computed deterministic portfolio analysis.

    This service deliberately owns orchestration only. It does not fetch GitHub data,
    recompute analysis, or turn unavailable AI into a fake natural-language fallback.
    """

    context = build_portfolio_interpretation_context(analysis)
    if context.successful_repository_count == 0:
        return _unavailable(InterpretationUnavailableReason.INSUFFICIENT_EVIDENCE)
    if client is None:
        return _unavailable(InterpretationUnavailableReason.NOT_CONFIGURED)

    try:
        interpretation = await client.interpret(context)
    except GeminiNotConfiguredError:
        return _unavailable(InterpretationUnavailableReason.NOT_CONFIGURED)
    except GeminiTimeoutError:
        return _unavailable(InterpretationUnavailableReason.TIMEOUT)
    except GeminiRateLimitError:
        return _unavailable(InterpretationUnavailableReason.RATE_LIMIT)
    except GeminiUnavailableError:
        return _unavailable(InterpretationUnavailableReason.UNAVAILABLE)
    except GeminiUpstreamError:
        return _unavailable(InterpretationUnavailableReason.UPSTREAM_ERROR)
    except GeminiInvalidResponseError:
        return _unavailable(InterpretationUnavailableReason.INVALID_RESPONSE)

    try:
        validate_interpretation_references(interpretation, context)
    except GeminiInvalidResponseError:
        return _unavailable(InterpretationUnavailableReason.INVALID_RESPONSE)

    return PortfolioInterpretationResult(available=True, interpretation=interpretation)

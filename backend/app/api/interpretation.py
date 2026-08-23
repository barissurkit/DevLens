import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import ValidationError

from app.api.errors import APIErrorResponse, map_github_exception
from app.api.github import (
    get_gemini_client,
    get_github_client,
    get_analysis_snapshot_cache_service,
    get_snapshot_persistence_service,
)
from app.schemas.analysis import PortfolioAnalysisRequest
from app.schemas.interpretation import (
    GitHubPortfolioInterpretationResponse,
    PortfolioInterpretationResult,
    PublicInterpretationAvailable,
    PublicInterpretationUnavailable,
    PublicPortfolioInterpretationResult,
)
from app.services.github.client import GitHubClient
from app.services.analysis_snapshot_persistence import AnalysisSnapshotPersistenceService
from app.services.analysis_snapshot_cache import AnalysisSnapshotCacheService
from app.services.portfolio_interpretation import interpret_github_portfolio
from app.services.portfolio_interpretation import PortfolioInterpreter
from app.services.portfolio_interpretation_composition import (
    analyze_and_interpret_github_portfolio,
    PortfolioInterpretationCompositionResult,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["Interpretation"],
)


def to_public_interpretation_result(
    result: PortfolioInterpretationResult,
) -> PublicPortfolioInterpretationResult:
    """Map the internal optional-AI result to the stable public contract."""

    if result.available:
        assert result.interpretation is not None
        return PublicInterpretationAvailable(
            status="available",
            interpretation=result.interpretation,
        )

    assert result.reason is not None
    return PublicInterpretationUnavailable(status="unavailable", reason=result.reason)


@router.post(
    "/interpretation",
    response_model=GitHubPortfolioInterpretationResponse,
    summary="Analyze a GitHub portfolio with optional interpretation",
    responses={
        404: {"model": APIErrorResponse, "description": "GitHub user not found."},
        429: {"model": APIErrorResponse, "description": "GitHub rate limit reached."},
        502: {"model": APIErrorResponse, "description": "GitHub upstream error."},
        503: {
            "model": APIErrorResponse,
            "description": "GitHub service unavailable or timed out.",
        },
    },
)
async def interpret_portfolio(
    request: PortfolioAnalysisRequest,
    github_client: GitHubClient = Depends(get_github_client),
    gemini_client: PortfolioInterpreter | None = Depends(get_gemini_client),
    persistence: AnalysisSnapshotPersistenceService = Depends(
        get_snapshot_persistence_service
    ),
    cache: AnalysisSnapshotCacheService = Depends(get_analysis_snapshot_cache_service),
) -> GitHubPortfolioInterpretationResponse:
    cached = await cache.get_fresh_analysis(
        username=request.username,
        request_kind="interpretation",
    )
    try:
        if cached is None:
            result = await analyze_and_interpret_github_portfolio(
                username=request.username,
                github_client=github_client,
                gemini_client=gemini_client,
            )
            analysis_generated_at = datetime.now(timezone.utc)
        else:
            analysis_generated_at = cached.analysis_generated_at
            result = PortfolioInterpretationCompositionResult(
                analysis=cached.analysis,
                interpretation=await interpret_github_portfolio(
                    analysis=cached.analysis,
                    client=gemini_client,
                ),
            )
    except (
        httpx.TimeoutException,
        httpx.RequestError,
        httpx.HTTPStatusError,
        ValidationError,
    ) as exc:
        raise map_github_exception(exc) from exc

    public_interpretation = to_public_interpretation_result(result.interpretation)
    response = GitHubPortfolioInterpretationResponse(
        analysis=result.analysis,
        interpretation=public_interpretation,
    )
    await persistence.persist(
        analysis=response.analysis,
        interpretation=response.interpretation,
        analysis_generated_at=analysis_generated_at,
        request_kind="interpretation",
    )
    return response

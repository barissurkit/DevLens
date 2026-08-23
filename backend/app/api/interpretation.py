import httpx
from fastapi import APIRouter, Depends
from pydantic import ValidationError

from app.api.errors import APIErrorResponse, map_github_exception
from app.api.github import (
    get_gemini_client,
    get_github_client,
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
from app.services.portfolio_interpretation import PortfolioInterpreter
from app.services.portfolio_interpretation_composition import (
    analyze_and_interpret_github_portfolio,
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
) -> GitHubPortfolioInterpretationResponse:
    try:
        result = await analyze_and_interpret_github_portfolio(
            username=request.username,
            github_client=github_client,
            gemini_client=gemini_client,
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
        request_kind="interpretation",
    )
    return response

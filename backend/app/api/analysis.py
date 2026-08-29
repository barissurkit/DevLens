import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import ValidationError

from app.api.errors import APIErrorResponse, map_github_exception
from app.api.auth import get_optional_authenticated_user
from app.api.github import (
    get_analysis_snapshot_cache_service,
    get_github_client,
    get_snapshot_persistence_service,
)
from app.auth.ownership import derive_viewer_context
from app.db.models import User
from app.schemas.analysis import GitHubPortfolioAnalysisResponse, PortfolioAnalysisRequest
from app.services.analysis_snapshot_persistence import AnalysisSnapshotPersistenceService
from app.services.analysis_snapshot_cache import AnalysisSnapshotCacheService
from app.services.github.client import GitHubClient
from app.services.github_portfolio_analysis import (
    analyze_github_portfolio as run_github_portfolio_analysis,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["Analysis"],
)


@router.post(
    "/analysis",
    response_model=GitHubPortfolioAnalysisResponse,
    summary="Analyze a GitHub portfolio",
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
async def analyze_portfolio(
    request: PortfolioAnalysisRequest,
    client: GitHubClient = Depends(get_github_client),
    persistence: AnalysisSnapshotPersistenceService = Depends(
        get_snapshot_persistence_service
    ),
    cache: AnalysisSnapshotCacheService = Depends(get_analysis_snapshot_cache_service),
    authenticated_user: User | None = Depends(get_optional_authenticated_user),
) -> GitHubPortfolioAnalysisResponse:
    cached = await cache.get_fresh_analysis(
        username=request.username,
        request_kind="analysis",
    )
    if cached is not None:
        return GitHubPortfolioAnalysisResponse(
            **cached.analysis.model_dump(),
            viewer_context=derive_viewer_context(
                authenticated_user=authenticated_user, target_github_user=cached.analysis.user
            ),
        )

    try:
        analysis = await run_github_portfolio_analysis(
            username=request.username,
            client=client,
        )
    except (
        httpx.TimeoutException,
        httpx.RequestError,
        httpx.HTTPStatusError,
        ValidationError,
    ) as exc:
        raise map_github_exception(exc) from exc
    analysis_generated_at = datetime.now(timezone.utc)

    await persistence.persist(
        analysis=analysis,
        analysis_generated_at=analysis_generated_at,
        request_kind="analysis",
    )
    return GitHubPortfolioAnalysisResponse(
        **analysis.model_dump(),
        viewer_context=derive_viewer_context(
            authenticated_user=authenticated_user, target_github_user=analysis.user
        ),
    )

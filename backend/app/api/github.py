import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError

from app.api.errors import APIErrorResponse, map_github_exception
from app.clients.gemini import GeminiClient, GeminiNotConfiguredError
from app.schemas.github import GitHubUser
from app.services.analysis_snapshot_persistence import AnalysisSnapshotPersistenceService
from app.services.analysis_snapshot_cache import AnalysisSnapshotCacheService
from app.services.portfolio_history import PortfolioHistoryService
from app.services.github.client import GitHubClient, GitHubMalformedResponseError, GitHubRequestBudgetExceeded
from app.rate_limit import rate_limit_dependency

router = APIRouter(
    prefix="/api/v1/github",
    tags=["GitHub"],
)


async def get_github_client(request: Request) -> GitHubClient:
    return GitHubClient(request.app.state.settings)


async def get_gemini_client(request: Request) -> GeminiClient | None:
    settings = request.app.state.settings
    if not settings.gemini_api_key:
        return None
    try:
        return GeminiClient(settings)
    except GeminiNotConfiguredError:
        return None


async def get_snapshot_persistence_service(
    request: Request,
) -> AnalysisSnapshotPersistenceService:
    return AnalysisSnapshotPersistenceService(request.app.state.settings)


async def get_analysis_snapshot_cache_service(
    request: Request,
) -> AnalysisSnapshotCacheService:
    return AnalysisSnapshotCacheService(request.app.state.settings)


async def get_portfolio_history_service(request: Request) -> PortfolioHistoryService:
    return PortfolioHistoryService(request.app.state.settings)


@router.get(
    "/users/{username}",
    response_model=GitHubUser,
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
async def get_github_user(
    username: str,
    _rate_limit: None = Depends(rate_limit_dependency("github_lookup")),
    client: GitHubClient = Depends(get_github_client),
) -> GitHubUser:
    try:
        return await client.get_user(username)
    except (
        httpx.TimeoutException,
        httpx.RequestError,
        httpx.HTTPStatusError,
        ValidationError,
        GitHubMalformedResponseError,
        GitHubRequestBudgetExceeded,
    ) as exc:
        raise map_github_exception(exc) from exc

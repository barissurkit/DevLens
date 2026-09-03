import httpx
from fastapi import APIRouter, Depends
from pydantic import ValidationError

from app.api.errors import APIErrorResponse, map_github_exception
from app.clients.gemini import GeminiClient, GeminiNotConfiguredError
from app.config import get_settings
from app.schemas.github import GitHubUser
from app.services.analysis_snapshot_persistence import AnalysisSnapshotPersistenceService
from app.services.analysis_snapshot_cache import AnalysisSnapshotCacheService
from app.services.portfolio_history import PortfolioHistoryService
from app.services.github.client import GitHubClient, GitHubMalformedResponseError, GitHubRequestBudgetExceeded

router = APIRouter(
    prefix="/api/v1/github",
    tags=["GitHub"],
)


async def get_github_client() -> GitHubClient:
    return GitHubClient(get_settings())


async def get_gemini_client() -> GeminiClient | None:
    settings = get_settings()
    if not settings.gemini_api_key:
        return None
    try:
        return GeminiClient(settings)
    except GeminiNotConfiguredError:
        return None


async def get_snapshot_persistence_service() -> AnalysisSnapshotPersistenceService:
    return AnalysisSnapshotPersistenceService(get_settings())


async def get_analysis_snapshot_cache_service() -> AnalysisSnapshotCacheService:
    return AnalysisSnapshotCacheService(get_settings())


async def get_portfolio_history_service() -> PortfolioHistoryService:
    return PortfolioHistoryService(get_settings())


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

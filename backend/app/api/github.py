import httpx
from fastapi import APIRouter, Depends, Path, Request
from pydantic import ValidationError

from app.api.errors import APIErrorResponse, map_github_exception
from app.clients.gemini import GeminiClient, GeminiNotConfiguredError
from app.clients.openrouter import OpenRouterClient
from app.schemas.github import GitHubUser
from app.schemas.open_source import OpenSourceContributions
from app.services.open_source_contributions import get_open_source_contributions
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


async def get_gemini_client(request: Request) -> GeminiClient | OpenRouterClient | None:
    """The configured AI provider's client (the name is historical: it is not Gemini only), or None."""

    settings = request.app.state.settings
    if not settings.ai_configured:
        return None
    try:
        if settings.ai_provider == "openrouter":
            return OpenRouterClient(settings)
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


@router.get(
    "/users/{username}/open-source",
    response_model=OpenSourceContributions,
    summary="Merged pull requests to other people's public repositories",
    responses={
        429: {"model": APIErrorResponse, "description": "Rate limit reached."},
        502: {"model": APIErrorResponse, "description": "GitHub upstream error."},
        503: {"model": APIErrorResponse, "description": "GitHub service unavailable or timed out."},
    },
)
async def get_open_source_contributions_endpoint(
    request: Request,
    # The name goes into a search query, so only a valid GitHub login may get that far.
    username: str = Path(min_length=1, max_length=39, pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$"),
    _rate_limit: None = Depends(rate_limit_dependency("github_lookup")),
    client: GitHubClient = Depends(get_github_client),
) -> OpenSourceContributions:
    try:
        return await get_open_source_contributions(
            username,
            client,
            ttl_seconds=request.app.state.settings.analysis_cache_ttl_seconds,
        )
    except (
        httpx.TimeoutException,
        httpx.RequestError,
        httpx.HTTPStatusError,
        ValidationError,
        GitHubMalformedResponseError,
        GitHubRequestBudgetExceeded,
    ) as exc:
        raise map_github_exception(exc) from exc

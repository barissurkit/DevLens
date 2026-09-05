import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.api.action_plan import require_workspace_origin
from app.api.errors import map_ai_suggestions_exception, map_github_exception
from app.api.auth import get_required_authenticated_user
from app.api.github import get_analysis_snapshot_cache_service, get_gemini_client, get_github_client
from app.auth.ownership import is_owner
from app.db.database import get_session
from app.db.models import User
from app.schemas.ai_suggestions import (
    AISuggestionsAvailable,
    AISuggestionsUnavailable,
    AISuggestionsUnavailableReason,
)
from app.schemas.analysis import PortfolioAnalysisRequest
from app.services.ai_suggestions import build_evidence_catalog, validate_suggestions
from app.services.github.client import GitHubClient
from app.services.github_portfolio_analysis import analyze_github_portfolio
from app.clients.gemini import (
    GeminiClient,
    GeminiInvalidResponseError, GeminiNotConfiguredError, GeminiRateLimitError,
    GeminiTimeoutError, GeminiUnavailableError, GeminiUpstreamError,
)
from app.rate_limit import enforce_rate_limit
from app.services.portfolio_interpretation_context import build_portfolio_interpretation_context

router = APIRouter(prefix="/api/v1/workspace", tags=["AI Suggestions"])


async def require_ai_user(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> User:
    return await get_required_authenticated_user(request, response, session)


async def _limit_ai_suggestions(
    request: Request,
    user: User = Depends(require_ai_user),
) -> None:
    await enforce_rate_limit(request, "ai_suggestions", user)


@router.post("/ai-suggestions", response_model=AISuggestionsAvailable | AISuggestionsUnavailable)
async def generate_ai_suggestions(
    payload: PortfolioAnalysisRequest,
    request: Request,
    response: Response,
    origin: str | None = Header(default=None),
    content_type: str | None = Header(default=None),
    _rate_limit: None = Depends(_limit_ai_suggestions),
    user: User = Depends(require_ai_user),
    github_client: GitHubClient = Depends(get_github_client),
    gemini_client: GeminiClient | None = Depends(get_gemini_client),
    cache=Depends(get_analysis_snapshot_cache_service),
) -> AISuggestionsAvailable | AISuggestionsUnavailable:
    require_workspace_origin(request, origin, content_type)
    cached = await cache.get_fresh_analysis(username=payload.username, request_kind="ai_suggestions")
    try:
        analysis = cached.analysis if cached is not None else await analyze_github_portfolio(username=payload.username, client=github_client)
        if not is_owner(authenticated_user=user, target_github_user=analysis.user):
            raise HTTPException(status_code=403, detail="Workspace ownership required.")
        if gemini_client is None:
            raise map_ai_suggestions_exception(GeminiNotConfiguredError())
        context = build_portfolio_interpretation_context(analysis)
        catalog = build_evidence_catalog(analysis, context)
        if not catalog:
            return AISuggestionsUnavailable(reason=AISuggestionsUnavailableReason.INSUFFICIENT_EVIDENCE)
        suggestions = await gemini_client.suggest_actions(context, catalog)
        return AISuggestionsAvailable(suggestions=validate_suggestions(suggestions, catalog).suggestions)
    except HTTPException:
        raise
    except (GeminiNotConfiguredError, GeminiTimeoutError, GeminiRateLimitError, GeminiUnavailableError, GeminiUpstreamError, GeminiInvalidResponseError) as exc:
        raise map_ai_suggestions_exception(exc) from exc
    except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError, ValidationError) as exc:
        raise map_github_exception(exc) from exc

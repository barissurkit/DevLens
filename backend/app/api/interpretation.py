import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

import httpx
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.api.errors import APIErrorResponse, map_github_exception
from app.api.auth import get_optional_authenticated_user
from app.api.github import (
    get_gemini_client,
    get_github_client,
    get_analysis_snapshot_cache_service,
    get_snapshot_persistence_service,
    get_portfolio_history_service,
)
from app.schemas.analysis import PortfolioAnalysisRequest
from app.auth.ownership import derive_viewer_context
from app.db.models import User
from app.schemas.interpretation import (
    GitHubPortfolioInterpretationResponse,
    InterpretationUnavailableReason,
    PortfolioInterpretationResult,
    PublicInterpretationAvailable,
    PublicInterpretationUnavailable,
    PublicPortfolioInterpretationResult,
)
from app.services.github.client import GitHubClient
from app.services.github.client import (
    GitHubMalformedResponseError,
    GitHubRepositoryPaginationLimitExceeded,
    GitHubRequestBudgetExceeded,
)
from app.services.analysis_snapshot_persistence import AnalysisSnapshotPersistenceService
from app.services.analysis_snapshot_cache import AnalysisSnapshotCacheService, CachedAnalysis
from app.services.portfolio_interpretation import interpret_github_portfolio
from app.services.portfolio_interpretation import PortfolioInterpreter
from app.services.portfolio_interpretation_composition import (
    analyze_and_interpret_github_portfolio,
    PortfolioInterpretationCompositionResult,
)
from app.db.constants import INTERPRETATION_SNAPSHOT_SCHEMA_VERSION
from app.observability import emit_event
from app.services.analysis_progress import AnalysisProgress, ProgressCallback, report_progress
from app.services.portfolio_history import PortfolioHistoryService
from app.services.guided_improvement import build_guided_improvements
from app.rate_limit import enforce_rate_limit, refund_rate_limit

router = APIRouter(
    prefix="/api/v1",
    tags=["Interpretation"],
)

logger = logging.getLogger(__name__)


async def _limit_interpretation(request: Request, authenticated_user: User | None = Depends(get_optional_authenticated_user)) -> None:
    await enforce_rate_limit(request, "portfolio_analysis", authenticated_user)


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


_INTERPRETATION_ERROR_RESPONSES = {
    404: {"model": APIErrorResponse, "description": "GitHub user not found."},
    429: {"model": APIErrorResponse, "description": "GitHub rate limit reached."},
    502: {"model": APIErrorResponse, "description": "GitHub upstream error."},
    503: {
        "model": APIErrorResponse,
        "description": "GitHub service unavailable or timed out.",
    },
}


# Provider-side failures that usually clear up on their own. Right after one, asking the provider again
# only adds load while it is still rate limited or down, so the stored failure is served for a short while.
_TRANSIENT_FAILURES = frozenset(
    {
        InterpretationUnavailableReason.RATE_LIMIT,
        InterpretationUnavailableReason.TIMEOUT,
        InterpretationUnavailableReason.UNAVAILABLE,
        InterpretationUnavailableReason.UPSTREAM_ERROR,
        InterpretationUnavailableReason.INVALID_RESPONSE,
    }
)
INTERPRETATION_RETRY_COOLDOWN = timedelta(seconds=60)


def _reusable_interpretation(
    cached: CachedAnalysis | None,
    *,
    retry_requested: bool = False,
    now: datetime | None = None,
) -> PortfolioInterpretationResult | None:
    """A stored interpretation of the cached analysis that can be served without calling the AI provider.

    A successful interpretation of the current interpretation schema is always reused. A transient
    failure is reused for a short cooldown so a struggling provider is not hammered, unless the caller
    explicitly asked to retry. Any other stored result is recomputed.
    """

    if cached is None or cached.interpretation_schema_version != INTERPRETATION_SNAPSHOT_SCHEMA_VERSION:
        return None
    stored = cached.interpretation
    if isinstance(stored, PublicInterpretationAvailable):
        return PortfolioInterpretationResult(available=True, interpretation=stored.interpretation)
    if (
        isinstance(stored, PublicInterpretationUnavailable)
        and stored.reason in _TRANSIENT_FAILURES
        and not retry_requested
        and cached.snapshot_created_at is not None
        and (now or datetime.now(timezone.utc)) - cached.snapshot_created_at < INTERPRETATION_RETRY_COOLDOWN
    ):
        return PortfolioInterpretationResult(available=False, reason=stored.reason)
    return None


async def _resolve_interpretation_response(
    *,
    request: PortfolioAnalysisRequest,
    github_client: GitHubClient,
    gemini_client: PortfolioInterpreter | None,
    persistence: AnalysisSnapshotPersistenceService,
    cache: AnalysisSnapshotCacheService,
    authenticated_user: User | None,
    history: PortfolioHistoryService,
    on_progress: ProgressCallback | None = None,
    on_cache_hit: Callable[[], Awaitable[None]] | None = None,
) -> GitHubPortfolioInterpretationResponse:
    cached = (
        None
        if request.refresh
        else await cache.get_fresh_analysis(
            username=request.username,
            request_kind="interpretation",
        )
    )
    if cached is not None and on_cache_hit is not None:
        await on_cache_hit()
    reused_interpretation = _reusable_interpretation(cached, retry_requested=request.retry_interpretation)
    try:
        if cached is None:
            # Only pass the callback when streaming so the plain endpoint keeps its exact call shape.
            progress_kwargs = {"on_progress": on_progress} if on_progress is not None else {}
            result = await analyze_and_interpret_github_portfolio(
                username=request.username,
                github_client=github_client,
                gemini_client=gemini_client,
                **progress_kwargs,
            )
            analysis_generated_at = datetime.now(timezone.utc)
        else:
            analysis_generated_at = cached.analysis_generated_at
            if reused_interpretation is None:
                if gemini_client is not None:
                    report_progress(on_progress, "interpretation")
                interpretation_result = await interpret_github_portfolio(
                    analysis=cached.analysis,
                    client=gemini_client,
                )
            else:
                interpretation_result = reused_interpretation
            result = PortfolioInterpretationCompositionResult(
                analysis=cached.analysis,
                interpretation=interpretation_result,
            )
    except (
        httpx.TimeoutException,
        httpx.RequestError,
        httpx.HTTPStatusError,
        ValidationError,
        GitHubMalformedResponseError,
        GitHubRepositoryPaginationLimitExceeded,
        GitHubRequestBudgetExceeded,
    ) as exc:
        raise map_github_exception(exc) from exc

    public_interpretation = to_public_interpretation_result(result.interpretation)
    outcome_fields: dict[str, str] = {
        "operation": "interpretation",
        "result": public_interpretation.status,
    }
    if isinstance(public_interpretation, PublicInterpretationUnavailable):
        outcome_fields["error_category"] = public_interpretation.reason.value
    emit_event(logger, "interpretation.completed", **outcome_fields)
    viewer_context = derive_viewer_context(
        authenticated_user=authenticated_user, target_github_user=result.analysis.user
    )
    response = GitHubPortfolioInterpretationResponse(
        analysis=result.analysis,
        interpretation=public_interpretation,
        viewer_context=viewer_context,
        guided_improvements=build_guided_improvements(result.analysis, viewer_context),
        analysis_generated_at=analysis_generated_at,
        cached=cached is not None,
    )
    if reused_interpretation is None:
        # Nothing new to store when an identical successful interpretation is already persisted.
        await persistence.persist(
            analysis=response.analysis,
            interpretation=response.interpretation,
            analysis_generated_at=analysis_generated_at,
            request_kind="interpretation",
        )
    if authenticated_user is not None and response.viewer_context.is_owner:
        await history.capture(user=authenticated_user, analysis=response.analysis)
    return response


@router.post(
    "/interpretation",
    response_model=GitHubPortfolioInterpretationResponse,
    summary="Analyze a GitHub portfolio with optional interpretation",
    responses=_INTERPRETATION_ERROR_RESPONSES,
)
async def interpret_portfolio(
    request: PortfolioAnalysisRequest,
    http_request: Request,
    _rate_limit: None = Depends(_limit_interpretation),
    github_client: GitHubClient = Depends(get_github_client),
    gemini_client: PortfolioInterpreter | None = Depends(get_gemini_client),
    persistence: AnalysisSnapshotPersistenceService = Depends(
        get_snapshot_persistence_service
    ),
    cache: AnalysisSnapshotCacheService = Depends(get_analysis_snapshot_cache_service),
    authenticated_user: User | None = Depends(get_optional_authenticated_user),
    history: PortfolioHistoryService = Depends(get_portfolio_history_service),
) -> GitHubPortfolioInterpretationResponse:
    return await _resolve_interpretation_response(
        request=request,
        github_client=github_client,
        gemini_client=gemini_client,
        persistence=persistence,
        cache=cache,
        authenticated_user=authenticated_user,
        history=history,
        on_cache_hit=lambda: refund_rate_limit(http_request, "portfolio_analysis", authenticated_user),
    )


def _ndjson(event: dict[str, object]) -> bytes:
    return (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")


@router.post(
    "/interpretation/stream",
    summary="Analyze a GitHub portfolio and stream progress as NDJSON",
    description=(
        "Same analysis as `/interpretation`, delivered as newline-delimited JSON. "
        "Each line is one event: `progress` (stage, completed, total), then either "
        "`result` (the interpretation response) or `error` (status and detail)."
    ),
    response_class=StreamingResponse,
    responses=_INTERPRETATION_ERROR_RESPONSES,
)
async def stream_interpretation(
    request: PortfolioAnalysisRequest,
    http_request: Request,
    _rate_limit: None = Depends(_limit_interpretation),
    github_client: GitHubClient = Depends(get_github_client),
    gemini_client: PortfolioInterpreter | None = Depends(get_gemini_client),
    persistence: AnalysisSnapshotPersistenceService = Depends(
        get_snapshot_persistence_service
    ),
    cache: AnalysisSnapshotCacheService = Depends(get_analysis_snapshot_cache_service),
    authenticated_user: User | None = Depends(get_optional_authenticated_user),
    history: PortfolioHistoryService = Depends(get_portfolio_history_service),
) -> StreamingResponse:
    queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()

    def on_progress(progress: AnalysisProgress) -> None:
        queue.put_nowait(
            {
                "event": "progress",
                "stage": progress.stage,
                "completed": progress.completed,
                "total": progress.total,
            }
        )

    async def run() -> None:
        try:
            response = await _resolve_interpretation_response(
                request=request,
                github_client=github_client,
                gemini_client=gemini_client,
                persistence=persistence,
                cache=cache,
                authenticated_user=authenticated_user,
                history=history,
                on_progress=on_progress,
                on_cache_hit=lambda: refund_rate_limit(http_request, "portfolio_analysis", authenticated_user),
            )
            queue.put_nowait({"event": "result", "data": response.model_dump(mode="json")})
        except HTTPException as exc:
            queue.put_nowait({"event": "error", "status": exc.status_code, "detail": exc.detail})
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("interpretation.stream.failed")
            queue.put_nowait(
                {
                    "event": "error",
                    "status": 500,
                    "detail": {"code": "internal_error", "message": "Analiz tamamlanamadı."},
                }
            )
        finally:
            queue.put_nowait(None)

    task = asyncio.create_task(run())

    async def events():
        try:
            while (item := await queue.get()) is not None:
                yield _ndjson(item)
        finally:
            # Stop the analysis when the client disconnects before it finished.
            task.cancel()

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )

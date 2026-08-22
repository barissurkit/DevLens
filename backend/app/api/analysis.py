import httpx
from fastapi import APIRouter, Depends
from pydantic import ValidationError

from app.api.errors import APIErrorResponse, map_github_exception
from app.api.github import get_github_client
from app.schemas.analysis import GitHubPortfolioAnalysis, PortfolioAnalysisRequest
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
    response_model=GitHubPortfolioAnalysis,
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
) -> GitHubPortfolioAnalysis:
    try:
        return await run_github_portfolio_analysis(
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

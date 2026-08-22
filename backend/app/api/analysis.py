import httpx
from fastapi import APIRouter, Depends
from pydantic import ValidationError

from app.api.errors import map_github_exception
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

from pydantic import BaseModel

from app.schemas.analysis import GitHubPortfolioAnalysis
from app.schemas.interpretation import PortfolioInterpretationResult
from app.services.github.client import GitHubClient
from app.services.github_portfolio_analysis import analyze_github_portfolio
from app.services.portfolio_interpretation import (
    PortfolioInterpreter,
    interpret_github_portfolio,
)


class PortfolioInterpretationCompositionResult(BaseModel):
    analysis: GitHubPortfolioAnalysis
    interpretation: PortfolioInterpretationResult


async def analyze_and_interpret_github_portfolio(
    *,
    username: str,
    github_client: GitHubClient,
    gemini_client: PortfolioInterpreter | None,
) -> PortfolioInterpretationCompositionResult:
    """Run deterministic analysis once, then optionally interpret that result."""

    analysis = await analyze_github_portfolio(username=username, client=github_client)
    interpretation = await interpret_github_portfolio(
        analysis=analysis,
        client=gemini_client,
    )
    return PortfolioInterpretationCompositionResult(
        analysis=analysis,
        interpretation=interpretation,
    )

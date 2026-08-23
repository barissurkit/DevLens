import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.schemas.interpretation import (
    PortfolioInterpretation,
    PortfolioInterpretationResult,
)
import app.services.portfolio_interpretation_composition as composition

from test_analysis_endpoint import create_result


def test_composition_runs_analysis_once_and_passes_its_result_to_interpretation(
    monkeypatch,
) -> None:
    analysis = create_result()
    interpretation = PortfolioInterpretationResult(
        available=True,
        interpretation=PortfolioInterpretation(summary="Grounded."),
    )
    analyze = AsyncMock(return_value=analysis)
    interpret = AsyncMock(return_value=interpretation)
    monkeypatch.setattr(composition, "analyze_github_portfolio", analyze)
    monkeypatch.setattr(composition, "interpret_github_portfolio", interpret)
    github_client = SimpleNamespace()
    gemini_client = SimpleNamespace()

    result = asyncio.run(
        composition.analyze_and_interpret_github_portfolio(
            username="octocat",
            github_client=github_client,
            gemini_client=gemini_client,
        )
    )

    analyze.assert_awaited_once_with(username="octocat", client=github_client)
    interpret.assert_awaited_once_with(analysis=analysis, client=gemini_client)
    assert result.analysis is analysis
    assert result.interpretation is interpretation


def test_composition_does_not_need_a_gemini_client_for_deterministic_analysis(
    monkeypatch,
) -> None:
    analysis = create_result()
    unavailable = PortfolioInterpretationResult(
        available=False,
        reason="not_configured",
    )
    monkeypatch.setattr(
        composition,
        "analyze_github_portfolio",
        AsyncMock(return_value=analysis),
    )
    interpret = AsyncMock(return_value=unavailable)
    monkeypatch.setattr(composition, "interpret_github_portfolio", interpret)

    result = asyncio.run(
        composition.analyze_and_interpret_github_portfolio(
            username="octocat",
            github_client=SimpleNamespace(),
            gemini_client=None,
        )
    )

    interpret.assert_awaited_once_with(analysis=analysis, client=None)
    assert result.interpretation is unavailable

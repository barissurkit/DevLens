import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.api.history import compare_history
from app.db.models import PortfolioAnalysisHistory
from app.db.repositories.portfolio_history import project_analysis
from app.schemas.analysis import PortfolioScore, PortfolioScoreDimensionResult, PortfolioScoreRuleResult
from app.services.portfolio_history import PortfolioHistoryService
from app.config import Settings


def analysis(*, score: int = 68, version: str = "v1") -> SimpleNamespace:
    return SimpleNamespace(
        user=SimpleNamespace(github_user_id=42, username="owner"),
        score=PortfolioScore(
            overall_score=score,
            is_available=True,
            scored_repository_count=4,
            version=version,
            dimensions=[PortfolioScoreDimensionResult(
                key="docs", label="Dokümantasyon", score=score,
                points_earned=34, points_possible=50,
                rules=[
                    PortfolioScoreRuleResult(key="readme", label="README", weight=10, detected_repository_count=3, analyzed_repository_count=4),
                    PortfolioScoreRuleResult(key="tests", label="Tests", weight=10, detected_repository_count=1, analyzed_repository_count=4),
                ],
            )],
            limitations=[],
            is_partial=False,
        ),
    )


def row(*, score: int, version: str = "v1", passed: list[str] | None = None, failed: list[str] | None = None) -> PortfolioAnalysisHistory:
    return PortfolioAnalysisHistory(
        id=uuid4(), user_id=uuid4(), github_user_id=42, github_username="owner",
        analysis_version=version, analysis_schema_version="v1", analysis_fingerprint="f" * 64,
        portfolio_score=score, category_scores=[{"key": "docs", "label": "Dokümantasyon", "score": score}],
        passed_checks=passed or [], failed_checks=failed or [],
    )


def test_projection_is_small_deterministic_and_excludes_ai_or_viewer_data() -> None:
    projection = project_analysis(analysis())
    assert projection.portfolio_score == 68
    assert projection.category_scores == [{"key": "docs", "label": "Dokümantasyon", "score": 68}]
    assert projection.passed_checks == ["readme"]
    assert projection.failed_checks == ["tests"]
    assert "fingerprint" not in projection.category_scores[0]


def test_projection_uses_portfolio_rule_coverage_threshold_and_stable_keys() -> None:
    value = analysis(score=68)
    value.score = value.score.model_copy(update={
        "overall_score": None,
        "dimensions": [value.score.dimensions[0].model_copy(update={
            "rules": [
                PortfolioScoreRuleResult(key="zulu", label="Z", weight=1, detected_repository_count=2, analyzed_repository_count=4),
                PortfolioScoreRuleResult(key="alpha", label="A", weight=1, detected_repository_count=1, analyzed_repository_count=4),
                PortfolioScoreRuleResult(key="bravo", label="B", weight=2, detected_repository_count=2, analyzed_repository_count=4),
            ],
        })],
    })

    projection = project_analysis(value)

    assert projection.portfolio_score is None
    assert projection.passed_checks == ["bravo", "zulu"]
    assert projection.failed_checks == ["alpha"]


def test_comparison_calculates_score_categories_and_check_deltas() -> None:
    comparison = compare_history(row(score=68, passed=["readme", "tests"]), row(score=61, passed=["readme"], failed=["tests"]))
    assert comparison.comparable is True
    assert comparison.portfolio_score == 7
    assert comparison.category_scores[0]["delta"] == 7
    assert comparison.newly_passing_checks == ["tests"]


def test_comparison_suppresses_delta_when_versions_differ() -> None:
    comparison = compare_history(row(score=68), row(score=61, version="v2"))
    assert comparison.comparable is False
    assert comparison.portfolio_score is None


def test_concurrent_unique_conflict_is_reported_as_deduplicated(monkeypatch) -> None:
    class Context:
        def __init__(self, value): self.value = value
        async def __aenter__(self): return self.value
        async def __aexit__(self, *args): return None

    first_session = SimpleNamespace(begin=lambda: Context(None))
    second_session = SimpleNamespace(scalar=AsyncMock(return_value=object()))
    sessions = iter([first_session, second_session])
    factory = lambda: Context(next(sessions))

    async def conflict(*args, **kwargs):
        raise IntegrityError("insert", {}, Exception("duplicate"))

    monkeypatch.setattr("app.services.portfolio_history.capture_history", conflict)
    service = PortfolioHistoryService(Settings(_env_file=None, database_url="postgresql+asyncpg://local/test"), lambda _: factory)
    user = SimpleNamespace(id=uuid4())
    assert asyncio.run(service.capture(user=user, analysis=analysis())) is True


def test_projection_failure_is_best_effort_and_logged(monkeypatch, caplog) -> None:
    monkeypatch.setattr("app.services.portfolio_history.project_analysis", lambda analysis: (_ for _ in ()).throw(AttributeError("bad shape")))
    service = PortfolioHistoryService(Settings(_env_file=None, database_url="postgresql+asyncpg://local/test"))

    assert asyncio.run(service.capture(user=SimpleNamespace(id=uuid4()), analysis=analysis())) is False
    assert any(
        getattr(record, "error_category", None) == "projection_error"
        for record in caplog.records
    )

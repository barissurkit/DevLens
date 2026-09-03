import pytest

from app.schemas.analysis import PortfolioScore, PortfolioScoreDimensionResult, PortfolioScoreRuleResult, ViewerContext
from app.schemas.guided_improvement import GuidedImprovementState
from app.services.guided_improvement import (
    GUIDED_IMPROVEMENT_REGISTRY,
    build_guided_improvements,
    canonical_guided_rule_keys,
)
from app.services.portfolio_scoring import is_portfolio_rule_passing

from test_analysis_endpoint import create_result


def analysis_with_rule(*, detected: int, analyzed: int, partial: bool = False):
    analysis = create_result()
    rule = PortfolioScoreRuleResult(
        key="readme_usage",
        label="README kullanımı",
        weight=9,
        detected_repository_count=detected,
        analyzed_repository_count=analyzed,
    )
    dimension = PortfolioScoreDimensionResult(
        key="documentation_consistency",
        label="Dokümantasyon Tutarlılığı",
        points_earned=0,
        points_possible=50,
        score=0,
        rules=[rule],
    )
    analysis.score = PortfolioScore(
        version="v1",
        is_available=True,
        overall_score=0,
        scored_repository_count=analyzed,
        dimensions=[dimension],
        is_partial=partial,
        limitations=[],
    )
    return analysis


def owner_context() -> ViewerContext:
    return ViewerContext(is_owner=True, mode="my_workspace")


def test_registry_matches_canonical_scoring_rules_exactly() -> None:
    assert set(GUIDED_IMPROVEMENT_REGISTRY) == canonical_guided_rule_keys()
    assert len(GUIDED_IMPROVEMENT_REGISTRY) == 12


def test_registry_entries_are_complete_and_non_empty() -> None:
    assert all(definition.title.strip() for definition in GUIDED_IMPROVEMENT_REGISTRY.values())
    assert all(definition.why.strip() for definition in GUIDED_IMPROVEMENT_REGISTRY.values())
    assert all(definition.steps and all(step.strip() for step in definition.steps) for definition in GUIDED_IMPROVEMENT_REGISTRY.values())


@pytest.mark.parametrize(
    ("detected", "analyzed", "expected_guidance"),
    [(0, 0, False), (0, 1, True), (1, 1, False), (1, 2, False), (1, 3, True), (2, 3, False)],
)
def test_projection_uses_canonical_rule_state_boundary(
    detected: int, analyzed: int, expected_guidance: bool
) -> None:
    if analyzed == 0:
        assert is_portfolio_rule_passing(detected_repository_count=detected, analyzed_repository_count=analyzed) is False
        return
    analysis = analysis_with_rule(detected=detected, analyzed=analyzed)
    improvements = build_guided_improvements(analysis, owner_context())
    assert bool(improvements) is expected_guidance
    if improvements:
        assert improvements[0].verification.current_state == GuidedImprovementState.NEEDS_IMPROVEMENT
        assert improvements[0].verification.detected_repository_count == detected
        assert improvements[0].verification.analyzed_repository_count == analyzed


def test_unavailable_or_partial_score_emits_no_guidance() -> None:
    unavailable = create_result()
    assert build_guided_improvements(unavailable, owner_context()) == []
    assert build_guided_improvements(analysis_with_rule(detected=0, analyzed=3, partial=True), owner_context()) == []


def test_explore_emits_no_guidance_even_for_owner_like_analysis() -> None:
    assert build_guided_improvements(
        analysis_with_rule(detected=0, analyzed=3),
        ViewerContext(is_owner=False, mode="explore"),
    ) == []


def test_projection_skips_unknown_scoring_rule() -> None:
    analysis = analysis_with_rule(detected=0, analyzed=3)
    analysis.score.dimensions[0].rules[0] = analysis.score.dimensions[0].rules[0].model_copy(update={"key": "future_rule"})
    assert build_guided_improvements(analysis, owner_context()) == []

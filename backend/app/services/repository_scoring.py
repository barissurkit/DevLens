from collections.abc import Callable
from dataclasses import dataclass

from app.schemas.analysis import (
    RepositoryAnalysis,
    RepositoryScore,
    ScoreDimensionResult,
    ScoreRuleResult,
)

SCORING_VERSION = "v1"
SCORING_MAX_POINTS = 100

TREE_TRUNCATION_LIMITATION = (
    "Repository tree response was truncated; structure-based signals may be incomplete."
)


@dataclass(frozen=True, slots=True)
class ScoringRuleDefinition:
    key: str
    label: str
    points_possible: int
    evaluate: Callable[[RepositoryAnalysis], bool]
    passed_evidence: str
    failed_evidence: str


@dataclass(frozen=True, slots=True)
class ScoringDimensionDefinition:
    key: str
    label: str
    rules: tuple[ScoringRuleDefinition, ...]


SCORING_DIMENSIONS: tuple[ScoringDimensionDefinition, ...] = (
    ScoringDimensionDefinition(
        key="documentation",
        label="Documentation",
        rules=(
            ScoringRuleDefinition(
                key="readme_exists",
                label="README exists",
                points_possible=8,
                evaluate=lambda analysis: analysis.readme.exists,
                passed_evidence="Root README.md content was available.",
                failed_evidence="Root README.md content was not available.",
            ),
            ScoringRuleDefinition(
                key="readme_title",
                label="Title",
                points_possible=5,
                evaluate=lambda analysis: analysis.readme.has_title,
                passed_evidence=("A level-one README heading signal was detected."),
                failed_evidence=("No level-one README heading signal was detected."),
            ),
            ScoringRuleDefinition(
                key="readme_description",
                label="Description",
                points_possible=8,
                evaluate=lambda analysis: analysis.readme.has_description,
                passed_evidence=("A meaningful README introduction signal was detected."),
                failed_evidence=("No meaningful README introduction signal was detected."),
            ),
            ScoringRuleDefinition(
                key="readme_installation",
                label="Installation",
                points_possible=9,
                evaluate=lambda analysis: analysis.readme.has_installation,
                passed_evidence=("A recognized README installation section heading was detected."),
                failed_evidence=("No recognized README installation section heading was detected."),
            ),
            ScoringRuleDefinition(
                key="readme_usage",
                label="Usage",
                points_possible=9,
                evaluate=lambda analysis: analysis.readme.has_usage,
                passed_evidence=("A recognized README usage section heading was detected."),
                failed_evidence=("No recognized README usage section heading was detected."),
            ),
            ScoringRuleDefinition(
                key="readme_technologies",
                label="Technologies",
                points_possible=6,
                evaluate=lambda analysis: analysis.readme.has_technologies,
                passed_evidence=("A recognized README technologies section heading was detected."),
                failed_evidence=("No recognized README technologies section heading was detected."),
            ),
            ScoringRuleDefinition(
                key="readme_requirements",
                label="Requirements",
                points_possible=5,
                evaluate=lambda analysis: analysis.readme.has_requirements,
                passed_evidence=("A recognized README requirements section heading was detected."),
                failed_evidence=("No recognized README requirements section heading was detected."),
            ),
        ),
    ),
    ScoringDimensionDefinition(
        key="testing_automation",
        label="Testing & Automation",
        rules=(
            ScoringRuleDefinition(
                key="tests_structure",
                label="Tests structure",
                points_possible=18,
                evaluate=lambda analysis: analysis.structure.has_tests,
                passed_evidence=("A test directory structure signal was detected."),
                failed_evidence=("No test directory structure signal was detected."),
            ),
            ScoringRuleDefinition(
                key="ci_workflow",
                label="CI workflow",
                points_possible=12,
                evaluate=lambda analysis: analysis.structure.has_ci,
                passed_evidence=("A GitHub Actions workflow file signal was detected."),
                failed_evidence=("No GitHub Actions workflow file signal was detected."),
            ),
        ),
    ),
    ScoringDimensionDefinition(
        key="repository_hygiene",
        label="Repository Hygiene",
        rules=(
            ScoringRuleDefinition(
                key="gitignore",
                label=".gitignore",
                points_possible=8,
                evaluate=lambda analysis: analysis.structure.has_gitignore,
                passed_evidence=".gitignore file signal was detected.",
                failed_evidence="No .gitignore file signal was detected.",
            ),
            ScoringRuleDefinition(
                key="license",
                label="LICENSE",
                points_possible=7,
                evaluate=lambda analysis: analysis.structure.has_license,
                passed_evidence=("A supported license filename signal was detected."),
                failed_evidence=("No supported license filename signal was detected."),
            ),
            ScoringRuleDefinition(
                key="contributing",
                label="CONTRIBUTING",
                points_possible=5,
                evaluate=lambda analysis: analysis.structure.has_contributing,
                passed_evidence=("A CONTRIBUTING.md file signal was detected."),
                failed_evidence=("No CONTRIBUTING.md file signal was detected."),
            ),
        ),
    ),
)


def normalize_score(
    *,
    points_earned: int,
    points_possible: int,
) -> int:
    if points_possible <= 0:
        raise ValueError("points_possible must be greater than zero.")

    if points_earned < 0 or points_earned > points_possible:
        raise ValueError("points_earned must be between zero and points_possible.")

    return (points_earned * SCORING_MAX_POINTS + points_possible // 2) // points_possible


def _score_rule(
    analysis: RepositoryAnalysis,
    definition: ScoringRuleDefinition,
) -> ScoreRuleResult:
    passed = definition.evaluate(analysis)

    return ScoreRuleResult(
        key=definition.key,
        label=definition.label,
        passed=passed,
        points_earned=definition.points_possible if passed else 0,
        points_possible=definition.points_possible,
        evidence=(definition.passed_evidence if passed else definition.failed_evidence),
    )


def _score_dimension(
    analysis: RepositoryAnalysis,
    definition: ScoringDimensionDefinition,
) -> ScoreDimensionResult:
    rules = [_score_rule(analysis, rule_definition) for rule_definition in definition.rules]

    points_earned = sum(rule.points_earned for rule in rules)
    points_possible = sum(rule.points_possible for rule in rules)

    return ScoreDimensionResult(
        key=definition.key,
        label=definition.label,
        points_earned=points_earned,
        points_possible=points_possible,
        score=normalize_score(
            points_earned=points_earned,
            points_possible=points_possible,
        ),
        rules=rules,
    )


def score_repository(
    analysis: RepositoryAnalysis,
) -> RepositoryScore:
    dimensions = [_score_dimension(analysis, definition) for definition in SCORING_DIMENSIONS]

    points_possible = sum(dimension.points_possible for dimension in dimensions)

    if points_possible != SCORING_MAX_POINTS:
        raise RuntimeError("V1 scoring rules must total 100 possible points.")

    overall_score = sum(dimension.points_earned for dimension in dimensions)

    limitations = [TREE_TRUNCATION_LIMITATION] if analysis.tree_truncated else []

    return RepositoryScore(
        version=SCORING_VERSION,
        overall_score=overall_score,
        dimensions=dimensions,
        is_partial=analysis.tree_truncated,
        limitations=limitations,
    )

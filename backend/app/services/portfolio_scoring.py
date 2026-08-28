from dataclasses import dataclass

from app.schemas.analysis import (
    PortfolioAggregation,
    PortfolioScore,
    PortfolioScoreDimensionResult,
    PortfolioScoreRuleResult,
)

PORTFOLIO_SCORING_VERSION = "v1"
PORTFOLIO_SCORING_MAX_POINTS = 100
MIN_REPOSITORIES_FOR_PORTFOLIO_SCORE = 2


@dataclass(frozen=True, slots=True)
class PortfolioScoringRuleDefinition:
    key: str
    label: str
    weight: int


@dataclass(frozen=True, slots=True)
class PortfolioScoringDimensionDefinition:
    key: str
    label: str
    rules: tuple[PortfolioScoringRuleDefinition, ...]


PORTFOLIO_SCORING_DIMENSIONS: tuple[
    PortfolioScoringDimensionDefinition,
    ...,
] = (
    PortfolioScoringDimensionDefinition(
        key="documentation_consistency",
        label="Dokümantasyon Tutarlılığı",
        rules=(
            PortfolioScoringRuleDefinition(
                key="readme_exists",
                label="README mevcut",
                weight=8,
            ),
            PortfolioScoringRuleDefinition(
                key="readme_title",
                label="README başlığı",
                weight=5,
            ),
            PortfolioScoringRuleDefinition(
                key="readme_description",
                label="README açıklaması",
                weight=8,
            ),
            PortfolioScoringRuleDefinition(
                key="readme_installation",
                label="README kurulumu",
                weight=9,
            ),
            PortfolioScoringRuleDefinition(
                key="readme_usage",
                label="README kullanımı",
                weight=9,
            ),
            PortfolioScoringRuleDefinition(
                key="readme_technologies",
                label="README teknolojileri",
                weight=6,
            ),
            PortfolioScoringRuleDefinition(
                key="readme_requirements",
                label="README gereksinimleri",
                weight=5,
            ),
        ),
    ),
    PortfolioScoringDimensionDefinition(
        key="testing_automation_adoption",
        label="Test ve Otomasyon Kullanımı",
        rules=(
            PortfolioScoringRuleDefinition(
                key="tests_structure",
                label="Test Yapısı",
                weight=18,
            ),
            PortfolioScoringRuleDefinition(
                key="ci_workflow",
                label="CI İş Akışı",
                weight=12,
            ),
        ),
    ),
    PortfolioScoringDimensionDefinition(
        key="repository_hygiene_consistency",
        label="Repository Hijyeni Tutarlılığı",
        rules=(
            PortfolioScoringRuleDefinition(
                key="gitignore",
                label=".gitignore",
                weight=8,
            ),
            PortfolioScoringRuleDefinition(
                key="license",
                label="LICENSE",
                weight=7,
            ),
            PortfolioScoringRuleDefinition(
                key="contributing",
                label="CONTRIBUTING",
                weight=5,
            ),
        ),
    ),
)


def round_half_up_ratio(*, numerator: int, denominator: int) -> int:
    if numerator < 0:
        raise ValueError("numerator must be non-negative.")

    if denominator <= 0:
        raise ValueError("denominator must be greater than zero.")

    return (2 * numerator + denominator) // (2 * denominator)


def _validate_aggregation_counts(
    aggregation: PortfolioAggregation,
) -> None:
    expected_selected_count = (
        aggregation.successful_repository_count
        + aggregation.failed_repository_count
    )

    if aggregation.selected_repository_count != expected_selected_count:
        raise ValueError(
            "selected_repository_count must equal successful plus failed "
            "repository counts."
        )

    if aggregation.has_failures != (
        aggregation.failed_repository_count > 0
    ):
        raise ValueError(
            "has_failures must match failed_repository_count."
        )

    if (
        aggregation.partial_evidence_repository_count
        > aggregation.successful_repository_count
    ):
        raise ValueError(
            "partial_evidence_repository_count cannot exceed "
            "successful_repository_count."
        )


def _signal_counts(aggregation: PortfolioAggregation) -> dict[str, int]:
    counts: dict[str, int] = {}

    for signal in aggregation.portfolio_signals:
        if signal.key in counts:
            raise ValueError(
                f"Duplicate portfolio signal key: {signal.key}"
            )

        counts[signal.key] = signal.detected_repository_count

        if (
            signal.detected_repository_count
            > aggregation.successful_repository_count
        ):
            raise ValueError(
                "Portfolio signal count cannot exceed successful repository "
                f"count: {signal.key}"
            )

    required_keys = [
        rule.key
        for dimension in PORTFOLIO_SCORING_DIMENSIONS
        for rule in dimension.rules
    ]
    missing_keys = [key for key in required_keys if key not in counts]

    if missing_keys:
        raise ValueError(
            "Portfolio aggregation is missing required scoring signal keys: "
            + ", ".join(missing_keys)
        )

    return counts


def _validate_policy() -> None:
    dimension_points = [
        sum(rule.weight for rule in dimension.rules)
        for dimension in PORTFOLIO_SCORING_DIMENSIONS
    ]

    if dimension_points != [50, 30, 20]:
        raise RuntimeError(
            "V1 portfolio scoring dimensions must total 50, 30, and 20 points."
        )

    if sum(dimension_points) != PORTFOLIO_SCORING_MAX_POINTS:
        raise RuntimeError(
            "V1 portfolio scoring rules must total 100 possible points."
        )


def _score_dimension(
    *,
    definition: PortfolioScoringDimensionDefinition,
    signal_counts: dict[str, int],
    repository_count: int,
) -> PortfolioScoreDimensionResult:
    rules = [
        PortfolioScoreRuleResult(
            key=rule.key,
            label=rule.label,
            weight=rule.weight,
            detected_repository_count=signal_counts[rule.key],
            analyzed_repository_count=repository_count,
        )
        for rule in definition.rules
    ]
    points_possible = sum(rule.weight for rule in definition.rules)
    weighted_numerator = sum(
        rule.weight * signal_counts[rule.key]
        for rule in definition.rules
    )
    points_earned = round_half_up_ratio(
        numerator=weighted_numerator,
        denominator=repository_count,
    )

    return PortfolioScoreDimensionResult(
        key=definition.key,
        label=definition.label,
        points_earned=points_earned,
        points_possible=points_possible,
        score=round_half_up_ratio(
            numerator=points_earned * 100,
            denominator=points_possible,
        ),
        rules=rules,
    )


def _limitations(aggregation: PortfolioAggregation) -> list[str]:
    limitations: list[str] = []

    if (
        aggregation.successful_repository_count
        < MIN_REPOSITORIES_FOR_PORTFOLIO_SCORE
    ):
        limitations.append(
            "Portföy skoru için en az iki repository'nin başarıyla analiz edilmesi gerekir."
        )

    if aggregation.failed_repository_count == 1:
        limitations.append(
            "1 seçilen repository analiz edilemedi ve portföy skorundan çıkarıldı."
        )
    elif aggregation.failed_repository_count > 1:
        limitations.append(
            f"{aggregation.failed_repository_count} seçilen repository analiz edilemedi ve portföy skorundan çıkarıldı."
        )

    if aggregation.partial_evidence_repository_count == 1:
        limitations.append(
            "1 başarıyla analiz edilen repository kısmi yapı kanıtına sahip; yapı tabanlı skor kanıtı eksik olabilir."
        )
    elif aggregation.partial_evidence_repository_count > 1:
        limitations.append(
            f"{aggregation.partial_evidence_repository_count} başarıyla analiz edilen repository kısmi yapı kanıtına sahip; yapı tabanlı skor kanıtı eksik olabilir."
        )

    return limitations


def score_portfolio(
    aggregation: PortfolioAggregation,
) -> PortfolioScore:
    """Score normalized portfolio evidence with the deterministic V1 policy."""

    _validate_aggregation_counts(aggregation)
    _validate_policy()

    repository_count = aggregation.successful_repository_count
    is_available = (
        repository_count >= MIN_REPOSITORIES_FOR_PORTFOLIO_SCORE
    )
    is_partial = (
        aggregation.failed_repository_count > 0
        or aggregation.partial_evidence_repository_count > 0
    )
    limitations = _limitations(aggregation)

    if not is_available:
        return PortfolioScore(
            version=PORTFOLIO_SCORING_VERSION,
            is_available=False,
            overall_score=None,
            scored_repository_count=repository_count,
            dimensions=[],
            is_partial=is_partial,
            limitations=limitations,
        )

    signal_counts = _signal_counts(aggregation)

    dimensions = [
        _score_dimension(
            definition=definition,
            signal_counts=signal_counts,
            repository_count=repository_count,
        )
        for definition in PORTFOLIO_SCORING_DIMENSIONS
    ]

    return PortfolioScore(
        version=PORTFOLIO_SCORING_VERSION,
        is_available=True,
        overall_score=sum(
            dimension.points_earned for dimension in dimensions
        ),
        scored_repository_count=repository_count,
        dimensions=dimensions,
        is_partial=is_partial,
        limitations=limitations,
    )

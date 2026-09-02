from dataclasses import dataclass

from app.schemas.analysis import (
    PortfolioAggregation,
    PortfolioDominantArea,
    PortfolioInsight,
    PortfolioIntelligence,
    PortfolioRecurringTechnology,
    RepositoryCategory,
)
from app.services.portfolio_scoring import is_portfolio_rule_passing

PORTFOLIO_INTELLIGENCE_VERSION = "v1"
MIN_REPOSITORIES_FOR_PATTERN = 2
MIN_REPOSITORIES_FOR_IMPROVEMENT = 3
MIN_DETECTIONS_FOR_STRENGTH = 2
MIN_REPOSITORIES_FOR_RECURRING_TECHNOLOGY = 2
MIN_REPOSITORIES_FOR_DOMINANT_AREA = 2

_SIGNAL_LABELS = {
    "readme_exists": "README içeriği",
    "readme_title": "README başlığı",
    "readme_description": "README açıklaması",
    "readme_installation": "README kurulum bölümü",
    "readme_usage": "README kullanım bölümü",
    "readme_technologies": "README teknoloji bölümü",
    "readme_requirements": "README gereksinimleri bölümü",
    "tests_structure": "test dizini yapısı",
    "ci_workflow": "GitHub Actions iş akışı",
    "gitignore": ".gitignore dosyası",
    "license": "desteklenen lisans dosyası adı",
}


def _signal_message(key: str, kind: str, detected_count: int = 0) -> str:
    label = _SIGNAL_LABELS[key]
    if kind == "strength":
        display_label = "README" if key.startswith("readme_") else label
        return f"{display_label} sinyalleri, başarıyla analiz edilen birden fazla herkese açık repository'de tespit edildi."
    if detected_count == 0:
        display_label = "README " + label.removeprefix("README ") if key.startswith("readme_") else label
        return f"Başarıyla analiz edilen herkese açık repository'lerin hiçbirinde {display_label} sinyali tespit edilmedi."
    display_label = "README " + label.removeprefix("README ") if key.startswith("readme_") else label
    return f"{display_label} sinyalleri, başarıyla analiz edilen herkese açık repository'lerin yalnızca sınırlı bir bölümünde tespit edildi."


@dataclass(frozen=True, slots=True)
class PortfolioInsightRule:
    key: str
    strength_message: str | None
    improvement_zero_message: str | None = None
    improvement_limited_message: str | None = None
    suppress_improvement_with_partial_evidence: bool = False


PORTFOLIO_INSIGHT_RULES: tuple[PortfolioInsightRule, ...] = (
    PortfolioInsightRule(
        key="readme_exists",
        strength_message=(
            "Root README content was available across multiple successfully "
            "analyzed public repositories."
        ),
        improvement_zero_message=(
            "No root README content was available across the successfully "
            "analyzed public repositories."
        ),
        improvement_limited_message=(
            "Root README content was available in only a limited portion of "
            "the successfully analyzed public repositories."
        ),
    ),
    PortfolioInsightRule(
        key="readme_title",
        strength_message=(
            "README title signals were detected across multiple successfully "
            "analyzed public repositories."
        ),
    ),
    PortfolioInsightRule(
        key="readme_description",
        strength_message=(
            "README description signals were detected across multiple "
            "successfully analyzed public repositories."
        ),
        improvement_zero_message=(
            "No meaningful README description signal was detected across the "
            "successfully analyzed public repositories."
        ),
        improvement_limited_message=(
            "Meaningful README description signals were detected in only a "
            "limited portion of the successfully analyzed public repositories."
        ),
    ),
    PortfolioInsightRule(
        key="readme_installation",
        strength_message=(
            "README installation-section signals were detected across multiple "
            "successfully analyzed public repositories."
        ),
        improvement_zero_message=(
            "No README installation-section signal was detected across the "
            "successfully analyzed public repositories."
        ),
        improvement_limited_message=(
            "README installation-section signals were detected in only a "
            "limited portion of the successfully analyzed public repositories."
        ),
    ),
    PortfolioInsightRule(
        key="readme_usage",
        strength_message=(
            "README usage-section signals were detected across multiple "
            "successfully analyzed public repositories."
        ),
        improvement_zero_message=(
            "No README usage-section signal was detected across the "
            "successfully analyzed public repositories."
        ),
        improvement_limited_message=(
            "README usage-section signals were detected in only a limited "
            "portion of the successfully analyzed public repositories."
        ),
    ),
    PortfolioInsightRule(
        key="readme_technologies",
        strength_message=(
            "README technology-section signals were detected across multiple "
            "successfully analyzed public repositories."
        ),
    ),
    PortfolioInsightRule(
        key="readme_requirements",
        strength_message=(
            "README requirements-section signals were detected across multiple "
            "successfully analyzed public repositories."
        ),
        improvement_zero_message=(
            "No README requirements-section signal was detected across the "
            "successfully analyzed public repositories."
        ),
        improvement_limited_message=(
            "README requirements-section signals were detected in only a "
            "limited portion of the successfully analyzed public repositories."
        ),
    ),
    PortfolioInsightRule(
        key="tests_structure",
        strength_message=(
            "Test-directory structure signals were detected across multiple "
            "successfully analyzed public repositories."
        ),
        improvement_zero_message=(
            "No test-directory structure signal was detected across the "
            "successfully analyzed public repositories."
        ),
        improvement_limited_message=(
            "Test-directory structure signals were detected in only a limited "
            "portion of the successfully analyzed public repositories."
        ),
        suppress_improvement_with_partial_evidence=True,
    ),
    PortfolioInsightRule(
        key="ci_workflow",
        strength_message=(
            "GitHub Actions workflow signals were detected across multiple "
            "successfully analyzed public repositories."
        ),
        improvement_zero_message=(
            "No GitHub Actions workflow signal was detected across the "
            "successfully analyzed public repositories."
        ),
        improvement_limited_message=(
            "GitHub Actions workflow signals were detected in only a limited "
            "portion of the successfully analyzed public repositories."
        ),
        suppress_improvement_with_partial_evidence=True,
    ),
    PortfolioInsightRule(
        key="gitignore",
        strength_message=(
            ".gitignore file signals were detected across multiple successfully "
            "analyzed public repositories."
        ),
    ),
    PortfolioInsightRule(
        key="license",
        strength_message=(
            "Supported license filename signals were detected across multiple "
            "successfully analyzed public repositories."
        ),
        improvement_zero_message=(
            "No supported license filename signal was detected across the "
            "successfully analyzed public repositories."
        ),
        improvement_limited_message=(
            "Supported license filename signals were detected in only a limited "
            "portion of the successfully analyzed public repositories."
        ),
        suppress_improvement_with_partial_evidence=True,
    ),
    PortfolioInsightRule(
        key="contributing",
        strength_message=None,
    ),
)


def _signal_counts(aggregation: PortfolioAggregation) -> dict[str, int]:
    counts: dict[str, int] = {}

    for signal in aggregation.portfolio_signals:
        if signal.key in counts:
            raise ValueError(
                f"Duplicate portfolio signal key: {signal.key}"
            )

        counts[signal.key] = signal.detected_repository_count

    missing_keys = [
        rule.key
        for rule in PORTFOLIO_INSIGHT_RULES
        if rule.key not in counts
    ]

    if missing_keys:
        raise ValueError(
            "Portfolio aggregation is missing required signal keys: "
            + ", ".join(missing_keys)
        )

    return counts


def _strength_signals(
    *,
    aggregation: PortfolioAggregation,
    signal_counts: dict[str, int],
) -> list[PortfolioInsight]:
    analyzed_count = aggregation.successful_repository_count

    if analyzed_count < MIN_REPOSITORIES_FOR_PATTERN:
        return []

    strengths: list[PortfolioInsight] = []

    for rule in PORTFOLIO_INSIGHT_RULES:
        detected_count = signal_counts[rule.key]

        if (
            rule.strength_message is not None
            and detected_count >= MIN_DETECTIONS_FOR_STRENGTH
            and is_portfolio_rule_passing(
                detected_repository_count=detected_count,
                analyzed_repository_count=analyzed_count,
            )
        ):
            strengths.append(
                PortfolioInsight(
                    key=rule.key,
                    message=_signal_message(rule.key, "strength"),
                    detected_repository_count=detected_count,
                    analyzed_repository_count=analyzed_count,
                )
            )

    return strengths


def _improvement_signals(
    *,
    aggregation: PortfolioAggregation,
    signal_counts: dict[str, int],
) -> list[PortfolioInsight]:
    analyzed_count = aggregation.successful_repository_count

    if analyzed_count < MIN_REPOSITORIES_FOR_IMPROVEMENT:
        return []

    improvements: list[PortfolioInsight] = []

    for rule in PORTFOLIO_INSIGHT_RULES:
        detected_count = signal_counts[rule.key]

        if (
            rule.improvement_zero_message is None
            or rule.improvement_limited_message is None
            or is_portfolio_rule_passing(
                detected_repository_count=detected_count,
                analyzed_repository_count=analyzed_count,
            )
            or (
                rule.suppress_improvement_with_partial_evidence
                and aggregation.partial_evidence_repository_count > 0
            )
        ):
            continue

        message = (
            rule.improvement_zero_message
            if detected_count == 0
            else rule.improvement_limited_message
        )
        improvements.append(
            PortfolioInsight(
                key=rule.key,
            message=_signal_message(rule.key, "improvement", detected_count),
                detected_repository_count=detected_count,
                analyzed_repository_count=analyzed_count,
            )
        )

    return improvements


def _recurring_technologies(
    aggregation: PortfolioAggregation,
) -> list[PortfolioRecurringTechnology]:
    if (
        aggregation.successful_repository_count
        < MIN_REPOSITORIES_FOR_PATTERN
    ):
        return []

    recurring = [
        PortfolioRecurringTechnology(
            technology=usage.technology,
            repository_count=usage.repository_count,
        )
        for usage in aggregation.technology_distribution
        if usage.repository_count
        >= MIN_REPOSITORIES_FOR_RECURRING_TECHNOLOGY
    ]

    return sorted(
        recurring,
        key=lambda usage: (
            usage.technology.casefold(),
            usage.technology,
        ),
    )


def _dominant_areas(
    aggregation: PortfolioAggregation,
) -> list[PortfolioDominantArea]:
    if (
        aggregation.successful_repository_count
        < MIN_REPOSITORIES_FOR_PATTERN
    ):
        return []

    category_counts = {
        usage.category: usage.repository_count
        for usage in aggregation.primary_category_distribution
        if usage.category is not RepositoryCategory.OTHER
        and usage.repository_count >= MIN_REPOSITORIES_FOR_DOMINANT_AREA
    }

    if not category_counts:
        return []

    dominant_count = max(category_counts.values())

    return [
        PortfolioDominantArea(
            category=category,
            repository_count=dominant_count,
        )
        for category in RepositoryCategory
        if category_counts.get(category) == dominant_count
    ]


def _limitations(aggregation: PortfolioAggregation) -> list[str]:
    limitations: list[str] = []

    if aggregation.failed_repository_count == 1:
        limitations.append(
            "1 seçilen repository analiz edilemedi ve portföy analizinden çıkarıldı."
        )
    elif aggregation.failed_repository_count > 1:
        limitations.append(
            f"{aggregation.failed_repository_count} seçilen repository analiz edilemedi ve portföy analizinden çıkarıldı."
        )

    if aggregation.partial_evidence_repository_count == 1:
        limitations.append(
            "1 başarıyla analiz edilen repository kısmi yapı kanıtına sahip; yokluğa dayalı yapı ve repository hijyeni içgörüleri eksik olabilir."
        )
    elif aggregation.partial_evidence_repository_count > 1:
        limitations.append(
            f"{aggregation.partial_evidence_repository_count} başarıyla analiz edilen repository kısmi yapı kanıtına sahip; yokluğa dayalı yapı ve repository hijyeni içgörüleri eksik olabilir."
        )

    if (
        aggregation.successful_repository_count
        < MIN_REPOSITORIES_FOR_PATTERN
    ):
        limitations.append(
            "Portföy düzeyindeki örüntüler için en az iki repository'nin başarıyla analiz edilmesi gerekir."
        )

    return limitations


def build_portfolio_intelligence(
    aggregation: PortfolioAggregation,
) -> PortfolioIntelligence:
    """Interpret normalized portfolio aggregation with the V1 policy."""

    if (
        aggregation.successful_repository_count
        < MIN_REPOSITORIES_FOR_PATTERN
    ):
        return PortfolioIntelligence(
            version=PORTFOLIO_INTELLIGENCE_VERSION,
            strength_signals=[],
            improvement_signals=[],
            recurring_technologies=[],
            dominant_areas=[],
            limitations=_limitations(aggregation),
        )

    signal_counts = _signal_counts(aggregation)

    return PortfolioIntelligence(
        version=PORTFOLIO_INTELLIGENCE_VERSION,
        strength_signals=_strength_signals(
            aggregation=aggregation,
            signal_counts=signal_counts,
        ),
        improvement_signals=_improvement_signals(
            aggregation=aggregation,
            signal_counts=signal_counts,
        ),
        recurring_technologies=_recurring_technologies(aggregation),
        dominant_areas=_dominant_areas(aggregation),
        limitations=_limitations(aggregation),
    )

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from app.schemas.analysis import (
    PortfolioAggregation,
    PortfolioCategoryUsage,
    PortfolioRepositoryAnalysis,
    PortfolioSignalCount,
    PortfolioTechnologyUsage,
    RepositoryAnalysis,
    RepositoryCategory,
    RepositoryScoreBucket,
)


@dataclass(frozen=True, slots=True)
class PortfolioSignalDefinition:
    key: str
    label: str
    detect: Callable[[RepositoryAnalysis], bool]


PORTFOLIO_SIGNAL_DEFINITIONS: tuple[PortfolioSignalDefinition, ...] = (
    PortfolioSignalDefinition(
        key="readme_exists",
        label="README mevcut",
        detect=lambda analysis: analysis.readme.exists,
    ),
    PortfolioSignalDefinition(
        key="readme_title",
        label="README başlığı",
        detect=lambda analysis: analysis.readme.has_title,
    ),
    PortfolioSignalDefinition(
        key="readme_description",
        label="README açıklaması",
        detect=lambda analysis: analysis.readme.has_description,
    ),
    PortfolioSignalDefinition(
        key="readme_installation",
        label="README kurulumu",
        detect=lambda analysis: analysis.readme.has_installation,
    ),
    PortfolioSignalDefinition(
        key="readme_usage",
        label="README kullanımı",
        detect=lambda analysis: analysis.readme.has_usage,
    ),
    PortfolioSignalDefinition(
        key="readme_technologies",
        label="README teknolojileri",
        detect=lambda analysis: analysis.readme.has_technologies,
    ),
    PortfolioSignalDefinition(
        key="readme_requirements",
        label="README gereksinimleri",
        detect=lambda analysis: analysis.readme.has_requirements,
    ),
    PortfolioSignalDefinition(
        key="tests_structure",
        label="Test Yapısı",
        detect=lambda analysis: analysis.structure.has_tests,
    ),
    PortfolioSignalDefinition(
        key="ci_workflow",
        label="CI İş Akışı",
        detect=lambda analysis: analysis.structure.has_ci,
    ),
    PortfolioSignalDefinition(
        key="gitignore",
        label=".gitignore",
        detect=lambda analysis: analysis.structure.has_gitignore,
    ),
    PortfolioSignalDefinition(
        key="license",
        label="LICENSE",
        detect=lambda analysis: analysis.structure.has_license,
    ),
    PortfolioSignalDefinition(
        key="contributing",
        label="CONTRIBUTING",
        detect=lambda analysis: analysis.structure.has_contributing,
    ),
)

REPOSITORY_SCORE_BUCKETS: tuple[tuple[int, int], ...] = (
    (0, 24),
    (25, 49),
    (50, 74),
    (75, 100),
)


def _technology_distribution(
    portfolio_analysis: PortfolioRepositoryAnalysis,
) -> list[PortfolioTechnologyUsage]:
    counts: Counter[str] = Counter()

    for result in portfolio_analysis.repositories:
        detected_names = {
            technology.name
            for technology in result.analysis.technologies.technologies
        }
        counts.update(detected_names)

    return [
        PortfolioTechnologyUsage(
            technology=technology,
            repository_count=counts[technology],
        )
        for technology in sorted(
            counts,
            key=lambda name: (name.casefold(), name),
        )
    ]


def _category_distribution(
    portfolio_analysis: PortfolioRepositoryAnalysis,
) -> list[PortfolioCategoryUsage]:
    counts: Counter[RepositoryCategory] = Counter()

    for result in portfolio_analysis.repositories:
        categories = {
            category_match.category
            for category_match in result.analysis.classification.categories
        }
        counts.update(categories)

    return [
        PortfolioCategoryUsage(
            category=category,
            repository_count=counts[category],
        )
        for category in RepositoryCategory
        if counts[category] > 0
    ]


def _primary_category_distribution(
    portfolio_analysis: PortfolioRepositoryAnalysis,
) -> list[PortfolioCategoryUsage]:
    counts = Counter(
        result.analysis.classification.primary_category
        for result in portfolio_analysis.repositories
    )

    return [
        PortfolioCategoryUsage(
            category=category,
            repository_count=counts[category],
        )
        for category in RepositoryCategory
        if counts[category] > 0
    ]


def _portfolio_signals(
    portfolio_analysis: PortfolioRepositoryAnalysis,
) -> list[PortfolioSignalCount]:
    return [
        PortfolioSignalCount(
            key=definition.key,
            label=definition.label,
            detected_repository_count=sum(
                definition.detect(result.analysis)
                for result in portfolio_analysis.repositories
            ),
        )
        for definition in PORTFOLIO_SIGNAL_DEFINITIONS
    ]


def _repository_score_distribution(
    portfolio_analysis: PortfolioRepositoryAnalysis,
) -> list[RepositoryScoreBucket]:
    counts = [0] * len(REPOSITORY_SCORE_BUCKETS)

    for result in portfolio_analysis.repositories:
        for index, (min_score, max_score) in enumerate(
            REPOSITORY_SCORE_BUCKETS
        ):
            if min_score <= result.score.overall_score <= max_score:
                counts[index] += 1
                break

    return [
        RepositoryScoreBucket(
            min_score=min_score,
            max_score=max_score,
            repository_count=counts[index],
        )
        for index, (min_score, max_score) in enumerate(
            REPOSITORY_SCORE_BUCKETS
        )
    ]


def aggregate_portfolio(
    portfolio_analysis: PortfolioRepositoryAnalysis,
) -> PortfolioAggregation:
    """Summarize normalized repository results without additional I/O."""

    successful_repository_count = len(portfolio_analysis.repositories)
    failed_repository_count = len(portfolio_analysis.failures)

    return PortfolioAggregation(
        selection_version=portfolio_analysis.selection_version,
        selected_repository_count=(
            successful_repository_count + failed_repository_count
        ),
        successful_repository_count=successful_repository_count,
        failed_repository_count=failed_repository_count,
        has_failures=failed_repository_count > 0,
        partial_evidence_repository_count=sum(
            result.score.is_partial
            for result in portfolio_analysis.repositories
        ),
        technology_distribution=_technology_distribution(
            portfolio_analysis
        ),
        category_distribution=_category_distribution(
            portfolio_analysis
        ),
        primary_category_distribution=(
            _primary_category_distribution(portfolio_analysis)
        ),
        portfolio_signals=_portfolio_signals(portfolio_analysis),
        repository_score_distribution=(
            _repository_score_distribution(portfolio_analysis)
        ),
    )

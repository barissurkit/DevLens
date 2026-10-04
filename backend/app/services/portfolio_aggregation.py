from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.schemas.analysis import (
    PortfolioAggregation,
    PortfolioCategoryUsage,
    PortfolioRepositoryAnalysis,
    PortfolioRepositoryResult,
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
    detect: Callable[[PortfolioRepositoryResult, datetime], bool]


RECENT_ACTIVITY_WINDOW = timedelta(days=365)


def _from_analysis(
    detect: Callable[[RepositoryAnalysis], bool],
) -> Callable[[PortfolioRepositoryResult, datetime], bool]:
    return lambda result, _now: detect(result.analysis)


def _was_recently_updated(result: PortfolioRepositoryResult, now: datetime) -> bool:
    updated_at = result.repository.updated_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return now - updated_at <= RECENT_ACTIVITY_WINDOW


PORTFOLIO_SIGNAL_DEFINITIONS: tuple[PortfolioSignalDefinition, ...] = (
    PortfolioSignalDefinition(
        key="readme_exists",
        label="README mevcut",
        detect=_from_analysis(lambda analysis: analysis.readme.exists),
    ),
    PortfolioSignalDefinition(
        key="readme_title",
        label="README başlığı",
        detect=_from_analysis(lambda analysis: analysis.readme.has_title),
    ),
    PortfolioSignalDefinition(
        key="readme_description",
        label="README açıklaması",
        detect=_from_analysis(lambda analysis: analysis.readme.has_description),
    ),
    PortfolioSignalDefinition(
        key="readme_installation",
        label="README kurulumu",
        detect=_from_analysis(lambda analysis: analysis.readme.has_installation),
    ),
    PortfolioSignalDefinition(
        key="readme_usage",
        label="README kullanımı",
        detect=_from_analysis(lambda analysis: analysis.readme.has_usage),
    ),
    PortfolioSignalDefinition(
        key="readme_technologies",
        label="README teknolojileri",
        detect=_from_analysis(lambda analysis: analysis.readme.has_technologies),
    ),
    PortfolioSignalDefinition(
        key="readme_requirements",
        label="README gereksinimleri",
        detect=_from_analysis(lambda analysis: analysis.readme.has_requirements),
    ),
    PortfolioSignalDefinition(
        key="tests_structure",
        label="Test Yapısı",
        detect=_from_analysis(lambda analysis: analysis.structure.has_tests),
    ),
    PortfolioSignalDefinition(
        key="ci_workflow",
        label="CI İş Akışı",
        detect=_from_analysis(lambda analysis: analysis.structure.has_ci),
    ),
    PortfolioSignalDefinition(
        key="gitignore",
        label=".gitignore",
        detect=_from_analysis(lambda analysis: analysis.structure.has_gitignore),
    ),
    PortfolioSignalDefinition(
        key="license",
        label="LICENSE",
        detect=_from_analysis(lambda analysis: analysis.structure.has_license),
    ),
    PortfolioSignalDefinition(
        key="contributing",
        label="CONTRIBUTING",
        detect=_from_analysis(lambda analysis: analysis.structure.has_contributing),
    ),
    PortfolioSignalDefinition(
        key="repo_description",
        label="Repository açıklaması",
        detect=lambda result, _now: bool(result.repository.description and result.repository.description.strip()),
    ),
    PortfolioSignalDefinition(
        key="repo_topics",
        label="Konu etiketleri",
        detect=lambda result, _now: len(result.repository.topics) > 0,
    ),
    PortfolioSignalDefinition(
        key="recent_activity",
        label="Son 12 ayda güncelleme",
        detect=_was_recently_updated,
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
    now: datetime,
) -> list[PortfolioSignalCount]:
    return [
        PortfolioSignalCount(
            key=definition.key,
            label=definition.label,
            detected_repository_count=sum(
                definition.detect(result, now)
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
    now: datetime | None = None,
) -> PortfolioAggregation:
    """Summarize normalized repository results without additional I/O.

    ``now`` is the reference time of time-based signals (recent activity); tests pass a fixed value.
    """

    now = now or datetime.now(timezone.utc)

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
        portfolio_signals=_portfolio_signals(portfolio_analysis, now),
        repository_score_distribution=(
            _repository_score_distribution(portfolio_analysis)
        ),
    )

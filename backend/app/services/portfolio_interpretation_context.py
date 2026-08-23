from app.schemas.analysis import GitHubPortfolioAnalysis
from app.schemas.interpretation import (
    InterpretationRepositoryContext,
    InterpretationScoreContext,
    InterpretationSignal,
    PortfolioInterpretationContext,
)


def build_portfolio_interpretation_context(
    analysis: GitHubPortfolioAnalysis,
) -> PortfolioInterpretationContext:
    """Project deterministic analysis into a bounded, AI-specific context."""

    return PortfolioInterpretationContext(
        username=analysis.user.username,
        public_repository_count=analysis.user.public_repos,
        selected_repository_count=analysis.aggregation.selected_repository_count,
        successful_repository_count=analysis.aggregation.successful_repository_count,
        failed_repository_count=analysis.aggregation.failed_repository_count,
        has_failures=analysis.aggregation.has_failures,
        partial_evidence_repository_count=(
            analysis.aggregation.partial_evidence_repository_count
        ),
        score=InterpretationScoreContext(
            is_available=analysis.score.is_available,
            overall_score=analysis.score.overall_score,
            scored_repository_count=analysis.score.scored_repository_count,
            dimension_scores={
                dimension.key: dimension.score
                for dimension in analysis.score.dimensions
            },
            is_partial=analysis.score.is_partial,
            limitations=list(analysis.score.limitations),
        ),
        strength_signals=[
            InterpretationSignal.model_validate(signal.model_dump())
            for signal in analysis.intelligence.strength_signals
        ],
        improvement_signals=[
            InterpretationSignal.model_validate(signal.model_dump())
            for signal in analysis.intelligence.improvement_signals
        ],
        recurring_technologies=[
            item.technology for item in analysis.intelligence.recurring_technologies
        ],
        dominant_areas=[item.category for item in analysis.intelligence.dominant_areas],
        limitations=list(analysis.intelligence.limitations),
        repositories=[
            InterpretationRepositoryContext(
                name=result.repository.name,
                primary_language=result.repository.primary_language,
                overall_score=result.score.overall_score,
                dimension_scores={
                    dimension.key: dimension.score
                    for dimension in result.score.dimensions
                },
                technologies=sorted(
                    {
                        technology.name
                        for technology in result.analysis.technologies.technologies
                    },
                    key=str.casefold,
                ),
                categories=[
                    category.category
                    for category in result.analysis.classification.categories
                ],
                is_partial=result.score.is_partial,
            )
            for result in analysis.repository_analysis.repositories
        ],
    )

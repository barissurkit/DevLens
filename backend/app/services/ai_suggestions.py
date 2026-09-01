from app.clients.gemini import GeminiInvalidResponseError
from app.schemas.ai_suggestions import AISuggestion, AISuggestions
from app.schemas.analysis import GitHubPortfolioAnalysis
from app.schemas.interpretation import PortfolioInterpretationContext


def build_evidence_catalog(
    analysis: GitHubPortfolioAnalysis,
    context: PortfolioInterpretationContext,
) -> dict[str, str]:
    catalog = {
        f"signal:{signal.key}": signal.message
        for signal in context.improvement_signals
    }
    for result in analysis.repository_analysis.repositories:
        for dimension in result.score.dimensions:
            for rule in dimension.rules:
                if not rule.passed:
                    catalog[f"repository:{result.repository.name}:{rule.key}"] = rule.evidence
    return dict(list(catalog.items())[:40])


def validate_suggestions(
    suggestions: AISuggestions,
    evidence_catalog: dict[str, str],
) -> AISuggestions:
    if len(suggestions.suggestions) > 5:
        raise GeminiInvalidResponseError("Too many AI suggestions.")
    valid: list[AISuggestion] = []
    for item in suggestions.suggestions:
        if not item.evidence_refs or any(ref not in evidence_catalog for ref in item.evidence_refs):
            raise GeminiInvalidResponseError("Unknown AI suggestion evidence reference.")
        valid.append(item)
    return AISuggestions(suggestions=valid)


import json
import logging

from app.clients.gemini import GeminiInvalidResponseError
from app.schemas.ai_suggestions import AISuggestion, AISuggestions
from app.schemas.analysis import GitHubPortfolioAnalysis
from app.schemas.interpretation import PortfolioInterpretationContext
from app.observability import emit_event

logger = logging.getLogger(__name__)

MAX_EVIDENCE_ITEMS = 40
MAX_EVIDENCE_VALUE_CHARS = 600
MAX_GROUNDING_CHARS = 24_000


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
    bounded: dict[str, str] = {}
    for evidence_id, value in catalog.items():
        if len(bounded) >= MAX_EVIDENCE_ITEMS or len(value) > MAX_EVIDENCE_VALUE_CHARS:
            continue
        candidate = {**bounded, evidence_id: value}
        if len(json.dumps(candidate, ensure_ascii=False, separators=(",", ":"))) > MAX_GROUNDING_CHARS:
            break
        bounded = candidate
    return bounded


def validate_suggestions(
    suggestions: AISuggestions,
    evidence_catalog: dict[str, str],
) -> AISuggestions:
    if len(suggestions.suggestions) > 5:
        emit_event(
            logger,
            "ai_suggestions.invalid_response",
            level=logging.WARNING,
            operation="suggest_actions",
            provider="gemini",
            failure_category="pydantic_schema",
        )
        raise GeminiInvalidResponseError("Too many AI suggestions.")
    for item in suggestions.suggestions:
        if not item.evidence_refs or len(set(item.evidence_refs)) != len(item.evidence_refs) or any(ref not in evidence_catalog for ref in item.evidence_refs):
            emit_event(
                logger,
                "ai_suggestions.invalid_response",
                level=logging.WARNING,
                operation="suggest_actions",
                provider="gemini",
                failure_category="evidence_reference",
            )
            raise GeminiInvalidResponseError("Unknown AI suggestion evidence reference.")
    return suggestions

import asyncio
from types import SimpleNamespace

import pytest

from app.clients.gemini import (
    GeminiClient,
    GeminiInvalidResponseError,
    GeminiNotConfiguredError,
    validate_interpretation_references,
)
from app.config import Settings
from app.prompts.portfolio_interpretation import (
    SYSTEM_INSTRUCTION,
    build_interpretation_content,
)
from app.schemas.interpretation import (
    InterpretationExplanation,
    InterpretationScoreContext,
    InterpretationSignal,
    PortfolioInterpretation,
    PortfolioInterpretationContext,
)
from app.services.portfolio_interpretation_context import (
    build_portfolio_interpretation_context,
)


def context() -> PortfolioInterpretationContext:
    return PortfolioInterpretationContext(
        username="octocat",
        public_repository_count=3,
        selected_repository_count=2,
        successful_repository_count=2,
        failed_repository_count=0,
        has_failures=False,
        partial_evidence_repository_count=0,
        score=InterpretationScoreContext(
            is_available=True,
            overall_score=0,
            scored_repository_count=2,
            dimension_scores={"testing": 0},
            is_partial=False,
            limitations=[],
        ),
        strength_signals=[
            InterpretationSignal(
                key="tests_structure",
                message="Tests are present.",
                detected_repository_count=2,
                analyzed_repository_count=2,
            )
        ],
        improvement_signals=[],
        recurring_technologies=["Python"],
        dominant_areas=[],
        limitations=[],
        repositories=[],
    )


def test_settings_keep_gemini_optional_and_model_overridable(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")

    settings = Settings(_env_file=None)

    assert settings.gemini_api_key is None
    assert settings.gemini_model == "gemini-test-model"


def test_prompt_is_deterministic_and_excludes_raw_payload_fields() -> None:
    first = build_interpretation_content(context())

    assert first == build_interpretation_content(context())
    assert "raw README" not in first
    assert "Authorization" not in first
    assert "tests_structure" in first
    assert "<devlens_context>" in first
    assert "only source of truth" in SYSTEM_INSTRUCTION
    assert "seniority" in SYSTEM_INSTRUCTION
    assert "employability" in SYSTEM_INSTRUCTION
    assert "untrusted data" in SYSTEM_INSTRUCTION


def test_context_builder_preserves_order_and_zero_score_semantics() -> None:
    analysis = SimpleNamespace(
        user=SimpleNamespace(username="octocat", public_repos=4),
        aggregation=SimpleNamespace(
            selected_repository_count=3,
            successful_repository_count=2,
            failed_repository_count=1,
            has_failures=True,
            partial_evidence_repository_count=1,
        ),
        score=SimpleNamespace(
            is_available=True,
            overall_score=0,
            scored_repository_count=2,
            dimensions=[SimpleNamespace(key="testing", score=0)],
            is_partial=True,
            limitations=["partial"],
        ),
        intelligence=SimpleNamespace(
            strength_signals=[],
            improvement_signals=[],
            recurring_technologies=[],
            dominant_areas=[],
            limitations=["failed repository"],
        ),
        repository_analysis=SimpleNamespace(
            repositories=[
                SimpleNamespace(
                    repository=SimpleNamespace(name="first", primary_language="Python"),
                    score=SimpleNamespace(
                        overall_score=0,
                        dimensions=[],
                        is_partial=True,
                    ),
                    analysis=SimpleNamespace(
                        technologies=SimpleNamespace(technologies=[]),
                        classification=SimpleNamespace(categories=[]),
                    ),
                ),
                SimpleNamespace(
                    repository=SimpleNamespace(name="second", primary_language=None),
                    score=SimpleNamespace(
                        overall_score=10,
                        dimensions=[],
                        is_partial=False,
                    ),
                    analysis=SimpleNamespace(
                        technologies=SimpleNamespace(technologies=[]),
                        classification=SimpleNamespace(categories=[]),
                    ),
                ),
            ]
        ),
    )

    result = build_portfolio_interpretation_context(analysis)  # type: ignore[arg-type]

    assert result.score.overall_score == 0
    assert result.has_failures is True
    assert result.repositories[0].name == "first"
    assert result.repositories[1].name == "second"
    assert result.repositories[0].is_partial is True


def test_unknown_and_duplicate_signal_references_are_rejected() -> None:
    unknown = PortfolioInterpretation(
        summary="Grounded summary.",
        strength_explanations=[
            InterpretationExplanation(signal_key="invented", explanation="No.")
        ],
    )
    with pytest.raises(GeminiInvalidResponseError, match="Unknown strength"):
        validate_interpretation_references(unknown, context())

    duplicate = PortfolioInterpretation(
        summary="Grounded summary.",
        strength_explanations=[
            InterpretationExplanation(signal_key="tests_structure", explanation="A."),
            InterpretationExplanation(signal_key="tests_structure", explanation="B."),
        ],
    )
    with pytest.raises(GeminiInvalidResponseError, match="Duplicate"):
        validate_interpretation_references(duplicate, context())


def test_gemini_key_is_required_only_at_client_boundary() -> None:
    with pytest.raises(GeminiNotConfiguredError):
        GeminiClient(Settings(_env_file=None))


class FakeModels:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def generate_content(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            parsed=PortfolioInterpretation(
                summary="Evidence-based summary.",
                strength_explanations=[
                    InterpretationExplanation(
                        signal_key="tests_structure",
                        explanation="Tests are present in the analyzed repositories.",
                    )
                ],
            )
        )


class FakeSdkClient:
    def __init__(self, models: FakeModels) -> None:
        self.aio = SimpleNamespace(models=models)


def test_client_uses_async_structured_generation_without_network() -> None:
    models = FakeModels()
    client = GeminiClient(
        Settings(_env_file=None, gemini_api_key="sentinel-not-a-real-key"),
        sdk_client=FakeSdkClient(models),
    )

    result = asyncio.run(client.interpret(context()))

    assert result.summary == "Evidence-based summary."
    assert len(models.calls) == 1
    request = models.calls[0]
    assert request["model"] == "gemini-2.5-flash"
    assert "tests_structure" in str(request["contents"])
    config = request["config"]
    assert getattr(config, "response_mime_type") == "application/json"
    assert getattr(config, "response_schema") is PortfolioInterpretation
    assert getattr(config, "candidate_count") == 1
    assert getattr(config, "tools", None) is None

import asyncio
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors

from app.clients.gemini import (
    GeminiClient,
    GeminiInvalidResponseError,
    GeminiNotConfiguredError,
    GeminiRateLimitError,
    GeminiUnavailableError,
    GeminiUpstreamError,
    _GEMINI_MAX_ATTEMPTS,
    _GEMINI_TIMEOUT_MS,
    _log_gemini_failure,
    _log_invalid_response_failure,
    _normalize_sdk_error,
    build_gemini_response_schema,
    validate_interpretation_references,
)
from app.config import Settings
from app.prompts.portfolio_interpretation import (
    GEMINI_INTERPRETATION_PROMPT_VERSION,
    SYSTEM_INSTRUCTION,
    build_interpretation_content,
)
from app.schemas.interpretation import (
    InterpretationExplanation,
    InterpretationScoreContext,
    InterpretationSignal,
    PortfolioInterpretation,
    PortfolioInterpretationContext,
    NextProjectRecommendation,
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


def test_settings_default_to_supported_gemini_production_model() -> None:
    settings = Settings(_env_file=None)

    assert settings.gemini_model == "gemini-3.6-flash"


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
    assert "Do not optimize for score" in SYSTEM_INSTRUCTION
    assert "technology choice as a reason" in SYSTEM_INSTRUCTION
    assert "exactly these top-level keys" in SYSTEM_INSTRUCTION
    assert "Do not omit any" in SYSTEM_INSTRUCTION
    assert "alternate keys such as" in SYSTEM_INSTRUCTION
    assert "must each be either a JSON string or JSON null" in SYSTEM_INSTRUCTION
    assert GEMINI_INTERPRETATION_PROMPT_VERSION == "v2"


def test_gemini_response_schema_removes_unsupported_constraint_keywords() -> None:
    schema = build_gemini_response_schema()
    schema_text = str(schema)

    assert "'default'" not in schema_text
    assert "'minLength'" not in schema_text
    assert "'maxLength'" not in schema_text
    assert "'$defs'" not in schema_text
    assert "'$ref'" not in schema_text
    assert "'anyOf'" not in schema_text
    assert schema["properties"]["technology_context"]["type"] == ["string", "null"]
    assert schema["properties"]["next_project_recommendation"]["type"] == [
        "object",
        "null",
    ]
    assert set(schema["properties"]) == {
        "summary",
        "strength_explanations",
        "improvement_explanations",
        "technology_context",
        "project_area_context",
        "limitations_note",
        "next_project_recommendation",
    }
    assert set(schema["required"]) == set(schema["properties"])
    assert set(schema["properties"]["strength_explanations"]["items"]["properties"]) == {
        "signal_key",
        "explanation",
    }


@pytest.mark.parametrize("status_code", [500, 503, 504])
def test_gemini_server_failures_are_unavailable(status_code: int) -> None:
    error = genai_errors.APIError(status_code, {"error": {"status": "UNAVAILABLE"}})

    assert isinstance(_normalize_sdk_error(error), GeminiUnavailableError)


def test_gemini_rate_limit_and_client_errors_keep_distinct_mapping() -> None:
    rate_limit = genai_errors.APIError(429, {"error": {"status": "RESOURCE_EXHAUSTED"}})
    invalid_request = genai_errors.APIError(400, {"error": {"status": "INVALID_ARGUMENT"}})

    assert isinstance(_normalize_sdk_error(rate_limit), GeminiRateLimitError)
    assert isinstance(_normalize_sdk_error(invalid_request), GeminiUpstreamError)


def test_gemini_diagnostics_log_safe_fields_only(caplog: pytest.LogCaptureFixture) -> None:
    secret = "sentinel-api-key-must-not-appear"
    error = genai_errors.APIError(
        503,
        {"error": {"status": "UNAVAILABLE", "message": secret}},
    )

    _log_gemini_failure(error=error, model="gemini-3.7-flash", elapsed_ms=321)

    message = caplog.text
    assert "upstream_status_code=503" in message
    assert "upstream_google_status=UNAVAILABLE" in message
    assert "elapsed_ms=321" in message
    assert "error_category=UNAVAILABLE" in message
    assert secret not in message


@pytest.mark.parametrize(
    ("response_text", "expected_parse", "expected_type", "expected_location"),
    [
        ('{"summary": 42}', "success", "string_type", "summary"),
        ("not-json", "failed", "json_invalid", ""),
    ],
)
def test_invalid_response_diagnostics_identify_safe_contract_failure(
    response_text: str,
    expected_parse: str,
    expected_type: str,
    expected_location: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from pydantic import ValidationError

    try:
        PortfolioInterpretation.model_validate_json(response_text)
    except ValidationError as error:
        response = SimpleNamespace(
            text=response_text,
            candidates=[SimpleNamespace(finish_reason="STOP")],
        )
        _log_invalid_response_failure(
            response=response,
            error=error,
            model="gemini-3.6-flash",
            elapsed_ms=20600,
        )

    message = caplog.text
    assert "model=gemini-3.6-flash" in message
    assert f"json_parse={expected_parse}" in message
    assert "response_text_bytes=" in message
    assert "finish_reasons=STOP" in message
    assert "top_level_value_types=summary:number" in message or "top_level_value_types=none" in message
    assert f"validation_error_types={expected_type}" in message
    assert f"validation_error_locations={expected_location or 'none'}" in message
    assert response_text not in message


def test_gemini_retries_503_with_bounded_backoff() -> None:
    models = FakeModels()
    models.failures = [
        genai_errors.APIError(503, {"error": {"status": "UNAVAILABLE"}}),
    ]

    client = GeminiClient(
        Settings(_env_file=None, gemini_api_key="sentinel-not-a-real-key"),
        sdk_client=FakeSdkClient(models),
    )

    with patch(
        "app.clients.gemini.asyncio.sleep",
        new_callable=AsyncMock,
    ) as sleep:
        result = asyncio.run(client.interpret(context()))

    assert result.summary == "Evidence-based summary."
    assert len(models.calls) == 2
    assert [call.args[0] for call in sleep.await_args_list] == [0.5]


def test_gemini_latency_budget_is_finite_and_sdk_retry_is_single_attempt() -> None:
    assert _GEMINI_MAX_ATTEMPTS == 2
    assert _GEMINI_TIMEOUT_MS == 30_000


def test_gemini_does_not_retry_invalid_argument() -> None:
    models = FakeModels()
    models.failures = [
        genai_errors.APIError(400, {"error": {"status": "INVALID_ARGUMENT"}}),
    ]
    client = GeminiClient(
        Settings(_env_file=None, gemini_api_key="sentinel-not-a-real-key"),
        sdk_client=FakeSdkClient(models),
    )

    with patch("app.clients.gemini.asyncio.sleep", new_callable=AsyncMock) as sleep:
        with pytest.raises(GeminiUpstreamError):
            asyncio.run(client.interpret(context()))

    assert len(models.calls) == 1
    sleep.assert_not_awaited()


def recommendation(**overrides: object) -> NextProjectRecommendation:
    values: dict[str, object] = {
        "title": "Test ve CI odaklı API projesi",
        "goal": "Test ve CI evidence'ını görünür hale getirmek.",
        "rationale": "Deterministic analysis identified testing evidence as an improvement opportunity.",
        "focus_signal_keys": ["tests_structure", "ci_workflow"],
        "suggested_deliverables": [
            "Automated tests",
            "CI workflow",
            "Installation documentation",
        ],
    }
    values.update(overrides)
    return NextProjectRecommendation.model_validate(values)


def improvement_context() -> PortfolioInterpretationContext:
    return context().model_copy(
        update={
            "improvement_signals": [
                InterpretationSignal(
                    key="tests_structure",
                    message="Tests are an improvement opportunity.",
                    detected_repository_count=0,
                    analyzed_repository_count=2,
                ),
                InterpretationSignal(
                    key="ci_workflow",
                    message="CI is an improvement opportunity.",
                    detected_repository_count=0,
                    analyzed_repository_count=2,
                ),
            ]
        }
    )


def valid_interpretation_with_recommendation() -> PortfolioInterpretation:
    return PortfolioInterpretation(
        summary="Grounded summary.",
        strength_explanations=[
            InterpretationExplanation(signal_key="tests_structure", explanation="A.")
        ],
        improvement_explanations=[
            InterpretationExplanation(signal_key="tests_structure", explanation="A."),
            InterpretationExplanation(signal_key="ci_workflow", explanation="B."),
        ],
        next_project_recommendation=recommendation(),
    )


def test_recommendation_model_is_bounded_and_serializable() -> None:
    value = recommendation()

    assert value.model_dump(mode="json")["focus_signal_keys"] == [
        "tests_structure",
        "ci_workflow",
    ]
    with pytest.raises(ValueError):
        recommendation(focus_signal_keys=[])
    with pytest.raises(ValueError):
        recommendation(suggested_deliverables=["one", "two"])
    with pytest.raises(ValueError):
        recommendation(suggested_deliverables=["same", "same", "other"])


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


@pytest.mark.parametrize(
    "focus_keys",
    [
        ["docker"],
        ["tests_structure", "tests_structure"],
        ["ci_workflow", "tests_structure"],
    ],
)
def test_recommendation_focus_must_be_ordered_unique_improvement_subset(
    focus_keys: list[str],
) -> None:
    value = valid_interpretation_with_recommendation()
    value.next_project_recommendation = recommendation(focus_signal_keys=focus_keys)

    with pytest.raises(GeminiInvalidResponseError, match="[Rr]ecommendation focus"):
        validate_interpretation_references(value, improvement_context())


def test_recommendation_requires_improvements_and_cannot_use_strength_only_signal() -> None:
    missing = valid_interpretation_with_recommendation()
    missing.next_project_recommendation = None
    with pytest.raises(GeminiInvalidResponseError, match="required"):
        validate_interpretation_references(missing, improvement_context())

    value = PortfolioInterpretation(
        summary="Grounded summary.",
        strength_explanations=[
            InterpretationExplanation(signal_key="tests_structure", explanation="A.")
        ],
        improvement_explanations=[
            InterpretationExplanation(signal_key="tests_structure", explanation="A."),
            InterpretationExplanation(signal_key="ci_workflow", explanation="B."),
        ],
        next_project_recommendation=recommendation(focus_signal_keys=["tests_structure"]),
    )
    with pytest.raises(GeminiInvalidResponseError):
        validate_interpretation_references(value, improvement_context().model_copy(
            update={"improvement_signals": []}
        ))


def test_no_improvement_signals_require_null_recommendation() -> None:
    value = PortfolioInterpretation(
        summary="Grounded summary.",
        strength_explanations=[
            InterpretationExplanation(signal_key="tests_structure", explanation="A.")
        ],
        next_project_recommendation=recommendation(),
    )

    with pytest.raises(GeminiInvalidResponseError, match="unsupported"):
        validate_interpretation_references(value, context())


def test_gemini_key_is_required_only_at_client_boundary() -> None:
    with pytest.raises(GeminiNotConfiguredError):
        GeminiClient(Settings(_env_file=None))


class FakeModels:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.failures: list[Exception] = []

    async def generate_content(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.failures:
            raise self.failures.pop(0)
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
    assert request["model"] == "gemini-3.6-flash"
    assert "tests_structure" in str(request["contents"])
    config = request["config"]
    assert getattr(config, "response_mime_type") == "application/json"
    assert getattr(config, "response_json_schema") is None
    assert getattr(config, "candidate_count") == 1
    assert getattr(config, "temperature", None) is None
    assert getattr(config, "tools", None) is None

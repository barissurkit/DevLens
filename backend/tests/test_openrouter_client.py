import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app.clients.gemini import (
    GeminiInvalidResponseError,
    GeminiNotConfiguredError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GeminiUnavailableError,
    GeminiUpstreamError,
)
from app.clients.openrouter import DailyCallBudget, OpenRouterClient, restore_deterministic_order
from app.config import Settings
from app.schemas.analysis import GitHubPortfolioAnalysis
from app.schemas.interpretation import PortfolioInterpretation
from app.services.portfolio_interpretation_context import build_portfolio_interpretation_context

FIXTURE = Path(__file__).resolve().parents[2] / "frontend" / "e2e" / "fixtures" / "portfolio.json"
KEY = "sk-or-test-key-not-real"
PRIMARY = "z-ai/glm-5.3-flash"
BACKUP = "openai/gpt-6-luna"


@pytest.fixture(scope="module")
def context():
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return build_portfolio_interpretation_context(GitHubPortfolioAnalysis.model_validate(document["analysis"]))


def settings(**overrides) -> Settings:
    values = {"_env_file": None, "ai_provider": "openrouter", "openrouter_api_key": KEY, "environment": "test"}
    values.update(overrides)
    return Settings(**values)


def answer(context, *, shuffle: bool = False, drop_strength: bool = False) -> dict:
    strengths = [{"signal_key": s.key, "explanation": f"{s.key} birçok repository'de görülüyor."} for s in context.strength_signals]
    improvements = [{"signal_key": s.key, "explanation": f"{s.key} birkaç repository'de eksik."} for s in context.improvement_signals]
    if shuffle:
        strengths.reverse()
        improvements.reverse()
    if drop_strength:
        strengths = strengths[:-1]
    recommendation = None
    if context.improvement_signals:
        recommendation = {
            "title": "Küçük bir proje",
            "goal": "Eksik sinyalleri tek projede kapatmak.",
            "rationale": "Bu sinyaller en çok eksik olanlardır.",
            "focus_signal_keys": [s.key for s in context.improvement_signals[:3]],
            "suggested_deliverables": ["README", "Testler", "CI iş akışı"],
        }
        if shuffle:
            recommendation["focus_signal_keys"].reverse()
    return {
        "summary": "Portföy genel olarak düzenli.",
        "strength_explanations": strengths,
        "improvement_explanations": improvements,
        "technology_context": None,
        "project_area_context": None,
        "limitations_note": "Yalnızca herkese açık repository'ler analiz edildi.",
        "next_project_recommendation": recommendation,
    }


def chat(content: str, *, finish: str = "stop", cost: float | None = 0.0009) -> httpx.Response:
    usage = {"prompt_tokens": 2700, "completion_tokens": 900}
    if cost is not None:
        usage["cost"] = cost
    return httpx.Response(200, json={"choices": [{"message": {"content": content}, "finish_reason": finish}], "usage": usage})


class Provider:
    """A scripted OpenRouter: each call takes the next reply prepared for the model it asked for."""

    def __init__(self, replies: dict[str, list]) -> None:
        self.replies = {model: list(items) for model, items in replies.items()}
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        reply = self.replies[json.loads(request.content)["model"]].pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    @property
    def models(self) -> list[str]:
        return [json.loads(request.content)["model"] for request in self.requests]

    def client(self, config: Settings, budget: DailyCallBudget | None = None) -> OpenRouterClient:
        http = httpx.AsyncClient(transport=httpx.MockTransport(self.handler))
        return OpenRouterClient(config, http_client=http, budget=budget or DailyCallBudget())


def interpret(client: OpenRouterClient, context) -> PortfolioInterpretation:
    return asyncio.run(client.interpret(context))


def test_a_valid_answer_in_a_code_fence_is_accepted_and_the_key_stays_in_the_header(context) -> None:
    provider = Provider({PRIMARY: [chat("```json\n" + json.dumps(answer(context), ensure_ascii=False) + "\n```")]})

    result = interpret(provider.client(settings()), context)

    assert result.summary == "Portföy genel olarak düzenli."
    request = provider.requests[0]
    body = json.loads(request.content)
    assert request.headers["authorization"] == f"Bearer {KEY}"
    assert KEY.encode() not in request.content
    assert body["response_format"] == {"type": "json_object"} and body["usage"] == {"include": True}
    assert body["messages"][0]["role"] == "system" and body["max_tokens"] == 6000
    assert provider.models == [PRIMARY]


def test_explanations_in_the_wrong_order_are_put_back_not_rejected(context) -> None:
    provider = Provider({PRIMARY: [chat(json.dumps(answer(context, shuffle=True)))]})

    result = interpret(provider.client(settings()), context)

    assert [item.signal_key for item in result.strength_explanations] == [s.key for s in context.strength_signals]
    assert [item.signal_key for item in result.improvement_explanations] == [s.key for s in context.improvement_signals]
    assert result.next_project_recommendation.focus_signal_keys == [s.key for s in context.improvement_signals[:3]]


def test_reordering_never_rescues_a_skipped_or_invented_signal(context) -> None:
    skipped = PortfolioInterpretation.model_validate(answer(context, drop_strength=True))
    assert len(restore_deterministic_order(skipped, context).strength_explanations) == len(context.strength_signals) - 1

    provider = Provider({
        PRIMARY: [chat(json.dumps(answer(context, drop_strength=True)))],
        BACKUP: [chat(json.dumps(answer(context, drop_strength=True)))],
    })
    with pytest.raises(GeminiInvalidResponseError):
        interpret(provider.client(settings()), context)
    assert provider.models == [PRIMARY, BACKUP]


def test_a_failing_primary_model_falls_back_to_the_next_one(context) -> None:
    provider = Provider({PRIMARY: [httpx.Response(503, text="busy")], BACKUP: [chat(json.dumps(answer(context)))]})

    assert interpret(provider.client(settings()), context).summary
    assert provider.models == [PRIMARY, BACKUP]


def test_an_answer_cut_off_at_the_token_limit_counts_as_a_failure_of_that_model(context) -> None:
    provider = Provider({PRIMARY: [chat("", finish="length")], BACKUP: [chat(json.dumps(answer(context)))]})

    assert interpret(provider.client(settings()), context).summary
    assert provider.models == [PRIMARY, BACKUP]


def test_a_model_that_rejects_the_reasoning_setting_is_asked_again_without_it(context) -> None:
    provider = Provider({PRIMARY: [httpx.Response(400, text="unsupported parameter: reasoning"), chat(json.dumps(answer(context)))]})

    assert interpret(provider.client(settings()), context).summary
    bodies = [json.loads(request.content) for request in provider.requests]
    assert ["reasoning" in body for body in bodies] == [True, False]


def test_missing_credit_stops_at_once_because_every_model_would_fail(context) -> None:
    provider = Provider({PRIMARY: [httpx.Response(402, text="insufficient credits")], BACKUP: []})

    with pytest.raises(GeminiUpstreamError):
        interpret(provider.client(settings()), context)
    assert provider.models == [PRIMARY]


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        (httpx.TimeoutException("slow"), GeminiTimeoutError),
        (httpx.ConnectError("down"), GeminiUnavailableError),
        (httpx.Response(429, text="slow down"), GeminiRateLimitError),
        (httpx.Response(401, text="bad key"), GeminiUpstreamError),
        (httpx.Response(200, json={"unexpected": True}), GeminiInvalidResponseError),
    ],
)
def test_every_failure_is_reported_as_the_matching_boundary_error(context, reply, expected) -> None:
    provider = Provider({PRIMARY: [reply], BACKUP: [reply]})

    with pytest.raises(expected):
        interpret(provider.client(settings()), context)


def test_the_daily_call_cap_stops_calls_before_they_are_made(context) -> None:
    provider = Provider({PRIMARY: [chat(json.dumps(answer(context))), chat(json.dumps(answer(context)))]})
    client = provider.client(settings(ai_daily_call_limit=2, openrouter_fallback_models=""), DailyCallBudget())

    interpret(client, context)
    interpret(client, context)
    with pytest.raises(GeminiRateLimitError):
        interpret(client, context)

    assert len(provider.requests) == 2


def test_the_budget_counts_every_attempt_and_zero_means_unlimited() -> None:
    budget = DailyCallBudget()
    assert [budget.try_acquire(2) for _ in range(3)] == [True, True, False]
    unlimited = DailyCallBudget()
    assert all(unlimited.try_acquire(0) for _ in range(1000))
    assert unlimited.used_today == 1000


def test_suggestions_use_the_same_gateway_with_the_schema_in_the_instruction(context) -> None:
    suggestions = {"suggestions": [{"title": "README ekle", "description": "Kurulum adımlarını yaz.", "reason": "Kurulum bölümü eksik.", "evidence_refs": ["ev-1"]}]}
    provider = Provider({PRIMARY: [chat(json.dumps(suggestions))]})

    result = asyncio.run(provider.client(settings()).suggest_actions(context, {"ev-1": "kanıt"}))

    assert result.suggestions[0].evidence_refs == ["ev-1"]
    body = json.loads(provider.requests[0].content)
    assert "evidence_refs" in body["messages"][0]["content"] and body["max_tokens"] <= 3000


def test_the_client_needs_a_key_and_models_are_deduplicated_in_order() -> None:
    with pytest.raises(GeminiNotConfiguredError):
        OpenRouterClient(settings(openrouter_api_key=None))

    config = settings(openrouter_model="a/one", openrouter_fallback_models=" b/two, a/one ,,c/three ")
    assert config.openrouter_models == ["a/one", "b/two", "c/three"]


def test_ai_is_configured_only_for_the_selected_provider() -> None:
    assert settings().ai_configured is True
    assert settings(openrouter_api_key=None, gemini_api_key="g").ai_configured is False
    assert settings(ai_provider="gemini", openrouter_api_key=KEY).ai_configured is False
    assert settings(ai_provider="gemini", gemini_api_key="g").ai_configured is True


def test_the_request_dependency_picks_the_configured_provider() -> None:
    from fastapi import Request

    import app.api.github as github_api
    from app.clients.gemini import GeminiClient
    from app.main import create_app

    def build(config: Settings):
        request = Request({"type": "http", "headers": []})
        request.scope["app"] = create_app(config)
        return asyncio.run(github_api.get_gemini_client(request))

    base = {"auth_enabled": False, "cors_allowed_origins": "http://localhost:3000"}
    assert isinstance(build(settings(**base)), OpenRouterClient)
    assert isinstance(build(settings(**base, ai_provider="gemini", gemini_api_key="g")), GeminiClient)
    assert build(settings(**base, openrouter_api_key=None)) is None

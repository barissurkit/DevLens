"""OpenRouter provider for the AI interpretation and the action suggestions.

It speaks the OpenAI-compatible chat API and answers the same two questions as ``GeminiClient`` with the same
prompts, schemas and validation, and it raises the same ``Gemini*`` boundary errors so the services and API error
mapping stay provider independent. On top of that it adds what a pay-as-you-go gateway needs: an ordered list of
fallback models, a hard daily cap on provider calls and cost reporting.
"""

import asyncio
import json
import logging
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.clients.gemini import (
    GeminiError,
    GeminiInvalidResponseError,
    GeminiNotConfiguredError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GeminiUnavailableError,
    GeminiUpstreamError,
    validate_interpretation_references,
)
from app.config import Settings
from app.observability import emit_event
from app.prompts.ai_suggestions import AI_SUGGESTIONS_SYSTEM_INSTRUCTION, build_suggestions_content
from app.prompts.portfolio_interpretation import SYSTEM_INSTRUCTION, build_interpretation_content
from app.schemas.ai_suggestions import AISuggestions
from app.schemas.interpretation import PortfolioInterpretation, PortfolioInterpretationContext

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_SUGGESTIONS_MAX_TOKENS = 3000
_TEMPERATURE = 0.3
_REASONING_EFFORT = "low"  # thinking models spend max_tokens on thoughts first; keep them short
_PUBLIC_REFERER = "https://devlens.barissurkit.com"

T = TypeVar("T", bound=BaseModel)


class DailyCallBudget:
    """Counts provider calls per UTC day inside this process; the cap protects the prepaid credit."""

    def __init__(self) -> None:
        self._day = ""
        self._count = 0

    def try_acquire(self, limit: int) -> bool:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if today != self._day:
            self._day, self._count = today, 0
        if limit > 0 and self._count >= limit:
            return False
        self._count += 1
        return True

    @property
    def used_today(self) -> int:
        return self._count if self._day == datetime.now(UTC).strftime("%Y-%m-%d") else 0


# One budget per process: the client itself is created per request.
DAILY_BUDGET = DailyCallBudget()


def extract_json(text: str) -> str:
    """Models sometimes wrap the object in a code fence or a sentence; keep only the outermost object."""

    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    start, end = stripped.find("{"), stripped.rfind("}")
    return stripped[start : end + 1] if start != -1 and end > start else stripped


def restore_deterministic_order(
    interpretation: PortfolioInterpretation,
    context: PortfolioInterpretationContext,
) -> PortfolioInterpretation:
    """Put the explanations in the order of the deterministic signals when the model only shuffled them.

    The contents are untouched and only used when the keys already match exactly as a set, so a model that skipped,
    invented or repeated a signal is still rejected by ``validate_interpretation_references``.
    """

    def ordered(items: list, expected: list[str]) -> list:
        keys = [item.signal_key for item in items]
        if keys == expected or sorted(keys) != sorted(expected) or len(set(keys)) != len(keys):
            return items
        return sorted(items, key=lambda item: expected.index(item.signal_key))

    update: dict[str, object] = {
        "strength_explanations": ordered(interpretation.strength_explanations, [s.key for s in context.strength_signals]),
        "improvement_explanations": ordered(interpretation.improvement_explanations, [s.key for s in context.improvement_signals]),
    }
    recommendation = interpretation.next_project_recommendation
    if recommendation is not None:
        expected = [s.key for s in context.improvement_signals]
        focus = recommendation.focus_signal_keys
        if len(set(focus)) == len(focus) and all(key in expected for key in focus):
            update["next_project_recommendation"] = recommendation.model_copy(
                update={"focus_signal_keys": sorted(focus, key=expected.index)}
            )
    return interpretation.model_copy(update=update)


class OpenRouterClient:
    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
        budget: DailyCallBudget | None = None,
    ) -> None:
        if not settings.openrouter_api_key:
            raise GeminiNotConfiguredError("OpenRouter API key is not configured.")
        self._api_key = settings.openrouter_api_key
        self._models = settings.openrouter_models
        self._max_tokens = settings.openrouter_max_tokens
        self._timeout = settings.openrouter_timeout_seconds
        self._daily_limit = settings.ai_daily_call_limit
        self._http = http_client
        self._budget = budget or DAILY_BUDGET

    async def interpret(self, context: PortfolioInterpretationContext) -> PortfolioInterpretation:
        def parse(text: str) -> PortfolioInterpretation:
            interpretation = PortfolioInterpretation.model_validate_json(extract_json(text))
            return validate_interpretation_references(restore_deterministic_order(interpretation, context), context)

        return await self._complete(
            operation="interpret",
            system=SYSTEM_INSTRUCTION,
            user=build_interpretation_content(context),
            max_tokens=self._max_tokens,
            parse=parse,
        )

    async def suggest_actions(
        self,
        context: PortfolioInterpretationContext,
        evidence_catalog: dict[str, str],
    ) -> AISuggestions:
        # The Gemini call passes a response schema; here the same shape is stated in the instruction.
        schema = json.dumps(AISuggestions.model_json_schema(), ensure_ascii=False, separators=(",", ":"))
        return await self._complete(
            operation="suggest_actions",
            system=f"{AI_SUGGESTIONS_SYSTEM_INSTRUCTION}\nThe JSON must follow this JSON schema:\n{schema}",
            user=build_suggestions_content(context, evidence_catalog),
            max_tokens=min(self._max_tokens, _SUGGESTIONS_MAX_TOKENS),
            parse=lambda text: AISuggestions.model_validate_json(extract_json(text)),
        )

    async def _complete(
        self,
        *,
        operation: str,
        system: str,
        user: str,
        max_tokens: int,
        parse: Callable[[str], T],
    ) -> T:
        last_error: GeminiError | None = None
        for position, model in enumerate(self._models, start=1):
            try:
                return await self._attempt(operation, model, position, system, user, max_tokens, parse)
            except _StopFallbacks as stop:
                raise stop.error from None
            except GeminiError as error:
                last_error = error
        raise last_error or GeminiUnavailableError("No OpenRouter model is configured.")

    async def _attempt(
        self,
        operation: str,
        model: str,
        position: int,
        system: str,
        user: str,
        max_tokens: int,
        parse: Callable[[str], T],
    ) -> T:
        started_at = time.monotonic()
        usage: dict = {}
        finish_reason: str | None = None

        def log(result: str, category: str | None = None, status: int | None = None, level: int = logging.INFO) -> None:
            emit_event(
                logger,
                "openrouter.request.completed",
                level=level,
                provider="openrouter",
                operation=operation,
                model=model,
                attempt=position,
                duration_ms=round((time.monotonic() - started_at) * 1000),
                result=result,
                error_category=category,
                upstream_status=status,
                finish_reason=finish_reason,
                cost_usd=usage.get("cost") if isinstance(usage.get("cost"), (int, float)) else None,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
            )

        if not self._budget.try_acquire(self._daily_limit):
            log("failure", "daily_limit", level=logging.WARNING)
            raise _StopFallbacks(GeminiRateLimitError("The daily AI call limit has been reached."))

        body = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": _TEMPERATURE,
            "response_format": {"type": "json_object"},
            "usage": {"include": True},
            "reasoning": {"effort": _REASONING_EFFORT},
        }
        try:
            response = await self._post(body)
            if response.status_code == 400 and "reasoning" in response.text.lower():
                # A model that does not take the reasoning setting is asked again without it.
                del body["reasoning"]
                response = await self._post(body)
        except (asyncio.TimeoutError, TimeoutError, httpx.TimeoutException) as error:
            log("failure", "timeout", level=logging.WARNING)
            raise GeminiTimeoutError("OpenRouter request timed out.") from error
        except httpx.RequestError as error:
            log("failure", "transport_error", level=logging.WARNING)
            raise GeminiUnavailableError("OpenRouter is unavailable.") from error

        status = response.status_code
        if status != 200:
            log("failure", "upstream_error", status, logging.WARNING)
            if status == 402:
                # Out of credit hits every model alike, so trying the next one only wastes time.
                raise _StopFallbacks(GeminiUpstreamError("OpenRouter credit is exhausted."))
            if status == 429:
                raise GeminiRateLimitError("OpenRouter rate limit prevented the request.")
            if status >= 500 or status == 408:
                raise GeminiUnavailableError("OpenRouter is unavailable.")
            raise GeminiUpstreamError("OpenRouter returned an upstream error.")

        try:
            payload = response.json()
            choice = payload["choices"][0]
            text = choice["message"].get("content") or ""
            finish_reason = choice.get("finish_reason") if isinstance(choice.get("finish_reason"), str) else None
            usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as error:
            log("failure", "response", level=logging.WARNING)
            raise GeminiInvalidResponseError("OpenRouter returned an unexpected response.") from error

        if finish_reason == "length":
            log("failure", "output_truncated", level=logging.WARNING)
            raise GeminiInvalidResponseError("OpenRouter output was cut off at the token limit.")
        try:
            result = parse(text)
        except (ValidationError, ValueError, TypeError) as error:
            log("failure", "validation", level=logging.WARNING)
            raise GeminiInvalidResponseError("OpenRouter returned an invalid structured answer.") from error
        except GeminiInvalidResponseError:
            log("failure", "validation", level=logging.WARNING)
            raise
        log("success")
        return result

    async def _post(self, body: dict) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": _PUBLIC_REFERER,
            "X-Title": "DevLens",
        }
        url = f"{OPENROUTER_BASE_URL}/chat/completions"
        if self._http is not None:
            return await self._http.post(url, headers=headers, json=body, timeout=self._timeout)
        async with httpx.AsyncClient() as client:
            return await client.post(url, headers=headers, json=body, timeout=self._timeout)


class _StopFallbacks(Exception):
    """Raised for failures that every fallback model would share (no credit, daily cap reached)."""

    def __init__(self, error: GeminiError) -> None:
        super().__init__(str(error))
        self.error = error

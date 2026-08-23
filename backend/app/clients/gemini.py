import asyncio
from collections.abc import Awaitable
from typing import Protocol

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import ValidationError

from app.config import Settings
from app.prompts.portfolio_interpretation import (
    SYSTEM_INSTRUCTION,
    build_interpretation_content,
)
from app.schemas.interpretation import (
    PortfolioInterpretation,
    PortfolioInterpretationContext,
)


class GeminiError(Exception):
    """Base class for expected Gemini boundary failures."""


class GeminiNotConfiguredError(GeminiError):
    pass


class GeminiTimeoutError(GeminiError):
    pass


class GeminiUnavailableError(GeminiError):
    pass


class GeminiRateLimitError(GeminiError):
    pass


class GeminiUpstreamError(GeminiError):
    pass


class GeminiInvalidResponseError(GeminiError):
    pass


class _AsyncModels(Protocol):
    def generate_content(self, **kwargs: object) -> Awaitable[object]: ...


class _AsyncGeminiSurface(Protocol):
    @property
    def models(self) -> _AsyncModels: ...


class _GeminiClient(Protocol):
    @property
    def aio(self) -> _AsyncGeminiSurface: ...


def validate_interpretation_references(
    interpretation: PortfolioInterpretation,
    context: PortfolioInterpretationContext,
) -> PortfolioInterpretation:
    strength_keys = {signal.key for signal in context.strength_signals}
    improvement_keys = {signal.key for signal in context.improvement_signals}
    strength_output = interpretation.strength_explanations
    improvement_output = interpretation.improvement_explanations

    if len({item.signal_key for item in strength_output}) != len(strength_output):
        raise GeminiInvalidResponseError("Duplicate strength signal references.")
    if len({item.signal_key for item in improvement_output}) != len(improvement_output):
        raise GeminiInvalidResponseError("Duplicate improvement signal references.")
    if any(item.signal_key not in strength_keys for item in strength_output):
        raise GeminiInvalidResponseError("Unknown strength signal reference.")
    if any(item.signal_key not in improvement_keys for item in improvement_output):
        raise GeminiInvalidResponseError("Unknown improvement signal reference.")

    expected_strength_keys = [signal.key for signal in context.strength_signals]
    actual_strength_keys = [item.signal_key for item in strength_output]
    if actual_strength_keys != expected_strength_keys:
        raise GeminiInvalidResponseError(
            "Strength signal references do not exactly match deterministic signals."
        )

    expected_improvement_keys = [signal.key for signal in context.improvement_signals]
    actual_improvement_keys = [item.signal_key for item in improvement_output]
    if actual_improvement_keys != expected_improvement_keys:
        raise GeminiInvalidResponseError(
            "Improvement signal references do not exactly match deterministic signals."
        )

    recommendation = interpretation.next_project_recommendation
    if not context.improvement_signals and recommendation is not None:
        raise GeminiInvalidResponseError(
            "A recommendation is unsupported without deterministic improvements."
        )
    if context.improvement_signals and recommendation is None:
        raise GeminiInvalidResponseError(
            "A recommendation is required when deterministic improvements exist."
        )
    if recommendation is not None:
        expected_keys = [signal.key for signal in context.improvement_signals]
        focus_keys = recommendation.focus_signal_keys
        if len(set(focus_keys)) != len(focus_keys):
            raise GeminiInvalidResponseError("Duplicate recommendation focus signals.")
        if any(key not in expected_keys for key in focus_keys):
            raise GeminiInvalidResponseError(
                "Unknown recommendation focus signal reference."
            )
        expected_positions = [expected_keys.index(key) for key in focus_keys]
        if expected_positions != sorted(expected_positions):
            raise GeminiInvalidResponseError(
                "Recommendation focus signals do not preserve deterministic order."
            )

    return interpretation


def _normalize_sdk_error(error: Exception) -> GeminiError | None:
    if isinstance(error, (asyncio.TimeoutError, TimeoutError, httpx.TimeoutException)):
        return GeminiTimeoutError("Gemini request timed out.")
    if isinstance(error, httpx.RequestError):
        return GeminiUnavailableError("Gemini service is unavailable.")

    if not isinstance(error, genai_errors.APIError):
        return None

    status_code = error.code
    if status_code in {429, 403}:
        return GeminiRateLimitError("Gemini rate limit or quota prevented the request.")
    if isinstance(status_code, int) and status_code >= 500:
        return GeminiUnavailableError("Gemini service is unavailable.")
    return GeminiUpstreamError("Gemini returned an upstream error.")


class GeminiClient:
    def __init__(
        self,
        settings: Settings,
        sdk_client: _GeminiClient | None = None,
    ) -> None:
        if not settings.gemini_api_key:
            raise GeminiNotConfiguredError("Gemini API key is not configured.")
        self._model = settings.gemini_model
        self._client = sdk_client or genai.Client(api_key=settings.gemini_api_key)

    async def interpret(
        self,
        context: PortfolioInterpretationContext,
    ) -> PortfolioInterpretation:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=PortfolioInterpretation,
            candidate_count=1,
            temperature=0.2,
        )
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=build_interpretation_content(context),
                config=config,
            )
        except Exception as error:
            normalized = _normalize_sdk_error(error)
            if normalized is None:
                raise
            raise normalized from error

        try:
            parsed = getattr(response, "parsed", None)
            interpretation = (
                parsed
                if isinstance(parsed, PortfolioInterpretation)
                else PortfolioInterpretation.model_validate_json(response.text)
            )
        except (AttributeError, TypeError, ValidationError, ValueError) as error:
            raise GeminiInvalidResponseError(
                "Gemini returned an invalid structured interpretation."
            ) from error

        return validate_interpretation_references(interpretation, context)

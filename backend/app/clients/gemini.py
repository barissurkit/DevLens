import asyncio
import json
import logging
import re
import time
from collections.abc import Awaitable
from typing import Protocol

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import ValidationError

from app.config import Settings
from app.observability import current_request_id, emit_event
from app.prompts.portfolio_interpretation import (
    SYSTEM_INSTRUCTION,
    build_interpretation_content,
)
from app.prompts.ai_suggestions import (
    AI_SUGGESTIONS_SYSTEM_INSTRUCTION,
    build_suggestions_content,
    build_suggestions_response_schema,
)
from app.schemas.ai_suggestions import AISuggestions
from app.schemas.interpretation import (
    PortfolioInterpretation,
    PortfolioInterpretationContext,
)

logger = logging.getLogger(__name__)
_GEMINI_MAX_ATTEMPTS = 2
_GEMINI_RETRY_INITIAL_DELAY_SECONDS = 0.5
_GEMINI_TIMEOUT_MS = 30_000


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


def build_gemini_response_schema() -> object:
    """Build a supported inline schema while keeping Pydantic as final validation."""

    source = PortfolioInterpretation.model_json_schema()
    definitions = source.get("$defs", {})
    supported_keys = {
        "anyOf",
        "description",
        "enum",
        "format",
        "items",
        "maxItems",
        "maximum",
        "minItems",
        "minimum",
        "properties",
        "required",
        "title",
        "type",
    }

    def inline(value: object) -> object:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if (
                isinstance(reference, str)
                and reference.startswith("#/$defs/")
                and isinstance(definitions, dict)
            ):
                definition = definitions.get(reference.removeprefix("#/$defs/"))
                if definition is not None:
                    return inline(definition)
            filtered = {
                key: (
                    {
                        property_name: inline(property_schema)
                        for property_name, property_schema in nested.items()
                    }
                    if key == "properties" and isinstance(nested, dict)
                    else inline(nested)
                )
                for key, nested in value.items()
                if key in supported_keys
            }
            variants = filtered.get("anyOf")
            if isinstance(variants, list) and len(variants) == 2:
                nullable = next(
                    (item for item in variants if item == {"type": "null"}),
                    None,
                )
                non_null = next(
                    (item for item in variants if item is not nullable),
                    None,
                )
                if nullable is not None and isinstance(non_null, dict):
                    non_null_type = non_null.get("type")
                    if isinstance(non_null_type, str):
                        merged = dict(non_null)
                        merged["type"] = [non_null_type, "null"]
                        return merged
            return filtered
        if isinstance(value, list):
            return [inline(item) for item in value]
        return value

    schema = inline(source)
    if isinstance(schema, dict):
        properties = schema.get("properties")
        if isinstance(properties, dict):
            schema["required"] = list(properties)
    return schema


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
    if status_code == 429:
        return GeminiRateLimitError("Gemini rate limit or quota prevented the request.")
    if isinstance(status_code, int) and status_code >= 500:
        return GeminiUnavailableError("Gemini service is unavailable.")
    return GeminiUpstreamError("Gemini returned an upstream error.")


def _safe_google_status(error: genai_errors.APIError) -> str:
    status = error.status
    if isinstance(status, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", status):
        return status
    return "unknown"


def _log_gemini_failure(
    *,
    error: Exception,
    model: str,
    operation: str,
    elapsed_ms: int,
    attempt: int = 1,
) -> None:
    if isinstance(error, genai_errors.APIError):
        google_status = _safe_google_status(error)
        category = google_status if google_status != "unknown" else "api_error"
        structured_category = "rate_limit" if error.code == 429 else "upstream_error"
        display_category = (
            structured_category if error.code in {403, 429} else category
        )
        logger.warning(
            "Gemini request failed: model=%s upstream_status_code=%s "
            "upstream_google_status=%s elapsed_ms=%s error_category=%s",
            model,
            error.code,
            google_status,
            elapsed_ms,
            display_category,
            extra={
                "event": "gemini.request.completed",
                "provider": "gemini",
                "operation": operation,
                "model": model,
                "attempt": attempt,
                "duration_ms": elapsed_ms,
                "upstream_status": error.code,
                "error_category": structured_category,
                "provider_status": google_status,
                "result": "failure",
                "request_id": current_request_id(),
            },
        )
        return

    if isinstance(error, (asyncio.TimeoutError, TimeoutError, httpx.TimeoutException)):
        category = "timeout"
    elif isinstance(error, httpx.RequestError):
        category = "transport_error"
    else:
        category = "unexpected_error"
    logger.warning(
        "Gemini request failed: model=%s upstream_status_code=%s "
        "upstream_google_status=%s elapsed_ms=%s error_category=%s",
        model,
        "none",
        "none",
        elapsed_ms,
        category,
        extra={
            "event": "gemini.request.completed",
            "provider": "gemini",
            "operation": operation,
            "model": model,
            "attempt": attempt,
            "duration_ms": elapsed_ms,
            "error_category": category,
            "result": "failure",
            "request_id": current_request_id(),
        },
    )


def _safe_response_text(response: object) -> str:
    value = getattr(response, "text", "")
    return value if isinstance(value, str) else ""


def _safe_finish_reasons(response: object) -> list[str]:
    candidates = getattr(response, "candidates", None)
    if not isinstance(candidates, list):
        return []
    reasons: list[str] = []
    for candidate in candidates[:3]:
        reason = getattr(candidate, "finish_reason", None)
        if reason is not None:
            reasons.append(str(reason))
    return reasons


def _safe_validation_locations(error: ValidationError) -> list[str]:
    locations: list[str] = []
    for item in error.errors()[:20]:
        location = item.get("loc", ())
        parts = [str(part) for part in location if isinstance(part, (str, int))]
        locations.append(".".join(parts)[:160])
    return locations


def _safe_json_value_types(decoded: object) -> str:
    if not isinstance(decoded, dict):
        return "non_object"
    type_names: list[str] = []
    for key, value in sorted(decoded.items(), key=lambda item: str(item[0]))[:30]:
        if not isinstance(key, str):
            continue
        if value is None:
            value_type = "null"
        elif isinstance(value, bool):
            value_type = "boolean"
        elif isinstance(value, (int, float)):
            value_type = "number"
        elif isinstance(value, str):
            value_type = "string"
        elif isinstance(value, list):
            value_type = "array"
        elif isinstance(value, dict):
            value_type = "object"
        else:
            value_type = "other"
        type_names.append(f"{key[:80]}:{value_type}")
    return ",".join(type_names) or "none"


def _log_invalid_response_failure(
    *,
    response: object,
    error: Exception,
    model: str,
    elapsed_ms: int,
    attempt: int = 1,
) -> None:
    text = _safe_response_text(response)
    parsed_json = False
    top_level_keys: list[str] = []
    top_level_value_types = "none"
    if text:
        try:
            decoded = json.loads(text)
            parsed_json = True
            if isinstance(decoded, dict):
                top_level_keys = sorted(
                    str(key)[:80] for key in decoded.keys() if isinstance(key, str)
                )[:30]
                top_level_value_types = _safe_json_value_types(decoded)
        except (TypeError, ValueError):
            pass

    fields: dict[str, object] = {
        "model": model,
        "elapsed_ms": elapsed_ms,
        "response_text_bytes": len(text.encode("utf-8")),
        "json_parse": "success" if parsed_json else "failed",
        "top_level_keys": ",".join(top_level_keys) or "none",
        "top_level_value_types": top_level_value_types,
        "finish_reasons": ",".join(_safe_finish_reasons(response)) or "none",
        "error_category": "validation" if isinstance(error, ValidationError) else "response",
    }
    if isinstance(error, ValidationError):
        fields["validation_error_count"] = error.error_count()
        fields["validation_error_types"] = ",".join(
            str(item.get("type", "unknown"))[:80] for item in error.errors()[:20]
        ) or "none"
        fields["validation_error_locations"] = ",".join(
            _safe_validation_locations(error)
        ) or "none"
    logger.warning(
        "Gemini response rejected: %s",
        " ".join(f"{key}={value}" for key, value in fields.items()),
        extra={
            "event": "gemini.request.completed",
            "provider": "gemini",
            "operation": "interpret",
            "model": model,
            "attempt": attempt,
            "duration_ms": elapsed_ms,
            "error_category": fields["error_category"],
            "result": "failure",
            "response_bytes": fields["response_text_bytes"],
            "request_id": current_request_id(),
        },
    )


class GeminiClient:
    def __init__(
        self,
        settings: Settings,
        sdk_client: _GeminiClient | None = None,
    ) -> None:
        if not settings.gemini_api_key:
            raise GeminiNotConfiguredError("Gemini API key is not configured.")
        self._model = settings.gemini_model
        self._client = sdk_client or genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                timeout=_GEMINI_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    async def interpret(
        self,
        context: PortfolioInterpretationContext,
    ) -> PortfolioInterpretation:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            candidate_count=1,
        )
        for attempt in range(_GEMINI_MAX_ATTEMPTS):
            started_at = time.monotonic()
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=build_interpretation_content(context),
                    config=config,
                )
                break
            except Exception as error:
                elapsed_ms = round((time.monotonic() - started_at) * 1000)
                _log_gemini_failure(
                    error=error,
                    model=self._model,
                    operation="interpret",
                    elapsed_ms=elapsed_ms,
                    attempt=attempt + 1,
                )
                if (
                    isinstance(error, genai_errors.APIError)
                    and error.code == 503
                    and attempt < _GEMINI_MAX_ATTEMPTS - 1
                ):
                    await asyncio.sleep(
                        _GEMINI_RETRY_INITIAL_DELAY_SECONDS * (2**attempt)
                    )
                    continue
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
            _log_invalid_response_failure(
                response=response,
                error=error,
                model=self._model,
                elapsed_ms=round((time.monotonic() - started_at) * 1000),
                attempt=attempt + 1,
            )
            raise GeminiInvalidResponseError(
                "Gemini returned an invalid structured interpretation."
            ) from error

        try:
            interpretation = validate_interpretation_references(interpretation, context)
        except GeminiInvalidResponseError as error:
            _log_invalid_response_failure(
                response=response,
                error=error,
                model=self._model,
                elapsed_ms=round((time.monotonic() - started_at) * 1000),
                attempt=attempt + 1,
            )
            raise

        emit_event(
            logger,
            "gemini.request.completed",
            provider="gemini",
            operation="interpret",
            model=self._model,
            attempt=attempt + 1,
            duration_ms=round((time.monotonic() - started_at) * 1000),
            result="success",
            response_bytes=len(_safe_response_text(response).encode("utf-8")),
        )
        return interpretation

    async def suggest_actions(
        self,
        context: PortfolioInterpretationContext,
        evidence_catalog: dict[str, str],
    ) -> AISuggestions:
        config = types.GenerateContentConfig(
            system_instruction=AI_SUGGESTIONS_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=build_suggestions_response_schema(),
            candidate_count=1,
        )
        started_at = time.monotonic()
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=build_suggestions_content(context, evidence_catalog),
                config=config,
            )
        except Exception as error:
            _log_gemini_failure(
                error=error,
                model=self._model,
                operation="suggest_actions",
                elapsed_ms=round((time.monotonic() - started_at) * 1000),
            )
            normalized = _normalize_sdk_error(error)
            if normalized is None:
                raise
            raise normalized from error
        try:
            parsed = getattr(response, "parsed", None)
            return parsed if isinstance(parsed, AISuggestions) else AISuggestions.model_validate_json(response.text)
        except (AttributeError, TypeError, ValidationError, ValueError) as error:
            _log_invalid_response_failure(
                response=response,
                error=error,
                model=self._model,
                elapsed_ms=round((time.monotonic() - started_at) * 1000),
            )
            raise GeminiInvalidResponseError("Gemini returned invalid AI suggestions.") from error

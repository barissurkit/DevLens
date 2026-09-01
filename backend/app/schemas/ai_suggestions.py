from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AISuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    reason: str = Field(min_length=1, max_length=600)
    evidence_refs: list[str] = Field(min_length=1, max_length=3)


class AISuggestions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suggestions: list[AISuggestion] = Field(default_factory=list, max_length=5)


class AISuggestionsUnavailableReason(StrEnum):
    NOT_CONFIGURED = "not_configured"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    RATE_LIMIT = "rate_limit"
    UPSTREAM_ERROR = "upstream_error"
    INVALID_RESPONSE = "invalid_response"


class AISuggestionsAvailable(BaseModel):
    status: Literal["available"] = "available"
    suggestions: list[AISuggestion]


class AISuggestionsUnavailable(BaseModel):
    status: Literal["unavailable"] = "unavailable"
    reason: AISuggestionsUnavailableReason

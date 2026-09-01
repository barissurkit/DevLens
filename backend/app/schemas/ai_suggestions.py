from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AISuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    reason: str = Field(min_length=1, max_length=600)
    evidence_refs: list[str] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def validate_unique_evidence_refs(self) -> "AISuggestion":
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("Evidence references must be unique.")
        return self


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

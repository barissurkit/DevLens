from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class GuidedImprovementState(StrEnum):
    NEEDS_IMPROVEMENT = "needs_improvement"
    CRITERIA_MET = "criteria_met"


class GuidedImprovementVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detected_repository_count: int = Field(ge=0)
    analyzed_repository_count: int = Field(ge=0)
    current_state: GuidedImprovementState
    analysis_available: bool
    analysis_partial: bool
    reanalysis_required: bool


class GuidedImprovement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    why: str = Field(min_length=1)
    steps: list[str] = Field(min_length=1)
    verification: GuidedImprovementVerification

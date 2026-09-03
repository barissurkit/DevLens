from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.analysis import GitHubPortfolioAnalysis, RepositoryCategory, ViewerContext
from app.schemas.guided_improvement import GuidedImprovement


class InterpretationSignal(BaseModel):
    key: str = Field(min_length=1)
    message: str = Field(min_length=1)
    detected_repository_count: int = Field(ge=0)
    analyzed_repository_count: int = Field(gt=0)


class InterpretationScoreContext(BaseModel):
    is_available: bool
    overall_score: int | None = Field(default=None, ge=0, le=100)
    scored_repository_count: int = Field(ge=0)
    dimension_scores: dict[str, int]
    is_partial: bool
    limitations: list[str]


class InterpretationRepositoryContext(BaseModel):
    name: str = Field(min_length=1)
    primary_language: str | None
    overall_score: int = Field(ge=0, le=100)
    dimension_scores: dict[str, int]
    technologies: list[str]
    categories: list[RepositoryCategory]
    is_partial: bool


class PortfolioInterpretationContext(BaseModel):
    username: str = Field(min_length=1)
    public_repository_count: int = Field(ge=0)
    selected_repository_count: int = Field(ge=0)
    successful_repository_count: int = Field(ge=0)
    failed_repository_count: int = Field(ge=0)
    has_failures: bool
    partial_evidence_repository_count: int = Field(ge=0)
    score: InterpretationScoreContext
    strength_signals: list[InterpretationSignal]
    improvement_signals: list[InterpretationSignal]
    recurring_technologies: list[str]
    dominant_areas: list[RepositoryCategory]
    limitations: list[str]
    repositories: list[InterpretationRepositoryContext]


class InterpretationExplanation(BaseModel):
    signal_key: str = Field(min_length=1)
    explanation: str = Field(min_length=1, max_length=600)


RecommendationText = Annotated[str, Field(min_length=1, max_length=240)]


class NextProjectRecommendation(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=600)
    rationale: str = Field(min_length=1, max_length=800)
    focus_signal_keys: list[RecommendationText] = Field(min_length=1, max_length=3)
    suggested_deliverables: list[RecommendationText] = Field(min_length=3, max_length=5)

    @model_validator(mode="after")
    def validate_deliverables(self) -> "NextProjectRecommendation":
        if len(set(self.suggested_deliverables)) != len(self.suggested_deliverables):
            raise ValueError("Suggested deliverables must be unique.")
        return self


class PortfolioInterpretation(BaseModel):
    summary: str = Field(min_length=1, max_length=1600)
    strength_explanations: list[InterpretationExplanation] = Field(default_factory=list, max_length=50)
    improvement_explanations: list[InterpretationExplanation] = Field(default_factory=list, max_length=50)
    technology_context: str | None = Field(default=None, max_length=600)
    project_area_context: str | None = Field(default=None, max_length=600)
    limitations_note: str | None = Field(default=None, max_length=600)
    next_project_recommendation: NextProjectRecommendation | None = None


class InterpretationUnavailableReason(StrEnum):
    NOT_CONFIGURED = "not_configured"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    RATE_LIMIT = "rate_limit"
    UPSTREAM_ERROR = "upstream_error"
    INVALID_RESPONSE = "invalid_response"


class PortfolioInterpretationResult(BaseModel):
    """Internal application result separating AI availability from analysis."""

    available: bool
    interpretation: PortfolioInterpretation | None = None
    reason: InterpretationUnavailableReason | None = None

    @model_validator(mode="after")
    def validate_state(self) -> "PortfolioInterpretationResult":
        if self.available and (self.interpretation is None or self.reason is not None):
            raise ValueError("Available interpretation results require an interpretation only.")
        if not self.available and (self.interpretation is not None or self.reason is None):
            raise ValueError("Unavailable interpretation results require a reason only.")
        return self

    @property
    def unavailable_reason(self) -> InterpretationUnavailableReason | None:
        """Compatibility name for callers that prefer an explicit field name."""

        return self.reason


class PublicInterpretationAvailable(BaseModel):
    status: Literal["available"]
    interpretation: PortfolioInterpretation


class PublicInterpretationUnavailable(BaseModel):
    status: Literal["unavailable"]
    reason: InterpretationUnavailableReason


PublicPortfolioInterpretationResult = Annotated[
    PublicInterpretationAvailable | PublicInterpretationUnavailable,
    Field(discriminator="status"),
]


class GitHubPortfolioInterpretationResponse(BaseModel):
    analysis: GitHubPortfolioAnalysis
    interpretation: PublicPortfolioInterpretationResult
    viewer_context: ViewerContext
    guided_improvements: list[GuidedImprovement] = Field(default_factory=list)

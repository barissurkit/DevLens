from pydantic import BaseModel, Field

from app.schemas.analysis import RepositoryCategory


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


class PortfolioInterpretation(BaseModel):
    summary: str = Field(min_length=1, max_length=1600)
    strength_explanations: list[InterpretationExplanation] = Field(default_factory=list, max_length=50)
    improvement_explanations: list[InterpretationExplanation] = Field(default_factory=list, max_length=50)
    technology_context: str | None = Field(default=None, max_length=600)
    project_area_context: str | None = Field(default=None, max_length=600)
    limitations_note: str | None = Field(default=None, max_length=600)

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.normalization import normalize_github_username
from app.schemas.github import GitHubRepository, GitHubUser


class PortfolioAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=39)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        return normalize_github_username(value) if isinstance(value, str) else value


class ViewerContext(BaseModel):
    """Request-scoped mode derived from the authenticated viewer and target ID."""

    is_owner: bool
    mode: Literal["my_workspace", "explore"]


class RepositoryStructureSignals(BaseModel):
    has_tests: bool
    has_ci: bool
    has_dockerfile: bool
    has_compose: bool
    has_env_example: bool
    has_license: bool
    has_gitignore: bool
    has_contributing: bool


class ReadmeAnalysis(BaseModel):
    exists: bool
    content_length: int
    has_title: bool
    has_description: bool
    has_installation: bool
    has_usage: bool
    has_technologies: bool
    has_requirements: bool
    has_images: bool
    has_demo_link: bool


TechnologyCategory = Literal[
    "Data & ML",
    "Backend",
    "Frontend",
    "Testing",
    "Database",
]


class DetectedTechnology(BaseModel):
    name: str
    category: TechnologyCategory
    source_dependency: str


class TechnologyAnalysis(BaseModel):
    dependencies: list[str]
    technologies: list[DetectedTechnology]


class RepositoryClassificationInput(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    topics: list[str] = Field(default_factory=list)
    readme_content: str | None = None
    technology_analysis: TechnologyAnalysis
    structure_signals: RepositoryStructureSignals


class RepositoryCategory(StrEnum):
    MACHINE_LEARNING = "Machine Learning"
    DATA_SCIENCE = "Data Science"
    BACKEND = "Backend"
    FRONTEND = "Frontend"
    FULL_STACK = "Full Stack"
    DEVOPS = "DevOps"
    DATA_ENGINEERING = "Data Engineering"
    CLI_DEVELOPER_TOOL = "CLI / Developer Tool"
    LEARNING_EXPERIMENT = "Learning / Experiment"
    OTHER = "Other"


class RepositoryCategoryMatch(BaseModel):
    category: RepositoryCategory
    evidence_score: int = Field(ge=0)
    evidence: list[str] = Field(min_length=1)


class RepositoryClassification(BaseModel):
    categories: list[RepositoryCategoryMatch] = Field(min_length=1)
    primary_category: RepositoryCategory


class RepositoryAnalysis(BaseModel):
    repository: GitHubRepository
    readme: ReadmeAnalysis
    structure: RepositoryStructureSignals
    tree_truncated: bool
    technologies: TechnologyAnalysis
    classification: RepositoryClassification


class ScoreRuleResult(BaseModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    passed: bool
    points_earned: int = Field(ge=0)
    points_possible: int = Field(gt=0)
    evidence: str = Field(min_length=1)


class ScoreDimensionResult(BaseModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    points_earned: int = Field(ge=0)
    points_possible: int = Field(gt=0)
    score: int = Field(ge=0, le=100)
    rules: list[ScoreRuleResult] = Field(min_length=1)


class RepositoryScore(BaseModel):
    version: str = Field(min_length=1)
    overall_score: int = Field(ge=0, le=100)
    dimensions: list[ScoreDimensionResult] = Field(min_length=1)
    is_partial: bool
    limitations: list[str]


class PortfolioRepositoryExclusionReason(StrEnum):
    FORK_REPOSITORY = "fork_repository"
    ARCHIVED_REPOSITORY = "archived_repository"


class ExcludedPortfolioRepository(BaseModel):
    repository: GitHubRepository
    reasons: list[PortfolioRepositoryExclusionReason] = Field(min_length=1)


class PortfolioRepositorySelection(BaseModel):
    version: str = Field(min_length=1)
    selected: list[GitHubRepository]
    excluded: list[ExcludedPortfolioRepository]


class PortfolioRepositoryFailureCode(StrEnum):
    GITHUB_TIMEOUT = "github_timeout"
    GITHUB_UNAVAILABLE = "github_unavailable"
    GITHUB_REPOSITORY_NOT_FOUND = "github_repository_not_found"
    GITHUB_RATE_LIMIT = "github_rate_limit"
    GITHUB_UPSTREAM_ERROR = "github_upstream_error"


class PortfolioRepositoryResult(BaseModel):
    repository: GitHubRepository
    analysis: RepositoryAnalysis
    score: RepositoryScore


class PortfolioRepositoryFailure(BaseModel):
    repository: GitHubRepository
    code: PortfolioRepositoryFailureCode
    message: str = Field(min_length=1)


class PortfolioRepositoryAnalysis(BaseModel):
    selection_version: str = Field(min_length=1)
    repositories: list[PortfolioRepositoryResult]
    failures: list[PortfolioRepositoryFailure]
    has_failures: bool


class PortfolioTechnologyUsage(BaseModel):
    technology: str = Field(min_length=1)
    repository_count: int = Field(gt=0)


class PortfolioCategoryUsage(BaseModel):
    category: RepositoryCategory
    repository_count: int = Field(gt=0)


class PortfolioSignalCount(BaseModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    detected_repository_count: int = Field(ge=0)


class RepositoryScoreBucket(BaseModel):
    min_score: int = Field(ge=0, le=100)
    max_score: int = Field(ge=0, le=100)
    repository_count: int = Field(ge=0)


class PortfolioAggregation(BaseModel):
    selection_version: str = Field(min_length=1)
    selected_repository_count: int = Field(ge=0)
    successful_repository_count: int = Field(ge=0)
    failed_repository_count: int = Field(ge=0)
    has_failures: bool
    partial_evidence_repository_count: int = Field(ge=0)
    technology_distribution: list[PortfolioTechnologyUsage]
    category_distribution: list[PortfolioCategoryUsage]
    primary_category_distribution: list[PortfolioCategoryUsage]
    portfolio_signals: list[PortfolioSignalCount]
    repository_score_distribution: list[RepositoryScoreBucket]


class PortfolioInsight(BaseModel):
    key: str = Field(min_length=1)
    message: str = Field(min_length=1)
    detected_repository_count: int = Field(ge=0)
    analyzed_repository_count: int = Field(gt=0)


class PortfolioRecurringTechnology(BaseModel):
    technology: str = Field(min_length=1)
    repository_count: int = Field(ge=2)


class PortfolioDominantArea(BaseModel):
    category: RepositoryCategory
    repository_count: int = Field(ge=2)


class PortfolioIntelligence(BaseModel):
    version: str = Field(min_length=1)
    strength_signals: list[PortfolioInsight]
    improvement_signals: list[PortfolioInsight]
    recurring_technologies: list[PortfolioRecurringTechnology]
    dominant_areas: list[PortfolioDominantArea]
    limitations: list[str]


class PortfolioScoreRuleResult(BaseModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    weight: int = Field(gt=0)
    detected_repository_count: int = Field(ge=0)
    analyzed_repository_count: int = Field(gt=0)


class PortfolioScoreDimensionResult(BaseModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    points_earned: int = Field(ge=0)
    points_possible: int = Field(gt=0)
    score: int = Field(ge=0, le=100)
    rules: list[PortfolioScoreRuleResult] = Field(min_length=1)


class PortfolioScore(BaseModel):
    version: str = Field(min_length=1)
    is_available: bool
    overall_score: int | None = Field(ge=0, le=100)
    scored_repository_count: int = Field(ge=0)
    dimensions: list[PortfolioScoreDimensionResult]
    is_partial: bool
    limitations: list[str]


class GitHubPortfolioAnalysis(BaseModel):
    user: GitHubUser
    selection: PortfolioRepositorySelection
    repository_analysis: PortfolioRepositoryAnalysis
    aggregation: PortfolioAggregation
    intelligence: PortfolioIntelligence
    score: PortfolioScore


class GitHubPortfolioAnalysisResponse(GitHubPortfolioAnalysis):
    viewer_context: ViewerContext
